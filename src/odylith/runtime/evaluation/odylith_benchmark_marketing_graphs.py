"""Marketing-first benchmark SVGs derived from the same Odylith report."""

from __future__ import annotations

import contextlib
import html
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

from odylith.runtime.evaluation import odylith_benchmark_runner


SVG_WIDTH = 1600
SVG_HEIGHT = 900
_BG = "#f6f1e7"
_TEXT = "#17202a"
_MUTED = "#5f6b76"
_GOOD = "#1d7f63"
_BAD = "#b42318"
_WARN = "#b7791f"
_WARN_SOFT = "#f4ead2"
_GRID = "#d8cfbd"
_BASELINE = "#b64035"
_ODYLITH = "#007f8c"
_PANEL = "#fffdfa"

QUALITY_FRONTIER_FILENAME = "odylith-benchmark-quality-frontier.svg"
QUALITY_FRONTIER_TITLE = "Odylith benchmark quality frontier"
QUALITY_FRONTIER_HEADING = "Live Benchmark Quality Frontier: grounding recall vs time to valid outcome"


def _comparison_contract(report: Mapping[str, Any]) -> str:
    return str(report.get("comparison_contract", "")).strip() or odylith_benchmark_runner.LIVE_COMPARISON_CONTRACT


def _is_live_end_to_end(report: Mapping[str, Any]) -> bool:
    return odylith_benchmark_runner._is_live_comparison_contract(_comparison_contract(report))  # noqa: SLF001


def _time_axis_noun(report: Mapping[str, Any]) -> str:
    return "time to valid outcome" if _is_live_end_to_end(report) else "packet time"


def _public_benchmark_name(report: Mapping[str, Any]) -> str:
    return "Live Benchmark" if _is_live_end_to_end(report) else "Internal Diagnostic Benchmark"


def _quality_frontier_heading(report: Mapping[str, Any]) -> str:
    if _is_live_end_to_end(report):
        return QUALITY_FRONTIER_HEADING
    return "Internal Diagnostic Quality Frontier: grounding recall vs packet time"


def _report_source_label(report: Mapping[str, Any]) -> str:
    token = str(report.get("_report_path", "")).strip()
    if not token:
        return ".odylith/runtime/odylith-benchmarks/latest.v1.json"
    repo_root = str(report.get("repo_root", "")).strip()
    if repo_root:
        with contextlib.suppress(ValueError):
            relative = Path(token).resolve().relative_to(Path(repo_root).resolve()).as_posix()
            if relative.startswith(".odylith/runtime/odylith-benchmarks/"):
                return Path(relative).name
            return relative
    normalized = token.replace("\\", "/")
    parts = [part for part in Path(normalized).parts if part not in {"/", ""}]
    for anchor in (".odylith", "docs"):
        if anchor in parts:
            anchored = "/".join(parts[parts.index(anchor) :])
            if anchored.startswith(".odylith/runtime/odylith-benchmarks/"):
                return Path(anchored).name
            return anchored
    if len(normalized) <= 64:
        return normalized
    if len(parts) >= 4:
        return f".../{'/'.join(parts[-4:])}"
    return Path(normalized).name


def _prompt_only_control_baseline(*, report: Mapping[str, Any], baseline_mode: str, pairs: Sequence[Mapping[str, Any]]) -> bool:
    if _is_live_end_to_end(report):
        return False
    if str(baseline_mode or "").strip() not in {"raw_agent_baseline", "odylith_off"}:
        return False
    return bool(pairs) and all(abs(float(row.get("baseline_recall", 0.0) or 0.0)) < 1e-9 for row in pairs)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _fmt_delta(value: float, *, digits: int = 3) -> str:
    return f"{float(value or 0.0):+.{digits}f}"


def _human_duration_label(milliseconds: float) -> str:
    if abs(float(milliseconds or 0.0)) < 1e-9:
        return "0s"
    return odylith_benchmark_runner._human_duration_label(milliseconds)  # noqa: SLF001


def _signed_human_duration_label(milliseconds: float) -> str:
    number = float(milliseconds or 0.0)
    if abs(number) < 1e-9:
        return "0s"
    sign = "+" if number >= 0.0 else "-"
    return f"{sign}{_human_duration_label(abs(number))}"


