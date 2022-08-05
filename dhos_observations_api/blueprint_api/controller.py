import time
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

import dateutil.parser as dp
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import (
    EntityNotFoundException,
    UnprocessibleEntityException,
)
from flask_batteries_included.helpers.security.jwt import current_jwt_user
from flask_batteries_included.sqldb import db
from she_logging import logger
from sqlalchemy import Integer, and_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import select, text

from dhos_observations_api.blueprint_api import message
from dhos_observations_api.models.api_spec import (
    AggregateUpdateResponse,
    ObservationSetRequest,
    ObservationSetResponse,
)
from dhos_observations_api.models.sql.agg_observation_sets import AggObservationSets
from dhos_observations_api.models.sql.observation import Observation
from dhos_observations_api.models.sql.observation_set import ObservationSet

AGG_DEFAULT: Dict = {
    "all_obs_sets": 0,
    "on_time": 0,
    "low": 0,
    "low_medium": 0,
    "medium": 0,
    "high": 0,
    "missing_obs": 0,
    "o2_therapy_status": 0,
    "heart_rate": 0,
    "spo2": 0,
    "temperature": 0,
    "diastolic_blood_pressure": 0,
    "respiratory_rate": 0,
    "consciousness_acvpu": 0,
    "systolic_blood_pressure": 0,
    "nurse_concern": 0,
}


def create_observation_set(
    obs_set: ObservationSetRequest.Meta.Dict,
    suppress_obs_publish: bool,
    referring_device_id: Optional[str] = None,  # used only for auditing
) -> ObservationSetResponse.Meta.Dict:
    if not obs_set["observations"]:
        raise ValueError("Observations should not be empty")

    encounter_id: Optional[str] = obs_set.get("encounter_id")
    patient_id: Optional[str] = obs_set.get("patient_id")
    if not encounter_id and not patient_id:
        raise ValueError(
            "An encounter_id or patient_id is required to create an observation set"
        )

    uuid: str = generate_uuid()

    ObservationSet.new(uuid=uuid, **obs_set)
    db.session.commit()

    if encounter_id:
        update_mins_late_for_encounter(encounter_id=encounter_id)

    audit_message: Dict = {
        "event_type": "create observation set",
        "event_data": {
            "device_id": referring_device_id,
            "clinician_id": current_jwt_user(),
            "encounter_id": encounter_id,
            "patient_id": patient_id,
            "obs_set_id": uuid,
        },
    }
    message.publish_audit_message(audit_message=audit_message)

    observation_set = get_observation_set_by_id(uuid)

    # Publish the new obs set for other microservices.
    if not suppress_obs_publish:
        logger.debug("Publishing scored obs message")
        message.publish_scored_obs_message(observation_set)
        logger.debug("Publishing encounter update message")
        message.publish_encounter_update_message(observation_set)

    return observation_set


def update_mins_late_for_encounter(encounter_id: str) -> None:
    """
    Query finds all observation sets for a given encounter
    it orders them by record_time it then gives each row an incrementing row number
    it then joins a copy of this row matching the current row number with the
    row number + 1 so that the previous row and the current row are joined on
    the same row. This allows the current row's record_time to be subtracted
    from the previous row's time_next_obs_set_due to provide the number of minutes
    an observation set it late. Each rows late value is then used to update its
    mins_late field. If it is the first entry in an encounter it is assumed to be
    on time and mins_late is set to 0.
    """
    sql = """
        UPDATE observation_set 
        SET mins_late = ex.curr_obs_mins_late
        FROM 
        (
            SELECT 
                a.uuid,
                CASE
                    WHEN p_obs.time_next_obs_set_due is null THEN 0
                    ELSE
                        ROUND((EXTRACT(hour FROM (a.record_time - p_obs.time_next_obs_set_due ))*60*60
                        + EXTRACT(minutes FROM (a.record_time - p_obs.time_next_obs_set_due))*60
                        + EXTRACT(seconds FROM (a.record_time - p_obs.time_next_obs_set_due)))/60)
                END AS curr_obs_mins_late
            FROM
                (
                    SELECT ROW_NUMBER() OVER (ORDER BY encounter_id, record_time) rn, 
                    o.uuid, o.time_next_obs_set_due, o.record_time, o.encounter_id
                    FROM observation_set o
                    WHERE o.encounter_id = :encounter_id
                ) a
            LEFT JOIN 
                (select ROW_NUMBER() OVER (ORDER BY encounter_id, record_time) rn,
                o.uuid, o.time_next_obs_set_due, o.record_time, o.encounter_id
                FROM observation_set o
                WHERE o.encounter_id = :encounter_id
                ) p_obs
            on a.rn = p_obs.rn + 1
        ) ex 
        WHERE observation_set.uuid = ex.uuid
        AND observation_set.encounter_id = :encounter_id
    """
    db.engine.execute(text(sql), {"encounter_id": encounter_id})


