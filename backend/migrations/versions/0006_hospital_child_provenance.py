"""Add source provenance to normalized hospital child records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_child_provenance"
down_revision: str | None = "0005_identity_route_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("hospital_department", "hospital_equipment", "hospital_capability")


def upgrade() -> None:
    """Add nullable traceability fields without altering existing source rows."""

    for table_name in TABLES:
        op.add_column(table_name, sa.Column("source_name", sa.String(128), nullable=True))
        op.add_column(
            table_name,
            sa.Column("source_record_id", sa.String(256), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("raw_payload_id", sa.String(64), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("schema_version", sa.String(64), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Remove only the child-record provenance fields from this revision."""

    for table_name in TABLES:
        op.drop_column(table_name, "fetched_at")
        op.drop_column(table_name, "schema_version")
        op.drop_column(table_name, "raw_payload_id")
        op.drop_column(table_name, "source_record_id")
        op.drop_column(table_name, "source_name")