def _relative_delta_percent_label(delta: float, baseline: float) -> str:
    baseline_value = float(baseline or 0.0)
    if abs(baseline_value) < 1e-9:
        return "0%" if abs(float(delta or 0.0)) < 1e-9 else f"{float(delta or 0.0):+.0f}"
    pct = (float(delta or 0.0) / baseline_value) * 100.0
    if abs(pct) >= 10.0:
        return f"{pct:+.0f}%"
    return f"{pct:+.1f}%"


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
) -> None:
    extras: list[str] = []
    if text_anchor:
        extras.append(f'text-anchor="{text_anchor}"')
    if fill:
        extras.append(f'fill="{fill}"')
    extra = ""
    if extras:
        extra = " " + " ".join(extras)
    for index, line in enumerate(lines):
        body.append(f'<text x="{x}" y="{y + index * line_height}" class="{class_name}"{extra}>{_esc(line)}</text>')


def _svg_canvas(*, title: str, body: Sequence[str], height: int = SVG_HEIGHT) -> str:
    style = """
    <style>
      text { fill: %s; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
      .title { font-size: 30px; font-weight: 700; }
      .subtitle { font-size: 15px; fill: %s; }
      .label { font-size: 14px; fill: %s; }
      .small { font-size: 12px; fill: %s; }
      .value { font-size: 20px; font-weight: 700; }
      .metric { font-size: 24px; font-weight: 700; }
      .chip { font-size: 12px; font-weight: 700; }
    </style>
    """ % (_TEXT, _MUTED, _MUTED, _MUTED)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{height}" viewBox="0 0 {SVG_WIDTH} {height}" role="img" aria-label="{_esc(title)}">'
        f"<title>{_esc(title)}</title>"
        f'<rect x="0" y="0" width="{SVG_WIDTH}" height="{height}" rx="24" fill="{_BG}"/>'
        f"{style}"
        + "".join(body)
        + "</svg>"
    )


