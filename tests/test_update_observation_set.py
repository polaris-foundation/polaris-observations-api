from datetime import datetime, timezone
from typing import Dict

import pytest
from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from flask_batteries_included.sqldb import db

from dhos_observations_api.blueprint_api import controller
from dhos_observations_api.models.sql.observation import Observation
from dhos_observations_api.models.sql.observation_set import ObservationSet


@pytest.mark.usefixtures("app", "jwt_send_clinician_uuid", "uses_sql_database")
class TestUpdateObservationSet:
    @pytest.fixture
    def an_obs_set(self, encounter_uuid: str, location_uuid: str) -> ObservationSet:
        record_time = datetime(2019, 1, 1, 11, 59, 20, tzinfo=timezone.utc)
        obs_set: Dict = ObservationSet.new(
            observations=[
                {
                    "patient_refused": False,
                    "observation_value": 1,
                    "observation_type": "spo2",
                }
            ],
            record_time=record_time,
            score_system="news2",
            spo2_scale=1,
            encounter_id=encounter_uuid,
        )
        db.session.commit()
        return ObservationSet.query.get(obs_set["uuid"])

    def test_patch_missing_obs_set(self) -> None:
        with pytest.raises(EntityNotFoundException):
            controller.update_observation_set(
                observation_set_uuid="nope", updated_obs_set={}
            )

    def test_patch_invalid_obs_set_without_type(
        self, an_obs_set: ObservationSet
    ) -> None:

        with pytest.raises(ValueError):
            controller.update_observation_set(
                observation_set_uuid=an_obs_set.uuid,
                updated_obs_set={"observations": [{"score_value": 1}]},
            )

    def test_patch_invalid_obs_set_without_value(
        self, an_obs_set: ObservationSet
    ) -> None:

        with pytest.raises(ValueError):
            controller.update_observation_set(
                observation_set_uuid=an_obs_set.uuid,
                updated_obs_set={"observations": [{"observation_type": "spo2"}]},
            )

    def test_patch_obs_set_success(self, an_obs_set: ObservationSet) -> None:

        response = controller.update_observation_set(
            observation_set_uuid=an_obs_set.uuid,
            updated_obs_set={
                "observations": [{"score_value": 2, "observation_type": "spo2"}]
            },
        )

        # check dict response
        assert isinstance(response, dict)
        observation_dict = next(
            (i for i in response["observations"] if i["observation_type"] == "spo2"),
            None,
        )
        assert observation_dict is not None
        assert observation_dict["score_value"] == 2

        # check model instance
        observation = next(
            (i for i in an_obs_set.observations if i.observation_type == "spo2"), None
        )
        assert observation is not None
        assert isinstance(observation, Observation)
        assert observation.score_value == 2
