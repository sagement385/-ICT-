"""SQLAlchemy models for source-backed route snapshots."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def new_id() -> str:
    """Return an opaque route snapshot identifier."""

    return str(uuid4())


class RouteSnapshot(Base):
    """Persist one provider route without treating it as permanently current."""

    __tablename__ = "route_snapshot"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("patient_case.incident_id"), nullable=False, index=True
    )
    hospital_id: Mapped[str] = mapped_column(
        ForeignKey("hospital.hospital_id"), nullable=False, index=True
    )
    recommendation_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("recommendation_run.id"), nullable=True, index=True
    )
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    distance_meters: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    traffic_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    path_json: Mapped[list[list[float]] | None] = mapped_column(JSON, nullable=True)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    raw_payload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
