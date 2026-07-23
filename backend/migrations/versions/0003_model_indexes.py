"""Add indexes declared by the existing SQLAlchemy models."""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_model_indexes"
down_revision: str | None = "0002_policy_route_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INDEXES = (
    ("ix_hospital_capability_hospital_id", "hospital_capability", "hospital_id"),
    ("ix_hospital_department_hospital_id", "hospital_department", "hospital_id"),
    ("ix_hospital_equipment_hospital_id", "hospital_equipment", "hospital_id"),
    ("ix_hospital_realtime_status_hospital_id", "hospital_realtime_status", "hospital_id"),
    ("ix_patient_symptom_incident_id", "patient_symptom", "incident_id"),
    ("ix_recommendation_result_hospital_id", "recommendation_result", "hospital_id"),
    (
        "ix_recommendation_result_recommendation_run_id",
        "recommendation_result",
        "recommendation_run_id",
    ),
    ("ix_recommendation_run_incident_id", "recommendation_run", "incident_id"),
    ("ix_recommendation_weight_policy_id", "recommendation_weight", "policy_id"),
)


def upgrade() -> None:
    """Create lookup indexes without modifying operational rows."""

    for index_name, table_name, column_name in INDEXES:
        op.create_index(index_name, table_name, [column_name])


def downgrade() -> None:
    """Drop only indexes introduced by this migration."""

    for index_name, table_name, _ in reversed(INDEXES):
        op.drop_index(index_name, table_name=table_name)
