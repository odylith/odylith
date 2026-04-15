from __future__ import annotations

from odylith.runtime.surfaces import tooling_dashboard_system_status_presenter as presenter


def test_render_system_status_html_renders_ablation_notice() -> None:
    html = presenter.render_system_status_html(
        {},
        odylith_switch={"enabled": False, "source": "fixture", "mode": "shadow", "note": "comparison run"},
        build_drawer_payload=lambda payload: {"status": "built"},
        render_curated_system_status_html=lambda payload: "<section>should not render</section>",
    )

    assert "odylith disabled" in html
    assert "source fixture" in html
    assert "mode shadow" in html
    assert "comparison run" in html


def test_render_system_status_html_prefers_existing_drawer_payload() -> None:
    rendered_payloads: list[dict[str, object]] = []

    def _render_curated(payload: dict[str, object]) -> str:
        rendered_payloads.append(dict(payload))
        return f"<section>{payload['headline']}</section>"

    html = presenter.render_system_status_html(
        {"odylith_drawer": {"status": "ready", "headline": "Current"}},
        odylith_switch={},
        build_drawer_payload=lambda payload: (_ for _ in ()).throw(AssertionError("existing drawer payload should not rebuild")),
        render_curated_system_status_html=_render_curated,
    )

    assert html == "<section>Current</section>"
    assert rendered_payloads == [{"status": "ready", "headline": "Current"}]


def test_render_system_status_html_suppresses_benchmark_story_strip() -> None:
    def _render_curated(payload: dict[str, object]) -> str:
        return f"<section>{payload['headline']}</section>"

    html = presenter.render_system_status_html(
        {
            "benchmark_story": {
                "show": True,
                "status": "warn",
                "headline": "Benchmark compare versus last shipped release",
                "summary": "Benchmark compare raised release warnings.",
                "metrics": [
                    {"label": "Prompt tokens", "value": "+22.0 tokens", "direction": "worse"},
                    {"label": "Validation success", "value": "+1.0 pts", "direction": "better"},
                ],
                "history": [
                    {
                        "badge": "Current",
                        "version": "v0.1.6",
                        "status": "provisional_pass",
                        "generated_utc": "2026-03-31T05:00:00Z",
                    }
                ],
            },
            "odylith_drawer": {"status": "ready", "headline": "Current"},
        },
        odylith_switch={},
        build_drawer_payload=lambda payload: (_ for _ in ()).throw(AssertionError("benchmark story should not rebuild drawer")),
        render_curated_system_status_html=_render_curated,
    )

    assert html == "<section>Current</section>"
    assert "Benchmark compare" not in html
