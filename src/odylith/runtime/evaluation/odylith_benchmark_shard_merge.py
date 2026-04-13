"""Merge benchmark shard history reports into one publication-safe report.

This is a maintainer-only operational helper for release proof on large
full-corpus runs. It is intentionally not wired into the public benchmark CLI
surface. The merged report must still satisfy the same full-corpus proof
contract as a serial run.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.evaluation import benchmark_group_summaries
from odylith.runtime.evaluation import odylith_benchmark_runner as runner


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(token).strip() for token in value if str(token).strip()]


def _scenario_id(row: Mapping[str, Any]) -> str:
    return (
        str(row.get("scenario_id", "")).strip()
        or str(row.get("case_id", "")).strip()
        or str(row.get("label", "")).strip()
    )


def _load_report(*, repo_root: Path, report_ref: str) -> dict[str, Any]:
    token = str(report_ref or "").strip()
    if not token:
        raise ValueError("Shard report reference cannot be empty.")
    candidate_path = Path(token)
    if candidate_path.exists():
        path = candidate_path.resolve()
    else:
        path = runner.history_report_path(repo_root=repo_root, report_id=token)
    payload = odylith_context_cache.read_json_object(path)
    if not payload:
        raise ValueError(f"Shard report `{token}` could not be loaded from `{path}`.")
    return dict(payload)


def _validate_shard_reports(
    *,
    repo_root: Path,
    reports: Sequence[Mapping[str, Any]],
) -> tuple[str, list[str], list[str], int]:
    if not reports:
        raise ValueError("At least one shard report is required.")
    first = reports[0]
    benchmark_profile = str(first.get("benchmark_profile", "")).strip()
    comparison_contract = str(first.get("comparison_contract", "")).strip()
    modes = [
        runner._normalize_mode(str(token).strip())  # noqa: SLF001
        for token in first.get("modes", [])
        if str(token).strip()
    ]
    cache_profiles = _list_of_strings(first.get("cache_profiles"))
    if not benchmark_profile or not comparison_contract or not modes or not cache_profiles:
        raise ValueError("Shard reports must carry benchmark profile, comparison contract, modes, and cache profiles.")
    shard_indices: set[int] = set()
    shard_count = 0
    for report in reports:
        if str(report.get("benchmark_profile", "")).strip() != benchmark_profile:
            raise ValueError("Shard reports disagree on benchmark_profile.")
        if str(report.get("comparison_contract", "")).strip() != comparison_contract:
            raise ValueError("Shard reports disagree on comparison_contract.")
        report_modes = [
            runner._normalize_mode(str(token).strip())  # noqa: SLF001
            for token in report.get("modes", [])
            if str(token).strip()
        ]
        if report_modes != modes:
            raise ValueError("Shard reports disagree on mode order.")
        report_cache_profiles = _list_of_strings(report.get("cache_profiles"))
        if report_cache_profiles != cache_profiles:
            raise ValueError("Shard reports disagree on cache profile order.")
        selection = _mapping(report.get("selection"))
        report_shard_count = int(selection.get("shard_count", report.get("shard_count", 1)) or 1)
        report_shard_index = int(selection.get("shard_index", report.get("shard_index", 1)) or 1)
        if report_shard_count <= 1:
            raise ValueError("Shard merge requires reports produced with shard_count > 1.")
        if shard_count and report_shard_count != shard_count:
            raise ValueError("Shard reports disagree on shard_count.")
        shard_count = report_shard_count
        if report_shard_index in shard_indices:
            raise ValueError(f"Duplicate shard_index {report_shard_index} in shard reports.")
        shard_indices.add(report_shard_index)
        report_repo_root = Path(str(report.get("repo_root", "")).strip() or repo_root).resolve()
        if report_repo_root != repo_root.resolve():
            raise ValueError("Shard reports disagree on repo_root.")
    expected_indices = set(range(1, shard_count + 1))
    if shard_indices != expected_indices:
        raise ValueError(
            "Shard reports do not form a complete shard set: "
            f"expected {sorted(expected_indices)}, got {sorted(shard_indices)}."
        )
    return benchmark_profile, modes, cache_profiles, shard_count


def _ordered_full_corpus_scenarios(*, repo_root: Path) -> list[dict[str, Any]]:
    scenarios = runner.load_benchmark_scenarios(repo_root=repo_root)
    if not scenarios:
        raise ValueError("Benchmark corpus is empty; cannot merge shard reports.")
    return [dict(row) for row in scenarios]


def _merge_cache_profile_reports(
    *,
    ordered_scenarios: Sequence[Mapping[str, Any]],
    cache_profiles: Sequence[str],
    reports: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    ordered_ids = [_scenario_id(row) for row in ordered_scenarios]
    merged: dict[str, list[dict[str, Any]]] = {}
    for cache_profile in cache_profiles:
        rows_by_id: dict[str, dict[str, Any]] = {}
        for report in reports:
            shard_rows = _mapping(report.get("cache_profile_scenarios")).get(cache_profile)
            if not isinstance(shard_rows, list):
                raise ValueError(f"Shard report is missing cache_profile_scenarios for `{cache_profile}`.")
            for row in shard_rows:
                if not isinstance(row, Mapping):
                    continue
                scenario_id = _scenario_id(row)
                if not scenario_id:
                    raise ValueError(f"Shard report row under `{cache_profile}` is missing scenario_id.")
                if scenario_id in rows_by_id:
                    raise ValueError(
                        f"Duplicate scenario `{scenario_id}` found for cache profile `{cache_profile}` across shard reports."
                    )
                rows_by_id[scenario_id] = dict(row)
        missing = [scenario_id for scenario_id in ordered_ids if scenario_id not in rows_by_id]
        extras = sorted(set(rows_by_id) - set(ordered_ids))
        if missing:
            raise ValueError(
                f"Shard reports do not cover the full current corpus for `{cache_profile}`; missing {missing[:8]}."
            )
        if extras:
            raise ValueError(
                f"Shard reports include scenario ids outside the current corpus for `{cache_profile}`: {extras[:8]}."
            )
        merged[cache_profile] = [rows_by_id[scenario_id] for scenario_id in ordered_ids]
    return merged


def _mode_rows_from_reports(
    *,
    cache_profile_reports: Mapping[str, Sequence[Mapping[str, Any]]],
    cache_profiles: Sequence[str],
    modes: Sequence[str],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    cache_profile_mode_rows: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for cache_profile in cache_profiles:
        mode_rows: dict[str, list[dict[str, Any]]] = {mode: [] for mode in modes}
        for scenario_report in cache_profile_reports.get(cache_profile, []):
            scenario_id = _scenario_id(scenario_report)
            seen_modes: set[str] = set()
            results = scenario_report.get("results")
            if not isinstance(results, list):
                raise ValueError(f"Scenario `{scenario_id}` under `{cache_profile}` is missing result rows.")
            for result in results:
                if not isinstance(result, Mapping):
                    continue
                mode = runner._normalize_mode(str(result.get("mode", "")).strip())  # noqa: SLF001
                if mode not in mode_rows:
                    continue
                mode_rows[mode].append(dict(result))
                seen_modes.add(mode)
            missing_modes = [mode for mode in modes if mode not in seen_modes]
            if missing_modes:
                raise ValueError(
                    f"Scenario `{scenario_id}` under `{cache_profile}` is missing modes {missing_modes} in shard reports."
                )
        cache_profile_mode_rows[cache_profile] = mode_rows
    return cache_profile_mode_rows


def merge_shard_reports(
    *,
    repo_root: Path,
    report_refs: Sequence[str],
    write_report: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    reports = [_load_report(repo_root=root, report_ref=token) for token in report_refs]
    benchmark_profile, modes, cache_profiles, shard_count = _validate_shard_reports(repo_root=root, reports=reports)
    ordered_scenarios = _ordered_full_corpus_scenarios(repo_root=root)
    ordered_ids = [_scenario_id(row) for row in ordered_scenarios]
    generated_utc = runner._utc_now()  # noqa: SLF001
    report_id = runner._benchmark_report_id(  # noqa: SLF001
        generated_utc=generated_utc,
        modes=modes,
        scenario_ids=ordered_ids,
        cache_profiles=cache_profiles,
    )
    comparison_contract = str(reports[0].get("comparison_contract", "")).strip()
    primary_cache_profile = str(reports[0].get("primary_cache_profile", "")).strip() or cache_profiles[0]
    latest_eligible = bool(
        benchmark_profile == runner.BENCHMARK_PROFILE_PROOF
        and cache_profiles == list(runner.DEFAULT_CACHE_PROFILES)
        and modes == list(runner.DEFAULT_MODES)
    )
    startup_hygiene = runner._cleanup_stale_benchmark_state(repo_root=root, clear_progress=True)  # noqa: SLF001
    progress_payload: dict[str, Any] = {
        "contract": runner.PROGRESS_CONTRACT,
        "version": runner.PROGRESS_VERSION,
        "report_id": report_id,
        "repo_root": str(root),
        "benchmark_profile": benchmark_profile,
        "benchmark_profile_label": runner._benchmark_profile_label(benchmark_profile),  # noqa: SLF001
        "benchmark_profile_description": runner._benchmark_profile_description(benchmark_profile),  # noqa: SLF001
        "comparison_contract": comparison_contract,
        "started_utc": generated_utc,
        "updated_utc": generated_utc,
        "status": "running",
        "phase": "merging_shard_reports",
        "modes": list(modes),
        "cache_profiles": list(cache_profiles),
        "primary_cache_profile": primary_cache_profile,
        "selection_strategy": "full_corpus",
        "shard_count": 1,
        "shard_index": 1,
        "scenario_count": len(ordered_scenarios),
        "total_results": len(ordered_scenarios) * len(modes) * len(cache_profiles),
        "completed_cache_profiles": 0,
        "completed_scenarios": 0,
        "completed_results": 0,
        "current_cache_profile": "",
        "current_scenario_id": "",
        "current_mode": "",
        "latest_eligible": latest_eligible,
        "selection": {
            "case_ids": [],
            "scenario_ids": [],
            "family_filters": [],
            "benchmark_profile": benchmark_profile,
            "profile_default_narrowing": "",
            "selection_strategy": "full_corpus",
            "shard_count": 1,
            "shard_index": 1,
            "default_modes_applied": True,
            "default_cache_profiles_applied": True,
            "limit": 0,
            "full_corpus_selected": True,
            "available_scenario_count": len(ordered_scenarios),
            "cache_profiles": list(cache_profiles),
        },
    }
    runner._write_progress(repo_root=root, payload=progress_payload)  # noqa: SLF001
    try:
        cache_profile_reports = _merge_cache_profile_reports(
            ordered_scenarios=ordered_scenarios,
            cache_profiles=cache_profiles,
            reports=reports,
        )
        cache_profile_mode_rows = _mode_rows_from_reports(
            cache_profile_reports=cache_profile_reports,
            cache_profiles=cache_profiles,
            modes=modes,
        )
        progress_payload.update(
            {
                "updated_utc": runner._utc_now(),  # noqa: SLF001
                "phase": "computing_post_run_metrics",
                "completed_cache_profiles": len(cache_profiles),
                "completed_scenarios": len(ordered_scenarios),
                "completed_results": len(ordered_scenarios) * len(modes) * len(cache_profiles),
            }
        )
        runner._write_progress(repo_root=root, payload=progress_payload)  # noqa: SLF001
        latency_probes = runner._singleton_family_latency_probes(  # noqa: SLF001
            repo_root=root,
            scenarios=ordered_scenarios,
            modes=modes,
            cache_profiles=cache_profiles,
            benchmark_profile=benchmark_profile,
        )
        final_hygiene = runner._benchmark_runtime_hygiene_snapshot(repo_root=root)  # noqa: SLF001
        corpus_summary = runner._corpus_summary(scenarios=ordered_scenarios)  # noqa: SLF001
        corpus_composition = runner._corpus_composition(  # noqa: SLF001
            scenarios=ordered_scenarios,
            available_scenarios=ordered_scenarios,
        )
        primary_scenario_reports = list(cache_profile_reports.get(primary_cache_profile, []))
        primary_mode_rows = cache_profile_mode_rows.get(primary_cache_profile, {})
        mode_summaries = {
            mode: runner._mode_summary(mode=mode, scenario_rows=rows)  # noqa: SLF001
            for mode, rows in primary_mode_rows.items()
        }
        primary_comparison = runner._primary_comparison(  # noqa: SLF001
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
            mode_summaries=mode_summaries,
        )
        cache_profile_summaries: dict[str, dict[str, Any]] = {}
        for cache_profile in cache_profiles:
            profile_mode_rows = cache_profile_mode_rows.get(cache_profile, {})
            profile_mode_summaries = {
                mode: runner._mode_summary(mode=mode, scenario_rows=rows)  # noqa: SLF001
                for mode, rows in profile_mode_rows.items()
            }
            profile_family_summaries = runner._family_summaries(modes=modes, mode_rows=profile_mode_rows)  # noqa: SLF001
            profile_family_summaries = runner._apply_singleton_family_latency_probes(  # noqa: SLF001
                family_summaries=profile_family_summaries,
                latency_probes=latency_probes,
                cache_profile=cache_profile,
            )
            profile_primary_comparison = runner._primary_comparison(  # noqa: SLF001
                candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
                baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
                mode_summaries=profile_mode_summaries,
            )
            profile_scenarios = list(cache_profile_reports.get(cache_profile, []))
            profile_fairness_findings = runner._fairness_findings(  # noqa: SLF001
                repo_root=root,
                comparison_contract=comparison_contract,
                published_scenarios=profile_scenarios,
            )
            profile_packet_source_summaries = benchmark_group_summaries.grouped_summaries(
                modes=modes,
                mode_rows=profile_mode_rows,
                group_field="packet_source",
                row_kind="packet",
                summarize=runner._mode_summary,  # noqa: SLF001
            )
            profile_execution_contracts = runner._live_execution_contracts(profile_mode_rows)  # noqa: SLF001
            cache_profile_summaries[cache_profile] = {
                "scenario_count": len(profile_scenarios),
                "mode_summaries": profile_mode_summaries,
                "family_summaries": profile_family_summaries,
                "packet_source_summaries": profile_packet_source_summaries,
                "execution_contracts": profile_execution_contracts,
                "family_deltas": runner._family_deltas(  # noqa: SLF001
                    candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
                    baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
                    family_summaries=profile_family_summaries,
                ),
                "primary_comparison": profile_primary_comparison,
                "fairness_contract_passed": not profile_fairness_findings,
                "fairness_findings": profile_fairness_findings,
                "acceptance": runner._acceptance(  # noqa: SLF001
                    mode_summaries=profile_mode_summaries,
                    primary_comparison=profile_primary_comparison,
                    family_summaries=profile_family_summaries,
                    corpus_summary=corpus_summary,
                    fairness_findings=profile_fairness_findings,
                    packet_source_summaries=profile_packet_source_summaries,
                    execution_contracts=profile_execution_contracts,
                    comparison_contract=comparison_contract,
                ),
            }
        family_summaries = (
            dict(_mapping(cache_profile_summaries.get(primary_cache_profile)).get("family_summaries", {}))
            if isinstance(cache_profile_summaries.get(primary_cache_profile), Mapping)
            else {}
        )
        published_scenarios = runner._aggregate_published_scenarios(  # noqa: SLF001
            scenarios=ordered_scenarios,
            modes=modes,
            cache_profiles=cache_profiles,
            cache_profile_reports=cache_profile_reports,
        )
        published_scenarios = runner._apply_singleton_latency_probes_to_published_scenarios(  # noqa: SLF001
            published_scenarios=published_scenarios,
            latency_probes=latency_probes,
        )
        fairness_findings = runner._fairness_findings(  # noqa: SLF001
            repo_root=root,
            comparison_contract=comparison_contract,
            published_scenarios=published_scenarios,
        )
        published_mode_rows: dict[str, list[dict[str, Any]]] = {mode: [] for mode in modes}
        for scenario_report in published_scenarios:
            for result in scenario_report.get("results", []):
                if not isinstance(result, Mapping):
                    continue
                mode = str(result.get("mode", "")).strip()
                if not mode:
                    continue
                published_mode_rows.setdefault(mode, []).append(dict(result))
        published_mode_summaries = {
            mode: runner._mode_summary(mode=mode, scenario_rows=rows)  # noqa: SLF001
            for mode, rows in published_mode_rows.items()
        }
        published_family_summaries = runner._family_summaries(  # noqa: SLF001
            modes=modes,
            mode_rows=published_mode_rows,
        )
        packet_source_summaries = benchmark_group_summaries.grouped_summaries(
            modes=modes,
            mode_rows=primary_mode_rows,
            group_field="packet_source",
            row_kind="packet",
            summarize=runner._mode_summary,  # noqa: SLF001
        )
        published_packet_source_summaries = benchmark_group_summaries.grouped_summaries(
            modes=modes,
            mode_rows=published_mode_rows,
            group_field="packet_source",
            row_kind="packet",
            summarize=runner._mode_summary,  # noqa: SLF001
        )
        published_comparison = runner._primary_comparison(  # noqa: SLF001
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
            mode_summaries=published_mode_summaries,
        )
        published_execution_contracts = runner._live_execution_contracts(published_mode_rows)  # noqa: SLF001
        family_deltas = runner._family_deltas(  # noqa: SLF001
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
            family_summaries=family_summaries,
        )
        published_family_deltas = runner._family_deltas(  # noqa: SLF001
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
            family_summaries=published_family_summaries,
        )
        packet_source_deltas = benchmark_group_summaries.grouped_deltas(
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
            grouped_summaries=packet_source_summaries,
            compare=runner._summary_comparison,  # noqa: SLF001
        )
        published_packet_source_deltas = benchmark_group_summaries.grouped_deltas(
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
            grouped_summaries=published_packet_source_summaries,
            compare=runner._summary_comparison,  # noqa: SLF001
        )
        adoption_proof = runner._run_live_adoption_proof(repo_root=root, scenarios=ordered_scenarios)  # noqa: SLF001
        runtime_posture = runner._runtime_posture_summary(repo_root=root)  # noqa: SLF001
        if int(adoption_proof.get("sample_size", 0) or 0) > 0:
            runtime_posture["route_ready_rate"] = float(adoption_proof.get("route_ready_rate", 0.0) or 0.0)
            runtime_posture["native_spawn_ready_rate"] = float(
                adoption_proof.get("native_spawn_ready_rate", 0.0) or 0.0
            )
        acceptance = runner._acceptance(  # noqa: SLF001
            mode_summaries=published_mode_summaries,
            primary_comparison=published_comparison,
            family_summaries=published_family_summaries,
            corpus_summary=corpus_summary,
            fairness_findings=fairness_findings,
            runtime_posture=runtime_posture,
            packet_source_summaries=published_packet_source_summaries,
            cache_profile_summaries=cache_profile_summaries,
            execution_contracts=published_execution_contracts,
            comparison_contract=comparison_contract,
        )
        observed_path_sources = sorted(
            {
                str(token).strip()
                for scenario_report in published_scenarios
                for result in scenario_report.get("results", [])
                if isinstance(result, Mapping)
                for token in result.get("observed_path_sources", [])
                if isinstance(result.get("observed_path_sources"), list) and str(token).strip()
            }
        )
        preflight_evidence_modes = sorted(
            {
                str(result.get("preflight_evidence_mode", "")).strip()
                for scenario_report in published_scenarios
                for result in scenario_report.get("results", [])
                if isinstance(result, Mapping) and str(result.get("preflight_evidence_mode", "")).strip()
            }
        )
        preflight_evidence_commands = sorted(
            {
                str(token).strip()
                for scenario_report in published_scenarios
                for result in scenario_report.get("results", [])
                if isinstance(result, Mapping)
                for token in result.get("preflight_evidence_commands", [])
                if isinstance(result.get("preflight_evidence_commands"), list) and str(token).strip()
            }
        )
        preflight_evidence_result_statuses = sorted(
            {
                str(result.get("preflight_evidence_result_status", "")).strip()
                for scenario_report in published_scenarios
                for result in scenario_report.get("results", [])
                if isinstance(result, Mapping) and str(result.get("preflight_evidence_result_status", "")).strip()
            }
        )
        robustness_summary = runner._robustness_summary(  # noqa: SLF001
            cache_profile_summaries=cache_profile_summaries,
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            latency_probes=latency_probes,
        )
        published_mode_table = runner._published_mode_table(  # noqa: SLF001
            mode_summaries=published_mode_summaries,
            mode_order=runner._PUBLIC_PUBLISHED_MODE_ORDER,  # noqa: SLF001
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
            comparison_contract=comparison_contract,
        )
        published_pair_timing_summary = runner._pair_timing_summary(  # noqa: SLF001
            scenarios=published_scenarios,
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
        )
        full_pair_timing_summary = runner._pair_timing_summary(  # noqa: SLF001
            scenarios=[
                scenario
                for cache_profile in cache_profiles
                for scenario in cache_profile_reports.get(cache_profile, [])
                if isinstance(scenario, Mapping)
            ],
            candidate_mode=runner._ODYLITH_ON_MODE,  # noqa: SLF001
            baseline_mode=runner._BASELINE_MODE,  # noqa: SLF001
        )
        tracked_mode_table = runner._published_mode_table(  # noqa: SLF001
            mode_summaries=published_mode_summaries,
            mode_order=modes,
            comparison_contract=comparison_contract,
        )
        report: dict[str, Any] = {
            "contract": runner.REPORT_CONTRACT,
            "version": runner.REPORT_VERSION,
            "generated_utc": generated_utc,
            "repo_root": str(root),
            "benchmark_profile": benchmark_profile,
            "benchmark_profile_label": runner._benchmark_profile_label(benchmark_profile),  # noqa: SLF001
            "benchmark_profile_description": runner._benchmark_profile_description(benchmark_profile),  # noqa: SLF001
            "comparison_contract": comparison_contract,
            "comparison_contract_details": runner._comparison_contract_details(comparison_contract),  # noqa: SLF001
            "selection_strategy": "full_corpus",
            "product_version": runner._product_version_from_pyproject(repo_root=root),  # noqa: SLF001
            "corpus_path": str(runner.store.optimization_evaluation_corpus_path(repo_root=root)),
            "scenario_count": len(primary_scenario_reports),
            "corpus_summary": corpus_summary,
            "corpus_composition": corpus_composition,
            "corpus_contract": runner.odylith_benchmark_contract.benchmark_corpus_contract(  # noqa: SLF001
                odylith_context_cache.read_json_object(runner.store.optimization_evaluation_corpus_path(repo_root=root))
            ),
            "fairness_contract_passed": not fairness_findings,
            "fairness_findings": fairness_findings,
            "observed_path_sources": observed_path_sources,
            "preflight_evidence_mode": preflight_evidence_modes[0]
            if len(preflight_evidence_modes) == 1
            else "mixed"
            if preflight_evidence_modes
            else "none",
            "preflight_evidence_commands": preflight_evidence_commands,
            "preflight_evidence_result_status": preflight_evidence_result_statuses[0]
            if len(preflight_evidence_result_statuses) == 1
            else "mixed"
            if preflight_evidence_result_statuses
            else "not_applicable",
            "preflight_evidence_modes": preflight_evidence_modes,
            "modes": list(modes),
            "cache_profiles": list(cache_profiles),
            "primary_cache_profile": primary_cache_profile,
            "selection": {
                "case_ids": [],
                "scenario_ids": [],
                "family_filters": [],
                "benchmark_profile": benchmark_profile,
                "profile_default_narrowing": "",
                "selection_strategy": "full_corpus",
                "shard_count": 1,
                "shard_index": 1,
                "default_modes_applied": True,
                "default_cache_profiles_applied": True,
                "limit": 0,
                "full_corpus_selected": True,
                "available_scenario_count": len(ordered_scenarios),
                "cache_profiles": list(cache_profiles),
            },
            "latest_eligible": latest_eligible,
            "scenarios": primary_scenario_reports,
            "published_view_strategy": runner._published_view_strategy(cache_profiles=cache_profiles),  # noqa: SLF001
            "published_cache_profiles": list(cache_profiles),
            "published_scenarios": published_scenarios,
            "cache_profile_scenarios": cache_profile_reports,
            "cache_profile_summaries": cache_profile_summaries,
            "singleton_family_latency_probes": latency_probes,
            "mode_summaries": mode_summaries,
            "published_mode_summaries": published_mode_summaries,
            "published_mode_table": published_mode_table,
            "published_mode_table_markdown": runner._published_mode_table_markdown(published_mode_table),  # noqa: SLF001
            "published_pair_timing_summary": published_pair_timing_summary,
            "full_pair_timing_summary": full_pair_timing_summary,
            "tracked_mode_table": tracked_mode_table,
            "tracked_mode_table_markdown": runner._published_mode_table_markdown(tracked_mode_table),  # noqa: SLF001
            "family_summaries": family_summaries,
            "published_family_summaries": published_family_summaries,
            "packet_source_summaries": packet_source_summaries,
            "published_packet_source_summaries": published_packet_source_summaries,
            "execution_contracts": published_execution_contracts,
            "family_deltas": family_deltas,
            "published_family_deltas": published_family_deltas,
            "packet_source_deltas": packet_source_deltas,
            "published_packet_source_deltas": published_packet_source_deltas,
            "primary_comparison": primary_comparison,
            "published_comparison": published_comparison,
            "comparison": published_comparison,
            "adoption_proof": adoption_proof,
            "runtime_posture": runtime_posture,
            "startup_hygiene": startup_hygiene,
            "final_hygiene": final_hygiene,
            "robustness_summary": robustness_summary,
            "status": str(acceptance.get("status", "")).strip() or "unknown",
            "acceptance": acceptance,
            "report_id": report_id,
            "merge_metadata": {
                "source_report_ids": [
                    str(report.get("report_id", "")).strip()
                    for report in reports
                    if str(report.get("report_id", "")).strip()
                ],
                "source_shard_count": shard_count,
                "source_shard_indices": sorted(
                    {
                        int(_mapping(report.get("selection")).get("shard_index", report.get("shard_index", 1)) or 1)
                        for report in reports
                    }
                ),
                "merge_kind": "full_corpus_shard_merge",
            },
        }
        report["published_summary"] = runner.compact_report_summary(report)
        report["summary_text"] = runner._render_report_summary(report)  # noqa: SLF001
        if write_report:
            progress_payload.update(
                {
                    "updated_utc": runner._utc_now(),  # noqa: SLF001
                    "phase": "persisting_report",
                }
            )
            runner._write_progress(repo_root=root, payload=progress_payload)  # noqa: SLF001
            profile_latest_path = runner.latest_report_path(repo_root=root, benchmark_profile=benchmark_profile)
            latest_path = runner.latest_report_path(repo_root=root)
            history_path = runner.history_report_path(repo_root=root, report_id=report_id)
            odylith_context_cache.write_json_if_changed(
                repo_root=root,
                path=profile_latest_path,
                payload=report,
                lock_key=str(profile_latest_path),
            )
            if latest_eligible:
                odylith_context_cache.write_json_if_changed(
                    repo_root=root,
                    path=latest_path,
                    payload=report,
                    lock_key=str(latest_path),
                )
            odylith_context_cache.write_json_if_changed(
                repo_root=root,
                path=history_path,
                payload=report,
                lock_key=str(history_path),
            )
        progress_payload.update(
            {
                "updated_utc": runner._utc_now(),  # noqa: SLF001
                "phase": "final_cleanup",
            }
        )
        runner._write_progress(repo_root=root, payload=progress_payload)  # noqa: SLF001
        runner._clear_progress(repo_root=root)  # noqa: SLF001
        return report
    except Exception:
        progress_payload.update(
            {
                "updated_utc": runner._utc_now(),  # noqa: SLF001
                "status": "failed",
            }
        )
        runner._write_progress(repo_root=root, payload=progress_payload)  # noqa: SLF001
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge benchmark shard history reports into one full-corpus report.")
    parser.add_argument("--repo-root", default=".", help="Repository root that owns the shard history reports.")
    parser.add_argument(
        "report_ref",
        nargs="+",
        help="Shard report ids or JSON paths to merge. The set must cover every shard index exactly once.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Build the merged report but do not write latest/history report files.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = merge_shard_reports(
        repo_root=Path(args.repo_root),
        report_refs=[str(token).strip() for token in args.report_ref if str(token).strip()],
        write_report=not bool(args.no_write),
    )
    print(report.get("summary_text", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
