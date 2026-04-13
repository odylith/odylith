from __future__ import annotations

import json
from pathlib import Path
import re

from odylith.runtime.evaluation import odylith_benchmark_graphs as graphs


def test_render_graph_assets_writes_codex_benchmark_svgs(tmp_path: Path) -> None:
    report = {
        "report_id": "test-report",
        "generated_utc": "2026-03-29T08:20:59Z",
        "scenario_count": 1,
        "primary_comparison": {
            "candidate_mode": "odylith_on",
            "baseline_mode": "odylith_repo_scan_baseline",
        },
        "scenarios": [
            {
                "scenario_id": "tooling-shell",
                "label": "Tooling shell renderer slice",
                "family": "cross_file_feature",
                "results": [
                    {
                        "mode": "odylith_on",
                        "codex_prompt_estimated_tokens": 119,
                        "latency_ms": 26.554,
                        "total_payload_estimated_tokens": 119,
                        "required_path_recall": 1.0,
                        "validation_success_proxy": 1.0,
                    },
                    {
                        "mode": "odylith_repo_scan_baseline",
                        "codex_prompt_estimated_tokens": 520,
                        "latency_ms": 36.99,
                        "total_payload_estimated_tokens": 520,
                        "required_path_recall": 0.0,
                        "validation_success_proxy": 0.0,
                    },
                ],
            }
        ],
        "family_summaries": {
            "cross_file_feature": {
                "odylith_on": {
                    "median_effective_tokens": 119.0,
                    "median_latency_ms": 26.554,
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "correctness_critical_scenario_count": 0,
                },
                "odylith_repo_scan_baseline": {
                    "median_effective_tokens": 520.0,
                    "median_latency_ms": 36.99,
                    "required_path_recall_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                    "correctness_critical_scenario_count": 0,
                },
            }
        },
        "adoption_proof": {
            "packet_present_rate": 1.0,
            "auto_grounded_rate": 0.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 0.5,
            "grounded_delegate_rate": 0.5,
            "requires_widening_rate": 0.0,
            "workspace_daemon_reused_rate": 0.0,
            "session_namespaced_rate": 0.0,
            "operation_distribution": {
                "impact": 1,
            },
        },
        "runtime_posture": {
            "governance_runtime_first_usage_rate": 1.0,
            "repo_scan_degraded_fallback_rate": 0.0,
            "memory_standardization_state": "standardized",
        },
    }

    written = graphs.render_graph_assets(report, out_dir=tmp_path)

    assert {path.name for path in written} == {
        graphs.QUALITY_FRONTIER_FILENAME,
        graphs.FRONTIER_FILENAME,
        graphs.HEATMAP_FILENAME,
        graphs.POSTURE_FILENAME,
    }
    for path in written:
        contents = path.read_text(encoding="utf-8")
        assert "<svg" in contents
        assert "test-report" in contents
        assert "Odylith" in contents or "Codex" in contents
    quality_frontier = (tmp_path / graphs.QUALITY_FRONTIER_FILENAME).read_text(encoding="utf-8")
    frontier = (tmp_path / graphs.FRONTIER_FILENAME).read_text(encoding="utf-8")
    assert "grounding recall vs time to valid outcome" in quality_frontier
    assert "Median tradeoff" in quality_frontier
    assert "Scenario spotlight" in quality_frontier
    assert "Static chart: full recall range" in quality_frontier
    assert "published scenarios in frame" in quality_frontier
    assert "Visual pair:" in quality_frontier
    assert "all 60 points stay naturally visible" in quality_frontier
    assert graphs._FRONTIER_BASELINE in frontier
    assert graphs._FRONTIER_ODYLITH in frontier
    assert "Focus window" in frontier
    assert "How to read" in frontier
    assert "Repo-scan baseline" in frontier


