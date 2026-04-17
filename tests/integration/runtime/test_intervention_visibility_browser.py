from __future__ import annotations

from html import escape
import json
from pathlib import Path

from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.surfaces import host_intervention_status
from odylith.runtime.surfaces import host_visible_intervention
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _new_page,
    _wait_for_shell_query_param,
    browser_context,
    compact_browser_context,
)


def _seed_codex_repo(repo_root: Path) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo guidance\n", encoding="utf-8")
    launcher = repo_root / ".odylith" / "bin"
    launcher.mkdir(parents=True, exist_ok=True)
    (launcher / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")
    codex_root = repo_root / ".codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    (codex_root / "config.toml").write_text("[features]\ncodex_hooks = true\n", encoding="utf-8")
    (codex_root / "hooks.json").write_text(
        json.dumps(
            {
                "UserPromptSubmit": [
                    {"hooks": [{"command": "./.odylith/bin/odylith codex prompt-context --repo-root ."}]}
                ],
                "PostToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {"command": "./.odylith/bin/odylith codex post-bash-checkpoint --repo-root ."}
                        ],
                    }
                ],
                "Stop": [
                    {"hooks": [{"command": "./.odylith/bin/odylith codex stop-summary --repo-root ."}]}
                ],
            }
        ),
        encoding="utf-8",
    )


def _assert_node_has_no_horizontal_overflow(locator, *, max_slack_px: int = 4) -> None:  # noqa: ANN001
    metrics = locator.evaluate(
        """(node) => ({
          clientWidth: node.clientWidth,
          scrollWidth: node.scrollWidth,
          rectWidth: node.getBoundingClientRect().width,
        })"""
    )
    assert int(metrics["scrollWidth"]) <= int(metrics["clientWidth"]) + max_slack_px, metrics
    assert int(metrics["rectWidth"]) > 280, metrics


def _assert_atlas_viewer_image_loaded(page) -> None:  # noqa: ANN001
    page.wait_for_function(
        """() => {
          const frame = document.querySelector("#frame-atlas");
          const doc = frame && frame.contentDocument;
          const image = doc && doc.querySelector("#viewerImage");
          if (!image || !image.complete) return false;
          const rect = image.getBoundingClientRect();
          return image.naturalWidth > 0
            && image.naturalHeight > 0
            && rect.width > 120
            && rect.height > 80;
        }""",
        timeout=15000,
    )


