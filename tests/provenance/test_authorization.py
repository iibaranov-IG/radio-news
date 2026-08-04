from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "provenance" / "horizon-components.json"
IMPLEMENTED = {
    "PKG-01",
    "CLI-01",
    "ORCH-01",
    "CONFIG-01",
    "REG-01",
    "SCRAPE-BASE",
    "RSS-01",
    "MODEL-01",
    "STORE-01",
    "FILE-01",
    "SQLITE-TARGET",
    "CI-01",
    "TEST-01",
}
BLOCKED = {"HTTP-GAP", "SSRF-01", "SSRF-02", "TEST-SEC", "I18N-02"}
IMPLEMENTATION_PATHS = {
    "pyproject.toml",
    ".github/workflows/ci.yml",
    *{
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (ROOT / "src" / "radio_news").rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix in {".py", ".sql", ".xml"}
    },
    *{
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (ROOT / "tests").rglob("*.py")
    },
}


def _matches(path: str, target: str) -> bool:
    normalized = target.rstrip("/")
    return path == normalized or path.startswith(normalized + "/")


def test_implementation_paths_are_authorized_for_first_slice() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    entries = {entry["component_id"]: entry for entry in manifest["components"]}
    assert IMPLEMENTED <= entries.keys()
    authorized_targets: list[str] = []
    for component_id in IMPLEMENTED:
        entry = entries[component_id]
        assert entry["implementation_authorized"] is True
        assert entry["authorized_stage"].startswith("FIRST_VERTICAL_SLICE")
        assert "not_started" not in entry["local_changes"]
        authorized_targets.extend(entry["target_paths"])
    uncovered = sorted(
        path
        for path in IMPLEMENTATION_PATHS
        if not any(_matches(path, target) for target in authorized_targets)
    )
    assert uncovered == []


def test_blocked_components_remain_unauthorized() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {entry["component_id"]: entry for entry in manifest["components"]}
    for component_id in BLOCKED:
        assert entries[component_id]["implementation_authorized"] is False