def test_render_graph_assets_prefers_published_conservative_view(tmp_path: Path) -> None:
    report = {
        "report_id": "test-report",
        "generated_utc": "2026-03-29T08:20:59Z",
        "scenario_count": 1,
        "published_view_strategy": "conservative_multi_profile",
        "published_cache_profiles": ["warm", "cold"],
        "primary_comparison": {
            "candidate_mode": "odylith_on",
            "baseline_mode": "odylith_repo_scan_baseline",
        },
        "published_comparison": {
            "candidate_mode": "odylith_on",
            "baseline_mode": "odylith_repo_scan_baseline",
        },
        "scenarios": [
            {
                "scenario_id": "tooling-shell",
                "label": "Tooling shell renderer slice",
                "family": "cross_file_feature",
                "results": [
                    {
                        "mode": "odylith_on",
                        "codex_prompt_estimated_tokens": 119,
                        "latency_ms": 26.554,
                        "total_payload_estimated_tokens": 119,
                        "required_path_recall": 1.0,
                        "validation_success_proxy": 1.0,
                    },
                    {
                        "mode": "raw_agent_baseline",
                        "codex_prompt_estimated_tokens": 90,
                        "latency_ms": 12.0,
                        "total_payload_estimated_tokens": 90,
                        "required_path_recall": 0.0,
                        "validation_success_proxy": 0.0,
                    },
                    {
                        "mode": "odylith_repo_scan_baseline",
                        "codex_prompt_estimated_tokens": 520,
                        "latency_ms": 36.99,
                        "total_payload_estimated_tokens": 520,
                        "required_path_recall": 0.0,
                        "validation_success_proxy": 0.0,
                    },
                ],
            }
        ],
        "published_scenarios": [
            {
                "scenario_id": "tooling-shell",
                "label": "Tooling shell renderer slice",
                "family": "cross_file_feature",
                "results": [
                    {
                        "mode": "odylith_on",
                        "codex_prompt_estimated_tokens": 200,
                        "latency_ms": 31.0,
                        "total_payload_estimated_tokens": 200,
                        "required_path_recall": 1.0,
                        "validation_success_proxy": 1.0,
                    },
                    {
                        "mode": "raw_agent_baseline",
                        "codex_prompt_estimated_tokens": 80,
                        "latency_ms": 9.0,
                        "total_payload_estimated_tokens": 80,
                        "required_path_recall": 0.0,
                        "validation_success_proxy": 0.0,
                    },
                    {
                        "mode": "odylith_repo_scan_baseline",
                        "codex_prompt_estimated_tokens": 400,
                        "latency_ms": 41.0,
                        "total_payload_estimated_tokens": 400,
                        "required_path_recall": 0.0,
                        "validation_success_proxy": 0.0,
                    },
                ],
            }
        ],
        "family_summaries": {
            "cross_file_feature": {
                "odylith_on": {
                    "median_effective_tokens": 119.0,
                    "median_latency_ms": 26.554,
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "correctness_critical_scenario_count": 0,
                },
                "raw_agent_baseline": {
                    "median_effective_tokens": 90.0,
                    "median_latency_ms": 12.0,
                    "required_path_recall_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                    "correctness_critical_scenario_count": 0,
                },
                "odylith_repo_scan_baseline": {
                    "median_effective_tokens": 520.0,
                    "median_latency_ms": 36.99,
                    "required_path_recall_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                    "correctness_critical_scenario_count": 0,
                },
            }
        },
        "published_family_summaries": {
            "cross_file_feature": {
                "odylith_on": {
                    "median_effective_tokens": 200.0,
                    "median_latency_ms": 31.0,
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "correctness_critical_scenario_count": 0,
                },
                "raw_agent_baseline": {
                    "median_effective_tokens": 80.0,
                    "median_latency_ms": 9.0,
                    "required_path_recall_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                    "correctness_critical_scenario_count": 0,
                },
                "odylith_repo_scan_baseline": {
                    "median_effective_tokens": 400.0,
                    "median_latency_ms": 41.0,
                    "required_path_recall_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                    "correctness_critical_scenario_count": 0,
                },
            }
        },
        "adoption_proof": {
            "packet_present_rate": 1.0,
            "auto_grounded_rate": 0.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 0.5,
            "grounded_delegate_rate": 0.5,
            "requires_widening_rate": 0.0,
            "workspace_daemon_reused_rate": 0.0,
            "session_namespaced_rate": 0.0,
            "operation_distribution": {"impact": 1},
        },
        "runtime_posture": {
            "governance_runtime_first_usage_rate": 1.0,
            "repo_scan_degraded_fallback_rate": 0.0,
            "memory_standardization_state": "standardized",
        },
    }

    graphs.render_graph_assets(report, out_dir=tmp_path)

    quality_frontier = (tmp_path / graphs.QUALITY_FRONTIER_FILENAME).read_text(encoding="utf-8")
    frontier = (tmp_path / graphs.FRONTIER_FILENAME).read_text(encoding="utf-8")
    heatmap = (tmp_path / graphs.HEATMAP_FILENAME).read_text(encoding="utf-8")
    assert "off 0.000 -> on 1.000" in quality_frontier
    assert "Odylith on improves recall and" in quality_frontier
    assert "time to valid outcome" in quality_frontier
    assert "Visual pair: odylith_on vs raw_agent_baseline" in quality_frontier
    assert "Static chart: full recall range | all 1 published scenarios in frame" in quality_frontier
    assert "One connecting line = one" in quality_frontier
    assert "scenario across both modes" in quality_frontier
    assert "Scenario spotlight" in quality_frontier
    assert "Median tradeoff" in frontier
    assert "off 80 -&gt; on 200" in frontier
    assert "+150%" in frontier
    assert "+244% (+22 ms)" in frontier
    assert "Live Benchmark Quality Frontier" in quality_frontier
    assert "Live Benchmark: time to valid outcome vs live session input" in frontier
    assert "Live Benchmark Family Heatmap" in heatmap
    assert "Visual pair: odylith_on vs raw_agent_baseline" in frontier
    assert "conservative_multi_profile" in frontier
    assert "warm, cold" in frontier
    assert "+120" in heatmap
    assert "Time to valid outcome" in heatmap
    assert "compact token deltas" in heatmap
    assert "shown as humanized durations" in heatmap
    assert heatmap.index(">Recall</text>") < heatmap.index(">Live session input</text>")
    assert heatmap.index(">Validation</text>") < heatmap.index(">Time to valid outcome</text>")
    assert heatmap.count('class="subtitle"') >= 2


