"""Odylith Benchmark Publication helpers for the Odylith evaluation layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.evaluation import odylith_benchmark_graphs
from odylith.runtime.evaluation import odylith_benchmark_runner
from odylith.runtime.evaluation import odylith_benchmark_tree_identity as tree_identity_runtime


_LIVE_SNAPSHOT_PATH = Path("docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md")
_DIAGNOSTIC_SNAPSHOT_PATH = Path("docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md")
_TABLES_PATH = Path("docs/benchmarks/BENCHMARK_TABLES.md")
_LATEST_SUMMARY_PATH = Path("docs/benchmarks/latest-summary.v1.json")
_PROOF_GRAPH_DIR = Path("docs/benchmarks/proof")
_DIAGNOSTIC_GRAPH_DIR = Path("docs/benchmarks/diagnostic")


def _load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"benchmark report must be an object: {path}")
    report = dict(payload)
    report.setdefault("_report_path", str(path.resolve()))
    return report


def _summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return odylith_benchmark_runner.compact_report_summary(report)


def _public_benchmark_name(*, diagnostic: bool) -> str:
    return "Internal Diagnostic Benchmark" if diagnostic else "Live Benchmark"


def _cache_profiles(summary: Mapping[str, Any]) -> list[str]:
    published = summary.get("published_cache_profiles", [])
    if isinstance(published, list):
        normalized = [str(token).strip() for token in published if str(token).strip()]
        if normalized:
            return normalized
    fallback = str(summary.get("primary_cache_profile", "")).strip()
    return [fallback] if fallback else []


def _quoted_list(tokens: Sequence[str]) -> str:
    normalized = [str(token).strip() for token in tokens if str(token).strip()]
    if not normalized:
        return "`-`"
    if len(normalized) == 1:
        return f"`{normalized[0]}`"
    if len(normalized) == 2:
        return f"`{normalized[0]}` and `{normalized[1]}`"
    head = ", ".join(f"`{token}`" for token in normalized[:-1])
    return f"{head}, and `{normalized[-1]}`"


def _human_duration_label(value: Any) -> str:
    milliseconds = float(value or 0.0)
    if abs(milliseconds) < 1000.0:
        return f"{milliseconds:.3f} ms"
    return odylith_benchmark_runner._human_duration_label(milliseconds)  # noqa: SLF001


def _format_rate(value: Any) -> str:
    return f"{float(value or 0.0):.3f}"


def _format_ratio(value: Any) -> str:
    return f"{float(value or 0.0):.2f}"


def _format_count(value: Any) -> str:
    return f"{int(value or 0):,}"


def _format_percent(value: Any) -> str:
    return f"{float(value or 0.0) * 100:.1f}%"


def _format_token_delta(value: Any) -> str:
    return f"{float(value or 0.0):+,.0f}"


def _format_duration_delta(value: Any) -> str:
    raw = float(value or 0.0)
    sign = "+" if raw >= 0 else "-"
    return f"{sign}{odylith_benchmark_runner._human_duration_label(abs(raw))}"  # noqa: SLF001


def _status_sentence(summary: Mapping[str, Any], *, diagnostic: bool) -> str:
    status = str(summary.get("status", "")).strip() or "unknown"
    report_id = str(summary.get("report_id", "")).strip() or "-"
    generated_utc = str(summary.get("generated_utc", "")).strip() or "-"
    sentence = (
        f"Current {_public_benchmark_name(diagnostic=diagnostic)} report: "
        f"`{report_id}` from `{generated_utc}` with status `{status}`."
    )
    if summary.get("current_tree_identity_match") is False:
        sentence += " This report does not match the current repo tree and is not current-head proof."
    return sentence


def _current_result_lines(summary: Mapping[str, Any], *, diagnostic: bool) -> list[str]:
    scenario_count = _format_count(summary.get("scenario_count", 0))
    cache_profiles = _quoted_list(_cache_profiles(summary))
    claim = str(summary.get("comparison_primary_claim", "")).strip() or str(summary.get("comparison_contract", "")).strip()
    published_pair_count = _format_count(summary.get("published_pair_count", 0))
    lines: list[str] = []
    if diagnostic:
        lines.append(
            f"The latest internal diagnostic benchmark ran `{scenario_count}` seeded scenarios on cache profile(s) "
            f"{cache_profiles} comparing `odylith_on` versus `odylith_off` on packet and prompt construction only."
        )
        lines.append(
            f"Across the `{published_pair_count}` diagnostic pairs, wall clock was "
            f"`{_human_duration_label(summary.get('published_pair_median_wall_clock_ms', 0.0))}` median, "
            f"`{_human_duration_label(summary.get('published_pair_p95_wall_clock_ms', 0.0))}` at `p95`, and "
            f"`{_human_duration_label(summary.get('published_pair_total_wall_clock_ms', 0.0))}` total."
        )
        return lines
    full_pair_count = _format_count(summary.get("full_pair_count", 0))
    lines.append(
        f"The latest live benchmark ran `{scenario_count}` seeded scenarios across matched cache profile(s) "
        f"{cache_profiles} under the declared comparison contract `{claim}`."
    )
    lines.append(
        f"That produced `{full_pair_count}` full matched pairs. The published comparison keeps the conservative "
        f"same-scenario view at `{published_pair_count}` pairs."
    )
    return lines


def _memory_posture_sentence(summary: Mapping[str, Any], *, diagnostic: bool) -> str:
    storage = str(summary.get("runtime_memory_storage", "")).strip()
    sparse = str(summary.get("runtime_memory_sparse_recall", "")).strip()
    remote = str(summary.get("runtime_remote_retrieval_status", "")).strip() or "unknown"
    readiness = bool(summary.get("runtime_memory_backed_retrieval_ready"))
    posture = "Current diagnostic posture" if diagnostic else "Current proof posture"
    substrate_bits = [f"`{storage}`" for storage in (storage,) if storage]
    if sparse:
        substrate_bits.append(f"`{sparse}`")
    if substrate_bits:
        return (
            f"{posture} is local-first on {' plus '.join(substrate_bits)}. "
            f"Remote retrieval is `{remote}` in the selected report. "
            f"Local memory-backed retrieval ready: `{readiness}`."
        )
    return f"{posture} reports remote retrieval as `{remote}`. Local memory-backed retrieval ready: `{readiness}`."


def _metric_lines(summary: Mapping[str, Any], *, diagnostic: bool) -> list[str]:
    metrics: list[tuple[str, str]] = []
    if diagnostic:
        metrics = [
            ("required-path recall", _format_rate(summary.get("required_path_recall_delta"))),
            ("required-path precision", _format_rate(summary.get("required_path_precision_delta"))),
            ("hallucinated-surface rate", _format_rate(summary.get("hallucinated_surface_rate_delta"))),
            ("validation-success proxy", _format_rate(summary.get("validation_success_delta"))),
            ("critical required-path recall", _format_rate(summary.get("critical_required_path_recall_delta"))),
            ("critical validation-success proxy", _format_rate(summary.get("critical_validation_success_delta"))),
            ("expectation-success proxy", _format_rate(summary.get("expectation_success_delta"))),
            ("median prompt-bundle input tokens", _format_token_delta(summary.get("prompt_token_delta"))),
            (
                "median total prompt-bundle payload tokens",
                _format_token_delta(summary.get("total_payload_token_delta")),
            ),
            ("median packet time", _format_duration_delta(summary.get("latency_delta_ms"))),
        ]
    else:
        metrics = [
            ("required-path recall", _format_rate(summary.get("required_path_recall_delta"))),
            ("required-path precision", _format_rate(summary.get("required_path_precision_delta"))),
            ("hallucinated-surface rate", _format_rate(summary.get("hallucinated_surface_rate_delta"))),
            ("validation success", _format_rate(summary.get("validation_success_delta"))),
            ("critical required-path recall", _format_rate(summary.get("critical_required_path_recall_delta"))),
            ("critical validation success", _format_rate(summary.get("critical_validation_success_delta"))),
            ("expectation success", _format_rate(summary.get("expectation_success_delta"))),
            ("write-surface precision", _format_rate(summary.get("write_surface_precision_delta"))),
            ("unnecessary widening", _format_rate(summary.get("unnecessary_widening_rate_delta"))),
            ("median live-session input tokens", _format_token_delta(summary.get("prompt_token_delta"))),
            ("median total model tokens", _format_token_delta(summary.get("total_payload_token_delta"))),
            ("median time to valid outcome", _format_duration_delta(summary.get("latency_delta_ms"))),
        ]
    return [f"- {label} by `{value}`" for label, value in metrics]


def _status_block(summary: Mapping[str, Any], *, diagnostic: bool) -> list[str]:
    hard_gate_failures = [
        str(token).strip()
        for token in summary.get("hard_gate_failure_labels", [])
        if isinstance(summary.get("hard_gate_failure_labels"), list) and str(token).strip()
    ]
    secondary_guardrail_failures = [
        str(token).strip()
        for token in summary.get("secondary_guardrail_failure_labels", [])
        if isinstance(summary.get("secondary_guardrail_failure_labels"), list) and str(token).strip()
    ]
    fairness_findings = [
        str(token).strip()
        for token in summary.get("fairness_findings", [])
        if isinstance(summary.get("fairness_findings"), list) and str(token).strip()
    ]
    weak_families = [
        str(token).strip()
        for token in summary.get("weak_families", [])
        if isinstance(summary.get("weak_families"), list) and str(token).strip()
    ]
    lines = ["## Publication Read", ""]
    if summary.get("current_tree_identity_match") is False:
        lines.extend(
            [
                "The selected report is stale relative to the current repo tree.",
                "- current-tree identity match: `False`",
                "- publication should be refreshed from a fresh current-head proof report before making release claims",
                "",
            ]
        )
    if hard_gate_failures:
        lines.append("The current report is on `hold` because these hard-gate blockers remain:")
        lines.extend(f"- {label}" for label in hard_gate_failures)
    else:
        lines.append("There are no hard-gate blockers on this report.")
    if secondary_guardrail_failures:
        lines.extend(["", "Secondary guardrail blockers:"])
        lines.extend(f"- {label}" for label in secondary_guardrail_failures)
    if fairness_findings:
        lines.append("")
        lines.append("Fairness findings stay release-blocking until they are resolved:")
        lines.extend(f"- {token}" for token in fairness_findings)
    lines.extend(
        [
            "",
            f"- fairness contract passed: `{bool(summary.get('fairness_contract_passed'))}`",
            f"- corpus seriousness floor passed: `{bool(summary.get('corpus_seriousness_floor_passed'))}`",
            f"- full tracked-corpus coverage rate: `{float(summary.get('corpus_full_coverage_rate', 0.0) or 0.0):.3f}`",
            f"- operating-policy scenarios in tracked corpus: `{_format_count(summary.get('corpus_implementation_scenario_count', 0))}`",
            f"- write-plus-validator scenarios in tracked corpus: `{_format_count(summary.get('corpus_write_plus_validator_scenario_count', 0))}`",
            f"- correctness-critical scenarios in tracked corpus: `{_format_count(summary.get('corpus_correctness_critical_scenario_count', 0))}`",
            f"- mechanism-heavy operating-policy ratio: `{_format_ratio(summary.get('corpus_mechanism_heavy_implementation_ratio'))}`",
        ]
    )
    if weak_families:
        lines.extend(
            [
                "",
                "Current diagnostic weak families:" if diagnostic else "Current attention families on the published view:",
            ]
        )
        lines.extend(f"- `{family}`" for family in weak_families)
    return lines


def _reading_notes(summary: Mapping[str, Any], *, diagnostic: bool) -> list[str]:
    if diagnostic:
        return [
            "- `odylith_off` is the raw prompt-bundle control for this mechanism-evidence view.",
            "- Prompt-visible path credit and Turn Gate evidence must remain explicit in the report contract.",
            f"- {_memory_posture_sentence(summary, diagnostic=True)}",
            "- Diagnostic gains only matter if they preserve or improve the live proof lane.",
        ]
    lines = [
        "- Time to valid outcome and full-session token spend stay published as diagnostics, not status blockers.",
        f"- {_memory_posture_sentence(summary, diagnostic=False)}",
        (
            "- Operating-posture diagnostics: auto-grounded "
            f"`{_format_percent(summary.get('odylith_auto_grounded_rate'))}`, delegated "
            f"`{_format_percent(summary.get('odylith_grounded_delegate_rate'))}`, widening "
            f"`{_format_percent(summary.get('odylith_requires_widening_rate'))}`, and workspace-daemon reuse "
            f"`{_format_percent(summary.get('odylith_workspace_daemon_reuse_rate'))}`."
        ),
    ]
    if len(_cache_profiles(summary)) > 1:
        lines.append(
            f"- Warm/cold robustness consistency cleared: `{bool(summary.get('robustness_warm_cold_consistency_cleared'))}`."
        )
    return lines


def render_live_snapshot_markdown(report: Mapping[str, Any]) -> str:
    summary = _summary(report)
    lines = [
        "# Live Benchmark Snapshot",
        "",
        "This note carries the fuller interpretation behind the short benchmark summary",
        "published in the root [README](../../README.md).",
        "",
        "## Current Result",
        "",
        _status_sentence(summary, diagnostic=False),
        "",
        *_current_result_lines(summary, diagnostic=False),
        "",
        _memory_posture_sentence(summary, diagnostic=False),
        "",
        "## Headline Movement",
        "",
        "Compared with `odylith_off`, Odylith moved:",
        "",
        *_metric_lines(summary, diagnostic=False),
        "",
        *_status_block(summary, diagnostic=False),
        "",
        "## Reading Notes",
        "",
        *_reading_notes(summary, diagnostic=False),
        "",
    ]
    return "\n".join(lines)


def render_diagnostic_snapshot_markdown(report: Mapping[str, Any]) -> str:
    summary = _summary(report)
    lines = [
        "# Internal Diagnostic Benchmark Snapshot",
        "",
        "This note carries the fuller interpretation behind the short diagnostic summary",
        "published in the root [README](../../README.md).",
        "",
        "## Current Result",
        "",
        _status_sentence(summary, diagnostic=True),
        "",
        *_current_result_lines(summary, diagnostic=True),
        "",
        _memory_posture_sentence(summary, diagnostic=True),
        "",
        "## Headline Movement",
        "",
        "Compared with the `odylith_off` prompt bundle, Odylith moved:",
        "",
        *_metric_lines(summary, diagnostic=True),
        "",
        *_status_block(summary, diagnostic=True),
        "",
        "## Reading Notes",
        "",
        *_reading_notes(summary, diagnostic=True),
        "",
    ]
    return "\n".join(lines)


def _table_markdown(title: str, table: Mapping[str, Any], note_lines: Sequence[str]) -> str:
    display_mode_order = [
        str(token).strip()
        for token in table.get("display_mode_order", [])
        if isinstance(table.get("display_mode_order"), list) and str(token).strip()
    ]
    if len(display_mode_order) < 2:
        raise ValueError(f"benchmark table missing lane order: {title}")
    left_mode, right_mode = display_mode_order[:2]
    lines = [
        f"## {title}",
        "",
        f"| Signal | {left_mode} | {right_mode} | Delta | Why It Matters |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in table.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        values = dict(row.get("values", {})) if isinstance(row.get("values"), Mapping) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("label", "")).strip(),
                    str(values.get(left_mode, "")).strip(),
                    str(values.get(right_mode, "")).strip(),
                    str(row.get("delta", "")).strip(),
                    str(row.get("why_it_matters", "")).strip(),
                ]
            )
            + " |"
        )
    if note_lines:
        lines.extend(["", *note_lines, ""])
    return "\n".join(lines)


def render_benchmark_tables_markdown(
    *, live_report: Mapping[str, Any], diagnostic_report: Mapping[str, Any]
) -> str:
    live_summary = _summary(live_report)
    diagnostic_summary = _summary(diagnostic_report)
    diagnostic_table = (
        dict(diagnostic_report.get("published_mode_table", {}))
        if isinstance(diagnostic_report.get("published_mode_table"), Mapping)
        else {}
    )
    live_table = (
        dict(live_report.get("published_mode_table", {}))
        if isinstance(live_report.get("published_mode_table"), Mapping)
        else {}
    )
    if not diagnostic_table or not live_table:
        raise ValueError("benchmark publication requires both diagnostic and live published tables")
    sections = [
        "# Benchmark Tables",
        "",
        "This note holds the detailed benchmark tables linked from the root",
        "[README](../../README.md).",
        "",
        "Benchmark metric order:",
        "[Odylith Benchmark Metrics And Priorities](METRICS_AND_PRIORITIES.md)",
        "",
        "Methodology and reviewer protocol:",
        "[How To Read Odylith's Benchmark Proof](README.md) and",
        "[Reviewer Guide And Prompt](REVIEWER_GUIDE.md)",
        "",
        "Family-by-family corpus map:",
        "[Benchmark Families And Eval Catalog](FAMILIES_AND_EVALS.md)",
        "",
        _table_markdown(
            "Internal Diagnostic Signal Table",
            diagnostic_table,
            [
                "> [!NOTE]",
                f"> Current diagnostic status: `{str(diagnostic_summary.get('status', '')).strip()}`.",
                f"> Fairness contract passed: `{bool(diagnostic_summary.get('fairness_contract_passed'))}`.",
                f"> Corpus seriousness floor passed: `{bool(diagnostic_summary.get('corpus_seriousness_floor_passed'))}`.",
            ],
        ),
        _table_markdown(
            "Live Signal Table",
            live_table,
            [
                "> [!NOTE]",
                f"> Current live-proof status: `{str(live_summary.get('status', '')).strip()}`.",
                f"> Comparison contract: `{str(live_summary.get('comparison_primary_claim', '')).strip()}`.",
                f"> Fairness contract passed: `{bool(live_summary.get('fairness_contract_passed'))}`.",
                f"> Full tracked-corpus coverage rate: `{float(live_summary.get('corpus_full_coverage_rate', 0.0) or 0.0):.3f}`.",
                "> `benchmark_compare` remains release-warn until a shipped release baseline is recorded in `docs/benchmarks/release-baselines.v1.json`.",
            ],
        ),
    ]
    return "\n".join(sections)


def _write_text_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _write_json_if_changed(path: Path, payload: Mapping[str, Any]) -> bool:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return _write_text_if_changed(path, rendered)


def _write_profile_graphs_if_changed(
    *,
    repo_root: Path,
    profile: str,
    report: Mapping[str, Any],
) -> list[str]:
    root = Path(repo_root).resolve()
    target_dir = root / (_PROOF_GRAPH_DIR if profile == "proof" else _DIAGNOSTIC_GRAPH_DIR)
    changed: list[str] = []
    for name, content in odylith_benchmark_graphs.render_graph_asset_contents(report).items():
        path = target_dir / name
        if _write_text_if_changed(path, content):
            changed.append(str(path.relative_to(root)))
    return changed


def write_publication_artifacts(
    *,
    repo_root: Path,
    live_report: Mapping[str, Any],
    diagnostic_report: Mapping[str, Any],
) -> list[str]:
    root = Path(repo_root).resolve()
    changed: list[str] = []
    writes = [
        (root / _LIVE_SNAPSHOT_PATH, render_live_snapshot_markdown(live_report)),
        (root / _DIAGNOSTIC_SNAPSHOT_PATH, render_diagnostic_snapshot_markdown(diagnostic_report)),
        (
            root / _TABLES_PATH,
            render_benchmark_tables_markdown(
                live_report=live_report,
                diagnostic_report=diagnostic_report,
            ),
        ),
    ]
    for path, content in writes:
        if _write_text_if_changed(path, content):
            changed.append(str(path.relative_to(root)))
    latest_summary = _summary(live_report)
    if _write_json_if_changed(root / _LATEST_SUMMARY_PATH, latest_summary):
        changed.append(str(_LATEST_SUMMARY_PATH))
    changed.extend(_write_profile_graphs_if_changed(repo_root=root, profile="proof", report=live_report))
    changed.extend(_write_profile_graphs_if_changed(repo_root=root, profile="diagnostic", report=diagnostic_report))
    return changed


def _default_report_path(repo_root: Path, filename: str) -> Path:
    return (Path(repo_root).resolve() / ".odylith/runtime/odylith-benchmarks" / filename).resolve()


def _validate_selected_report(*, repo_root: Path, path: Path, report: Mapping[str, Any]) -> None:
    if not tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=repo_root, report=report):
        raise ValueError(
            f"benchmark publication refused `{path}` because it does not match the current repo tree identity"
        )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh benchmark publication markdown, latest-summary JSON, and README-linked profile SVGs "
            "from selected reports."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--live-report")
    parser.add_argument("--diagnostic-report")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    live_report_path = (
        Path(args.live_report).resolve()
        if args.live_report
        else _default_report_path(repo_root, "latest-proof.v1.json")
    )
    diagnostic_report_path = (
        Path(args.diagnostic_report).resolve()
        if args.diagnostic_report
        else _default_report_path(repo_root, "latest-diagnostic.v1.json")
    )
    live_report = _load_report(live_report_path)
    diagnostic_report = _load_report(diagnostic_report_path)
    _validate_selected_report(repo_root=repo_root, path=live_report_path, report=live_report)
    _validate_selected_report(repo_root=repo_root, path=diagnostic_report_path, report=diagnostic_report)
    changed = write_publication_artifacts(
        repo_root=repo_root,
        live_report=live_report,
        diagnostic_report=diagnostic_report,
    )
    print(
        json.dumps(
            {
                "live_report": str(live_report_path),
                "diagnostic_report": str(diagnostic_report_path),
                "changed": changed,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
