from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.security.jwt import current_jwt_user
from flask_batteries_included.sqldb import ModelIdentifier, db
from sqlalchemy import Index

from dhos_observations_api.models.api_spec import (
    ObservationRequest,
    ObservationSetResponse,
)
from dhos_observations_api.models.sql.observation import Observation
from dhos_observations_api.models.sql.observation_metadata import ObservationMetaData


class ObservationSet(ModelIdentifier, db.Model):
    # Required fields
    uuid = db.Column(
        db.String(length=36),
        unique=True,
        nullable=False,
        primary_key=True,
    )
    encounter_id = db.Column(db.String(length=36), nullable=True, index=True)
    record_time = db.Column(db.DateTime(timezone=True), unique=False, nullable=False)
    score_system = db.Column(db.String, nullable=True)
    observations = db.relationship(
        Observation,
        primaryjoin="ObservationSet.uuid == Observation.observation_set_uuid",
    )

    # Optional fields
    score_string = db.Column(db.String, nullable=True)
    score_value = db.Column(db.Integer, nullable=True)
    score_severity = db.Column(db.String, nullable=True)
    monitoring_instruction = db.Column(db.String, nullable=True)
    time_next_obs_set_due = db.Column(
        db.DateTime(timezone=True), unique=False, nullable=True, default=None
    )
    spo2_scale = db.Column(db.Integer, nullable=True, default=1)
    is_partial = db.Column(db.Boolean, nullable=True)
    empty_set = db.Column(db.Boolean, nullable=True)
    ranking = db.Column(db.String, nullable=True)
    obx_reference_range = db.Column(
        db.String, nullable=True
    )  # Used only in ORU messages
    obx_abnormal_flags = db.Column(
        db.String, nullable=True
    )  # Used only in ORU messages
    location = db.Column(db.String(length=36), nullable=True)

    patient_id = db.Column(db.String(length=36), nullable=True, index=True)
    mins_late = db.Column(db.Integer, nullable=True)

    # Index to help finding latest obs set per encounter
    __table_args__ = (Index("encounter_record_time", encounter_id, record_time.desc()),)

    @classmethod
    def new(
        cls,
        record_time: Union[str, datetime],
        uuid: Optional[str] = None,
        observations: List[ObservationRequest.Meta.Dict] = None,
        **kw: Any,
    ) -> Dict:
        if not uuid:
            uuid = generate_uuid()

        if kw.get("spo2_scale", None) is None:
            kw["spo2_scale"] = 1

        if kw.get("created_by_", None) is None:
            kw["created_by_"] = current_jwt_user()

        if kw.get("created", None) is None:
            kw["created"] = datetime.utcnow()

        if kw.get("modified_by_", None) is None:
            kw["modified_by_"] = current_jwt_user()

        if kw.get("modified", None) is None:
            kw["modified"] = datetime.utcnow()

        observation_models: List[Observation] = []
        observation_metadatas: List[ObservationMetaData] = []
        if observations:
            for obs in observations:
                obs_uuid: str = generate_uuid()
                observation_metadata = obs.pop("observation_metadata", None)
                observation_models.append(
                    Observation.new(uuid=obs_uuid, observation_set_uuid=uuid, **obs)
                )

                if observation_metadata:
                    observation_metadatas.append(
                        ObservationMetaData.new(
                            observation_uuid=obs_uuid, **observation_metadata
                        )
                    )

        obs_set = ObservationSet(
            uuid=uuid,
            record_time=record_time,
            **kw,
        )

        db.session.bulk_save_objects(
            [obs_set] + observation_models + observation_metadatas
        )

        return cls._merge_obs_set_dicts(
            observation_set=obs_set.to_map_dict(),
            observations=[o.to_map_dict() for o in observation_models],
            observation_metadatas=[om.to_map_dict() for om in observation_metadatas],
        )

    def _merge_obs_set_dicts(
        observation_set: Dict,
        observations: List[Dict],
        observation_metadatas: List[Dict],
    ) -> Dict:
        # Merged the data used to generate the objects into expected return
        # format to prevent fetching the object from the database again
        result = observation_set
        result.update({"observations": observations})

        for observation_metadata in observation_metadatas:
            for i, observation in enumerate(result["observations"]):
                # Check if observation has metadata and add correct metadata
                # to correct observation
                if observation["uuid"] == observation_metadata["observation_uuid"]:
                    del observation_metadata["observation_uuid"]
                    result["observations"][i].update(
                        {"observation_metadata": observation_metadata}
                    )
                    break
        return result

    def __repr__(self) -> str:
        return (
            f"<ObservationSet {self.uuid} encounter={self.encounter_id} {self.score_severity} obs"
            f"={len(self.observations)}>"
        )

    def to_dict(self, compact: bool = True) -> ObservationSetResponse.Meta.Dict:
        observations = [o.to_dict() for o in self.observations]
        record_time = self.record_time

        if record_time.tzinfo is None:
            # sqlite loses utc, shouldn't happen outside tests
            record_time = record_time.replace(tzinfo=timezone.utc)

        result: ObservationSetResponse.Meta.Dict = {
            "encounter_id": self.encounter_id,
            "patient_id": self.patient_id,
            "score_system": self.score_system,
            "score_string": self.score_string,
            "score_value": self.score_value,
            "score_severity": self.score_severity,
            "record_time": record_time,
            "spo2_scale": self.spo2_scale,
            "observations": observations,
            "is_partial": self.is_partial,
            "empty_set": self.empty_set,
            "ranking": self.ranking,
            "time_next_obs_set_due": self.time_next_obs_set_due,
            "monitoring_instruction": self.monitoring_instruction,
            "location": self.location,
            "mins_late": self.mins_late,
        }

        if not compact:
            result.update(
                {
                    "obx_reference_range": self.obx_reference_range,
                    "obx_abnormal_flags": self.obx_abnormal_flags,
                }
            )
        result.update(self.pack_identifier())  # type:ignore
        return result

    def to_map_dict(self) -> Dict:
        record_time = self.record_time

        if record_time.tzinfo is None:
            # sqlite loses utc, shouldn't happen outside tests
            record_time = record_time.replace(tzinfo=timezone.utc)

        result = {
            "encounter_id": self.encounter_id,
            "patient_id": self.patient_id,
            "score_system": self.score_system,
            "score_string": self.score_string,
            "score_value": self.score_value,
            "score_severity": self.score_severity,
            "record_time": record_time,
            "spo2_scale": self.spo2_scale,
            "is_partial": self.is_partial,
            "empty_set": self.empty_set,
            "ranking": self.ranking,
            "time_next_obs_set_due": self.time_next_obs_set_due,
            "monitoring_instruction": self.monitoring_instruction,
            "location": self.location,
            "obx_reference_range": self.obx_reference_range,
            "obx_abnormal_flags": self.obx_abnormal_flags,
            "mins_late": self.mins_late,
        }
        result.update(self.pack_identifier())  # type:ignore

        return result

    def on_patch(self) -> None:
        self.modified = datetime.utcnow()
        self.modified_by_ = current_jwt_user()
