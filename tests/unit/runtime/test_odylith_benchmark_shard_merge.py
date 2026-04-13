from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.evaluation import odylith_benchmark_runner as runner
from odylith.runtime.evaluation import odylith_benchmark_shard_merge as shard_merge


def _write_corpus(tmp_path: Path, case_ids: list[str]) -> None:
    cases = []
    for case_id in case_ids:
        cases.append(
            {
                "case_id": case_id,
                "label": case_id.replace("-", " ").title(),
                "family": "merge_heavy_change",
                "priority": "high",
                "benchmark": {
                    "prompt": f"Work {case_id}.",
                    "paths": [f"src/{case_id}.py"],
                    "required_paths": [f"src/{case_id}.py"],
                    "validation_commands": ["pytest -q"],
                    "needs_write": True,
                },
                "match": {"paths_any": [f"src/{case_id}.py"]},
                "expect": {"within_budget": True},
            }
        )
    corpus = {
        "version": "v1",
        "program": {},
        "cases": cases,
        "architecture_cases": [],
    }
    corpus_path = tmp_path / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text(json.dumps(corpus, indent=2) + "\n", encoding="utf-8")


def _result(mode: str, cache_profile: str) -> dict[str, object]:
    return {
        "mode": mode,
        "kind": "packet",
        "packet_source": "impact",
        "cache_profile": cache_profile,
        "scenario_family": "merge_heavy_change",
        "scenario_priority": "high",
        "needs_write": True,
        "correctness_critical": True,
        "latency_ms": 10.0,
        "instrumented_reasoning_duration_ms": 5.0,
        "uninstrumented_overhead_ms": 5.0,
        "required_path_count": 1,
        "required_path_recall": 1.0,
        "required_path_precision": 1.0,
        "required_path_misses": [],
        "observed_path_count": 1,
        "observed_paths": ["src/example.py"],
        "observed_path_sources": (
            ["odylith_prompt_payload"] if mode == runner._ODYLITH_ON_MODE else ["raw_prompt_visible_paths"]  # noqa: SLF001
        ),
        "hallucinated_surface_count": 0,
        "hallucinated_surface_rate": 0.0,
        "hallucinated_surfaces": [],
        "candidate_write_path_count": 1,
        "candidate_write_paths": ["src/example.py"],
        "expected_write_path_count": 1,
        "write_surface_precision": 1.0,
        "unnecessary_widening_count": 0,
        "unnecessary_widening_rate": 0.0,
        "unnecessary_widening_paths": [],
        "validation_command_count": 1,
        "validation_success_proxy": True,
        "expectation_ok": True,
        "selected_command_count": 1,
        "selected_doc_count": 1,
        "selected_test_count": 1,
        "full_scan": False,
        "packet": {"within_budget": True, "route_ready": True, "live_status": "completed"},
        "timing_trace": {},
        "operator_diag_artifact_tokens": {},
        "prompt_artifact_tokens": {},
        "runtime_contract_artifact_tokens": {},
        "effective_estimated_tokens": 10.0,
        "effective_token_basis": "codex_exec_input_tokens",
        "codex_prompt_estimated_tokens": 10.0,
        "total_payload_estimated_tokens": 10.0,
        "adaptive_escalation": {},
        "orchestration": {},
        "selector_diagnostics": {},
        "strict_gate_command_count": 0,
        "expectation_details": {
            "validator_status": "passed",
            "validator_status_basis": "validator_result",
        },
        "preflight_evidence_mode": "none",
        "preflight_evidence_commands": [],
        "preflight_evidence_result_status": "not_applicable",
    }


