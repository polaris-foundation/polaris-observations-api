"""agg_obs

Revision ID: d4de063df517
Revises: 99661944c32f
Create Date: 2021-04-08 10:29:43.366564

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4de063df517"
down_revision = "99661944c32f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "observation_type_idx", "observation", ["observation_type"], unique=False
    )
    conn = op.get_bind()
    # Create aggregate view of the observations data
    conn.execute(
        """
        CREATE MATERIALIZED VIEW agg_observation_sets AS
        SELECT 
            to_char( os.record_time, 'YYYY-MM-DD') as record_day
            , os.location location_id
            , os.score_severity
            , count(distinct os.uuid) all_obs_sets
            , count(distinct os_late.uuid) late_obs_sets
            , count(distinct o2_therapy_status.uuid) o2_therapy_status
            , count(distinct heart_rate.uuid) heart_rate
            , count(distinct spo2.uuid) spo2
            , count(distinct temperature.uuid) temperature
            , count(distinct diastolic_blood_pressure.uuid) diastolic_blood_pressure
            , count(distinct respiratory_rate.uuid) respiratory_rate
            , count(distinct consciousness_acvpu.uuid) consciousness_acvpu
            , count(distinct systolic_blood_pressure.uuid) systolic_blood_pressure
            , count(distinct nurse_concern.uuid) nurse_concern
            , count(case when os.mins_late <= -60 then 1 else null end) minus60
            , count(case when os.mins_late > -60 and os.mins_late <= -45 then 1 else null end) minus45_59
            , count(case when os.mins_late > -45 and os.mins_late <= -30 then 1 else null end) minus30_44
            , count(case when os.mins_late > -30 and os.mins_late <= -15 then 1 else null end) minus15_29
            , count(case when os.mins_late > -15 and os.mins_late <= 0 then 1 else null end) minus0_14
            , count(case when os.mins_late > 0 and os.mins_late <= 15 then 1 else null end) plus1_15
            , count(case when os.mins_late > 15 and os.mins_late <= 30 then 1 else null end) plus16_30
            , count(case when os.mins_late > 30 and os.mins_late <= 45 then 1 else null end) plus31_45
            , count(case when os.mins_late > 45 and os.mins_late <= 60 then 1 else null end) plus46_60
            , count(case when os.mins_late > 60 and os.mins_late <= 75 then 1 else null end) plus61_75
            , count(case when os.mins_late > 75 and os.mins_late <= 90 then 1 else null end) plus76_90
            , count(case when os.mins_late > 90 and os.mins_late <= 105 then 1 else null end) plus91_105
            , count(case when os.mins_late > 105 and os.mins_late <= 120 then 1 else null end) plus106_120
            , count(case when os.mins_late > 120 and os.mins_late <= 135 then 1 else null end) plus121_135
            , count(case when os.mins_late > 135 and os.mins_late <= 150 then 1 else null end) plus136_150
            , count(case when os.mins_late > 150 and os.mins_late <= 165 then 1 else null end) plus151_165
            , count(case when os.mins_late > 165 and os.mins_late <= 180 then 1 else null end) plus166_180
            , count(case when os.mins_late > 180 then 1 else null end) plus180
        FROM observation_set os
        LEFT JOIN observation_set os_late on os.uuid = os_late.uuid and os_late.mins_late > 0
        LEFT JOIN observation o2_therapy_status on os.uuid = o2_therapy_status.observation_set_uuid and o2_therapy_status.observation_type = 'o2_therapy_status'
        LEFT JOIN observation heart_rate on os.uuid = heart_rate.observation_set_uuid and heart_rate.observation_type = 'heart_rate'
        LEFT JOIN observation spo2 on os.uuid = spo2.observation_set_uuid and spo2.observation_type = 'spo2'
        LEFT JOIN observation temperature on os.uuid = temperature.observation_set_uuid and temperature.observation_type = 'temperature'
        LEFT JOIN observation diastolic_blood_pressure on os.uuid = diastolic_blood_pressure.observation_set_uuid and diastolic_blood_pressure.observation_type = 'diastolic_blood_pressure'
        LEFT JOIN observation respiratory_rate on os.uuid = respiratory_rate.observation_set_uuid and respiratory_rate.observation_type = 'respiratory_rate'
        LEFT JOIN observation consciousness_acvpu on os.uuid = consciousness_acvpu.observation_set_uuid and consciousness_acvpu.observation_type = 'consciousness_acvpu'
        LEFT JOIN observation systolic_blood_pressure on os.uuid = systolic_blood_pressure.observation_set_uuid and systolic_blood_pressure.observation_type = 'systolic_blood_pressure'
        LEFT JOIN observation nurse_concern on os.uuid = nurse_concern.observation_set_uuid and nurse_concern.observation_type = 'nurse_concern'
        GROUP BY record_day, os.location, os.score_severity
        ORDER BY record_day;
        """
    )
    op.create_index(
        "location_id_idx", "agg_observation_sets", ["location_id"], unique=False
    )
    op.create_index(
        "record_day_idx", "agg_observation_sets", ["record_day"], unique=False
    )
    op.create_index(
        "score_severity_idx", "agg_observation_sets", ["score_severity"], unique=False
    )


def downgrade():
    op.drop_index("observation_type_idx", table_name="observation")
    conn = op.get_bind()
    conn.execute("DROP MATERIALIZED VIEW agg_observation_sets;")