def test_frontier_summary_card_uses_roomier_tradeoff_spacing() -> None:
    frontier = graphs._render_frontier_svg(  # noqa: SLF001
        {
            "report_id": "summary-spacing-report",
            "generated_utc": "2026-03-31T21:13:10Z",
            "scenario_count": 1,
            "published_view_strategy": "conservative_multi_profile",
            "published_cache_profiles": ["warm", "cold"],
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "raw_agent_baseline",
            },
            "published_scenarios": [
                {
                    "scenario_id": "summary-card",
                    "label": "Summary card spacing",
                    "family": "cross_file_feature",
                    "results": [
                        {
                            "mode": "odylith_on",
                            "codex_prompt_estimated_tokens": 136,
                            "latency_ms": 11.410,
                            "total_payload_estimated_tokens": 162,
                        },
                        {
                            "mode": "raw_agent_baseline",
                            "codex_prompt_estimated_tokens": 90,
                            "latency_ms": 2.478,
                            "total_payload_estimated_tokens": 90,
                        },
                    ],
                }
            ],
        }
    )

    summary_match = re.search(
        r'<rect x="1060" y="\d+" width="436" height="(\d+)" rx="22" fill="#f6f1e7" stroke="#d8cfbd" stroke-width="1"/><text x="1088" y="\d+" class="value">Median tradeoff</text>',
        frontier,
    )
    prompt_row_match = re.search(
        r'<text x="1088" y="(\d+)" class="small">Live session input</text><text x="1088" y="(\d+)" class="value" fill="[^"]+">\+51%</text><text x="1464" y="(\d+)" class="small" text-anchor="end">off 90 -&gt; on 136</text>',
        frontier,
    )
    latency_row_match = re.search(
        r'<text x="1088" y="(\d+)" class="small">Time to valid outcome</text><text x="1088" y="(\d+)" class="value" fill="[^"]+">\+360% \(\+9 ms\)</text><text x="1464" y="(\d+)" class="small" text-anchor="end">off 2 ms -&gt; on 11 ms</text>',
        frontier,
    )

    assert summary_match is not None
    assert int(summary_match.group(1)) >= 220
    assert prompt_row_match is not None
    assert int(prompt_row_match.group(2)) - int(prompt_row_match.group(1)) >= 30
    assert int(prompt_row_match.group(3)) == int(prompt_row_match.group(2))
    assert latency_row_match is not None
    assert int(latency_row_match.group(2)) - int(latency_row_match.group(1)) >= 30
    assert int(latency_row_match.group(3)) == int(latency_row_match.group(2))


def test_family_heatmap_prefers_published_family_deltas() -> None:
    heatmap = graphs._render_family_heatmap_svg(  # noqa: SLF001
        {
            "report_id": "delta-report",
            "generated_utc": "2026-03-29T08:20:59Z",
            "scenario_count": 1,
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "odylith_repo_scan_baseline",
            },
            "published_family_summaries": {
                "cross_file_feature": {
                    "odylith_on": {
                        "median_effective_tokens": 200.0,
                        "median_latency_ms": 31.0,
                        "required_path_recall_rate": 1.0,
                        "validation_success_rate": 1.0,
                        "expectation_success_rate": 1.0,
                        "correctness_critical_scenario_count": 0,
                    },
                    "odylith_repo_scan_baseline": {
                        "median_effective_tokens": 400.0,
                        "median_latency_ms": 41.0,
                        "required_path_recall_rate": 0.0,
                        "validation_success_rate": 0.0,
                        "expectation_success_rate": 0.0,
                        "correctness_critical_scenario_count": 0,
                    },
                }
            },
            "published_family_deltas": {
                "cross_file_feature": {
                    "median_prompt_token_delta": -137.0,
                    "median_latency_delta_ms": -9.5,
                    "required_path_recall_delta": 0.75,
                    "validation_success_delta": 0.5,
                    "expectation_success_delta": 0.25,
                }
            },
            "adoption_proof": {},
            "runtime_posture": {},
        }
    )

    assert "-137" in heatmap
    assert "-10 ms" in heatmap
    assert "+0.750" in heatmap


def test_report_meta_lines_wrap_long_published_strategy() -> None:
    lines = graphs._report_meta_lines(
        {
            "report_id": "21b8a857cf5d6318",
            "generated_utc": "2026-03-29T22:50:03Z",
            "scenario_count": 24,
            "published_view_strategy": "conservative_multi_profile",
            "published_cache_profiles": ["warm", "cold"],
        },
        limit=44,
    )

    assert len(lines) >= 2
    assert "21b8a857cf5d6318" in " ".join(lines)
    assert "conservative_multi_profile" in " ".join(lines)


def test_family_heatmap_expands_svg_height_for_tall_family_tables(tmp_path: Path) -> None:
    families = {
        f"family_{index}": {
            "odylith_on": {
                "median_effective_tokens": 100.0,
                "median_latency_ms": 20.0,
                "required_path_recall_rate": 1.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "correctness_critical_scenario_count": 0,
            },
            "odylith_repo_scan_baseline": {
                "median_effective_tokens": 300.0,
                "median_latency_ms": 40.0,
                "required_path_recall_rate": 0.0,
                "validation_success_rate": 0.0,
                "expectation_success_rate": 0.0,
                "correctness_critical_scenario_count": 0,
            },
        }
        for index in range(24)
    }
    report = {
        "report_id": "tall-report",
        "generated_utc": "2026-03-29T22:50:03Z",
        "scenario_count": 24,
        "published_view_strategy": "conservative_multi_profile",
        "published_cache_profiles": ["warm", "cold"],
        "published_comparison": {
            "candidate_mode": "odylith_on",
            "baseline_mode": "odylith_repo_scan_baseline",
        },
        "published_family_summaries": families,
        "adoption_proof": {},
        "runtime_posture": {},
    }

    graphs.render_graph_assets(report, out_dir=tmp_path)

    heatmap = (tmp_path / graphs.HEATMAP_FILENAME).read_text(encoding="utf-8")
    assert 'height="' in heatmap
    assert 'viewBox="0 0 1600 ' in heatmap
    match = re.search(r'height="(\d+)" viewBox="0 0 1600 (\d+)"', heatmap)
    assert match is not None
    assert match.group(1) == match.group(2)
    assert int(match.group(1)) > graphs.SVG_HEIGHT


