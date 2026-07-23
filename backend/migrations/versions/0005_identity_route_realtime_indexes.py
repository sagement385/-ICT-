"""Add cross-source identities, route validity, realtime provenance, and lookup constraints."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_identity_route_indexes"
down_revision: str | None = "0004_emergency_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply additive schema changes without seeding operational records."""

    op.add_column(
        "route_snapshot",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "route_snapshot",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "hospital_realtime_status",
        sa.Column("source_updated_at_raw", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "hospital_realtime_status",
        sa.Column(
            "source_timezone",
            sa.String(length=64),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
    )

    op.create_table(
        "hospital_source_identity",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("hospital_id", sa.String(length=128), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("source_record_id", sa.String(length=256), nullable=False),
        sa.Column("source_hospital_name", sa.String(length=256), nullable=True),
        sa.Column("match_method", sa.String(length=64), nullable=False),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column(
            "verified",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "match_confidence IS NULL OR (match_confidence >= 0 AND match_confidence <= 1)",
            name="ck_hospital_source_identity_confidence",
        ),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospital.hospital_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_name",
            "source_record_id",
            name="uq_hospital_source_identity_source_record",
        ),
    )
    op.create_index(
        "ix_hospital_source_identity_hospital_id",
        "hospital_source_identity",
        ["hospital_id"],
    )

    op.create_index(
        "ix_hospital_realtime_status_latest",
        "hospital_realtime_status",
        ["hospital_id", "source_updated_at", "fetched_at"],
    )
    op.create_index(
        "ix_route_snapshot_incident_hospital_fetched",
        "route_snapshot",
        ["incident_id", "hospital_id", "fetched_at"],
    )
    op.create_index(
        "ix_recommendation_run_incident_started",
        "recommendation_run",
        ["incident_id", "started_at"],
    )
    op.create_index(
        "ix_recommendation_result_run_rank",
        "recommendation_result",
        ["recommendation_run_id", "rank"],
    )

    op.create_unique_constraint(
        "uq_recommendation_policy_name_version",
        "recommendation_policy",
        ["policy_name", "policy_version"],
    )
    op.create_unique_constraint(
        "uq_recommendation_weight_policy_factor",
        "recommendation_weight",
        ["policy_id", "factor_name"],
    )
    op.create_unique_constraint(
        "uq_data_source_registry_source_name",
        "data_source_registry",
        ["source_name"],
    )


def downgrade() -> None:
    """Remove only schema objects introduced by this migration."""

    op.drop_constraint(
        "uq_data_source_registry_source_name",
        "data_source_registry",
        type_="unique",
    )
    op.drop_constraint(
        "uq_recommendation_weight_policy_factor",
        "recommendation_weight",
        type_="unique",
    )
    op.drop_constraint(
        "uq_recommendation_policy_name_version",
        "recommendation_policy",
        type_="unique",
    )

    op.drop_index("ix_recommendation_result_run_rank", table_name="recommendation_result")
    op.drop_index("ix_recommendation_run_incident_started", table_name="recommendation_run")
    op.drop_index(
        "ix_route_snapshot_incident_hospital_fetched",
        table_name="route_snapshot",
    )
    op.drop_index(
        "ix_hospital_realtime_status_latest",
        table_name="hospital_realtime_status",
    )
    op.drop_index(
        "ix_hospital_source_identity_hospital_id",
        table_name="hospital_source_identity",
    )
    op.drop_table("hospital_source_identity")

    op.drop_column("hospital_realtime_status", "source_timezone")
    op.drop_column("hospital_realtime_status", "source_updated_at_raw")
    op.drop_column("route_snapshot", "created_at")
    op.drop_column("route_snapshot", "expires_at")
