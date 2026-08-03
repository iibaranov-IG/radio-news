from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from .config import SourceConfig
from .domain import RawItem


class SourceAdapter(Protocol):
    def read(self) -> list[RawItem]: ...


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, SourceConfig] = {}

    def register(self, source: SourceConfig) -> str:
        if source.source_id in self._sources:
            raise ValueError(f"duplicate source_id: {source.source_id}")
        self._sources[source.source_id] = source
        payload = asdict(source)
        payload["fixture_path"] = str(payload["fixture_path"])
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


def _text(node: ET.Element, name: str) -> str:
    child = node.find(name)
    return "" if child is None or child.text is None else child.text.strip()


class RSSFixtureParser:
    def __init__(self, source: SourceConfig, *, fetched_at: datetime) -> None:
        if source.source_type != "rss_fixture":
            raise ValueError("network sources are not authorized in the first slice")
        self.source = source
        self.fetched_at = fetched_at.astimezone(UTC)

    def read(self) -> list[RawItem]:
        payload_bytes = Path(self.source.fixture_path).read_bytes()
        payload = payload_bytes.decode("utf-8")
        root = ET.fromstring(payload_bytes)
        items: list[RawItem] = []
        for element in root.findall("./channel/item"):
            guid = _text(element, "guid") or _text(element, "link")
            link = _text(element, "link")
            title = _text(element, "title")
            content = _text(element, "description")
            published_at = datetime.strptime(
                _text(element, "pubDate"), "%a, %d %b %Y %H:%M:%S %z"
            ).astimezone(UTC)
            content_hash = hashlib.sha256((title + "\n" + content + "\n" + payload).encode()).hexdigest()
            raw_id = hashlib.sha256(f"{self.source.source_id}\0{guid}".encode()).hexdigest()
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