def test_operating_posture_expands_operation_mix_card_for_multiple_rows() -> None:
    posture = graphs._render_operating_posture_svg(  # noqa: SLF001
        {
            "report_id": "op-mix-report",
            "generated_utc": "2026-03-31T17:32:45Z",
            "scenario_count": 12,
            "adoption_proof": {
                "packet_present_rate": 0.9,
                "auto_grounded_rate": 0.9,
                "route_ready_rate": 0.75,
                "native_spawn_ready_rate": 0.75,
                "grounded_delegate_rate": 0.42,
                "operation_distribution": {
                    "impact": 5,
                    "architecture": 3,
                    "governance_slice": 3,
                    "none": 1,
                },
            },
            "runtime_posture": {},
        }
    )

    match = re.search(r'<rect x="1056" y="\d+" width="440" height="(\d+)" rx="22" fill="#f6f1e7"', posture)
    assert match is not None
    assert int(match.group(1)) >= 324
    assert ">None</text>" in posture
    assert 'text-anchor="end">1 scenarios</text>' in posture


def test_graph_comparison_falls_back_to_repo_scan_lane_when_raw_is_absent() -> None:
    comparison = graphs._graph_comparison(  # noqa: SLF001
        {
            "report_id": "fallback-report",
            "generated_utc": "2026-03-31T16:00:00Z",
            "scenario_count": 1,
            "published_scenarios": [
                {
                    "scenario_id": "fallback-scenario",
                    "label": "Fallback scenario",
                    "family": "cross_file_feature",
                    "results": [
                        {"mode": "odylith_on", "codex_prompt_estimated_tokens": 120, "latency_ms": 25.0},
                        {"mode": "odylith_repo_scan_baseline", "codex_prompt_estimated_tokens": 420, "latency_ms": 45.0},
                    ],
                }
            ],
        }
    )

    assert comparison == {
        "candidate_mode": "odylith_on",
        "baseline_mode": "odylith_repo_scan_baseline",
    }


def test_scenario_rows_normalize_public_odylith_off_alias() -> None:
    rows = graphs._scenario_rows(  # noqa: SLF001
        {
            "report_id": "public-alias-report",
            "generated_utc": "2026-04-02T17:10:00Z",
            "scenario_count": 1,
            "published_mode_table": {
                "mode_order": ["odylith_on", "odylith_off"],
            },
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "odylith_off",
            },
            "published_scenarios": [
                {
                    "scenario_id": "alias-scenario",
                    "label": "Alias scenario",
                    "family": "cross_file_feature",
                    "results": [
                        {
                            "mode": "odylith_on",
                            "codex_prompt_estimated_tokens": 140,
                            "latency_ms": 8.75,
                            "total_payload_estimated_tokens": 160,
                            "required_path_recall": 1.0,
                            "validation_success_proxy": 1.0,
                        },
                        {
                            "mode": "raw_agent_baseline",
                            "codex_prompt_estimated_tokens": 88,
                            "latency_ms": 0.012,
                            "total_payload_estimated_tokens": 88,
                            "required_path_recall": 0.0,
                            "validation_success_proxy": 0.0,
                        },
                    ],
                }
            ],
        }
    )

    assert len(rows) == 1
    assert rows[0]["candidate_prompt"] == 140.0
    assert rows[0]["baseline_prompt"] == 88.0
    assert rows[0]["candidate_latency"] == 8.75
    assert rows[0]["baseline_latency"] == 0.012


def test_frontier_uses_axis_labels_not_function_repr_for_diagnostic_alias_reports() -> None:
    frontier = graphs._render_frontier_svg(  # noqa: SLF001
        {
            "report_id": "diagnostic-frontier-alias-report",
            "generated_utc": "2026-04-02T17:15:00Z",
            "scenario_count": 1,
            "benchmark_profile": "diagnostic",
            "comparison_contract": "internal_packet_prompt_diagnostic",
            "published_mode_table": {
                "mode_order": ["odylith_on", "odylith_off"],
            },
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "odylith_off",
            },
            "published_scenarios": [
                {
                    "scenario_id": "diagnostic-alias",
                    "label": "Diagnostic alias scenario",
                    "family": "cross_file_feature",
                    "results": [
                        {
                            "mode": "odylith_on",
                            "codex_prompt_estimated_tokens": 148,
                            "latency_ms": 8.706,
                            "total_payload_estimated_tokens": 195,
                            "required_path_recall": 1.0,
                            "validation_success_proxy": 1.0,
                        },
                        {
                            "mode": "raw_agent_baseline",
                            "codex_prompt_estimated_tokens": 96,
                            "latency_ms": 0.005,
                            "total_payload_estimated_tokens": 96,
                            "required_path_recall": 0.0,
                            "validation_success_proxy": 0.0,
                        },
                    ],
                }
            ],
        }
    )

    assert "<function" not in frontier
    assert "prompt-bundle input" in frontier
    assert "packet time" in frontier
    assert "Static chart: Focus window | 1 of 1 scenarios in frame" in frontier
    assert "off 96 -&gt; on 148" in frontier


def test_family_heatmap_gives_diagnostic_headers_room_for_long_axis_labels() -> None:
    heatmap = graphs._render_family_heatmap_svg(  # noqa: SLF001
        {
            "report_id": "diagnostic-heatmap-spacing-report",
            "generated_utc": "2026-04-02T17:22:00Z",
            "scenario_count": 1,
            "benchmark_profile": "diagnostic",
            "comparison_contract": "internal_packet_prompt_diagnostic",
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "raw_agent_baseline",
            },
            "published_family_summaries": {
                "cross_file_feature": {
                    "odylith_on": {
                        "median_effective_tokens": 148.0,
                        "median_latency_ms": 8.706,
                        "required_path_recall_rate": 1.0,
                        "validation_success_rate": 1.0,
                        "expectation_success_rate": 1.0,
                        "correctness_critical_scenario_count": 0,
                    },
                    "raw_agent_baseline": {
                        "median_effective_tokens": 96.0,
                        "median_latency_ms": 0.005,
                        "required_path_recall_rate": 0.0,
                        "validation_success_rate": 0.0,
                        "expectation_success_rate": 0.0,
                        "correctness_critical_scenario_count": 0,
                    },
                }
            },
            "published_family_deltas": {
                "cross_file_feature": {
                    "median_prompt_token_delta": 52.0,
                    "median_latency_delta_ms": 8.701,
                    "required_path_recall_delta": 1.0,
                    "validation_success_delta": 1.0,
                    "expectation_success_delta": 1.0,
                }
            },
        }
    )

    prompt_match = re.search(
        r'<text x="([0-9.]+)" y="[^"]+" class="label" text-anchor="middle" font-weight="700">Prompt-bundle input</text>',
        heatmap,
    )
    latency_match = re.search(
        r'<text x="([0-9.]+)" y="[^"]+" class="label" text-anchor="middle" font-weight="700">Packet time \(ms\)</text>',
        heatmap,
    )

    assert prompt_match is not None
    assert latency_match is not None
    assert float(latency_match.group(1)) - float(prompt_match.group(1)) >= 180.0


