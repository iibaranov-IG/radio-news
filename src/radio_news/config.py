from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ALLOWED_APP_KEYS = {"database_path", "source"}
_ALLOWED_SOURCE_KEYS = {"source_id", "display_name", "source_type", "enabled", "trust_class", "fixture_path"}


@dataclass(frozen=True, slots=True)
class SourceConfig:
    source_id: str
    display_name: str
    source_type: str
    enabled: bool
    trust_class: str
    fixture_path: Path

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, base_dir: Path) -> "SourceConfig":
        unknown = set(data) - _ALLOWED_SOURCE_KEYS
        if unknown:
            raise ValueError(f"unknown source config fields: {sorted(unknown)}")
        missing = _ALLOWED_SOURCE_KEYS - set(data)
        if missing:
            raise ValueError(f"missing source config fields: {sorted(missing)}")
        if data["source_type"] != "rss_fixture":
            raise ValueError("first slice supports source_type='rss_fixture' only")
        fixture_path = Path(os.path.expandvars(str(data["fixture_path"])))
        if not fixture_path.is_absolute():
            fixture_path = (base_dir / fixture_path).resolve()
        return cls(
            source_id=str(data["source_id"]),
            display_name=str(data["display_name"]),
            source_type=str(data["source_type"]),
            enabled=bool(data["enabled"]),
            trust_class=str(data["trust_class"]),
            fixture_path=fixture_path,
        )


@dataclass(frozen=True, slots=True)
class AppConfig:
    database_path: Path
    source: SourceConfig

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, base_dir: Path) -> "AppConfig":
        unknown = set(data) - _ALLOWED_APP_KEYS
        if unknown:
            raise ValueError(f"unknown app config fields: {sorted(unknown)}")
        missing = _ALLOWED_APP_KEYS - set(data)
        if missing:
            raise ValueError(f"missing app config fields: {sorted(missing)}")
        database_path = Path(os.path.expandvars(str(data["database_path"])))
        if not database_path.is_absolute():
            database_path = (base_dir / database_path).resolve()
        return cls(database_path=database_path, source=SourceConfig.from_dict(data["source"], base_dir=base_dir))


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).resolve()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("config root must be an object")
    return AppConfig.from_dict(raw, base_dir=config_path.parent)
