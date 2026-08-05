from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HORIZON_MANIFEST = ROOT / "provenance" / "horizon-components.json"
PRODUCT_MANIFEST = ROOT / "provenance" / "product-stages.json"
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


def _horizon_authorized_targets() -> tuple[dict[str, dict[str, object]], list[str]]:
    manifest = json.loads(HORIZON_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    entries = {entry["component_id"]: entry for entry in manifest["components"]}
    assert IMPLEMENTED <= entries.keys()
    targets: list[str] = []
    for component_id in IMPLEMENTED:
        entry = entries[component_id]
        assert entry["implementation_authorized"] is True
        assert entry["authorized_stage"].startswith("FIRST_VERTICAL_SLICE")
        assert "not_started" not in entry["local_changes"]
        targets.extend(entry["target_paths"])
    return entries, targets


def _product_authorized_targets() -> list[str]:
    manifest = json.loads(PRODUCT_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["active_stage"] == "PRODUCT_SLICE_P4"
    assert manifest["authorization_document"] == "docs/product/p4-deterministic-draft-edition.md"
    stages = {entry["stage_id"]: entry for entry in manifest["stages"]}

    p1 = stages["PRODUCT_SLICE_P1"]
    assert p1["authorized_stage"] == "PRODUCT_SLICE_P1"
    assert p1["implementation_authorized"] is True
    assert p1["gate_status"] == "PASS"
    assert p1["merge_commit"] == "b2296481c24098931c27124aef97f649dc9188fe"

    p2 = stages["PRODUCT_SLICE_P2"]
    assert p2["authorized_stage"] == "PRODUCT_SLICE_P2"
    assert p2["implementation_authorized"] is True
    assert p2["authorization_merge_commit"] == "e9f1de908383399ec3b909e341616e09d5148f41"
    assert p2["implementation_merge_commit"] == "3ed3aa6623d5dbe16458c8bc45f76def1a921910"
    assert p2["gate_status"] == "PASS"
    assert set(p2["authorized_existing_components"]) <= IMPLEMENTED

    p3 = stages["PRODUCT_SLICE_P3"]
    assert p3["authorized_stage"] == "PRODUCT_SLICE_P3"
    assert p3["implementation_authorized"] is True
    assert p3["authorization_merge_commit"] == "2cf3849c4b3f493c7b01a3ac27fcac89310c145c"
    assert p3["implementation_merge_commit"] == "d3475ded0d1890aaa2af58b2bf9f1cbcfda6b668"
    assert p3["gate_status"] == "PASS"
    assert set(p3["authorized_existing_components"]) <= IMPLEMENTED

    p4 = stages["PRODUCT_SLICE_P4"]
    assert p4["authorized_stage"] == "PRODUCT_SLICE_P4"
    assert p4["implementation_authorized"] is True
    assert p4["authorization_merge_commit"] == "1eef0dd3cc5d86e99da4a0bdf665636a7f51bf76"
    assert set(p4["authorized_existing_components"]) <= IMPLEMENTED
    assert "deterministic_generation_only" in p4["constraints"]
    assert "writes_confined_to_p4_draft_state" in p4["constraints"]
    assert "p3_and_evidence_domain_immutable" in p4["constraints"]
    assert "additive_migration_only" in p4["constraints"]
    assert "no_ai_or_llm" in p4["constraints"]
    assert "no_rundown" in p4["constraints"]

    p5 = stages["PRODUCT_SLICE_P5"]
    assert p5["authorized_stage"] == "PRODUCT_SLICE_P5"
    assert p5["implementation_authorized"] is False

    return (
        list(p1["authorized_paths"])
        + list(p2["authorized_paths"])
        + list(p3["authorized_paths"])
        + list(p4["authorized_paths"])
    )


def test_implementation_paths_are_covered_by_active_authorities() -> None:
    _, horizon_targets = _horizon_authorized_targets()
    product_targets = _product_authorized_targets()
    authorized_targets = horizon_targets + product_targets
    uncovered = sorted(
        path
        for path in IMPLEMENTATION_PATHS
        if not any(_matches(path, target) for target in authorized_targets)
    )
    assert uncovered == []


def test_blocked_components_remain_unauthorized() -> None:
    entries, _ = _horizon_authorized_targets()
    for component_id in BLOCKED:
        assert entries[component_id]["implementation_authorized"] is False
