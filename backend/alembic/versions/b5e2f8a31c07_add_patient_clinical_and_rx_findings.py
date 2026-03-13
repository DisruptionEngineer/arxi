"""add patient clinical data and rx clinical findings

Revision ID: b5e2f8a31c07
Revises: a3f7c1d92e4b
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b5e2f8a31c07"
down_revision: Union[str, Sequence[str], None] = "a3f7c1d92e4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add patient allergies/conditions and Rx clinical_findings."""
    # Patient clinical profile
    op.add_column(
        "patients",
        sa.Column("allergies", sa.JSON(), nullable=True, server_default="[]"),
        schema="arxi",
    )
    op.add_column(
        "patients",
        sa.Column("conditions", sa.JSON(), nullable=True, server_default="[]"),
        schema="arxi",
    )
    # Prescription AI clinical findings
    op.add_column(
        "prescriptions",
        sa.Column("clinical_findings", sa.JSON(), nullable=True),
        schema="arxi",
    )


def downgrade() -> None:
    """Remove clinical columns."""
    op.drop_column("prescriptions", "clinical_findings", schema="arxi")
    op.drop_column("patients", "conditions", schema="arxi")
    op.drop_column("patients", "allergies", schema="arxi")
