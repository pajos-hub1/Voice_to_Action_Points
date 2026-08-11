import json
import re
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


# --- Deterministic entity parsing for the mock backend ---------------------------------
# Pulls structured fields (attendees, when, recipient, amount, ...) out of the transcript
# with simple heuristics, so downstream mock integrations get real data to work with.
# The OpenAI backend replaces this entirely when INTENT_BACKEND=openai.

_STOP_WORDS = re.compile(r"\b(?:for|at|on|about|regarding|concerning)\b", re.IGNORECASE)


def _phrase_after(transcript: str, *anchors: str) -> str | None:
    """Return the phrase after the first matching anchor, truncated at a stop word or ,;."""
    pattern = re.compile(
        r"\b(?:%s)\s+([\w][^,;.]*)" % "|".join(re.escape(a) for a in anchors),
        re.IGNORECASE,
    )
    match = pattern.search(transcript)
    if match is None:
        return None
    phrase = _STOP_WORDS.split(match.group(1).strip())[0].strip()
    return phrase or None


_DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_RELATIVE_DAYS = ("today", "tomorrow", "yesterday")
_WEEK_PHRASES = ("next week", "this week")
_TIME_RE = re.compile(r"\b(\d{1,2}(?::\d{2})?\s?(?:am|pm|a\.m\.|p\.m\.))\b", re.IGNORECASE)


def _extract_when(transcript: str) -> str | None:
    lowered = transcript.lower()
    parts: list[str] = []
    for phrase in _WEEK_PHRASES:
        if phrase in lowered:
            parts.append(phrase)
            break
    for token in (*_RELATIVE_DAYS, *_DAY_NAMES):
        if token in lowered:
            parts.append(token)
            break
    match = _TIME_RE.search(transcript)
    if match is not None:
        parts.append(match.group(1))
    return " ".join(parts) if parts else None


_AMOUNT_RE = re.compile(r"\$\s?\d+(?:\.\d{2})?|\b\d+(?:\.\d{2})?\s?(?:dollars?|usd)\b", re.IGNORECASE)


def _extract_amount(transcript: str) -> str | None:
    match = _AMOUNT_RE.search(transcript)
    return match.group(0) if match is not None else None


def extract_entities(transcript: str, intent: str) -> dict[str, Any]:
    entities: dict[str, Any] = {"raw_transcript": transcript}
    if intent == "send_email":
        recipient = _phrase_after(transcript, "to")
        if recipient is not None:
            entities["recipient"] = recipient
    elif intent == "schedule_meeting":
        attendees = _phrase_after(transcript, "with", "attendees")
        if attendees is not None:
            entities["attendees"] = attendees
        when = _extract_when(transcript)
        if when is not None:
            entities["when"] = when
    elif intent == "create_ticket":
        title = _phrase_after(transcript, "ticket for", "ticket about")
        if title is not None:
            entities["title"] = title
    elif intent == "delete_resource":
        resource = _phrase_after(transcript, "delete", "remove")
        if resource is not None:
            entities["resource"] = resource
    elif intent == "process_payment":
        payee = _phrase_after(transcript, "to", "for")
        if payee is not None:
            entities["payee"] = payee
        amount = _extract_amount(transcript)
        if amount is not None:
            entities["amount"] = amount
    return entities


class MockIntentExtractor(IntentExtractor):
    """Deterministic keyword + entity extraction, so the app runs with zero credentials."""

    def extract(self, transcript: str) -> IntentResult:
        lowered = transcript.lower()
        for keyword, intent, risk in KEYWORD_RULES:
            if keyword in lowered:
                return IntentResult(
                    intent=intent,
                    entities=extract_entities(transcript, intent),
                    risk_level=risk,
                )
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
