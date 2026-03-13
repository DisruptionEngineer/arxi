"""add clinical review fields

Revision ID: a3f7c1d92e4b
Revises: 1582b3a228fd
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a3f7c1d92e4b"
down_revision: Union[str, Sequence[str], None] = "1582b3a228fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add structured clinical documentation columns to prescriptions."""
    op.add_column(
        "prescriptions",
        sa.Column("rejection_reason", sa.String(50), nullable=True),
        schema="arxi",
    )
    op.add_column(
        "prescriptions",
        sa.Column("followup_action", sa.String(50), nullable=True),
        schema="arxi",
    )
    op.add_column(
        "prescriptions",
        sa.Column("clinical_checks", sa.JSON(), nullable=True),
        schema="arxi",
    )
    op.add_column(
        "prescriptions",
        sa.Column("reviewer_name", sa.String(200), nullable=True),
        schema="arxi",
    )


def downgrade() -> None:
    """Remove clinical documentation columns."""
    op.drop_column("prescriptions", "reviewer_name", schema="arxi")
    op.drop_column("prescriptions", "clinical_checks", schema="arxi")
    op.drop_column("prescriptions", "followup_action", schema="arxi")
    op.drop_column("prescriptions", "rejection_reason", schema="arxi")
