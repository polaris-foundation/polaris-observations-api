from typing import Dict

import pytest

from dhos_observations_api.models.sql.observation_metadata import ObservationMetaData


@pytest.mark.usefixtures("app", "uses_sql_database")
class TestObservationMetadata:
    def test_metadata_for_o2_therapy(self) -> None:
        obs_metadata: Dict = {
            "mask": "Venturi",
            "mask_percent": 80,
            "observation_uuid": "uuid",
        }
        return_value = ObservationMetaData.new(**obs_metadata)
        assert return_value.mask == "Venturi"
        assert return_value.mask_percent == 80
        assert return_value.to_dict()["mask"] == "Venturi"
        assert return_value.to_dict()["mask_percent"] == 80

    def test_metadata_for_bp(self) -> None:
        obs_metadata: Dict = {
            "patient_position": "standing",
            "observation_uuid": "uuid",
        }
        return_value = ObservationMetaData.new(**obs_metadata)
        assert return_value.patient_position == "standing"
        assert return_value.to_dict()["patient_position"] == "standing"

    def test_metadata_for_gcs(self) -> None:
        obs_metadata: Dict = {
            "gcs_eyes": 4,
            "gcs_eyes_description": "Spontaneous",
            "gcs_verbal": 5,
            "gcs_verbal_description": "Oriented",
            "gcs_motor": 6,
            "gcs_motor_description": "Commands",
            "observation_uuid": "uuid",
        }
        return_value = ObservationMetaData.new(**obs_metadata)
        assert return_value.gcs_eyes == 4
        assert return_value.gcs_eyes_description == "Spontaneous"
        assert return_value.gcs_verbal == 5
        assert return_value.gcs_verbal_description == "Oriented"
        assert return_value.gcs_motor == 6
        assert return_value.gcs_motor_description == "Commands"
        assert return_value.to_dict()["gcs_eyes"] == 4
        assert return_value.to_dict()["gcs_eyes_description"] == "Spontaneous"
        assert return_value.to_dict()["gcs_verbal"] == 5
        assert return_value.to_dict()["gcs_verbal_description"] == "Oriented"
        assert return_value.to_dict()["gcs_motor"] == 6
        assert return_value.to_dict()["gcs_motor_description"] == "Commands"
