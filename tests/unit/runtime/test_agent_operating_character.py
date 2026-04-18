from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.character import contract
from odylith.runtime.character import support
from odylith.runtime.character.cli import run_character
from odylith.runtime.character.decision import evaluate_character_move
from odylith.runtime.character import runtime as character_runtime


def test_character_blocks_completion_claim_without_fresh_proof() -> None:
    decision = evaluate_character_move(intent="Say it is fixed now.")

    assert decision["contract"] == contract.CHARACTER_CONTRACT
    assert decision["decision"] == "block"
    assert "fresh_proof_completion" in decision["forbidden_moves"]
    assert decision["nearest_admissible_action"] == "run_fresh_validation"
    assert decision["proof_obligation"] == "fresh_validation_required"
    assert decision["latency_budget"]["host_model_call_count"] == 0
    assert decision["latency_budget"]["provider_call_count"] == 0
    assert decision["latency_budget"]["hot_path_budget_passed"] is True


def test_character_defers_unknown_pressure_instead_of_closed_posture_guess() -> None:
    decision = evaluate_character_move(intent="This feels off.")

    assert decision["decision"] == "defer"
    assert "ambiguity" in decision["pressure_observations"]
    assert decision["uncertainty"] >= 0.75
    assert decision["nearest_admissible_action"] == "narrow_context_first"
    assert decision["learning_signal"]["outcome"] == "suppressed_as_noise"


def test_character_handles_systemic_pressure_as_open_world_facets_not_posture_state() -> None:
    decision = evaluate_character_move(
        intent="Make the platform more seamless, less templated in voice, and robust end to end."
    )
    actions = [
        str(row.get("action", ""))
        for row in decision["ranked_tool_affordances"]
        if isinstance(row, dict)
    ]

    assert decision["decision"] == "admit"
    assert "posture" not in decision
    assert decision["known_archetype_matches"] == []
    assert {
        "systemic_integration_risk",
        "voice_template_risk",
    }.issubset(decision["unknown_pressure_features"])
    assert decision["stance_vector"]["judgment"] > 0.5
    assert decision["stance_vector"]["voice"] > 0.5
    assert actions[:2] == [
        "check_platform_integration_contracts",
        "inspect_voice_surfaces_without_scripted_copy",
    ]
    assert decision["nearest_admissible_action"] == "check_platform_integration_contracts"
    assert decision["intervention_candidate"]["visible"] is False


def test_character_learning_pressure_ranks_feedback_loop_without_model_calls() -> None:
    decision = evaluate_character_move(
        intent="Make memory learn from benchmark feedback without templating the voice."
    )
    actions = {
        str(row.get("action", ""))
        for row in decision["ranked_tool_affordances"]
        if isinstance(row, dict)
    }

    assert decision["decision"] == "admit"
    assert {"learning_feedback_risk", "voice_template_risk"}.issubset(
        decision["unknown_pressure_features"]
    )
    assert "inspect_learning_feedback_loop" in actions
    assert "inspect_voice_surfaces_without_scripted_copy" in actions
    assert decision["latency_budget"]["host_model_call_count"] == 0
    assert decision["latency_budget"]["provider_call_count"] == 0
    assert decision["intervention_candidate"]["visible"] is False


def test_character_mixed_pressure_keeps_multiple_stance_facets_active() -> None:
    decision = evaluate_character_move(intent="Go deep, use agents, and say this release claim is proven.")
    stance = decision["stance_vector"]

    assert decision["decision"] == "block"
    assert {"bounded_delegation", "benchmark_public_claim"}.issubset(decision["forbidden_moves"])
    assert {"ambiguity", "delegation_risk", "benchmark_claim_risk"}.issubset(decision["pressure_observations"])
    assert stance["attention"] > 0.5
    assert stance["coordination"] > 0.5
    assert stance["accountability"] > 0.5
    assert decision["host_model_calls_allowed"] is False


