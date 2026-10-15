"""Structural ownership contracts for Odylith runtime modules."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CHATTER_FRAGMENTS = (
    "Odylith kept",
    "Odylith control advisories",
    "Odylith self-evaluation",
    "odylith runtime ",
    "The Odylith runtime handoff",
    "The retained Odylith packet",
    "recent Odylith ",
)


def test_runtime_orchestration_templates_stay_debranded() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_runtime_signals.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_assessment_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_runtime_policy.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for fragment in RUNTIME_CHATTER_FRAGMENTS:
            assert fragment not in text, f"runtime chatter remains in {path.relative_to(ROOT)}: {fragment!r}"


def test_runtime_user_facing_reason_templates_stay_task_first() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_runtime_signals.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_runtime_policy.py",
    )
    fragments = (
        "current runtime handoff",
        "retained context packet",
        "hold-local or serial execution",
        "packetizer alignment is drifting",
        "odylith ceiling kept",
        "odylith execution profile aligned",
        "odylith execution priors influenced",
        "odylith_execution=",
        "odylith_mode=",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment not in text, f"user-facing runtime template drifted in {path.relative_to(ROOT)}: {fragment!r}"


def test_subagent_router_runtime_policy_no_longer_uses_bind_shims() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_runtime_policy.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "def bind(" not in text, f"router bind shim resurfaced in {path.relative_to(ROOT)}"
        assert "globals().update(" not in text, f"router globals injection resurfaced in {path.relative_to(ROOT)}"


def test_subagent_orchestrator_runtime_no_longer_uses_bind_shims() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_local_gates.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_odylith_runtime.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "def bind(" not in text, f"orchestrator bind shim resurfaced in {path.relative_to(ROOT)}"
        assert "globals().update(" not in text, f"orchestrator globals injection resurfaced in {path.relative_to(ROOT)}"
        assert ".bind(sys.modules[__name__])" not in text, f"orchestrator host bind call resurfaced in {path.relative_to(ROOT)}"


def test_context_engine_runtime_extracts_do_not_rebind_store_hosts() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_projection_compiler_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_grounding_runtime.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "def _host():" not in text, f"store-host shim resurfaced in {path.relative_to(ROOT)}"
        assert "host = _host()" not in text, f"store-host rebinding resurfaced in {path.relative_to(ROOT)}"


def test_context_engine_packet_extracts_use_direct_support_owners() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_packet_summary_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_packet_architecture_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_projection_registry_runtime.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "def bind(host: Any) -> None:" not in text, f"packet bind shim resurfaced in {path.relative_to(ROOT)}"
        assert "_HOST_BIND_NAMES" not in text, f"packet host bind list resurfaced in {path.relative_to(ROOT)}"
        assert "projection_runtime_bindings" not in text, f"generic projection binder resurfaced in {path.relative_to(ROOT)}"


def test_context_engine_bind_shims_are_eliminated_from_remaining_extracts() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_hot_path_delivery_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_hot_path_governance_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_hot_path_packet_bootstrap_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_hot_path_packet_core_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_hot_path_packet_finalize_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_hot_path_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_hot_path_scope_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_memory_snapshot_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_packet_adaptive_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_packet_session_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_projection_backlog_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_projection_entity_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_projection_query_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_projection_search_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_runtime_learning_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_packet_builder.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_packet_completion.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_packet_context_views.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_packet_preflight.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "def bind(host: Any) -> None:" not in text, f"bind shim resurfaced in {path.relative_to(ROOT)}"
        assert "_HOST_BIND_NAMES" not in text, f"host bind list resurfaced in {path.relative_to(ROOT)}"
        assert "globals().update({" not in text, f"globals injection resurfaced in {path.relative_to(ROOT)}"
        assert "def _store():" not in text, f"store shim resurfaced in {path.relative_to(ROOT)}"
        assert "class _Store" not in text, f"store proxy resurfaced in {path.relative_to(ROOT)}"
        assert "_LazyModuleProxy" not in text, f"lazy module proxy resurfaced in {path.relative_to(ROOT)}"


def test_runtime_learning_runtime_does_not_shadow_numeric_helper_owners() -> None:
    path = (
        ROOT
        / "src"
        / "odylith"
        / "runtime"
        / "context_engine"
        / "odylith_context_engine_runtime_learning_runtime.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "\n    def _safe_float(" not in text, "nested _safe_float helper resurfaced in runtime learning runtime"
    assert "\n    def _safe_int(" not in text, "nested _safe_int helper resurfaced in runtime learning runtime"


def test_selected_runtime_consumers_use_direct_snapshot_owners() -> None:
    runtime_learning_path = (
        ROOT
        / "src"
        / "odylith"
        / "runtime"
        / "context_engine"
        / "odylith_context_engine_runtime_learning_runtime.py"
    )
    runtime_learning_text = runtime_learning_path.read_text(encoding="utf-8")
    assert "def load_runtime_memory_snapshot(" not in runtime_learning_text

    direct_owner_expectations = {
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine.py": (
            "store.load_runtime_optimization_snapshot(",
            "store.load_runtime_evaluation_snapshot(",
            "store.load_runtime_memory_snapshot(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_runtime_surface_summary.py": (
            "odylith_context_engine_store.load_runtime_optimization_snapshot(",
            "odylith_context_engine_store.load_runtime_evaluation_snapshot(",
            "odylith_context_engine_store.load_runtime_memory_snapshot(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_packet_session_runtime.py": (
            "context_engine_store.load_runtime_optimization_snapshot(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_delivery_surface_payload_runtime.py": (
            "runtime_learning_runtime.load_runtime_memory_snapshot(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_memory_snapshot_runtime.py": (
            "context_engine_store.load_runtime_optimization_snapshot(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py": (
            "store.load_runtime_optimization_snapshot(",
            "store.load_runtime_evaluation_snapshot(",
            "store.load_runtime_memory_snapshot(",
        ),
    }
    for path, banned_fragments in direct_owner_expectations.items():
        text = path.read_text(encoding="utf-8")
        for fragment in banned_fragments:
            assert fragment not in text, f"snapshot-owner alias wall resurfaced in {path.relative_to(ROOT)}: {fragment}"


def test_benchmark_runner_uses_runtime_posture_owner_directly() -> None:
    runner_path = (
        ROOT
        / "src"
        / "odylith"
        / "runtime"
        / "evaluation"
        / "odylith_benchmark_runner.py"
    )
    runner_text = runner_path.read_text(encoding="utf-8")
    assert "def _runtime_posture_summary(" not in runner_text
    assert "def _prime_benchmark_runtime_cache(" not in runner_text
    assert "benchmark_runtime_posture_runtime.runtime_posture_summary(" in runner_text
    assert "benchmark_runtime_posture_runtime.prime_benchmark_runtime_cache(" in runner_text


def test_session_brief_runtime_uses_dossier_compaction_owner_directly() -> None:
    path = (
        ROOT
        / "src"
        / "odylith"
        / "runtime"
        / "context_engine"
        / "odylith_context_engine_packet_session_runtime.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "dossier_compaction_runtime.compact_context_dossier_for_delivery(" in text
    assert "context_engine_store._compact_context_dossier(" not in text


def test_context_engine_legacy_binding_modules_are_deleted() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_hot_path_packet_bindings.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_packet_runtime_bindings.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_projection_runtime_bindings.py",
    )
    for path in paths:
        assert not path.exists(), f"legacy binding module survived cleanup: {path.relative_to(ROOT)}"


def test_runtime_store_shims_are_not_reintroduced_outside_context_engine() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_refresh_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "sync_workstream_artifacts.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "def _context_engine_store():" not in text, f"context-engine store shim resurfaced in {path.relative_to(ROOT)}"


def test_runtime_artifact_and_daemon_owners_stay_direct_in_selected_consumers() -> None:
    direct_owner_expectations = {
        ROOT / "src" / "odylith" / "install" / "repair.py": (
            "from odylith.runtime.context_engine import odylith_context_engine_runtime_artifacts",
            "odylith_context_engine_runtime_artifacts.sessions_root(",
            "odylith_context_engine_runtime_artifacts.stop_path(",
            "odylith_context_engine_store.sessions_root(",
            "odylith_context_engine_store.stop_path(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "update_compass.py": (
            "from odylith.runtime.context_engine import odylith_context_engine_runtime_artifacts",
            "odylith_context_engine_runtime_artifacts.append_runtime_event(",
            "odylith_context_engine_store.append_runtime_event(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_refresh_runtime.py": (
            "from odylith.runtime.context_engine import odylith_context_engine_workspace_daemon",
            "odylith_context_engine_workspace_daemon.runtime_daemon_transport(",
            "odylith_context_engine_store.runtime_daemon_transport(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "render_compass_dashboard.py": (
            "from odylith.runtime.context_engine import odylith_context_engine_workspace_daemon",
            "odylith_context_engine_workspace_daemon.runtime_daemon_transport(",
            "odylith_context_engine_workspace_daemon.request_runtime_daemon(",
            "from odylith.runtime.context_engine import odylith_context_engine_store",
            "odylith_context_engine_store.runtime_daemon_transport(",
            "odylith_context_engine_store.request_runtime_daemon(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "render_tooling_dashboard.py": (
            "from odylith.runtime.context_engine import odylith_context_engine_runtime_artifacts",
            "odylith_context_engine_runtime_artifacts.state_js_path(",
            "odylith_context_engine_runtime_artifacts.ensure_state_js_probe_asset(",
            "odylith_context_engine_store.state_js_path(",
            "odylith_context_engine_store.ensure_state_js_probe_asset(",
        ),
    }
    for path, expectations in direct_owner_expectations.items():
        text = path.read_text(encoding="utf-8")
        required = expectations[: len(expectations) // 2] if path.name == "render_compass_dashboard.py" else ()
        forbidden = ()
        if path.name == "repair.py":
            required = expectations[:3]
            forbidden = expectations[3:]
        elif path.name == "update_compass.py":
            required = expectations[:2]
            forbidden = expectations[2:]
        elif path.name == "compass_refresh_runtime.py":
            required = expectations[:2]
            forbidden = expectations[2:]
        elif path.name == "render_compass_dashboard.py":
            required = expectations[:3]
            forbidden = expectations[3:]
        elif path.name == "render_tooling_dashboard.py":
            required = expectations[:3]
            forbidden = expectations[3:]
        for token in required:
            assert token in text, f"direct owner token missing in {path.relative_to(ROOT)}: {token}"
        for token in forbidden:
            assert token not in text, f"store reach-through resurfaced in {path.relative_to(ROOT)}: {token}"


def test_selected_runtime_extracts_do_not_rebind_host_modules() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_code_graph_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_engineering_notes_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_projection_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_runtime_signals.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_subtasks_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_assessment_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "backlog_traceability_paths.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "backlog_rich_text.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "backlog_detail_pages.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_outcome_digest_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_runtime_payload_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_standup_fact_packets.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "render_backlog_ui_html_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "render_backlog_ui_payload_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_execution_focus_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_transaction_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_window_update_index.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "def _host():" not in text, f"host shim resurfaced in {path.relative_to(ROOT)}"
        assert "host = _host()" not in text, f"host rebinding resurfaced in {path.relative_to(ROOT)}"


def test_runtime_tree_has_no_host_rebinding_shims() -> None:
    for path in sorted((ROOT / "src" / "odylith" / "runtime").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "def _host():" not in text, f"host shim resurfaced in {path.relative_to(ROOT)}"
        assert "host = _host()" not in text, f"host rebinding resurfaced in {path.relative_to(ROOT)}"


def test_compass_extracts_use_direct_support_owners() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_outcome_digest_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_standup_fact_packets.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_window_update_index.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "compass_dashboard_runtime" not in text, f"dashboard-runtime reach-through resurfaced in {path.relative_to(ROOT)}"


def test_selected_hot_paths_use_common_value_coercion_helpers() -> None:
    local_helper_bans = {
        ROOT / "src" / "odylith" / "runtime" / "discipline" / "runtime.py": ("def _mapping(",),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "execution_engine_handshake.py": ("def _mapping(",),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_runtime_surface_summary.py": ("def _mapping(",),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_quality.py": ("def _int_value(",),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_retrieval.py": ("def _int_value(",),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_routing.py": (
            "def _int_value(",
            "def _dedupe_strings(",
            "def _normalized_string_list(",
            "def _count_or_list_len(",
            "def _fallback_anchor_commands(",
            "def _fallback_scan_commands(",
            "def _truncate(",
            "def _routing_validation_bundle(",
            "def _routing_governance_obligations(",
            "def build_narrowing_guidance(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_budgeting.py": ("def _int_value(", "def _mapping_value("),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_packet_context_views.py": (
            "def _mapping_value(",
            "def _string_rows(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_packet_preflight.py": (
            "def _int_value(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "tooling_context_retrieval.py": (
            "def _int_value(",
            "def _dedupe_strings(",
            "def _string_list(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py": ("def _mapping(",),
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_live_diagnostics.py": (
            "def _dedupe_strings(",
            "def _string_rows(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_live_prompt.py": (
            "def _dedupe_strings(",
            "def _string_rows(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_prompt_payloads.py": (
            "def _dedupe_strings(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_shard_merge.py": ("def _mapping(",),
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_evaluation_ledger.py": (
            "def _int_value(",
            "def _mapping_value(",
            "def _float_value(",
            "def _string_list(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "common" / "host_runtime.py": ("def _normalize_token(",),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "path_bundle_codec.py": ("def _string_rows(",),
        ROOT / "src" / "odylith" / "runtime" / "context_engine" / "session_bootstrap_payload_compactor.py": ("def _string_rows(",),
        ROOT / "src" / "odylith" / "runtime" / "governance" / "guidance_behavior_runtime.py": ("def _mapping(",),
        ROOT / "src" / "odylith" / "runtime" / "governance" / "guidance_behavior_runtime_contracts.py": ("def _dedupe_strings(",),
        ROOT / "src" / "odylith" / "runtime" / "governance" / "proof_state" / "contract.py": ("def _normalize_token(",),
        ROOT / "src" / "odylith" / "runtime" / "governance" / "proof_state" / "enforcement.py": ("def _normalize_string(",),
        ROOT / "src" / "odylith" / "runtime" / "governance" / "proof_state" / "resolver.py": ("def _normalize_token(",),
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "conversation_runtime.py": (
            "def _normalize_string(",
            "def _normalize_token(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "memory" / "tooling_memory_contracts.py": ("def _string_rows(",),
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_support.py": (
            "def _float_value(",
            "def _dedupe_strings(",
            "def _normalize_list(",
            "def _normalize_context_signals(",
            "def _mapping_lookup(",
            "def _nested_mapping(",
            "def _normalized_rate(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator.py": ("def _int_value(",),
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_local_gates.py": ("def _int_value(",),
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_context_support.py": (
            "def _int_value(",
            "def _dedupe_strings(",
            "def _normalize_string(",
            "def _normalize_token(",
            "def _normalize_list(",
            "def _normalize_context_signals(",
            "def _mapping_value(",
            "def _context_lookup(",
            "def _normalized_rate(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router.py": (
            "def _int_value(",
            "def _normalize_list(",
            "def _normalize_context_signals(",
            "def _mapping_value(",
            "def _context_lookup(",
            "def _normalized_rate(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_execution_engine_runtime.py": (
            "def _context_lookup(",
        ),
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_standup_brief_batch.py": ("def _mapping(",),
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_standup_brief_substrate.py": ("def _mapping(",),
    }
    for path, banned_fragments in local_helper_bans.items():
        text = path.read_text(encoding="utf-8")
        assert "from odylith.runtime.common.value_coercion import " in text
        for fragment in banned_fragments:
            assert fragment not in text, f"duplicate coercion helper resurfaced in {path.relative_to(ROOT)}: {fragment}"


def test_selected_runtime_and_install_slices_use_shared_json_release_and_severity_owners() -> None:
    json_owner_paths = (
        ROOT / "src" / "odylith" / "runtime" / "governance" / "guidance_behavior_benchmark_contracts.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "validate_guidance_behavior.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "validate_discipline.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "release_truth_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "tooling_dashboard_surface_status.py",
        ROOT / "src" / "odylith" / "install" / "release_assets.py",
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "engine.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_dashboard_base.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "host_intervention_status.py",
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "benchmark_snapshot_fallbacks.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "proof_state" / "ledger.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "delivery_intelligence_engine.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_standup_brief_maintenance.py",
    )
    for path in json_owner_paths:
        text = path.read_text(encoding="utf-8")
        assert "from odylith.common.json_objects import " in text
        if path.name in {"validate_guidance_behavior.py", "validate_discipline.py"}:
            assert "json.loads(path.read_text" not in text
        if path.name == "guidance_behavior_benchmark_contracts.py":
            assert "def _read_json_object(" in text
        if path.name in {"release_truth_runtime.py", "tooling_dashboard_surface_status.py"}:
            assert "load_json_object as _read_json_object" in text
            assert "def _read_json_object(" not in text
        if path.name in {
            "engine.py",
            "compass_dashboard_base.py",
            "host_intervention_status.py",
            "benchmark_snapshot_fallbacks.py",
            "ledger.py",
            "delivery_intelligence_engine.py",
            "compass_standup_brief_maintenance.py",
        }:
            assert 'json.loads(path.read_text(encoding="utf-8"))' not in text
        if path.name in {
            "engine.py",
            "compass_dashboard_base.py",
            "host_intervention_status.py",
            "benchmark_snapshot_fallbacks.py",
            "compass_standup_brief_maintenance.py",
        }:
            assert "def _load_json(" not in text

    release_text_paths = (
        ROOT / "src" / "odylith" / "install" / "release_assets.py",
        ROOT / "src" / "odylith" / "runtime" / "release_notes.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "version_truth.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "tooling_dashboard_release_presenter.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "shell_onboarding.py",
    )
    for path in release_text_paths:
        text = path.read_text(encoding="utf-8")
        assert "from odylith.common.release_text import " in text
    for path in (
        ROOT / "src" / "odylith" / "runtime" / "release_notes.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "tooling_dashboard_release_presenter.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "shell_onboarding.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert 're.sub(r"\\[([^\\]]+)\\]\\([^)]+\\)", r"\\1", token)' not in text
        assert 're.sub(r"<[^>]+>", "", token)' not in text

    severity_paths = (
        ROOT / "src" / "odylith" / "runtime" / "governance" / "validate_guidance_behavior.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "validate_discipline.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "guidance_behavior_runtime.py",
    )
    for path in severity_paths:
        text = path.read_text(encoding="utf-8")
        assert "from odylith.contracts.severity import " in text
    validate_guidance_text = severity_paths[0].read_text(encoding="utf-8")
    validate_discipline_text = severity_paths[1].read_text(encoding="utf-8")
    runtime_text = severity_paths[2].read_text(encoding="utf-8")
    assert "_VALID_SEVERITIES = {" not in validate_guidance_text
    assert "VALID_SEVERITIES = {" not in validate_discipline_text
    assert "validate_guidance_behavior._VALID_SEVERITIES" not in runtime_text


def test_benchmark_mode_normalization_uses_shared_owner() -> None:
    owner_path = ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_mode.py"
    owner_text = owner_path.read_text(encoding="utf-8")
    assert '"odylith_off": "raw_agent_baseline"' in owner_text

    for path in (
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py",
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_live_execution.py",
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_live_prompt.py",
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_graphs.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "from odylith.runtime.evaluation import odylith_benchmark_mode" in text
        assert 'if token == "odylith_off":' not in text
    graphs_text = (
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_graphs.py"
    ).read_text(encoding="utf-8")
    assert "def _normalize_mode(" not in graphs_text


def test_compass_runtime_payload_uses_window_summary_support_owner() -> None:
    path = ROOT / "src" / "odylith" / "runtime" / "surfaces" / "compass_runtime_payload_runtime.py"
    text = path.read_text(encoding="utf-8")
    assert "from odylith.runtime.surfaces import compass_window_summary_support" in text
    assert "compass_window_summary_support.CompassWindowSummaryContext(" in text
    assert "compass_window_summary_support.summarize_window(" in text
    for fragment in (
        "class _CompassWindowSummary:",
        "class _CompassWindowSummaryContext:",
        "def _cached_window_events(",
        "def _cached_window_transactions(",
        "def _cached_recent_completed_rows(",
        "def _summarize_window(",
    ):
        assert fragment not in text, f"window-summary owner drift resurfaced in {path.relative_to(ROOT)}: {fragment}"


def test_router_assessment_runtime_uses_execution_engine_owner_and_avoids_local_signal_walls() -> None:
    path = ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_assessment_runtime.py"
    text = path.read_text(encoding="utf-8")
    assert "from odylith.runtime.orchestration import subagent_router_signal_summary" in text
    assert "from odylith.runtime.orchestration import subagent_router_assessment_context" in text
    assert "request_with_consumer_write_policy = signal_summary.request_with_consumer_write_policy" in text
    assert "_context_signal_summary = signal_summary._context_signal_summary" in text
    assert "subagent_router_assessment_context.AssessmentState(" in text
    assert "subagent_router_assessment_context.apply_context_signal_adjustments(" in text
    for fragment in (
        "def _bool_value(",
        "def _preferred_value(",
        "def request_with_consumer_write_policy(",
        "def _context_signal_summary(",
        "request_with_consumer_write_policy = subagent_router_signal_summary.request_with_consumer_write_policy",
        "_context_signal_summary = subagent_router_signal_summary._context_signal_summary",
        "_normalize_string = ",
        "_normalize_list = ",
        "_normalize_token = ",
        "_clamp_score = ",
        "_keyword_score = ",
        "_contains_any = ",
        "_router_profile_from_token = ",
    ):
        assert fragment not in text, f"router assessment local signal wall resurfaced in {path.relative_to(ROOT)}"

    support_path = ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_signal_summary.py"
    support_text = support_path.read_text(encoding="utf-8")
    assert "execution_engine_summary_from_context_sources(" in support_text
    assert "router_execution_engine_fields(" in support_text

    context_path = ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_assessment_context.py"
    context_text = context_path.read_text(encoding="utf-8")
    assert "class AssessmentState:" in context_text
    assert "def apply_context_signal_adjustments(" in context_text
    assert "scores = state" in context_text
    for fragment in (
        "def bind(host: Any) -> None:",
        "_HOST_BIND_NAMES",
        "globals().update(",
        "ambiguity = state.ambiguity",
        "blast_radius = state.blast_radius",
        "coordination_cost = state.coordination_cost",
        "requested_depth = state.requested_depth",
        "accuracy_bias = state.accuracy_bias",
    ):
        assert fragment not in context_text, f"router assessment context regressed into host-binding sludge in {context_path.relative_to(ROOT)}"
