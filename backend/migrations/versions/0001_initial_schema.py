"""Create the initial source-traceable domain tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create tables only; no operational rows are seeded."""

    op.create_table(
        "raw_ingestion_event",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("source_record_id", sa.String(256)),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "patient_case",
        sa.Column("incident_id", sa.String(128), primary_key=True),
        sa.Column("consciousness_status", sa.String(64)),
        sa.Column("breathing_status", sa.String(64)),
        sa.Column("bleeding_status", sa.String(64)),
        sa.Column("urgency_level", sa.String(64)),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("address_text", sa.Text),
        sa.Column("source_model_name", sa.String(128), nullable=False),
        sa.Column("source_model_version", sa.String(128), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "patient_symptom",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("incident_id", sa.String(128), sa.ForeignKey("patient_case.incident_id"), nullable=False),
        sa.Column("symptom_code", sa.String(128), nullable=False),
        sa.Column("symptom_label", sa.String(256), nullable=False),
        sa.Column("confidence", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "hospital",
        sa.Column("hospital_id", sa.String(128), primary_key=True),
        sa.Column("hospital_name", sa.String(256), nullable=False),
        sa.Column("hospital_type_code", sa.String(64)),
        sa.Column("address", sa.Text),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("phone", sa.String(64)),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("source_record_id", sa.String(256)),
        sa.Column("raw_payload_id", sa.String(64)),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "hospital_department",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("hospital_id", sa.String(128), sa.ForeignKey("hospital.hospital_id"), nullable=False),
        sa.Column("department_code", sa.String(128)),
        sa.Column("department_name", sa.String(256), nullable=False),
        sa.Column("specialist_count", sa.Integer),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "hospital_equipment",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("hospital_id", sa.String(128), sa.ForeignKey("hospital.hospital_id"), nullable=False),
        sa.Column("equipment_code", sa.String(128)),
        sa.Column("equipment_name", sa.String(256), nullable=False),
        sa.Column("equipment_count", sa.Integer),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "hospital_capability",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("hospital_id", sa.String(128), sa.ForeignKey("hospital.hospital_id"), nullable=False),
        sa.Column("capability_code", sa.String(128)),
        sa.Column("capability_name", sa.String(256), nullable=False),
        sa.Column("available", sa.Boolean),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "hospital_realtime_status",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("hospital_id", sa.String(128), sa.ForeignKey("hospital.hospital_id"), nullable=False),
        sa.Column("acceptance_status", sa.String(128)),
        sa.Column("available_beds", sa.Integer),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("source_record_id", sa.String(256)),
        sa.Column("raw_payload_id", sa.String(64)),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "recommendation_policy",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("policy_name", sa.String(256), nullable=False),
        sa.Column("policy_version", sa.String(128), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("evidence_source", sa.String(512)),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "recommendation_weight",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("policy_id", sa.String(64), sa.ForeignKey("recommendation_policy.id"), nullable=False),
        sa.Column("factor_name", sa.String(128), nullable=False),
        sa.Column("weight_value", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "recommendation_run",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("incident_id", sa.String(128), sa.ForeignKey("patient_case.incident_id"), nullable=False),
        sa.Column("policy_id", sa.String(64), sa.ForeignKey("recommendation_policy.id")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("error_code", sa.String(128)),
    )
    op.create_table(
        "recommendation_result",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("recommendation_run_id", sa.String(64), sa.ForeignKey("recommendation_run.id"), nullable=False),
        sa.Column("hospital_id", sa.String(128), sa.ForeignKey("hospital.hospital_id"), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("total_score", sa.Float, nullable=False),
        sa.Column("score_breakdown_json", sa.JSON, nullable=False),
        sa.Column("exclusion_reasons_json", sa.JSON, nullable=False),
        sa.Column("recommendation_reasons_json", sa.JSON, nullable=False),
        sa.Column("data_freshness_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "data_source_registry",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("dataset_id", sa.String(128)),
        sa.Column("provider_name", sa.String(256), nullable=False),
        sa.Column("base_url", sa.String(512)),
        sa.Column("auth_type", sa.String(128)),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("schema_version", sa.String(64)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Drop tables in reverse dependency order."""

    for table_name in (
        "data_source_registry",
        "recommendation_result",
        "recommendation_run",
        "recommendation_weight",
        "recommendation_policy",
        "hospital_realtime_status",
        "hospital_capability",
        "hospital_equipment",
        "hospital_department",
        "hospital",
        "patient_symptom",
        "patient_case",
        "raw_ingestion_event",
    ):
        op.drop_table(table_name)

