from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from importlib.resources import files
from typing import Protocol

from .config import SourceConfig
from .domain import RawItem, SourceRecord
from .errors import FixtureParseError, SourceConfigurationConflict

_FIXTURE_PACKAGE = "radio_news.fixtures"


class SourceAdapter(Protocol):
    def read(self, *, payload_override: bytes | None = None) -> list[RawItem]: ...


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


class SourceRegistry:
    def __init__(self) -> None:
        self._records: dict[str, SourceRecord] = {}

    @staticmethod
    def fingerprint(source: SourceConfig) -> str:
        logical_config = {
            "source_id": source.source_id,
            "source_type": source.source_type,
            "display_name": source.display_name,
            "enabled": source.enabled,
            "trust_class": source.trust_class,
            "fixture_resource": source.fixture_resource,
        }
        return hashlib.sha256(_canonical_json(logical_config)).hexdigest()

    def register(self, source: SourceConfig, *, created_at: datetime) -> SourceRecord:
        fingerprint = self.fingerprint(source)
        existing = self._records.get(source.source_id)
        if existing is not None:
            if existing.configuration_fingerprint != fingerprint:
                raise SourceConfigurationConflict(
                    f"source_id {source.source_id!r} has a conflicting configuration"
                )
            return existing
        record = SourceRecord(
            source_id=source.source_id,
            source_type=source.source_type,
            display_name=source.display_name,
            enabled=source.enabled,
            trust_class=source.trust_class,
            configuration_fingerprint=fingerprint,
            created_at=created_at.astimezone(UTC),
        )
        self._records[source.source_id] = record
        return record


def load_fixture_bytes(resource_name: str) -> bytes:
    resource = files(_FIXTURE_PACKAGE).joinpath(resource_name)
    if not resource.is_file():
        raise FixtureParseError(f"packaged fixture not found: {resource_name}")
    return resource.read_bytes()


def _required_text(node: ET.Element, name: str) -> str:
    child = node.find(name)
    text = "" if child is None or child.text is None else child.text.strip()
    if not text:
        raise FixtureParseError(f"RSS item is missing required field: {name}")
    return text


class RSSFixtureParser:
    def __init__(self, source: SourceConfig, *, fetched_at: datetime) -> None:
        if source.source_type != "rss_fixture":
            raise FixtureParseError("network sources are not authorized in the first slice")
        if fetched_at.tzinfo is None:
            raise FixtureParseError("fetched_at must be timezone-aware")
        self.source = source
        self.fetched_at = fetched_at.astimezone(UTC)

    def read(self, *, payload_override: bytes | None = None) -> list[RawItem]:
        payload_bytes = payload_override or load_fixture_bytes(self.source.fixture_resource)
        try:
            payload = payload_bytes.decode("utf-8")
            root = ET.fromstring(payload_bytes)
        except (UnicodeDecodeError, ET.ParseError) as exc:
            raise FixtureParseError(f"invalid RSS fixture: {exc}") from exc
        elements = root.findall("./channel/item")
        if not elements:
            raise FixtureParseError("RSS fixture contains no channel items")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        items: list[RawItem] = []
        for element in elements:
            guid = _required_text(element, "guid")
            link = _required_text(element, "link")
            title = _required_text(element, "title")
            content = _required_text(element, "description")
            pub_date = _required_text(element, "pubDate")
            try:
                published_at = parsedate_to_datetime(pub_date).astimezone(UTC)
            except (TypeError, ValueError) as exc:
                raise FixtureParseError(f"invalid pubDate: {pub_date}") from exc
            item_payload = {
                "guid": guid,
                "link": link,
                "title": title,
                "content": content,
                "published_at": published_at.isoformat(),
                "feed_payload_hash": payload_hash,
            }
            content_hash = hashlib.sha256(_canonical_json(item_payload)).hexdigest()
            raw_id = hashlib.sha256(
                f"{self.source.source_id}\0{guid}".encode("utf-8")
            ).hexdigest()
            items.append(
                RawItem(
                    id=raw_id,
                    source_id=self.source.source_id,
                    source_external_id=guid,
                    source_url=link,
                    published_at=published_at,
                    fetched_at=self.fetched_at,
                    raw_title=title,
                    raw_content=content,
                    raw_payload=payload,
                    content_hash=content_hash,
                )
            )
        return items