def update_observation_set(observation_set_uuid: str, updated_obs_set: Dict) -> Dict:
    with db.session.begin(subtransactions=True):
        observation_set = (
            ObservationSet.query.options(joinedload(ObservationSet.observations))
            .filter(ObservationSet.uuid == observation_set_uuid)
            .first()
        )

        if not observation_set:
            raise EntityNotFoundException(
                f"Observation set with uuid '{observation_set_uuid}' does not exist"
            )

        observations: Dict[str, Observation] = {
            o.observation_type: o for o in observation_set.observations
        }

        obs = updated_obs_set.pop("observations", [])

        # Ensure modified (by) is updated.
        observation_set.on_patch()

        for k, v in updated_obs_set.items():
            if hasattr(observation_set, k):
                setattr(observation_set, k, v)

        for observation_dict in obs:

            observation_name = observation_dict.get("observation_type", None)
            score_value = observation_dict.get("score_value", None)

            if None in (observation_name, score_value):
                raise ValueError(
                    "Observation object must contain both 'observation_type' and 'score_value'"
                )

            observation: Optional[Observation] = observations.get(observation_name)
            if not observation:
                raise EntityNotFoundException(
                    f"Observation of type '{observation_name}' not found in set"
                )

            # Ensure modified (by) is updated.
            observation.on_patch()
            observation.score_value = score_value

    result = observation_set.to_dict()
    db.session.commit()
    return result


def get_observation_set_by_id(
    observation_set_uuid: str, compact: bool = False
) -> ObservationSetResponse.Meta.Dict:
    observation_set: ObservationSet = (
        ObservationSet.query.options(joinedload(ObservationSet.observations))
        .filter(ObservationSet.uuid == observation_set_uuid)
        .first()
    )

    if observation_set is None:
        raise EntityNotFoundException(
            f"Observation set {observation_set_uuid} not found"
        )

    return observation_set.to_dict(compact=compact)


def get_observation_sets_by_locations_and_date_range(
    location_uuids: List[str],
    start_date_str: str,
    end_date_str: str,
    limit: int = None,
    compact: bool = False,
) -> List[ObservationSetResponse.Meta.Dict]:

    # Check dates are formatted correctly
    today = date.today()

    start_date = dp.parse(
        start_date_str,
        default=datetime(today.year, today.month, today.day, tzinfo=timezone.utc),
    )
    # End date is inclusive so defaults if the time is omitted need to be at the end of the day.
    end_date = dp.parse(
        end_date_str,
        default=datetime(
            today.year, today.month, today.day, 23, 59, 59, 999_999, tzinfo=timezone.utc
        ),
    )

    if start_date > end_date:
        logger.debug(
            "The start date: '%s' is before: '%s'",
            end_date.isoformat(),
            start_date.isoformat(),
        )
        raise UnprocessibleEntityException("End date is before Start date")

    # When compact it will just return their uuids
    if compact:
        query = (
            db.session.query(ObservationSet)
            .filter(
                and_(
                    ObservationSet.location.in_(location_uuids),
                    start_date < ObservationSet.record_time,
                    ObservationSet.record_time <= end_date,
                )
            )
            .order_by(ObservationSet.record_time.desc())
            .limit(limit)
        )
        return [{"uuid": o.uuid} for o in query]

    query = (
        db.session.query(ObservationSet)
        .options(joinedload(ObservationSet.observations))
        .filter(
            and_(
                ObservationSet.location.in_(location_uuids),
                start_date < ObservationSet.record_time,
                ObservationSet.record_time <= end_date,
            )
        )
        .order_by(ObservationSet.record_time.desc())
        .limit(limit)
    )

    return [obs_set.to_dict(compact=True) for obs_set in query]