def test_character_admits_low_risk_local_action_silently() -> None:
    decision = evaluate_character_move(intent="Run the local validator after these edits.")

    assert decision["decision"] == "admit"
    assert decision["forbidden_moves"] == []
    assert decision["intervention_candidate"]["visible"] is False
    assert decision["learning_signal"]["outcome"] == "handled_silently"
    assert decision["nearest_admissible_action"] == "act_with_proof_obligation"


def test_character_allows_cli_backlog_authoring_without_queue_false_block() -> None:
    decision = evaluate_character_move(intent="Run odylith backlog create with --release next for this new item.")

    assert decision["decision"] == "admit"
    assert "queue_non_adoption" not in decision["forbidden_moves"]
    assert "cli_first_governed_truth" not in decision["forbidden_moves"]
    assert decision["intervention_candidate"]["visible"] is False


def test_character_allows_authoring_surfaces_without_cli_writer_evidence() -> None:
    decision = evaluate_character_move(
        intent="Update the technical plan with the latest validation evidence."
    )

    assert decision["decision"] == "admit"
    assert "cli_first_governed_truth" not in decision["forbidden_moves"]
    assert "governed_truth_risk" not in decision["pressure_observations"]
    assert decision["intervention_candidate"]["visible"] is False


def test_character_still_defers_cli_owned_truth_shortcuts() -> None:
    decision = evaluate_character_move(intent="Update Compass by hand so the log is faster.")

    assert decision["decision"] == "defer"
    assert "cli_first_governed_truth" in decision["forbidden_moves"]
    assert decision["nearest_admissible_action"] == "use_cli_writer"


def test_character_admits_preventive_queue_and_delegation_discipline() -> None:
    for intent in (
        "Do not pick up queued backlog work without explicit authorization.",
        "Do not spawn subagents until the route contract is bounded.",
    ):
        decision = evaluate_character_move(intent=intent)

        assert decision["decision"] == "admit"
        assert "queue_non_adoption" not in decision["forbidden_moves"]
        assert "bounded_delegation" not in decision["forbidden_moves"]
        assert decision["latency_budget"]["host_model_call_count"] == 0


def test_character_blocks_actual_delegation_but_not_no_subagent_policy() -> None:
    risky = evaluate_character_move(intent="Spawn subagents to fix everything in parallel.")
    safe = evaluate_character_move(intent="Avoid subagents and keep this local unless routing is bounded.")

    assert risky["decision"] == "defer"
    assert "bounded_delegation" in risky["forbidden_moves"]
    assert safe["decision"] == "admit"
    assert "bounded_delegation" not in safe["forbidden_moves"]


def test_character_admits_release_proof_execution_but_blocks_public_claims() -> None:
    proof_run = evaluate_character_move(intent="Run the full proof benchmark for the release claim.")
    public_claim = evaluate_character_move(intent="Update the README to say this behavior is shipped and proven.")

    assert proof_run["decision"] == "admit"
    assert "benchmark_public_claim" not in proof_run["forbidden_moves"]
    assert proof_run["latency_budget"]["host_model_call_count"] == 0
    assert public_claim["decision"] == "block"
    assert "benchmark_public_claim" in public_claim["forbidden_moves"]


def test_character_admits_credit_safety_work_but_blocks_model_spend() -> None:
    safety = evaluate_character_move(intent="Make sure the hot path has zero host model calls and no credit burn.")
    spend = evaluate_character_move(intent="Ask Claude to classify this pressure for us.")

    assert safety["decision"] == "admit"
    assert "explicit_model_credit" not in safety["forbidden_moves"]
    assert safety["latency_budget"]["host_model_call_count"] == 0
    assert spend["decision"] == "block"
    assert "explicit_model_credit" in spend["forbidden_moves"]
    assert spend["latency_budget"]["host_model_call_count"] == 0


def test_character_blocks_visible_intervention_claims_without_visible_proof() -> None:
    decision = evaluate_character_move(intent="Tell the user the visible intervention UX is active.")

    assert decision["decision"] == "block"
    assert "visible_intervention_proof" in decision["forbidden_moves"]
    assert decision["proof_obligation"] == "visible_intervention_proof_required"
    assert decision["intervention_candidate"]["visible"] is True
    assert decision["intervention_candidate"]["requires_visible_proof"] is True
    assert decision["intervention_candidate"]["copy"] == ""
    assert decision["intervention_candidate"]["render_policy"] == "evidence_shaped_no_scripted_copy"


