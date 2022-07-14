"""mins_late

Revision ID: 99661944c32f
Revises: 9a4a12ce753b
Create Date: 2021-04-01 15:43:37.772668

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "99661944c32f"
down_revision = "9a4a12ce753b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "observation_set", sa.Column("mins_late", sa.Integer(), nullable=True)
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


def downgrade():
    op.drop_column("observation_set", "mins_late")
