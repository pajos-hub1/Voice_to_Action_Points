from app.config import get_settings
from orchestration.factory import get_intent_extractor as build_intent_extractor
from orchestration.intent import IntentExtractor
from voice.base import Transcriber
from voice.factory import get_transcriber as build_transcriber


def get_transcriber_dep() -> Transcriber:
    return build_transcriber(get_settings())


def get_intent_extractor_dep() -> IntentExtractor:
    return build_intent_extractor(get_settings())
