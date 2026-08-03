from __future__ import annotations

from datetime import UTC, datetime

import pytest

from radio_news.config import AppConfig
from radio_news.errors import SourceConfigurationConflict
from radio_news.sources import SourceRegistry


def test_source_identity_is_stable(app_config: AppConfig, now: datetime) -> None:
    first = SourceRegistry().register(app_config.source, created_at=now)
    second = SourceRegistry().register(app_config.source, created_at=now)
    assert first.source_id == second.source_id
    assert first.configuration_fingerprint == second.configuration_fingerprint


def test_source_fingerprint_independent_of_checkout_path(config_dict: dict[str, object]) -> None:
    first = AppConfig.from_dict(config_dict)
    second = AppConfig.from_dict(config_dict)
    assert SourceRegistry.fingerprint(first.source) == SourceRegistry.fingerprint(second.source)


def test_duplicate_source_same_config_is_noop(app_config: AppConfig, now: datetime) -> None:
    registry = SourceRegistry()
    first = registry.register(app_config.source, created_at=now)
    second = registry.register(
        app_config.source,
        created_at=datetime(2026, 8, 4, tzinfo=UTC),
    )
    assert first is second


def test_duplicate_source_conflicting_config_fails(
    config_dict: dict[str, object], now: datetime
) -> None:
    registry = SourceRegistry()
    first = AppConfig.from_dict(config_dict)
    registry.register(first.source, created_at=now)
    changed = {
        "source": {**config_dict["source"], "display_name": "Changed"}  # type: ignore[dict-item]
    }
    second = AppConfig.from_dict(changed)
    with pytest.raises(SourceConfigurationConflict):
        registry.register(second.source, created_at=now)