def query_observation_sets_for_encounters(
    encounter_ids: List[str], limit: int = None
) -> Query:
    query: Query = (
        db.session.query(ObservationSet)
        .filter(ObservationSet.encounter_id.in_(encounter_ids))
        .options(joinedload(ObservationSet.observations))
        .order_by(ObservationSet.record_time.desc())
        .limit(limit)
    )

    return query


def get_observation_sets_for_encounters(
    encounter_ids: List[str], limit: int = None, compact: bool = False
) -> List[ObservationSetResponse.Meta.Dict]:
    query: Query = query_observation_sets_for_encounters(encounter_ids, limit=limit)
    return [obs_set.to_dict(compact=compact) for obs_set in query]


def get_latest_observation_set_for_encounters(
    encounter_ids: List[str], compact: bool = False
) -> ObservationSetResponse.Meta.Dict:
    obs_set_query: Query = query_observation_sets_for_encounters(
        encounter_ids=encounter_ids, limit=1
    )

    latest_observation_set: Optional[ObservationSet] = obs_set_query.first()

    if latest_observation_set is None:
        raise EntityNotFoundException(
            f"Encounter {', '.join(encounter_ids)} has no observation sets"
        )

    # The obs sets are already sorted by record_time descending, so just return the first.
    return latest_observation_set.to_dict(compact=compact)


def get_latest_observation_sets_by_encounter_ids(
    encounter_ids: List[str], compact: bool = False
) -> Dict[str, Dict]:

    subq = (
        db.session.query(
            ObservationSet.encounter_id,
            func.max(ObservationSet.record_time).label("maxdate"),
        )
        .group_by(ObservationSet.encounter_id)
        .filter(ObservationSet.encounter_id.in_(encounter_ids))
        .subquery("t2")
    )

    query = (
        db.session.query(ObservationSet)
        .options(joinedload(ObservationSet.observations))
        .join(
            subq,
            and_(
                ObservationSet.encounter_id == subq.c.encounter_id,
                ObservationSet.record_time == subq.c.maxdate,
            ),
        )
        .filter(ObservationSet.encounter_id.in_(encounter_ids))
    )

    return {obs_set.encounter_id: obs_set.to_dict(compact=compact) for obs_set in query}


def get_observation_sets_for_patient(
    patient_id: str, limit: Optional[int] = None
) -> List[ObservationSetResponse.Meta.Dict]:

    query: Query = (
        db.session.query(ObservationSet)
        .options(joinedload(ObservationSet.observations))
        .filter(ObservationSet.patient_id == patient_id)
        .order_by(ObservationSet.record_time.desc())
        .limit(limit)
    )

    return [obs_set.to_dict() for obs_set in query]


def retrieve_observation_count_for_encounter_ids(encounter_uuids: List[str]) -> Dict:
    logger.debug(
        "Getting obs set counts for %d encounters",
        len(encounter_uuids),
        extra={"encounter_uuids": encounter_uuids},
    )

    results: List[Tuple[str, int]] = (
        ObservationSet.query.with_entities(
            ObservationSet.encounter_id, func.count(ObservationSet.encounter_id)
        )
        .filter(ObservationSet.encounter_id.in_(encounter_uuids))
        .group_by(ObservationSet.encounter_id)
    )

    counts = dict.fromkeys(encounter_uuids, 0)
    counts.update(
        {encounter_uuid: obs_set_count for encounter_uuid, obs_set_count in results}
    )
    return counts