def _comparison(report: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(report.get("published_comparison"), Mapping):
        return dict(report.get("published_comparison", {}))
    if isinstance(report.get("primary_comparison"), Mapping):
        return dict(report.get("primary_comparison", {}))
    return {}


def _report_family_summaries(report: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(report.get("published_family_summaries"), Mapping):
        return dict(report.get("published_family_summaries", {}))
    if isinstance(report.get("family_summaries"), Mapping):
        return dict(report.get("family_summaries", {}))
    return {}


def _report_scenarios(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = report.get("published_scenarios")
    if isinstance(rows, list):
        return [dict(row) for row in rows if isinstance(row, Mapping)]
    rows = report.get("scenarios")
    if isinstance(rows, list):
        return [dict(row) for row in rows if isinstance(row, Mapping)]
    return []


def _quality_comparison(report: Mapping[str, Any]) -> tuple[str, str]:
    comparison = _comparison(report)
    candidate_mode = str(comparison.get("candidate_mode", "odylith_on") or "odylith_on")
    baseline_mode = str(comparison.get("baseline_mode", "odylith_off") or "odylith_off")
    seen_modes: set[str] = set()
    family_summaries = _report_family_summaries(report)
    for summary in family_summaries.values():
        if isinstance(summary, Mapping):
            for token in summary.keys():
                mode = str(token or "").strip()
                if mode:
                    seen_modes.add(mode)
    if "odylith_on" in seen_modes:
        candidate_mode = "odylith_on"
    if "odylith_off" in seen_modes:
        baseline_mode = "odylith_off"
    elif "raw_agent_baseline" in seen_modes:
        baseline_mode = "raw_agent_baseline"
    return candidate_mode, baseline_mode


def _mode_short_label(mode: str) -> str:
    token = str(mode or "").strip()
    if token == "odylith_on":
        return "on"
    if token in {"raw_agent_baseline", "odylith_off"}:
        return "off"
    if token in {"odylith_repo_scan_baseline", "full_scan_baseline"}:
        return "repo-scan"
    return token.replace("_", " ") or "mode"


def _mode_compact_label(mode: str) -> str:
    token = str(mode or "").strip()
    if token == "odylith_on":
        return "Odylith on"
    if token in {"raw_agent_baseline", "odylith_off"}:
        return "Odylith off / raw host CLI"
    if token in {"odylith_repo_scan_baseline", "full_scan_baseline"}:
        return "Repo-scan baseline"
    return token.replace("_", " ").strip() or "Benchmark mode"


def _report_meta(report: Mapping[str, Any]) -> str:
    benchmark_profile = str(report.get("benchmark_profile", "")).strip()
    profiles = report.get("published_cache_profiles", [])
    profile_suffix = ""
    if benchmark_profile:
        profile_suffix = f" | {_public_benchmark_name(report)}"
    if isinstance(profiles, list):
        normalized = [str(token).strip() for token in profiles if str(token).strip()]
        if normalized:
            profile_suffix += f" | {', '.join(normalized)}"
    return (
        f"Report {report.get('report_id', '')} | "
        f"{report.get('generated_utc', '')} | "
        f"{report.get('scenario_count', 0)} scenarios"
        f"{profile_suffix}"
    )


def _clamp_unit(value: Any) -> float:
    try:
        numeric = float(value or 0.0)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(1.0, numeric))


def _plot_x(value: float, *, plot_x: float, plot_w: float) -> float:
    return plot_x + _clamp_unit(value) * plot_w


def _plot_y(value: float, *, plot_y: float, plot_h: float) -> float:
    return plot_y + plot_h - _clamp_unit(value) * plot_h


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


def _short_family(value: str) -> str:
    token = str(value or "").strip().replace("_", " ").replace("-", " ")
    return " ".join(part.capitalize() for part in token.split())


def _short_label(value: str, *, limit: int = 34) -> str:
    token = " ".join(str(value or "").strip().replace("-", " ").split())
    if len(token) <= limit:
        return token
    return token[: max(0, limit - 1)].rstrip() + "..."


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


def _nice_axis_max(values: Sequence[float], *, tick_count: int = 6) -> float:
    rows = [float(value or 0.0) for value in values]
    if not rows:
        return 1.0
    step = _nice_tick_step(max(rows), tick_count=tick_count)
    return step * math.ceil(max(rows) / step)


def _quality_pairs(report: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str, str]:
    candidate_mode, baseline_mode = _quality_comparison(report)
    pairs: list[dict[str, Any]] = []
    for scenario in _report_scenarios(report):
        results = {
            str(row.get("mode", "")).strip(): row
            for row in scenario.get("results", [])
            if isinstance(row, Mapping) and str(row.get("mode", "")).strip()
        }
        candidate = results.get(candidate_mode)
        baseline = results.get(baseline_mode)
        if not isinstance(candidate, Mapping) or not isinstance(baseline, Mapping):
            continue
        if not candidate or not baseline:
            continue
        pairs.append(
            {
                "label": str(scenario.get("label", "")).strip() or str(scenario.get("scenario_id", "")).strip(),
                "family": _short_family(str(scenario.get("family", "")).strip()),
                "baseline_recall": _clamp_unit(baseline.get("required_path_recall")),
                "baseline_latency": float(baseline.get("latency_ms", 0.0) or 0.0),
                "candidate_recall": _clamp_unit(candidate.get("required_path_recall")),
                "candidate_latency": float(candidate.get("latency_ms", 0.0) or 0.0),
            }
        )
    return pairs, candidate_mode, baseline_mode


def render_quality_frontier_svg(report: Mapping[str, Any]) -> str:
    pairs, candidate_mode, baseline_mode = _quality_pairs(report)
    prompt_only_control = _prompt_only_control_baseline(report=report, baseline_mode=baseline_mode, pairs=pairs)
    candidate_compact_label = _mode_compact_label(candidate_mode)
    baseline_compact_label = "Prompt-only raw host control" if prompt_only_control else _mode_compact_label(baseline_mode)
    candidate_short_label = _mode_short_label(candidate_mode)
    baseline_short_label = "control" if prompt_only_control else _mode_short_label(baseline_mode)
    baseline_recalls = [float(row.get("baseline_recall", 0.0) or 0.0) for row in pairs]
    candidate_recalls = [float(row.get("candidate_recall", 0.0) or 0.0) for row in pairs]
    baseline_latencies = [float(row.get("baseline_latency", 0.0) or 0.0) for row in pairs]
    candidate_latencies = [float(row.get("candidate_latency", 0.0) or 0.0) for row in pairs]

    baseline_median_recall = statistics.median(baseline_recalls) if baseline_recalls else 0.0
    candidate_median_recall = statistics.median(candidate_recalls) if candidate_recalls else 0.0
    baseline_median_latency = statistics.median(baseline_latencies) if baseline_latencies else 0.0
    candidate_median_latency = statistics.median(candidate_latencies) if candidate_latencies else 0.0

    enriched_pairs: list[dict[str, Any]] = []
    for row in pairs:
        delta_recall = float(row.get("candidate_recall", 0.0) or 0.0) - float(row.get("baseline_recall", 0.0) or 0.0)
        delta_latency = float(row.get("candidate_latency", 0.0) or 0.0) - float(row.get("baseline_latency", 0.0) or 0.0)
        enriched_pairs.append(
            {
                **row,
                "delta_recall": delta_recall,
                "delta_latency": delta_latency,
                "movement_score": abs(delta_recall) + abs(delta_latency),
                "joint_gain": delta_recall - delta_latency,
            }
        )

    both_improve = 0
    split_tradeoff = 0
    unchanged = 0
    baseline_better = 0
    for row in enriched_pairs:
        delta_recall = float(row["delta_recall"])
        delta_latency = float(row["delta_latency"])
        if abs(delta_recall) < 1e-9 and abs(delta_latency) < 1e-9:
            unchanged += 1
        elif delta_recall >= 0.0 and delta_latency <= 0.0 and (delta_recall > 0.0 or delta_latency < 0.0):
            both_improve += 1
        elif delta_recall <= 0.0 and delta_latency >= 0.0 and (delta_recall < 0.0 or delta_latency > 0.0):
            baseline_better += 1
        else:
            split_tradeoff += 1
    plot_x = 86
    plot_w = 944
    plot_h = 546
    x_max = 1.0
    y_max = _nice_axis_max([*baseline_latencies, *candidate_latencies, 1.0], tick_count=6)
    total_count = len(enriched_pairs)
    recall_delta = candidate_median_recall - baseline_median_recall
    latency_delta = candidate_median_latency - baseline_median_latency
    time_axis_noun = _time_axis_noun(report)
    recall_delta_color = _GOOD if recall_delta > 0 else _BAD if recall_delta < 0 else _TEXT
    latency_delta_color = _GOOD if latency_delta < 0 else _BAD if latency_delta > 0 else _TEXT
    live_proof = _is_live_end_to_end(report)

    subtitle_lines = _wrap_words(
        (
            "Each line connects the same benchmark scenario with a prompt-only raw host control (red) "
            f"and Odylith on (teal). Right is better and lower {time_axis_noun} is better."
            if prompt_only_control
            else f"Each line connects the same benchmark scenario with Odylith off (red) and Odylith on (teal). Right is better and lower {time_axis_noun} is better."
        ),
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
        *_wrap_words("Read right/down as better.", limit=38),
    ]
    if prompt_only_control:
        read_lines.extend(
            _wrap_words(
                "In this diagnostic lane, the red control is prompt-only, so recall stays on the 0.00 rail by contract.",
                limit=38,
            )
        )
    read_lines.extend(
        _wrap_words(
            (
                f"The main field spans recall 0.00 to 1.00 and {time_axis_noun} 0 to {_human_duration_label(y_max)}."
                if live_proof
                else f"The main field spans recall 0.00 to 1.00 and {time_axis_noun} 0 to {int(round(y_max))} ms."
            ),
            limit=38,
        )
    )
    read_line_height = 20
    read_h = 76 + max(1, len(read_lines)) * read_line_height

    spotlight_pairs = sorted(
        [row for row in enriched_pairs if row["joint_gain"] > 0],
        key=lambda row: (row["joint_gain"], row["movement_score"], row["label"]),
        reverse=True,
    )[:3]
    if not spotlight_pairs:
        spotlight_pairs = sorted(
            enriched_pairs,
            key=lambda row: (row["movement_score"], row["joint_gain"], row["label"]),
            reverse=True,
        )[:3]
    spotlight_row_count = len(spotlight_pairs)
    spotlight_intro_lines = (
        _wrap_words("Largest scenario recall gains per added paired-time cost.", limit=38)
        if spotlight_pairs
        else _wrap_words("No published scenario pairs are available in this report.", limit=38)
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
        (
            "line_text",
            "One connecting line = one scenario across both modes",
            _wrap_words("One connecting line = one scenario across both modes", limit=32),
        ),
        (
            "line_good",
            f"Odylith on improves recall and {time_axis_noun}",
            _wrap_words(f"Odylith on improves recall and {time_axis_noun}", limit=32),
        ),
        (
            "line_warn",
            "Split tradeoff or one-axis improvement",
            _wrap_words("Split tradeoff or one-axis improvement", limit=32),
        ),
        (
            "line_bad",
            f"{baseline_compact_label} wins recall and {time_axis_noun}",
            _wrap_words(f"{baseline_compact_label} wins recall and {time_axis_noun}", limit=32),
        ),
    ]
    legend_row_heights = [max(24, len(lines) * 18 + 6) for _kind, _label, lines in legend_items]
    legend_h = 58 + sum(legend_row_heights) + 18
    read_y = right_y + summary_h + card_gap
    spotlight_y = read_y + read_h + card_gap
    legend_y = spotlight_y + spotlight_h + card_gap
    footer_line_height = 16
    footer_lines: list[str] = []
    for line in (
        _report_meta(report),
        f"Visual pair: {candidate_mode} vs {baseline_mode}",
        f"Source: {_report_source_label(report)}",
    ):
        footer_lines.extend(_wrap_words(line, limit=52) or [line])
    footer_y = legend_y + legend_h + 42
    footer_bottom = footer_y + max(0, len(footer_lines) - 1) * footer_line_height + 12
    plot_h = max(plot_h, int(footer_bottom - plot_y - 104))
    plot_bottom = plot_y + plot_h + 78
    panel_bottom = max(plot_bottom, footer_bottom) + 36
    panel_height = panel_bottom - 40
    svg_height = max(SVG_HEIGHT, int(panel_bottom + 40))

    body: list[str] = [
        f'<rect x="44" y="40" width="1512" height="{panel_height:.0f}" rx="28" fill="{_PANEL}" stroke="{_GRID}" stroke-width="1.5"/>',
        f'<text x="86" y="86" class="title">{_quality_frontier_heading(report)}</text>',
    ]
    _append_text_lines(body, x=86, y=subtitle_y, lines=subtitle_lines, class_name="subtitle", line_height=18)
    body.append(f'<text x="86" y="{status_y}" class="small">Static chart: full recall range | all {total_count} published scenarios in frame</text>')
    status_suffix = (
        "| prompt-only control stays on the 0.00 recall rail by contract; paired packet time still separates scenarios"
        if prompt_only_control
        else "| all 60 points stay naturally visible on observed paired-time spread"
    )
    body.append(f'<text x="478" y="{status_y}" class="small" fill="{_GOOD}">{_esc(status_suffix)}</text>')

    body.append(f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" rx="24" fill="#faf7ef" stroke="{_GRID}" stroke-width="1"/>')

    x_tick_values = (0.0, 0.25, 0.5, 0.75, 1.0)
    y_tick_values = tuple(y_max * index / 6 for index in range(0, 7))
    for tick in x_tick_values:
        x = _plot_x(tick, plot_x=plot_x, plot_w=plot_w)
        body.append(f'<line x1="{x:.2f}" y1="{plot_y}" x2="{x:.2f}" y2="{plot_y + plot_h}" stroke="{_GRID}" stroke-width="1" opacity="0.8"/>')
        body.append(f'<text x="{x:.2f}" y="{plot_y + plot_h + 26}" class="axis" text-anchor="middle">{tick:.2f}</text>')
    for tick in y_tick_values:
        y = plot_y + plot_h - ((tick / max(1.0, y_max)) * plot_h)
        body.append(f'<line x1="{plot_x}" y1="{y:.2f}" x2="{plot_x + plot_w}" y2="{y:.2f}" stroke="{_GRID}" stroke-width="1" opacity="0.8"/>')
        tick_label = _human_duration_label(tick) if live_proof else str(int(round(tick)))
        body.append(f'<text x="{plot_x - 18}" y="{y + 4:.2f}" class="axis" text-anchor="end">{_esc(tick_label)}</text>')

    body.extend(
        [
            f'<line x1="{plot_x}" y1="{plot_y + plot_h}" x2="{plot_x + plot_w}" y2="{plot_y + plot_h}" stroke="{_TEXT}" stroke-width="2"/>',
            f'<line x1="{plot_x}" y1="{plot_y}" x2="{plot_x}" y2="{plot_y + plot_h}" stroke="{_TEXT}" stroke-width="2"/>',
            f'<text x="{plot_x + plot_w / 2:.2f}" y="{plot_y + plot_h + 54}" class="label" text-anchor="middle">Grounding recall</text>',
            f'<text x="{plot_x - 58}" y="{plot_y + plot_h / 2:.2f}" class="label" text-anchor="middle" transform="rotate(-90 {plot_x - 58} {plot_y + plot_h / 2:.2f})">{_esc(time_axis_noun.capitalize() if live_proof else time_axis_noun.capitalize() + " (ms)")}</text>',
            f'<text x="{plot_x}" y="{plot_y + plot_h + 78}" class="small">All published scenario pairs stay in frame without synthetic spreading because {time_axis_noun} provides natural point separation.</text>',
        ]
    )
    if prompt_only_control:
        body.append(f'<text x="{plot_x + 18}" y="{plot_y + 28}" class="small" fill="{_BASELINE}">Prompt-only control rail</text>')

    def _median_line(position: float, *, vertical: bool, color: str) -> None:
        if vertical:
            body.append(f'<line x1="{position:.2f}" y1="{plot_y}" x2="{position:.2f}" y2="{plot_y + plot_h}" stroke="{color}" stroke-width="1.8" stroke-dasharray="7 6" opacity="0.8"/>')
        else:
            body.append(f'<line x1="{plot_x}" y1="{position:.2f}" x2="{plot_x + plot_w}" y2="{position:.2f}" stroke="{color}" stroke-width="1.8" stroke-dasharray="7 6" opacity="0.8"/>')

    _median_line(_plot_x(baseline_median_recall, plot_x=plot_x, plot_w=plot_w), vertical=True, color=_BASELINE)
    _median_line(_plot_x(candidate_median_recall, plot_x=plot_x, plot_w=plot_w), vertical=True, color=_ODYLITH)
    _median_line(plot_y + plot_h - ((baseline_median_latency / max(1.0, y_max)) * plot_h), vertical=False, color=_BASELINE)
    _median_line(plot_y + plot_h - ((candidate_median_latency / max(1.0, y_max)) * plot_h), vertical=False, color=_ODYLITH)

    for row in enriched_pairs:
        x1 = _plot_x(float(row["baseline_recall"]), plot_x=plot_x, plot_w=plot_w)
        y1 = plot_y + plot_h - ((float(row["baseline_latency"]) / max(1.0, y_max)) * plot_h)
        x2 = _plot_x(float(row["candidate_recall"]), plot_x=plot_x, plot_w=plot_w)
        y2 = plot_y + plot_h - ((float(row["candidate_latency"]) / max(1.0, y_max)) * plot_h)
        improved_recall = float(row["candidate_recall"]) >= float(row["baseline_recall"])
        improved_latency = float(row["candidate_latency"]) <= float(row["baseline_latency"])
        line_color = _GOOD if improved_recall and improved_latency else _WARN if improved_recall or improved_latency else _BAD
        body.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{line_color}" stroke-width="2.4" opacity="0.68"/>')
        body.append(f'<circle cx="{x1:.2f}" cy="{y1:.2f}" r="5.3" fill="{_BASELINE}" stroke="{_PANEL}" stroke-width="1.4"/>')
        body.append(f'<polygon points="{_diamond_points(x2, y2, 6.2)}" fill="{_ODYLITH}" stroke="{_PANEL}" stroke-width="1.4"/>')

    body.extend(
        [
            f'<rect x="{right_x}" y="{right_y}" width="{right_w}" height="{summary_h}" rx="22" fill="{_BG}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_inner_x}" y="{right_y + summary_title_y_offset}" class="value">Median tradeoff</text>',
            f'<line x1="{right_x + 24}" y1="{right_y + summary_rule_y_offset}" x2="{right_inner_right}" y2="{right_y + summary_rule_y_offset}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_inner_x}" y="{right_y + summary_prompt_label_y_offset}" class="small">Grounding recall</text>',
            f'<text x="{right_inner_x}" y="{right_y + summary_prompt_value_y_offset}" class="value" fill="{recall_delta_color}">{_esc(_fmt_delta(recall_delta, digits=3))}</text>',
            f'<text x="{summary_value_right_x}" y="{right_y + summary_prompt_value_y_offset}" class="small" text-anchor="end">{baseline_short_label} {baseline_median_recall:.3f} -> {candidate_short_label} {candidate_median_recall:.3f}</text>',
            f'<line x1="{right_x + 24}" y1="{right_y + summary_mid_rule_y_offset}" x2="{right_inner_right}" y2="{right_y + summary_mid_rule_y_offset}" stroke="{_GRID}" stroke-width="1"/>',
            f'<text x="{right_inner_x}" y="{right_y + summary_latency_label_y_offset}" class="small">{_esc(time_axis_noun.capitalize())}</text>',
            f'<text x="{right_inner_x}" y="{right_y + summary_latency_value_y_offset}" class="value" fill="{latency_delta_color}">{_esc((_relative_delta_percent_label(latency_delta, baseline_median_latency) + f" ({_signed_human_duration_label(latency_delta)})") if live_proof else (_fmt_delta(latency_delta, digits=3) + " ms"))}</text>',
            f'<text x="{summary_value_right_x}" y="{right_y + summary_latency_value_y_offset}" class="small" text-anchor="end">{_esc((f"{baseline_short_label} {_human_duration_label(baseline_median_latency)} -> {candidate_short_label} {_human_duration_label(candidate_median_latency)}") if live_proof else (f"{baseline_short_label} {baseline_median_latency:.3f} ms -> {candidate_short_label} {candidate_median_latency:.3f} ms"))}</text>',
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
            f'<text x="{right_inner_x}" y="{spotlight_y + 30}" class="value">Scenario spotlight</text>',
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
    if spotlight_pairs:
        for index, row in enumerate(spotlight_pairs):
            y = spotlight_y + spotlight_row_top + index * spotlight_row_step
            body.extend(
                [
                    f'<rect x="{right_x + 24}" y="{y - 18}" width="{right_w - 48}" height="34" rx="10" fill="{_PANEL}" stroke="{_GRID}" stroke-width="1"/>',
                    f'<text x="{right_x + 38}" y="{y + 2}" class="label">{_esc(_short_label(str(row["label"]), limit=22))}</text>',
                    f'<text x="{right_inner_right - 16}" y="{y + 2}" class="small" text-anchor="end">{_esc((f"R {_fmt_delta(float(row['delta_recall']), digits=3)} | {_signed_human_duration_label(float(row['delta_latency']))}") if live_proof else (f"R {_fmt_delta(float(row['delta_recall']), digits=3)} | {float(row['delta_latency']):+.1f} ms"))}</text>',
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
            body.append(f'<circle cx="{right_x + 38}" cy="{legend_cursor}" r="5.5" fill="{_BASELINE}"/>')
        elif kind == "diamond":
            body.append(f'<polygon points="{_diamond_points(right_x + 38, legend_cursor, 6.2)}" fill="{_ODYLITH}"/>')
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
    return _svg_canvas(title=QUALITY_FRONTIER_TITLE, body=body, height=svg_height)


def render_marketing_graph_assets(report: Mapping[str, Any]) -> dict[str, str]:
    return {
        QUALITY_FRONTIER_FILENAME: render_quality_frontier_svg(report),
    }
