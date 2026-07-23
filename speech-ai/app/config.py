"""Environment configuration for optional speech providers and safe file limits."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SpeechSettings(BaseSettings):
    """Speech service settings with no provider selected by default."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
        populate_by_name=True,
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    stt_provider: str | None = Field(default=None, alias="SPEECH_STT_PROVIDER")
    entity_extractor: str | None = Field(
        default=None,
        alias="SPEECH_ENTITY_EXTRACTOR",
    )
    audio_root: str | None = Field(default=None, alias="SPEECH_AUDIO_ROOT")
    max_audio_bytes: int = Field(
        default=25 * 1024 * 1024,
        ge=1,
        alias="SPEECH_MAX_AUDIO_BYTES",
    )
    allowed_audio_extensions: str = Field(
        default=".wav,.mp3,.m4a,.flac",
        alias="SPEECH_ALLOWED_AUDIO_EXTENSIONS",
    )
    backend_api_base_url: str | None = Field(
        default=None,
        alias="BACKEND_API_BASE_URL",
    )
    backend_timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        alias="BACKEND_TIMEOUT_SECONDS",
    )
    backend_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        alias="BACKEND_MAX_RETRIES",
    )

    @property
    def allowed_extensions(self) -> set[str]:
        """Return normalized configured audio extensions."""

        return {
            extension.strip().lower()
            for extension in self.allowed_audio_extensions.split(",")
            if extension.strip()
        }


@lru_cache(maxsize=1)
def get_settings() -> SpeechSettings:
    """Return the process-wide settings snapshot."""

    return SpeechSettings()