def get_observation_sets(
    modified_since: str, compact: bool
) -> List[ObservationSetResponse.Meta.Dict]:

    query: Query = (
        db.session.query(ObservationSet)
        .options(joinedload(ObservationSet.observations))
        .filter(ObservationSet.modified > modified_since)
        .order_by(ObservationSet.modified.desc())
    )

    return [obs_set.to_dict(compact=compact) for obs_set in query]


def refresh_agg_observation_sets() -> AggregateUpdateResponse.Meta.Dict:
    start = time.time()
    sql = "REFRESH MATERIALIZED VIEW agg_observation_sets;"
    db.engine.execute(text(sql))
    end = time.time()

    return {"time_taken": f"{end-start:.3f} seconds"}


def on_time_observation_sets(
    start_date: str, end_date: str, location_uuids: List[str]
) -> Dict:
    stmt = (
        select(
            AggObservationSets.location_id,
            AggObservationSets.record_day,
            AggObservationSets.score_severity,
            AggObservationSets.on_time,
            AggObservationSets.late_obs_sets,
        )
        .where(
            and_(
                AggObservationSets.location_id.in_(location_uuids),
                AggObservationSets.record_day.between(start_date, end_date),
            )
        )
        .order_by("location_id", "record_day", "score_severity")
    )
    results = db.engine.execute(stmt)

    default: Dict = {"on_time": 0, "late": 0}
    stats: Dict = defaultdict(
        lambda: {
            **default,
            "date": defaultdict(
                lambda: {
                    **default,
                    "risk": defaultdict(lambda: {**default}),
                }
            ),
            "risk": defaultdict(lambda: {**default}),
        }
    )
    stats["on_time"] = 0
    stats["late"] = 0
    stats["risk"] = defaultdict(lambda: {**default})

    for location_id, record_day, score_severity, on_time, late in results:
        # update main totals
        stats["on_time"] += on_time
        stats["late"] += late

        stats["risk"][score_severity]["on_time"] += on_time
        stats["risk"][score_severity]["late"] += late

        # Update totals for location
        stats[location_id]["on_time"] += on_time
        stats[location_id]["late"] += late

        # Update risk for location
        stats[location_id]["risk"][score_severity]["on_time"] += on_time
        stats[location_id]["risk"][score_severity]["late"] += late

        # Update date for location
        stats[location_id]["date"][record_day]["on_time"] += on_time
        stats[location_id]["date"][record_day]["late"] += late

        # Add risk for date
        stats[location_id]["date"][record_day]["risk"][score_severity] = {
            "on_time": on_time,
            "late": late,
        }

    return stats


