"""SQLAlchemy models for policy-controlled recommendation runs."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
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


class RecommendationPolicy(Base):
    """Versioned policy metadata; no medical defaults are stored here."""

    __tablename__ = "recommendation_policy"
    __table_args__ = (
        UniqueConstraint(
            "policy_name",
            "policy_version",
            name="uq_recommendation_policy_name_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    policy_name: Mapped[str] = mapped_column(String(256), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_source: Mapped[str | None] = mapped_column(String(512), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RecommendationWeight(Base):
    """A policy factor and all behavior needed to interpret its DB weight."""

    __tablename__ = "recommendation_weight"
    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "factor_name",
            name="uq_recommendation_weight_policy_factor",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    policy_id: Mapped[str] = mapped_column(ForeignKey("recommendation_policy.id"), nullable=False, index=True)
    factor_name: Mapped[str] = mapped_column(String(128), nullable=False)
    weight_value: Mapped[float] = mapped_column(Float, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    normalization: Mapped[str | None] = mapped_column(String(32), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    missing_data_behavior: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stale_data_behavior: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hard_exclusion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    configuration_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RecommendationRun(Base):
    """Audit record for one recommendation attempt."""

    __tablename__ = "recommendation_run"
    __table_args__ = (
        Index("ix_recommendation_run_incident_started", "incident_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    incident_id: Mapped[str] = mapped_column(ForeignKey("patient_case.incident_id"), nullable=False, index=True)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("recommendation_policy.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class RecommendationResult(Base):
    """Persisted result with explicit freshness and explanation payloads."""

    __tablename__ = "recommendation_result"
    __table_args__ = (
        Index(
            "ix_recommendation_result_run_rank",
            "recommendation_run_id",
            "rank",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    recommendation_run_id: Mapped[str] = mapped_column(ForeignKey("recommendation_run.id"), nullable=False, index=True)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospital.hospital_id"), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    exclusion_reasons_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    recommendation_reasons_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    data_freshness_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
