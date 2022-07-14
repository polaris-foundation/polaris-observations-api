from typing import Literal

import pytest
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.timestamp import (
    parse_iso8601_to_datetime_typesafe,
)
from mock import Mock

from dhos_observations_api.blueprint_api import controller
from dhos_observations_api.models.api_spec import ObservationSetRequest


@pytest.mark.usefixtures("app")
class TestPublishObservationSet:
    @pytest.mark.parametrize(
        ["suppress_obs_publish", "expected_call_count", "encounter_or_patient"],
        [(False, 3, "encounter"), (True, 1, "encounter"), (False, 2, "patient")],
    )
    def test_obs_set_publish(
        self,
        encounter_uuid: str,
        mock_publish: Mock,
        suppress_obs_publish: bool,
        expected_call_count: int,
        encounter_or_patient: Literal["encounter", "patient"],
    ) -> None:
        json_in: ObservationSetRequest.Meta.Dict = {
            "record_time": parse_iso8601_to_datetime_typesafe(
                "1970-01-01T00:00:00.000Z"
            ),
            "score_system": "news2",
            "observations": [
                {
                    "observation_type": "spo2",
                    "observation_value": 42,
                    "measured_time": parse_iso8601_to_datetime_typesafe(
                        "1970-01-01T00:00:00.000Z"
                    ),
                }
            ],
            "obx_reference_range": "0-4",
            "obx_abnormal_flags": "HIGH",
        }
        if encounter_or_patient == "encounter":
            json_in["encounter_id"] = generate_uuid()
        else:
            json_in["patient_id"] = generate_uuid()

        response = controller.create_observation_set(
            json_in, suppress_obs_publish=suppress_obs_publish
        )
        assert response["obx_reference_range"] == "0-4"
        assert response["obx_abnormal_flags"] == "HIGH"
        assert isinstance(response, dict)
        assert mock_publish.call_count == expected_call_count