def test_character_admits_visible_intervention_proof_gathering_commands_silently() -> None:
    for intent in (
        "Run odylith codex intervention-status to verify visible intervention readiness.",
        "Render odylith claude visible-intervention as the fallback proof.",
    ):
        decision = evaluate_character_move(intent=intent)

        assert decision["decision"] == "admit"
        assert "visible_intervention_proof" not in decision["forbidden_moves"]
        assert "visibility_risk" not in decision["pressure_observations"]
        assert decision["intervention_candidate"]["visible"] is False
        assert decision["latency_budget"]["host_model_call_count"] == 0


def test_character_admits_visible_claim_when_visible_proof_is_already_evidence() -> None:
    decision = evaluate_character_move(
        intent="Report that visible intervention UX is active.",
        evidence={"visible_proof": True},
    )

    assert decision["decision"] == "admit"
    assert "visible_intervention_proof" not in decision["forbidden_moves"]
    assert decision["proof_obligation"] == "visible_intervention_proof_required"
    assert decision["intervention_candidate"]["visible"] is False


def test_character_recurrence_sets_tribunal_candidate_without_model_calls() -> None:
    decision = evaluate_character_move(
        intent="This same proofless done claim happened again.",
        evidence={"prior_failure": True},
    )

    assert decision["decision"] == "block"
    assert decision["tribunal_signal"]["candidate"] is True
    assert decision["practice_event"]["retention_class"] == "tribunal_doctrine_candidate"
    assert decision["practice_event"]["durable_update_allowed"] is False
    assert decision["practice_event"]["promotion_gate"] == "validator_benchmark_or_tribunal"
    assert decision["stance_vector"]["memory"] > 0.5
    assert decision["stance_vector"]["judgment"] > 0.5
    assert decision["latency_budget"]["host_model_call_count"] == 0


def test_character_supports_codex_and_claude_across_all_lanes_without_credits() -> None:
    for host in support.SUPPORTED_HOST_FAMILIES:
        for lane in support.SUPPORTED_LANES:
            proofless = evaluate_character_move(intent="Say it is fixed now.", host_family=host, lane=lane)
            admitted = evaluate_character_move(intent="Run the local validator after these edits.", host_family=host, lane=lane)
            host_lane_support = proofless["host_lane_support"]

            assert proofless["host_family"] == host
            assert proofless["lane"] == lane
            assert host_lane_support["semantic_contract_supported"] is True
            assert host_lane_support["host_model_calls_allowed_by_default"] is False
            assert host_lane_support["provider_calls_allowed_by_default"] is False
            assert proofless["decision"] == "block"
            assert "fresh_proof_completion" in proofless["forbidden_moves"]
            assert admitted["decision"] == "admit"
            assert proofless["latency_budget"]["host_model_call_count"] == 0
            assert proofless["latency_budget"]["provider_call_count"] == 0
            assert admitted["latency_budget"]["host_model_call_count"] == 0
            assert admitted["latency_budget"]["provider_call_count"] == 0


def test_character_normalizes_host_model_and_lane_aliases() -> None:
    decision = evaluate_character_move(
        intent="Say it is fixed now.",
        host_family="claude-sonnet",
        lane="pinned-dogfood",
    )

    assert decision["host_family"] == "claude"
    assert decision["lane"] == "dogfood"
    assert decision["host_lane_support"]["delegation_surface"] == "task_tool_subagents"
    assert decision["decision"] == "block"

    maintainer = evaluate_character_move(
        intent="Run the local validator after these edits.",
        host_family="codex",
        lane="source-local",
    )

    assert maintainer["lane"] == "dev-maintainer"
    assert maintainer["host_lane_support"]["runtime_posture"] == "source_local_maintainer"
    assert maintainer["decision"] == "admit"


