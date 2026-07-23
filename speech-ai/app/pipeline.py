"""Speech processing workflow with safe input and empty-output validation."""

from pathlib import Path

from app.config import SpeechSettings, get_settings
from app.errors import SpeechServiceError
from app.medical_entity_extractor import MedicalEntityExtractor
from app.schemas import PatientEvent
from app.stt_provider import SttProvider


class SpeechPipeline:
    """Compose approved providers without logging audio or transcripts."""

    def __init__(
        self,
        stt: SttProvider,
        extractor: MedicalEntityExtractor,
        settings: SpeechSettings | None = None,
    ) -> None:
        self.stt = stt
        self.extractor = extractor
        self.settings = settings or get_settings()

    def process(self, audio_path: str, incident_id: str) -> PatientEvent:
        """Validate an audio file and return one contract-validated event."""

        path = self._validate_audio_path(audio_path)
        transcript = self.stt.transcribe(str(path)).strip()
        if not transcript:
            raise SpeechServiceError(
                "STT_TRANSCRIPT_EMPTY",
                "STT provider가 빈 전사 결과를 반환했습니다.",
            )
        return self.extractor.extract(transcript, incident_id)

    def _validate_audio_path(self, audio_path: str) -> Path:
        """Reject missing, oversized, unsupported, or out-of-root files."""

        path = Path(audio_path).expanduser().resolve()
        if not path.is_file():
            raise SpeechServiceError("AUDIO_FILE_NOT_FOUND", "오디오 파일을 찾을 수 없습니다.")
        if path.suffix.lower() not in self.settings.allowed_extensions:
            raise SpeechServiceError(
                "AUDIO_FORMAT_NOT_ALLOWED",
                "허용되지 않은 오디오 파일 형식입니다.",
                {"allowed_extensions": sorted(self.settings.allowed_extensions)},
            )
        if path.stat().st_size > self.settings.max_audio_bytes:
            raise SpeechServiceError(
                "AUDIO_FILE_TOO_LARGE",
                "오디오 파일이 설정된 크기 제한을 초과했습니다.",
                {"max_audio_bytes": self.settings.max_audio_bytes},
            )
        if self.settings.audio_root:
            root = Path(self.settings.audio_root).expanduser().resolve()
            if path != root and root not in path.parents:
                raise SpeechServiceError(
                    "AUDIO_PATH_OUTSIDE_CONFIGURED_ROOT",
                    "오디오 파일이 설정된 데이터 루트 밖에 있습니다.",
                )
        return path
