"""Safe speech pipeline input and provider-output tests."""

from pathlib import Path

import pytest

from app.config import SpeechSettings
from app.errors import SpeechServiceError
from app.pipeline import SpeechPipeline
from app.schemas import PatientEvent

FIXTURE_ROOT = Path(__file__).parent / "fixtures"
TEST_AUDIO = FIXTURE_ROOT / "TEST_AUDIO.wav"


class EmptyStt:
    """Return an explicitly empty TEST transcript."""

    def transcribe(self, audio_path: str) -> str:
        """Confirm the TEST fixture reached the provider boundary."""

        assert audio_path.endswith("TEST_AUDIO.wav")
        return "   "


class NeverExtractor:
    """Fail when called because empty STT output must stop first."""

    def extract(self, transcript: str, incident_id: str) -> PatientEvent:
        """Signal an invalid pipeline call."""

        del transcript, incident_id
        raise AssertionError("extractor must not run for an empty transcript")


def settings() -> SpeechSettings:
    """Return isolated TEST-only audio policy settings."""

    return SpeechSettings(
        _env_file=None,
        SPEECH_AUDIO_ROOT=str(FIXTURE_ROOT),
        SPEECH_ALLOWED_AUDIO_EXTENSIONS=".wav",
        SPEECH_MAX_AUDIO_BYTES=1024,
    )


def test_pipeline_rejects_missing_audio() -> None:
    """Missing paths fail before any provider is invoked."""

    pipeline = SpeechPipeline(EmptyStt(), NeverExtractor(), settings())

    with pytest.raises(SpeechServiceError, match="오디오 파일") as caught:
        pipeline.process(str(FIXTURE_ROOT / "TEST_MISSING.wav"), "TEST_PATIENT_001")

    assert caught.value.code == "AUDIO_FILE_NOT_FOUND"


def test_pipeline_rejects_empty_transcript() -> None:
    """A provider cannot turn an empty transcript into a fabricated patient event."""

    pipeline = SpeechPipeline(EmptyStt(), NeverExtractor(), settings())

    with pytest.raises(SpeechServiceError) as caught:
        pipeline.process(str(TEST_AUDIO), "TEST_PATIENT_001")

    assert caught.value.code == "STT_TRANSCRIPT_EMPTY"
