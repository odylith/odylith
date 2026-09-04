from __future__ import annotations

import ast
import shlex
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (_ROOT / path).read_text(encoding="utf-8")


def test_greenfield_make_targets_reference_only_live_test_files() -> None:
    commands: dict[str, str] = {}
    target_paths: dict[str, set[Path]] = {}
    for target in ("greenfield-test-fast", "greenfield-test-lifecycle"):
        result = subprocess.run(
            ["make", "-n", target],
            cwd=_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        commands[target] = result.stdout
        target_paths[target] = {
            Path(token)
            for line in result.stdout.splitlines()
            for token in shlex.split(line)
            if token.endswith(".py")
        }

    fast_paths = target_paths["greenfield-test-fast"]
    lifecycle_paths = target_paths["greenfield-test-lifecycle"]
    assert fast_paths
    assert lifecycle_paths
    assert all((_ROOT / path).is_file() for path in fast_paths | lifecycle_paths)
    assert fast_paths.isdisjoint(lifecycle_paths)
    assert '-m "not greenfield_lifecycle"' in commands["greenfield-test-fast"]


def test_greenfield_materiality_has_one_prewrite_owner() -> None:
    materialization = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_model_intent_materialization.py"
    )
    staging = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_candidate_intent_stage.py"
    )
    cli = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_proposals_cli.py"
    )
    clarification = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_material_clarification.py"
    )

    assert not (
        _ROOT
        / "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_transaction_authority.py"
    ).exists()
    assert not (
        _ROOT
        / "src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py"
    ).exists()
    assert len(materialization.splitlines()) < 300
    assert "import re" not in materialization
    assert "intent_hypothesis_from_operator_evidence" not in materialization
    assert "materialize_prompt_intent_hypothesis" not in cli
    assert "greenfield_prompt_intent_materialization" not in cli
    assert "materialize_model_authored_intent" in cli
    assert "restage_compiled_candidate_intent" not in staging
    assert "stage_candidate_intent(" in materialization
    assert "import re" not in clarification
    assert "incomplete_path_clarification" not in clarification
    assert "has_explicit_visible_result" not in clarification
    assert "explicit_material_clarification" not in clarification
    assert "material_clarification_for_fields" in clarification


def test_authored_proposal_api_has_no_relation_free_compatibility_compiler() -> None:
    dispatcher = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_confirmed_proposal.py"
    )
    compatibility_path = (
        _ROOT
        / "src/odylith/runtime/domain_intelligence/greenfield_legacy_proposal_compat.py"
    )
    tree = ast.parse(dispatcher)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert not compatibility_path.exists()
    assert "odylith.runtime.domain_intelligence.greenfield_legacy_proposal_compat" not in imports
    assert "import re" not in dispatcher
    assert "sealed_authored_projection" in dispatcher
    assert "build_legacy_confirmed_greenfield_proposal_compat" not in dispatcher
    assert "build_authored_greenfield_proposal" in dispatcher


def test_greenfield_failed_preconfirm_has_no_quality_debt_escape_hatch() -> None:
    engine = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_engine.py"
    )
    writer = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_compiled_write.py"
    )
    cli = _source("src/odylith/runtime/domain_intelligence/greenfield_cli_output.py")
    preview = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_prewrite_commit_result.py"
    )

    for stale_owner in (
        "PRECONFIRM_COMPLETION_PRIORITY_STATUS",
        "_completion_priority_debt",
        "write_allowed_with_projection_quality_debt",
        "passed_with_quality_debt",
    ):
        assert stale_owner not in engine
    assert "completion_priority_write_policy" not in writer
    assert "_print_completion_quality_debt" not in cli
    assert preview.count("completion_priority_quality_debt") == 1
    assert "contains unresolved quality debt" in preview


def test_authored_projection_has_no_downstream_semantic_owner() -> None:
    projection = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_authored_proposal.py"
    )

    for stale_local_claim in (
        '"owned_state"',
        '"accepted_inputs"',
        '"produced_outputs"',
        '"outside_boundary"',
        '"local_proof"',
        '"upstream_truth"',
        '"downstream_consumers"',
        '"unique_failure"',
        '"kind": "service"',
        "def _security_compliance",
        "--> component1",
        "-. deferred .->",
    ):
        assert stale_local_claim not in projection
    assert '"security_compliance": {}' in projection
    assert len(projection.splitlines()) < 900


def test_retired_preconfirm_probe_graph_stays_deleted() -> None:
    retired_paths = (
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_rescue_probe.py",
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_structured_rescue_proof.py",
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_patchset.py",
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_repair.py",
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_repair_context.py",
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_rescue_planner.py",
        "src/odylith/runtime/domain_intelligence/greenfield_prewrite_projection_rerender.py",
        "scripts/release/greenfield_rescue_smoke.py",
        "tests/unit/runtime/test_greenfield_preconfirm_executable_patchset.py",
        "tests/unit/runtime/test_greenfield_preconfirm_projection_rerender.py",
        "tests/unit/runtime/test_greenfield_semantic_patch_targets.py",
        "tests/unit/runtime/test_greenfield_preconfirm_rescue_probe.py",
        "tests/unit/runtime/test_greenfield_preconfirm_structured_rescue_proof.py",
    )
    active_sources = (
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_engine.py",
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_package_findings.py",
    )
    retired_tokens = (
        "greenfield_preconfirm_rescue_probe",
        "greenfield_preconfirm_structured_rescue_proof",
        "RESCUE_PROBE",
        "STRUCTURED_RESCUE_PROOF",
        "internal_probe_changed",
    )

    assert all(not (_ROOT / path).exists() for path in retired_paths)
    assert not (
        _ROOT
        / "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_patch_apply.py"
    ).exists()
    for source_path in active_sources:
        source = _source(source_path)
        assert all(token not in source for token in retired_tokens)


def test_authored_preconfirm_owner_has_no_legacy_facades_or_repair_callbacks() -> None:
    proposals = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_proposals.py"
    )
    engine = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_engine.py"
    )

    for stale_symbol in (
        "def complete_confirmed_proposal",
        "def complete_greenfield_semantic_apply_payload",
        "def normalize_host_reasoned_proposal",
        "def format_proposal_text",
        "def validate_host_reasoned_proposal",
        "def require_distinct_supplied_diagram_sources",
        "def apply_greenfield_proposal",
        "def _repair_confirmed_apply_payload",
        "def main",
        "assert_greenfield_package_ready",
        "rebound_package",
    ):
        assert stale_symbol not in proposals
    for stale_owner in (
        "greenfield_preconfirm_patch_apply",
        "greenfield_preconfirm_rescue_planner",
        "greenfield_semantic_compiler",
        "repair_proposal",
        "prepare_repair_context",
        "rerender_prewrite",
    ):
        assert stale_owner not in engine