def test_operating_posture_uses_diagnostic_summary_fallback_when_adoption_sample_is_absent() -> None:
    posture = graphs._render_operating_posture_svg(  # noqa: SLF001
        {
            "report_id": "diagnostic-posture-report",
            "generated_utc": "2026-04-02T17:29:00Z",
            "scenario_count": 32,
            "benchmark_profile": "diagnostic",
            "published_summary": {
                "adoption_proof_sample_size": 0,
                "odylith_packet_present_rate": 1.0,
                "odylith_auto_grounded_rate": 0.0,
                "odylith_grounded_delegate_rate": 0.25,
                "odylith_requires_widening_rate": 0.031,
                "odylith_workspace_daemon_reuse_rate": 0.0,
                "odylith_session_namespaced_rate": 0.0,
                "runtime_route_ready_rate": 0.917,
                "runtime_native_spawn_ready_rate": 0.917,
                "runtime_governance_runtime_first_usage_rate": 0.0,
                "runtime_repo_scan_degraded_fallback_rate": 0.0,
                "runtime_memory_standardization_state": "standardized",
            },
            "adoption_proof": {},
            "runtime_posture": {},
        }
    )

    assert "Not sampled" in posture
    assert "Operation mix is only published" in posture
    assert "Auto grounding applied" in posture
    assert "On demand" in posture
    assert "Not triggered" in posture
    assert ">100%</text>" in posture
    assert posture.count(">92%</text>") >= 2
    assert ">25%</text>" in posture
    assert "standardized" in posture
    assert "published_summary and runtime_posture" in posture


def test_frontier_calls_out_long_tail_outliers() -> None:
    frontier = graphs._render_frontier_svg(  # noqa: SLF001
        {
            "report_id": "outlier-report",
            "generated_utc": "2026-03-31T16:00:00Z",
            "scenario_count": 2,
            "published_view_strategy": "conservative_multi_profile",
            "published_cache_profiles": ["warm", "cold"],
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "raw_agent_baseline",
            },
                "published_scenarios": [
                    {
                        "scenario_id": "dense-cluster",
                    "label": "Dense cluster",
                    "family": "cross_file_feature",
                    "results": [
                        {
                            "mode": "odylith_on",
                            "codex_prompt_estimated_tokens": 140,
                            "latency_ms": 12.0,
                            "total_payload_estimated_tokens": 160,
                            "required_path_recall": 1.0,
                            "validation_success_proxy": 1.0,
                        },
                        {
                            "mode": "raw_agent_baseline",
                            "codex_prompt_estimated_tokens": 96,
                            "latency_ms": 2.0,
                            "total_payload_estimated_tokens": 96,
                            "required_path_recall": 0.0,
                            "validation_success_proxy": 0.0,
                        },
                    ],
                },
                    {
                        "scenario_id": "dense-cluster-2",
                        "label": "Dense cluster two",
                        "family": "cross_file_feature",
                        "results": [
                            {
                                "mode": "odylith_on",
                                "codex_prompt_estimated_tokens": 144,
                                "latency_ms": 11.0,
                                "total_payload_estimated_tokens": 164,
                                "required_path_recall": 1.0,
                                "validation_success_proxy": 1.0,
                            },
                            {
                                "mode": "raw_agent_baseline",
                                "codex_prompt_estimated_tokens": 98,
                                "latency_ms": 2.1,
                                "total_payload_estimated_tokens": 98,
                                "required_path_recall": 0.0,
                                "validation_success_proxy": 0.0,
                            },
                        ],
                    },
                    {
                        "scenario_id": "dense-cluster-3",
                        "label": "Dense cluster three",
                        "family": "cross_file_feature",
                        "results": [
                            {
                                "mode": "odylith_on",
                                "codex_prompt_estimated_tokens": 148,
                                "latency_ms": 13.0,
                                "total_payload_estimated_tokens": 168,
                                "required_path_recall": 1.0,
                                "validation_success_proxy": 1.0,
                            },
                            {
                                "mode": "raw_agent_baseline",
                                "codex_prompt_estimated_tokens": 100,
                                "latency_ms": 2.2,
                                "total_payload_estimated_tokens": 100,
                                "required_path_recall": 0.0,
                                "validation_success_proxy": 0.0,
                            },
                        ],
                    },
                    {
                        "scenario_id": "dense-cluster-4",
                        "label": "Dense cluster four",
                        "family": "cross_file_feature",
                        "results": [
                            {
                                "mode": "odylith_on",
                                "codex_prompt_estimated_tokens": 152,
                                "latency_ms": 12.5,
                                "total_payload_estimated_tokens": 172,
                                "required_path_recall": 1.0,
                                "validation_success_proxy": 1.0,
                            },
                            {
                                "mode": "raw_agent_baseline",
                                "codex_prompt_estimated_tokens": 102,
                                "latency_ms": 2.4,
                                "total_payload_estimated_tokens": 102,
                                "required_path_recall": 0.0,
                                "validation_success_proxy": 0.0,
                            },
                        ],
                    },
                    {
                        "scenario_id": "long-tail",
                        "label": "Long tail benchmark slice",
                        "family": "release_publication",
                    "results": [
                        {
                            "mode": "odylith_on",
                            "codex_prompt_estimated_tokens": 160,
                            "latency_ms": 220.0,
                            "total_payload_estimated_tokens": 180,
                            "required_path_recall": 1.0,
                            "validation_success_proxy": 1.0,
                        },
                        {
                            "mode": "raw_agent_baseline",
                            "codex_prompt_estimated_tokens": 110,
                            "latency_ms": 2.3,
                            "total_payload_estimated_tokens": 110,
                            "required_path_recall": 0.0,
                            "validation_success_proxy": 0.0,
                        },
                    ],
                },
            ],
        }
    )

    assert "1 long-tail outlier" in frontier
    assert "Long-tail spotlight" in frontier
    assert "Long tail benchmark slice" in frontier


