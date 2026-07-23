"""Speech boundary service that starts safely before model providers exist."""

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import SpeechServiceError

app = FastAPI(
    title="Chungbuk 119 Speech AI Boundary",
    version="0.1.0",
    description="승인된 STT·추출 provider를 연결하기 위한 비진단 음성 처리 경계",
)


@app.exception_handler(SpeechServiceError)
async def speech_error_handler(request: Request, error: SpeechServiceError) -> JSONResponse:
    """Return a stable envelope without transcript or patient content."""

    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Report process health without requiring optional models."""

    return {"status": "ok", "service": "speech-ai"}


@app.get("/status")
async def status() -> dict[str, object]:
    """Expose provider readiness without credentials or model output."""

    settings = get_settings()
    missing = []
    if not settings.stt_provider:
        missing.append("SPEECH_STT_PROVIDER")
    if not settings.entity_extractor:
        missing.append("SPEECH_ENTITY_EXTRACTOR")
    return {
        "status": "ready" if not missing else "not_configured",
        "stt_configured": bool(settings.stt_provider),
        "entity_extractor_configured": bool(settings.entity_extractor),
        "backend_configured": bool(settings.backend_api_base_url),
        "missing_settings": missing,
        "medical_decision_support_only": True,
    }


def main() -> None:
    """Run the optional service with health endpoints always available."""

    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8100)


if __name__ == "__main__":
    main()
