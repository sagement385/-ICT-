"""Add source-backed emergency-institution eligibility profiles."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_emergency_profiles"
down_revision: str | None = "0003_model_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the profile table without changing or seeding existing hospital rows."""

    op.create_table(
        "hospital_emergency_profile",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("hospital_id", sa.String(length=128), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("source_record_id", sa.String(length=256), nullable=False),
        sa.Column("source_institution_name", sa.String(length=256), nullable=False),
        sa.Column("source_address", sa.Text(), nullable=True),
        sa.Column("source_latitude", sa.Float(), nullable=True),
        sa.Column("source_longitude", sa.Float(), nullable=True),
        sa.Column("emergency_type_code", sa.String(length=64), nullable=True),
        sa.Column("emergency_type_name", sa.String(length=128), nullable=True),
        sa.Column("representative_phone", sa.String(length=64), nullable=True),
        sa.Column("emergency_phone", sa.String(length=64), nullable=True),
        sa.Column("match_method", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("coordinate_distance_meters", sa.Float(), nullable=True),
        sa.Column(
            "coordinate_warning",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("raw_payload_id", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospital.hospital_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "hospital_id",
            "source_name",
            name="uq_hospital_emergency_profile_hospital_source",
        ),
        sa.UniqueConstraint(
            "source_name",
            "source_record_id",
            name="uq_hospital_emergency_profile_source_record",
        ),
    )
    op.create_index(
        "ix_hospital_emergency_profile_hospital_id",
        "hospital_emergency_profile",
        ["hospital_id"],
    )


def downgrade() -> None:
    """Remove only the additive emergency-institution profile table."""

    op.drop_index(
        "ix_hospital_emergency_profile_hospital_id",
        table_name="hospital_emergency_profile",
    )
    op.drop_table("hospital_emergency_profile")
