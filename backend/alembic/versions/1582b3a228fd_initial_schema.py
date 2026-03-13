"""initial schema

Revision ID: 1582b3a228fd
Revises:
Create Date: 2026-03-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1582b3a228fd"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables across schemas."""
    # Create schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS compliance")
    op.execute("CREATE SCHEMA IF NOT EXISTS arxi")

    # --- public.users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "pharmacist", "technician", "agent", name="role"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema="public",
    )

    # --- compliance.audit_log ---
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("actor_id", sa.String(100), nullable=False, index=True),
        sa.Column("actor_role", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False, index=True),
        sa.Column("resource_id", sa.String(100), nullable=False, index=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        schema="compliance",
    )

    # --- arxi.drugs ---
    op.create_table(
        "drugs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ndc", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("drug_name", sa.String(300), nullable=False, index=True),
        sa.Column("generic_name", sa.String(300), nullable=False, server_default=""),
        sa.Column("dosage_form", sa.String(100), nullable=False, server_default=""),
        sa.Column("strength", sa.String(100), nullable=False, server_default=""),
        sa.Column("route", sa.String(100), nullable=False, server_default=""),
        sa.Column("manufacturer", sa.String(200), nullable=False, server_default=""),
        sa.Column("dea_schedule", sa.String(10), nullable=False, server_default=""),
        sa.Column("package_description", sa.Text(), nullable=False, server_default=""),
        schema="arxi",
    )

    # --- arxi.patients ---
    op.create_table(
        "patients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False, index=True),
        sa.Column("gender", sa.String(10), nullable=False),
        sa.Column("date_of_birth", sa.String(10), nullable=False),
        sa.Column("address_line1", sa.String(200), nullable=False, server_default=""),
        sa.Column("city", sa.String(100), nullable=False, server_default=""),
        sa.Column("state", sa.String(2), nullable=False, server_default=""),
        sa.Column("postal_code", sa.String(10), nullable=False, server_default=""),
        schema="arxi",
    )

    # --- arxi.prescriptions ---
    op.create_table(
        "prescriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "status",
            sa.Enum(
                "received",
                "parsed",
                "validated",
                "pending_review",
                "approved",
                "rejected",
                "corrected",
                name="rxstatus",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("message_id", sa.String(100), nullable=False, server_default=""),
        sa.Column("raw_xml", sa.Text(), nullable=True),
        # Patient info (denormalized)
        sa.Column("patient_id", sa.String(36), nullable=True),
        sa.Column("patient_first_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("patient_last_name", sa.String(100), nullable=False, server_default="", index=True),
        sa.Column("patient_dob", sa.String(10), nullable=False, server_default=""),
        # Prescriber
        sa.Column("prescriber_npi", sa.String(10), nullable=False, server_default=""),
        sa.Column("prescriber_dea", sa.String(20), nullable=False, server_default=""),
        sa.Column("prescriber_name", sa.String(200), nullable=False, server_default=""),
        # Medication
        sa.Column("drug_description", sa.String(500), nullable=False, server_default=""),
        sa.Column("ndc", sa.String(20), nullable=False, server_default="", index=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("days_supply", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("refills", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sig_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("written_date", sa.String(10), nullable=False, server_default=""),
        sa.Column("substitutions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        # Review
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="arxi",
    )


def downgrade() -> None:
    """Drop all tables and schemas."""
    op.drop_table("prescriptions", schema="arxi")
    op.drop_table("patients", schema="arxi")
    op.drop_table("drugs", schema="arxi")
    op.drop_table("audit_log", schema="compliance")
    op.drop_table("users", schema="public")

    # Clean up enum types
    op.execute("DROP TYPE IF EXISTS rxstatus")
    op.execute("DROP TYPE IF EXISTS role")

    # Drop schemas
    op.execute("DROP SCHEMA IF EXISTS arxi")
    op.execute("DROP SCHEMA IF EXISTS compliance")
