from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

from .config import AppConfig
from .domain import Claim, Fact, NormalizedItem, Story, VerificationResult
from .sources import RSSFixtureParser, SourceRegistry
from .storage import SQLiteStore

POLICY_VERSION = "manual-fact-v1"


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode()).hexdigest()}"


def _canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


@dataclass(frozen=True, slots=True)
class PipelineResult:
    raw_item_ids: tuple[str, ...]
    counts: dict[str, int]


def run_fixture_pipeline(config: AppConfig, *, editor_id: str, now: datetime) -> PipelineResult:
    if not config.source.enabled:
        raise ValueError("configured fixture source is disabled")
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(UTC)

    registry = SourceRegistry()
    registry.register(config.source)
    parser = RSSFixtureParser(config.source, fetched_at=now)
    store = SQLiteStore(config.database_path)
    store.migrate()

    raw_ids: list[str] = []
    for raw in parser.read():
        canonical_url = _canonical_url(raw.source_url)
        normalized = NormalizedItem(
            id=_stable_id("normalized", raw.id),
            raw_item_id=raw.id,
            title=" ".join(raw.raw_title.split()),
            content=" ".join(raw.raw_content.split()),
            canonical_url=canonical_url,
        )
        canonical_key = hashlib.sha256(f"{canonical_url}\0{normalized.title.casefold()}".encode()).hexdigest()
        story = Story(
            id=_stable_id("story", canonical_key),
            canonical_key=canonical_key,
            title=normalized.title,
            created_at=raw.published_at,
        )
        claim = Claim(
            id=_stable_id("claim", raw.id),
            story_id=story.id,
            raw_item_id=raw.id,
            text=normalized.content,
            asserted_at=raw.published_at,
        )
        fact = Fact(
            id=_stable_id("fact", f"{story.id}\0{normalized.content}"),
            story_id=story.id,
            canonical_text=normalized.content,
            editor_id=editor_id,
            decided_at=now,
            editorial_status="APPROVED",
        )
        verification = VerificationResult(
            id=_stable_id("verification", f"{fact.id}\0{POLICY_VERSION}"),
            fact_id=fact.id,
            status="READY",
            reason="manual fact approved from one fixture claim",
            policy_version=POLICY_VERSION,
            evaluated_at=now,
        )
        store.upsert_graph(raw, normalized, story, claim, fact, verification)
        raw_ids.append(raw.id)

    return PipelineResult(raw_item_ids=tuple(raw_ids), counts=store.counts())
