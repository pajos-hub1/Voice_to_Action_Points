from app.config import Settings
from orchestration.intent import IntentExtractor, MockIntentExtractor, OpenAIIntentExtractor


def get_intent_extractor(settings: Settings) -> IntentExtractor:
    if settings.intent_backend == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("INTENT_BACKEND=openai requires OPENAI_API_KEY to be set.")
        return OpenAIIntentExtractor(api_key=settings.openai_api_key, model=settings.openai_model)
    return MockIntentExtractor()
