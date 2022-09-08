import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict
from unittest.mock import Mock

import pytest
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.timestamp import (
    parse_iso8601_to_datetime_typesafe,
)
from flask_batteries_included.sqldb import db
from pytest_mock import MockFixture

from dhos_observations_api.blueprint_api import controller
from dhos_observations_api.models.api_spec import ObservationSetRequest
from dhos_observations_api.models.sql.observation_set import ObservationSet


@pytest.mark.usefixtures("app", "uses_sql_database")
class TestController:
    @pytest.mark.parametrize("suppress_obs_publish", [True, False])
    @pytest.mark.parametrize(
        ["obs_set_time", "obs_set_spo2_scale"],
        [
            ("2019-01-08T00:00:00.000Z", 2),
            ("2019-01-08T00:00:00.000Z", 1),
            ("2019-01-06T00:00:00.000Z", 2),
            ("2019-01-06T00:00:00.000Z", 1),
            ("2019-01-04T00:00:00.000Z", 2),
            ("2019-01-04T00:00:00.000Z", 1),
            ("2019-01-02T00:00:00.000Z", 2),
            ("2019-01-02T00:00:00.000Z", 1),
            ("1970-01-01T00:00:00.000Z", 1),
            ("1970-01-01T00:00:00.000Z", 2),
        ],
    )
    def test_create_observation_set_spo2_scale_changed_with_history(
        self,
        mocker: MockFixture,
        encounter_uuid: str,
        location_uuid: str,
        obs_set_time: str,
        obs_set_spo2_scale: int,
        mock_publish: Mock,
        suppress_obs_publish: bool,
    ) -> None:
        obs_set: ObservationSetRequest.Meta.Dict = {
            "encounter_id": encounter_uuid,
            "location": location_uuid,
            "record_time": parse_iso8601_to_datetime_typesafe(obs_set_time),
            "score_system": "news2",
            "spo2_scale": obs_set_spo2_scale,
            "observations": [
                {
                    "observation_type": "spo2",
                    "measured_time": parse_iso8601_to_datetime_typesafe(obs_set_time),
                    "observation_value": 97,
                }
            ],
        }
        result = controller.create_observation_set(
            obs_set, suppress_obs_publish=suppress_obs_publish
        )
        assert result["encounter_id"] == encounter_uuid
        assert result["spo2_scale"] == obs_set_spo2_scale
        assert "spo2_scale_has_changed" not in result
        assert result["location"] == location_uuid

        assert mock_publish.call_count == (1 if suppress_obs_publish else 3)

    def test_retrieve_observation_count_for_encounter_ids(
        self, statement_counter: Callable
    ) -> None:
        encounter_1 = generate_uuid()
        for i in range(5):
            ObservationSet.new(
                encounter_id=encounter_1,
                score_system="news2",
                record_time=datetime.now(),
                observations=[
                    {
                        "observation_type": "o2_therapy_status",
                        "patient_refused": False,
                        "observation_unit": "L/min",
                        "measured_time": datetime.now(),
                        "observation_value": 22,
                        "observation_metadata": {
                            "mask": "High Flow",
                            "mask_percent": 35,
                        },
                    }
                ],
            )

        encounter_2 = generate_uuid()
        for i in range(3):
            ObservationSet.new(
                encounter_id=encounter_2,
                score_system="news2",
                record_time=datetime.now(),
                observations=[
                    {
                        "observation_type": "o2_therapy_status",
                        "patient_refused": False,
                        "observation_unit": "L/min",
                        "measured_time": datetime.now(),
                        "observation_value": 22,
                        "observation_metadata": {
                            "mask": "High Flow",
                            "mask_percent": 35,
                        },
                    }
                ],
            )

        db.session.commit()
        encounter_3 = generate_uuid()
        with statement_counter(limit=1):
            result = controller.retrieve_observation_count_for_encounter_ids(
                [encounter_1, encounter_2, encounter_3]
            )
        assert result == {encounter_1: 5, encounter_2: 3, encounter_3: 0}

    def test_refresh_agg_observation_sets(
        self,
        mocker: MockFixture,
    ) -> None:
        mocker.patch(
            "dhos_observations_api.blueprint_api.controller.db.engine.execute",
        )
        result = controller.refresh_agg_observation_sets()
        assert result["time_taken"] is not None

    def test_on_time_observation_sets(
        self, mocker: MockFixture, aggregate_observation_sets: Dict
    ) -> None:
        obs_sets = [
            ["location_uuid_1", "2021-01-01", "low", 9, 1],
            ["location_uuid_1", "2021-01-01", "medium", 8, 2],
            ["location_uuid_1", "2021-01-01", "high", 5, 5],
        ]
        mocker.patch(
            "dhos_observations_api.blueprint_api.controller.db.engine.execute",
            return_value=obs_sets,
        )
        result = controller.on_time_observation_sets(
            start_date="2021-01-01",
            end_date="2021-02-01",
            location_uuids=["location_uuid_1"],
        )
        assert result == aggregate_observation_sets

    def test_missing_observation_sets(
        self, mocker: MockFixture, aggregate_missing_observation_sets: Dict
    ) -> None:
        obs_sets = [
            ["location_uuid_1", 30, 5, 27, 27, 29, 25, 30, 29, 26, 30],
        ]
        mocker.patch(
            "dhos_observations_api.blueprint_api.controller.db.engine.execute",
            return_value=obs_sets,
        )
        result = controller.missing_observation_sets(
            start_date="2021-01-01",
            end_date="2021-02-01",
            location_uuids=["location_uuid_1"],
        )
        assert result == aggregate_missing_observation_sets

    def test_observation_sets_time_intervals(
        self,
        mocker: MockFixture,
        aggregate_observation_intervals: Dict,
    ) -> None:
        obs_sets = [
            [
                "location_uuid_1",
                "low",
                121,
                91,
                81,
                71,
                81,
                91,
                101,
                111,
                101,
                91,
                71,
                61,
                51,
                41,
                31,
                21,
                11,
                51,
            ]
        ]
        mocker.patch(
            "dhos_observations_api.blueprint_api.controller.db.engine.execute",
            return_value=obs_sets,
        )
        result = controller.observation_sets_time_intervals(
            start_date="2021-01-01",
            end_date="2021-02-01",
            location_uuids=["location_uuid_1"],
        )
        assert result == aggregate_observation_intervals

    def test_agg_observation_sets_by_month(
        self,
        mocker: MockFixture,
        agg_observation_sets_by_month: Dict,
    ) -> None:
        obs_sets = [
            [
                "2021-09",
                "low",
                25,
                5,
                10,
                24,
                24,
                23,
                23,
                21,
                21,
                17,
                17,
                17,
            ],
            [
                "2021-09",
                "low-medium",
                25,
                5,
                10,
                24,
                24,
                23,
                23,
                21,
                21,
                17,
                17,
                17,
            ],
            [
                "2021-09",
                "medium",
                25,
                5,
                10,
                24,
                24,
                23,
                23,
                21,
                21,
                17,
                17,
                17,
            ],
            [
                "2021-09",
                "high",
                25,
                5,
                10,
                24,
                24,
                23,
                23,
                21,
                21,
                17,
                17,
                17,
            ],
            [
                "2021-08",
                "low",
                35,
                5,
                20,
                33,
                33,
                31,
                31,
                27,
                27,
                19,
                19,
                19,
            ],
            [
                "2021-08",
                "low-medium",
                35,
                10,
                20,
                33,
                33,
                31,
                31,
                27,
                27,
                19,
                19,
                19,
            ],
            [
                "2021-08",
                "medium",
                35,
                10,
                20,
                33,
                33,
                31,
                31,
                27,
                27,
                19,
                19,
                19,
            ],
            [
                "2021-08",
                "high",
                35,
                10,
                20,
                33,
                33,
                31,
                31,
                27,
                27,
                19,
                19,
                19,
            ],
        ]
        mocker.patch(
            "dhos_observations_api.blueprint_api.controller.db.engine.execute",
            return_value=obs_sets,
        )
        result = controller.agg_observation_sets_by_month(
            start_date="2021-08-01",
            end_date="2021-10-01",
            location_uuids=["location_uuid_1"],
        )
        assert result == agg_observation_sets_by_month

    def test_agg_observation_sets_by_location_month(
        self,
        mocker: MockFixture,
        agg_observation_sets_by_location_month: Dict,
    ) -> None:
        obs_sets = [
            [
                "location_uuid_1",
                "2021-09",
                "low",
                25,
                5,
                10,
                24,
                24,
                23,
                23,
                21,
                21,
                17,
                17,
                17,
            ],
            [
                "location_uuid_1",
                "2021-09",
                "low-medium",
                25,
                5,
                10,
                24,
                24,
                23,
                23,
                21,
                21,
                17,
                17,
                17,
            ],
            [
                "location_uuid_1",
                "2021-09",
                "medium",
                25,
                5,
                10,
                24,
                24,
                23,
                23,
                21,
                21,
                17,
                17,
                17,
            ],
            [
                "location_uuid_1",
                "2021-09",
                "high",
                25,
                5,
                10,
                24,
                24,
                23,
                23,
                21,
                21,
                17,
                17,
                17,
            ],
            [
                "location_uuid_1",
                "2021-08",
                "low",
                35,
                5,
                20,
                33,
                33,
                31,
                31,
                27,
                27,
                19,
                19,
                19,
            ],
            [
                "location_uuid_1",
                "2021-08",
                "low-medium",
                35,
                10,
                20,
                33,
                33,
                31,
                31,
                27,
                27,
                19,
                19,
                19,
            ],
            [
                "location_uuid_1",
                "2021-08",
                "medium",
                35,
                10,
                20,
                33,
                33,
                31,
                31,
                27,
                27,
                19,
                19,
                19,
            ],
            [
                "location_uuid_1",
                "2021-08",
                "high",
                35,
                10,
                20,
                33,
                33,
                31,
                31,
                27,
                27,
                19,
                19,
                19,
            ],
        ]
        mocker.patch(
            "dhos_observations_api.blueprint_api.controller.db.engine.execute",
            return_value=obs_sets,
        )
        result = controller.all_agg_obs_by_location_by_month(
            start_date="2021-08-01",
            end_date="2021-10-01",
        )
        assert result == agg_observation_sets_by_location_month

    def test_mins_late(
        self,
        encounter_uuid: str,
        location_uuid: str,
        mock_publish: Mock,
        mocker: MockFixture,
    ) -> None:
        obs_set: ObservationSetRequest.Meta.Dict = {
            "score_system": "news2",
            "record_time": parse_iso8601_to_datetime_typesafe(
                "2021-10-05T09:10:00.000Z"
            ),
            "spo2_scale": 1,
            "observations": [
                {
                    "observation_type": "temperature",
                    "patient_refused": False,
                    "observation_unit": "celsius",
                    "measured_time": parse_iso8601_to_datetime_typesafe(
                        "2021-10-05T09:10:00.000Z"
                    ),
                    "observation_value": 35,
                }
            ],
            "encounter_id": encounter_uuid,
            "is_partial": True,
            "patient_id": "patient_uuid",
            "score_severity": "low-medium",
            "score_string": "3",
            "time_next_obs_set_due": parse_iso8601_to_datetime_typesafe(
                "2021-10-05T10:00:00.000Z"
            ),
        }
        mock_obs_update = mocker.patch(
            "dhos_observations_api.blueprint_api.message.publish_scored_obs_message",
            return_value=None,
        )
        obs1 = controller.create_observation_set(obs_set, suppress_obs_publish=False)
        mock_obs_update.assert_called_with(obs1)
        assert obs1["mins_late"] == 0

        obs_set["record_time"] = parse_iso8601_to_datetime_typesafe(
            "2021-10-05T11:20:00.000Z"
        )
        obs_set["time_next_obs_set_due"] = parse_iso8601_to_datetime_typesafe(
            "2021-10-05T12:20:00.000Z"
        )
        obs2 = controller.create_observation_set(obs_set, suppress_obs_publish=False)
        assert obs2["mins_late"] == 80

    def test_get_latest_observation_sets_by_encounter_ids_performance(
        self, mocker: MockFixture, statement_counter: Callable
    ) -> None:
        encounter_uuids = []
        mocker.patch(
            "dhos_observations_api.blueprint_api.message.publish_scored_obs_message",
            return_value=None,
        )
        for i in range(100):
            encounter_uuid = str(uuid.uuid4())
            encounter_uuids.append(encounter_uuid)
            record_time = datetime(
                2019, 1, 1, 11, 59, 20, tzinfo=timezone.utc
            ) + timedelta(seconds=i)
            for j in range(10):
                record_time = datetime(
                    2019, 1, 1, 11, 59, 20, tzinfo=timezone.utc
                ) + timedelta(seconds=j)
                obs_set: ObservationSetRequest.Meta.Dict = {
                    "score_system": "news2",
                    "record_time": record_time,
                    "spo2_scale": 1,
                    "observations": [
                        {
                            "observation_type": "temperature",
                            "patient_refused": False,
                            "observation_unit": "celsius",
                            "measured_time": record_time,
                            "observation_value": 35,
                        },
                        {
                            "observation_type": "o2_therapy_status",
                            "patient_refused": False,
                            "observation_unit": "L/min",
                            "measured_time": record_time,
                            "observation_value": 22,
                            "observation_metadata": {
                                "mask": "High Flow",
                                "mask_percent": 35,
                            },
                        },
                    ],
                    "encounter_id": encounter_uuid,
                    "is_partial": True,
                    "patient_id": "patient_uuid",
                    "score_severity": "low-medium",
                    "score_string": "3",
                    "time_next_obs_set_due": record_time,
                }

            controller.create_observation_set(obs_set, suppress_obs_publish=False)

        with statement_counter(limit=1):
            time_start = time.perf_counter()
            results = controller.get_latest_observation_sets_by_encounter_ids(
                encounter_ids=encounter_uuids
            )
            time_taken = time.perf_counter() - time_start
        print(f"get_latest_observation_sets_by_encounter_ids:{time_taken}")
        assert len(results) == 100
        assert time_taken < 0.5
