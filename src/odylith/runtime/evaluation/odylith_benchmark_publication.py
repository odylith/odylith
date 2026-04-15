from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.evaluation import odylith_benchmark_runner


_LIVE_SNAPSHOT_PATH = Path("docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md")
_DIAGNOSTIC_SNAPSHOT_PATH = Path("docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md")
_TABLES_PATH = Path("docs/benchmarks/BENCHMARK_TABLES.md")
_LATEST_SUMMARY_PATH = Path("docs/benchmarks/latest-summary.v1.json")


def _load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"benchmark report must be an object: {path}")
    return dict(payload)


def _summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return odylith_benchmark_runner.compact_report_summary(report)


def _format_rate(value: Any) -> str:
    return f"{float(value or 0.0):.3f}"


def _format_ratio(value: Any) -> str:
    return f"{float(value or 0.0):.2f}"


def _format_count(value: Any) -> str:
    return f"{int(value or 0):,}"


def _format_token_delta(value: Any) -> str:
    return f"{float(value or 0.0):+,.0f}"


def _format_duration_delta(value: Any) -> str:
    raw = float(value or 0.0)
    sign = "+" if raw >= 0 else "-"
    return f"{sign}{odylith_benchmark_runner._human_duration_label(abs(raw))}"  # noqa: SLF001


def _status_sentence(summary: Mapping[str, Any]) -> str:
    status = str(summary.get("status", "")).strip() or "unknown"
    report_id = str(summary.get("report_id", "")).strip() or "-"
    generated_utc = str(summary.get("generated_utc", "")).strip() or "-"
    return f"Current report: `{report_id}` from `{generated_utc}` with status `{status}`."


def _profile_sentence(summary: Mapping[str, Any]) -> str:
    scenario_count = _format_count(summary.get("scenario_count", 0))
    published_cache_profiles = [
        str(token).strip()
        for token in summary.get("published_cache_profiles", [])
        if isinstance(summary.get("published_cache_profiles"), list) and str(token).strip()
    ]
    cache_profiles = ", ".join(published_cache_profiles) or str(summary.get("primary_cache_profile", "warm")).strip() or "warm"
    claim = str(summary.get("comparison_primary_claim", "")).strip() or str(summary.get("comparison_contract", "")).strip()
    return (
        f"The current published view covers `{scenario_count}` scenarios on cache profile(s) `{cache_profiles}` "
        f"under the declared comparison contract `{claim}`."
    )


def _fairness_sentence(summary: Mapping[str, Any]) -> str:
    fairness_passed = bool(summary.get("fairness_contract_passed"))
    seriousness_passed = bool(summary.get("corpus_seriousness_floor_passed"))
    full_coverage = float(summary.get("corpus_full_coverage_rate", 0.0) or 0.0)
    return (
        f"Fairness contract passed: `{fairness_passed}`. "
        f"Corpus seriousness floor passed: `{seriousness_passed}`. "
        f"Tracked full-corpus coverage rate: `{full_coverage:.3f}`."
    )


def _metric_lines(summary: Mapping[str, Any], *, diagnostic: bool) -> list[str]:
    metrics: list[tuple[str, str]] = []
    if diagnostic:
        metrics = [
            ("required-path recall", _format_rate(summary.get("required_path_recall_delta"))),
            ("required-path precision", _format_rate(summary.get("required_path_precision_delta"))),
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


def _status_block(summary: Mapping[str, Any]) -> list[str]:
    hard_gate_failures = [
        str(token).strip()
        for token in summary.get("hard_gate_failure_labels", [])
        if isinstance(summary.get("hard_gate_failure_labels"), list) and str(token).strip()
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
    if hard_gate_failures:
        lines.append("There are hard-gate blockers on this report.")
        lines.extend(f"- {label}" for label in hard_gate_failures)
    else:
        lines.append("There are no hard-gate blockers on this report.")
    if fairness_findings:
        lines.append("")
        lines.append("Fairness findings:")
        lines.extend(f"- {token}" for token in fairness_findings)
    lines.extend(
        [
            "",
            f"- fairness contract passed: `{bool(summary.get('fairness_contract_passed'))}`",
            f"- corpus seriousness floor passed: `{bool(summary.get('corpus_seriousness_floor_passed'))}`",
            f"- full tracked-corpus coverage rate: `{float(summary.get('corpus_full_coverage_rate', 0.0) or 0.0):.3f}`",
            f"- implementation scenarios in tracked corpus: `{_format_count(summary.get('corpus_implementation_scenario_count', 0))}`",
            f"- write-plus-validator scenarios in tracked corpus: `{_format_count(summary.get('corpus_write_plus_validator_scenario_count', 0))}`",
            f"- correctness-critical scenarios in tracked corpus: `{_format_count(summary.get('corpus_correctness_critical_scenario_count', 0))}`",
            f"- mechanism-heavy implementation ratio: `{_format_ratio(summary.get('corpus_mechanism_heavy_implementation_ratio'))}`",
        ]
    )
    if weak_families:
        lines.extend(["", "Current attention families:"])
        lines.extend(f"- `{family}`" for family in weak_families)
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
        _status_sentence(summary),
        "",
        _profile_sentence(summary),
        "",
        _fairness_sentence(summary),
        "",
        "## Headline Movement",
        "",
        "Compared with `odylith_off`, Odylith moved:",
        "",
        *_metric_lines(summary, diagnostic=False),
        "",
        *_status_block(summary),
        "",
        "## Reading Notes",
        "",
        "- This is the full-product assistance lane, not the narrower packet-only diagnostic lane.",
        "- Timing is matched-pair benchmark wall clock to a valid outcome, not solo-user interactive latency.",
        "- Token totals are full multi-turn host-session spend, not just the first prompt.",
        "- Publication claims should be refreshed only from a validated proof report selected for publication.",
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
        _status_sentence(summary),
        "",
        _profile_sentence(summary),
        "",
        _fairness_sentence(summary),
        "",
        "## Headline Movement",
        "",
        "Compared with `odylith_off`, Odylith moved:",
        "",
        *_metric_lines(summary, diagnostic=True),
        "",
        *_status_block(summary),
        "",
        "## Reading Notes",
        "",
        "- This is the internal packet-and-prompt diagnostic lane, not the product-claim lane.",
        "- Prompt-visible path credit and preflight evidence must remain explicit in the report contract.",
        "- Diagnostic gains only matter if they preserve or improve the live proof lane.",
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
    return changed


def _default_report_path(repo_root: Path, filename: str) -> Path:
    return (Path(repo_root).resolve() / ".odylith/runtime/odylith-benchmarks" / filename).resolve()


def _validate_selected_report(*, repo_root: Path, path: Path, report: Mapping[str, Any]) -> None:
    if not odylith_benchmark_runner.benchmark_report_matches_current_tree(repo_root=repo_root, report=report):
        raise ValueError(
            f"benchmark publication refused `{path}` because it does not match the current repo tree identity"
        )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh benchmark publication markdown and latest-summary JSON from selected reports."
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
    if not args.live_report:
        _validate_selected_report(repo_root=repo_root, path=live_report_path, report=live_report)
    if not args.diagnostic_report:
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
