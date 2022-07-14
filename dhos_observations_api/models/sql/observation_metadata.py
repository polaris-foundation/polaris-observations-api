from typing import Dict, Optional

from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.sqldb import ModelIdentifier, db


class ObservationMetaData(ModelIdentifier, db.Model):
    uuid = db.Column(
        db.String(length=36),
        unique=True,
        nullable=False,
        primary_key=True,
    )
    observation_uuid = db.Column(db.String, db.ForeignKey("observation.uuid"))
    mask = db.Column(db.String().evaluates_none(), nullable=True)
    mask_percent = db.Column(db.Integer().evaluates_none(), nullable=True)
    gcs_eyes = db.Column(db.Integer().evaluates_none(), nullable=True)
    gcs_eyes_description = db.Column(db.String().evaluates_none(), nullable=True)
    gcs_verbal = db.Column(db.Integer().evaluates_none(), nullable=True)
    gcs_verbal_description = db.Column(db.String().evaluates_none(), nullable=True)
    gcs_motor = db.Column(db.Integer().evaluates_none(), nullable=True)
    gcs_motor_description = db.Column(db.String().evaluates_none(), nullable=True)
    patient_position = db.Column(db.String().evaluates_none(), nullable=True)

    @classmethod
    def new(
        cls,
        observation_uuid: str,
        uuid: Optional[str] = None,
        mask: str = None,
        mask_percent: int = None,
        gcs_eyes: int = None,
        gcs_eyes_description: str = None,
        gcs_verbal: int = None,
        gcs_verbal_description: str = None,
        gcs_motor: int = None,
        gcs_motor_description: str = None,
        patient_position: str = None,
    ) -> "ObservationMetaData":
        if not uuid:
            uuid = generate_uuid()
        return ObservationMetaData(
            observation_uuid=observation_uuid,
            uuid=uuid,
            mask=mask,
            mask_percent=mask_percent,
            gcs_eyes=gcs_eyes,
            gcs_eyes_description=gcs_eyes_description,
            gcs_verbal=gcs_verbal,
            gcs_verbal_description=gcs_verbal_description,
            gcs_motor=gcs_motor,
            gcs_motor_description=gcs_motor_description,
            patient_position=patient_position,
        )

    def to_dict(self) -> Dict:
        return {
            "mask": self.mask,
            "mask_percent": self.mask_percent,
            "gcs_eyes": self.gcs_eyes,
            "gcs_eyes_description": self.gcs_eyes_description,
            "gcs_verbal": self.gcs_verbal,
            "gcs_verbal_description": self.gcs_verbal_description,
            "gcs_motor": self.gcs_motor,
            "gcs_motor_description": self.gcs_motor_description,
            "patient_position": self.patient_position,
            "uuid": self.uuid,
        }

    def to_map_dict(self) -> Dict:
        return {
            "mask": self.mask,
            "mask_percent": self.mask_percent,
            "gcs_eyes": self.gcs_eyes,
            "gcs_eyes_description": self.gcs_eyes_description,
            "gcs_verbal": self.gcs_verbal,
            "gcs_verbal_description": self.gcs_verbal_description,
            "gcs_motor": self.gcs_motor,
            "gcs_motor_description": self.gcs_motor_description,
            "patient_position": self.patient_position,
            "uuid": self.uuid,
            "observation_uuid": self.observation_uuid,
        }
