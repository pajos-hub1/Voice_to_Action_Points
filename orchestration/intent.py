import json
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from orchestration.enums import RiskLevel

DEFAULT_INTENT = "unknown"

# (keyword, intent, risk_level) — first match wins. Good enough to drive the
# pipeline end-to-end without any external LLM call.
KEYWORD_RULES: list[tuple[str, str, RiskLevel]] = [
    ("email", "send_email", RiskLevel.MEDIUM),
    ("mail", "send_email", RiskLevel.MEDIUM),
    ("meeting", "schedule_meeting", RiskLevel.LOW),
    ("calendar", "schedule_meeting", RiskLevel.LOW),
    ("ticket", "create_ticket", RiskLevel.MEDIUM),
    ("delete", "delete_resource", RiskLevel.HIGH),
    ("remove", "delete_resource", RiskLevel.HIGH),
    ("pay", "process_payment", RiskLevel.HIGH),
    ("payment", "process_payment", RiskLevel.HIGH),
]

SYSTEM_PROMPT = """You are an intent-extraction engine for a voice assistant. Given a transcript of a \
spoken instruction, respond with ONLY a JSON object (no prose, no markdown fences) with this exact shape:
{"intent": "<short_snake_case_intent_name>", "entities": {"<key>": "<value>"}, "risk_level": "LOW"|"MEDIUM"|"HIGH"}
risk_level should be HIGH for anything destructive, irreversible, or financial (deleting data, payments, \
sending messages externally), MEDIUM for things that notify or create records other people will see, and LOW \
for internal/reversible actions like scheduling. If the instruction is unclear, use intent "unknown" with an \
empty entities object."""


class IntentResult(BaseModel):
    intent: str = Field(min_length=1)
    entities: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW


class MalformedIntentError(RuntimeError):
    """Raised when the intent backend can't produce schema-valid JSON after a retry."""


class IntentExtractor(ABC):
    @abstractmethod
    def extract(self, transcript: str) -> IntentResult:
        """Classify intent and extract entities from a transcript (blocking; run off the event loop)."""


class MockIntentExtractor(IntentExtractor):
    """Deterministic keyword-based extractor, so the app runs with zero credentials."""

    def extract(self, transcript: str) -> IntentResult:
        lowered = transcript.lower()
        for keyword, intent, risk in KEYWORD_RULES:
            if keyword in lowered:
                return IntentResult(intent=intent, entities={"raw_transcript": transcript}, risk_level=risk)
        return IntentResult(intent=DEFAULT_INTENT, entities={"raw_transcript": transcript}, risk_level=RiskLevel.LOW)


class OpenAIIntentExtractor(IntentExtractor):
    """Real OpenAI backend: strict JSON-mode prompt, Pydantic-validated, one retry on malformed output."""

    def __init__(self, api_key: str, model: str):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def extract(self, transcript: str) -> IntentResult:
        for _ in range(2):
            raw = self._call(transcript)
            try:
                return IntentResult.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValueError) as error:
                last_error = error
        raise MalformedIntentError(f"OpenAI returned malformed intent JSON twice: {last_error}") from last_error

    def _call(self, transcript: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
        )
        return response.choices[0].message.content or "{}"
