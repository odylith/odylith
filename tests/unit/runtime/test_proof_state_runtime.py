from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_projection_backlog_runtime as projection_backlog
from odylith.runtime.context_engine import odylith_context_engine_projection_entity_runtime as projection_entity
from odylith.runtime.context_engine import odylith_context_engine_store as context_engine_store
from odylith.runtime.governance import proof_state
from odylith.runtime.governance import sync_casebook_bug_index
from odylith.runtime.governance.proof_state import resolver as proof_state_resolver

projection_entity.bind(context_engine_store.__dict__)
projection_backlog.bind(context_engine_store.__dict__)


def _write_casebook_bug(
    repo_root: Path,
    *,
    filename: str = "2026-04-08-live-proof-state.md",
    title: str = "Live Proof State",
    bug_id: str = "CB-077",
    workstream: str = "B-062",
    lane_id: str = "proof-state-control-plane",
    blocker: str = "Lambda permission lifecycle on ecs-drift-monitor invoke",
    fingerprint: str = "aws:lambda:Permission doesn't support update",
    phase: str = "manifests-deploy",
    clearance: str = "Hosted SIM3 passes beyond manifests-deploy",
    proof_status: str = "diagnosed",
    include_proof_fields: bool = True,
) -> str:
    bug_root = repo_root / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    path = bug_root / filename
    lines = [
        f"# {title}",
        "",
        f"- Bug ID: {bug_id}",
        f"- Linked Workstream: {workstream}",
    ]
    if include_proof_fields:
        lines.extend(
            [
                f"- Proof Lane ID: {lane_id}",
                f"- Current Blocker: {blocker}",
                f"- Failure Fingerprint: {fingerprint}",
                f"- First Failing Phase: {phase}",
                f"- Clearance Condition: {clearance}",
                f"- Current Proof Status: {proof_status}",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path.relative_to(repo_root)).replace("\\", "/")


def _write_plan(repo_root: Path, *, lane_id: str = "proof-state-control-plane", blocker: str = "", phase: str = "", clearance: str = "") -> None:
    plan_root = repo_root / "odylith" / "technical-plans" / "in-progress" / "2026-04"
    plan_root.mkdir(parents=True, exist_ok=True)
    (plan_root / "2026-04-08-proof-state.md").write_text(
        (
            "Status: In progress\n\n"
            "Backlog: B-062\n"
            f"Proof Lane ID: {lane_id}\n"
            f"Current Blocker: {blocker}\n"
            "Failure Fingerprint: aws:lambda:Permission doesn't support update\n"
            f"First Failing Phase: {phase}\n"
            f"Clearance Condition: {clearance}\n"
            "Current Proof Status: diagnosed\n"
        ),
        encoding="utf-8",
    )


def _write_stream_event(repo_root: Path, payload: dict[str, object]) -> None:
    stream_path = repo_root / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _scope() -> dict[str, object]:
    return {
        "scope_key": "workstream:B-062",
        "scope_type": "workstream",
        "scope_id": "B-062",
        "scope_label": "B-062",
        "evidence_context": {
            "linked_workstreams": ["B-062"],
        },
    }


def _bug_scope(*, bug_id: str, source_path: str, workstream: str = "B-062") -> dict[str, object]:
    return {
        "scope_key": f"bug:{bug_id}",
        "scope_type": "bug",
        "scope_id": bug_id,
        "scope_label": bug_id,
        "evidence_context": {
            "linked_workstreams": [workstream],
            "linked_bug_ids": [bug_id],
            "linked_bug_paths": [source_path],
        },
    }


def _write_casebook_index(repo_root: Path) -> None:
    index_path = repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(sync_casebook_bug_index.render_bug_index(repo_root=repo_root), encoding="utf-8")


def test_annotate_scopes_with_proof_state_merges_live_falsification_and_persists_ledger(tmp_path: Path) -> None:
    _write_casebook_bug(tmp_path)
    proof_state.persist_live_proof_lanes(
        repo_root=tmp_path,
        live_proof_lanes={
            "proof-state-control-plane": {
                "lane_id": "proof-state-control-plane",
                "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                "recent_work_categories": ["observability"],
            }
        },
    )
    _write_stream_event(
        tmp_path,
        {
            "ts_iso": "2026-04-08T18:42:00Z",
            "proof_lane": "proof-state-control-plane",
            "proof_fingerprint": "aws:lambda:Permission doesn't support update",
            "proof_phase": "manifests-deploy",
            "proof_status": "falsified_live",
            "evidence_tier": "code_only",
            "work_category": "governance",
            "deployment_truth": {
                "pushed_head": "def456",
                "runner_fingerprint": "runner-v3",
            },
            "workstreams": ["B-062"],
        },
    )

    annotated = proof_state.annotate_scopes_with_proof_state(repo_root=tmp_path, scopes=[_scope()])

    resolved = annotated[0]["proof_state"]
    assert resolved["lane_id"] == "proof-state-control-plane"
    assert resolved["linked_bug_id"] == "CB-077"
    assert resolved["proof_status"] == "falsified_live"
    assert resolved["frontier_phase"] == "manifests-deploy"
    assert resolved["repeated_fingerprint_count"] == 1
    assert resolved["deployment_truth"] == {
        "local_head": "unknown",
        "pushed_head": "def456",
        "published_source_commit": "unknown",
        "runner_fingerprint": "runner-v3",
        "last_live_failing_commit": "def456",
    }
    assert any("Previous fix did not clear the live blocker" in warning for warning in resolved["warnings"])
    assert annotated[0]["claim_guard"]["same_fingerprint_as_last_falsification"] is True

    live_lanes = proof_state.load_live_proof_lanes(repo_root=tmp_path)
    assert live_lanes["proof-state-control-plane"]["repeated_fingerprint_count"] == 1
    assert live_lanes["proof-state-control-plane"]["last_falsification"] == {
        "recorded_at": "2026-04-08T18:42:00Z",
        "failure_fingerprint": "aws:lambda:Permission doesn't support update",
        "frontier_phase": "manifests-deploy",
    }


def test_claim_enforcement_rewrites_unqualified_resolution_terms() -> None:
    claim_lint = proof_state.build_claim_lint(
        {
            "highest_truthful_claim": "fixed in code",
            "blocked_terms": ["fixed", "cleared", "resolved"],
            "hosted_frontier_advanced": False,
            "same_fingerprint_as_last_falsification": True,
            "claim_scope": "code_or_preview",
        }
    )

    enforced = proof_state.enforce_claim_text(
        "The blocker is fixed and resolved.",
        claim_lint=claim_lint,
        surface="test",
    )
    already_qualified = proof_state.enforce_claim_text(
        "The blocker is fixed live.",
        claim_lint=claim_lint,
        surface="test",
    )

    assert enforced["text"] == "The blocker is fixed in code and fixed in code."
    assert set(enforced["blocked_term_hits"]) == {"fixed", "resolved"}
    assert enforced["gate"]["state"] == "rewrite_or_block"
    assert enforced["forced_checks"][0]["answer"] == "yes"
    assert enforced["forced_checks"][1]["answer"] == "no"
    assert enforced["forced_checks"][2]["answer"] == "code_or_preview"
    assert already_qualified["text"] == "The blocker is fixed live."


def test_resolve_scope_collection_proof_state_marks_ambiguous_multiple_lanes() -> None:
    resolved = proof_state.resolve_scope_collection_proof_state(
        [
            {"proof_state": {"lane_id": "lane-a", "current_blocker": "A"}},
            {"proof_state": {"lane_id": "lane-b", "current_blocker": "B"}},
        ]
    )

    assert resolved == {
        "proof_state_resolution": {
            "state": "ambiguous",
            "lane_ids": ["lane-a", "lane-b"],
        }
    }


def test_load_context_dossier_promotes_resolved_proof_state(monkeypatch, tmp_path: Path) -> None:
    class _Connection:
        def close(self) -> None:
            return None

    monkeypatch.setattr(projection_entity, "_warm_runtime", lambda **_: True)
    monkeypatch.setattr(projection_entity, "_connect", lambda _root: _Connection())
    monkeypatch.setattr(
        projection_entity,
        "_resolve_context_entity",
        lambda *_args, **_kwargs: (
            {"kind": "workstream", "entity_id": "B-062", "title": "Proof lane"},
            [],
            {"resolution_mode": "exact"},
        ),
    )
    monkeypatch.setattr(projection_entity, "_odylith_ablation_active", lambda **_: False)
    monkeypatch.setattr(projection_entity, "_relation_rows", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        projection_entity,
        "_related_entities",
        lambda *args, **kwargs: {"workstream": [], "component": [], "diagram": []},
    )
    monkeypatch.setattr(projection_entity, "_recent_context_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        projection_entity,
        "_delivery_context_rows",
        lambda *args, **kwargs: [
            {
                "scope_key": "workstream:B-062",
                "proof_state": {
                    "lane_id": "proof-state-control-plane",
                    "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                    "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                    "frontier_phase": "manifests-deploy",
                    "proof_status": "fixed_in_code",
                },
                "claim_guard": {
                    "highest_truthful_claim": "fixed in code",
                    "blocked_terms": ["fixed", "cleared", "resolved"],
                },
            }
        ],
    )
    monkeypatch.setattr(projection_entity, "record_runtime_timing", lambda **_: None)

    payload = projection_entity.load_context_dossier(
        repo_root=tmp_path,
        ref="B-062",
        kind="workstream",
        runtime_mode="standalone",
    )

    assert payload["proof_state"]["lane_id"] == "proof-state-control-plane"
    assert payload["claim_guard"]["highest_truthful_claim"] == "fixed in code"
    assert payload["proof_state_resolution"] == {
        "state": "resolved",
        "lane_ids": ["proof-state-control-plane"],
    }


def test_annotate_scopes_merges_casebook_and_plan_rows_for_same_lane_with_casebook_precedence(tmp_path: Path) -> None:
    _write_casebook_bug(tmp_path)
    _write_plan(
        tmp_path,
        blocker="Plan fallback blocker text",
        phase="plan-phase",
        clearance="Plan fallback clearance",
    )

    annotated = proof_state.annotate_scopes_with_proof_state(repo_root=tmp_path, scopes=[_scope()])

    resolved = annotated[0]["proof_state"]
    assert resolved["lane_id"] == "proof-state-control-plane"
    assert resolved["current_blocker"] == "Lambda permission lifecycle on ecs-drift-monitor invoke"
    assert resolved["first_failing_phase"] == "manifests-deploy"
    assert resolved["clearance_condition"] == "Hosted SIM3 passes beyond manifests-deploy"
    assert annotated[0]["proof_state_resolution"] == {
        "state": "resolved",
        "lane_ids": ["proof-state-control-plane"],
    }


def test_bug_scope_resolution_prefers_linked_casebook_bug_over_shared_workstream_ambiguity(tmp_path: Path) -> None:
    source_path = _write_casebook_bug(tmp_path)
    _write_casebook_bug(
        tmp_path,
        filename="2026-04-08-other-live-proof-state.md",
        title="Other Live Proof State",
        bug_id="CB-078",
        lane_id="proof-state-control-plane-b",
        blocker="Second blocker on the same workstream",
        fingerprint="aws:lambda:Permission alternate failure",
        clearance="Hosted SIM3 passes beyond alternate phase",
    )

    annotated = proof_state.annotate_scopes_with_proof_state(
        repo_root=tmp_path,
        scopes=[_bug_scope(bug_id="CB-077", source_path=source_path), _scope()],
    )

    assert annotated[0]["proof_state"]["lane_id"] == "proof-state-control-plane"
    assert annotated[0]["proof_state_resolution"] == {
        "state": "resolved",
        "lane_ids": ["proof-state-control-plane"],
    }
    assert "proof_state" not in annotated[1]
    assert annotated[1]["proof_state_resolution"] == {
        "state": "ambiguous",
        "lane_ids": ["proof-state-control-plane", "proof-state-control-plane-b"],
    }


def test_bug_scope_does_not_inherit_other_workstream_lane_without_matching_bug_truth(tmp_path: Path) -> None:
    source_path = _write_casebook_bug(
        tmp_path,
        filename="2026-04-08-untracked-live-proof-state.md",
        title="Untracked Live Proof State",
        bug_id="CB-077",
        include_proof_fields=False,
    )
    _write_casebook_bug(
        tmp_path,
        filename="2026-04-08-other-live-proof-state.md",
        title="Other Live Proof State",
        bug_id="CB-078",
        lane_id="proof-state-control-plane-b",
    )

    annotated = proof_state.annotate_scopes_with_proof_state(
        repo_root=tmp_path,
        scopes=[_bug_scope(bug_id="CB-077", source_path=source_path)],
    )

    assert "proof_state" not in annotated[0]
    assert annotated[0]["proof_state_resolution"] == {
        "state": "none",
        "lane_ids": [],
    }


def test_annotate_scopes_infers_single_live_lane_without_tracked_truth(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(proof_state_resolver, "_current_local_head", lambda _repo_root: "abc123")
    proof_state.persist_live_proof_lanes(
        repo_root=tmp_path,
        live_proof_lanes={
            "proof-state-control-plane": {
                "lane_id": "proof-state-control-plane",
                "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                "first_failing_phase": "manifests-deploy",
                "frontier_phase": "manifests-deploy",
                "proof_status": "fixed_in_code",
                "workstreams": ["B-062"],
                "deployment_truth": {"runner_fingerprint": "runner-v3"},
            }
        },
    )

    annotated = proof_state.annotate_scopes_with_proof_state(repo_root=tmp_path, scopes=[_scope()])

    resolved = annotated[0]["proof_state"]
    assert resolved["lane_id"] == "proof-state-control-plane"
    assert resolved["source"] == "inferred"
    assert resolved["resolution_state"] == "inferred"
    assert resolved["deployment_truth"]["local_head"] == "abc123"
    assert annotated[0]["proof_state_resolution"] == {
        "state": "resolved",
        "lane_ids": ["proof-state-control-plane"],
    }


def test_annotate_scopes_merges_deployment_truth_and_promotes_advanced_frontier_live(monkeypatch, tmp_path: Path) -> None:
    _write_casebook_bug(tmp_path)
    monkeypatch.setattr(proof_state_resolver, "_current_local_head", lambda _repo_root: "abc123")
    proof_state.persist_live_proof_lanes(
        repo_root=tmp_path,
        live_proof_lanes={
            "proof-state-control-plane": {
                "lane_id": "proof-state-control-plane",
                "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                "deployment_truth": {
                    "pushed_head": "def456",
                    "published_source_commit": "fedcba",
                },
                "workstreams": ["B-062"],
            }
        },
    )
    _write_stream_event(
        tmp_path,
        {
            "ts_iso": "2026-04-08T19:15:00Z",
            "proof_lane": "proof-state-control-plane",
            "proof_fingerprint": "aws:lambda:Permission doesn't support update",
            "proof_phase": "post-manifests-smoke",
            "proof_status": "deployed",
            "evidence_tier": "deployed_not_live_verified",
            "deployment_truth": {
                "runner_fingerprint": "runner-v4",
            },
            "workstreams": ["B-062"],
        },
    )

    annotated = proof_state.annotate_scopes_with_proof_state(repo_root=tmp_path, scopes=[_scope()])

    resolved = annotated[0]["proof_state"]
    assert resolved["proof_status"] == "live_verified"
    assert resolved["evidence_tier"] == "live_verified"
    assert resolved["frontier_phase"] == "post-manifests-smoke"
    assert resolved["deployment_truth"] == {
        "local_head": "abc123",
        "pushed_head": "def456",
        "published_source_commit": "fedcba",
        "runner_fingerprint": "runner-v4",
        "last_live_failing_commit": "unknown",
    }
    assert annotated[0]["claim_guard"]["hosted_frontier_advanced"] is True
    assert annotated[0]["claim_guard"]["highest_truthful_claim"] == "fixed live"
    assert annotated[0]["claim_guard"]["blocked_terms"] == []


def test_annotate_scopes_marks_multiple_inferred_live_lanes_ambiguous(tmp_path: Path) -> None:
    proof_state.persist_live_proof_lanes(
        repo_root=tmp_path,
        live_proof_lanes={
            "lane-a": {
                "lane_id": "lane-a",
                "failure_fingerprint": "fingerprint-a",
                "workstreams": ["B-062"],
            },
            "lane-b": {
                "lane_id": "lane-b",
                "failure_fingerprint": "fingerprint-b",
                "workstreams": ["B-062"],
            },
        },
    )

    annotated = proof_state.annotate_scopes_with_proof_state(repo_root=tmp_path, scopes=[_scope()])

    assert "proof_state" not in annotated[0]
    assert annotated[0]["proof_state_resolution"] == {
        "state": "ambiguous",
        "lane_ids": ["lane-a", "lane-b"],
    }


def test_load_bug_snapshot_enriches_rows_with_proof_state_and_claim_guard(tmp_path: Path) -> None:
    _write_casebook_bug(tmp_path)
    _write_casebook_index(tmp_path)
    _write_stream_event(
        tmp_path,
        {
            "ts_iso": "2026-04-08T19:15:00Z",
            "proof_lane": "proof-state-control-plane",
            "proof_fingerprint": "aws:lambda:Permission doesn't support update",
            "proof_phase": "manifests-deploy",
            "proof_status": "fixed_in_code",
            "evidence_tier": "code_only",
            "work_category": "primary_blocker",
            "workstreams": ["B-062"],
        },
    )

    rows = projection_backlog.load_bug_snapshot(repo_root=tmp_path, runtime_mode="standalone")
    bug = next(row for row in rows if row["bug_id"] == "CB-077")

    assert bug["proof_state"]["lane_id"] == "proof-state-control-plane"
    assert bug["proof_state"]["current_blocker"] == "Lambda permission lifecycle on ecs-drift-monitor invoke"
    assert bug["proof_state_resolution"] == {
        "state": "resolved",
        "lane_ids": ["proof-state-control-plane"],
    }
    assert bug["claim_guard"]["highest_truthful_claim"] == "fixed in code"
    assert bug["claim_guard"]["blocked_terms"] == ["fixed", "cleared", "resolved"]


def test_proof_drift_warning_triggers_when_non_primary_work_dominates() -> None:
    state = {
        "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
        "proof_status": "fixed_in_code",
        "recent_work_categories": ["observability", "governance", "test_hardening", "primary_blocker"],
    }

    warning = proof_state.proof_drift_warning(state)

    assert warning == (
        "Recent activity is skewing away from the primary blocker while "
        "Lambda permission lifecycle on ecs-drift-monitor invoke is still open."
    )
    assert warning in proof_state.proof_preview_lines(state)
