import pytest

from orchestration.enums import RiskLevel
from orchestration.intent import MockIntentExtractor


@pytest.mark.parametrize(
    "transcript,expected_intent,expected_risk",
    [
        ("please schedule a meeting with the design team", "schedule_meeting", RiskLevel.LOW),
        ("send an email to finance about the invoice", "send_email", RiskLevel.MEDIUM),
        ("open a ticket for the broken build", "create_ticket", RiskLevel.MEDIUM),
        ("delete the staging database", "delete_resource", RiskLevel.HIGH),
        ("process a payment for the vendor", "process_payment", RiskLevel.HIGH),
        ("what's the weather like", "unknown", RiskLevel.LOW),
    ],
)
def test_mock_intent_extractor_keyword_rules(transcript, expected_intent, expected_risk) -> None:
    result = MockIntentExtractor().extract(transcript)
    assert result.intent == expected_intent
    assert result.risk_level == expected_risk
    assert result.entities["raw_transcript"] == transcript


@pytest.mark.parametrize(
    "transcript,expected_intent,expected_entities",
    [
        (
            "please schedule a meeting with the design team for tomorrow at 3pm",
            "schedule_meeting",
            {"attendees": "the design team", "when": "tomorrow 3pm"},
        ),
        ("send an email to finance about the invoice", "send_email", {"recipient": "finance"}),
        ("open a ticket for the broken login flow", "create_ticket", {"title": "the broken login flow"}),
        ("delete the staging database", "delete_resource", {"resource": "the staging database"}),
        ("process a payment of $250 to the vendor", "process_payment", {"payee": "the vendor", "amount": "$250"}),
    ],
)
def test_mock_intent_extractor_parses_entities(transcript, expected_intent, expected_entities) -> None:
    result = MockIntentExtractor().extract(transcript)

    assert result.intent == expected_intent
    for key, expected in expected_entities.items():
        assert result.entities[key] == expected
