"""Exact delivery contracts use controlled input; repository ownership stays live."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.evaluation import odylith_benchmark_runner as runner


REPO_ROOT = Path(__file__).resolve().parents[3]
OPERATIONS_DOC = "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"
BENCHMARK_PATHS = [
    "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
    "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
]
MISS_RECOVERY = {
    "active": True,
    "applied": True,
    "mode": "projection_exact_rescue",
}


def _uncompressed_narrowing_packet(*, packet_kind: str, ambiguity: str, paths: list[str]) -> dict:
    """The delivery input explicitly has no selected owner, not a stale repo winner."""
    return {
        "changed_paths": paths,
        "explicit_paths": paths,
        "context_packet_state": "gated_ambiguous",
        "narrowing_guidance": {"required": True, "reason": "selection_ambiguous"},
        "context_packet": {
            "packet_kind": packet_kind,
            "packet_state": "gated_ambiguous",
            "selection_state": "none" if ambiguity == "no_candidates" else "ambiguous",
            "anchors": {
                "changed_paths": paths,
                "explicit_paths": paths,
                "has_non_shared_anchor": True,
            },
            "retrieval_plan": {
                "ambiguity_class": ambiguity,
                "selected_counts": {"commands": 4, "docs": 6, "guidance": 3},
                "guidance_coverage": "direct",
                "evidence_consensus": "mixed",
                "precision_score": 27,
                "miss_recovery": dict(MISS_RECOVERY),
            },
            "route": {"route_ready": False, "narrowing_required": True},
        },
    }


@pytest.fixture
def governance_delivery_input() -> dict:
    payload = _uncompressed_narrowing_packet(
        packet_kind="governance_slice", ambiguity="low_signal", paths=[OPERATIONS_DOC]
    )
    payload["narrowing_guidance"]["reason"] = "Need one code or contract path."
    payload["validation_bundle"] = {
        "strict_gate_commands": ["odylith validate plan-bindings --repo-root ."],
        "plan_binding_required": True,
        "governed_surface_sync_required": True,
    }
    # B-002 is an input owner for this codec contract, not inferred current-repo truth.
    payload["governance_obligations"] = {
        "touched_workstreams": [{"entity_id": "B-002"}],
        "touched_components": [{"entity_id": "odylith"}],
        "closeout_docs": [OPERATIONS_DOC],
    }
    payload["surface_refs"] = {
        "impacted_surfaces": dict.fromkeys(("radar", "registry", "atlas", "casebook", "compass"), True)
    }
    assert payload["governance_obligations"]["touched_workstreams"] == [{"entity_id": "B-002"}]
    assert payload["context_packet"]["retrieval_plan"]["selected_counts"] == {
        "commands": 4, "docs": 6, "guidance": 3,
    }
    assert len(payload["surface_refs"]["impacted_surfaces"]) == 5
    return payload


def test_governance_slice_hot_path_limits_operator_payload_lists(governance_delivery_input: dict) -> None:
    original = deepcopy(governance_delivery_input)
    payload = store._compact_hot_path_runtime_packet(  # noqa: SLF001
        packet_kind="governance_slice", payload=governance_delivery_input
    )
    context_packet = dict(payload["context_packet"])
    narrowing_guidance = dict(payload["narrowing_guidance"])
    governance_signal = governance_signal_codec.expand_governance_signal(dict(context_packet["route"]["governance"]))

    assert governance_delivery_input == original
    assert sorted(payload.keys()) == ["changed_paths", "context_packet", "narrowing_guidance"]
    assert payload.get("routing_handoff") is None
    assert payload.get("packet_metrics") is None
    assert payload.get("validation_bundle") is None
    assert payload.get("governance_obligations") is None
    assert payload.get("surface_refs") is None
    assert payload["changed_paths"] == governance_delivery_input["changed_paths"][:5]
    assert governance_signal["strict_gate_command_count"] == 1
    assert governance_signal["plan_binding_required"] is True
    assert governance_signal["governed_surface_sync_required"] is True
    assert governance_signal["closeout_doc_count"] >= 1
    assert governance_signal["primary_workstream_id"] == "B-002"
    assert governance_signal["primary_component_id"] == "odylith"
    assert governance_signal["surface_count"] == 5
    assert narrowing_guidance == {"required": True, "reason": "Need one code or contract path."}
    assert context_packet["anchors"].get("explicit_paths") is None
    assert context_packet["anchors"]["has_non_shared_anchor"] is True
    assert context_packet["retrieval_plan"]["selected_counts"] == "c4d6g3"
    assert context_packet["retrieval_plan"]["guidance_coverage"] == "direct"
    assert context_packet.get("execution_profile") is None
    assert context_packet["route"].get("native_spawn_ready") is None
    assert context_packet["route"].get("reasoning_bias") is None
    assert context_packet["route"].get("parallelism_hint") is None


def test_governance_slice_hot_path_compacts_embedded_governance_keys(governance_delivery_input: dict) -> None:
    payload = store._compact_hot_path_runtime_packet(  # noqa: SLF001
        packet_kind="governance_slice", payload=governance_delivery_input
    )
    governance_signal = dict(payload["context_packet"]["route"]["governance"])

    assert governance_signal["sg"] == 1
    assert governance_signal["pb"] is True
    assert governance_signal["gs"] is True
    assert governance_signal["cd"] >= 1
    assert governance_signal["w"] == "B-002"
    assert governance_signal["c"] == "odylith"
    assert governance_signal["sf"] == 5
    assert "strict_gate_command_count" not in governance_signal
    assert "primary_workstream_id" not in governance_signal


def test_ambiguous_session_brief_keeps_fallback_recommendation_without_bug_result_paths() -> None:
    source = _uncompressed_narrowing_packet(
        packet_kind="session_brief", ambiguity="low_signal", paths=[OPERATIONS_DOC]
    )
    source["full_scan_recommended"] = True
    source["fallback_scan"] = {
        "recommended": True,
        "reason": "adaptive_full_scan_fallback",
        "performed": True,
        "results": [{"path": "odylith/casebook/bugs/controlled-fallback-hit.md", "kind": "bug"}],
    }
    assert source["context_packet"]["selection_state"] == "ambiguous"
    assert source["fallback_scan"]["results"][0]["kind"] == "bug"
    payload = store._compact_hot_path_runtime_packet(  # noqa: SLF001
        packet_kind="session_brief", payload=source
    )

    assert payload["fallback_scan"] == {
        "recommended": True,
        "reason": "adaptive_full_scan_fallback",
        "performed": True,
    }
    assert not any(path.startswith("odylith/casebook/bugs/") for path in runner._observed_packet_paths(payload))  # noqa: SLF001


def test_session_brief_exact_path_hot_path_keeps_only_live_narrowing_signal() -> None:
    source = _uncompressed_narrowing_packet(
        packet_kind="session_brief", ambiguity="no_candidates", paths=[OPERATIONS_DOC]
    )
    assert source["context_packet"]["selection_state"] == "none"
    assert source["context_packet"]["retrieval_plan"]["ambiguity_class"] == "no_candidates"
    payload = store._compact_hot_path_runtime_packet(  # noqa: SLF001
        packet_kind="session_brief", payload=source
    )
    context_packet = dict(payload["context_packet"])

    assert context_packet.get("packet_kind") is None
    assert context_packet.get("execution_profile") is None
    assert context_packet.get("optimization") is None
    assert context_packet.get("selection_state") is None
    assert context_packet["retrieval_plan"] == {
        "ambiguity_class": "no_candidates",
        "miss_recovery": {"active": True, "applied": True, "mode": "projection_exact_rescue"},
    }
    assert context_packet["route"] == {
        "narrowing_required": True, "b": "guarded_narrowing", "p": "serial_guarded",
    }
    assert payload["narrowing_guidance"] == {"required": True, "reason": "Need one code path."}


def test_architecture_hot_path_drops_ambiguous_count_scaffolding() -> None:
    source = _uncompressed_narrowing_packet(
        packet_kind="impact", ambiguity="low_signal", paths=BENCHMARK_PATHS
    )
    assert source["context_packet"]["selection_state"] == "ambiguous"
    assert source["context_packet"]["retrieval_plan"]["selected_counts"]
    payload = store._compact_hot_path_runtime_packet(packet_kind="impact", payload=source)  # noqa: SLF001
    context_packet = dict(payload["context_packet"])
    retrieval_plan = dict(context_packet["retrieval_plan"])

    assert context_packet.get("selection_state") is None
    assert retrieval_plan.get("selected_counts") is None
    assert retrieval_plan["ambiguity_class"] == "low_signal"
    assert retrieval_plan["miss_recovery"] == {"active": True, "applied": True, "mode": "projection_exact_rescue"}
    assert context_packet["anchors"]["changed_paths"] == BENCHMARK_PATHS
    assert context_packet["route"] == {"narrowing_required": True}


def test_packet_level_architecture_audit_keeps_doc_only_slice_grounded() -> None:
    # Graph construction is independently checked below against live source truth.
    edges = [
        {"source": OPERATIONS_DOC, "target": "odylith", "kind": "component"},
        {"source": OPERATIONS_DOC, "target": "B-002", "kind": "traceability"},
    ]
    source = {
        "resolved": True,
        "changed_paths": [OPERATIONS_DOC],
        "coverage": {"confidence_tier": "medium", "support_paths": [OPERATIONS_DOC]},
        "authority_graph": {
            "edges": edges,
            "counts": {
                "edges": len(edges),
                "traceability_edges": sum(edge["kind"] == "traceability" for edge in edges),
            },
        },
        "execution_hint": {"mode": "local_grounding_first", "fanout": "no_fanout", "risk_tier": "moderate"},
        "contract_touchpoint_count": 2,
        "validation_obligation_count": 2,
    }
    assert source["authority_graph"]["counts"] == {"edges": 2, "traceability_edges": 1}
    payload = store._compact_packet_level_architecture_audit(source)  # noqa: SLF001

    assert payload == {
        "resolved": True,
        "changed_paths": [OPERATIONS_DOC],
        "coverage": {"confidence_tier": "medium"},
        "authority_graph": {"counts": {"edges": 2, "traceability_edges": 1}},
        "execution_hint": {"mode": "local_grounding_first", "fanout": "no_fanout", "risk_tier": "moderate"},
        "contract_touchpoint_count": 2,
        "validation_obligation_count": 2,
    }


@pytest.mark.parametrize("scenario_id, delivery_companions", [
    ("compass-refresh-queued-state-recovery", []),
    (
        "architecture-benchmark-honest-baseline-contract",
        ["docs/benchmarks/REVIEWER_GUIDE.md"],
    ),
])
def test_current_repo_exact_code_selection_retains_grounded_owner(
    scenario_id: str, delivery_companions: list[str]
) -> None:
    scenario = next(row for row in runner.load_benchmark_scenarios(repo_root=REPO_ROOT) if row["scenario_id"] == scenario_id)
    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT, scenario=scenario, mode="odylith_on", existing_paths=scenario["changed_paths"]
    )
    impact = store.build_impact_report(
        repo_root=REPO_ROOT,
        changed_paths=scenario["changed_paths"],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint=scenario["family"],
        intent=scenario.get("intent", ""),
        retain_hot_path_internal_context=True,
        finalize_packet=False,
    )
    selection = impact["workstream_selection"]
    assert selection["state"] == "inferred_confident"
    selected = selection["selected_workstream"]
    evidence = selected["evidence"]
    assert evidence["counters"]["trace_code_exact"] >= 1
    assert evidence["strong_signal_count"] >= 1
    assert any(
        path.startswith("src/") and path in scenario["changed_paths"] and (REPO_ROOT / path).is_file()
        for path in evidence["matched_paths"]
    )
    assert packet_source == "impact"
    assert payload["context_packet"]["selection_state"] == f"i:{selected['entity_id']}"
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001
    assert not any(path.startswith("odylith/casebook/bugs/") for path in observed_paths)
    # The runner review guide is an existing delivery companion, independent of
    # workstream traceability; do not mistake it for a newly inferred owner.
    declared_paths = set(
        scenario["changed_paths"] + scenario["required_paths"] + scenario["supporting_paths"] + delivery_companions
    )
    assert set(observed_paths) <= declared_paths
    assert set(delivery_companions) <= set(observed_paths)
    assert all((REPO_ROOT / path).is_file() for path in observed_paths)
    assert len(payload.get("docs", [])) <= 4


@pytest.mark.parametrize("scenario_id, expected_source", [
    ("closeout-surface-path-normalization", "governance_slice"),
    ("session-brief-runtime-path-ambiguity", "session_brief"),
])
def test_current_repo_shared_runbook_still_requires_narrowing(scenario_id: str, expected_source: str) -> None:
    scenario = next(row for row in runner.load_benchmark_scenarios(repo_root=REPO_ROOT) if row["scenario_id"] == scenario_id)
    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT, scenario=scenario, mode="odylith_on", existing_paths=scenario["changed_paths"]
    )
    assert packet_source == expected_source
    assert payload["narrowing_guidance"]["required"] is True
    assert payload["context_packet"]["route"]["narrowing_required"] is True
    assert not store._hot_path_route_ready(payload)  # noqa: SLF001
    assert store._hot_path_workstream_selection(payload).get("state") not in {"explicit", "inferred_confident"}  # noqa: SLF001


def test_current_repo_doc_architecture_packet_preserves_live_graph_counts() -> None:
    full = store.build_architecture_audit(
        repo_root=REPO_ROOT, changed_paths=[OPERATIONS_DOC], runtime_mode="local", detail_level="compact"
    )
    packet = store.build_architecture_audit(
        repo_root=REPO_ROOT, changed_paths=[OPERATIONS_DOC], runtime_mode="local", detail_level="packet"
    )
    assert full["resolved"] is True
    assert packet["resolved"] is True
    assert packet["changed_paths"] == [OPERATIONS_DOC]
    assert packet["authority_graph"]["counts"] == {
        key: full["authority_graph"]["counts"][key] for key in ("edges", "traceability_edges")
    }
    assert packet["authority_graph"]["counts"]["traceability_edges"] >= 1
    assert packet["execution_hint"] == {
        "mode": "local_grounding_first", "fanout": "no_fanout", "risk_tier": "moderate",
    }
