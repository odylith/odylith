from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.common import derivation_provenance
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.governance import sync_session


def test_provenance_matches_only_enforces_generation_when_requested(tmp_path: Path) -> None:
    expected = derivation_provenance.build_derivation_provenance(
        repo_root=tmp_path,
        projection_scope="reasoning",
        projection_fingerprint="fp-1",
        sync_generation=3,
        code_version="code-v1",
        flags={"projection_names": ["workstreams", "plans"]},
    )
    actual = dict(expected)
    actual["sync_generation"] = 1

    assert derivation_provenance.provenance_matches(
        actual=actual,
        expected=expected,
        require_generation=False,
    )
    assert not derivation_provenance.provenance_matches(
        actual=actual,
        expected=expected,
        require_generation=True,
    )


def test_governed_sync_session_persists_debug_manifest(tmp_path: Path) -> None:
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)

    session.bump_generation(
        step_label="refresh registry truth",
        mutation_classes=("repo_owned_truth",),
        invalidated_namespaces=("runtime_warm", "projection_repo_state"),
        paths=("odylith/registry/source/component_registry.v1.json",),
    )

    debug_path = odylith_context_cache.cache_path(
        repo_root=tmp_path,
        namespace="debug",
        key="governed-sync-session",
    )
    payload = json.loads(debug_path.read_text(encoding="utf-8"))

    assert payload["generation"] == 1
    assert payload["last_invalidation_step"] == "refresh registry truth"
    assert payload["invalidation_events"][0]["invalidated_namespaces"] == [
        "runtime_warm",
        "projection_repo_state",
    ]
