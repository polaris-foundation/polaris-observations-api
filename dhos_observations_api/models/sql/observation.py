from datetime import datetime, timezone
from typing import Any, Dict

from flask_batteries_included.helpers.security.jwt import current_jwt_user
from flask_batteries_included.sqldb import ModelIdentifier, db

from dhos_observations_api.models.sql.observation_metadata import ObservationMetaData


class Observation(ModelIdentifier, db.Model):
    uuid = db.Column(
        db.String(length=36),
        unique=True,
        nullable=False,
        primary_key=True,
    )
    observation_set_uuid = db.Column(
        db.String, db.ForeignKey("observation_set.uuid"), index=True
    )
    observation_type = db.Column(db.String, unique=False, nullable=False, index=True)
    measured_time = db.Column(
        db.DateTime(timezone=True),
        unique=False,
        nullable=False,
        default=datetime.utcnow,
    )
    patient_refused = db.Column(db.Boolean().evaluates_none(), nullable=True)
    score_value = db.Column(db.Integer().evaluates_none(), nullable=True)
    observation_value = db.Column(db.Float().evaluates_none(), nullable=True)
    observation_string = db.Column(db.String().evaluates_none(), nullable=True)
    observation_unit = db.Column(db.String().evaluates_none(), nullable=True)
    observation_metadata = db.relationship(
        ObservationMetaData,
        lazy="joined",
        uselist=False,
        primaryjoin="Observation.uuid == ObservationMetaData.observation_uuid",
    )

    def __repr__(self) -> str:
        return (
            f"<Observation {self.observation_type} {self.observation_value}"
            f"{self.observation_unit if self.observation_unit else ''}>"
        )

    @classmethod
    def new(
        cls,
        observation_value: float = None,
        observation_string: str = None,
        patient_refused: bool = False,
        **kw: Any,
    ) -> "Observation":
        exclusive_keys = [observation_value, observation_string]
        if patient_refused is False and all(k is None for k in exclusive_keys):
            raise KeyError(
                "observation must contain either 'observation_value' or 'observation_string'"
            )

        if all(k is not None for k in exclusive_keys):
            raise KeyError(
                "observation must contain 'observation_value' or 'observation_string', not both"
            )

        # Force none on Nullable fields to allow bulk inserts

        instance = cls(
            observation_value=observation_value,
            observation_string=observation_string,
            patient_refused=patient_refused,
            **kw,
        )

        return instance

    def to_dict(self) -> Dict:
        if self.observation_metadata is None:
            metadata = None
        else:
            metadata = self.observation_metadata.to_dict()

        measured_time = self.measured_time
        if measured_time.tzinfo is None:
            # sqlite loses utc, shouldn't happen outside tests
            measured_time = measured_time.replace(tzinfo=timezone.utc)

        return {
            "observation_type": self.observation_type,
            "patient_refused": self.patient_refused,
            "score_value": self.score_value,
            "observation_value": self.observation_value,
            "observation_string": self.observation_string,
            "observation_unit": self.observation_unit,
            "observation_metadata": metadata,
            "measured_time": measured_time,
            "uuid": self.uuid,
        }

    def to_map_dict(self) -> Dict:
        measured_time = (
            datetime.utcnow() if self.measured_time is None else self.measured_time
        )

        if measured_time.tzinfo is None:
            # sqlite loses utc, shouldn't happen outside tests
            measured_time = measured_time.replace(tzinfo=timezone.utc)

        return {
            "observation_type": self.observation_type,
            "patient_refused": self.patient_refused,
            "score_value": self.score_value,
            "observation_value": self.observation_value,
            "observation_string": self.observation_string,
            "observation_unit": self.observation_unit,
            "measured_time": measured_time,
            "uuid": self.uuid,
        }

    def on_patch(self) -> None:
        self.modified = datetime.utcnow()
        self.modified_by_ = current_jwt_user()
