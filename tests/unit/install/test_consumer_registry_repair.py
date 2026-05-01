from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from odylith.install.consumer_registry_repair import repair_component_register_registry_drift


def _write_legacy_component_register_output(repo_root: Path) -> tuple[Path, Path]:
    manifest_path = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    spec_path = repo_root / "odylith" / "registry" / "source" / "components" / "dentoai-isb" / "CURRENT_SPEC.md"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "components": [
                    {
                        "component_id": "dentoai-isb",
                        "name": "Dentoai Isb",
                        "kind": "library",
                        "category": "detected",
                        "qualification": "detected",
                        "aliases": [],
                        "path_prefixes": ["dentoai_isb"],
                        "workstreams": [],
                        "diagrams": [],
                        "owner": "product",
                        "status": "active",
                        "what_it_is": "Logical component registered through `odylith component register`.",
                        "why_tracked": "Registered so agent sessions can see Dentoai Isb as a named ownership boundary.",
                        "spec_ref": "odylith/registry/source/components/dentoai-isb/CURRENT_SPEC.md",
                        "sources": ["manifest"],
                        "subcomponents": [],
                        "product_layer": "cli_bootstrap",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    spec_path.write_text(
        (
            "# Dentoai Isb\n\n"
            "## Overview\n\n"
            "Dentoai Isb is a `library` component registered through `odylith component register`.\n\n"
            "## Boundary\n\n"
            "- **Evidence anchor**: `dentoai_isb`\n\n"
            "## Contract\n\n"
            "TBD.\n"
        ),
        encoding="utf-8",
    )
    return manifest_path, spec_path


def test_repair_component_register_registry_drift_updates_detected_taxonomy_and_spec_history(
    tmp_path: Path,
) -> None:
    manifest_path, spec_path = _write_legacy_component_register_output(tmp_path)

    result = repair_component_register_registry_drift(
        repo_root=tmp_path,
        consumer_repo=True,
        today=dt.date(2026, 4, 30),
    )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    component = payload["components"][0]
    spec_text = spec_path.read_text(encoding="utf-8")
    assert result.changed is True
    assert result.repaired_components == ("dentoai-isb",)
    assert result.repaired_specs == ("odylith/registry/source/components/dentoai-isb/CURRENT_SPEC.md",)
    assert component["category"] == "governance_engine"
    assert component["qualification"] == "candidate"
    assert "## Feature History" in spec_text
    assert "- 2026-04-30: Repaired Odylith 0.1.11 component register metadata drift for `dentoai-isb`." in spec_text

    second = repair_component_register_registry_drift(
        repo_root=tmp_path,
        consumer_repo=True,
        today=dt.date(2026, 4, 30),
    )

    assert second.changed is False


def test_repair_component_register_registry_drift_skips_product_repos(tmp_path: Path) -> None:
    manifest_path, spec_path = _write_legacy_component_register_output(tmp_path)
    before_manifest = manifest_path.read_text(encoding="utf-8")
    before_spec = spec_path.read_text(encoding="utf-8")

    result = repair_component_register_registry_drift(
        repo_root=tmp_path,
        consumer_repo=False,
        today=dt.date(2026, 4, 30),
    )

    assert result.changed is False
    assert result.skipped_reason == "not a consumer repo"
    assert manifest_path.read_text(encoding="utf-8") == before_manifest
    assert spec_path.read_text(encoding="utf-8") == before_spec
