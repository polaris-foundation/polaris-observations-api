"""modified_idx

Revision ID: 9a4a12ce753b
Revises: 7c044c108b2f
Create Date: 2021-02-15 17:11:45.456115

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "9a4a12ce753b"
down_revision = "7c044c108b2f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("modified_idx", "observation_set", ["modified"], unique=False)


def downgrade():
    op.drop_index("modified_idx", table_name="observation_set")
