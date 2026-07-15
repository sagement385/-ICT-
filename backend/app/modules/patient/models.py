"""SQLAlchemy models for patient events and raw ingestion records."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def new_id() -> str:
    """Return an opaque database identifier."""

    return str(uuid4())


class RawIngestionEvent(Base):
    """Immutable source payload envelope."""

    __tablename__ = "raw_ingestion_event"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PatientCase(Base):
    """Structured patient state keyed by the incident id from the contract."""

    __tablename__ = "patient_case"

    incident_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    consciousness_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    breathing_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bleeding_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    urgency_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    address_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PatientSymptom(Base):
    """A symptom extracted by the speech AI pipeline."""

    __tablename__ = "patient_symptom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("patient_case.incident_id"), nullable=False, index=True)
    symptom_code: Mapped[str] = mapped_column(String(128), nullable=False)
    symptom_label: Mapped[str] = mapped_column(String(256), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

