from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import ConfigError

_ALLOWED_APP_KEYS = {"source"}
_ALLOWED_SOURCE_KEYS = {
    "source_id",
    "display_name",
    "source_type",
    "enabled",
    "trust_class",
    "fixture_resource",
}
_ALLOWED_SOURCE_TYPES = {"rss_fixture"}
_ALLOWED_TRUST_CLASSES = {"TEST"}


def _require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{field} must be an object")
    return value


def _require_exact_keys(data: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ConfigError(f"unknown {field} fields: {sorted(unknown)}")
    missing = allowed - set(data)
    if missing:
        raise ConfigError(f"missing {field} fields: {sorted(missing)}")


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ConfigError(f"{field} must not be empty")
    return normalized


def _require_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ConfigError(f"{field} must be a boolean")
    return value


def _require_fixture_resource(value: Any) -> str:
    resource = _require_nonempty_string(value, "fixture_resource")
    logical = PurePosixPath(resource)
    if logical.is_absolute() or logical.name != resource or resource in {".", ".."}:
        raise ConfigError("fixture_resource must be a single packaged fixture filename")
    if logical.suffix.lower() != ".xml":
        raise ConfigError("fixture_resource must name an XML fixture")
    return resource


@dataclass(frozen=True, slots=True)
class SourceConfig:
    source_id: str
    display_name: str
    source_type: str
    enabled: bool
    trust_class: str
    fixture_resource: str

    @classmethod
    def from_dict(cls, value: Any) -> "SourceConfig":
        data = _require_object(value, "source")
        _require_exact_keys(data, _ALLOWED_SOURCE_KEYS, "source config")
        source_type = _require_nonempty_string(data["source_type"], "source_type")
        if source_type not in _ALLOWED_SOURCE_TYPES:
            raise ConfigError(f"unknown source_type: {source_type}")
        trust_class = _require_nonempty_string(data["trust_class"], "trust_class")
        if trust_class not in _ALLOWED_TRUST_CLASSES:
            raise ConfigError(f"unknown trust_class: {trust_class}")
        return cls(
            source_id=_require_nonempty_string(data["source_id"], "source_id"),
            display_name=_require_nonempty_string(data["display_name"], "display_name"),
            source_type=source_type,
            enabled=_require_bool(data["enabled"], "enabled"),
            trust_class=trust_class,
            fixture_resource=_require_fixture_resource(data["fixture_resource"]),
        )


@dataclass(frozen=True, slots=True)
class AppConfig:
    source: SourceConfig

    @classmethod
    def from_dict(cls, value: Any) -> "AppConfig":
        data = _require_object(value, "config root")
        _require_exact_keys(data, _ALLOWED_APP_KEYS, "app config")
        return cls(source=SourceConfig.from_dict(data["source"]))


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot load config: {exc}") from exc
    return AppConfig.from_dict(raw)
