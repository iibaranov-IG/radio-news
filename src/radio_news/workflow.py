from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .config import AppConfig
from .domain import (
    Claim,
    DomainGraph,
    Fact,
    NormalizedItem,
    Story,
    VerificationResult,
)
from .errors import RadioNewsError
from .sources import RSSFixtureParser, SourceRegistry
from .storage import SQLiteStore
from .verification import VerificationPolicy


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _canonical_url(url: str) -> str:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        raise RadioNewsError("fixture item URL must be absolute")
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, "")
    )


@dataclass(frozen=True, slots=True)
class PipelineItemResult:
    raw_item_id: str
    status: str
    verification_status: str


@dataclass(frozen=True, slots=True)
class PipelineResult:
    source_id: str
    source_status: str
    items: tuple[PipelineItemResult, ...]
    counts: dict[str, int]
    migration_versions: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        verification_statuses = sorted({item.verification_status for item in self.items})
        result: dict[str, object] = {
            "source_id": self.source_id,
            "source_status": self.source_status,
            "raw_item_ids": [item.raw_item_id for item in self.items],
            "item_statuses": [item.status for item in self.items],
            "verification_status": (
                verification_statuses[0]
                if len(verification_statuses) == 1
                else verification_statuses
            ),
            "migration_versions": list(self.migration_versions),
        }
        result.update(self.counts)
        return result


def run_fixture_pipeline(
    config: AppConfig,
    *,
    database_path: str | Path,
    editor_id: str,
    now: datetime,
    payload_override: bytes | None = None,
    policy: VerificationPolicy | None = None,
) -> PipelineResult:
    if not config.source.enabled:
        raise RadioNewsError("configured fixture source is disabled")
    if not editor_id.strip():
        raise RadioNewsError("editor_id must not be empty")
    if now.tzinfo is None:
        raise RadioNewsError("now must be timezone-aware")
    now = now.astimezone(UTC)
    policy = policy or VerificationPolicy()

    registry = SourceRegistry()
    source = registry.register(config.source, created_at=now)
    parser = RSSFixtureParser(config.source, fetched_at=now)
    store = SQLiteStore(database_path)
    migration_versions = store.migrate()

    item_results: list[PipelineItemResult] = []
    source_status = "existing"
    raw_items = parser.read(payload_override=payload_override)
    for raw in raw_items:
        canonical_url = _canonical_url(raw.source_url)
        normalized = NormalizedItem(
            id=_stable_id("normalized", raw.id),
            raw_item_id=raw.id,
            title=" ".join(raw.raw_title.split()),
            content=" ".join(raw.raw_content.split()),
            canonical_url=canonical_url,
        )
        canonical_key = hashlib.sha256(
            f"{canonical_url}\0{normalized.title.casefold()}".encode("utf-8")
        ).hexdigest()
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
            editor_id=editor_id.strip(),
            decided_at=now,
            editorial_status="APPROVED",
            supporting_claim_ids=(claim.id,),
        )
        decision = policy.evaluate(fact, (claim,))
        verification = VerificationResult(
            id=_stable_id("verification", f"{fact.id}\0{decision.policy_version}"),
            fact_id=fact.id,
            status=decision.status,
            reason_codes=decision.reason_codes,
            reason=decision.reason,
            policy_version=decision.policy_version,
            evaluated_at=now,
        )
        persist = store.persist_graph(
            DomainGraph(
                source=source,
                raw=raw,
                normalized=normalized,
                story=story,
                claim=claim,
                fact=fact,
                verification=verification,
            )
        )
        source_status = persist.source_status
        item_results.append(
            PipelineItemResult(
                raw_item_id=raw.id,
                status=persist.status,
                verification_status=verification.status,
            )
        )

    return PipelineResult(
        source_id=source.source_id,
        source_status=source_status,
        items=tuple(item_results),
        counts=store.counts(),
        migration_versions=migration_versions,
    )
