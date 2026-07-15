"""Patient persistence tests using isolated TEST fixture data."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.errors import ApplicationError
from app.modules.patient.models import PatientCase, RawIngestionEvent
from app.modules.patient.schemas import PatientEventRequest
from app.modules.patient.service import PatientService

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "recommendation-policy-engine-test.json"


def load_event() -> PatientEventRequest:
    """Build one patient event entirely from the TEST fixture."""

    fixture: dict[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    patient = fixture["patient"]
    return PatientEventRequest.model_validate(
        {
            "incident_id": patient["incident_id"],
            "observed_at": datetime.fromisoformat(fixture["now"]),
            "location": {
                "latitude": patient["latitude"],
                "longitude": patient["longitude"],
                "address_text": None,
            },
            "symptoms": [
                {
                    "code": patient["symptom_code"],
                    "label": patient["symptom_label"],
                    "confidence": None,
                }
            ],
            "consciousness_status": None,
            "breathing_status": None,
            "bleeding_status": None,
            "urgency_level": None,
            "source": {
                "model_name": "TEST_CHAT_INTAKE",
                "model_version": "TEST_VERSION_001",
            },
        }
    )


@pytest.mark.asyncio
async def test_duplicate_incident_returns_conflict_without_duplicate_raw_event() -> None:
    """A repeated incident is rejected before a second raw envelope is stored."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        service = PatientService(session)
        event = load_event()
        await service.create(event)

        with pytest.raises(ApplicationError) as error:
            await service.create(event)

        assert error.value.code == "PATIENT_ALREADY_EXISTS"
        assert error.value.status_code == 409
        assert await session.scalar(select(func.count()).select_from(PatientCase)) == 1
        assert await session.scalar(select(func.count()).select_from(RawIngestionEvent)) == 1

    await engine.dispose()