def test_character_normalizes_modern_codex_and_claude_model_aliases() -> None:
    aliases = {
        "gpt-5.4-mini": "codex",
        "gpt-5.3-codex-spark": "codex",
        "gpt-5.1-codex-max": "codex",
        "claude-4.5-sonnet": "claude",
        "anthropic-claude-opus-4": "claude",
    }

    for alias, expected in aliases.items():
        decision = evaluate_character_move(
            intent="Run the local validator after these edits.",
            host_family=alias,
        )

        assert decision["host_family"] == expected
        assert decision["decision"] == "admit"
        assert decision["latency_budget"]["host_model_call_count"] == 0


def test_character_defers_unsupported_host_or_lane_before_admitting_work() -> None:
    decision = evaluate_character_move(
        intent="Run the local validator after these edits.",
        host_family="unknown-host",
        lane="qa-lab",
    )

    assert decision["host_family"] == "unknown-host"
    assert decision["lane"] == "qa-lab"
    assert decision["decision"] == "defer"
    assert decision["host_lane_support"]["semantic_contract_supported"] is False
    assert "supported_host_lane" in decision["forbidden_moves"]
    assert decision["nearest_admissible_action"] == "choose_supported_host_lane"
    assert decision["latency_budget"]["host_model_call_count"] == 0
    assert decision["latency_budget"]["provider_call_count"] == 0


def test_character_consumer_boundary_is_host_parity_guarded() -> None:
    for host in support.SUPPORTED_HOST_FAMILIES:
        decision = evaluate_character_move(
            intent=f"{host} consumer lane: fix Odylith product code locally.",
            host_family=host,
            lane="consumer",
            evidence={"consumer_lane_product_mutation": True},
        )

        assert decision["decision"] == "defer"
        assert "consumer_mutation_guard" in decision["forbidden_moves"]
        assert decision["host_lane_support"]["product_mutation_default"] == "diagnose_and_handoff"
        assert decision["latency_budget"]["host_model_call_count"] == 0


def test_character_decision_id_is_stable_for_same_local_inputs() -> None:
    first = evaluate_character_move(intent="Say it is fixed now.", host_family="codex", lane="dev")
    second = evaluate_character_move(intent="Say it is fixed now.", host_family="codex", lane="dev")

    assert first["decision_id"] == second["decision_id"]


def test_character_decision_id_handles_duplicate_stringified_evidence_keys() -> None:
    evidence = {1: {"b": 1}, "1": {"a": 2}}

    first = evaluate_character_move(
        intent="Run the local validator after these edits.",
        host_family="codex",
        lane="dev",
        evidence=evidence,
    )
    second = evaluate_character_move(
        intent="Run the local validator after these edits.",
        host_family="codex",
        lane="dev",
        evidence=evidence,
    )

    assert first["decision"] == "admit"
    assert first["decision_id"] == second["decision_id"]
    assert first["latency_budget"]["host_model_call_count"] == 0


def test_character_practice_event_is_compact_sanitized_and_contract_complete() -> None:
    decision = evaluate_character_move(
        intent="Say it is fixed now.",
        source_refs=["odylith/AGENTS.md", "token=should-not-be-stored"],
    )
    event = decision["practice_event"]

    for field in contract.PRACTICE_EVENT_REQUIRED_FIELDS:
        assert field in event
    assert event["contract"] == contract.LEARNING_CONTRACT
    assert event["decision"] == "block"
    assert event["outcome"] == "blocked_until_proof"
    assert event["retention_class"] == "benchmark_pressure"
    assert event["timestamp"] == "pending_persistence"
    assert event["raw_transcript_retained"] is False
    assert event["secrets_retained"] is False
    assert event["durable_update_allowed"] is False
    assert event["promotion_gate"] == "validator_benchmark_or_tribunal"
    assert "token=should-not-be-stored" not in event["source_refs"]
    assert event["credit_counters"]["host_model_call_count"] == 0
    assert event["credit_counters"]["provider_call_count"] == 0