def test_intervention_status_text_is_browser_visible_for_unproven_and_chat_confirmed(
    browser_context,
    tmp_path: Path,
) -> None:  # noqa: ANN001
    _base_url, context = browser_context
    _seed_codex_repo(tmp_path)
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Observation waiting for chat confirmation.",
        session_id="browser-session",
        host_family="codex",
        intervention_key="iv-browser",
        turn_phase="post_bash_checkpoint",
        display_markdown="---\n**Odylith Observation:** Browser status confirms this.\n---",
        delivery_channel="assistant_visible_fallback",
        delivery_status="assistant_render_required",
        render_surface="codex_post_tool_use",
    )
    unproven = host_intervention_status.render_intervention_status(
        host_intervention_status.inspect_intervention_status(
            repo_root=tmp_path,
            host_family="codex",
            session_id="browser-session",
        )
    )
    proven = host_intervention_status.render_intervention_status(
        host_intervention_status.inspect_intervention_status(
            repo_root=tmp_path,
            host_family="codex",
            session_id="browser-session",
            last_assistant_message="---\n**Odylith Observation:** Browser status confirms this.\n---",
        )
    )

    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    page.set_content(
        "<!doctype html><html><body>"
        f"<section id='unproven'><pre>{escape(unproven)}</pre></section>"
        f"<section id='proven'><pre>{escape(proven)}</pre></section>"
        "</body></html>",
        wait_until="domcontentloaded",
    )

    page.locator("#unproven", has_text="Chat-visible proof: pending_confirmation").wait_for(timeout=15000)
    page.locator("#unproven", has_text="still require exact chat confirmation").wait_for(timeout=15000)
    page.locator("#proven", has_text="Chat-visible proof: proven_this_session").wait_for(timeout=15000)
    page.locator("#proven", has_text="assistant_chat_transcript").wait_for(timeout=15000)
    page.locator("#proven", has_text="Chat transcript confirmations recorded on this probe: 1").wait_for(
        timeout=15000
    )
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_intervention_status_browser_distinguishes_proven_session_with_pending_hidden_beat(
    browser_context,
    tmp_path: Path,
) -> None:  # noqa: ANN001
    _base_url, context = browser_context
    _seed_codex_repo(tmp_path)
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Earlier visible Observation.",
        session_id="browser-pending-session",
        host_family="codex",
        intervention_key="iv-browser-visible",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Earlier browser-visible proof.",
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface="codex_visible_intervention",
    )
    stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Later hidden Observation.",
        session_id="browser-pending-session",
        host_family="codex",
        intervention_key="iv-browser-hidden",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Later hidden proof still needs chat.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_post_tool_use",
    )
    rendered = host_intervention_status.render_intervention_status(
        host_intervention_status.inspect_intervention_status(
            repo_root=tmp_path,
            host_family="codex",
            session_id="browser-pending-session",
        )
    )

    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    page.set_content(
        "<!doctype html><html><body>"
        f"<section id='pending'><pre>{escape(rendered)}</pre></section>"
        "</body></html>",
        wait_until="domcontentloaded",
    )

    page.locator("#pending", has_text="Chat-visible proof: proven_with_pending_confirmation").wait_for(
        timeout=15000
    )
    page.locator("#pending", has_text="pending chat-confirmation event(s)").wait_for(timeout=15000)
    page.locator("#pending", has_text="assistant_fallback_ready").wait_for(timeout=15000)
    page.locator("#pending", has_text="Ledger: 2 recent event(s), 1 proven-visible event(s), 1 pending").wait_for(
        timeout=15000
    )
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_visible_intervention_fallback_markdown_is_transcript_visible_in_compact_browser(
    compact_browser_context,
    tmp_path: Path,
) -> None:  # noqa: ANN001
    _base_url, context = compact_browser_context
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        session_id="compact-visible-session",
        prompt="ZERO ambient highlights, ZERO intervention blocks, and ZERO Assist visible in my chat.",
    )

    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    page.set_content(
        "<!doctype html><html><head><style>"
        "body{margin:0;font-family:Arial,sans-serif;background:#fff;color:#111827;}"
        ".chat{width:min(100vw,430px);padding:12px;}"
        ".message{border:1px solid #d1d5db;border-radius:8px;padding:10px;white-space:pre-wrap;overflow-wrap:anywhere;}"
        "</style></head><body>"
        f"<main class='chat'><article id='assistant-message' class='message'>{escape(rendered)}</article></main>"
        "</body></html>",
        wait_until="domcontentloaded",
    )

    message = page.locator("#assistant-message")
    message.wait_for(timeout=15000)
    message.locator("text=Odylith Observation").wait_for(timeout=15000)
    message.locator("text=visibility failure, not a quiet moment").wait_for(timeout=15000)
    rendered_text = message.inner_text().strip()
    assert rendered_text.startswith("---\n\n**Odylith Observation:**")
    assert not rendered_text.lstrip().startswith("{")
    assert "assistant has to show the Odylith Markdown directly" in rendered_text
    _assert_node_has_no_horizontal_overflow(message)
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_d038_atlas_visibility_broker_flow_renders_in_shell(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(
        base_url + "/odylith/index.html?tab=atlas&diagram=D-038",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text="D-038").wait_for(timeout=15000)
    atlas.locator("#diagramTitle", has_text="Conversation Observation And Governed Proposal Flow").wait_for(
        timeout=15000
    )
    _wait_for_shell_query_param(page, tab="atlas", key="diagram", value="D-038")
    _assert_atlas_viewer_image_loaded(page)

    visible_summary = atlas.locator("#diagramSummary").inner_text()
    visible_components = atlas.locator("#componentList").inner_text().lower()
    registry_links = atlas.locator("#registryLinks").inner_text().lower()

    assert "proposition ledger" in visible_summary.lower()
    assert "conflict graph" in visible_summary.lower()
    assert "subset optimizer" in visible_summary.lower()
    assert "bootstrap adjudication report" in visible_summary.lower()
    assert "odylith risks, history, insight, observation, proposal, or assist" in visible_summary.lower()
    assert "governance-intervention-engine" in visible_components
    assert "execution-engine" in visible_components
    assert "governance-intervention-engine" in registry_links
    assert "execution-engine" in registry_links
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
