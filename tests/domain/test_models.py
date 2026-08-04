from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from radio_news.domain import Claim, Fact, RawItem


def test_domain_entities_are_immutable() -> None:
    raw = RawItem(
        id="raw-1",
        source_id="source-1",
        source_external_id="external-1",
        source_url="https://example.test/1",
        published_at=datetime(2026, 8, 3, tzinfo=UTC),
        fetched_at=datetime(2026, 8, 3, tzinfo=UTC),
        raw_title="Title",
        raw_content="Content",
        raw_payload="<rss/>",
        content_hash="a" * 64,
    )
    with pytest.raises(FrozenInstanceError):
        raw.raw_title = "Changed"  # type: ignore[misc]


def test_fact_explicitly_records_supporting_claim_ids() -> None:
    claim = Claim(
        id="claim-1",
        story_id="story-1",
        raw_item_id="raw-1",
        text="Claim",
        asserted_at=datetime(2026, 8, 3, tzinfo=UTC),
    )
    fact = Fact(
        id="fact-1",
        story_id="story-1",
        canonical_text="Fact",
        editor_id="editor-1",
        decided_at=datetime(2026, 8, 3, tzinfo=UTC),
        editorial_status="APPROVED",
        supporting_claim_ids=(claim.id,),
    )
    assert fact.supporting_claim_ids == (claim.id,)