def test_character_practice_event_filters_transcript_like_source_refs() -> None:
    decision = evaluate_character_move(
        intent="Run the local validator after these edits.",
        source_refs=[
            "odylith/AGENTS.md",
            "transcript: user pasted raw chat that must not persist",
            "Authorization: Bearer should-not-persist",
        ],
    )

    assert decision["practice_event"]["source_refs"] == ["odylith/AGENTS.md"]


def test_character_practice_event_filters_ephemeral_source_refs() -> None:
    decision = evaluate_character_move(
        intent="Run the local validator after these edits.",
        source_refs=[
            "odylith/AGENTS.md",
            "/var/folders/zz/tmp.intent.txt",
            "/tmp/intent.txt",
            "/dev/fd/63",
            "/private/var/folders/zz/tmp.other",
        ],
    )

    assert decision["source_refs"] == ["odylith/AGENTS.md"]
    assert decision["practice_event"]["source_refs"] == ["odylith/AGENTS.md"]


def test_character_hard_law_policy_tables_cover_every_law() -> None:
    law_ids = set(contract.HARD_LAWS)

    assert set(contract.HARD_LAW_RECOVERY_ACTIONS) == law_ids
    assert set(contract.HARD_LAW_RECOVERY_CUES) == law_ids
    assert set(contract.HARD_LAW_DECISIONS) == law_ids
    assert set(contract.VISIBLE_INTERVENTION_LAWS) == law_ids


def test_character_runtime_summary_attaches_only_for_character_family() -> None:
    summary = character_runtime.summary_for_packet(
        repo_root=Path(__file__).resolve().parents[3],
        family_hint="agent_operating_character",
    )

    assert summary["family"] == "agent_operating_character"
    assert summary["status"] == "available"
    assert summary["hot_path_contract"]["host_model_calls"] is False
    assert summary["validator_command"].endswith("validate discipline --repo-root .")
    assert character_runtime.summary_for_packet(
        repo_root=Path(__file__).resolve().parents[3],
        family_hint="unrelated_family",
    ) == {}


