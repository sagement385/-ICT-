"""Speech processing workflow without a bundled model or fixture import."""

from app.medical_entity_extractor import MedicalEntityExtractor
from app.schemas import PatientEvent
from app.stt_provider import SttProvider


class SpeechPipeline:
    """Compose STT and entity extraction through explicit provider interfaces."""

    def __init__(self, stt: SttProvider, extractor: MedicalEntityExtractor) -> None:
        self.stt = stt
        self.extractor = extractor

    def process(self, audio_path: str, incident_id: str) -> PatientEvent:
        """Process one audio path; no fallback text or patient values are generated."""

        transcript = self.stt.transcribe(audio_path)
        return self.extractor.extract(transcript, incident_id)

