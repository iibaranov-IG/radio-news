from __future__ import annotations

from datetime import UTC, datetime

from radio_news.domain import Claim, Fact
from radio_news.verification import VerificationPolicy


def make_claim(story_id: str = "story-1") -> Claim:
    return Claim("claim-1", story_id, "raw-1", "claim", datetime(2026, 8, 3, tzinfo=UTC))


def make_fact(story_id: str = "story-1", status: str = "APPROVED") -> Fact:
    return Fact(
        "fact-1",
        story_id,
        "fact",
        "editor-1",
        datetime(2026, 8, 3, tzinfo=UTC),
        status,
        ("claim-1",),
    )


def test_verifier_returns_ready_for_approved_manual_fact() -> None:
    decision = VerificationPolicy().evaluate(make_fact(), (make_claim(),))
    assert decision.status == "READY"


def test_verifier_rejects_fact_without_supporting_claims() -> None:
    original = make_fact()
    fact = Fact(
        original.id,
        original.story_id,
        original.canonical_text,
        original.editor_id,
        original.decided_at,
        original.editorial_status,
        (),
    )
    decision = VerificationPolicy().evaluate(fact, ())
    assert decision.status == "BLOCKED"
    assert decision.reason_codes == ("NO_SUPPORTING_CLAIMS",)


def test_verifier_rejects_cross_story_claim() -> None:
    decision = VerificationPolicy().evaluate(make_fact(), (make_claim("story-2"),))
    assert decision.status == "BLOCKED"
    assert "CROSS_STORY_CLAIM" in decision.reason_codes


def test_verifier_result_is_deterministic() -> None:
    policy = VerificationPolicy()
    first = policy.evaluate(make_fact(), (make_claim(),))
    second = policy.evaluate(make_fact(), (make_claim(),))
    assert first == second
