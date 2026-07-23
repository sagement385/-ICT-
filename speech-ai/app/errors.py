"""Typed speech-boundary errors that never fabricate provider output."""


class SpeechServiceError(RuntimeError):
    """Base error carrying a stable non-sensitive code."""

    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class SpeechProviderNotConfigured(SpeechServiceError):
    """Raised when an approved model provider has not been selected."""

    def __init__(self, missing_settings: list[str]) -> None:
        super().__init__(
            "SPEECH_PROVIDER_NOT_CONFIGURED",
            "승인된 STT 또는 의료 엔터티 추출 provider가 설정되지 않았습니다.",
            {"missing_settings": missing_settings},
        )
