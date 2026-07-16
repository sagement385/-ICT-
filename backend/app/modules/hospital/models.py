"""SQLAlchemy models for normalized hospital capability and freshness data."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def new_id() -> str:
    """Return an opaque database identifier."""

    return str(uuid4())


class Hospital(Base):
    """Normalized hospital base information with source provenance."""

    __tablename__ = "hospital"

    hospital_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    hospital_name: Mapped[str] = mapped_column(String(256), nullable=False)
    hospital_type_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    raw_payload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class HospitalDepartment(Base):
    """Hospital department and specialist count from a source record."""

    __tablename__ = "hospital_department"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospital.hospital_id"), nullable=False, index=True)
    department_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    department_name: Mapped[str] = mapped_column(String(256), nullable=False)
    specialist_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HospitalEquipment(Base):
    """Hospital equipment record."""

    __tablename__ = "hospital_equipment"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospital.hospital_id"), nullable=False, index=True)
    equipment_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    equipment_name: Mapped[str] = mapped_column(String(256), nullable=False)
    equipment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HospitalCapability(Base):
    """Named care capability. Availability is source data, not inferred here."""

    __tablename__ = "hospital_capability"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospital.hospital_id"), nullable=False, index=True)
    capability_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capability_name: Mapped[str] = mapped_column(String(256), nullable=False)
    available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HospitalRealtimeStatus(Base):
    """Time-bound hospital acceptance and bed status."""

    __tablename__ = "hospital_realtime_status"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospital.hospital_id"), nullable=False, index=True)
    acceptance_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    available_beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    raw_payload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HospitalEmergencyProfile(Base):
    """Official emergency-institution registration linked to a canonical hospital."""

    __tablename__ = "hospital_emergency_profile"
    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "source_record_id",
            name="uq_hospital_emergency_profile_source_record",
        ),
        UniqueConstraint(
            "hospital_id",
            "source_name",
            name="uq_hospital_emergency_profile_hospital_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    hospital_id: Mapped[str] = mapped_column(
        ForeignKey("hospital.hospital_id"),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_institution_name: Mapped[str] = mapped_column(String(256), nullable=False)
    source_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    emergency_type_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emergency_type_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    representative_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    match_method: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    coordinate_distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    coordinate_warning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_payload_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DataSourceRegistry(Base):
    """Registry row describing a configured external data source."""

    __tablename__ = "data_source_registry"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(256), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    auth_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schema_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