def missing_observation_sets(
    start_date: str, end_date: str, location_uuids: List[str]
) -> Dict:
    stmt = (
        select(
            AggObservationSets.location_id,
            func.cast(func.sum(AggObservationSets.all_obs_sets), Integer),
            func.cast(func.sum(AggObservationSets.missing_obs), Integer),
            func.cast(func.sum(AggObservationSets.o2_therapy_status), Integer),
            func.cast(func.sum(AggObservationSets.heart_rate), Integer),
            func.cast(func.sum(AggObservationSets.spo2), Integer),
            func.cast(func.sum(AggObservationSets.temperature), Integer),
            func.cast(func.sum(AggObservationSets.diastolic_blood_pressure), Integer),
            func.cast(func.sum(AggObservationSets.respiratory_rate), Integer),
            func.cast(func.sum(AggObservationSets.consciousness_acvpu), Integer),
            func.cast(func.sum(AggObservationSets.systolic_blood_pressure), Integer),
        )
        .where(
            and_(
                AggObservationSets.location_id.in_(location_uuids),
                AggObservationSets.record_day.between(start_date, end_date),
            )
        )
        .group_by(AggObservationSets.location_id)
    )
    results = db.engine.execute(stmt)

    stats: Dict = defaultdict(int)

    for (
        location_id,
        all_obs_sets,
        missing_obs,
        o2_therapy_status,
        heart_rate,
        spo2,
        temperature,
        diastolic_blood_pressure,
        respiratory_rate,
        consciousness_acvpu,
        systolic_blood_pressure,
    ) in results:
        stats["total_obs_sets"] += all_obs_sets
        stats["num_obs_missing"] += missing_obs
        stats["o2_therapy_status_missing"] += all_obs_sets - o2_therapy_status
        stats["heart_rate_missing"] += all_obs_sets - heart_rate
        stats["spo2_missing"] += all_obs_sets - spo2
        stats["temperature_missing"] += all_obs_sets - temperature
        stats["diastolic_blood_pressure_missing"] += (
            all_obs_sets - diastolic_blood_pressure
        )
        stats["respiratory_rate_missing"] += all_obs_sets - respiratory_rate
        stats["consciousness_acvpu_missing"] += all_obs_sets - consciousness_acvpu
        stats["systolic_blood_pressure_missing"] += (
            all_obs_sets - systolic_blood_pressure
        )
        stats[location_id] = {
            "total_obs_sets": all_obs_sets,
            "num_obs_missing": missing_obs,
            "o2_therapy_status_missing": all_obs_sets - o2_therapy_status,
            "heart_rate_missing": all_obs_sets - heart_rate,
            "spo2_missing": all_obs_sets - spo2,
            "temperature_missing": all_obs_sets - temperature,
            "diastolic_blood_pressure_missing": all_obs_sets - diastolic_blood_pressure,
            "respiratory_rate_missing": all_obs_sets - respiratory_rate,
            "consciousness_acvpu_missing": all_obs_sets - consciousness_acvpu,
            "systolic_blood_pressure_missing": all_obs_sets - systolic_blood_pressure,
        }

    return stats


