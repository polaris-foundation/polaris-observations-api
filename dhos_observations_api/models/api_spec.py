from datetime import datetime
from typing import List, Optional, TypedDict

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_batteries_included.helpers.apispec import (
    FlaskBatteriesPlugin,
    initialise_apispec,
    openapi_schema,
)
from marshmallow import EXCLUDE, Schema, fields

dhos_observations_api_spec: APISpec = APISpec(
    version="1.0.0",
    openapi_version="3.0.3",
    title="DHOS Observations API",
    info={
        "description": "The DHOS Observations API is responsible for storing and retrieving vital sign observations."
    },
    plugins=[FlaskPlugin(), MarshmallowPlugin(), FlaskBatteriesPlugin()],
)

initialise_apispec(dhos_observations_api_spec)


class Identifier(Schema):
    class Meta:
        class Dict(TypedDict, total=False):
            uuid: str
            created: datetime
            created_by: str
            modified: datetime
            modified_by: str

    uuid = fields.String(
        required=True,
        metadata={
            "description": "Universally unique identifier for object",
            "example": "2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
        },
    )
    created = fields.DateTime(
        required=True,
        metadata={
            "description": "When the object was created",
            "example": "2017-09-23T08:29:19.123+00:00",
        },
    )
    created_by = fields.String(
        required=True,
        allow_none=True,
        metadata={
            "description": "UUID of the user that created the object",
            "example": "d26570d8-a2c9-4906-9c6a-ea1a98b8b80f",
        },
    )
    modified = fields.DateTime(
        required=True,
        metadata={
            "description": "When the object was modified",
            "example": "2017-09-23T08:29:19.123+00:00",
        },
    )
    modified_by = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "UUID of the user that modified the object",
            "example": "2a0e26e5-21b6-463a-92e8-06d7290067d0",
        },
    )


@openapi_schema(dhos_observations_api_spec)
class ObservationMetadataRequest(Schema):
    class Meta:
        title = "Observation metadata request"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            mask: Optional[str]
            mask_percent: Optional[int]
            gcs_eyes: int
            gcs_eyes_description: str
            gcs_verbal: int
            gcs_motor: int
            gcs_motor_description: str
            patient_position: str

    mask = fields.String(
        required=False, allow_none=True, metadata={"example": "Venturi"}
    )
    mask_percent = fields.Integer(
        required=False, allow_none=True, metadata={"example": 75}
    )
    gcs_eyes = fields.Integer(required=False, allow_none=True, metadata={"example": 4})
    gcs_eyes_description = fields.String(
        required=False, allow_none=True, metadata={"example": "Spontaneous"}
    )
    gcs_verbal = fields.Integer(
        required=False, allow_none=True, metadata={"example": 2}
    )
    gcs_verbal_description = fields.String(
        required=False, allow_none=True, metadata={"example": "Oriented"}
    )
    gcs_motor = fields.Integer(required=False, allow_none=True, metadata={"example": 5})
    gcs_motor_description = fields.String(
        required=False, allow_none=True, metadata={"example": "Obeys Commands"}
    )
    patient_position = fields.String(
        required=False, allow_none=True, metadata={"example": "Standing"}
    )


@openapi_schema(dhos_observations_api_spec)
class ObservationRequest(Schema):
    class Meta:
        title = "Observation request"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            observation_type: str
            measured_time: datetime
            patient_refused: bool
            score_value: int
            observation_value: float
            observation_string: str
            observation_unit: str
            observation_metadata: ObservationMetadataRequest.Meta.Dict

    observation_type = fields.String(required=True, metadata={"example": "heart_rate"})
    measured_time = fields.AwareDateTime(
        required=True, metadata={"example": "2017-09-23T08:29:19.123+00:00"}
    )
    patient_refused = fields.Boolean(
        required=False, allow_none=True, metadata={"example": False}
    )
    score_value = fields.Integer(
        required=False, allow_none=True, metadata={"example": 4}
    )
    observation_value = fields.Float(
        required=False, allow_none=True, metadata={"example": 58}
    )
    observation_string = fields.String(
        required=False, allow_none=True, metadata={"example": "General concern"}
    )
    observation_unit = fields.String(
        required=False, allow_none=True, metadata={"example": "bpm"}
    )
    observation_metadata = fields.Nested(
        ObservationMetadataRequest, required=False, allow_none=True
    )


