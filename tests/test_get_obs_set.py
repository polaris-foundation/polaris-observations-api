from datetime import datetime, timezone
from typing import Any, Dict, Generator

import pytest
from flask import jsonify
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from flask_batteries_included.helpers.timestamp import (
    parse_iso8601_to_datetime_typesafe,
)
from flask_batteries_included.sqldb import db

from dhos_observations_api.blueprint_api import controller
from dhos_observations_api.models.api_spec import ObservationSetResponse
from dhos_observations_api.models.sql.observation import Observation
from dhos_observations_api.models.sql.observation_metadata import ObservationMetaData
from dhos_observations_api.models.sql.observation_set import ObservationSet


@pytest.mark.usefixtures("app", "jwt_send_clinician_uuid")
class TestGetObservationSet:
    @pytest.fixture(autouse=True)
    def clean_up_after_test(self) -> Generator[None, None, None]:
        # Yield nothing, then after the test run the cleanup query.
        yield
        for model in (ObservationMetaData, Observation, ObservationSet):
            rows_deleted = db.session.query(model).delete()
            print(f"{model.__name__}: {rows_deleted} rows deleted")
        db.session.commit()

    def test_get_obs_set_unknown_uuid(self) -> None:
        with pytest.raises(EntityNotFoundException):
            controller.get_observation_set_by_id(observation_set_uuid="fake-uuid")

    @pytest.mark.parametrize("compact", [True, False])
    def test_get_obs_set_success(self, encounter_uuid: str, compact: bool) -> None:
        record_time = datetime.now().replace(tzinfo=timezone.utc)
        obs_set = ObservationSet.new(
            encounter_id=encounter_uuid,
            record_time=record_time,
            observations=[
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "spo2",
                }
            ],
        )

        response = jsonify(
            controller.get_observation_set_by_id(obs_set["uuid"], compact=compact)
        )
        assert response.json
        returned_obs_set: Dict[str, Any] = ObservationSetResponse().load(response.json)

        assert returned_obs_set["uuid"] == obs_set["uuid"]
        assert returned_obs_set["observations"][0]["patient_refused"] is False
        assert returned_obs_set["observations"][0]["observation_value"] == 1
        assert returned_obs_set["observations"][0]["observation_type"] == "spo2"
        assert ("obx_reference_range" not in returned_obs_set) == compact

    def test_get_all_observation_sets_for_encounter_unknown(self) -> None:
        # We don't validate encounter UUIDs, so invalid uuid just returns an empty list
        result = controller.get_observation_sets_for_encounters(
            encounter_ids=["fake-uuid"]
        )
        assert result == []

    def test_get_all_observation_sets_for_encounter_success(
        self, encounter_uuid: str, clinician: str
    ) -> None:
        older_record_time = datetime(2018, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        newer_record_time = datetime(2018, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        obs_set_older = ObservationSet.new(
            encounter_id=encounter_uuid,
            record_time=older_record_time,
            score_system="news2",
            spo2_scale=2,
            observations=[
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "spo2",
                    "measured_time": older_record_time,
                    "observation_metadata": {"mask": "Room Air", "mask_percent": 100},
                },
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "heart_rate",
                    "measured_time": older_record_time,
                },
            ],
        )
        obs_set_newer = ObservationSet.new(
            encounter_id=encounter_uuid,
            record_time=newer_record_time,
            score_system="news2",
            observations=[
                {
                    "patient_refused": False,
                    "observation_value": 60,
                    "observation_type": "heart_rate",
                    "measured_time": newer_record_time,
                }
            ],
        )
        db.session.commit()
        response = controller.get_observation_sets_for_encounters([encounter_uuid])

        assert len(response) == 2
        assert response[0]["uuid"] == obs_set_newer["uuid"]
        assert response[0]["created_by"] == clinician
        assert response[0]["created_by"] == obs_set_newer["created_by"]
        assert response[0]["created"] == obs_set_newer["created"]
        assert response[0]["modified_by"] == clinician
        assert response[0]["modified_by"] == obs_set_newer["modified_by"]
        assert response[0]["modified"] == obs_set_newer["modified"]
        assert response[0]["spo2_scale"] == obs_set_newer["spo2_scale"]
        assert response[1]["uuid"] == obs_set_older["uuid"]

        response = controller.get_observation_sets_for_encounters(
            encounter_ids=[encounter_uuid], limit=1, compact=True
        )
        assert len(response) == 1
        assert response[0]["uuid"] == obs_set_newer["uuid"]

    def test_get_all_observation_sets_for_encounter_with_children(
        self, encounter_uuid: str
    ) -> None:
        child_encounter_uuid = generate_uuid()
        another_child_encounter_uuid = generate_uuid()

        older_record_time = datetime(2018, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        newer_record_time = datetime(2018, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        another_record_time = datetime(2010, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        parent_obs_dict = ObservationSet.new(
            encounter_id=encounter_uuid,
            record_time=newer_record_time,
            observations=[
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "spo2",
                }
            ],
        )
        parent_obs = ObservationSet.query.get(parent_obs_dict["uuid"])

        child_obs_dict = ObservationSet.new(
            encounter_id=child_encounter_uuid,
            record_time=older_record_time,
            observations=[
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "spo2",
                }
            ],
        )
        child_obs = ObservationSet.query.get(child_obs_dict["uuid"])

        another_child_obs_dict = ObservationSet.new(
            encounter_id=another_child_encounter_uuid,
            record_time=another_record_time,
            observations=[
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "spo2",
                }
            ],
        )
        another_child_obs = ObservationSet.query.get(another_child_obs_dict["uuid"])

        for limit, expected_encounter_ids, expected_obs_sets in [
            (
                None,
                [encounter_uuid, child_encounter_uuid, another_child_encounter_uuid],
                [parent_obs, child_obs, another_child_obs],
            ),
            (1, [encounter_uuid], [parent_obs]),
            (2, [encounter_uuid, child_encounter_uuid], [parent_obs, child_obs]),
            (
                3,
                [encounter_uuid, child_encounter_uuid, another_child_encounter_uuid],
                [parent_obs, child_obs, another_child_obs],
            ),
        ]:

            observation_sets = controller.get_observation_sets_for_encounters(
                encounter_ids=[
                    another_child_encounter_uuid,
                    child_encounter_uuid,
                    encounter_uuid,
                ],
                limit=limit,
            )
            encounter_ids = [os["encounter_id"] for os in observation_sets]
            observation_ids = [o["uuid"] for o in observation_sets]

            assert encounter_ids == expected_encounter_ids
            assert observation_ids == [obs.uuid for obs in expected_obs_sets]

    def test_get_latest_observation_set_for_encounter_unknown(
        self, encounter_uuid: str
    ) -> None:
        with pytest.raises(EntityNotFoundException):
            controller.get_latest_observation_set_for_encounters(
                encounter_ids=[encounter_uuid]
            )

    def test_get_latest_observation_set_for_encounter_success(
        self, encounter_uuid: str
    ) -> None:

        ObservationSet.new(
            encounter_id=encounter_uuid,
            record_time=parse_iso8601_to_datetime_typesafe("2018-01-01T00:00:00.000Z"),
            score_system="news2",
            spo2_scale=1,
            observations=[
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "spo2",
                    "measured_time": parse_iso8601_to_datetime_typesafe(
                        "2018-01-01T00:00:00.000Z"
                    ),
                },
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "heart_rate",
                    "measured_time": parse_iso8601_to_datetime_typesafe(
                        "2018-01-01T00:00:00.000Z"
                    ),
                },
            ],
        )

        obs_set_newer = ObservationSet.new(
            encounter_id=encounter_uuid,
            record_time=parse_iso8601_to_datetime_typesafe("2018-01-02T00:00:00.000Z"),
            score_system="news2",
            spo2_scale=1,
            observations=[
                {
                    "patient_refused": False,
                    "observation_value": 60,
                    "observation_type": "heart_rate",
                    "measured_time": parse_iso8601_to_datetime_typesafe(
                        "2018-01-02T00:00:00.000Z"
                    ),
                },
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "spo2",
                    "measured_time": parse_iso8601_to_datetime_typesafe(
                        "2018-01-02T00:00:00.000Z"
                    ),
                },
            ],
        )
        db.session.commit()

        response = controller.get_latest_observation_set_for_encounters(
            encounter_ids=[encounter_uuid]
        )

        assert response["uuid"] == obs_set_newer["uuid"]
