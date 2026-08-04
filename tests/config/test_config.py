from __future__ import annotations

import copy

import pytest

from radio_news.config import AppConfig
from radio_news.errors import ConfigError


def mutate(config: dict[str, object]) -> dict[str, object]:
    return copy.deepcopy(config)


def test_string_false_is_rejected(config_dict: dict[str, object]) -> None:
    data = mutate(config_dict)
    data["source"]["enabled"] = "false"  # type: ignore[index]
    with pytest.raises(ConfigError, match="boolean"):
        AppConfig.from_dict(data)


def test_integer_zero_enabled_is_rejected(config_dict: dict[str, object]) -> None:
    data = mutate(config_dict)
    data["source"]["enabled"] = 0  # type: ignore[index]
    with pytest.raises(ConfigError, match="boolean"):
        AppConfig.from_dict(data)


def test_source_must_be_object(config_dict: dict[str, object]) -> None:
    data = mutate(config_dict)
    data["source"] = []
    with pytest.raises(ConfigError, match="source must be an object"):
        AppConfig.from_dict(data)


def test_empty_source_id_is_rejected(config_dict: dict[str, object]) -> None:
    data = mutate(config_dict)
    data["source"]["source_id"] = "  "  # type: ignore[index]
    with pytest.raises(ConfigError, match="source_id must not be empty"):
        AppConfig.from_dict(data)


def test_empty_display_name_is_rejected(config_dict: dict[str, object]) -> None:
    data = mutate(config_dict)
    data["source"]["display_name"] = ""  # type: ignore[index]
    with pytest.raises(ConfigError, match="display_name must not be empty"):
        AppConfig.from_dict(data)


def test_unknown_trust_class_is_rejected(config_dict: dict[str, object]) -> None:
    data = mutate(config_dict)
    data["source"]["trust_class"] = "whatever"  # type: ignore[index]
    with pytest.raises(ConfigError, match="unknown trust_class"):
        AppConfig.from_dict(data)


def test_non_string_required_values_are_rejected(config_dict: dict[str, object]) -> None:
    data = mutate(config_dict)
    data["source"]["source_id"] = 42  # type: ignore[index]
    with pytest.raises(ConfigError, match="source_id must be a string"):
        AppConfig.from_dict(data)


def test_unknown_fields_are_rejected(config_dict: dict[str, object]) -> None:
    data = mutate(config_dict)
    data["unexpected"] = True
    with pytest.raises(ConfigError, match="unknown app config fields"):
        AppConfig.from_dict(data)


def test_fixture_resource_outside_package_root_is_rejected(config_dict: dict[str, object]) -> None:
    data = mutate(config_dict)
    data["source"]["fixture_resource"] = "../sample.xml"  # type: ignore[index]
    with pytest.raises(ConfigError, match="single packaged fixture filename"):
        AppConfig.from_dict(data)
