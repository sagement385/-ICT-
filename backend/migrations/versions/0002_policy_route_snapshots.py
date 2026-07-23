"""Add policy factor metadata and source-backed route snapshots."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_policy_route_snapshots"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add only schema objects; no policy, weight, route, or hospital rows are seeded."""

    op.add_column(
        "recommendation_weight",
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "recommendation_weight",
        sa.Column("source_field", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "recommendation_weight",
        sa.Column("direction", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "recommendation_weight",
        sa.Column("normalization", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "recommendation_weight",
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "recommendation_weight",
        sa.Column("missing_data_behavior", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "recommendation_weight",
        sa.Column("stale_data_behavior", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "recommendation_weight",
        sa.Column("hard_exclusion", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "recommendation_weight",
        sa.Column("explanation", sa.Text(), nullable=True),
    )
    op.add_column(
        "recommendation_weight",
        sa.Column("configuration_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "recommendation_run",
        sa.Column(
            "warnings_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "recommendation_result",
        sa.Column(
            "source_provenance_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )

    op.create_table(
        "route_snapshot",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("incident_id", sa.String(length=128), nullable=False),
        sa.Column("hospital_id", sa.String(length=128), nullable=False),
        sa.Column("recommendation_run_id", sa.String(length=64), nullable=True),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("distance_meters", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("traffic_summary", sa.Text(), nullable=True),
        sa.Column("path_json", sa.JSON(), nullable=True),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("source_record_id", sa.String(length=256), nullable=True),
        sa.Column("raw_payload_id", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("source_metadata_json", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospital.hospital_id"]),
        sa.ForeignKeyConstraint(["incident_id"], ["patient_case.incident_id"]),
        sa.ForeignKeyConstraint(["recommendation_run_id"], ["recommendation_run.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_route_snapshot_hospital_id", "route_snapshot", ["hospital_id"])
    op.create_index("ix_route_snapshot_incident_id", "route_snapshot", ["incident_id"])
    op.create_index(
        "ix_route_snapshot_recommendation_run_id",
        "route_snapshot",
        ["recommendation_run_id"],
    )


def downgrade() -> None:
    """Remove the additive schema objects in reverse dependency order."""

    op.drop_index("ix_route_snapshot_recommendation_run_id", table_name="route_snapshot")
    op.drop_index("ix_route_snapshot_incident_id", table_name="route_snapshot")
    op.drop_index("ix_route_snapshot_hospital_id", table_name="route_snapshot")
    op.drop_table("route_snapshot")
    op.drop_column("recommendation_result", "source_provenance_json")
    op.drop_column("recommendation_run", "warnings_json")
    for column_name in (
        "configuration_json",
        "explanation",
        "hard_exclusion",
        "stale_data_behavior",
        "missing_data_behavior",
        "required",
        "normalization",
        "direction",
        "source_field",
        "enabled",
    ):
        op.drop_column("recommendation_weight", column_name)
