"""Speech-to-text provider interface with no vendor default."""

from typing import Protocol

from app.errors import SpeechProviderNotConfigured


class SttProvider(Protocol):
    """Contract for a real STT implementation selected by deployment config."""

    def transcribe(self, audio_path: str) -> str:
        """Return transcription text for an approved audio input."""


class NotConfiguredSttProvider:
    """Explicit provider used until a real STT model is selected."""

    def transcribe(self, audio_path: str) -> str:
        """Stop instead of returning fabricated transcription."""

        del audio_path
        raise SpeechProviderNotConfigured(["SPEECH_STT_PROVIDER"])
