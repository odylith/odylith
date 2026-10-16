"""Canonical Registry categories survive loading, caching, and surface payloads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.governance import component_registry_intelligence as registry
from odylith.runtime.surfaces import render_registry_dashboard as renderer
from tests.unit.runtime.test_render_registry_dashboard import _load_registry_payload, _seed_repo


def _seed_application_registry(root: Path) -> Path:
    _seed_repo(root)
    manifest = root / "odylith/registry/source/component_registry.v1.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["components"][0]["category"] = "application"
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest


@pytest.mark.parametrize(("category", "kind", "expected"), [
    ("application", "", "application"),
    ("Application", "composite", "application"),
    ("governance_engine", "", "governance_engine"),
    ("governance-surface", "", "governance_surface"),
    ("control_gate", "", "control_gate"),
    ("infrastructure", "", "infrastructure"),
    ("data", "", "data"),
    ("platform_runtime", "", "governance_engine"),
    ("tooling", "", "control_gate"),
    ("", "", ""),
    ("unrecognized", "", ""),
    ("uncategorized", "", ""),
    ("", "composite", "governance_surface"),
    ("", "system", "infrastructure"),
    ("", "service", "governance_engine"),
    ("", "validator", "control_gate"),
    ("", "dataset", "data"),
    ("unrecognized", "system", "infrastructure"),
    ("", "unrecognized", "governance_engine"),
])
def test_category_normalization_preserves_authored_application_and_existing_contracts(
    category: str, kind: str, expected: str,
) -> None:
    assert registry.normalize_component_category(category, fallback_kind=kind) == expected


def test_authored_application_survives_manifest_and_rendered_payload(tmp_path: Path) -> None:
    manifest = _seed_application_registry(tmp_path)
    source_bytes = manifest.read_bytes()
    report = registry.build_component_registry_report(repo_root=tmp_path)
    assert report.components["radar"].category == "application"
    assert report.components["odylith"].category == "governance_engine"
    assert not any("invalid category" in error for error in report.diagnostics)

    assert renderer.main(["--repo-root", str(tmp_path), "--runtime-mode", "standalone"]) == 0
    payload = _load_registry_payload(tmp_path)
    assert {row["component_id"]: row["category"] for row in payload["components"]} == {
        "radar": "application", "odylith": "governance_engine",
    }
    assert payload["counts"]["by_category"] == {"application": 1, "governance_engine": 1}
    assert manifest.read_bytes() == source_bytes


def test_explicit_unknown_manifest_category_remains_rejected(tmp_path: Path) -> None:
    manifest = _seed_application_registry(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["components"][0]["category"] = "unrecognized"
    manifest.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    report = registry.build_component_registry_report(repo_root=tmp_path)

    assert "radar" not in report.components
    assert any("invalid category `unrecognized`" in error for error in report.diagnostics)


def test_legacy_normalized_index_and_report_caches_are_invalidated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _seed_application_registry(tmp_path)
    source_bytes = manifest.read_bytes()
    normalize = registry.normalize_component_category

    def legacy_category(value: str, *, fallback_kind: str = "") -> str:
        if value == "application":
            return "governance_engine"
        return normalize(value, fallback_kind=fallback_kind)

    with monkeypatch.context() as legacy:
        legacy.setattr(registry, "_COMPONENT_INDEX_CACHE_VERSION", "v2")
        legacy.setattr(registry, "_COMPONENT_REPORT_CACHE_VERSION", "v5")
        legacy.setattr(registry, "normalize_component_category", legacy_category)
        assert registry.build_component_registry_report(repo_root=tmp_path).components["radar"].category == "governance_engine"

    assert registry.build_component_registry_report(repo_root=tmp_path).components["radar"].category == "application"
    assert registry.build_component_registry_report(repo_root=tmp_path).components["radar"].category == "application"
    assert manifest.read_bytes() == source_bytes
