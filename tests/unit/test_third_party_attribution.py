from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_module():
    path = REPO_ROOT / "scripts" / "audit_third_party_licenses.py"
    spec = importlib.util.spec_from_file_location("audit_third_party_licenses", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runtime_license_audit_has_no_blockers() -> None:
    module = _load_module()
    dependency_entries, bundled_entries, missing = module.collect_inventory(REPO_ROOT / "pyproject.toml")
    issues = module.audit_issues(
        dependency_entries=dependency_entries,
        bundled_entries=bundled_entries,
        missing_packages=missing,
    )

    assert not issues
    runtime_names = {entry.name for entry in dependency_entries}
    bundled_names = {entry.name for entry in bundled_entries}
    assert "lancedb" in runtime_names
    assert "sigstore" in runtime_names
    assert "tantivy" in runtime_names
    assert "python-build-standalone" in bundled_names
    assert "CPython" in bundled_names


def test_checked_in_attribution_file_is_current() -> None:
    module = _load_module()
    dependency_entries, bundled_entries, missing = module.collect_inventory(REPO_ROOT / "pyproject.toml")
    issues = module.audit_issues(
        dependency_entries=dependency_entries,
        bundled_entries=bundled_entries,
        missing_packages=missing,
    )
    rendered = module.render_markdown(
        dependency_entries=dependency_entries,
        bundled_entries=bundled_entries,
        issues=issues,
    )
    tracked = (REPO_ROOT / "THIRD_PARTY_ATTRIBUTION.md").read_text(encoding="utf-8")

    assert tracked == rendered


def test_current_inventory_matches_lancedb_tantivy_and_vespa_distribution_posture() -> None:
    module = _load_module()
    entries = module._load_runtime_inventory_fallback()  # noqa: SLF001
    by_name = {entry.name.lower(): entry for entry in entries}

    assert by_name["lancedb"].license_expression == "Apache-2.0"
    assert by_name["tantivy"].license_expression == "MIT"
    assert "vespa" not in by_name