def test_frontier_expands_long_tail_spotlight_for_three_rows() -> None:
    dense_rows = [
        {
            "scenario_id": f"dense-{index}",
            "label": f"Dense cluster {index}",
            "family": "cross_file_feature",
            "results": [
                {"mode": "odylith_on", "codex_prompt_estimated_tokens": 140 + (index % 3) * 4, "latency_ms": 12.0 + (index % 2), "total_payload_estimated_tokens": 160},
                {"mode": "raw_agent_baseline", "codex_prompt_estimated_tokens": 90 + (index % 3) * 2, "latency_ms": 2.0 + (index % 2) * 0.1, "total_payload_estimated_tokens": 90},
            ],
        }
        for index in range(27)
    ]
    frontier = graphs._render_frontier_svg(  # noqa: SLF001
        {
            "report_id": "outlier-stack-report",
            "generated_utc": "2026-03-31T16:00:00Z",
            "scenario_count": 30,
            "published_view_strategy": "conservative_multi_profile",
            "published_cache_profiles": ["warm", "cold"],
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "raw_agent_baseline",
            },
            "published_scenarios": [
                *dense_rows,
                {
                    "scenario_id": "outlier-1",
                    "label": "Benchmark publication make this very long",
                    "family": "release_publication",
                    "results": [
                        {"mode": "odylith_on", "codex_prompt_estimated_tokens": 140, "latency_ms": 241.0, "total_payload_estimated_tokens": 160},
                        {"mode": "raw_agent_baseline", "codex_prompt_estimated_tokens": 90, "latency_ms": 2.1, "total_payload_estimated_tokens": 90},
                    ],
                },
                {
                    "scenario_id": "outlier-2",
                    "label": "Benchmark proof and publication follow through",
                    "family": "release_publication",
                    "results": [
                        {"mode": "odylith_on", "codex_prompt_estimated_tokens": 265, "latency_ms": 6.4, "total_payload_estimated_tokens": 285},
                        {"mode": "raw_agent_baseline", "codex_prompt_estimated_tokens": 95, "latency_ms": 2.3, "total_payload_estimated_tokens": 95},
                    ],
                },
                {
                    "scenario_id": "outlier-3",
                    "label": "Benchmark component governance slice",
                    "family": "component_governance",
                    "results": [
                        {"mode": "odylith_on", "codex_prompt_estimated_tokens": 176, "latency_ms": 80.0, "total_payload_estimated_tokens": 196},
                        {"mode": "raw_agent_baseline", "codex_prompt_estimated_tokens": 96, "latency_ms": 2.4, "total_payload_estimated_tokens": 96},
                    ],
                },
            ],
        }
    )

    match = re.search(r'<rect x="1060" y="\d+" width="436" height="(\d+)" rx="22" fill="#f6f1e7" stroke="#d8cfbd" stroke-width="1"/><text x="1088" y="\d+" class="value">Long-tail spotlight</text>', frontier)
    assert match is not None
    assert int(match.group(1)) >= 202
    assert "3 scenarios sit outside the focus" in frontier
    assert "window." in frontier


def test_frontier_wraps_right_rail_copy_and_expands_cards() -> None:
    dense_rows = [
        {
            "scenario_id": f"dense-{index}",
            "label": f"Dense cluster {index}",
            "family": "cross_file_feature",
            "results": [
                {"mode": "odylith_on", "codex_prompt_estimated_tokens": 140 + (index % 3) * 4, "latency_ms": 12.0 + (index % 2), "total_payload_estimated_tokens": 160},
                {"mode": "raw_agent_baseline", "codex_prompt_estimated_tokens": 90 + (index % 3) * 2, "latency_ms": 2.0 + (index % 2) * 0.1, "total_payload_estimated_tokens": 90},
            ],
        }
        for index in range(29)
    ]
    frontier = graphs._render_frontier_svg(  # noqa: SLF001
        {
            "report_id": "wrapped-rail-report",
            "generated_utc": "2026-03-31T20:02:03Z",
            "scenario_count": 30,
            "published_view_strategy": "conservative_multi_profile",
            "published_cache_profiles": ["warm", "cold"],
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "raw_agent_baseline",
            },
            "published_scenarios": [
                *dense_rows,
                {
                    "scenario_id": "governance-outlier",
                    "label": "Benchmark component governance slice",
                    "family": "component_governance",
                    "results": [
                        {"mode": "odylith_on", "codex_prompt_estimated_tokens": 176, "latency_ms": 80.0, "total_payload_estimated_tokens": 196},
                        {"mode": "raw_agent_baseline", "codex_prompt_estimated_tokens": 96, "latency_ms": 2.4, "total_payload_estimated_tokens": 96},
                    ],
                },
            ],
        }
    )

    how_to_read_match = re.search(r'<rect x="1060" y="\d+" width="436" height="(\d+)" rx="22" fill="#f6f1e7" stroke="#d8cfbd" stroke-width="1"/><text x="1088" y="\d+" class="value">How to read</text>', frontier)
    legend_match = re.search(r'<rect x="1060" y="\d+" width="436" height="(\d+)" rx="22" fill="#f6f1e7" stroke="#d8cfbd" stroke-width="1"/><text x="1088" y="\d+" class="value">Marks and signals</text>', frontier)

    assert how_to_read_match is not None
    assert int(how_to_read_match.group(1)) > 92
    assert "Each line links the same benchmark" in frontier
    assert "scenario in both modes." in frontier
    assert "Read left/down as better." in frontier
    assert "The main field caps at" in frontier

    assert legend_match is not None
    assert int(legend_match.group(1)) > 206
    assert "One connecting line = one" in frontier
    assert "scenario across both modes" in frontier