class ObservationUpdate(Schema):
    class Meta:
        ordered = True

    observation_type = fields.String(required=True, metadata={"example": "heart_rate"})
    score_value = fields.Integer(required=True, metadata={"example": 4})


@openapi_schema(dhos_observations_api_spec)
class ObservationSetSchema(Schema):
    class Meta:
        title = "Observation set fields common to request and response"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, total=False):
            score_system: str
            score_value: int
            score_string: str
            score_severity: Optional[str]
            record_time: datetime
            spo2_scale: int
            # observations: List[ObservationRequest.Meta.Dict]
            encounter_id: str
            patient_id: str
            is_partial: bool
            empty_set: bool
            ranking: str
            obx_reference_range: str
            obx_abnormal_flags: str
            time_next_obs_set_due: Optional[datetime]
            monitoring_instruction: str
            location: str
            mins_late: int

    score_system = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "news2", "enum": ["news2", "meows"]},
    )
    score_value = fields.Integer(
        required=False, allow_none=True, metadata={"example": 12}
    )
    score_string = fields.String(
        required=False, allow_none=True, metadata={"example": "12C"}
    )
    score_severity = fields.String(
        required=False, allow_none=True, metadata={"example": "high"}
    )
    record_time = fields.AwareDateTime(
        required=True, metadata={"example": "2017-09-23T08:31:19.123+00:00"}
    )
    spo2_scale = fields.Integer(
        required=False, allow_none=True, metadata={"example": 2}
    )

    encounter_id = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "e22f5175-6283-408d-9ba4-ea3b3a5354b8"},
    )
    patient_id = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "f33e5175-2285-508d-0ba4-ea3b3a5354b9"},
    )
    is_partial = fields.Boolean(
        required=False, allow_none=True, metadata={"example": False}
    )
    empty_set = fields.Boolean(
        required=False, allow_none=True, metadata={"example": False}
    )
    ranking = fields.String(
        required=False,
        allow_none=True,
        metadata={"example": "0101010,2017-09-23T08:29:19.123+00:00"},
    )
    obx_reference_range = fields.String(
        required=False, allow_none=True, metadata={"example": "0-4"}
    )
    obx_abnormal_flags = fields.String(
        required=False, allow_none=True, metadata={"example": "HIGH"}
    )
    time_next_obs_set_due = fields.AwareDateTime(
        required=False,
        allow_none=True,
        metadata={"example": "2019-01-23T08:31:19.123+00:00"},
    )
    monitoring_instruction = fields.String(
        required=False, allow_none=True, metadata={"example": "medium_monitoring"}
    )
    location = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "example": "285c1c51-5d72-4066-b1da-49604a3f21b0",
            "description": "UUID of location, (not used by v1 endpoint)",
        },
    )
    mins_late = fields.Integer(
        required=False, allow_none=True, metadata={"example": 12}
    )


@openapi_schema(dhos_observations_api_spec)
class ObservationSetRequest(ObservationSetSchema):
    class Meta:
        title = "Observation set request"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, ObservationSetSchema.Meta.Dict, total=False):
            observations: List[ObservationRequest.Meta.Dict]

    observations = fields.List(fields.Nested(ObservationRequest), required=True)


@openapi_schema(dhos_observations_api_spec)
class ObservationResponse(ObservationRequest):
    class Meta:
        title = "Observation response"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict, ObservationRequest.Meta.Dict, total=False):
            uuid: str

    uuid = fields.String(
        required=True,
        metadata={
            "description": "Universally unique identifier for object",
            "example": "2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
        },
    )


@openapi_schema(dhos_observations_api_spec)
class ObservationSetResponse(ObservationSetSchema, Identifier):
    class Meta:
        title = "Observation set response"
        ordered = True

        class Dict(
            ObservationSetSchema.Meta.Dict, Identifier.Meta.Dict, TypedDict, total=False
        ):
            observations: List[ObservationResponse.Meta.Dict]
            spo2_scale_has_changed: Optional[bool]

    spo2_scale_has_changed = fields.Boolean(
        required=False,
        metadata={
            "example": False,
            "description": "(v1 only) True if spo2_scale passed in POST does not match expected from encounter",
        },
    )
    observations = fields.List(fields.Nested(ObservationResponse), required=True)