def observation_sets_time_intervals(
    start_date: str, end_date: str, location_uuids: List[str]
) -> Dict:
    """
    Gather the number of observations sets that are recorded within a specific
    interval relative to when they are expected to be recorded. This data is
    used to show how early or how late observations are relative to when the
    scoring system they are on says they should be recorded. minus30_44
    represents observation sets that were taken from 30 minutes to 44 minutes
    and 59.999 seconds before they were due to be taken. plus180 is where
    observation sets are overdue by 3 hours or more.

    The data is then returned grouped by location and severity as well as totalled
    by severity.
    """

    sql: str = """
        SELECT
            location_id,
            score_severity,
            SUM(minus60),
            SUM(minus45_59),
            SUM(minus30_44),
            SUM(minus15_29),
            SUM(minus0_14),
            SUM(plus1_15),
            SUM(plus16_30),
            SUM(plus31_45),
            SUM(plus46_60),
            SUM(plus61_75),
            SUM(plus76_90),
            SUM(plus91_105),
            SUM(plus106_120),
            SUM(plus121_135),
            SUM(plus136_150),
            SUM(plus151_165),
            SUM(plus166_180),
            SUM(plus180)
        FROM agg_observation_sets
        WHERE record_day BETWEEN :start_date AND :end_date
            AND location_id in :location_uuids
        GROUP BY location_id, score_severity
        ORDER BY location_id, score_severity
    """
    agg_data = db.engine.execute(
        text(sql),
        {
            "start_date": start_date,
            "end_date": end_date,
            "location_uuids": tuple(location_uuids),
        },
    )

    default: Dict = {
        "minus60": 0,
        "minus45_59": 0,
        "minus30_44": 0,
        "minus15_29": 0,
        "minus0_14": 0,
        "plus1_15": 0,
        "plus16_30": 0,
        "plus31_45": 0,
        "plus46_60": 0,
        "plus61_75": 0,
        "plus76_90": 0,
        "plus91_105": 0,
        "plus106_120": 0,
        "plus121_135": 0,
        "plus136_150": 0,
        "plus151_165": 0,
        "plus166_180": 0,
        "plus180": 0,
    }

    data: Dict = defaultdict(
        lambda: {
            "risk": defaultdict(lambda: {**default}),
        }
    )
    data["risk"] = defaultdict(lambda: {**default})

    for (
        location_id,
        score_severity,
        minus60,
        minus45_59,
        minus30_44,
        minus15_29,
        minus0_14,
        plus1_15,
        plus16_30,
        plus31_45,
        plus46_60,
        plus61_75,
        plus76_90,
        plus91_105,
        plus106_120,
        plus121_135,
        plus136_150,
        plus151_165,
        plus166_180,
        plus180,
    ) in agg_data:
        data["risk"][score_severity]["minus60"] += int(minus60)
        data["risk"][score_severity]["minus45_59"] += int(minus45_59)
        data["risk"][score_severity]["minus30_44"] += int(minus30_44)
        data["risk"][score_severity]["minus15_29"] += int(minus15_29)
        data["risk"][score_severity]["minus0_14"] += int(minus0_14)
        data["risk"][score_severity]["plus1_15"] += int(plus1_15)
        data["risk"][score_severity]["plus16_30"] += int(plus16_30)
        data["risk"][score_severity]["plus31_45"] += int(plus31_45)
        data["risk"][score_severity]["plus46_60"] += int(plus46_60)
        data["risk"][score_severity]["plus61_75"] += int(plus61_75)
        data["risk"][score_severity]["plus76_90"] += int(plus76_90)
        data["risk"][score_severity]["plus91_105"] += int(plus91_105)
        data["risk"][score_severity]["plus106_120"] += int(plus106_120)
        data["risk"][score_severity]["plus121_135"] += int(plus121_135)
        data["risk"][score_severity]["plus136_150"] += int(plus136_150)
        data["risk"][score_severity]["plus151_165"] += int(plus151_165)
        data["risk"][score_severity]["plus166_180"] += int(plus166_180)
        data["risk"][score_severity]["plus180"] += int(plus180)

        data[location_id]["risk"][score_severity] = {
            "minus60": int(minus60),
            "minus45_59": int(minus45_59),
            "minus30_44": int(minus30_44),
            "minus15_29": int(minus15_29),
            "minus0_14": int(minus0_14),
            "plus1_15": int(plus1_15),
            "plus16_30": int(plus16_30),
            "plus31_45": int(plus31_45),
            "plus46_60": int(plus46_60),
            "plus61_75": int(plus61_75),
            "plus76_90": int(plus76_90),
            "plus91_105": int(plus91_105),
            "plus106_120": int(plus106_120),
            "plus121_135": int(plus121_135),
            "plus136_150": int(plus136_150),
            "plus151_165": int(plus151_165),
            "plus166_180": int(plus166_180),
            "plus180": int(plus180),
        }

    return data


def agg_observation_sets_by_month(
    start_date: str, end_date: str, location_uuids: List[str]
) -> Dict:
    sql: str = _build_agg_obs_by_month_query(location_uuids)

    agg_data = db.engine.execute(
        text(sql),
        {
            "start_date": start_date,
            "end_date": end_date,
            "location_uuids": tuple(location_uuids),
        },
    )

    data: Dict = defaultdict(lambda: {**AGG_DEFAULT})

    for (
        year_month,
        score_severity,
        all_obs_sets,
        on_time,
        missing_obs,
        o2_therapy_status,
        heart_rate,
        spo2,
        temperature,
        diastolic_blood_pressure,
        respiratory_rate,
        consciousness_acvpu,
        systolic_blood_pressure,
        nurse_concern,
    ) in agg_data:
        score_severity = (
            "low_medium" if score_severity == "low-medium" else score_severity
        )
        data[year_month]["all_obs_sets"] += int(all_obs_sets)
        data[year_month]["on_time"] += int(on_time)
        data[year_month][score_severity] += int(all_obs_sets)
        data[year_month]["missing_obs"] += int(missing_obs)
        data[year_month]["o2_therapy_status"] += int(all_obs_sets - o2_therapy_status)
        data[year_month]["heart_rate"] += int(all_obs_sets - heart_rate)
        data[year_month]["spo2"] += int(all_obs_sets - spo2)
        data[year_month]["temperature"] += int(all_obs_sets - temperature)
        data[year_month]["diastolic_blood_pressure"] += int(
            all_obs_sets - diastolic_blood_pressure
        )
        data[year_month]["respiratory_rate"] += int(all_obs_sets - respiratory_rate)
        data[year_month]["consciousness_acvpu"] += int(
            all_obs_sets - consciousness_acvpu
        )
        data[year_month]["systolic_blood_pressure"] += int(
            all_obs_sets - systolic_blood_pressure
        )
        data[year_month]["nurse_concern"] += int(all_obs_sets - nurse_concern)

    return data


