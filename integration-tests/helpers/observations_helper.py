from datetime import datetime, timezone
from typing import Dict, Optional

from assertpy import assert_that, soft_assertions
from dateutil import parser


def generate_observation_set_request(
    encounter_uuid: str,
    location_uuid: str,
    measured_time: Optional[datetime] = None,
    timespec: str = "milliseconds",
    utc_to_z: bool = True,
) -> Dict:
    if measured_time is None:
        measured_time = datetime.now(tz=timezone.utc)
    measured_time_str = measured_time.isoformat(timespec=timespec)

    if utc_to_z:
        measured_time_str = measured_time_str.replace("+00:00", "Z")

    return {
        "score_system": "news2",
        "record_time": measured_time_str,
        "spo2_scale": 1,
        "observations": [
            {
                "measured_time": measured_time_str,
                "observation_string": "Alert",
                "observation_type": "consciousness_acvpu",
                "patient_refused": False,
                "observation_unit": None,
                "observation_value": None,
                "score_value": 0,
            },
            {
                "observation_type": "heart_rate",
                "patient_refused": False,
                "observation_unit": "bpm",
                "measured_time": measured_time_str,
                "observation_value": 100,
                "score_value": 1,
            },
            {
                "observation_type": "spo2",
                "patient_refused": False,
                "observation_unit": "percentage",
                "measured_time": measured_time_str,
                "observation_value": 55,
                "score_value": 3,
            },
            {
                "observation_type": "o2_therapy_status",
                "patient_refused": False,
                "observation_unit": "L/min",
                "measured_time": "2021-04-06T13:56:32.312Z",
                "observation_value": 22,
                "observation_metadata": {"mask": "High Flow", "mask_percent": 35},
            },
            {
                "observation_type": "respiratory_rate",
                "patient_refused": False,
                "observation_unit": "/min",
                "measured_time": measured_time_str,
                "observation_value": 35,
                "score_value": 3,
            },
            {
                "observation_type": "temperature",
                "patient_refused": False,
                "observation_unit": "celsius",
                "measured_time": measured_time_str,
                "observation_value": 37,
                "score_value": 0,
            },
        ],
        "encounter_id": encounter_uuid,
        "location": location_uuid,
        "is_partial": True,
        "obx_abnormal_flags": "EXTHIGH",
        "obx_reference_range": "0-4",
        "ranking": "040710,998415907513237",
        "score_severity": "high",
        "score_string": "7",
        "score_value": 7,
        "time_next_obs_set_due": "2020-03-13T09:41:26.763Z",
    }


def generate_update_observation_set_request() -> Dict:
    return {
        "score_string": "12C",
        "score_value": 12,
        "observations": [
            {"observation_type": "temperature", "score_value": 7},
            {"observation_type": "respiratory_rate", "score_value": 9},
        ],
    }


def assert_observations_set_body(
    actual_observation_set: dict, expected_observation_set: dict
) -> None:
    if "record_time" in actual_observation_set:
        actual_observation_set["record_time"] = parser.isoparse(
            actual_observation_set["record_time"]
        )
    with soft_assertions():
        assert_that(actual_observation_set).has_score_system(
            expected_observation_set["score_system"]
        ).has_record_time(
            parser.isoparse(expected_observation_set["record_time"])
        ).has_spo2_scale(
            expected_observation_set["spo2_scale"]
        ).has_encounter_id(
            expected_observation_set["encounter_id"]
        ).has_is_partial(
            expected_observation_set["is_partial"]
        )
        for expected_observation in expected_observation_set["observations"]:
            for actual_observation in actual_observation_set["observations"]:
                if (
                    actual_observation["observation_type"]
                    == expected_observation["observation_type"]
                ):
                    if "measured_time" in actual_observation:
                        actual_observation["measured_time"] = parser.isoparse(
                            actual_observation["measured_time"]
                        )

                    assert_that(actual_observation).has_measured_time(
                        parser.isoparse(expected_observation["measured_time"])
                    ).has_patient_refused(
                        expected_observation["patient_refused"]
                    ).has_observation_unit(
                        expected_observation["observation_unit"]
                    ).has_observation_value(
                        expected_observation["observation_value"]
                    )