def _scenario_report(case_id: str, cache_profile: str) -> dict[str, object]:
    return {
        "scenario_id": case_id,
        "label": case_id,
        "summary": case_id,
        "family": "merge_heavy_change",
        "priority": "high",
        "prompt": f"Work {case_id}.",
        "acceptance_criteria": [],
        "required_paths": [f"src/{case_id}.py"],
        "validation_commands": ["pytest -q"],
        "needs_write": True,
        "changed_paths": [f"src/{case_id}.py"],
        "workstream": "B-093",
        "kind": "packet",
        "cache_profile": cache_profile,
        "results": [
            _result(runner._ODYLITH_ON_MODE, cache_profile),  # noqa: SLF001
            _result(runner._RAW_AGENT_BASELINE_MODE, cache_profile),  # noqa: SLF001
        ],
    }


def _write_history_report(
    tmp_path: Path,
    *,
    report_id: str,
    shard_index: int,
    shard_count: int,
    case_ids: list[str],
) -> None:
    report = {
        "report_id": report_id,
        "repo_root": str(tmp_path),
        "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
        "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
        "modes": list(runner.DEFAULT_MODES),
        "cache_profiles": list(runner.DEFAULT_CACHE_PROFILES),
        "primary_cache_profile": "warm",
        "selection": {
            "shard_count": shard_count,
            "shard_index": shard_index,
            "full_corpus_selected": False,
        },
        "cache_profile_scenarios": {
            "warm": [_scenario_report(case_id, "warm") for case_id in case_ids],
            "cold": [_scenario_report(case_id, "cold") for case_id in case_ids],
        },
    }
    history_path = runner.history_report_path(repo_root=tmp_path, report_id=report_id)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _stub_merge_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shard_merge.runner, "_singleton_family_latency_probes", lambda **kwargs: {})
    monkeypatch.setattr(shard_merge.runner, "_benchmark_runtime_hygiene_snapshot", lambda **kwargs: {})
    monkeypatch.setattr(shard_merge.runner, "_run_live_adoption_proof", lambda **kwargs: {"sample_size": 0})
    monkeypatch.setattr(shard_merge.runner, "_runtime_posture_summary", lambda **kwargs: {})
    monkeypatch.setattr(
        shard_merge.runner,
        "_mode_summary",
        lambda *, mode, scenario_rows: {"mode": mode, "scenario_count": len(list(scenario_rows)), "within_budget_rate": 1.0},
    )
    monkeypatch.setattr(
        shard_merge.runner,
        "_family_summaries",
        lambda *, modes, mode_rows: {
            "merge_heavy_change": {
                mode: {"scenario_count": len(mode_rows.get(mode, []))}
                for mode in modes
            }
        },
    )
    monkeypatch.setattr(shard_merge.runner, "_apply_singleton_family_latency_probes", lambda **kwargs: kwargs["family_summaries"])
    monkeypatch.setattr(
        shard_merge.runner,
        "_primary_comparison",
        lambda **kwargs: {"candidate_mode": kwargs["candidate_mode"], "baseline_mode": kwargs["baseline_mode"]},
    )
    monkeypatch.setattr(shard_merge.runner, "_family_deltas", lambda **kwargs: {})
    monkeypatch.setattr(shard_merge.runner, "_live_execution_contracts", lambda mode_rows: {})
    monkeypatch.setattr(
        shard_merge.benchmark_group_summaries,
        "grouped_summaries",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        shard_merge.benchmark_group_summaries,
        "grouped_deltas",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        shard_merge.runner,
        "_aggregate_published_scenarios",
        lambda **kwargs: list(kwargs["cache_profile_reports"][kwargs["cache_profiles"][0]]),
    )
    monkeypatch.setattr(
        shard_merge.runner,
        "_apply_singleton_latency_probes_to_published_scenarios",
        lambda **kwargs: kwargs["published_scenarios"],
    )
    monkeypatch.setattr(shard_merge.runner, "_fairness_findings", lambda **kwargs: [])
    monkeypatch.setattr(shard_merge.runner, "_robustness_summary", lambda **kwargs: {})
    monkeypatch.setattr(
        shard_merge.runner,
        "_published_mode_table",
        lambda **kwargs: {
            "rows": [],
            "mode_order": [],
            "display_mode_order": [],
            "delta_header": "Delta",
            "why_it_matters_header": "Why It Matters",
        },
    )
    monkeypatch.setattr(shard_merge.runner, "_published_mode_table_markdown", lambda table: "")
    monkeypatch.setattr(shard_merge.runner, "_pair_timing_summary", lambda **kwargs: {})
    monkeypatch.setattr(
        shard_merge.runner,
        "_acceptance",
        lambda **kwargs: {"status": "provisional_pass", "hard_failure_labels": [], "advisory_failure_labels": []},
    )
    monkeypatch.setattr(
        shard_merge.runner,
        "compact_report_summary",
        lambda report: {"status": report["status"], "comparison_contract": report["comparison_contract"]},
    )
    monkeypatch.setattr(shard_merge.runner, "_render_report_summary", lambda report: f"summary {report['report_id']}")