@openapi_schema(dhos_observations_api_spec)
class ObservationSetUpdate(Schema):
    class Meta:
        title = "Observation set update"
        unknown = EXCLUDE
        ordered = True

    score_value = fields.Integer(required=True, metadata={"example": 12})
    score_string = fields.String(
        required=False, allow_none=True, metadata={"example": "12C"}
    )
    score_severity = fields.String(
        required=False, allow_none=True, metadata={"example": "high"}
    )
    spo2_scale = fields.Integer(
        required=False, allow_none=True, metadata={"example": 2}
    )
    observations = fields.List(fields.Nested(ObservationUpdate), required=True)
    is_partial = fields.Boolean(required=False, metadata={"example": False})
    empty_set = fields.Boolean(required=False, metadata={"example": False})
    ranking = fields.String(
        required=False, metadata={"example": "0101010,2017-09-23T08:29:19.123+00:00"}
    )
    obx_reference_range = fields.String(
        required=False, allow_none=True, metadata={"example": "0-4"}
    )
    obx_abnormal_flags = fields.String(
        required=False, allow_none=True, metadata={"example": "HIGH"}
    )
    time_next_obs_set_due = fields.AwareDateTime(
        required=False, metadata={"example": "2019-01-23T08:31:19.123+00:00"}
    )
    monitoring_instruction = fields.String(
        required=False, metadata={"example": "medium_monitoring"}
    )


@openapi_schema(dhos_observations_api_spec)
class AggregateUpdateResponse(Schema):
    class Meta:
        title = "Observation aggregate data update"
        unknown = EXCLUDE
        ordered = True

        class Dict(TypedDict):
            time_taken: str

    time_taken = fields.String(required=True, metadata={"example": "20.123 seconds"})


@openapi_schema(dhos_observations_api_spec)
class AggregateOnTimeStats(Schema):
    class Meta:
        title = "Aggregate On Time Observation Sets"
        unknown = EXCLUDE
        ordered = True

    on_time = fields.Integer(
        required=False,
        metadata={
            "example": 9900,
            "description": "Number of observation sets which were taken on time",
        },
    )
    late = fields.Integer(
        required=False,
        metadata={
            "example": 100,
            "description": "Number of observation sets which were taken late",
        },
    )


@openapi_schema(dhos_observations_api_spec)
class AggregateOnTimeStatsWithRisk(AggregateOnTimeStats):
    class Meta:
        title = "Aggregate On Time Observation Sets and by risk"
        unknown = EXCLUDE
        ordered = True

    risk = fields.Dict(keys=fields.String(), values=fields.Nested(AggregateOnTimeStats))


@openapi_schema(dhos_observations_api_spec)
class AggregateOnTimeStatsWithRiskAndDate(AggregateOnTimeStatsWithRisk):
    class Meta:
        title = "Date based aggregate on time observation sets data"
        unknown = EXCLUDE
        ordered = True

    date = fields.Dict(
        keys=fields.String(), values=fields.Nested(AggregateOnTimeStatsWithRisk)
    )


@openapi_schema(dhos_observations_api_spec)
class AggregateOnTimeObservationSets(AggregateOnTimeStats):
    class Meta:
        title = "Location based aggregate on time observation data"
        unknown = EXCLUDE
        ordered = True

    fields.Dict(
        keys=fields.String(), values=fields.Nested(AggregateOnTimeStatsWithRisk)
    )


@openapi_schema(dhos_observations_api_spec)
class AggregateMissingStats(Schema):
    class Meta:
        title = "Aggregate missing observation sets"
        unknown = EXCLUDE
        ordered = True

    total_obs_sets = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets taken",
        },
    )
    num_obs_missing = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets missing observations",
        },
    )
    o2_therapy_status_missing = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets missing o2_therapy_status",
        },
    )
    heart_rate_missing = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets missing heart_rate",
        },
    )
    spo2_missing = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets missing spo2",
        },
    )
    temperature_missing = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets missing temperature",
        },
    )
    diastolic_blood_pressure_missing = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets missing diastolic_blood_pressure",
        },
    )
    respiratory_rate_missing = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets missing respiratory_rate",
        },
    )
    consciousness_acvpu_missing = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets missing consciousness_acvpu",
        },
    )
    systolic_blood_pressure_missing = fields.Integer(
        required=False,
        metadata={
            "example": 10000,
            "description": "Number of observation sets missing systolic_blood_pressure",
        },
    )


