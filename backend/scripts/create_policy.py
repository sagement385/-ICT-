"""Validate and optionally import an explicitly reviewed policy document."""

import argparse
import asyncio
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.database import get_session_factory
from app.modules.recommendation.models import RecommendationPolicy, RecommendationWeight


class PolicyFactorDocument(BaseModel):
    """One policy factor whose numeric value must come from an approved document."""

    model_config = ConfigDict(extra="forbid")

    factor_name: str = Field(min_length=1)
    weight_value: float | None = None
    requires_approval: bool = True
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def weight_is_finite(self) -> "PolicyFactorDocument":
        """Reject non-finite numeric values without inventing a replacement."""

        if self.weight_value is not None and not math.isfinite(self.weight_value):
            raise ValueError("weight_value must be finite when provided")
        return self


class PolicyDocument(BaseModel):
    """Machine-readable policy proposal and approval metadata."""

    model_config = ConfigDict(extra="forbid")

    policy_name: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    enabled: bool = False
    approval_status: Literal["REVIEW_REQUIRED", "APPROVED"]
    evidence_source: list[str] = Field(min_length=1)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    clinical_boundary: dict[str, str | bool]
    candidate_constraints: list[str] = Field(min_length=1)
    factors: list[PolicyFactorDocument] = Field(min_length=1)
    activation_requirements: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_activation_metadata(self) -> "PolicyDocument":
        """Prevent an unapproved document from claiming active status."""

        factor_names = [factor.factor_name for factor in self.factors]
        if len(factor_names) != len(set(factor_names)):
            raise ValueError("factor_name values must be unique")
        if self.enabled and self.approval_status != "APPROVED":
            raise ValueError("enabled policies must have APPROVED status")
        if self.approval_status == "APPROVED" and any(
            factor.weight_value is None for factor in self.factors
        ):
            raise ValueError("approved policies require a numeric value for every factor")
        return self


def load_policy(path: Path) -> PolicyDocument:
    """Load and validate a policy document without touching the database."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return PolicyDocument.model_validate(payload)


async def insert_policy(document: PolicyDocument, activate: bool) -> str:
    """Insert a reviewed policy and its DB-provided weights."""

    if document.approval_status != "APPROVED":
        raise ValueError("DB insertion requires approval_status=APPROVED")
    if any(factor.weight_value is None for factor in document.factors):
        raise ValueError("DB insertion requires a numeric value for every factor")

    session_factory = get_session_factory()
    async with session_factory() as session:
        policy = RecommendationPolicy(
            policy_name=document.policy_name,
            policy_version=document.policy_version,
            enabled=activate,
            evidence_source=json.dumps(document.evidence_source, ensure_ascii=False),
            effective_from=document.effective_from,
            effective_to=document.effective_to,
        )
        session.add(policy)
        await session.flush()
        for factor in document.factors:
            session.add(
                RecommendationWeight(
                    policy_id=policy.id,
                    factor_name=factor.factor_name,
                    weight_value=factor.weight_value,
                )
            )
        await session.commit()
        return policy.id


def main() -> None:
    """Validate a draft or insert only an explicitly approved policy."""

    parser = argparse.ArgumentParser(description="Validate or import a recommendation policy document")
    parser.add_argument("--file", required=True, type=Path, help="Policy JSON document")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true", help="Validate without database writes")
    mode.add_argument("--insert", action="store_true", help="Insert an approved policy as disabled")
    parser.add_argument("--activate", action="store_true", help="Activate the inserted approved policy")
    args = parser.parse_args()
    if args.activate and not args.insert:
        parser.error("--activate requires --insert")

    document = load_policy(args.file.resolve())
    if args.validate_only:
        print(
            f"Validated policy {document.policy_name} {document.policy_version}; "
            f"approval={document.approval_status}; factors={len(document.factors)}; database_write=false"
        )
        return

    policy_id = asyncio.run(insert_policy(document, activate=args.activate))
    print(f"Inserted policy {document.policy_name} {document.policy_version}; id={policy_id}; enabled={args.activate}")


if __name__ == "__main__":
    main()
