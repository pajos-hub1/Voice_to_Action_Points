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