def _build_agg_obs_by_month_query(location_uuids: Optional[List[str]] = None) -> str:
    initial_select = "" if location_uuids else "location_id, "
    where_clause = "AND location_id in :location_uuids" if location_uuids else ""

    return f"""
        SELECT {initial_select}
		    SUBSTRING(RECORD_DAY,1,7) year_month,
			SCORE_SEVERITY score_severity,
            SUM(ALL_OBS_SETS) all_obs_sets,
            SUM(ALL_OBS_SETS - LATE_OBS_SETS) on_time,
            SUM(MISSING_OBS) missing_obs,
            SUM(o2_therapy_status) o2_therapy_status,
            SUM(heart_rate) heart_rate,
            SUM(spo2) spo2,
            SUM(temperature) temperature,
            SUM(diastolic_blood_pressure) diastolic_blood_pressure,
            SUM(respiratory_rate) respiratory_rate,
            SUM(consciousness_acvpu) consciousness_acvpu,
            SUM(systolic_blood_pressure) systolic_blood_pressure,
            SUM(nurse_concern) nurse_concern
        FROM agg_observation_sets
        WHERE record_day BETWEEN :start_date AND :end_date
        {where_clause}
        GROUP BY location_id, SUBSTRING(RECORD_DAY,1,7), SCORE_SEVERITY
        ORDER BY location_id, SUBSTRING(RECORD_DAY,1,7), SCORE_SEVERITY
    """


def all_agg_obs_by_location_by_month(start_date: str, end_date: str) -> Dict:
    sql: str = _build_agg_obs_by_month_query()
    agg_data = db.engine.execute(
        text(sql),
        {"start_date": start_date, "end_date": end_date},
    )

    data: Dict = defaultdict(lambda: defaultdict(lambda: {**AGG_DEFAULT}))

    for (
        location_id,
        year_month,
        score_severity,
        all_obs_sets,
        on_time,
        missing_obs,
        o2_therapy_status,
        heart_rate,
        spo2,
        temperature,
        diastolic_blood_pressure,
        respiratory_rate,
        consciousness_acvpu,
        systolic_blood_pressure,
        nurse_concern,
    ) in agg_data:
        score_severity = (
            "low_medium" if score_severity == "low-medium" else score_severity
        )
        data[location_id][year_month]["all_obs_sets"] += int(all_obs_sets)
        data[location_id][year_month]["on_time"] += int(on_time)
        data[location_id][year_month][score_severity] += int(all_obs_sets)
        data[location_id][year_month]["missing_obs"] += int(missing_obs)
        data[location_id][year_month]["o2_therapy_status"] += int(
            all_obs_sets - o2_therapy_status
        )
        data[location_id][year_month]["heart_rate"] += int(all_obs_sets - heart_rate)
        data[location_id][year_month]["spo2"] += int(all_obs_sets - spo2)
        data[location_id][year_month]["temperature"] += int(all_obs_sets - temperature)
        data[location_id][year_month]["diastolic_blood_pressure"] += int(
            all_obs_sets - diastolic_blood_pressure
        )
        data[location_id][year_month]["respiratory_rate"] += int(
            all_obs_sets - respiratory_rate
        )
        data[location_id][year_month]["consciousness_acvpu"] += int(
            all_obs_sets - consciousness_acvpu
        )
        data[location_id][year_month]["systolic_blood_pressure"] += int(
            all_obs_sets - systolic_blood_pressure
        )
        data[location_id][year_month]["nurse_concern"] += int(
            all_obs_sets - nurse_concern
        )

    return data
