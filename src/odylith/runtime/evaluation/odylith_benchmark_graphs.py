"""Render benchmark SVGs directly from Odylith benchmark reports.

This module is the maintained README benchmark graph contract for Odylith
release work. Keep the filenames, proof-host framing, and visual tone stable across
releases unless the product is intentionally redesigning the benchmark story.
"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping, Sequence

from odylith.runtime.evaluation import odylith_benchmark_marketing_graphs as marketing_graphs
from odylith.runtime.evaluation import odylith_benchmark_runner
from odylith.runtime.evaluation import odylith_benchmark_taxonomy


SVG_WIDTH = 1600
SVG_HEIGHT = 900
_BG = "#f6f1e7"
_PANEL = "#fffdfa"
_GRID = "#d8cfbd"
_TEXT = "#17202a"
_MUTED = "#5f6b76"
_BASELINE = "#c75b52"
_ODYLITH = "#0f766e"
_ODYLITH_DARK = "#115e59"
_FRONTIER_BASELINE = "#b64035"
_FRONTIER_ODYLITH = "#007f8c"
_GOOD = "#1d7f63"
_WARN = "#b7791f"
_BAD = "#b42318"
_NEUTRAL = "#ece5d8"

FRONTIER_FILENAME = "odylith-benchmark-frontier.svg"
HEATMAP_FILENAME = "odylith-benchmark-family-heatmap.svg"
POSTURE_FILENAME = "odylith-benchmark-operating-posture.svg"
QUALITY_FRONTIER_FILENAME = marketing_graphs.QUALITY_FRONTIER_FILENAME
FRONTIER_TITLE = "Odylith benchmark frontier"
HEATMAP_TITLE = "Odylith benchmark family heatmap"
POSTURE_TITLE = "Odylith benchmark operating posture"
QUALITY_FRONTIER_TITLE = marketing_graphs.QUALITY_FRONTIER_TITLE
FRONTIER_HEADING = "Live Benchmark: time to valid outcome vs live session input"
HEATMAP_HEADING = "Live Benchmark Family Heatmap: where Odylith wins"
POSTURE_HEADING = "Live Benchmark operating posture on the current proof-host corpus"
QUALITY_FRONTIER_HEADING = marketing_graphs.QUALITY_FRONTIER_HEADING
_VISUAL_CANDIDATE_MODE = "odylith_on"
_VISUAL_BASELINE_MODE = "raw_agent_baseline"
_REPO_SCAN_BASELINE_MODE = "odylith_repo_scan_baseline"
_LEGACY_REPO_SCAN_BASELINE_MODE = "full_scan_baseline"


def _normalize_mode(mode: str) -> str:
    return odylith_benchmark_runner._normalize_mode(str(mode or "").strip())  # noqa: SLF001


def _lookup_mode_mapping(mapping: Mapping[str, Any], mode: str) -> Any:
    target = _normalize_mode(mode)
    for key, value in mapping.items():
        if _normalize_mode(str(key).strip()) == target:
            return value
    return None


def _comparison_contract(report: Mapping[str, Any]) -> str:
    return str(report.get("comparison_contract", "")).strip() or "live_end_to_end"


def _is_live_end_to_end(report: Mapping[str, Any]) -> bool:
    return _comparison_contract(report) == "live_end_to_end"


def _token_axis_noun(report: Mapping[str, Any]) -> str:
    return "live session input" if _is_live_end_to_end(report) else "prompt-bundle input"


def _token_axis_label(report: Mapping[str, Any]) -> str:
    if _is_live_end_to_end(report):
        return "Live session input tokens"
    return f"{_token_axis_noun(report).capitalize()} tokens"


def _time_axis_noun(report: Mapping[str, Any]) -> str:
    return "time to valid outcome" if _is_live_end_to_end(report) else "packet time"


def _time_axis_label(report: Mapping[str, Any]) -> str:
    if _is_live_end_to_end(report):
        return _time_axis_noun(report).capitalize()
    return f"{_time_axis_noun(report).capitalize()} (ms)"


def _public_benchmark_name(report: Mapping[str, Any]) -> str:
    return "Live Benchmark" if _is_live_end_to_end(report) else "Grounding Benchmark"


def _frontier_heading(report: Mapping[str, Any]) -> str:
    if _is_live_end_to_end(report):
        return FRONTIER_HEADING
    return "Grounding Benchmark: packet/prompt time vs prompt-bundle input"


def _heatmap_heading(report: Mapping[str, Any]) -> str:
    if _is_live_end_to_end(report):
        return HEATMAP_HEADING
    return "Grounding Benchmark Family Heatmap: where Odylith wins"


def _posture_heading(report: Mapping[str, Any]) -> str:
    if _is_live_end_to_end(report):
        return POSTURE_HEADING
    return "Grounding Benchmark operating posture on the current proof-host corpus"


def _report_source_label(report: Mapping[str, Any]) -> str:
    return marketing_graphs._report_source_label(report)  # noqa: SLF001


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _short_family(value: str) -> str:
    token = str(value or "").strip().replace("_", " ").replace("-", " ")
    words = [part.capitalize() for part in token.split()]
    return " ".join(words)


def _short_label(value: str, *, limit: int = 34) -> str:
    token = " ".join(str(value or "").strip().replace("-", " ").split())
    if len(token) <= limit:
        return token
    return token[: max(0, limit - 1)].rstrip() + "..."


def _fmt_int(value: float) -> str:
    return f"{int(round(float(value or 0.0)))}"


def _fmt_ms(value: float) -> str:
    return f"{float(value or 0.0):.3f} ms"


def _fmt_delta(value: float, *, digits: int = 1) -> str:
    number = float(value or 0.0)
    if digits == 0:
        return f"{number:+.0f}"
    return f"{number:+.{digits}f}"


def _fmt_rate(value: float) -> str:
    return f"{float(value or 0.0):.3f}"


def _fmt_pct(value: float) -> str:
    return f"{float(value or 0.0) * 100:.0f}%"


def _human_duration_label(milliseconds: float) -> str:
    if abs(float(milliseconds or 0.0)) < 1e-9:
        return "0s"
    return odylith_benchmark_runner._human_duration_label(milliseconds)  # noqa: SLF001


def _compact_number_label(value: float) -> str:
    number = float(value or 0.0)
    abs_number = abs(number)
    if abs_number >= 1_000_000:
        label = f"{number / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{label}M"
    if abs_number >= 1_000:
        label = f"{number / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{label}k"
    return odylith_benchmark_runner._human_number_label(number)  # noqa: SLF001


def _signed_human_duration_label(milliseconds: float) -> str:
    number = float(milliseconds or 0.0)
    if abs(number) < 1e-9:
        return "0s"
    sign = "+" if number >= 0.0 else "-"
    return f"{sign}{_human_duration_label(abs(number))}"


def _relative_delta_percent_label(delta: float, baseline: float) -> str:
    baseline_value = float(baseline or 0.0)
    if abs(baseline_value) < 1e-9:
        if abs(float(delta or 0.0)) < 1e-9:
            return "0%"
        return _signed_human_duration_label(delta) if abs(delta) >= 1000.0 else f"{float(delta or 0.0):+.0f}"
    pct = (float(delta or 0.0) / baseline_value) * 100.0
    if abs(pct) >= 10.0:
        return f"{pct:+.0f}%"
    return f"{pct:+.1f}%"


def _svg_canvas(*, title: str, body: Sequence[str], width: int = SVG_WIDTH, height: int = SVG_HEIGHT) -> str:
    style = """
    <style>
      text { fill: %s; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
      .title { font-size: 30px; font-weight: 700; }
      .subtitle { font-size: 15px; fill: %s; }
      .axis { font-size: 14px; fill: %s; }
      .label { font-size: 13px; fill: %s; }
      .small { font-size: 12px; fill: %s; }
      .chip { font-size: 12px; font-weight: 700; }
      .value { font-size: 16px; font-weight: 700; }
      .cell { font-size: 12px; font-weight: 700; text-anchor: middle; dominant-baseline: middle; }
    </style>
    """ % (_TEXT, _MUTED, _MUTED, _MUTED, _MUTED)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(title)}">'
        f"<title>{_esc(title)}</title>"
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="24" fill="{_BG}"/>'
        f"{style}"
        + "".join(body)
        + "</svg>"
    )


def _nice_tick_step(max_value: float, tick_count: int = 6) -> float:
    if max_value <= 0:
        return 1.0
    rough = max_value / max(1, tick_count)
    magnitude = 10 ** math.floor(math.log10(rough))
    for factor in (1, 2, 5, 10):
        step = factor * magnitude
        if step >= rough:
            return step
    return 10 * magnitude


def _nice_axis_max(values: Iterable[float], *, tick_count: int = 6) -> float:
    rows = [float(value or 0.0) for value in values]
    if not rows:
        return 1.0
    step = _nice_tick_step(max(rows), tick_count=tick_count)
    return step * math.ceil(max(rows) / step)


def _scale(value: float, *, domain_min: float, domain_max: float, range_min: float, range_max: float) -> float:
    if domain_max <= domain_min:
        return range_min
    ratio = (float(value) - domain_min) / (domain_max - domain_min)
    return range_min + (range_max - range_min) * ratio


def _diamond_points(x: float, y: float, size: float) -> str:
    return " ".join(
        f"{px:.2f},{py:.2f}"
        for px, py in (
            (x, y - size),
            (x + size, y),
            (x, y + size),
            (x - size, y),
        )
    )


def _lerp_color(start_hex: str, end_hex: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, float(ratio)))

    def _rgb(token: str) -> tuple[int, int, int]:
        raw = token.lstrip("#")
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)

    start = _rgb(start_hex)
    end = _rgb(end_hex)
    blended = tuple(round(a + (b - a) * ratio) for a, b in zip(start, end, strict=True))
    return "#%02x%02x%02x" % blended


def _heat_color(value: float, *, max_abs: float, positive_good: bool) -> str:
    if max_abs <= 0 or abs(value) < 1e-9:
        return _NEUTRAL
    ratio = min(abs(float(value)) / max_abs, 1.0)
    good = (value > 0 and positive_good) or (value < 0 and not positive_good)
    if good:
        return _lerp_color(_NEUTRAL, _GOOD, 0.25 + 0.75 * ratio)
    return _lerp_color(_NEUTRAL, _BAD, 0.2 + 0.8 * ratio)


def _report_meta(report: Mapping[str, Any]) -> str:
    benchmark_profile = str(report.get("benchmark_profile", "")).strip()
    published_strategy = str(report.get("published_view_strategy", "")).strip()
    published_profiles = [
        str(token).strip()
        for token in report.get("published_cache_profiles", [])
        if str(token).strip()
    ] if isinstance(report.get("published_cache_profiles"), list) else []
    strategy_suffix = ""
    if benchmark_profile:
        strategy_suffix = f" | {_public_benchmark_name(report)}"
    if published_strategy:
        strategy_suffix += f" | {published_strategy}"
        if published_profiles:
            strategy_suffix += f" ({', '.join(published_profiles)})"
    return (
        f"Report {report.get('report_id', '')} | "
        f"{report.get('generated_utc', '')} | "
        f"{report.get('scenario_count', 0)} scenarios"
        f"{strategy_suffix}"
    )


def _wrap_words(value: str, *, limit: int) -> list[str]:
    words = [token for token in str(value or "").split() if token]
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= limit:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines


def _report_meta_lines(report: Mapping[str, Any], *, limit: int = 54) -> list[str]:
    return _wrap_words(_report_meta(report), limit=limit)


def _append_text_lines(
    body: list[str],
    *,
    x: float,
    y: float,
    lines: Sequence[str],
    class_name: str,
    line_height: int,
    text_anchor: str | None = None,
    fill: str | None = None,
    font_weight: str | None = None,
) -> float:
    if not lines:
        return y
    extras: list[str] = []
    if text_anchor:
        extras.append(f'text-anchor="{text_anchor}"')
    if fill:
        extras.append(f'fill="{fill}"')
    if font_weight:
        extras.append(f'font-weight="{font_weight}"')
    extra = ""
    if extras:
        extra = " " + " ".join(extras)
    for index, line in enumerate(lines):
        body.append(f'<text x="{x}" y="{y + index * line_height}" class="{class_name}"{extra}>{_esc(line)}</text>')
    return y + (len(lines) - 1) * line_height


def _percentile(values: Iterable[float], quantile: float) -> float:
    rows = sorted(float(value or 0.0) for value in values)
    if not rows:
        return 0.0
    if len(rows) == 1:
        return rows[0]
    position = max(0.0, min(1.0, float(quantile))) * (len(rows) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return rows[lower]
    weight = position - lower
    return rows[lower] + (rows[upper] - rows[lower]) * weight


def _focus_axis(values: Iterable[float], *, tick_count: int, focus_quantile: float = 0.95) -> dict[str, float]:
    rows = [float(value or 0.0) for value in values]
    if not rows:
        return {
            "focus_max": 1.0,
            "global_max": 1.0,
            "outlier_count": 0.0,
        }
    global_max = max(rows)
    focus_target = max(_percentile(rows, focus_quantile), 1.0)
    focus_max = _nice_axis_max([focus_target], tick_count=tick_count)
    if focus_max >= global_max:
        focus_max = _nice_axis_max(rows, tick_count=tick_count)
    outlier_count = sum(value > focus_max + 1e-9 for value in rows)
    return {
        "focus_max": focus_max,
        "global_max": global_max,
        "outlier_count": float(outlier_count),
    }


def _report_comparison(report: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(report.get("published_comparison"), Mapping):
        return dict(report.get("published_comparison", {}))
    if isinstance(report.get("primary_comparison"), Mapping):
        return dict(report.get("primary_comparison", {}))
    return {}


def _report_scenarios(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = report.get("published_scenarios")
    if isinstance(rows, list):
        return [dict(row) for row in rows if isinstance(row, Mapping)]
    rows = report.get("scenarios")
    if isinstance(rows, list):
        return [dict(row) for row in rows if isinstance(row, Mapping)]
    return []


def _report_family_summaries(report: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(report.get("published_family_summaries"), Mapping):
        return dict(report.get("published_family_summaries", {}))
    if isinstance(report.get("family_summaries"), Mapping):
        return dict(report.get("family_summaries", {}))
    return {}


def _report_family_deltas(report: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(report.get("published_family_deltas"), Mapping):
        return dict(report.get("published_family_deltas", {}))
    if isinstance(report.get("family_deltas"), Mapping):
        return dict(report.get("family_deltas", {}))
    return {}


def _mode_label(mode: str) -> str:
    labels = {
        "odylith_on": "Odylith on",
        "odylith_on_no_fanout": "Odylith on (no fanout)",
        "odylith_repo_scan_baseline": "Repo-scan baseline",
        "full_scan_baseline": "Repo-scan baseline",
        "raw_agent_baseline": "odylith_off (raw host CLI)",
        "odylith_off": "odylith_off (raw host CLI)",
    }
    token = str(mode or "").strip()
    if token in labels:
        return labels[token]
    return _short_family(token)


def _mode_compact_label(mode: str) -> str:
    labels = {
        "odylith_on": "Odylith on",
        "odylith_on_no_fanout": "Odylith on / no fanout",
        "odylith_repo_scan_baseline": "Repo-scan baseline",
        "full_scan_baseline": "Repo-scan baseline",
        "raw_agent_baseline": "odylith_off / raw host CLI",
        "odylith_off": "odylith_off / raw host CLI",
    }
    token = str(mode or "").strip()
    if token in labels:
        return labels[token]
    return _short_family(token)


def _mode_short_label(mode: str) -> str:
    labels = {
        "odylith_on": "on",
        "odylith_on_no_fanout": "on",
        "odylith_repo_scan_baseline": "scan",
        "full_scan_baseline": "scan",
        "raw_agent_baseline": "off",
        "odylith_off": "off",
    }
    token = str(mode or "").strip()
    if token in labels:
        return labels[token]
    return _short_family(token).lower()


def _report_mode_order(report: Mapping[str, Any]) -> list[str]:
    published_table = dict(report.get("published_mode_table", {})) if isinstance(report.get("published_mode_table"), Mapping) else {}
    rows = published_table.get("mode_order", [])
    if isinstance(rows, list):
        ordered = [_normalize_mode(str(mode).strip()) for mode in rows if str(mode).strip()]
        if ordered:
            return list(dict.fromkeys(mode for mode in ordered if mode))

    ordered: list[str] = []

    def _add(mode: Any) -> None:
        token = _normalize_mode(str(mode or "").strip())
        if token and token not in ordered:
            ordered.append(token)

    comparison = _report_comparison(report)
    _add(comparison.get("candidate_mode"))
    _add(comparison.get("baseline_mode"))
    for scenario in _report_scenarios(report):
        for row in scenario.get("results", []):
            if isinstance(row, Mapping):
                _add(row.get("mode"))
    for family_modes in _report_family_summaries(report).values():
        if not isinstance(family_modes, Mapping):
            continue
        for mode in family_modes.keys():
            _add(mode)
    return ordered


def _graph_comparison(report: Mapping[str, Any]) -> dict[str, Any]:
    comparison = _report_comparison(report)
    ordered_modes = _report_mode_order(report)
    available_modes = {str(mode).strip() for mode in ordered_modes if str(mode).strip()}
    candidate_mode = _normalize_mode(str(comparison.get("candidate_mode", "")).strip() or _VISUAL_CANDIDATE_MODE)
    baseline_mode = _normalize_mode(str(comparison.get("baseline_mode", "")).strip() or _VISUAL_BASELINE_MODE)
    if _VISUAL_CANDIDATE_MODE in available_modes and _VISUAL_BASELINE_MODE in available_modes:
        candidate_mode = _VISUAL_CANDIDATE_MODE
        baseline_mode = _VISUAL_BASELINE_MODE
    elif candidate_mode not in available_modes and _VISUAL_CANDIDATE_MODE in available_modes:
        candidate_mode = _VISUAL_CANDIDATE_MODE
    elif candidate_mode not in available_modes and ordered_modes:
        candidate_mode = ordered_modes[0]

    if baseline_mode not in available_modes:
        if _REPO_SCAN_BASELINE_MODE in available_modes:
            baseline_mode = _REPO_SCAN_BASELINE_MODE
        elif _LEGACY_REPO_SCAN_BASELINE_MODE in available_modes:
            baseline_mode = _LEGACY_REPO_SCAN_BASELINE_MODE
        elif _VISUAL_BASELINE_MODE in available_modes:
            baseline_mode = _VISUAL_BASELINE_MODE
        else:
            baseline_mode = next(
                (
                    mode
                    for mode in ordered_modes
                    if mode != candidate_mode
                ),
                baseline_mode or _VISUAL_BASELINE_MODE,
            )
    return {
        "candidate_mode": candidate_mode,
        "baseline_mode": baseline_mode,
    }


def _scenario_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    comparison = _graph_comparison(report)
    candidate_mode = _normalize_mode(str(comparison.get("candidate_mode", "")).strip() or "odylith_on")
    baseline_mode = _normalize_mode(str(comparison.get("baseline_mode", "")).strip() or "full_scan_baseline")
    rows: list[dict[str, Any]] = []
    for scenario in _report_scenarios(report):
        results = {
            _normalize_mode(str(row.get("mode", "")).strip()): row
            for row in scenario.get("results", [])
            if isinstance(row, Mapping) and str(row.get("mode", "")).strip()
        }
        candidate = results.get(candidate_mode)
        baseline = results.get(baseline_mode)
        if not isinstance(candidate, Mapping) or not isinstance(baseline, Mapping):
            continue
        rows.append(
            {
                "scenario_id": str(scenario.get("scenario_id", "")).strip(),
                "label": str(scenario.get("label", "")).strip() or str(scenario.get("scenario_id", "")).strip(),
                "family": str(scenario.get("family", "")).strip(),
                "candidate_prompt": float(candidate.get("codex_prompt_estimated_tokens", 0.0) or 0.0),
                "baseline_prompt": float(baseline.get("codex_prompt_estimated_tokens", 0.0) or 0.0),
                "candidate_latency": float(candidate.get("latency_ms", 0.0) or 0.0),
                "baseline_latency": float(baseline.get("latency_ms", 0.0) or 0.0),
                "candidate_total": float(candidate.get("total_payload_estimated_tokens", 0.0) or 0.0),
                "baseline_total": float(baseline.get("total_payload_estimated_tokens", 0.0) or 0.0),
                "required_path_recall_delta": float(candidate.get("required_path_recall", 0.0) or 0.0)
                - float(baseline.get("required_path_recall", 0.0) or 0.0),
                "validation_success_delta": float(candidate.get("validation_success_proxy", 0.0) or 0.0)
                - float(baseline.get("validation_success_proxy", 0.0) or 0.0),
            }
        )
    return rows


def _render_frontier_svg(report: Mapping[str, Any]) -> str:
    rows = _scenario_rows(report)
    comparison = _graph_comparison(report)
    candidate_mode = str(comparison.get("candidate_mode", "")).strip() or "odylith_on"
    baseline_mode = str(comparison.get("baseline_mode", "")).strip() or "full_scan_baseline"
    candidate_compact_label = _mode_compact_label(candidate_mode)
    baseline_compact_label = _mode_compact_label(baseline_mode)
    candidate_short_label = _mode_short_label(candidate_mode)
    baseline_short_label = _mode_short_label(baseline_mode)
    candidate_prompts = [row["candidate_prompt"] for row in rows]
    baseline_prompts = [row["baseline_prompt"] for row in rows]
    candidate_latencies = [row["candidate_latency"] for row in rows]
    baseline_latencies = [row["baseline_latency"] for row in rows]
    candidate_median_prompt = statistics.median(candidate_prompts) if candidate_prompts else 0.0
    baseline_median_prompt = statistics.median(baseline_prompts) if baseline_prompts else 0.0
    candidate_median_latency = statistics.median(candidate_latencies) if candidate_latencies else 0.0
    baseline_median_latency = statistics.median(baseline_latencies) if baseline_latencies else 0.0
    report_meta_lines = _report_meta_lines(report, limit=44)
    prompt_axis = _focus_axis(
        [max(row["candidate_prompt"], row["baseline_prompt"]) for row in rows],
        tick_count=7,
    )
    latency_axis = _focus_axis(
        [max(row["candidate_latency"], row["baseline_latency"]) for row in rows],
        tick_count=6,
    )
    visible_rows: list[dict[str, Any]] = []
    outlier_rows: list[dict[str, Any]] = []
    for row in rows:
        prompt_extent = max(row["candidate_prompt"], row["baseline_prompt"])
        latency_extent = max(row["candidate_latency"], row["baseline_latency"])
        enriched = {
            **row,
            "prompt_extent": prompt_extent,
            "latency_extent": latency_extent,
        }
        if prompt_extent > prompt_axis["focus_max"] + 1e-9 or latency_extent > latency_axis["focus_max"] + 1e-9:
            outlier_rows.append(enriched)
        else:
            visible_rows.append(enriched)
    if not visible_rows and outlier_rows:
        visible_rows = outlier_rows
        outlier_rows = []
        prompt_axis["focus_max"] = _nice_axis_max(
            [max(row["candidate_prompt"], row["baseline_prompt"]) for row in visible_rows],
            tick_count=7,
        )
        latency_axis["focus_max"] = _nice_axis_max(
            [max(row["candidate_latency"], row["baseline_latency"]) for row in visible_rows],
            tick_count=6,
        )

    plot_x = 86
    plot_w = 944
    plot_h = 546
    x_max = float(prompt_axis["focus_max"] or 1.0)
    y_max = float(latency_axis["focus_max"] or 1.0)
    total_count = len(rows)
    visible_count = len(visible_rows)
    outlier_count = len(outlier_rows)
    outlier_label = "long-tail outlier" if outlier_count == 1 else "long-tail outliers"
    prompt_delta = candidate_median_prompt - baseline_median_prompt
    latency_delta = candidate_median_latency - baseline_median_latency
    token_axis_noun = _token_axis_noun(report)
    time_axis_noun = _time_axis_noun(report)
    token_axis_label = _token_axis_label(report)
    time_axis_label = _time_axis_label(report)
    prompt_delta_color = _GOOD if prompt_delta < 0 else _BAD if prompt_delta > 0 else _TEXT
    latency_delta_color = _GOOD if latency_delta < 0 else _BAD if latency_delta > 0 else _TEXT
    live_proof = _is_live_end_to_end(report)
    outlier_rows = sorted(
        outlier_rows,
        key=lambda row: max(
            row["prompt_extent"] / max(1.0, x_max),
            row["latency_extent"] / max(1.0, y_max),
        ),
        reverse=True,
    )
    subtitle_lines = _wrap_words(
        f"The main field is zoomed to the dense scenario cluster so long-tail cases do not flatten the rest. Left and down is better for {token_axis_noun} and {time_axis_noun}.",
        limit=112,
    )
    subtitle_y = 112
    subtitle_bottom = subtitle_y + max(0, (len(subtitle_lines) - 1) * 18)
    status_y = subtitle_bottom + 26
    plot_y = status_y + 34
    right_x = 1060
    right_y = plot_y
    right_w = 436
    right_inner_x = right_x + 28
    right_inner_right = right_x + right_w - 24
    summary_value_right_x = right_x + right_w - 32
    card_gap = 18
    summary_title_y_offset = 34
    summary_rule_y_offset = 54
    summary_prompt_label_y_offset = 84
    summary_prompt_value_y_offset = 122
    summary_mid_rule_y_offset = 140
    summary_latency_label_y_offset = 170
    summary_latency_value_y_offset = 208
    summary_h = 230
    read_lines = [
        *_wrap_words("Each line links the same benchmark scenario in both modes.", limit=38),
        *_wrap_words("Read left/down as better.", limit=38),
        *_wrap_words(
            (
                f"The main field caps at {_compact_number_label(x_max)} tokens and {_human_duration_label(y_max)}."
                if live_proof
                else f"The main field caps at {_fmt_int(x_max)} tokens and {_fmt_int(y_max)} ms."
            ),
            limit=38,
        ),
    ]
    read_line_height = 20
    read_h = 76 + max(1, len(read_lines)) * read_line_height
    spotlight_row_count = min(3, len(outlier_rows))
    spotlight_intro_lines = (
        _wrap_words(
            f"{outlier_count} scenario{' sits' if outlier_count == 1 else 's sit'} outside the focus window.",
            limit=38,
        )
        if outlier_rows
        else _wrap_words("No scenarios spill past the focus window.", limit=38)
    )
    spotlight_row_top = 68 + max(1, len(spotlight_intro_lines)) * 20
    spotlight_row_step = 34
    spotlight_row_h = 34
    spotlight_row_bottom = 18
    spotlight_h = (
        74 + max(1, len(spotlight_intro_lines)) * 20
        if spotlight_row_count == 0
        else spotlight_row_top
        + max(0, spotlight_row_count - 1) * spotlight_row_step
        + spotlight_row_h
        + spotlight_row_bottom
    )
    legend_items = [
        ("point", baseline_compact_label, _wrap_words(baseline_compact_label, limit=30)),
        ("diamond", candidate_compact_label, _wrap_words(candidate_compact_label, limit=30)),
        ("line_text", "One connecting line = one scenario across both modes", _wrap_words("One connecting line = one scenario across both modes", limit=32)),
        ("line_good", f"{candidate_compact_label} wins on both {time_axis_noun} and {token_axis_noun}", _wrap_words(f"{candidate_compact_label} wins on both {time_axis_noun} and {token_axis_noun}", limit=32)),
        ("line_warn", "Split tradeoff: one improves while the other worsens", _wrap_words("Split tradeoff: one improves while the other worsens", limit=32)),
        ("line_bad", f"{baseline_compact_label} wins on both {time_axis_noun} and {token_axis_noun}", _wrap_words(f"{baseline_compact_label} wins on both {time_axis_noun} and {token_axis_noun}", limit=32)),
    ]
    legend_row_heights = [max(24, len(lines) * 18 + 6) for _kind, _label, lines in legend_items]
    legend_h = 58 + sum(legend_row_heights) + 18
    read_y = right_y + summary_h + card_gap
    spotlight_y = read_y + read_h + card_gap
    legend_y = spotlight_y + spotlight_h + card_gap
    footer_line_height = 16
    footer_lines = [
        *report_meta_lines,
        f"Visual pair: {candidate_mode} vs {baseline_mode}",
        f"Source: {_report_source_label(report)}",
    ]
    footer_y = legend_y + legend_h + 42
    footer_bottom = footer_y + max(0, len(footer_lines) - 1) * footer_line_height + 12
    plot_h = max(plot_h, int(footer_bottom - plot_y - 104))
    plot_bottom = plot_y + plot_h + 78
    panel_bottom = max(plot_bottom, footer_bottom) + 36
    panel_height = panel_bottom - 40
    svg_height = max(SVG_HEIGHT, int(panel_bottom + 40))

    body: list[str] = [
        f'<rect x="44" y="40" width="1512" height="{panel_height:.0f}" rx="28" fill="{_PANEL}" stroke="{_GRID}" stroke-width="1.5"/>',
        f'<text x="86" y="86" class="title">{_frontier_heading(report)}</text>',
    ]
    _append_text_lines(body, x=86, y=subtitle_y, lines=subtitle_lines, class_name="subtitle", line_height=18)
    body.append(f'<text x="86" y="{status_y}" class="small">Static chart: Focus window | {visible_count} of {total_count} scenarios in frame</text>')
    if outlier_count > 0:
        body.append(f'<text x="420" y="{status_y}" class="small" fill="{_BAD}">| {outlier_count} {outlier_label} called out separately</text>')
    else:
        body.append(f'<text x="420" y="{status_y}" class="small" fill="{_GOOD}">| all scenarios fit in frame</text>')

    body.append(f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" rx="24" fill="#faf7ef" stroke="{_GRID}" stroke-width="1"/>')

    for index in range(0, 8):
        tick_value = x_max * index / 7
        x = _scale(tick_value, domain_min=0, domain_max=x_max, range_min=plot_x, range_max=plot_x + plot_w)
        body.append(f'<line x1="{x:.2f}" y1="{plot_y}" x2="{x:.2f}" y2="{plot_y + plot_h}" stroke="{_GRID}" stroke-width="1" opacity="0.8"/>')
        x_label = _compact_number_label(tick_value) if live_proof else _fmt_int(tick_value)
        body.append(f'<text x="{x:.2f}" y="{plot_y + plot_h + 26}" class="axis" text-anchor="middle">{_esc(x_label)}</text>')
    for index in range(0, 7):
        tick_value = y_max * index / 6
        y = _scale(tick_value, domain_min=0, domain_max=y_max, range_min=plot_y + plot_h, range_max=plot_y)
        body.append(f'<line x1="{plot_x}" y1="{y:.2f}" x2="{plot_x + plot_w}" y2="{y:.2f}" stroke="{_GRID}" stroke-width="1" opacity="0.8"/>')
        y_label = _human_duration_label(tick_value) if live_proof else _fmt_int(tick_value)
        body.append(f'<text x="{plot_x - 18}" y="{y + 4:.2f}" class="axis" text-anchor="end">{_esc(y_label)}</text>')

    body.extend(
        [
            f'<line x1="{plot_x}" y1="{plot_y + plot_h}" x2="{plot_x + plot_w}" y2="{plot_y + plot_h}" stroke="{_TEXT}" stroke-width="2"/>',
            f'<line x1="{plot_x}" y1="{plot_y}" x2="{plot_x}" y2="{plot_y + plot_h}" stroke="{_TEXT}" stroke-width="2"/>',
            f'<text x="{plot_x + plot_w / 2:.2f}" y="{plot_y + plot_h + 54}" class="label" text-anchor="middle">{_esc(token_axis_label)}</text>',
            f'<text x="{plot_x - 58}" y="{plot_y + plot_h / 2:.2f}" class="label" text-anchor="middle" transform="rotate(-90 {plot_x - 58} {plot_y + plot_h / 2:.2f})">{_esc(time_axis_label)}</text>',
            f'<text x="{plot_x}" y="{plot_y + plot_h + 78}" class="small">{_esc((f"Main field caps at {_compact_number_label(x_max)} {token_axis_noun} tokens and {_human_duration_label(y_max)} to keep the dense cluster legible.") if live_proof else (f"Main field caps at {_fmt_int(x_max)} {token_axis_noun} tokens and {_fmt_int(y_max)} ms to keep the dense cluster legible."))}</text>',
        ]
    )

    def _median_line(x_or_y: float, *, vertical: bool, color: str) -> None:
        if vertical:
            body.append(f'<line x1="{x_or_y:.2f}" y1="{plot_y}" x2="{x_or_y:.2f}" y2="{plot_y + plot_h}" stroke="{color}" stroke-width="1.8" stroke-dasharray="7 6" opacity="0.8"/>')
        else:
            body.append(f'<line x1="{plot_x}" y1="{x_or_y:.2f}" x2="{plot_x + plot_w}" y2="{x_or_y:.2f}" stroke="{color}" stroke-width="1.8" stroke-dasharray="7 6" opacity="0.8"/>')

    _median_line(
        _scale(baseline_median_prompt, domain_min=0, domain_max=x_max, range_min=plot_x, range_max=plot_x + plot_w),
        vertical=True,
        color=_FRONTIER_BASELINE,
    )
    _median_line(
        _scale(candidate_median_prompt, domain_min=0, domain_max=x_max, range_min=plot_x, range_max=plot_x + plot_w),
        vertical=True,
        color=_FRONTIER_ODYLITH,
    )
    _median_line(
        _scale(baseline_median_latency, domain_min=0, domain_max=y_max, range_min=plot_y + plot_h, range_max=plot_y),
        vertical=False,
        color=_FRONTIER_BASELINE,
    )
    _median_line(
        _scale(candidate_median_latency, domain_min=0, domain_max=y_max, range_min=plot_y + plot_h, range_max=plot_y),
        vertical=False,
        color=_FRONTIER_ODYLITH,
    )

    for row in visible_rows:
        x1 = _scale(row["baseline_prompt"], domain_min=0, domain_max=x_max, range_min=plot_x, range_max=plot_x + plot_w)
        y1 = _scale(row["baseline_latency"], domain_min=0, domain_max=y_max, range_min=plot_y + plot_h, range_max=plot_y)
        x2 = _scale(row["candidate_prompt"], domain_min=0, domain_max=x_max, range_min=plot_x, range_max=plot_x + plot_w)
        y2 = _scale(row["candidate_latency"], domain_min=0, domain_max=y_max, range_min=plot_y + plot_h, range_max=plot_y)
        improved_prompt = row["candidate_prompt"] <= row["baseline_prompt"]
        improved_latency = row["candidate_latency"] <= row["baseline_latency"]
        line_color = _GOOD if improved_prompt and improved_latency else _WARN if improved_prompt or improved_latency else _BAD
        body.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{line_color}" stroke-width="2.4" opacity="0.68"/>')
        body.append(f'<circle cx="{x1:.2f}" cy="{y1:.2f}" r="5.3" fill="{_FRONTIER_BASELINE}" stroke="{_PANEL}" stroke-width="1.4"/>')
        body.append(f'<polygon points="{_diamond_points(x2, y2, 6.2)}" fill="{_FRONTIER_ODYLITH}" stroke="{_PANEL}" stroke-width="1.4"/>')

    body.extend(
        [
            f'<rect x="{right_x}" y="{right_y}" width="{right_w}" height="{summary_h}" rx="22" fill="{_BG}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_inner_x}" y="{right_y + summary_title_y_offset}" class="value">Median tradeoff</text>',
            f'<line x1="{right_x + 24}" y1="{right_y + summary_rule_y_offset}" x2="{right_inner_right}" y2="{right_y + summary_rule_y_offset}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_inner_x}" y="{right_y + summary_prompt_label_y_offset}" class="small">{_esc(token_axis_noun.capitalize())}</text>',
            f'<text x="{right_inner_x}" y="{right_y + summary_prompt_value_y_offset}" class="value" fill="{prompt_delta_color}">{_esc(_relative_delta_percent_label(prompt_delta, baseline_median_prompt) if live_proof else _fmt_delta(prompt_delta, digits=0))}</text>',
            f'<text x="{summary_value_right_x}" y="{right_y + summary_prompt_value_y_offset}" class="small" text-anchor="end">{_esc((f"{baseline_short_label} {_compact_number_label(baseline_median_prompt)} -> {candidate_short_label} {_compact_number_label(candidate_median_prompt)}") if live_proof else (f"{baseline_short_label} {_fmt_int(baseline_median_prompt)} -> {candidate_short_label} {_fmt_int(candidate_median_prompt)}"))}</text>',
            f'<line x1="{right_x + 24}" y1="{right_y + summary_mid_rule_y_offset}" x2="{right_inner_right}" y2="{right_y + summary_mid_rule_y_offset}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_inner_x}" y="{right_y + summary_latency_label_y_offset}" class="small">{_esc(time_axis_noun.capitalize())}</text>',
            f'<text x="{right_inner_x}" y="{right_y + summary_latency_value_y_offset}" class="value" fill="{latency_delta_color}">{_esc((_relative_delta_percent_label(latency_delta, baseline_median_latency) + f" ({_signed_human_duration_label(latency_delta)})") if live_proof else (_fmt_delta(latency_delta, digits=3) + " ms"))}</text>',
            f'<text x="{summary_value_right_x}" y="{right_y + summary_latency_value_y_offset}" class="small" text-anchor="end">{_esc((f"{baseline_short_label} {_human_duration_label(baseline_median_latency)} -> {candidate_short_label} {_human_duration_label(candidate_median_latency)}") if live_proof else (f"{baseline_short_label} {_fmt_ms(baseline_median_latency)} -> {candidate_short_label} {_fmt_ms(candidate_median_latency)}"))}</text>',
            f'<rect x="{right_x}" y="{read_y}" width="{right_w}" height="{read_h}" rx="22" fill="{_BG}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_inner_x}" y="{read_y + 30}" class="value">How to read</text>',
        ]
    )
    _append_text_lines(
        body,
        x=right_inner_x,
        y=read_y + 58,
        lines=read_lines,
        class_name="label",
        line_height=read_line_height,
    )

    body.extend(
        [
            f'<rect x="{right_x}" y="{spotlight_y}" width="{right_w}" height="{spotlight_h}" rx="22" fill="{_BG}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_inner_x}" y="{spotlight_y + 30}" class="value">Long-tail spotlight</text>',
        ]
    )
    _append_text_lines(
        body,
        x=right_inner_x,
        y=spotlight_y + 54,
        lines=spotlight_intro_lines,
        class_name="label",
        line_height=20,
    )
    if outlier_rows:
        for index, row in enumerate(outlier_rows[:3]):
            y = spotlight_y + spotlight_row_top + index * spotlight_row_step
            body.extend(
                [
                    f'<rect x="{right_x + 24}" y="{y - 18}" width="{right_w - 48}" height="34" rx="10" fill="{_PANEL}" stroke="{_GRID}" stroke-width="1"/>',
                    f'<text x="{right_x + 38}" y="{y + 2}" class="label">{_esc(_short_label(row["label"], limit=26))}</text>',
                    f'<text x="{right_inner_right - 16}" y="{y + 2}" class="small" text-anchor="end">{_esc((f"peak {_human_duration_label(row['latency_extent'])} | {_compact_number_label(row['prompt_extent'])} tok") if live_proof else (f"peak {_fmt_ms(row['latency_extent'])} | {_fmt_int(row['prompt_extent'])} {token_axis_noun.split()[0]} tok"))}</text>',
                ]
            )

    body.extend(
        [
            f'<rect x="{right_x}" y="{legend_y}" width="{right_w}" height="{legend_h}" rx="22" fill="{_BG}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_inner_x}" y="{legend_y + 32}" class="value">Marks and signals</text>',
        ]
    )
    legend_cursor = legend_y + 56
    for (kind, _label, lines), row_h in zip(legend_items, legend_row_heights, strict=True):
        if kind == "point":
            body.append(f'<circle cx="{right_x + 38}" cy="{legend_cursor}" r="5.5" fill="{_FRONTIER_BASELINE}"/>')
        elif kind == "diamond":
            body.append(f'<polygon points="{_diamond_points(right_x + 38, legend_cursor, 6.2)}" fill="{_FRONTIER_ODYLITH}"/>')
        elif kind == "line_text":
            body.append(f'<line x1="{right_x + 32}" y1="{legend_cursor}" x2="{right_x + 50}" y2="{legend_cursor}" stroke="{_TEXT}" stroke-width="2.3"/>')
        elif kind == "line_good":
            body.append(f'<line x1="{right_x + 32}" y1="{legend_cursor}" x2="{right_x + 50}" y2="{legend_cursor}" stroke="{_GOOD}" stroke-width="2.5"/>')
        elif kind == "line_warn":
            body.append(f'<line x1="{right_x + 32}" y1="{legend_cursor}" x2="{right_x + 50}" y2="{legend_cursor}" stroke="{_WARN}" stroke-width="2.5"/>')
        elif kind == "line_bad":
            body.append(f'<line x1="{right_x + 32}" y1="{legend_cursor}" x2="{right_x + 50}" y2="{legend_cursor}" stroke="{_BAD}" stroke-width="2.5"/>')
        _append_text_lines(
            body,
            x=right_x + 56,
            y=legend_cursor + 5,
            lines=lines,
            class_name="small",
            line_height=18,
        )
        legend_cursor += row_h

    for index, line in enumerate(footer_lines):
        body.append(f'<text x="{right_inner_x}" y="{footer_y + index * footer_line_height}" class="small">{_esc(line)}</text>')
    return _svg_canvas(title=FRONTIER_TITLE, body=body, height=svg_height)


def _render_family_heatmap_svg(report: Mapping[str, Any]) -> str:
    family_summaries = _report_family_summaries(report)
    family_deltas = _report_family_deltas(report)
    report_comparison = _report_comparison(report)
    comparison = _graph_comparison(report)
    candidate_mode = _normalize_mode(str(comparison.get("candidate_mode", "")).strip() or "odylith_on")
    baseline_mode = _normalize_mode(str(comparison.get("baseline_mode", "")).strip() or "full_scan_baseline")
    candidate_label = _mode_label(candidate_mode)
    baseline_label = _mode_label(baseline_mode)
    uses_report_comparison = (
        candidate_mode == _normalize_mode(str(report_comparison.get("candidate_mode", "")).strip() or "odylith_on")
        and baseline_mode == _normalize_mode(str(report_comparison.get("baseline_mode", "")).strip() or "full_scan_baseline")
    )
    rows: list[dict[str, Any]] = []
    family_names = odylith_benchmark_taxonomy.ordered_family_names(
        {
            *[str(family).strip() for family in family_summaries.keys() if str(family).strip()],
            *[str(family).strip() for family in family_deltas.keys() if str(family).strip()],
        }
    )
    for family in family_names:
        modes = dict(family_summaries.get(family, {})) if isinstance(family_summaries.get(family), Mapping) else {}
        if not isinstance(modes, Mapping):
            modes = {}
        candidate_payload = _lookup_mode_mapping(modes, candidate_mode)
        baseline_payload = _lookup_mode_mapping(modes, baseline_mode)
        candidate = dict(candidate_payload) if isinstance(candidate_payload, Mapping) else {}
        baseline = dict(baseline_payload) if isinstance(baseline_payload, Mapping) else {}
        delta_row = (
            dict(family_deltas.get(family, {}))
            if uses_report_comparison and isinstance(family_deltas.get(family), Mapping)
            else {}
        )
        rows.append(
            {
                "category": odylith_benchmark_taxonomy.family_group_label(family),
                "family": family,
                "baseline_prompt": float(baseline.get("median_effective_tokens", 0.0) or 0.0),
                "baseline_latency": float(baseline.get("median_latency_ms", 0.0) or 0.0),
                "prompt_delta": float(
                    delta_row.get(
                        "median_prompt_token_delta",
                        float(candidate.get("median_effective_tokens", 0.0) or 0.0)
                        - float(baseline.get("median_effective_tokens", 0.0) or 0.0),
                    )
                    or 0.0
                ),
                "latency_delta": float(
                    delta_row.get(
                        "median_latency_delta_ms",
                        float(candidate.get("median_latency_ms", 0.0) or 0.0)
                        - float(baseline.get("median_latency_ms", 0.0) or 0.0),
                    )
                    or 0.0
                ),
                "recall_delta": float(
                    delta_row.get(
                        "required_path_recall_delta",
                        float(candidate.get("required_path_recall_rate", 0.0) or 0.0)
                        - float(baseline.get("required_path_recall_rate", 0.0) or 0.0),
                    )
                    or 0.0
                ),
                "validation_delta": float(
                    delta_row.get(
                        "validation_success_delta",
                        float(candidate.get("validation_success_rate", 0.0) or 0.0)
                        - float(baseline.get("validation_success_rate", 0.0) or 0.0),
                    )
                    or 0.0
                ),
                "expectation_delta": float(
                    delta_row.get(
                        "expectation_success_delta",
                        float(candidate.get("expectation_success_rate", 0.0) or 0.0)
                        - float(baseline.get("expectation_success_rate", 0.0) or 0.0),
                    )
                    or 0.0
                ),
                "critical_count": int(candidate.get("correctness_critical_scenario_count", 0) or 0),
            }
        )
    report_meta_lines = _report_meta_lines(report, limit=72)
    time_axis_noun = _time_axis_noun(report)
    token_axis_noun = _token_axis_noun(report)
    live_proof = _is_live_end_to_end(report)

    title_y = 88
    subtitle_y = 114
    subtitle_lines = _wrap_words(
        (
            f"These are published median family deltas from the {_public_benchmark_name(report)} for {candidate_label} versus {baseline_label}. Families are ordered by Odylith's developer-first benchmark archetypes rather than token cost. Green means Odylith wins that family. {token_axis_noun.capitalize()} deltas are shown as compact token deltas and {time_axis_noun} deltas are shown as humanized durations; lower values are better for both. Recall and validation favor higher values."
            if live_proof
            else f"These are published median family deltas from the {_public_benchmark_name(report)} for {candidate_label} versus {baseline_label}. Families are ordered by Odylith's developer-first benchmark archetypes rather than token cost. Green means Odylith wins that family. {token_axis_noun.capitalize()} deltas are tokens and {time_axis_noun} deltas are milliseconds; lower values are better for both. Recall and validation favor higher values."
        ),
        limit=126,
    )
    subtitle_bottom = subtitle_y + max(0, (len(subtitle_lines) - 1) * 18)
    table_x = 86
    table_y = int(subtitle_bottom + 40)
    row_h = 44
    category_w = 208
    name_w = 328
    columns = [
        ("recall_delta", "Recall", True, 150),
        ("validation_delta", "Validation", True, 150),
        ("expectation_delta", "Fit", True, 130),
        ("prompt_delta", token_axis_noun.capitalize(), False, max(180, min(260, len(token_axis_noun.capitalize()) * 8))),
        (
            "latency_delta",
            time_axis_noun.capitalize() if live_proof else f"{time_axis_noun.capitalize()} (ms)",
            False,
            max(180, min(300, len(f'{time_axis_noun.capitalize()} (ms)') * 8)),
        ),
    ]
    header_specs: list[dict[str, Any]] = []
    max_header_lines = 1
    for key, label, positive_good, width in columns:
        wrap_limit = max(18, int((width - 24) / 6.4))
        header_lines = _wrap_words(label, limit=wrap_limit) or [label]
        max_header_lines = max(max_header_lines, len(header_lines))
        header_specs.append(
            {
                "key": key,
                "label": label,
                "positive_good": positive_good,
                "width": width,
                "header_lines": header_lines,
            }
        )
    header_line_height = 16
    header_h = max(row_h, 22 + max_header_lines * header_line_height + 10)
    table_w = max(1460, category_w + name_w + sum(int(spec["width"]) for spec in header_specs))
    table_h = header_h + row_h * len(rows)
    footer_line_height = 16
    footer_y = table_y + table_h + 34
    footer_bottom = footer_y + max(1, len(report_meta_lines)) * footer_line_height + 28
    svg_height = max(SVG_HEIGHT, int(footer_bottom + 40))
    panel_height = svg_height - 80

    body: list[str] = [
        f'<rect x="44" y="40" width="1512" height="{panel_height}" rx="28" fill="{_PANEL}" stroke="{_GRID}" stroke-width="1.5"/>',
        f'<text x="86" y="{title_y}" class="title">{_heatmap_heading(report)}</text>',
    ]
    _append_text_lines(body, x=86, y=subtitle_y, lines=subtitle_lines, class_name="subtitle", line_height=18)

    max_abs = {
        str(spec["key"]): max(abs(float(row[str(spec["key"])])) for row in rows) if rows else 1.0
        for spec in header_specs
    }
    body.append(f'<rect x="{table_x}" y="{table_y}" width="{table_w}" height="{table_h}" rx="18" fill="{_BG}" stroke="{_GRID}" stroke-width="1"/>')
    body.append(f'<text x="{table_x + 18}" y="{table_y + header_h / 2 + 5:.2f}" class="label" font-weight="700">Archetype</text>')
    body.append(f'<text x="{table_x + category_w + 18}" y="{table_y + header_h / 2 + 5:.2f}" class="label" font-weight="700">Family</text>')
    x = table_x + category_w + name_w
    for spec in header_specs:
        header_lines = list(spec["header_lines"])
        header_top = table_y + 24 + ((max_header_lines - len(header_lines)) * header_line_height / 2)
        _append_text_lines(
            body,
            x=x + float(spec["width"]) / 2,
            y=header_top,
            lines=header_lines,
            class_name="label",
            line_height=header_line_height,
            text_anchor="middle",
            font_weight="700",
        )
        x += int(spec["width"])

    previous_category = ""
    for index, row in enumerate(rows):
        y = table_y + header_h + index * row_h
        stripe_fill = _PANEL if index % 2 else "#faf5ec"
        body.append(f'<rect x="{table_x}" y="{y}" width="{table_w}" height="{row_h}" fill="{stripe_fill}"/>')
        current_category = str(row["category"])
        if previous_category and current_category != previous_category:
            body.append(
                f'<line x1="{table_x}" y1="{y}" x2="{table_x + table_w}" y2="{y}" stroke="{_GRID}" stroke-width="2"/>'
            )
        body.append(f'<text x="{table_x + 18}" y="{y + 28}" class="small">{_esc(current_category)}</text>')
        body.append(f'<text x="{table_x + category_w + 18}" y="{y + 28}" class="label">{_esc(_short_family(row["family"]))}</text>')
        if row["critical_count"] > 0:
            critical_x = table_x + category_w + 236
            body.append(f'<rect x="{critical_x}" y="{y + 10}" width="62" height="22" rx="11" fill="{_BAD}" opacity="0.14"/>')
            body.append(f'<text x="{critical_x + 31}" y="{y + 25}" class="chip" text-anchor="middle" fill="{_BAD}">critical</text>')
        x = table_x + category_w + name_w
        for spec in header_specs:
            key = str(spec["key"])
            value = float(row[key] or 0.0)
            width = int(spec["width"])
            fill = _heat_color(value, max_abs=max_abs[key], positive_good=bool(spec["positive_good"]))
            body.append(f'<rect x="{x + 8}" y="{y + 6}" width="{width - 16}" height="{row_h - 12}" rx="10" fill="{fill}" stroke="{_GRID}" stroke-width="0.5"/>')
            label = _fmt_delta(value, digits=0) if "prompt" in key else _fmt_delta(value, digits=3 if key != "latency_delta" else 3)
            if live_proof and key == "prompt_delta":
                label = f"{value:+,.0f}"
            elif live_proof and key == "latency_delta":
                label = _signed_human_duration_label(value)
            elif key == "prompt_delta":
                label = f"{int(round(value)):+d}"
            elif key == "latency_delta":
                label = f"{value:+.3f}"
            else:
                label = f"{value:+.3f}"
            body.append(f'<text x="{x + width / 2:.2f}" y="{y + row_h / 2:.2f}" class="cell">{_esc(label)}</text>')
            x += width
        previous_category = current_category

    body.extend(
        [
            f'<text x="{table_x + table_w - 18}" y="{footer_y}" class="small" text-anchor="end">Green: Odylith better | Red: baseline better | Ordered by developer archetype</text>',
        ]
    )
    for index, line in enumerate(report_meta_lines):
        body.append(f'<text x="{table_x}" y="{footer_y + index * footer_line_height}" class="small">{_esc(line)}</text>')
    return _svg_canvas(title=HEATMAP_TITLE, body=body, height=svg_height)


def _render_operating_posture_svg(report: Mapping[str, Any]) -> str:
    adoption = dict(report.get("adoption_proof", {})) if isinstance(report.get("adoption_proof"), Mapping) else {}
    runtime = dict(report.get("runtime_posture", {})) if isinstance(report.get("runtime_posture"), Mapping) else {}
    summary = dict(report.get("published_summary", {})) if isinstance(report.get("published_summary"), Mapping) else {}
    adoption_sample_size = int(
        adoption.get("sample_size", summary.get("adoption_proof_sample_size", 0)) or 0
    )
    has_adoption_sample = adoption_sample_size > 0 or bool(adoption)

    def _rate(*, adoption_key: str = "", summary_key: str = "", runtime_key: str = "") -> float:
        if adoption_key and adoption_key in adoption:
            return float(adoption.get(adoption_key, 0.0) or 0.0)
        if runtime_key and runtime_key in runtime:
            return float(runtime.get(runtime_key, 0.0) or 0.0)
        if summary_key:
            return float(summary.get(summary_key, 0.0) or 0.0)
        return 0.0

    def _state(*, runtime_key: str = "", summary_key: str = "") -> str:
        if runtime_key:
            token = str(runtime.get(runtime_key, "")).strip()
            if token:
                return token
        if summary_key:
            token = str(summary.get(summary_key, "")).strip()
            if token:
                return token
        return "unknown"

    operation_distribution = (
        dict(adoption.get("operation_distribution", {}))
        if has_adoption_sample and isinstance(adoption.get("operation_distribution"), Mapping)
        else {}
    )
    funnel = [
        ("Packet present", _rate(adoption_key="packet_present_rate", summary_key="odylith_packet_present_rate")),
        ("Auto grounding applied", _rate(adoption_key="auto_grounded_rate", summary_key="odylith_auto_grounded_rate")),
        ("Route ready", _rate(adoption_key="route_ready_rate", runtime_key="route_ready_rate", summary_key="runtime_route_ready_rate")),
        ("Native spawn ready", _rate(adoption_key="native_spawn_ready_rate", runtime_key="native_spawn_ready_rate", summary_key="runtime_native_spawn_ready_rate")),
        ("Grounded delegate", _rate(adoption_key="grounded_delegate_rate", summary_key="odylith_grounded_delegate_rate")),
    ]
    title_y = 88
    subtitle_y = 114
    subtitle_lines = _wrap_words(
        "This is the system behavior behind the current proof-host scorecard: packet coverage, grounding, delegation readiness, and runtime posture.",
        limit=118,
    )
    subtitle_bottom = subtitle_y + max(0, (len(subtitle_lines) - 1) * 18)
    start_x = 98
    top_y = int(subtitle_bottom + 66)
    bar_w = 160
    gap = 24
    chart_h = 300
    right_x = 1056
    operation_card_y = top_y - 28
    operation_row_top = 78
    operation_row_step = 74
    operation_row_bottom = 58
    operation_track_y_offset = 18
    operation_track_h = 18
    operation_track_w = 300
    operation_count_x = right_x + 412
    operation_count_y_offset = 31
    operation_card_h = max(
        264,
        operation_row_top + max(0, len(operation_distribution) - 1) * operation_row_step + operation_row_bottom,
    )
    chip_x = 98
    chip_y = top_y + chart_h + 80
    chip_w = 430
    chip_h = 92
    footer_y = chip_y + 2 * chip_h + 24 + 28
    panel_bottom = max(operation_card_y + operation_card_h, footer_y + 22) + 20
    panel_height = panel_bottom - 40
    svg_height = max(SVG_HEIGHT, int(panel_bottom + 40))
    body: list[str] = [
        f'<rect x="44" y="40" width="1512" height="{panel_height:.0f}" rx="28" fill="{_PANEL}" stroke="{_GRID}" stroke-width="1.5"/>',
        f'<text x="86" y="{title_y}" class="title">{_posture_heading(report)}</text>',
    ]
    _append_text_lines(body, x=86, y=subtitle_y, lines=subtitle_lines, class_name="subtitle", line_height=18)
    optional_funnel_labels = {"Auto grounding applied", "Grounded delegate"}
    for index, (label, rate) in enumerate(funnel):
        x = start_x + index * (bar_w + gap)
        fill = _lerp_color(_NEUTRAL, _ODYLITH, 0.25 + 0.75 * rate)
        h = chart_h * rate
        y = top_y + (chart_h - h)
        value_y = y - 10
        value_label = _fmt_pct(rate)
        body.append(f'<rect x="{x}" y="{top_y}" width="{bar_w}" height="{chart_h}" rx="18" fill="{_BG}" stroke="{_GRID}" stroke-width="1"/>')
        if rate > 0.0:
            body.append(f'<rect x="{x}" y="{y:.2f}" width="{bar_w}" height="{h:.2f}" rx="18" fill="{fill}"/>')
        elif label in optional_funnel_labels:
            placeholder_h = 64
            placeholder_y = top_y + chart_h - placeholder_h
            value_y = placeholder_y - 10
            value_label = "On demand"
            body.append(
                f'<rect x="{x}" y="{placeholder_y:.2f}" width="{bar_w}" height="{placeholder_h:.2f}" rx="18" fill="{_NEUTRAL}" opacity="0.9"/>'
            )
            body.append(
                f'<text x="{x + bar_w / 2:.2f}" y="{placeholder_y + 36:.2f}" class="small" text-anchor="middle">Not triggered</text>'
            )
        body.append(f'<text x="{x + bar_w / 2:.2f}" y="{top_y + chart_h + 34}" class="label" text-anchor="middle">{_esc(label)}</text>')
        body.append(f'<text x="{x + bar_w / 2:.2f}" y="{value_y:.2f}" class="value" text-anchor="middle">{_esc(value_label)}</text>')

    body.extend(
        [
            f'<rect x="{right_x}" y="{operation_card_y}" width="440" height="{operation_card_h}" rx="22" fill="{_BG}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_x + 28}" y="{operation_card_y + 38}" class="value">Operation mix</text>',
            f'<line x1="{right_x + 24}" y1="{operation_card_y + 56}" x2="{right_x + 416}" y2="{operation_card_y + 56}" stroke="{_GRID}" stroke-width="1"/>',
        ]
    )
    if operation_distribution:
        total_operations = max(1, sum(int(value or 0) for value in operation_distribution.values()))
        for index, (name, count) in enumerate(sorted(operation_distribution.items(), key=lambda item: (-int(item[1]), item[0]))):
            y = operation_card_y + operation_row_top + index * operation_row_step
            width = 320 * (int(count or 0) / total_operations)
            fill = _ODYLITH if name == "impact" else _ODYLITH_DARK if name == "governance_slice" else "#375a7f"
            body.append(f'<text x="{right_x + 28}" y="{y}" class="label">{_esc(_short_family(name))}</text>')
            body.append(
                f'<rect x="{right_x + 28}" y="{y + operation_track_y_offset}" width="{operation_track_w}" height="{operation_track_h}" rx="9" fill="{_PANEL}" stroke="{_GRID}" stroke-width="1"/>'
            )
            body.append(
                f'<rect x="{right_x + 28}" y="{y + operation_track_y_offset}" width="{width * (operation_track_w / 320):.2f}" height="{operation_track_h}" rx="9" fill="{fill}"/>'
            )
            body.append(
                f'<text x="{operation_count_x}" y="{y + operation_count_y_offset}" class="label" text-anchor="end">{int(count or 0)} scenarios</text>'
            )
    else:
        body.append(f'<text x="{right_x + 28}" y="{operation_card_y + 118}" class="value">Not sampled</text>')
        _append_text_lines(
            body,
            x=right_x + 28,
            y=operation_card_y + 152,
            lines=_wrap_words(
                "Operation mix is only published when adoption-proof sampling runs. This report did not include that sample.",
                limit=38,
            ),
            class_name="small",
            line_height=18,
        )

    chips = [
        ("Requires widening", _fmt_pct(_rate(adoption_key="requires_widening_rate", summary_key="odylith_requires_widening_rate")), _WARN),
        ("Workspace daemon reused", _fmt_pct(_rate(adoption_key="workspace_daemon_reused_rate", summary_key="odylith_workspace_daemon_reuse_rate")), _ODYLITH),
        ("Session namespaced", _fmt_pct(_rate(adoption_key="session_namespaced_rate", summary_key="odylith_session_namespaced_rate")), _ODYLITH),
        ("Governance runtime-first", _fmt_pct(_rate(runtime_key="governance_runtime_first_usage_rate", summary_key="runtime_governance_runtime_first_usage_rate")), _ODYLITH),
        ("Repo-scan degraded fallback", _fmt_pct(_rate(runtime_key="repo_scan_degraded_fallback_rate", summary_key="runtime_repo_scan_degraded_fallback_rate")), _GOOD),
        ("Memory standardization", _state(runtime_key="memory_standardization_state", summary_key="runtime_memory_standardization_state"), "#6b46c1"),
    ]
    for index, (label, value, color) in enumerate(chips):
        x = chip_x + (index % 3) * (chip_w + 26)
        y = chip_y + (index // 3) * (chip_h + 24)
        body.extend(
            [
                f'<rect x="{x}" y="{y}" width="{chip_w}" height="{chip_h}" rx="18" fill="{_BG}" stroke="{_GRID}" stroke-width="1"/>',
                f'<rect x="{x + 18}" y="{y + 18}" width="10" height="56" rx="5" fill="{color}"/>',
                f'<text x="{x + 46}" y="{y + 40}" class="label">{_esc(label)}</text>',
                f'<text x="{x + 46}" y="{y + 68}" class="value">{_esc(value)}</text>',
            ]
        )

    body.extend(
        [
            f'<text x="98" y="{footer_y}" class="small">{_esc(_report_meta(report))}</text>',
            f'<text x="98" y="{footer_y + 22}" class="small">{_esc("Rates come from adoption_proof when sampled; otherwise they fall back to published_summary and runtime_posture for the active benchmark profile.")}</text>',
        ]
    )
    return _svg_canvas(title=POSTURE_TITLE, body=body, height=svg_height)


def render_graph_assets(report: Mapping[str, Any], *, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        **marketing_graphs.render_marketing_graph_assets(report),
        FRONTIER_FILENAME: _render_frontier_svg(report),
        HEATMAP_FILENAME: _render_family_heatmap_svg(report),
        POSTURE_FILENAME: _render_operating_posture_svg(report),
    }
    written: list[Path] = []
    for name, contents in outputs.items():
        target = (out_dir / name).resolve()
        target.write_text(contents, encoding="utf-8")
        written.append(target)
    return written


def render_profile_graph_assets(
    *,
    repo_root: Path,
    out_dir: Path,
    benchmark_profiles: Sequence[str],
) -> dict[str, list[Path]]:
    written: dict[str, list[Path]] = {}
    root = Path(repo_root).resolve()
    base_out_dir = Path(out_dir).resolve()
    for raw_profile in benchmark_profiles:
        profile = odylith_benchmark_runner._normalize_benchmark_profile(str(raw_profile).strip())  # noqa: SLF001
        report = odylith_benchmark_runner.load_latest_benchmark_report(
            repo_root=root,
            benchmark_profile=profile,
        )
        if not report:
            continue
        report_path = odylith_benchmark_runner.latest_report_path(
            repo_root=root,
            benchmark_profile=profile,
        )
        if not report_path.is_file() and profile == odylith_benchmark_runner.BENCHMARK_PROFILE_PROOF:
            report_path = odylith_benchmark_runner.latest_report_path(repo_root=root)
        report = dict(report)
        report.setdefault("_report_path", str(report_path.resolve()))
        written[profile] = render_graph_assets(report, out_dir=base_out_dir / profile)
    return written


def load_report(path: Path) -> dict[str, Any]:
    resolved = Path(path).resolve()
    report = json.loads(resolved.read_text(encoding="utf-8"))
    if isinstance(report, dict):
        report.setdefault("_report_path", str(resolved))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Odylith benchmark SVG graphs from a benchmark report.")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(".odylith/runtime/odylith-benchmarks/latest.v1.json"),
        help="Path to the benchmark report JSON.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("docs/benchmarks"),
        help="Directory to write SVG assets into.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repo root used with --profiles to resolve profile-specific latest benchmark reports.",
    )
    parser.add_argument(
        "--profiles",
        nargs="*",
        default=(),
        help="Render the latest report for each listed benchmark profile into out-dir/<profile>/.",
    )
    args = parser.parse_args(argv)
    if args.profiles:
        written_sets = render_profile_graph_assets(
            repo_root=args.repo_root,
            out_dir=args.out_dir,
            benchmark_profiles=args.profiles,
        )
        for paths in written_sets.values():
            for path in paths:
                print(path)
        return 0
    report = load_report(args.report)
    written = render_graph_assets(report, out_dir=args.out_dir)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
