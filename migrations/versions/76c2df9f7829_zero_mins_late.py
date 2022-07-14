"""zero_mins_late

Revision ID: 76c2df9f7829
Revises: 683bdc6f91b7
Create Date: 2021-10-05 10:02:09.769402

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "76c2df9f7829"
down_revision = "683bdc6f91b7"
branch_labels = None
depends_on = None


def upgrade():
    print("Updating all observation sets with NULL mins_late field")
    conn = op.get_bind()
    conn.execute(
        """
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
                ) a
            LEFT JOIN 
                (select ROW_NUMBER() OVER (ORDER BY encounter_id, record_time) rn,
                o.uuid, o.time_next_obs_set_due, o.record_time, o.encounter_id
                FROM observation_set o) p_obs
            on a.rn = p_obs.rn + 1 and a.encounter_id = p_obs.encounter_id
        ) ex 
        WHERE observation_set.uuid = ex.uuid and observation_set.mins_late is NULL;
    """
    )
    print("Updating `agg_observation_sets`")
    conn.execute("REFRESH MATERIALIZED VIEW agg_observation_sets;")


def downgrade():
    print(
        "Updating all observation sets so that the first observation set in an encounter has NULL mins_late field"
    )
    conn = op.get_bind()
    conn.execute(
        """
        UPDATE observation_set 
        SET mins_late = ex.curr_obs_mins_late
        FROM 
        (
            SELECT 
                a.uuid, ROUND((EXTRACT(hour FROM (a.record_time - p_obs.time_next_obs_set_due ))*60*60
                + EXTRACT(minutes FROM (a.record_time - p_obs.time_next_obs_set_due))*60
                + EXTRACT(seconds FROM (a.record_time - p_obs.time_next_obs_set_due)))/60)
                curr_obs_mins_late
            FROM
                (
                    SELECT ROW_NUMBER() OVER (ORDER BY encounter_id, record_time) rn, 
                    o.uuid, o.time_next_obs_set_due, o.record_time, o.encounter_id
                    FROM observation_set o
                ) a
            LEFT JOIN 
                (select ROW_NUMBER() OVER (ORDER BY encounter_id, record_time) rn,
                o.uuid, o.time_next_obs_set_due, o.record_time, o.encounter_id
                FROM observation_set o) p_obs
            on a.rn = p_obs.rn + 1 and a.encounter_id = p_obs.encounter_id
        ) ex 
        WHERE observation_set.uuid = ex.uuid;
        """
    )
    conn.execute("REFRESH MATERIALIZED VIEW agg_observation_sets;")

    # ### end Alembic commands ###
