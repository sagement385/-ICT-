"""Backend event delivery tests with an in-memory HTTP transport."""

import json
from pathlib import Path

import httpx
import pytest

from app.backend_client import BackendClient
from app.errors import SpeechServiceError
from app.schemas import PatientEvent

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "patient-event-test.json"


def patient_event() -> PatientEvent:
    """Load redacted TEST data from the fixture boundary."""

    return PatientEvent.model_validate(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


@pytest.mark.asyncio
async def test_backend_client_retries_one_server_failure() -> None:
    """A transient 5xx is retried within the configured bound."""

    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.headers["Idempotency-Key"] == "TEST_PATIENT_001"
        if calls == 1:
            return httpx.Response(503, json={"error": {"code": "TEST_TRANSIENT"}})
        return httpx.Response(201, json={"incident_id": "TEST_PATIENT_001"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await BackendClient(
            "http://test-backend",
            max_retries=1,
            http_client=http_client,
        ).submit_patient_event(patient_event())

    assert calls == 2
    assert result["incident_id"] == "TEST_PATIENT_001"


@pytest.mark.asyncio
async def test_backend_client_resolves_duplicate_to_existing_event() -> None:
    """A duplicate POST reads the canonical stored event instead of duplicating it."""

    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.method == "POST":
            return httpx.Response(409, json={"error": {"code": "PATIENT_ALREADY_EXISTS"}})
        return httpx.Response(200, json={"incident_id": "TEST_PATIENT_001"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await BackendClient(
            "http://test-backend",
            http_client=http_client,
        ).submit_patient_event(patient_event())

    assert methods == ["POST", "GET"]
    assert result["incident_id"] == "TEST_PATIENT_001"


@pytest.mark.asyncio
async def test_backend_client_requires_configuration() -> None:
    """Missing backend configuration returns a stable non-secret error."""

    with pytest.raises(SpeechServiceError) as caught:
        await BackendClient(None).submit_patient_event(patient_event())

    assert caught.value.code == "BACKEND_NOT_CONFIGURED"
