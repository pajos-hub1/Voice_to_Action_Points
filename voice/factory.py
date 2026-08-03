from app.config import Settings
from voice.azure_transcriber import AzureTranscriber
from voice.base import Transcriber
from voice.mock_transcriber import MockTranscriber


def get_transcriber(settings: Settings) -> Transcriber:
    if settings.transcriber_backend == "azure":
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise RuntimeError(
                "TRANSCRIBER_BACKEND=azure requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION to be set."
            )
        return AzureTranscriber(speech_key=settings.azure_speech_key, region=settings.azure_speech_region)
    return MockTranscriber()