def test_merge_shard_reports_writes_full_corpus_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_corpus(tmp_path, ["case-a", "case-b"])
    _write_history_report(tmp_path, report_id="shard-a", shard_index=1, shard_count=2, case_ids=["case-a"])
    _write_history_report(tmp_path, report_id="shard-b", shard_index=2, shard_count=2, case_ids=["case-b"])
    _stub_merge_helpers(monkeypatch)

    report = shard_merge.merge_shard_reports(
        repo_root=tmp_path,
        report_refs=["shard-a", "shard-b"],
    )

    assert report["latest_eligible"] is True
    assert report["selection"]["full_corpus_selected"] is True
    assert report["merge_metadata"]["source_shard_count"] == 2
    assert report["merge_metadata"]["source_report_ids"] == ["shard-a", "shard-b"]
    assert len(report["cache_profile_scenarios"]["warm"]) == 2
    assert len(report["published_scenarios"]) == 2
    assert runner.latest_report_path(repo_root=tmp_path).is_file()
    assert runner.latest_report_path(repo_root=tmp_path, benchmark_profile=runner.BENCHMARK_PROFILE_PROOF).is_file()
    assert runner.history_report_path(repo_root=tmp_path, report_id=report["report_id"]).is_file()


def test_merge_shard_reports_rejects_incomplete_shard_set(tmp_path: Path) -> None:
    _write_corpus(tmp_path, ["case-a", "case-b"])
    _write_history_report(tmp_path, report_id="shard-a", shard_index=1, shard_count=2, case_ids=["case-a"])

    with pytest.raises(ValueError, match="complete shard set"):
        shard_merge.merge_shard_reports(
            repo_root=tmp_path,
            report_refs=["shard-a"],
            write_report=False,
        )


def test_merge_shard_reports_rejects_missing_full_corpus_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_corpus(tmp_path, ["case-a", "case-b", "case-c"])
    _write_history_report(tmp_path, report_id="shard-a", shard_index=1, shard_count=2, case_ids=["case-a"])
    _write_history_report(tmp_path, report_id="shard-b", shard_index=2, shard_count=2, case_ids=["case-b"])
    _stub_merge_helpers(monkeypatch)

    with pytest.raises(ValueError, match="do not cover the full current corpus"):
        shard_merge.merge_shard_reports(
            repo_root=tmp_path,
            report_refs=["shard-a", "shard-b"],
            write_report=False,
        )


def test_merge_shard_reports_rejects_duplicate_scenario_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_corpus(tmp_path, ["case-a", "case-b"])
    _write_history_report(tmp_path, report_id="shard-a", shard_index=1, shard_count=2, case_ids=["case-a"])
    _write_history_report(tmp_path, report_id="shard-b", shard_index=2, shard_count=2, case_ids=["case-a"])
    _stub_merge_helpers(monkeypatch)

    with pytest.raises(ValueError, match="Duplicate scenario `case-a`"):
        shard_merge.merge_shard_reports(
            repo_root=tmp_path,
            report_refs=["shard-a", "shard-b"],
            write_report=False,
        )
