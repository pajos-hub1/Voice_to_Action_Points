from app.config import get_settings
from voice.base import Transcriber
from voice.factory import get_transcriber as build_transcriber


def get_transcriber_dep() -> Transcriber:
    return build_transcriber(get_settings())