def test_benchmark_graph_style_contract_stays_stable() -> None:
    assert graphs.QUALITY_FRONTIER_FILENAME == "odylith-benchmark-quality-frontier.svg"
    assert graphs.FRONTIER_FILENAME == "odylith-benchmark-frontier.svg"
    assert graphs.HEATMAP_FILENAME == "odylith-benchmark-family-heatmap.svg"
    assert graphs.POSTURE_FILENAME == "odylith-benchmark-operating-posture.svg"
    assert graphs.QUALITY_FRONTIER_TITLE == "Odylith benchmark quality frontier"
    assert graphs.FRONTIER_TITLE == "Odylith benchmark frontier"
    assert graphs.HEATMAP_TITLE == "Odylith benchmark family heatmap"
    assert graphs.POSTURE_TITLE == "Odylith benchmark operating posture"
    assert graphs.QUALITY_FRONTIER_HEADING == "Live Benchmark Quality Frontier: grounding recall vs time to valid outcome"
    assert graphs.FRONTIER_HEADING == "Live Benchmark: time to valid outcome vs live session input"
    assert graphs.HEATMAP_HEADING == "Live Benchmark Family Heatmap: where Odylith wins"
    assert graphs.POSTURE_HEADING == "Live Benchmark operating posture on the current proof-host corpus"
    assert graphs._BG == "#f6f1e7"
    assert graphs._PANEL == "#fffdfa"
    assert graphs._BASELINE == "#c75b52"
    assert graphs._ODYLITH == "#0f766e"
    assert graphs._FRONTIER_BASELINE == "#b64035"


def test_render_graph_assets_uses_diagnostic_labels_for_diagnostic_reports(tmp_path: Path) -> None:
    report = {
        "report_id": "diag-report",
        "generated_utc": "2026-04-02T12:00:00Z",
        "scenario_count": 1,
        "benchmark_profile": "diagnostic",
        "comparison_contract": "internal_packet_prompt_diagnostic",
        "repo_root": str(tmp_path),
        "_report_path": str(tmp_path / ".odylith" / "runtime" / "odylith-benchmarks" / "latest-diagnostic.v1.json"),
        "published_comparison": {
            "candidate_mode": "odylith_on",
            "baseline_mode": "raw_agent_baseline",
        },
        "published_scenarios": [
            {
                "scenario_id": "diag-case",
                "label": "Diagnostic case",
                "family": "cross_file_feature",
                "results": [
                    {
                        "mode": "odylith_on",
                        "codex_prompt_estimated_tokens": 120,
                        "latency_ms": 11.0,
                        "total_payload_estimated_tokens": 150,
                        "required_path_recall": 1.0,
                        "validation_success_proxy": 1.0,
                    },
                    {
                        "mode": "raw_agent_baseline",
                        "codex_prompt_estimated_tokens": 200,
                        "latency_ms": 9.0,
                        "total_payload_estimated_tokens": 240,
                        "required_path_recall": 0.0,
                        "validation_success_proxy": 0.0,
                    },
                ],
            }
        ],
        "published_family_summaries": {
            "cross_file_feature": {
                "odylith_on": {
                    "median_effective_tokens": 120.0,
                    "median_latency_ms": 11.0,
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "correctness_critical_scenario_count": 0,
                },
                "raw_agent_baseline": {
                    "median_effective_tokens": 200.0,
                    "median_latency_ms": 9.0,
                    "required_path_recall_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                    "correctness_critical_scenario_count": 0,
                },
            }
        },
        "published_family_deltas": {
            "cross_file_feature": {
                "median_prompt_token_delta": -80.0,
                "median_latency_delta_ms": 2.0,
                "required_path_recall_delta": 1.0,
                "validation_success_delta": 1.0,
                "expectation_success_delta": 1.0,
            }
        },
        "adoption_proof": {},
        "runtime_posture": {},
    }

    graphs.render_graph_assets(report, out_dir=tmp_path)

    frontier = (tmp_path / graphs.FRONTIER_FILENAME).read_text(encoding="utf-8")
    heatmap = (tmp_path / graphs.HEATMAP_FILENAME).read_text(encoding="utf-8")
    quality = (tmp_path / graphs.QUALITY_FRONTIER_FILENAME).read_text(encoding="utf-8")
    assert "Internal Diagnostic Benchmark: packet/prompt time vs prompt-bundle input" in frontier
    assert "Prompt-bundle input tokens" in frontier
    assert "Packet time (ms)" in frontier
    assert "Source: latest-diagnostic.v1.json" in frontier
    assert "Internal Diagnostic Family Heatmap" in heatmap
    assert "Prompt-bundle input" in heatmap
    assert "Packet time (ms)" in heatmap
    assert "Internal Diagnostic Quality Frontier" in quality
    assert "packet time" in quality
    assert "prompt-only raw host control" in quality
    assert "0.00 rail by contract" in quality
    assert "Prompt-only control rail" in quality