@openapi_schema(dhos_observations_api_spec)
class AggregateMissingObservationSets(AggregateMissingStats):
    class Meta:
        title = "Location based aggregate on time observation data"
        unknown = EXCLUDE
        ordered = True

    fields.Dict(keys=fields.String(), values=fields.Nested(AggregateMissingStats))


@openapi_schema(dhos_observations_api_spec)
class AggregateTimeInterval(Schema):
    class Meta:
        title = (
            "Number of observation sets grouped by risk level and 15 minute intervals"
        )
        unknown = EXCLUDE
        ordered = True

    minus60 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken early by 60 minutes and over",
        },
    )
    minus45_59 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken early by 45-59 minutes",
        },
    )
    minus30_44 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken early by 30-44 minutes",
        },
    )
    minus15_29 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken early by 15-29 minutes",
        },
    )
    minus0_14 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken early/on time by 0-14 minutes",
        },
    )
    plus1_15 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 1-15 minutes",
        },
    )
    plus16_30 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 16-30 minutes",
        },
    )
    plus31_45 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 31-45 minutes",
        },
    )
    plus46_60 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 46-60 minutes",
        },
    )
    plus61_75 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 61-75 minutes",
        },
    )
    plus76_90 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 76-90 minutes",
        },
    )
    plus91_105 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 91-105 minutes",
        },
    )
    plus106_120 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 106-120 minutes",
        },
    )
    plus121_135 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 121-135 minutes",
        },
    )
    plus136_150 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 136-150 minutes",
        },
    )
    plus151_165 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 151-165 minutes",
        },
    )
    plus166_180 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 166-180 minutes",
        },
    )
    plus180 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Number of observation sets which were taken late by 180 minutes and over",
        },
    )


@openapi_schema(dhos_observations_api_spec)
class AggregateObservationsByInterval(AggregateTimeInterval):
    class Meta:
        title = "Location based aggregate on time observation data"
        unknown = EXCLUDE
        ordered = True

    fields.Dict(
        keys=fields.String(),
        values=fields.Dict(
            keys=fields.String(), values=fields.Nested(AggregateTimeInterval)
        ),
    )


@openapi_schema(dhos_observations_api_spec)
class AggregateMonthlyObs(Schema):
    class Meta:
        title = "Number of observation sets grouped by month"
        unknown = EXCLUDE
        ordered = True

    all_obs_sets = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "All observations sets taken during the month",
        },
    )

    on_time = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "All on time observations sets taken during the month",
        },
    )

    low = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Low severity observations sets taken during the month",
        },
    )

    low_medium = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Low medium severity observations sets taken during the month",
        },
    )

    medium = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Medium severity observations sets taken during the month",
        },
    )

    high = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "High severity observations sets taken during the month",
        },
    )

    missing_obs = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets with missing observations taken during the month",
        },
    )

    o2_therapy_status = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets missing o2 therapy status observations taken during the month",
        },
    )

    heart_rate = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets missing heart rate observations taken during the month",
        },
    )

    spo2 = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets missing spo2 observations taken during the month",
        },
    )

    temperature = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets missing temperature observations taken during the month",
        },
    )

    diastolic_blood_pressure = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets missing diastolic blood pressure observations taken during the month",
        },
    )

    respiratory_rate = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets missing respiratory rate observations taken during the month",
        },
    )

    consciousness_acvpu = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets missing ACVPU observations taken during the month",
        },
    )

    systolic_blood_pressure = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets missing systolic blood pressure observations taken during the month",
        },
    )

    nurse_concern = fields.Integer(
        required=False,
        metadata={
            "example": 1324,
            "description": "Observations sets missing nurse concern observations taken during the month",
        },
    )


@openapi_schema(dhos_observations_api_spec)
class AggregateObservationSetsByMonth(Schema):
    class Meta:
        title = "Monthly aggregate observation data"
        unknown = EXCLUDE
        ordered = True

    fields.Dict(
        keys=fields.String(),
        values=fields.Dict(
            keys=fields.String(), values=fields.Nested(AggregateMonthlyObs)
        ),
    )


@openapi_schema(dhos_observations_api_spec)
class AggregateObservationSetsByLocationMonth(Schema):
    class Meta:
        title = "Monthly aggregate observation data"
        unknown = EXCLUDE
        ordered = True

    fields.Dict(
        keys=fields.String(),
        values=fields.Dict(
            keys=fields.String(), values=fields.Nested(AggregateObservationSetsByMonth)
        ),
    )