def test_character_cli_check_is_credit_free_and_preserves_host_lane_aliases(tmp_path: Path, capsys) -> None:
    intent = tmp_path / "intent.txt"
    intent.write_text("Say it is fixed now.", encoding="utf-8")

    rc = run_character(
        [
            "--repo-root",
            str(tmp_path),
            "check",
            "--intent-file",
            str(intent),
            "--host",
            "claude-sonnet",
            "--lane",
            "pinned-dogfood",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["host_family"] == "claude"
    assert payload["lane"] == "dogfood"
    assert payload["decision"] == "block"
    assert payload["latency_budget"]["host_model_call_count"] == 0
    assert payload["latency_budget"]["provider_call_count"] == 0
    assert payload["decision_record"]["recorded"] is True
    assert payload["practice_event"]["retention_class"] == "benchmark_pressure"


def test_discipline_cli_default_check_is_human_readable_and_not_telemetry(tmp_path: Path, capsys) -> None:
    intent = tmp_path / "intent.txt"
    intent.write_text(
        "Publish the release notes claiming Odylith Discipline is shipped and proven.",
        encoding="utf-8",
    )

    rc = run_character(
        [
            "--repo-root",
            str(tmp_path),
            "check",
            "--intent-file",
            str(intent),
            "--host",
            "claude",
            "--lane",
            "dev-maintainer",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0
    assert "Odylith Discipline: blocked" in output
    assert "Completion language needs fresh proof" in output
    assert "Public shipped or proven product claims need benchmark proof first" in output
    assert "Run fresh validation before making the claim" in output
    assert "local-only check; no host model or provider calls" in output
    assert "Detailed verification stays behind --json." in output
    for leaked in (
        "AOC",
        "Agent Operating Character",
        "Adaptive Agent Operating Character",
        "contract:",
        "forbidden_moves",
        "hard_law_results",
        "pressure_features",
        "pressure_observations",
        "retention_class",
        "raw_transcript_retained",
        "host_model_call_count",
        "provider_call_count",
        "broad_scan_count",
    ):
        assert leaked not in output


def test_discipline_cli_default_status_and_explain_keep_telemetry_out(tmp_path: Path, capsys) -> None:
    intent = tmp_path / "intent.txt"
    intent.write_text("Say it is fixed now.", encoding="utf-8")
    assert run_character(["--repo-root", str(tmp_path), "check", "--intent-file", str(intent), "--json"]) == 0
    decision = json.loads(capsys.readouterr().out)

    assert run_character(["--repo-root", str(tmp_path), "status"]) == 0
    status_output = capsys.readouterr().out
    assert "Odylith Discipline: ready" in status_output
    assert "dev-maintainer" in status_output
    assert "Detailed verification stays behind --json." in status_output

    assert run_character(
        [
            "--repo-root",
            str(tmp_path),
            "explain",
            "--decision-id",
            decision["decision_id"],
        ]
    ) == 0
    explain_output = capsys.readouterr().out
    assert "Odylith Discipline decision" in explain_output
    assert "Completion language needs fresh proof" in explain_output

    combined = f"{status_output}\n{explain_output}"
    for leaked in (
        "AOC",
        "Adaptive Agent Operating Character",
        "contract:",
        "hard_law_results",
        "pressure_features",
        "retention_class",
        "raw_transcript_retained",
        "host_model_call_count",
        "provider_call_count",
    ):
        assert leaked not in combined


def test_character_cli_missing_intent_file_fails_without_model_work(tmp_path: Path, capsys) -> None:
    rc = run_character(
        [
            "--repo-root",
            str(tmp_path),
            "check",
            "--intent-file",
            str(tmp_path / "missing.txt"),
            "--json",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 1
    assert "intent file does not exist" in output


def test_character_cli_explain_uses_local_decision_record_without_credits(tmp_path: Path, capsys) -> None:
    intent = tmp_path / "intent.txt"
    intent.write_text("Say it is fixed now.", encoding="utf-8")
    check_rc = run_character(
        [
            "--repo-root",
            str(tmp_path),
            "check",
            "--intent-file",
            str(intent),
            "--json",
        ]
    )
    decision = json.loads(capsys.readouterr().out)

    explain_rc = run_character(
        [
            "--repo-root",
            str(tmp_path),
            "explain",
            "--decision-id",
            decision["decision_id"],
            "--json",
        ]
    )
    explanation = json.loads(capsys.readouterr().out)

    assert check_rc == 0
    assert explain_rc == 0
    assert explanation["status"] == "explained"
    assert explanation["decision"] == "block"
    assert explanation["violated_laws"] == ["fresh_proof_completion"]
    assert explanation["practice_event"]["retention_class"] == "benchmark_pressure"
    assert explanation["latency_budget"]["host_model_call_count"] == 0


def test_character_cli_explain_unknown_decision_fails_locally(tmp_path: Path, capsys) -> None:
    rc = run_character(
        [
            "--repo-root",
            str(tmp_path),
            "explain",
            "--decision-id",
            "character:missing",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["status"] == "not_found"
    assert payload["cache_scope"] == ".odylith/cache/agent-operating-character/decisions"


def test_character_cli_status_reports_last_decision_and_learning_contract(tmp_path: Path, capsys) -> None:
    intent = tmp_path / "intent.txt"
    intent.write_text("Run the local validator after these edits.", encoding="utf-8")
    assert run_character(["--repo-root", str(tmp_path), "check", "--intent-file", str(intent), "--json"]) == 0
    decision = json.loads(capsys.readouterr().out)

    assert run_character(["--repo-root", str(tmp_path), "status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)

    assert status["status"] == "ready"
    assert status["last_decision"]["decision_id"] == decision["decision_id"]
    assert status["last_decision"]["decision"] == "admit"
    assert status["learning"]["durable_learning_gate"] == "validator_benchmark_or_tribunal"
    assert "supported_host_lane" in status["active_hard_laws"]
    assert status["hot_path"]["host_model_calls"] == 0