def test_diagnostic_quality_frontier_uses_compact_source_label_for_nonzero_baseline(tmp_path: Path) -> None:
    report = {
        "report_id": "diag-nonzero-baseline",
        "generated_utc": "2026-04-03T20:55:33Z",
        "scenario_count": 1,
        "benchmark_profile": "diagnostic",
        "comparison_contract": "internal_packet_prompt_diagnostic",
        "repo_root": str(tmp_path),
        "_report_path": str(tmp_path / ".odylith" / "runtime" / "odylith-benchmarks" / "latest-diagnostic.v1.json"),
        "published_comparison": {
            "candidate_mode": "odylith_on",
            "baseline_mode": "raw_agent_baseline",
        },
        "published_scenarios": [
            {
                "scenario_id": "diag-case",
                "label": "Diagnostic case",
                "family": "cross_file_feature",
                "results": [
                    {
                        "mode": "odylith_on",
                        "latency_ms": 11.0,
                        "required_path_recall": 1.0,
                    },
                    {
                        "mode": "raw_agent_baseline",
                        "latency_ms": 7.0,
                        "required_path_recall": 0.4,
                    },
                ],
            }
        ],
        "published_family_summaries": {
            "cross_file_feature": {
                "odylith_on": {"median_latency_ms": 11.0, "required_path_recall_rate": 1.0},
                "raw_agent_baseline": {"median_latency_ms": 7.0, "required_path_recall_rate": 0.4},
            }
        },
        "adoption_proof": {},
        "runtime_posture": {},
    }

    graphs.render_graph_assets(report, out_dir=tmp_path)
    quality = (tmp_path / graphs.QUALITY_FRONTIER_FILENAME).read_text(encoding="utf-8")

    assert "Prompt-only control rail" not in quality
    assert "0.00 rail by contract" not in quality
    assert "Source: latest-diagnostic.v1.json" in quality
    assert ".odylith/runtime/odylith-benchmarks/latest-diagnostic.v1.json" not in quality


def test_render_profile_graph_assets_writes_profile_subdirectories(tmp_path: Path) -> None:
    benchmark_root = tmp_path / ".odylith" / "runtime" / "odylith-benchmarks"
    benchmark_root.mkdir(parents=True, exist_ok=True)
    proof_report = {
        "report_id": "proof-report",
        "generated_utc": "2026-04-02T12:00:00Z",
        "scenario_count": 0,
        "benchmark_profile": "proof",
        "published_comparison": {"candidate_mode": "odylith_on", "baseline_mode": "raw_agent_baseline"},
        "published_scenarios": [],
        "published_family_summaries": {},
        "adoption_proof": {},
        "runtime_posture": {},
    }
    diagnostic_report = {
        "report_id": "diagnostic-report",
        "generated_utc": "2026-04-02T12:00:00Z",
        "scenario_count": 0,
        "benchmark_profile": "diagnostic",
        "comparison_contract": "internal_packet_prompt_diagnostic",
        "published_comparison": {"candidate_mode": "odylith_on", "baseline_mode": "raw_agent_baseline"},
        "published_scenarios": [],
        "published_family_summaries": {},
        "adoption_proof": {},
        "runtime_posture": {},
    }
    (benchmark_root / "latest-proof.v1.json").write_text(json.dumps(proof_report), encoding="utf-8")
    (benchmark_root / "latest-diagnostic.v1.json").write_text(json.dumps(diagnostic_report), encoding="utf-8")

    written = graphs.render_profile_graph_assets(
        repo_root=tmp_path,
        out_dir=tmp_path / "docs" / "benchmarks",
        benchmark_profiles=("proof", "diagnostic"),
    )

    assert set(written.keys()) == {"proof", "diagnostic"}
    assert (tmp_path / "docs" / "benchmarks" / "proof" / graphs.FRONTIER_FILENAME).is_file()
    assert (tmp_path / "docs" / "benchmarks" / "diagnostic" / graphs.FRONTIER_FILENAME).is_file()


def test_render_profile_graph_assets_uses_canonical_latest_for_proof_when_profile_snapshot_missing(tmp_path: Path) -> None:
    benchmark_root = tmp_path / ".odylith" / "runtime" / "odylith-benchmarks"
    benchmark_root.mkdir(parents=True, exist_ok=True)
    proof_report = {
        "report_id": "proof-canonical",
        "generated_utc": "2026-04-02T12:00:00Z",
        "scenario_count": 0,
        "benchmark_profile": "proof",
        "published_comparison": {"candidate_mode": "odylith_on", "baseline_mode": "raw_agent_baseline"},
        "published_scenarios": [],
        "published_family_summaries": {},
        "adoption_proof": {},
        "runtime_posture": {},
    }
    (benchmark_root / "latest.v1.json").write_text(json.dumps(proof_report), encoding="utf-8")

    written = graphs.render_profile_graph_assets(
        repo_root=tmp_path,
        out_dir=tmp_path / "docs" / "benchmarks",
        benchmark_profiles=("proof",),
    )

    assert set(written.keys()) == {"proof"}
    frontier = (tmp_path / "docs" / "benchmarks" / "proof" / graphs.FRONTIER_FILENAME).read_text(encoding="utf-8")
    assert "Source: " in frontier
    assert "latest.v1.json" in frontier
