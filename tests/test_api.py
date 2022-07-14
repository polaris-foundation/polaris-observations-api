from typing import Any, Dict, Optional
from unittest.mock import Mock

import pytest
from flask import g
from flask.testing import FlaskClient
from flask_batteries_included.helpers.timestamp import parse_iso8601_to_datetime
from pytest_mock import MockFixture

from dhos_observations_api import blueprint_api
from dhos_observations_api.blueprint_api import controller


@pytest.mark.usefixtures(
    "jwt_send_clinician_uuid", "uses_sql_database", "jwt_contains_referring_device_id"
)
class TestApi:
    @pytest.fixture(autouse=True)
    def mock_bearer_validation(self, mocker: MockFixture) -> Mock:
        return mocker.patch(
            "jose.jwt.get_unverified_claims",
            return_value={
                "sub": "1234567890",
                "name": "John Doe",
                "iat": 1_516_239_022,
                "iss": "http://localhost/",
            },
        )

    def test_encounter_id_is_not_validated(self, client: Any) -> None:
        obs_set: Dict = {
            "encounter_id": "unknown_encounter",
            "record_time": "1970-01-01T00:00:00.000Z",
            "score_system": "news2",
            "spo2_scale": 1,
            "score_value": 0,
            "score_severity": "LOW",
            "score_string": "0",
            "observations": [
                {
                    "observation_type": "spo2",
                    "observation_value": 1,
                    "measured_time": "1970-01-01T00:00:00.000Z",
                    "score_value": 0,
                }
            ],
        }
        response = client.post(
            "/dhos/v2/observation_set?suppress_obs_publish=true",
            json=obs_set,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "encounter_id,patient_id,expected",
        [
            ("123-encounter_id", None, 200),
            (None, "123-patient", 200),
            ("123-encounter_id", "123-patient", 200),
            (None, None, 400),
        ],
    )
    def test_an_id_is_required(
        self,
        client: Any,
        encounter_id: Optional[str],
        patient_id: Optional[str],
        expected: int,
    ) -> None:
        obs_set: Dict = {
            "record_time": "1970-01-01T00:00:00.000Z",
            "score_system": "news2",
            "spo2_scale": 1,
            "score_value": 0,
            "score_severity": "LOW",
            "score_string": "0",
            "observations": [
                {
                    "observation_type": "spo2",
                    "observation_value": 1,
                    "measured_time": "1970-01-01T00:00:00.000Z",
                    "score_value": 0,
                }
            ],
        }
        if encounter_id:
            obs_set["encounter_id"] = encounter_id
        if patient_id:
            obs_set["patient_id"] = patient_id

        response = client.post(
            "/dhos/v2/observation_set?suppress_obs_publish=true",
            json=obs_set,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == expected

    @pytest.mark.parametrize(
        "start_date,end_date",
        [
            ("1970-01-03T00:00:00.000Z", "1970-01-04T00:00:00.000Z"),
            ("1970-01-03T00:00:00.000", "1970-01-04T00:00:00.000Z"),
            ("1970-01-03T00:00:00.000Z", "1970-01-04T00:00"),
            ("1970-01-03T00:00:00.000Z", "1970-01-04"),
        ],
    )
    def test_get_observation_sets_by_locations_and_date_range(
        self,
        client: FlaskClient,
        location_uuid: str,
        mocked_get_observations: Mock,
        start_date: str,
        end_date: str,
    ) -> None:
        response = client.get(
            f"/dhos/v2/observation_set_search?location={location_uuid}&start_date={start_date}&end_date={end_date}",
            headers={"Authorization": "Bearer TOKEN"},
        )

        assert response.status_code == 200
        assert response.json
        assert len(response.json) == 3

    def test_search_observation_sets_by_locations_and_date_range(
        self, client: FlaskClient, location_uuid: str, mocked_get_observations: Mock
    ) -> None:
        start_date = "1970-01-03T00:00:00.000Z"
        end_date = "1970-01-04T00:00:00.000Z"
        response = client.post(
            f"/dhos/v2/observation_set_search?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": "Bearer TOKEN"},
            json=[location_uuid],
        )

        assert response.status_code == 200
        assert response.json
        assert len(response.json) == 3

    def test_post_encounter_invalid(self, client: FlaskClient) -> None:
        json = {
            "score_system": "news2",
            "score_value": 12,
            "record_time": "2019-01-09T08:31:19.123+00:00",
            "spo2_scale": 2,
            "observations": [],
            "encounter_id": "8040254e-6ee7-42d4-83bf-1ae662a38859",
            "is_partial": False,
        }
        response = client.post(
            "/dhos/v2/observation_set",
            json=json,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        ["ask_suppress", "is_prod", "should_suppress"],
        [
            (False, False, False),
            (True, False, True),
            (False, True, False),
            (True, True, False),
        ],
    )
    def test_suppress_publish_ignored_in_prod(
        self,
        mocker: MockFixture,
        client: FlaskClient,
        ask_suppress: bool,
        is_prod: bool,
        should_suppress: bool,
    ) -> None:
        mocker.patch.object(
            blueprint_api, "is_production_environment", return_value=is_prod
        )
        mock_create = mocker.patch.object(
            controller, "create_observation_set", return_value={"uuid": "obs_uuid"}
        )
        obs_set_details: Dict[str, Any] = {
            "score_system": "news2",
            "score_value": 12,
            "record_time": "2019-01-09T08:31:19.123+00:00",
            "spo2_scale": 2,
            "observations": [],
            "encounter_id": "8040254e-6ee7-42d4-83bf-1ae662a38859",
            "is_partial": False,
        }

        expected_obs_set: Dict[str, object] = {
            **obs_set_details,
            "record_time": parse_iso8601_to_datetime(obs_set_details["record_time"]),
        }

        response = client.post(
            f"/dhos/v2/observation_set?suppress_obs_publish={str(ask_suppress).lower()}",
            json=obs_set_details,
            headers={"Authorization": "Bearer TOKEN"},
        )
        mock_create.assert_called_with(
            obs_set=expected_obs_set,
            suppress_obs_publish=should_suppress,
            referring_device_id=g.jwt_claims.get("referring_device_id"),
        )
        assert response.status_code == 200
        assert response.json
        assert response.json["uuid"] == "obs_uuid"

    def test_post_no_body(self, client: FlaskClient) -> None:
        response = client.post(
            f"/dhos/v2/observation_set", headers={"Authorization": "Bearer TOKEN"}
        )
        assert response.status_code == 400

    def test_post_invalid_body(self, client: FlaskClient) -> None:
        response = client.post(
            f"/dhos/v2/observation_set",
            json={"invalid": "body"},
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    def test_patch_route(self, client: FlaskClient, mocker: MockFixture) -> None:
        g.jwt_claims = {"system_id": "dhos-observations-adapter-worker"}
        mock_update = mocker.patch.object(
            controller, "update_observation_set", return_value={"uuid": "some_uuid"}
        )
        payload = {"score_value": 14, "observations": []}
        response = client.patch(
            f"/dhos/v2/observation_set/obs_set_uuid",
            json=payload,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json
        assert response.json["uuid"] == "some_uuid"
        mock_update.assert_called_with(
            observation_set_uuid="obs_set_uuid", updated_obs_set=payload
        )

    def test_get_by_encounter_id_route(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        mock_get = mocker.patch.object(
            controller,
            "get_observation_sets_for_encounters",
            return_value=[{"uuid": "something_1"}, {"uuid": "something_2"}],
        )
        response = client.get(
            f"/dhos/v2/observation_set?encounter_id=abcde&limit=21&compact=false",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json
        assert len(response.json) == 2
        assert response.json[0]["uuid"] == "something_1"
        mock_get.assert_called_with(encounter_ids=["abcde"], limit=21, compact=False)

    def test_get_by_multi_encounter_id_route(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        mock_get = mocker.patch.object(
            controller,
            "get_observation_sets_for_encounters",
            return_value=[{"uuid": "something_1"}, {"uuid": "something_2"}],
        )
        response = client.get(
            f"/dhos/v2/observation_set?encounter_id=abcde,fghij&limit=42&compact=true",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json
        assert len(response.json) == 2
        assert response.json[0]["uuid"] == "something_1"
        mock_get.assert_called_with(
            encounter_ids=["abcde", "fghij"], limit=42, compact=True
        )

    def test_get_by_multi_encounter_id_route2(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        mock_get = mocker.patch.object(
            controller,
            "get_observation_sets_for_encounters",
            return_value=[{"uuid": "something_1"}, {"uuid": "something_2"}],
        )
        response = client.get(
            f"/dhos/v2/observation_set?encounter_id=abcde&encounter_id=fghij&limit=42&compact=true",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json
        assert len(response.json) == 2
        assert response.json[0]["uuid"] == "something_1"
        mock_get.assert_called_with(
            encounter_ids=["abcde", "fghij"], limit=42, compact=True
        )

    @pytest.mark.parametrize(
        "url, expected_limit",
        [
            ("/dhos/v2/patient/1/observation_set?limit=100", 100),
            ("/dhos/v2/patient/1/observation_set", None),
        ],
    )
    def test_get_observation_sets_for_patient(
        self,
        client: FlaskClient,
        mocked_get_patient_observations: Mock,
        url: str,
        expected_limit: Optional[int],
    ) -> None:
        response = client.get(url, headers={"Authorization": "Bearer TOKEN"})
        assert response.status_code == 200
        assert response.json
        assert len(response.json) == 3
        mocked_get_patient_observations.assert_called_with(
            patient_id="1", limit=expected_limit
        )

    def test_retrieve_observation_set_count(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        payload = ["encounter_uuid_1", "encounter_uuid_2"]
        expected = {"encounter_uuid_1": 5, "encounter_uuid_2": 4}
        mock_retrieve = mocker.patch.object(
            controller,
            "retrieve_observation_count_for_encounter_ids",
            return_value=expected,
        )
        response = client.post(
            "/dhos/v2/observation_set/count",
            json=payload,
            headers={"Authorization": "Bearer TOKEN"},
        )
        mock_retrieve.assert_called_with(encounter_uuids=payload)
        assert response.status_code == 200
        assert response.json == expected

    def test_get_observation_sets(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        expected = {"uuid": "123456"}
        mocked_get_observations = mocker.patch(
            "dhos_observations_api.blueprint_api.controller.get_observation_sets",
            return_value=expected,
        )
        url = "/dhos/v2/observation_sets?modified_since=1988-01-01"
        response = client.get(url, headers={"Authorization": "Bearer TOKEN"})
        assert response.status_code == 200
        assert response.json == expected
        mocked_get_observations.assert_called_with(
            modified_since="1988-01-01", compact=False
        )

    def test_refresh_agg_observation_sets(
        self, client: FlaskClient, mocker: MockFixture
    ) -> None:
        url = "/dhos/v2/aggregate_obs"
        expected = {"time_taken": 1.234}
        mocked_refresh_agg_observation_sets = mocker.patch(
            "dhos_observations_api.blueprint_api.controller.refresh_agg_observation_sets",
            return_value=expected,
        )
        response = client.post(url, headers={"Authorization": "Bearer TOKEN"})
        assert response.json == expected
        assert response.status_code == 200
        mocked_refresh_agg_observation_sets.assert_called_once()

    def test_on_time_observation_sets(
        self, client: FlaskClient, mocker: MockFixture, aggregate_observation_sets: Dict
    ) -> None:
        url = "/dhos/v2/on_time_obs_stats?start_date=2021-01-01&end_date=2021-02-01"
        mocked_refresh_agg_observation_sets = mocker.patch(
            "dhos_observations_api.blueprint_api.controller.on_time_observation_sets",
            return_value=aggregate_observation_sets,
        )
        response = client.post(
            url, headers={"Authorization": "Bearer TOKEN"}, json=["location_uuid_1"]
        )
        assert response.json == aggregate_observation_sets
        assert response.status_code == 200
        mocked_refresh_agg_observation_sets.assert_called_once()

    def test_missing_observation_sets(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        aggregate_missing_observation_sets: Dict,
    ) -> None:
        url = "/dhos/v2/missing_obs_stats?start_date=2021-01-01&end_date=2021-02-01"
        mocked_missing_observation_sets = mocker.patch(
            "dhos_observations_api.blueprint_api.controller.missing_observation_sets",
            return_value=aggregate_missing_observation_sets,
        )
        response = client.post(
            url, headers={"Authorization": "Bearer TOKEN"}, json=["location_uuid_1"]
        )
        assert response.json == aggregate_missing_observation_sets
        assert response.status_code == 200
        mocked_missing_observation_sets.assert_called_once()

    def test_observation_sets_time_intervals(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        aggregate_observation_intervals: Dict,
        create_aggregate_observation_intervals: str,
    ) -> None:
        url = "/dhos/v2/on_time_intervals?start_date=2021-01-01&end_date=2021-02-01"
        mocked_refresh_agg_observation_sets = mocker.patch(
            "dhos_observations_api.blueprint_api.controller.observation_sets_time_intervals",
            return_value=aggregate_observation_intervals,
        )
        response = client.post(
            url, headers={"Authorization": "Bearer TOKEN"}, json=["location_uuid_1"]
        )
        assert response.json == aggregate_observation_intervals
        assert response.status_code == 200
        mocked_refresh_agg_observation_sets.assert_called_once()

    def test_agg_observation_sets_by_month(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        agg_observation_sets_by_month: Dict,
    ) -> None:
        url = "/dhos/v2/observation_sets_by_month?start_date=2021-08-01&end_date=2021-10-01"
        mocked_agg_observation_sets = mocker.patch(
            "dhos_observations_api.blueprint_api.controller.agg_observation_sets_by_month",
            return_value=agg_observation_sets_by_month,
        )
        response = client.post(
            url, headers={"Authorization": "Bearer TOKEN"}, json=["location_uuid_1"]
        )
        mocked_agg_observation_sets.assert_called_once()
        assert response.json == agg_observation_sets_by_month
        assert response.status_code == 200

    def test_all_agg_observation_sets_by_month(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        agg_observation_sets_by_location_month: Dict,
    ) -> None:
        url = "/dhos/v2/observation_sets_by_month?start_date=2021-08-01&end_date=2021-10-01"
        mocked_agg_observation_sets = mocker.patch(
            "dhos_observations_api.blueprint_api.controller.all_agg_obs_by_location_by_month",
            return_value=agg_observation_sets_by_location_month,
        )
        response = client.get(url, headers={"Authorization": "Bearer TOKEN"})
        mocked_agg_observation_sets.assert_called_once()
        assert response.json == agg_observation_sets_by_location_month
        assert response.status_code == 200
