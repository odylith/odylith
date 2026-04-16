from __future__ import annotations

import datetime as dt
import gzip
import json
import re
import shutil
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from odylith.runtime.governance import sync_casebook_bug_index
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_standup_brief_maintenance
from odylith.runtime.surfaces import compass_transaction_runtime
from odylith.runtime.surfaces import render_casebook_dashboard
from odylith.runtime.surfaces import render_compass_dashboard
from odylith.runtime.surfaces import render_mermaid_catalog
from odylith.runtime.surfaces import render_tooling_dashboard as tooling_dashboard_renderer
from tests.integration.runtime.surface_browser_test_support import (
    _REPO_ROOT,
    _assert_clean_page,
    _assert_compass_live_state,
    _browser,
    _static_server,
    _atlas_total,
    _click_visible,
    _compass_brief_metadata,
    _new_page,
    _select_radar_row_with_link,
    _wait_for_compass_brief_state,
    _wait_for_shell_query_param,
    _wait_for_shell_tab,
    browser_context,
    compact_browser_context,
)


class _CompassProvider:
    _PATH_LIKE_RE = re.compile(r"`?(?:\.?/)?(?:\.odylith|odylith|src|tests|docs|skills|agents-guidelines)/[A-Za-z0-9._/\-]+`?")

    def __init__(self) -> None:
        self.calls = 0

    @staticmethod
    def _facts(section: dict[str, object]) -> list[dict[str, object]]:
        facts = section.get("facts")
        if not isinstance(facts, list):
            return []
        return [fact for fact in facts if isinstance(fact, dict) and str(fact.get("id", "")).strip()]

    @staticmethod
    def _fact_id(fact: dict[str, object] | None) -> str:
        return str((fact or {}).get("id", "")).strip()

    @classmethod
    def _pick_fact(cls, section: dict[str, object], *, preferred_kinds: tuple[str, ...]) -> dict[str, object] | None:
        facts = cls._facts(section)
        for fact in facts:
            if str(fact.get("kind", "")).strip().lower() in preferred_kinds:
                return fact
        return facts[0] if facts else None

    @classmethod
    def _trim_words(cls, text: str, *, limit: int) -> str:
        words = str(text or "").split()
        if len(words) <= limit:
            return " ".join(words)
        trimmed = " ".join(words[:limit]).rstrip(",;:")
        return trimmed

    @classmethod
    def _brief_text(cls, raw_text: str, *, mode: str) -> str:
        text = str(raw_text or "").strip()
        if not text:
            return ""
        for prefix in (
            "Primary execution signal:",
            "Timeline signal:",
            "Timeline signal on the primary lane:",
            "Concrete movement in the repo:",
            "Concrete proof in the repo:",
            "Most concrete movement:",
            "Most concrete portfolio movement:",
            "Plan posture:",
            "Risk posture:",
        ):
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
        if mode == "direction" and " because " in text:
            _prefix, reason = text.split(" because ", 1)
            text = reason.strip()
        if mode == "impact" and text.lower().startswith("for ") and "," in text:
            _prefix, text = text.split(",", 1)
            text = text.strip()
        if mode == "leverage" and text.lower().startswith("the architecture move is to"):
            text = text[len("The architecture move is to") :].strip()
        if text.lower().startswith("immediate forcing function is"):
            text = text[len("Immediate forcing function is"):].strip()
        if text.lower().startswith("then move"):
            text = text[len("Then move") :].strip()
        if mode == "next" and ":" in text:
            _label, text = text.split(":", 1)
            text = text.strip()
        if mode == "risk" and text.lower().startswith("primary blocker is an open p1 bug:"):
            text = text[len("Primary blocker is an open P1 bug:") :].strip()
        if mode == "risk" and text.lower().startswith("primary watch item is"):
            text = text[len("Primary watch item is") :].strip()
        if mode == "freshness" and ":" in text and text.lower().startswith("freshness signal is"):
            _prefix, text = text.split(":", 1)
            text = text.strip()
        if ", which " in text:
            text = text.split(", which ", 1)[0].strip()
        if "; " in text:
            text = text.split(";", 1)[0].strip()
        text = cls._PATH_LIKE_RE.sub("the local runtime", text)
        text = re.sub(r"`?\./\.odylith/bin/odylith`?", "the launcher", text)
        if text.lower().startswith("to "):
            text = text[3:].strip()
        text = cls._trim_words(text, limit=26 if mode in {"direction", "impact"} else 20)
        text = " ".join(text.split()).strip(" .,:;")
        if text:
            text = text[:1].upper() + text[1:]
        if text and text[-1] not in ".!?":
            text = f"{text}."
        return text

    def generate_structured(self, *, request):  # noqa: ANN001
        self.calls += 1
        prompt_payload = request.prompt_payload if isinstance(request.prompt_payload, dict) else {}
        bundle_entries = prompt_payload.get("entries")
        if str(prompt_payload.get("bundle_mode", "")).strip().lower() == "delta_substrate_update" and isinstance(
            bundle_entries, list
        ):
            briefs = []
            for item in bundle_entries:
                if not isinstance(item, dict):
                    continue
                entry_kind = str(item.get("entry_kind", "")).strip().lower()
                window_key = str(item.get("window_key", "")).strip()
                if entry_kind not in {"global", "scoped"} or not window_key:
                    continue
                current = item.get("current") if isinstance(item.get("current"), dict) else {}
                previous = item.get("previous_accepted") if isinstance(item.get("previous_accepted"), dict) else {}
                sections = (
                    previous.get("sections")
                    if isinstance(previous.get("sections"), list)
                    else self._bundle_sections_for_entry(
                        entry=item,
                        current=current,
                    )
                )
                brief = {
                    "entry_kind": entry_kind,
                    "window_key": window_key,
                    "sections": sections,
                }
                if entry_kind == "scoped":
                    scope_id = str(item.get("scope_id", "")).strip()
                    if not scope_id:
                        continue
                    brief["scope_id"] = scope_id
                briefs.append(brief)
            return {"briefs": briefs}
        scoped_fact_packets = prompt_payload.get("scoped_fact_packets")
        if isinstance(scoped_fact_packets, list):
            return {
                "briefs": [
                    {
                        "scope_id": str(item.get("scope_id", "")).strip(),
                        "sections": self._sections_for_fact_packet(
                            item.get("fact_packet") if isinstance(item.get("fact_packet"), dict) else {}
                        ),
                    }
                    for item in scoped_fact_packets
                    if isinstance(item, dict) and str(item.get("scope_id", "")).strip()
                ]
            }
        window_fact_packets = prompt_payload.get("window_fact_packets")
        if isinstance(window_fact_packets, list):
            return {
                "briefs": [
                    {
                        "window_key": str(item.get("window_key", "")).strip(),
                        "sections": self._sections_for_fact_packet(
                            item.get("fact_packet") if isinstance(item.get("fact_packet"), dict) else {}
                        ),
                    }
                    for item in window_fact_packets
                    if isinstance(item, dict) and str(item.get("window_key", "")).strip()
                ]
            }
        fact_packet = prompt_payload.get("fact_packet") if isinstance(prompt_payload.get("fact_packet"), dict) else {}
        return {"sections": self._sections_for_fact_packet(fact_packet)}

    def _bundle_sections_for_entry(
        self,
        *,
        entry: dict[str, object],
        current: dict[str, object],
    ) -> list[dict[str, object]]:
        sections = current.get("sections") if isinstance(current.get("sections"), list) else []
        section_map = {
            str(section.get("key", "")).strip(): section
            for section in sections
            if isinstance(section, dict) and str(section.get("key", "")).strip()
        }
        summary = current.get("summary") if isinstance(current.get("summary"), dict) else {}
        freshness_bucket = str(summary.get("freshness_bucket", "")).strip().lower()

        completed_fact = self._pick_fact(
            section_map.get("completed", {}),
            preferred_kinds=("plan_completion", "execution_highlight", "window_summary"),
        )
        direction_fact = self._pick_fact(section_map.get("current_execution", {}), preferred_kinds=("direction",))
        freshness_fact = self._pick_fact(section_map.get("current_execution", {}), preferred_kinds=("freshness",))
        forcing_fact = self._pick_fact(
            section_map.get("next_planned", {}),
            preferred_kinds=("forcing_function", "fallback_next"),
        )
        follow_on_fact = self._pick_fact(section_map.get("next_planned", {}), preferred_kinds=("follow_on",))
        risk_fact = self._pick_fact(
            section_map.get("risks_to_watch", {}),
            preferred_kinds=("risk_posture", "bug", "self_host_posture"),
        )

        current_bullets: list[dict[str, object]] = []
        if direction_fact is not None:
            current_bullets.append(
                {
                    "text": self._brief_text(str(direction_fact.get("text", "")), mode="direction"),
                    "fact_ids": [self._fact_id(direction_fact)],
                }
            )
        if freshness_bucket in {"aging", "stale"} and freshness_fact is not None:
            current_bullets.append(
                {
                    "text": self._brief_text(str(freshness_fact.get("text", "")), mode="freshness"),
                    "fact_ids": [self._fact_id(freshness_fact)],
                }
            )
        if completed_fact is not None and direction_fact is not None and forcing_fact is not None and risk_fact is not None:
            return [
                {
                    "key": "completed",
                    "label": "Completed in this window",
                    "bullets": [
                        {
                            "text": self._brief_text(str(completed_fact.get("text", "")), mode="completed"),
                            "fact_ids": [self._fact_id(completed_fact)],
                        }
                    ],
                },
                {
                    "key": "current_execution",
                    "label": "Current execution",
                    "bullets": current_bullets,
                },
                {
                    "key": "next_planned",
                    "label": "Next planned",
                    "bullets": [
                        {
                            "text": self._brief_text(str(forcing_fact.get("text", "")), mode="next"),
                            "fact_ids": [self._fact_id(forcing_fact)],
                        },
                        *(
                            [
                                {
                                    "text": self._brief_text(str(follow_on_fact.get("text", "")), mode="next"),
                                    "fact_ids": [self._fact_id(follow_on_fact)],
                                }
                            ]
                            if follow_on_fact is not None and self._fact_id(follow_on_fact) != self._fact_id(forcing_fact)
                            else []
                        ),
                    ],
                },
                {
                    "key": "risks_to_watch",
                    "label": "Risks to watch",
                    "bullets": [
                        {
                            "text": self._brief_text(str(risk_fact.get("text", "")), mode="risk"),
                            "fact_ids": [self._fact_id(risk_fact)],
                        }
                    ],
                },
            ]
        return [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [{"text": "Maintained narration is ready for this view.", "fact_ids": ["F-001"]}],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "bullets": [{"text": "Compass is warming the brief from the current narration substrate.", "fact_ids": ["F-004"]}],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "bullets": [{"text": "Reuse the maintained brief bundle instead of rebuilding the same narration again.", "fact_ids": ["F-009"]}],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "bullets": [{"text": "No extra blocker is injected into this maintained test harness response.", "fact_ids": ["F-011"]}],
            },
        ]

    def _sections_for_fact_packet(self, fact_packet: dict[str, object]) -> list[dict[str, object]]:
        sections = fact_packet.get("sections") if isinstance(fact_packet.get("sections"), list) else []
        section_map = {
            str(section.get("key", "")).strip(): section
            for section in sections
            if isinstance(section, dict) and str(section.get("key", "")).strip()
        }
        summary = fact_packet.get("summary") if isinstance(fact_packet.get("summary"), dict) else {}
        freshness = summary.get("freshness") if isinstance(summary, dict) and isinstance(summary.get("freshness"), dict) else {}
        freshness_bucket = str(freshness.get("bucket", "")).strip().lower()

        completed_fact = self._pick_fact(
            section_map.get("completed", {}),
            preferred_kinds=("plan_completion", "execution_highlight", "window_summary"),
        )
        direction_fact = self._pick_fact(section_map.get("current_execution", {}), preferred_kinds=("direction",))
        freshness_fact = self._pick_fact(section_map.get("current_execution", {}), preferred_kinds=("freshness",))
        secondary_fact = self._pick_fact(
            section_map.get("current_execution", {}),
            preferred_kinds=("signal", "self_host_status", "portfolio_posture", "timeline", "checklist"),
        )
        forcing_fact = self._pick_fact(
            section_map.get("next_planned", {}),
            preferred_kinds=("forcing_function", "fallback_next"),
        )
        follow_on_fact = self._pick_fact(section_map.get("next_planned", {}), preferred_kinds=("follow_on",))
        risk_fact = self._pick_fact(
            section_map.get("risks_to_watch", {}),
            preferred_kinds=("risk_posture", "bug", "self_host_posture"),
        )

        current_bullets: list[dict[str, object]] = []
        if direction_fact is not None:
            current_bullets.append(
                {
                    "text": self._brief_text(str(direction_fact.get("text", "")), mode="direction"),
                    "fact_ids": [self._fact_id(direction_fact)],
                }
            )
        if freshness_bucket in {"aging", "stale"} and freshness_fact is not None:
            current_bullets.append(
                {
                    "text": self._brief_text(str(freshness_fact.get("text", "")), mode="freshness"),
                    "fact_ids": [self._fact_id(freshness_fact)],
                }
            )
        elif secondary_fact is not None:
            current_bullets.append(
                {
                    "text": self._brief_text(str(secondary_fact.get("text", "")), mode="signal"),
                    "fact_ids": [self._fact_id(secondary_fact)],
                }
            )

        return [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [
                    {
                        "text": self._brief_text(
                            str((completed_fact or {}).get("text", "")) or "Verified movement landed in this window.",
                            mode="completed",
                        ),
                        "fact_ids": [self._fact_id(completed_fact)],
                    }
                ],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "bullets": current_bullets,
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "bullets": [
                    {
                        "text": self._brief_text(
                            str((forcing_fact or {}).get("text", "")) or "The next checkpoint is ready.",
                            mode="next",
                        ),
                        "fact_ids": [self._fact_id(forcing_fact)],
                    },
                    *(
                        [
                            {
                                "text": self._brief_text(str(follow_on_fact.get("text", "")), mode="next"),
                                "fact_ids": [self._fact_id(follow_on_fact)],
                            }
                        ]
                        if follow_on_fact is not None and self._fact_id(follow_on_fact) != self._fact_id(forcing_fact)
                        else []
                    ),
                ],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "bullets": [
                    {
                        "text": self._brief_text(
                            str((risk_fact or {}).get("text", "")) or "No blocking Compass risk is surfaced in this synthetic proof run.",
                            mode="risk",
                        ),
                        "fact_ids": [self._fact_id(risk_fact)],
                    }
                ],
            },
        ]

    def generate_finding(self, *, prompt_payload):  # noqa: ANN001, ARG002
        raise AssertionError("Compass browser proof should use structured generation only.")


def _write_fixture_current_release_assignments(fixture_root, *workstream_ids: str) -> None:  # noqa: ANN001
    releases_root = fixture_root / "odylith" / "radar" / "source" / "releases"
    releases_root.mkdir(parents=True, exist_ok=True)
    events_path = releases_root / "release-assignment-events.v1.jsonl"
    rows = [
        {
            "action": "add",
            "release_id": "release-0-1-11",
            "workstream_id": workstream_id,
            "recorded_at": f"2026-04-09T00:00:0{index}Z",
        }
        for index, workstream_id in enumerate(workstream_ids)
    ]
    events_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _rewrite_fixture_workstream_status(fixture_root, *, idea_id: str, status: str) -> None:  # noqa: ANN001
    ideas_root = fixture_root / "odylith" / "radar" / "source" / "ideas"
    for path in ideas_root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if f"idea_id: {idea_id}" not in text:
            continue
        path.write_text(
            text.replace("status: finished", f"status: {status}", 1),
            encoding="utf-8",
        )
        return
    raise AssertionError(f"missing idea fixture for {idea_id}")


def _pane_hidden(page, frame_selector: str) -> bool:  # noqa: ANN001
    return bool(page.locator(frame_selector).evaluate("node => Boolean(node.hidden)"))


def _assert_single_visible_pane(page, active_frame_selector: str) -> None:  # noqa: ANN001
    panes = (
        "#frame-radar",
        "#frame-registry",
        "#frame-casebook",
        "#frame-atlas",
        "#frame-compass",
    )
    visible = [selector for selector in panes if not _pane_hidden(page, selector)]
    assert visible == [active_frame_selector]


def _render_tooling_shell_fixture(fixture_root) -> None:  # noqa: ANN001
    rc = tooling_dashboard_renderer.main(["--repo-root", str(fixture_root), "--output", "odylith/index.html"])
    assert rc == 0


def _first_non_default_option(frame, selector: str, excluded: set[str] | None = None) -> str:  # noqa: ANN001
    excluded_tokens = {"all", ""}
    if excluded:
        excluded_tokens |= {str(token) for token in excluded}
    options = frame.locator(f"{selector} option").evaluate_all(
        """nodes => nodes
          .map((node) => (node.value || "").trim())
          .filter((token) => token.length > 0)
        """
    )
    for token in options:
        if token not in excluded_tokens:
            return str(token)
    return ""


def _first_scope_option_with_scoped_brief(frame, *, window_token: str) -> str:  # noqa: ANN001
    options = frame.locator("#scope-select option").evaluate_all(
        """nodes => nodes
          .map((node) => (node.value || "").trim())
          .filter((token) => /^B-\\d{3,}$/.test(token))
        """
    )
    option_set = {str(token) for token in options}
    runtime_path = _REPO_ROOT / "odylith" / "compass" / "runtime" / "current.v1.json"
    payload = json.loads(runtime_path.read_text(encoding="utf-8"))
    scoped = payload.get("standup_brief_scoped") if isinstance(payload.get("standup_brief_scoped"), dict) else {}
    window_scoped = scoped.get(window_token) if isinstance(scoped.get(window_token), dict) else {}
    for scope_id, brief in window_scoped.items():
        if str(scope_id) in option_set and isinstance(brief, dict) and str(brief.get("fingerprint", "")).strip():
            return str(scope_id)
    return _first_non_default_option(frame, "#scope-select", excluded={""})


def _first_filter_value_with_results(frame, selector: str, item_selector: str) -> tuple[str, int]:  # noqa: ANN001
    options = frame.locator(f"{selector} option").evaluate_all(
        """nodes => nodes
          .map((node) => (node.value || "").trim())
          .filter((token) => token.length > 0 && token !== "all")
        """
    )
    for token in options:
        frame.locator(selector).select_option(token)
        count = frame.locator(item_selector).count()
        if count > 0:
            return str(token), count
    return "", 0


def _reset_select_to_first_option(frame, selector: str) -> None:  # noqa: ANN001
    values = frame.locator(f"{selector} option").evaluate_all(
        """nodes => nodes
          .map((node) => (node.value || ""))
        """
    )
    assert values, f"expected at least one option for {selector}"
    frame.locator(selector).select_option(str(values[0]))


def _select_registry_component_with_detail_actions(registry) -> tuple[str, str]:  # noqa: ANN001
    buttons = registry.locator("button[data-component]")
    count = buttons.count()
    for index in range(count):
        button = buttons.nth(index)
        component_id = str(button.get_attribute("data-component") or "").strip()
        if not component_id:
            continue
        button.click()
        registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)
        registry.locator("#detail .component-name").wait_for(timeout=15000)
        if registry.locator("#detail a.detail-action-chip").count():
            component_name = registry.locator("#detail .component-name").inner_text().strip()
            return component_id, component_name
    raise AssertionError("expected at least one Registry component with detail action chips")


def _select_radar_row_with_cross_surface_links(radar) -> str:  # noqa: ANN001
    row_buttons = radar.locator("button[data-idea-id]")
    count = row_buttons.count()
    for index in range(count):
        button = row_buttons.nth(index)
        idea_id = str(button.get_attribute("data-idea-id") or "").strip()
        if not idea_id:
            continue
        button.click()
        _wait_for_radar_detail_id(radar, idea_id)
        registry_links = radar.locator("#detail a.chip-registry-component")
        diagram_links = radar.locator("#detail a.chip-topology-diagram")
        if registry_links.count() and diagram_links.count():
            return idea_id
    raise AssertionError("expected a Radar workstream with both Registry and Atlas detail links")


def _reset_radar_filters(radar) -> None:  # noqa: ANN001
    radar.locator("#query").fill("")
    for selector in ("#section", "#phase", "#activity", "#lane", "#priority"):
        radar.locator(selector).select_option("all")


def _select_radar_workstream(radar, idea_id: str) -> None:  # noqa: ANN001
    _reset_radar_filters(radar)
    radar.locator("#query").fill(idea_id)
    radar.locator(f'button[data-idea-id="{idea_id}"]').wait_for(timeout=15000)
    radar.locator(f'button[data-idea-id="{idea_id}"]').first.click()
    _wait_for_radar_detail_id(radar, idea_id)
    radar.locator("#query").fill("")
    _wait_for_radar_detail_id(radar, idea_id)


def _wait_for_radar_detail_id(radar, idea_id: str) -> None:  # noqa: ANN001
    radar.locator(f'button[data-idea-id="{idea_id}"].active').wait_for(timeout=15000)
    radar.locator("#detail .detail-title").wait_for(timeout=15000)
    radar.locator("#detail").filter(has_text=idea_id).wait_for(timeout=15000)


def _open_radar_topology_relations(radar) -> None:  # noqa: ANN001
    panel = radar.locator("#detail details.topology-relations-panel").first
    panel.wait_for(timeout=15000)
    if panel.get_attribute("open") is None:
        panel.evaluate("node => { node.open = true; }")
    panel.locator(".topology-relations").wait_for(timeout=15000)


def _wait_for_locator_count(page, frame_selector: str, locator_selector: str, expected: int) -> None:  # noqa: ANN001
    page.wait_for_function(
        """({ frameSelector, locatorSelector, expected }) => {
            const frame = document.querySelector(frameSelector);
            const doc = frame && frame.contentDocument;
            if (!doc) return false;
            return doc.querySelectorAll(locatorSelector).length === expected;
        }""",
        arg={"frameSelector": frame_selector, "locatorSelector": locator_selector, "expected": expected},
        timeout=15000,
    )


def test_shell_tab_matrix_keeps_single_visible_pane_in_compact_viewport(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
    assert response is not None and response.ok

    expectations = (
        ("radar", "#tab-radar", "#frame-radar", "Backlog Workstream Radar", "radar/radar.html"),
        ("registry", "#tab-registry", "#frame-registry", "Component Registry", "registry/registry.html"),
        ("casebook", "#tab-casebook", "#frame-casebook", "Casebook", "casebook/casebook.html"),
        ("atlas", "#tab-atlas", "#frame-atlas", "Atlas", "atlas/atlas.html"),
        ("compass", "#tab-compass", "#frame-compass", "Executive Compass", "compass/compass.html"),
    )

    for tab, tab_selector, frame_selector, heading_text, route_fragment in expectations:
        _click_visible(page.locator(tab_selector))
        _wait_for_shell_tab(page, tab)
        assert page.locator(tab_selector).get_attribute("aria-selected") == "true"
        _assert_single_visible_pane(page, frame_selector)
        page.frame_locator(frame_selector).locator("h1", has_text=heading_text).wait_for(timeout=15000)
        src = str(page.locator(frame_selector).get_attribute("src") or "")
        assert route_fragment in src

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shell_runtime_status_stays_hidden_across_tab_switches(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok

    page.frame_locator("#frame-atlas").locator("h1", has_text="Atlas").wait_for(timeout=15000)
    page.wait_for_function(
        """() => {
            const status = document.querySelector("#shellRuntimeStatus");
            return Boolean(status && status.hidden);
        }""",
        timeout=20000,
    )
    assert page.evaluate(
        """() => getComputedStyle(document.querySelector(".viewport"))
            .getPropertyValue("--runtime-status-offset")
            .trim()"""
    ) == "0px"

    page.locator("#tab-registry").click()
    page.frame_locator("#frame-registry").locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    page.wait_for_function(
        """() => {
            const status = document.querySelector("#shellRuntimeStatus");
            return Boolean(status && status.hidden);
        }""",
        timeout=10000,
    )
    assert page.evaluate(
        """() => getComputedStyle(document.querySelector(".viewport"))
            .getPropertyValue("--runtime-status-offset")
            .trim()"""
    ) == "0px"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shell_compass_tab_dedupes_stale_runtime_status_to_compass_notice(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    payload["generated_utc"] = "2020-01-02T17:06:12Z"
    payload["now_local_iso"] = "2020-01-02T09:06:12-08:00"
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    _render_tooling_shell_fixture(fixture_root)

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
                assert response is not None and response.ok

                assert page.locator("#runtimeStatusReopen").count() == 0
                page.wait_for_function(
                    """() => {
                        const status = document.querySelector("#shellRuntimeStatus");
                        return Boolean(status && status.hidden && status.getAttribute("aria-hidden") === "true");
                    }""",
                    timeout=15000,
                )

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                page.wait_for_function(
                    """() => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const banner = doc && doc.querySelector("#status-banner");
                        return Boolean(
                          banner
                          && !banner.classList.contains("hidden")
                          && (banner.textContent || "").includes("Compass snapshot")
                        );
                    }""",
                    timeout=15000,
                )
                assert "ask agent `Refresh Compass runtime for this repo.`" in compass.locator("#status-banner").inner_text()

                page.locator("#tab-radar").click()
                _wait_for_shell_tab(page, "radar")
                page.wait_for_function(
                    """() => {
                        const node = document.querySelector("#shellRuntimeStatus");
                        return Boolean(node && node.hidden);
                    }""",
                    timeout=15000,
                )

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_shell_compass_tab_surfaces_failed_full_refresh_warning(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    payload["generated_utc"] = "2026-04-07T17:06:12Z"
    payload["warning"] = (
        "Requested Compass refresh did not finish before the refresh timeout. "
        "Showing the last successful shell-safe runtime snapshot from 2026-04-07T17:06:12Z."
    )
    runtime_contract = dict(payload.get("runtime_contract") or {})
    runtime_contract["refresh_profile"] = "shell-safe"
    runtime_contract["last_refresh_attempt"] = {
        "status": "failed",
        "requested_profile": "shell-safe",
        "applied_profile": "shell-safe",
        "attempted_utc": "2026-04-07T17:17:57Z",
        "reason": "timeout",
        "runtime_mode": "auto",
        "fallback_used": True,
    }
    payload["runtime_contract"] = runtime_contract
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    _render_tooling_shell_fixture(fixture_root)

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
                assert response is not None and response.ok

                page.wait_for_function(
                    """() => {
                        const node = document.querySelector("#shellRuntimeStatus");
                        return Boolean(node && node.hidden && node.getAttribute("aria-hidden") === "true");
                    }""",
                    timeout=15000,
                )

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#status-banner").wait_for(timeout=15000)
                assert compass.locator("#status-banner").evaluate(
                    "(node) => !node.classList.contains('hidden')"
                )
                banner_text = compass.locator("#status-banner").inner_text().strip()
                assert "Requested Compass refresh did not finish before the refresh timeout." in banner_text
                assert "Showing the last successful shell-safe runtime snapshot" in banner_text

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_registry_search_filters_reset_and_detail_actions(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
    assert response is not None and response.ok

    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    baseline_count = registry.locator("button[data-component]").count()
    assert baseline_count > 1

    component_id, component_name = _select_registry_component_with_detail_actions(registry)
    _wait_for_shell_query_param(page, tab="registry", key="component", value=component_id)
    assert component_name
    assert registry.locator("#detail a.detail-action-chip").count() > 0

    registry.locator("#search").fill(component_id.lower())
    _wait_for_locator_count(page, "#frame-registry", "button[data-component]", 1)
    registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)
    assert registry.locator("#detail .component-name").inner_text().strip() == component_name

    registry.locator("#resetFilters").click()
    page.wait_for_function(
        """(frameSelector) => {
            const frame = document.querySelector(frameSelector);
            const doc = frame && frame.contentDocument;
            const search = doc && doc.querySelector("#search");
            return Boolean(doc) && search && search.value === "";
        }""",
        arg="#frame-registry",
        timeout=15000,
    )
    reset_count = registry.locator("button[data-component]").count()
    assert reset_count == baseline_count

    qualification_value = _first_non_default_option(registry, "#qualificationFilter")
    if not qualification_value:
        pytest.skip("Registry fixture does not currently expose non-default qualification filters.")
    registry.locator("#qualificationFilter").select_option(qualification_value)
    qualification_count = registry.locator("button[data-component]").count()
    assert 0 < qualification_count <= baseline_count

    registry.locator("#resetFilters").click()
    category_value = _first_non_default_option(registry, "#categoryFilter")
    if not category_value:
        pytest.skip("Registry fixture does not currently expose non-default category filters.")
    registry.locator("#categoryFilter").select_option(category_value)
    category_count = registry.locator("button[data-component]").count()
    assert 0 < category_count <= baseline_count

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_registry_memory_substrate_deep_links_select_the_right_component_detail(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    registry = page.frame_locator("#frame-registry")
    memory_components = (
        ("odylith-projection-bundle", "Odylith Projection Bundle"),
        ("odylith-projection-snapshot", "Odylith Projection Snapshot"),
        ("odylith-memory-backend", "Odylith Memory Backend"),
        ("odylith-remote-retrieval", "Odylith Remote Retrieval"),
        ("odylith-memory-contracts", "Odylith Memory Contracts"),
    )

    for component_id, component_name in memory_components:
        response = page.goto(
            base_url + f"/odylith/index.html?tab=registry&component={component_id}",
            wait_until="domcontentloaded",
        )
        assert response is not None and response.ok
        registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
        _wait_for_shell_query_param(page, tab="registry", key="component", value=component_id)
        registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)
        registry.locator("#detail .component-name", has_text=component_name).wait_for(timeout=15000)
        assert registry.locator("#detail a.detail-action-chip").count() > 0

    registry.locator("#search").fill("memory")
    filtered_components = {
        str(component_id)
        for component_id in registry.locator("button[data-component]").evaluate_all(
            """nodes => nodes
              .map((node) => String(node.getAttribute("data-component") || "").trim())
              .filter(Boolean)
            """
        )
    }
    assert {
        "odylith-projection-bundle",
        "odylith-projection-snapshot",
        "odylith-memory-backend",
        "odylith-remote-retrieval",
        "odylith-memory-contracts",
    }.issubset(filtered_components)

    registry.locator("#search").fill("remote retrieval")
    registry.locator('button[data-component="odylith-remote-retrieval"]').wait_for(timeout=15000)
    assert registry.locator("button[data-component]").count() == 1
    registry.locator('button[data-component="odylith-remote-retrieval"]').click()
    _wait_for_shell_query_param(page, tab="registry", key="component", value="odylith-remote-retrieval")
    registry.locator("#detail .component-name", has_text="Odylith Remote Retrieval").wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_search_selection_and_cross_surface_detail_links(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    baseline_count = radar.locator("button[data-idea-id]").count()
    assert baseline_count > 1

    idea_id = _select_radar_row_with_cross_surface_links(radar)
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=idea_id)
    radar.locator("#detail .detail-title").wait_for(timeout=15000)
    assert radar.locator("#detail a.chip-registry-component").count() > 0
    assert radar.locator("#detail a.chip-topology-diagram").count() > 0

    radar.locator("#query").fill(idea_id)
    _wait_for_locator_count(page, "#frame-radar", "button[data-idea-id]", 1)
    _wait_for_radar_detail_id(radar, idea_id)

    radar.locator("#query").fill("")
    phase_value, phase_count = _first_filter_value_with_results(radar, "#phase", "button[data-idea-id]")
    if not phase_value:
        pytest.skip("Radar fixture does not currently expose non-default phase filters with results.")
    assert 0 < phase_count <= baseline_count

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_topology_relation_chips_route_to_their_own_workstream_ids(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    source_id = "B-048"
    _select_radar_workstream(radar, source_id)
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=source_id)
    _open_radar_topology_relations(radar)
    relation_ids = [
        str(token)
        for token in radar.locator("#detail").evaluate(
            """(node) => Array.from(
                new Set(
                  Array.from(node.querySelectorAll('details.topology-relations-panel .topology-relations [data-link-idea]'))
                    .map((chip) => String(chip.getAttribute('data-link-idea') || '').trim())
                    .filter(Boolean)
                )
            )"""
        )
    ]
    if not relation_ids:
        pytest.skip("Radar fixture does not currently expose B-048 relation chips.")

    for target_id in relation_ids:
        _select_radar_workstream(radar, source_id)
        _wait_for_shell_query_param(page, tab="radar", key="workstream", value=source_id)
        _open_radar_topology_relations(radar)
        chip = radar.locator(f'#detail [data-link-idea="{target_id}"]').first
        chip.wait_for(timeout=15000)
        chip.evaluate("node => node.click()")
        _wait_for_radar_detail_id(radar, target_id)
        radar.locator(f'button[data-idea-id="{target_id}"].active').wait_for(timeout=15000)
        _wait_for_shell_query_param(page, tab="radar", key="workstream", value=target_id)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_topology_relation_clicks_self_heal_incompatible_filters(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    source_id = "B-048"
    source_section = "execution"
    _select_radar_workstream(radar, source_id)
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=source_id)
    _open_radar_topology_relations(radar)
    target_id = str(
        radar.locator("#detail").evaluate(
            """(node) => {
                const rows = Array.from(node.querySelectorAll('details.topology-relations-panel .topology-rel-row'));
                const childrenRow = rows.find(
                  (row) => String(row.querySelector('.topology-rel-title')?.textContent || '').trim().toLowerCase() === 'children'
                );
                const chip = childrenRow?.querySelector('[data-link-idea]');
                return chip ? String(chip.getAttribute('data-link-idea') || '').trim() : '';
            }"""
        )
        or ""
    ).strip()
    if not target_id:
        pytest.skip("Radar fixture does not currently expose a B-048 child relation chip.")

    radar.locator("#section").select_option(source_section)
    radar.locator("#query").fill(source_id)
    _open_radar_topology_relations(radar)
    radar.locator(f'#detail [data-link-idea="{target_id}"]').first.wait_for(timeout=15000)
    assert radar.locator(f'button[data-idea-id="{target_id}"]').count() == 0

    radar.locator(f'#detail [data-link-idea="{target_id}"]').first.evaluate("node => node.click()")
    _wait_for_radar_detail_id(radar, target_id)
    radar.locator(f'button[data-idea-id="{target_id}"].active').wait_for(timeout=15000)
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=target_id)
    assert radar.locator("#query").input_value() == ""
    assert radar.locator("#section").input_value() == "all"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_b058_memory_diagram_chip_routes_to_d025(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar&workstream=B-058", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    _wait_for_radar_detail_id(radar, "B-058")
    radar.locator("#detail").evaluate(
        """(node) => {
            const link = Array.from(
              node.querySelectorAll('a.chip-topology-diagram[href*="diagram=D-025"]')
            ).find((candidate) => candidate instanceof HTMLElement && candidate.offsetParent !== null);
            if (!link) {
              throw new Error("missing visible D-025 topology chip");
            }
            link.click();
        }"""
    )

    _wait_for_shell_tab(page, "atlas")
    _wait_for_shell_query_param(page, tab="atlas", key="diagram", value="D-025")
    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text="D-025").wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_search_filters_and_empty_state(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    filter_geometry = casebook.locator(".filters-bar").evaluate(
        """node => {
            const bar = node.getBoundingClientRect();
            const search = node.querySelector('#searchInput').getBoundingClientRect();
            const severity = node.querySelector('#severityFilter').getBoundingClientRect();
            const status = node.querySelector('#statusFilter').getBoundingClientRect();
            return {
              barLeft: bar.left,
              barRight: bar.right,
              searchWidth: search.width,
              severityWidth: severity.width,
              statusWidth: status.width,
              rightSlack: bar.right - status.right,
            };
        }"""
    )
    assert abs(filter_geometry["searchWidth"] - filter_geometry["severityWidth"]) <= 2
    assert abs(filter_geometry["severityWidth"] - filter_geometry["statusWidth"]) <= 2
    assert filter_geometry["rightSlack"] <= 16

    baseline_count = casebook.locator("button.bug-row").count()
    assert baseline_count > 1

    first_bug = casebook.locator("button.bug-row").first
    bug_route = str(first_bug.get_attribute("data-bug") or "").strip()
    bug_title = first_bug.locator(".bug-row-title").inner_text().strip()
    assert bug_route
    assert bug_title
    first_bug.click()
    _wait_for_shell_query_param(page, tab="casebook", key="bug", value=bug_route)
    casebook.locator("#detailPane .detail-title", has_text=bug_title).wait_for(timeout=15000)
    casebook.locator("#detailPane .section-heading", has_text="Odylith Agent Learnings").wait_for(timeout=15000)
    assert casebook.locator("#detailPane").get_by_text("Human Readout", exact=True).count() == 0
    assert casebook.locator("#detailPane").get_by_text("Nearby Change Guidance", exact=True).count() == 0
    assert casebook.locator("#detailPane").get_by_text("Inspect Next", exact=True).count() == 0

    severity_value = _first_non_default_option(casebook, "#severityFilter")
    if not severity_value:
        pytest.skip("Casebook fixture does not currently expose non-default severity filters.")
    casebook.locator("#severityFilter").select_option(severity_value)
    severity_count = casebook.locator("button.bug-row").count()
    assert 0 < severity_count <= baseline_count

    _reset_select_to_first_option(casebook, "#severityFilter")
    status_value = _first_non_default_option(casebook, "#statusFilter")
    if not status_value:
        pytest.skip("Casebook fixture does not currently expose non-default status filters.")
    casebook.locator("#statusFilter").select_option(status_value)
    status_count = casebook.locator("button.bug-row").count()
    assert 0 < status_count <= baseline_count

    _reset_select_to_first_option(casebook, "#statusFilter")
    casebook.locator("#searchInput").fill("zzzzzz-no-casebook-match")
    casebook.locator("#listMeta", has_text="Visible: 0").wait_for(timeout=15000)
    assert casebook.locator("button.bug-row").count() == 0
    assert casebook.locator("#listMeta").inner_text().strip() == "Visible: 0"
    assert casebook.locator("#detailPane").inner_text().strip() == ""

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_first_bug_rows_load_details_without_dead_shards(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)

    sample_rows = casebook.locator("button.bug-row").evaluate_all(
        """nodes => nodes.slice(0, 6).map((node) => ({
          route: (node.getAttribute('data-bug') || '').trim(),
          title: ((node.querySelector('.bug-row-title') && node.querySelector('.bug-row-title').textContent) || '').trim(),
        }))"""
    )
    assert sample_rows, "expected visible Casebook bug rows"

    for item in sample_rows:
        bug_route = str(item.get("route") or "").strip()
        bug_title = str(item.get("title") or "").strip()
        assert bug_route
        assert bug_title
        casebook.locator(f'button.bug-row[data-bug="{bug_route}"]').click()
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=bug_route)
        casebook.locator(f'button.bug-row.active[data-bug="{bug_route}"]').wait_for(timeout=15000)
        casebook.locator("#detailPane .detail-title", has_text=bug_title).wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_proof_control_panel_stays_pinned_to_the_selected_bug_lane(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    bug_root = fixture_root / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    (bug_root / "2026-04-08-proof-control-primary.md").write_text(
        (
            "# Proof Control Primary\n\n"
            "- Bug ID: CB-999\n"
            "- Severity: P1\n"
            "- Reproducibility: High\n"
            "- Status: Open\n"
            "- Components Affected: `src/odylith/runtime/governance/proof_state/resolver.py`\n"
            "- Linked Workstream: B-062\n"
            "- Proof Lane ID: casebook-proof-browser-primary\n"
            "- Current Blocker: Lambda permission lifecycle on ecs-drift-monitor invoke\n"
            "- Failure Fingerprint: aws:lambda:Permission doesn't support update\n"
            "- First Failing Phase: manifests-deploy\n"
            "- Clearance Condition: Hosted SIM3 passes beyond manifests-deploy\n"
            "- Current Proof Status: diagnosed\n"
            "- Description: Browser proof should stay pinned to the selected blocker lane.\n"
        ),
        encoding="utf-8",
    )
    (bug_root / "2026-04-08-proof-control-secondary.md").write_text(
        (
            "# Proof Control Secondary\n\n"
            "- Bug ID: CB-998\n"
            "- Severity: P1\n"
            "- Reproducibility: High\n"
            "- Status: Open\n"
            "- Components Affected: `src/odylith/runtime/governance/proof_state/resolver.py`\n"
            "- Linked Workstream: B-062\n"
            "- Proof Lane ID: casebook-proof-browser-secondary\n"
            "- Current Blocker: Secondary blocker that should not bleed into CB-999\n"
            "- Failure Fingerprint: alternate-fingerprint\n"
            "- First Failing Phase: alternate-phase\n"
            "- Clearance Condition: Hosted SIM3 passes beyond alternate-phase\n"
            "- Current Proof Status: diagnosed\n"
            "- Description: This bug shares the workstream but not the blocker lane.\n"
        ),
        encoding="utf-8",
    )
    proof_stream = "\n".join(
        (
            json.dumps(
                {
                    "ts_iso": "2026-04-08T18:42:00Z",
                    "proof_lane": "casebook-proof-browser-primary",
                    "proof_fingerprint": "aws:lambda:Permission doesn't support update",
                    "proof_phase": "manifests-deploy",
                    "proof_status": "falsified_live",
                    "evidence_tier": "code_only",
                    "work_category": "governance",
                    "deployment_truth": {
                        "pushed_head": "abc123",
                        "runner_fingerprint": "runner-v3",
                    },
                    "workstreams": ["B-062"],
                }
            ),
            json.dumps(
                {
                    "ts_iso": "2026-04-08T19:12:00Z",
                    "proof_lane": "casebook-proof-browser-primary",
                    "proof_fingerprint": "aws:lambda:Permission doesn't support update",
                    "proof_phase": "manifests-deploy",
                    "proof_status": "fixed_in_code",
                    "evidence_tier": "code_only",
                    "work_category": "observability",
                    "workstreams": ["B-062"],
                }
            ),
        )
    ) + "\n"
    (fixture_root / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl").write_text(
        proof_stream,
        encoding="utf-8",
    )
    (fixture_root / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl").write_text(
        proof_stream,
        encoding="utf-8",
    )
    (bug_root / "INDEX.md").write_text(
        sync_casebook_bug_index.render_bug_index(repo_root=fixture_root),
        encoding="utf-8",
    )

    casebook_rc = render_casebook_dashboard.main(
        ["--repo-root", str(fixture_root), "--output", "odylith/casebook/casebook.html"]
    )
    assert casebook_rc == 0
    _render_tooling_shell_fixture(fixture_root)

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=casebook&bug=CB-999",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                casebook = page.frame_locator("#frame-casebook")
                casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
                _wait_for_shell_query_param(page, tab="casebook", key="bug", value="CB-999")
                casebook.locator("#detailPane .detail-title", has_text="Proof control primary").wait_for(timeout=15000)
                casebook.locator("#detailPane .section-heading", has_text="Proof Control Panel").wait_for(timeout=15000)
                casebook.locator("#detailPane").get_by_text("Current blocker", exact=True).first.wait_for(timeout=15000)
                casebook.locator("#detailPane").get_by_text(
                    "Lambda permission lifecycle on ecs-drift-monitor invoke"
                ).first.wait_for(timeout=15000)
                casebook.locator("#detailPane").get_by_text("Failure fingerprint", exact=True).first.wait_for(timeout=15000)
                casebook.locator("#detailPane").get_by_text("Highest truthful claim", exact=True).first.wait_for(timeout=15000)
                casebook.locator("#detailPane").get_by_text("fixed in code").first.wait_for(timeout=15000)
                casebook.locator("#detailPane").get_by_text("Deployed vs local truth", exact=True).first.wait_for(timeout=15000)
                casebook.locator("#detailPane").get_by_text(
                    "Recent activity is skewing away from the primary blocker"
                ).first.wait_for(timeout=15000)
                assert (
                    casebook.locator("#detailPane")
                    .get_by_text("Secondary blocker that should not bleed into CB-999")
                    .count()
                    == 0
                )

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_atlas_navigation_filters_and_context_links(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    baseline_total = _atlas_total(atlas)
    assert baseline_total > 1

    initial_diagram = atlas.locator("#diagramId").inner_text().strip()
    initial_title = atlas.locator("#diagramTitle").inner_text().strip()
    assert initial_diagram
    assert initial_title

    atlas.locator("#nextDiagram").click()
    atlas.locator("#diagramId").wait_for(timeout=15000)
    next_diagram = atlas.locator("#diagramId").inner_text().strip()
    assert next_diagram
    assert next_diagram != initial_diagram

    atlas.locator("#prevDiagram").click()
    atlas.locator("#diagramId", has_text=initial_diagram).wait_for(timeout=15000)
    atlas.locator("#search").fill(initial_title)
    page.wait_for_function(
        """(frameSelector) => {
            const frame = document.querySelector(frameSelector);
            const doc = frame && frame.contentDocument;
            const total = doc && doc.querySelector("#statTotal");
            return Boolean(total) && total.textContent.trim() === "1";
        }""",
        arg="#frame-atlas",
        timeout=15000,
    )
    atlas.locator("#diagramId", has_text=initial_diagram).wait_for(timeout=15000)

    title_tokens = [token for token in re.findall(r"[A-Za-z0-9]+", initial_title) if len(token) >= 4]
    short_title = (max(title_tokens, key=len)[:6] if title_tokens else initial_title[:6]).strip()
    atlas.locator("#search").fill(short_title)
    page.wait_for_function(
        """({ frameSelector, baselineTotal }) => {
            const frame = document.querySelector(frameSelector);
            const doc = frame && frame.contentDocument;
            const total = doc && doc.querySelector("#statTotal");
            if (!total) return false;
            const value = Number.parseInt(total.textContent.trim(), 10);
            return Number.isFinite(value) && value >= 1 && value < baselineTotal;
        }""",
        arg={"frameSelector": "#frame-atlas", "baselineTotal": baseline_total},
        timeout=15000,
    )
    atlas.locator("#diagramId", has_text=initial_diagram).wait_for(timeout=15000)

    diagram_ids = atlas.locator("button[data-diagram]").evaluate_all(
        """nodes => nodes
          .map((node) => (node.getAttribute("data-diagram") || "").trim())
          .filter((token) => token.length > 0)
        """
    )
    searchable_diagram = initial_diagram
    short_diagram_token = ""
    for token in diagram_ids:
        match = re.search(r"-(\d+)$", str(token))
        if not match:
            continue
        suffix = match.group(1)
        stripped = str(int(suffix))
        if len(stripped) < 2 or stripped == suffix:
            continue
        if sum(1 for other in diagram_ids if stripped in str(other)) != 1:
            continue
        searchable_diagram = str(token)
        short_diagram_token = stripped
        break

    if searchable_diagram != initial_diagram:
        atlas.locator(f'button[data-diagram="{searchable_diagram}"]').click()
        atlas.locator("#diagramId", has_text=searchable_diagram).wait_for(timeout=15000)

    diagram_suffix = searchable_diagram.split("-", 1)[-1].strip()
    id_queries: list[str] = []
    if short_diagram_token:
        id_queries.append(short_diagram_token)
    for candidate in (searchable_diagram, diagram_suffix, f"-{diagram_suffix}"):
        token = str(candidate).strip()
        if token and token not in id_queries:
            id_queries.append(token)

    narrowed_by_id_query = False
    for query in id_queries:
        atlas.locator("#search").fill(query)
        try:
            page.wait_for_function(
                """({ frameSelector, baselineTotal }) => {
                    const frame = document.querySelector(frameSelector);
                    const doc = frame && frame.contentDocument;
                    const total = doc && doc.querySelector("#statTotal");
                    if (!total) return false;
                    const value = Number.parseInt(total.textContent.trim(), 10);
                    return Number.isFinite(value) && value >= 1 && value < baselineTotal;
                }""",
                arg={"frameSelector": "#frame-atlas", "baselineTotal": baseline_total},
                timeout=3000,
            )
            atlas.locator("#diagramId", has_text=searchable_diagram).wait_for(timeout=3000)
            narrowed_by_id_query = True
            break
        except PlaywrightTimeoutError:
            continue

    if not narrowed_by_id_query:
        pytest.skip("Atlas fixture does not currently expose a narrowing diagram-id substring query.")

    atlas.locator("#search").fill("")
    workstream_value = _first_non_default_option(atlas, "#workstreamFilter")
    if not workstream_value:
        pytest.skip("Atlas fixture does not currently expose non-default workstream filters.")
    atlas.locator("#workstreamFilter").select_option(workstream_value)
    filtered_total = _atlas_total(atlas)
    assert 0 < filtered_total <= baseline_total
    _wait_for_shell_query_param(page, tab="atlas", key="workstream", value=workstream_value)

    active_workstream_links = atlas.locator("#activeWorkstreamLinks a.workstream-pill-link").count()
    owner_workstream_links = atlas.locator("#ownerWorkstreamLinks a.workstream-pill-link").count()
    assert active_workstream_links > 0 or owner_workstream_links > 0
    assert atlas.locator("#registryLinks a").count() > 0

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_d025_memory_substrate_route_exposes_governed_registry_links(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas&diagram=D-025", wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text="D-025").wait_for(timeout=15000)
    _wait_for_shell_query_param(page, tab="atlas", key="diagram", value="D-025")

    registry_hrefs = [
        str(href)
        for href in atlas.locator("#registryLinks a").evaluate_all(
            """nodes => nodes
              .map((node) => String(node.getAttribute("href") || "").trim())
              .filter(Boolean)
            """
        )
    ]
    assert registry_hrefs, "expected D-025 to expose Registry component links"
    for component_id in (
        "odylith-projection-bundle",
        "odylith-projection-snapshot",
        "odylith-memory-backend",
        "odylith-remote-retrieval",
        "odylith-memory-contracts",
    ):
        assert any(f"component={component_id}" in href for href in registry_hrefs), (
            f"expected D-025 registry links to include {component_id}"
        )

    workstream_tokens = {
        str(token)
        for token in atlas.locator(
            "#activeWorkstreamLinks a.workstream-pill-link, "
            "#ownerWorkstreamLinks a.workstream-pill-link, "
            "#historicalWorkstreamLinks a.workstream-pill-link"
        ).evaluate_all(
            """nodes => nodes
              .map((node) => String(node.textContent || "").trim())
              .filter(Boolean)
            """
        )
    }
    assert {"B-058", "B-059"}.issubset(workstream_tokens)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_scope_window_and_detail_behavior_in_compact_viewport(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="24h")
    _wait_for_compass_brief_state(
        page,
        window_token="24h",
        scope_label="Global",
        statuses=("ready", "unavailable"),
    )
    global_24h_meta = _compass_brief_metadata(compass)
    assert global_24h_meta["source"] in {"provider", "cache", "unavailable"}
    if global_24h_meta["source"] in {"provider", "cache"}:
        assert global_24h_meta["hasNotice"] == "false"
    assert global_24h_meta["fingerprint"]
    layout = compass.locator(".layout").evaluate(
        """(node) => {
            const stacks = Array.from(node.querySelectorAll(':scope > .stack'));
            const firstBox = stacks[0] ? stacks[0].getBoundingClientRect() : null;
            const secondBox = stacks[1] ? stacks[1].getBoundingClientRect() : null;
            return {
              clientWidth: node.clientWidth,
              scrollWidth: node.scrollWidth,
              stackCount: stacks.length,
              firstBottom: firstBox ? firstBox.bottom : 0,
              secondTop: secondBox ? secondBox.top : 0,
              gridTemplateColumns: getComputedStyle(node).gridTemplateColumns,
            };
        }"""
    )
    assert layout["stackCount"] >= 2
    assert layout["secondTop"] - layout["firstBottom"] >= 10

    scope_value = _first_scope_option_with_scoped_brief(compass, window_token="24h")
    if not scope_value or not re.fullmatch(r"B-\d{3,}", scope_value):
        pytest.skip("Compass fixture does not currently expose non-global workstream scope options.")
    compass.locator("#scope-select").select_option(scope_value)
    _wait_for_shell_query_param(page, tab="compass", key="scope", value=scope_value)
    compass.locator("#scope-pill", has_text=scope_value).wait_for(timeout=15000)
    _wait_for_compass_brief_state(
        page,
        window_token="24h",
        scope_label=scope_value,
        statuses=("ready", "unavailable"),
    )
    scoped_24h_meta = _compass_brief_metadata(compass)
    assert scoped_24h_meta["source"] in {"provider", "cache", "unavailable"}
    if scoped_24h_meta["source"] in {"provider", "cache"}:
        if scoped_24h_meta["hasNotice"] == "true":
            assert scoped_24h_meta["noticeReason"].startswith("scoped_")
            assert "showing_global" in scoped_24h_meta["noticeReason"]
        else:
            assert scoped_24h_meta["hasNotice"] == "false"
    assert scoped_24h_meta["fingerprint"]
    if scoped_24h_meta["hasNotice"] == "false":
        assert scoped_24h_meta["fingerprint"] != global_24h_meta["fingerprint"]

    summary_rows = compass.locator("tr.ws-summary-row")
    assert summary_rows.count() > 0
    target_row = compass.locator(f'tr.ws-summary-row[data-ws-id="{scope_value}"]').first
    if target_row.count() == 0:
        target_row = summary_rows.first
    target_workstream = str(target_row.get_attribute("data-ws-id") or "").strip()
    assert target_workstream
    target_row.click()
    compass.locator(f'tr.ws-detail-row.is-open[data-ws-detail="{target_workstream}"]').wait_for(timeout=15000)

    compass.locator('button[data-window="48h"]').click()
    _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
    _wait_for_compass_brief_state(
        page,
        window_token="48h",
        scope_label=scope_value,
        statuses=("ready", "unavailable"),
    )
    page.wait_for_function(
        """() => {
            const frame = document.querySelector("#frame-compass");
            const doc = frame && frame.contentDocument;
            if (!doc) return false;
            return doc.querySelectorAll("#timeline .tx-card, #timeline .empty, #timeline .timeline-day-title, #timeline .hour-empty").length > 0;
        }""",
        timeout=15000,
    )
    _assert_compass_live_state(compass, window_token="48h")
    scoped_48h_meta = _compass_brief_metadata(compass)
    assert scoped_48h_meta["source"] in {"provider", "cache", "unavailable"}
    assert scoped_48h_meta["fingerprint"]
    if scoped_48h_meta["fingerprint"] == scoped_24h_meta["fingerprint"]:
        assert scoped_24h_meta["hasNotice"] == "true"
        assert scoped_48h_meta["hasNotice"] == "true"
        assert scoped_48h_meta["noticeReason"].startswith("scoped_")
        assert "showing" in scoped_48h_meta["noticeReason"]
    else:
        assert scoped_48h_meta["fingerprint"] != scoped_24h_meta["fingerprint"]

    compass.locator("#scope-global").click()
    page.wait_for_function(
        """() => {
            try {
              const url = new URL(window.location.href);
              return url.pathname.endsWith("/odylith/index.html")
                && url.searchParams.get("tab") === "compass"
                && !url.searchParams.has("scope");
            } catch (_error) {
              return false;
            }
        }""",
        timeout=15000,
    )
    compass.locator("#scope-pill", has_text="Global").wait_for(timeout=15000)
    _wait_for_compass_brief_state(
        page,
        window_token="48h",
        scope_label="Global",
        statuses=("ready", "unavailable"),
    )
    global_48h_meta = _compass_brief_metadata(compass)
    assert global_48h_meta["source"] in {"provider", "cache", "unavailable"}
    if global_48h_meta["source"] in {"provider", "cache"}:
        assert global_48h_meta["hasNotice"] == "false"
    assert global_48h_meta["fingerprint"]
    assert global_48h_meta["window"] == "48h"
    if scoped_48h_meta["source"] in {"provider", "cache"} and scoped_48h_meta["hasNotice"] == "false":
        assert global_48h_meta["fingerprint"] != scoped_48h_meta["fingerprint"]

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_scoped_brief_missing_shows_global_live_brief_with_notice(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    history_dir = runtime_dir / "history"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    payload["generated_utc"] = "2026-04-10T20:08:00Z"
    scoped_24h = (payload.get("standup_brief_scoped") or {}).get("24h")
    scoped_48h = (payload.get("standup_brief_scoped") or {}).get("48h")
    assert isinstance(scoped_24h, dict) and scoped_24h
    assert isinstance(scoped_48h, dict) and scoped_48h
    standup_brief = payload.get("standup_brief") if isinstance(payload.get("standup_brief"), dict) else {}
    digest = payload.get("digest") if isinstance(payload.get("digest"), dict) else {}

    def _ready_global_brief(window: str) -> dict[str, object]:
        return {
            "status": "ready",
            "source": "provider",
            "fingerprint": f"seeded-global-{window}",
            "generated_utc": payload["generated_utc"],
            "sections": [
                {
                    "key": "current_execution",
                    "label": "Current execution",
                    "bullets": [
                        {
                            "text": "Compass is holding one calm global brief while scoped narration catches up.",
                            "fact_ids": [],
                        }
                    ],
                }
            ],
            "evidence_lookup": {},
        }

    for window in ("24h", "48h"):
        brief = standup_brief.get(window)
        if not isinstance(brief, dict) or brief.get("status") != "ready":
            standup_brief[window] = _ready_global_brief(window)
        digest[window] = ["Compass is holding one calm global brief while scoped narration catches up."]
    payload["standup_brief"] = standup_brief
    payload["digest"] = digest

    scope_value = next(iter(scoped_24h.keys()))
    verified = payload.get("verified_scoped_workstreams") if isinstance(payload.get("verified_scoped_workstreams"), dict) else {}
    for window in ("24h", "48h"):
        verified_list = verified.get(window)
        if isinstance(verified_list, list) and scope_value not in verified_list:
            verified_list.append(scope_value)
    payload["verified_scoped_workstreams"] = verified

    for collection_key in ("current_workstreams", "workstream_catalog"):
        rows = payload.get(collection_key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or str(row.get("idea_id", "")).strip() != scope_value:
                continue
            activity = row.get("activity") if isinstance(row.get("activity"), dict) else {}
            activity["24h"] = {"commit_count": 1, "local_change_count": 1, "file_touch_count": 1}
            activity["48h"] = {"commit_count": 1, "local_change_count": 1, "file_touch_count": 1}
            row["activity"] = activity
            break

    scoped_24h.pop(scope_value, None)
    scoped_48h.pop(scope_value, None)
    digest_scoped = payload.get("digest_scoped") if isinstance(payload.get("digest_scoped"), dict) else {}
    digest_24h = digest_scoped.get("24h") if isinstance(digest_scoped.get("24h"), dict) else {}
    digest_48h = digest_scoped.get("48h") if isinstance(digest_scoped.get("48h"), dict) else {}
    digest_24h.pop(scope_value, None)
    digest_48h.pop(scope_value, None)
    payload["digest_scoped"] = digest_scoped
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    for day_token in payload.get("history", {}).get("dates", []):
        token = str(day_token or "").strip()
        if not token:
            continue
        (history_dir / f"{token}.v1.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&window=24h&date=live&scope={scope_value}",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _wait_for_shell_query_param(page, tab="compass", key="scope", value=scope_value)
                page.wait_for_function(
                    """({ windowToken, scopeLabel }) => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const target = doc && doc.querySelector("#digest-list");
                        if (!target || !target.dataset) return false;
                        return (target.dataset.briefStatus || "") === "ready"
                          && (target.dataset.briefWindow || "") === windowToken
                          && (target.dataset.briefScope || "") === scopeLabel
                          && (target.dataset.briefHasNotice || "") === "true";
                    }""",
                    arg={"windowToken": "24h", "scopeLabel": scope_value},
                    timeout=15000,
                )
                scoped_24h_meta = _compass_brief_metadata(compass)
                assert scoped_24h_meta["status"] == "ready"
                assert scoped_24h_meta["source"] in {"provider", "cache"}
                assert scoped_24h_meta["hasNotice"] == "true"
                assert scoped_24h_meta["noticeReason"] == "scoped_brief_missing_showing_global"
                assert "Showing the global live brief" in compass.locator("#digest-list").inner_text()

                compass.locator('button[data-window="48h"]').click()
                _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
                page.wait_for_function(
                    """({ windowToken, scopeLabel }) => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const target = doc && doc.querySelector("#digest-list");
                        if (!target || !target.dataset) return false;
                        return (target.dataset.briefStatus || "") === "ready"
                          && (target.dataset.briefWindow || "") === windowToken
                          && (target.dataset.briefScope || "") === scopeLabel
                          && (target.dataset.briefHasNotice || "") === "true";
                    }""",
                    arg={"windowToken": "48h", "scopeLabel": scope_value},
                    timeout=15000,
                )
                scoped_48h_meta = _compass_brief_metadata(compass)
                assert scoped_48h_meta["status"] == "ready"
                assert scoped_48h_meta["source"] in {"provider", "cache"}
                assert scoped_48h_meta["hasNotice"] == "true"
                assert scoped_48h_meta["noticeReason"] == "scoped_brief_missing_showing_global"
                assert "Showing the global live brief" in compass.locator("#digest-list").inner_text()

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_quiet_catalog_scope_reports_quiet_window_instead_of_missing_brief(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    catalog = [row for row in payload.get("workstream_catalog", []) if isinstance(row, dict)]
    assert catalog
    quiet_scope = str(catalog[0].get("idea_id", "")).strip()
    assert quiet_scope
    for row in catalog:
        if str(row.get("idea_id", "")).strip() != quiet_scope:
            continue
        activity = row.get("activity") if isinstance(row.get("activity"), dict) else {}
        for window in ("24h", "48h"):
            window_activity = activity.get(window)
            if not isinstance(window_activity, dict):
                window_activity = {}
                activity[window] = window_activity
            window_activity["commit_count"] = 0
            window_activity["local_change_count"] = 0
            window_activity["file_touch_count"] = 0
        row["activity"] = activity
        break
    standup_brief_scoped = payload.get("standup_brief_scoped") if isinstance(payload.get("standup_brief_scoped"), dict) else {}
    for window in ("24h", "48h"):
        scoped_map = standup_brief_scoped.get(window)
        if isinstance(scoped_map, dict):
            scoped_map[quiet_scope] = {
                "status": "unavailable",
                "source": "unavailable",
                "fingerprint": "",
                "generated_utc": str(payload.get("generated_utc", "")).strip(),
                "diagnostics": {
                    "reason": "scoped_window_inactive",
                    "title": "Nothing moved in this window",
                    "message": (
                        f"{quiet_scope} was quiet in the last {24 if window == '24h' else 48} hours, "
                        "so Compass has nothing new to brief for that scope."
                    ),
                },
                "sections": [],
                "evidence_lookup": {},
            }
    payload["standup_brief_scoped"] = standup_brief_scoped
    digest_scoped = payload.get("digest_scoped") if isinstance(payload.get("digest_scoped"), dict) else {}
    for window in ("24h", "48h"):
        scoped_digest = digest_scoped.get(window)
        if isinstance(scoped_digest, dict):
            scoped_digest.pop(quiet_scope, None)
    payload["digest_scoped"] = digest_scoped
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&window=24h&date=live&scope={quiet_scope}",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _wait_for_shell_query_param(page, tab="compass", key="scope", value=quiet_scope)
                page.wait_for_function(
                    """({ windowToken, scopeLabel }) => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const target = doc && doc.querySelector("#digest-list");
                        if (!target || !target.dataset) return false;
                        return (target.dataset.briefStatus || "") === "unavailable"
                          && (target.dataset.briefWindow || "") === windowToken
                          && (target.dataset.briefScope || "") === scopeLabel;
                    }""",
                    arg={"windowToken": "24h", "scopeLabel": quiet_scope},
                    timeout=15000,
                )
                quiet_24h_text = compass.locator("#digest-list").inner_text()
                assert "Nothing moved in this window" in quiet_24h_text
                assert "was quiet in the last 24 hours" in quiet_24h_text
                assert "No scoped standup brief is available" not in quiet_24h_text

                compass.locator('button[data-window="48h"]').click()
                _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
                page.wait_for_function(
                    """({ windowToken, scopeLabel }) => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const target = doc && doc.querySelector("#digest-list");
                        if (!target || !target.dataset) return false;
                        return (target.dataset.briefStatus || "") === "unavailable"
                          && (target.dataset.briefWindow || "") === windowToken
                          && (target.dataset.briefScope || "") === scopeLabel;
                    }""",
                    arg={"windowToken": "48h", "scopeLabel": quiet_scope},
                    timeout=15000,
                )
                quiet_48h_text = compass.locator("#digest-list").inner_text()
                assert "Nothing moved in this window" in quiet_48h_text
                assert "was quiet in the last 48 hours" in quiet_48h_text
                assert "No scoped standup brief is available" not in quiet_48h_text

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_dropdown_excludes_unverified_governance_only_scope_and_scoped_timeline_stays_empty(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    current_rows = [row for row in payload.get("current_workstreams", []) if isinstance(row, dict)]
    assert len(current_rows) >= 5
    weak_scope = str(current_rows[0].get("idea_id", "")).strip()
    assert weak_scope
    broad_ids = [
        str(row.get("idea_id", "")).strip()
        for row in current_rows
        if str(row.get("idea_id", "")).strip() and str(row.get("idea_id", "")).strip() != weak_scope
    ][:4]
    assert len(broad_ids) == 4

    for collection_name in ("workstream_catalog", "current_workstreams"):
        rows = payload.get(collection_name)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or str(row.get("idea_id", "")).strip() != weak_scope:
                continue
            activity = row.get("activity") if isinstance(row.get("activity"), dict) else {}
            for window in ("24h", "48h"):
                window_activity = activity.get(window)
                if not isinstance(window_activity, dict):
                    window_activity = {}
                    activity[window] = window_activity
                window_activity["commit_count"] = 0
                window_activity["local_change_count"] = 1
                window_activity["file_touch_count"] = 1
            row["activity"] = activity
            break

    payload["timeline_events"] = [
        row
        for row in payload.get("timeline_events", [])
        if isinstance(row, dict) and weak_scope not in [str(item).strip() for item in row.get("workstreams", [])]
    ]
    payload["timeline_transactions"] = [
        row
        for row in payload.get("timeline_transactions", [])
        if isinstance(row, dict) and weak_scope not in [str(item).strip() for item in row.get("workstreams", [])]
    ]
    now_local_iso = str(payload.get("now_local_iso", "")).strip() or "2026-04-09T12:00:00-07:00"
    payload["timeline_events"].insert(
        0,
        {
            "id": f"local:M:odylith/radar/source/ideas/{weak_scope}.md",
            "kind": "local_change",
            "ts_iso": now_local_iso,
            "summary": f"Modified radar source for {weak_scope}",
            "author": "local",
            "sha": "",
            "workstreams": [weak_scope],
            "files": [
                f"odylith/radar/source/ideas/2026-04/{weak_scope.lower()}-example.md",
            ],
            "source": "local",
            "session_id": "",
            "transaction_id": "",
            "transaction_seq": None,
            "transaction_boundary": "",
            "context": "",
            "headline_hint": "",
            "proof_lane": "",
            "proof_fingerprint": "",
            "proof_phase": "",
            "evidence_tier": "",
            "proof_status": "",
            "work_category": "",
            "deployment_truth": {},
        },
    )
    payload["timeline_transactions"].insert(
        0,
        {
            "id": "txn:global:auto-global-weak-scope",
            "transaction_id": "txn:global:auto-global-weak-scope",
            "session_id": "",
            "start_ts_iso": now_local_iso,
            "end_ts_iso": now_local_iso,
            "headline": "Broad governance transaction should stay global.",
            "context": "",
            "event_count": 9,
            "files_count": 2,
            "workstreams": [weak_scope, *broad_ids],
            "files": [
                "odylith/radar/source/ideas/2026-04/example-a.md",
                "odylith/radar/source/ideas/2026-04/example-b.md",
            ],
            "events": [{"kind": "local_change", "summary": "Updated governance source"}],
        },
    )

    scoped_catalog = payload.get("verified_scoped_workstreams")
    scoped_catalog = scoped_catalog if isinstance(scoped_catalog, dict) else {}
    for window in ("24h", "48h"):
        existing = scoped_catalog.get(window)
        scoped_catalog[window] = [
            str(item).strip()
            for item in (existing if isinstance(existing, list) else [])
            if str(item).strip() and str(item).strip() != weak_scope
        ]
    payload["verified_scoped_workstreams"] = scoped_catalog
    window_scope_signals = payload.get("window_scope_signals")
    if not isinstance(window_scope_signals, dict):
        window_scope_signals = {}
    promoted_scoped = payload.get("promoted_scoped_workstreams")
    if not isinstance(promoted_scoped, dict):
        promoted_scoped = {}
    low_signal = {
        "rank": 1,
        "rung": "R1",
        "token": "background_trace",
        "label": "Background trace",
        "reasons": [
            "Only low-signal governance-local churn remains in this window.",
        ],
        "caps": ["governance_only_local_change"],
        "promoted_default": False,
        "budget_class": "cache_only",
        "feature_vector": {
            "has_any_signal": True,
            "verified_completion": False,
            "narrow_verified_signal": False,
            "meaningful_scope_activity": False,
            "decision_evidence": False,
            "implementation_evidence": False,
            "open_warning": False,
            "cross_surface_conflict": False,
            "stale_authority": False,
            "unsafe_closeout": False,
            "proof_blocker": False,
        },
    }
    for window in ("24h", "48h"):
        existing_signals = window_scope_signals.get(window)
        if not isinstance(existing_signals, dict):
            existing_signals = {}
            window_scope_signals[window] = existing_signals
        existing_signals[weak_scope] = dict(low_signal)
        existing_promoted = promoted_scoped.get(window)
        promoted_scoped[window] = [
            str(item).strip()
            for item in (existing_promoted if isinstance(existing_promoted, list) else [])
            if str(item).strip() and str(item).strip() != weak_scope
        ]
    payload["window_scope_signals"] = window_scope_signals
    payload["promoted_scoped_workstreams"] = promoted_scoped

    standup_brief_scoped = payload.get("standup_brief_scoped") if isinstance(payload.get("standup_brief_scoped"), dict) else {}
    digest_scoped = payload.get("digest_scoped") if isinstance(payload.get("digest_scoped"), dict) else {}
    for window in ("24h", "48h"):
        scoped_briefs = standup_brief_scoped.get(window)
        if isinstance(scoped_briefs, dict):
            scoped_briefs[weak_scope] = {
                "status": "unavailable",
                "source": "unavailable",
                "fingerprint": "",
                "generated_utc": str(payload.get("generated_utc", "")).strip(),
                "diagnostics": {
                    "reason": "scoped_window_inactive",
                    "title": "Nothing moved in this window",
                    "message": (
                        f"{weak_scope} was quiet in the last {24 if window == '24h' else 48} hours, "
                        "so Compass has nothing new to brief for that scope."
                    ),
                },
                "sections": [],
                "evidence_lookup": {},
            }
        scoped_digest = digest_scoped.get(window)
        if isinstance(scoped_digest, dict):
            scoped_digest.pop(weak_scope, None)
    payload["standup_brief_scoped"] = standup_brief_scoped
    payload["digest_scoped"] = digest_scoped

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=48h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                option_values = compass.locator("#scope-select option").evaluate_all(
                    "(nodes) => nodes.map((node) => String(node.value || '').trim())"
                )
                assert weak_scope not in option_values[1:]

                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&window=48h&date=live&scope={weak_scope}",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _wait_for_shell_query_param(page, tab="compass", key="scope", value=weak_scope)
                page.wait_for_function(
                    """({ windowToken, scopeLabel }) => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const target = doc && doc.querySelector("#digest-list");
                        if (!target || !target.dataset) return false;
                        return (target.dataset.briefStatus || "") === "unavailable"
                          && (target.dataset.briefWindow || "") === windowToken
                          && (target.dataset.briefScope || "") === scopeLabel;
                    }""",
                    arg={"windowToken": "48h", "scopeLabel": weak_scope},
                    timeout=15000,
                )
                quiet_text = compass.locator("#digest-list").inner_text()
                assert "Nothing moved in this window" in quiet_text
                assert f"{weak_scope} was quiet in the last 48 hours" in quiet_text
                compass.locator("#timeline .empty", has_text="No audit events in this scope and window.").wait_for(timeout=15000)
                assert "Broad governance transaction should stay global." not in compass.locator("#timeline").inner_text()

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_radar_default_order_prefers_high_scope_signal_without_hiding_low_signal_scope(
    tmp_path,
) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    payload_path = fixture_root / "odylith" / "radar" / "backlog-payload.v1.js"
    payload_text = payload_path.read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\})\s*;\s*$", payload_text, flags=re.S)
    assert match is not None
    payload = json.loads(match.group(1))
    entries = payload.get("entries")
    assert isinstance(entries, list)

    candidate_rows = [
        row
        for row in entries
        if isinstance(row, dict) and str(row.get("idea_id", "")).strip()
    ]
    assert len(candidate_rows) >= 2
    high_row = candidate_rows[0]
    low_row = candidate_rows[1]
    high_id = str(high_row.get("idea_id", "")).strip()
    low_id = str(low_row.get("idea_id", "")).strip()
    assert high_id and low_id and high_id != low_id

    for row in entries:
        if not isinstance(row, dict):
            continue
        row["status"] = "finished"

    high_row["status"] = "implementation"
    high_row["title"] = "Scope Ladder Fixture High"
    high_row["ordering_score"] = "1"
    high_row["scope_signal_rank"] = 4
    high_row["scope_signal_promoted_default"] = True
    high_row["scope_signal_budget_class"] = "escalated_reasoning"
    high_row["scope_signal"] = {
        "rank": 4,
        "rung": "R4",
        "token": "actionable_priority",
        "label": "Actionable priority",
        "promoted_default": True,
        "budget_class": "escalated_reasoning",
        "reasons": ["open warning posture"],
        "caps": [],
        "features": {},
    }

    low_row["status"] = "implementation"
    low_row["title"] = "Scope Ladder Fixture Low"
    low_row["ordering_score"] = "999"
    low_row["scope_signal_rank"] = 1
    low_row["scope_signal_promoted_default"] = False
    low_row["scope_signal_budget_class"] = "cache_only"
    low_row["scope_signal"] = {
        "rank": 1,
        "rung": "R1",
        "token": "background_trace",
        "label": "Background trace",
        "promoted_default": False,
        "budget_class": "cache_only",
        "reasons": ["governance-only local churn"],
        "caps": ["governance_only"],
        "features": {},
    }

    payload_path.write_text(
        'window["__ODYLITH_BACKLOG_DATA__"] = ' + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
                assert response is not None and response.ok

                radar = page.frame_locator("#frame-radar")
                radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
                radar.locator("#query").fill("scope ladder fixture")
                _wait_for_locator_count(page, "#frame-radar", "button[data-idea-id]", 2)
                first_two_ids = radar.locator("button[data-idea-id]").evaluate_all(
                    "(nodes) => nodes.slice(0, 2).map((node) => String(node.getAttribute('data-idea-id') || '').trim())"
                )
                assert first_two_ids == [high_id, low_id]
                assert radar.locator(f'button[data-idea-id=\"{high_id}\"]').count() == 1
                assert radar.locator(f'button[data-idea-id=\"{low_id}\"]').count() == 1

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_registry_default_order_prefers_high_scope_signal_without_hiding_low_signal_component(
    tmp_path,
) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    payload_path = fixture_root / "odylith" / "registry" / "registry-payload.v1.js"
    payload_text = payload_path.read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\})\s*;\s*$", payload_text, flags=re.S)
    assert match is not None
    payload = json.loads(match.group(1))

    components = payload.get("components")
    assert isinstance(components, list)
    component_rows = [
        row
        for row in components
        if isinstance(row, dict) and str(row.get("component_id", "")).strip()
    ]
    assert len(component_rows) >= 2

    high_row = component_rows[0]
    low_row = component_rows[1]
    high_id = str(high_row.get("component_id", "")).strip()
    low_id = str(low_row.get("component_id", "")).strip()
    assert high_id and low_id and high_id != low_id

    high_row["name"] = "Scope Ladder Fixture High"
    low_row["name"] = "Scope Ladder Fixture Low"
    high_row["category"] = "scope_test"
    low_row["category"] = "scope_test"

    delivery = payload.get("delivery_intelligence")
    if not isinstance(delivery, dict):
        delivery = {}
        payload["delivery_intelligence"] = delivery
    delivery_components = delivery.get("components")
    if not isinstance(delivery_components, dict):
        delivery_components = {}
        delivery["components"] = delivery_components

    delivery_components[high_id] = {
        "scope_signal": {
            "rank": 4,
            "rung": "R4",
            "token": "actionable_priority",
            "label": "Actionable priority",
            "promoted_default": True,
            "budget_class": "escalated_reasoning",
            "reasons": ["open warning posture"],
            "caps": [],
            "features": {},
        }
    }
    delivery_components[low_id] = {
        "scope_signal": {
            "rank": 1,
            "rung": "R1",
            "token": "background_trace",
            "label": "Background trace",
            "promoted_default": False,
            "budget_class": "cache_only",
            "reasons": ["governance-only local churn"],
            "caps": ["governance_only"],
            "features": {},
        }
    }

    payload_path.write_text(
        'window["__ODYLITH_REGISTRY_DATA__"] = ' + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
                assert response is not None and response.ok

                registry = page.frame_locator("#frame-registry")
                registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
                registry.locator("#search").fill("scope ladder fixture")
                _wait_for_locator_count(page, "#frame-registry", "button[data-component]", 2)
                first_two_ids = registry.locator("button[data-component]").evaluate_all(
                    "(nodes) => nodes.slice(0, 2).map((node) => String(node.getAttribute('data-component') || '').trim())"
                )
                assert first_two_ids == [high_id, low_id]
                assert registry.locator(f'button[data-component=\"{high_id}\"]').count() == 1
                assert registry.locator(f'button[data-component=\"{low_id}\"]').count() == 1

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_atlas_scope_signal_ladder_diagrams_keep_owner_context_without_leaking_active_noise(
    browser_context,
) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas&diagram=D-029", wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text="D-029").wait_for(timeout=15000)
    _wait_for_shell_query_param(page, tab="atlas", key="diagram", value="D-029")

    owner_tokens = atlas.locator("#ownerWorkstreamLinks a.workstream-pill-link").evaluate_all(
        "(nodes) => nodes.map((node) => String(node.textContent || '').trim()).filter(Boolean)"
    )
    assert owner_tokens == ["B-071"]
    assert atlas.locator("#activeWorkstreamLinks a.workstream-pill-link").count() == 0
    assert atlas.locator("#historicalWorkstreamLinks a.workstream-pill-link").count() == 0

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_refreshed_compass_artifacts_do_not_show_stale_unavailable_brief(
    tmp_path,
) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    baseline_payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    stale_payload = json.loads(json.dumps(baseline_payload))
    stale_payload["generated_utc"] = "2020-01-02T16:45:00Z"
    stale_payload["standup_brief"] = {
        "24h": {
            "status": "unavailable",
            "source": "unavailable",
            "fingerprint": "stale-24h",
            "generated_utc": "",
            "sections": [],
            "diagnostics": {
                "reason": "provider_deferred",
                "title": "Standup brief unavailable",
                "message": "Compass kept the cheap refresh path here, and no exact same-packet narrated brief was available to replay.",
            },
            "evidence_lookup": {},
        },
        "48h": {
            "status": "unavailable",
            "source": "unavailable",
            "fingerprint": "stale-48h",
            "generated_utc": "",
            "sections": [],
            "diagnostics": {
                "reason": "provider_deferred",
                "title": "Standup brief unavailable",
                "message": "Compass kept the cheap refresh path here, and no exact same-packet narrated brief was available to replay.",
            },
            "evidence_lookup": {},
        },
    }
    stale_payload["standup_brief_scoped"] = {"24h": {}, "48h": {}}
    runtime_json_path.write_text(json.dumps(stale_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(stale_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    fresh_payload = json.loads(json.dumps(baseline_payload))
    fresh_payload["generated_utc"] = "2026-04-08T01:00:00Z"
    fresh_payload["now_local_iso"] = "2026-04-07T18:00:00-07:00"
    runtime_contract = fresh_payload.get("runtime_contract") if isinstance(fresh_payload.get("runtime_contract"), dict) else {}
    runtime_contract["refresh_profile"] = "shell-safe"
    runtime_contract["last_refresh_attempt"] = {
        "status": "passed",
        "requested_profile": "shell-safe",
        "applied_profile": "shell-safe",
        "runtime_mode": "auto",
        "reason": "",
        "attempted_utc": fresh_payload["generated_utc"],
        "fallback_used": False,
    }
    fresh_payload["runtime_contract"] = runtime_contract

    def _normalize_brief(brief: dict[str, object], *, source: str, generated_utc: str) -> dict[str, object]:
        normalized = dict(brief)
        normalized["status"] = "ready"
        normalized["source"] = source
        normalized["generated_utc"] = generated_utc
        normalized.pop("notice", None)
        normalized.pop("diagnostics", None)
        return normalized

    standup_brief = fresh_payload.get("standup_brief") if isinstance(fresh_payload.get("standup_brief"), dict) else {}
    for window in ("24h", "48h"):
        brief = standup_brief.get(window)
        if isinstance(brief, dict):
            standup_brief[window] = _normalize_brief(brief, source="provider", generated_utc=fresh_payload["generated_utc"])
    fresh_payload["standup_brief"] = standup_brief

    standup_brief_scoped = (
        fresh_payload.get("standup_brief_scoped")
        if isinstance(fresh_payload.get("standup_brief_scoped"), dict)
        else {}
    )
    for window in ("24h", "48h"):
        scoped_map = standup_brief_scoped.get(window)
        if not isinstance(scoped_map, dict):
            continue
        for ws_id, brief in list(scoped_map.items()):
            if isinstance(brief, dict):
                scoped_map[ws_id] = _normalize_brief(brief, source="cache", generated_utc=fresh_payload["generated_utc"])
    fresh_payload["standup_brief_scoped"] = standup_brief_scoped
    runtime_json_path.write_text(json.dumps(fresh_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(fresh_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    assert fresh_payload["standup_brief"]["24h"]["source"] in {"provider", "cache"}
    assert "notice" not in fresh_payload["standup_brief"]["24h"]
    assert fresh_payload["standup_brief"]["48h"]["source"] in {"provider", "cache"}
    assert "notice" not in fresh_payload["standup_brief"]["48h"]

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _assert_compass_live_state(compass, window_token="24h")
                _wait_for_compass_brief_state(
                    page,
                    window_token="24h",
                    scope_label="Global",
                    statuses=("ready", "unavailable"),
                )
                meta_24h = _compass_brief_metadata(compass)
                assert meta_24h["source"] in {"provider", "cache"}
                assert meta_24h["hasNotice"] == "false"
                compass.locator('button[data-window="48h"]').click()
                _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
                _assert_compass_live_state(compass, window_token="48h")
                _wait_for_compass_brief_state(page, window_token="48h", scope_label="Global")
                meta_48h = _compass_brief_metadata(compass)
                assert meta_48h["source"] in {"provider", "cache"}
                assert meta_48h["hasNotice"] == "false"

                scope_value = _first_non_default_option(compass, "#scope-select", excluded={""})
                if scope_value and re.fullmatch(r"B-\d{3,}", scope_value):
                    compass.locator("#scope-select").select_option(scope_value)
                    _wait_for_shell_query_param(page, tab="compass", key="scope", value=scope_value)
                    _wait_for_compass_brief_state(page, window_token="48h", scope_label=scope_value)
                    scoped_meta = _compass_brief_metadata(compass)
                    assert scoped_meta["source"] in {"provider", "cache"}
                    assert scoped_meta["hasNotice"] == "false"
                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_unavailable_brief_hides_copy_button_and_stays_compact(
    tmp_path,
) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    payload["generated_utc"] = "2026-04-10T02:00:00Z"
    payload["standup_brief"] = {
        "24h": {
            "status": "unavailable",
            "source": "unavailable",
            "fingerprint": "provider-error-24h",
            "generated_utc": "",
            "sections": [],
            "diagnostics": {
                "reason": "provider_error",
                "title": "Brief unavailable right now",
                "message": "The narration provider failed on the last attempt. Compass will retry on backoff.",
                "next_retry_utc": "2026-04-10T02:30:00Z",
            },
            "evidence_lookup": {},
        },
        "48h": {
            "status": "unavailable",
            "source": "unavailable",
            "fingerprint": "provider-error-48h",
            "generated_utc": "",
            "sections": [],
            "diagnostics": {
                "reason": "provider_error",
                "title": "Brief unavailable right now",
                "message": "The narration provider failed on the last attempt. Compass will retry on backoff.",
                "next_retry_utc": "2026-04-10T02:30:00Z",
            },
            "evidence_lookup": {},
        },
    }
    payload["standup_brief_scoped"] = {"24h": {}, "48h": {}}
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _assert_compass_live_state(compass, window_token="24h")
                _wait_for_compass_brief_state(
                    page,
                    window_token="24h",
                    scope_label="Global",
                    statuses=("unavailable",),
                )

                meta = _compass_brief_metadata(compass)
                assert meta["status"] == "unavailable"
                assert meta["source"] == "unavailable"

                card_state = compass.locator("#standup-brief-card").evaluate(
                    """(node) => {
                        const copyButton = node.querySelector("#copy-brief");
                        return {
                          compact: node.classList.contains("standup-brief-card--compact"),
                          copyHidden: Boolean(copyButton && copyButton.classList.contains("hidden")),
                          copyDisabled: Boolean(copyButton && copyButton.disabled),
                        };
                    }"""
                )
                assert card_state == {
                    "compact": True,
                    "copyHidden": True,
                    "copyDisabled": True,
                }
                digest_text = compass.locator("#digest-list").inner_text()
                assert "Brief unavailable right now" in digest_text
                assert "Next retry" in digest_text

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_live_brief_warm_poll_reasons_match_retry_policy(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="24h")

    retry_matrix = compass.locator("body").evaluate(
        """() => ({
            providerDeferred: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "provider_deferred" } },
              { date: "live" }
            ),
            rateLimited: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "rate_limited" } },
              { date: "live" }
            ),
            timeout: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "timeout" } },
              { date: "live" }
            ),
            transportError: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "transport_error" } },
              { date: "live" }
            ),
            creditsExhausted: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "credits_exhausted" } },
              { date: "live" }
            ),
            authError: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "auth_error" } },
              { date: "live" }
            ),
            providerUnavailable: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "provider_unavailable" } },
              { date: "live" }
            ),
            providerError: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "provider_error" } },
              { date: "live" }
            ),
            invalidBatch: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "invalid_batch" } },
              { date: "live" }
            ),
            scopedGlobalBorrow: shouldPollForWarmBrief(
              { status: "ready", notice: { reason: "scoped_provider_deferred_showing_global" } },
              { date: "live" }
            ),
            scopedWiderGlobalBorrow: shouldPollForWarmBrief(
              { status: "ready", notice: { reason: "scoped_provider_deferred_showing_wider_global" } },
              { date: "live" }
            ),
            historicalSnapshot: shouldPollForWarmBrief(
              { status: "unavailable", diagnostics: { reason: "provider_deferred" } },
              { date: "2026-04-10" }
            ),
        })"""
    )
    assert retry_matrix == {
        "providerDeferred": True,
        "rateLimited": True,
        "timeout": True,
        "transportError": True,
        "creditsExhausted": False,
        "authError": False,
        "providerUnavailable": False,
        "providerError": False,
        "invalidBatch": False,
        "scopedGlobalBorrow": True,
        "scopedWiderGlobalBorrow": True,
        "historicalSnapshot": False,
    }

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_provider_deferred_warm_poll_only_rerenders_brief(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")
    fixture_context_engine_dir = fixture_root / ".odylith" / "runtime"
    fixture_context_engine_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        _REPO_ROOT / ".odylith" / "runtime" / "odylith-context-engine-state.v1.js",
        fixture_context_engine_dir / "odylith-context-engine-state.v1.js",
    )

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    payload["generated_utc"] = "2026-04-12T23:10:00Z"
    standup_brief = payload.get("standup_brief") if isinstance(payload.get("standup_brief"), dict) else {}
    standup_brief["24h"] = {
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": "provider-deferred-24h",
        "generated_utc": "",
        "sections": [],
        "diagnostics": {
            "reason": "provider_deferred",
            "title": "Standup brief unavailable",
            "message": "Compass is still warming the live 24-hour brief.",
        },
        "evidence_lookup": {},
    }
    payload["standup_brief"] = standup_brief
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _assert_compass_live_state(compass, window_token="24h")
                _wait_for_compass_brief_state(
                    page,
                    window_token="24h",
                    scope_label="Global",
                    statuses=("unavailable",),
                )

                program_section = compass.locator("#execution-waves-host .execution-wave-section").first
                program_section.wait_for(timeout=15000)
                if program_section.get_attribute("open") is None:
                    program_section.locator("> summary").first.click()
                program_section.evaluate("(node) => { node.dataset.codexWarmBriefProbe = '1'; }")
                assert program_section.evaluate("(node) => node.dataset.codexWarmBriefProbe") == "1"

                compass.locator("body").evaluate(
                    """() => {
                        const readyBrief = {
                          status: "ready",
                          source: "provider",
                          fingerprint: "provider-ready-24h",
                          generated_utc: "2026-04-12T23:11:45Z",
                          sections: [
                            {
                              key: "completed",
                              label: "Completed in this window",
                              bullets: [{ text: "The live brief warmed successfully.", fact_ids: [] }],
                            },
                            {
                              key: "current_execution",
                              label: "Current execution",
                              bullets: [{ text: "Only the standup brief card should update now.", fact_ids: [] }],
                            },
                            {
                              key: "next_planned",
                              label: "Next planned",
                              bullets: [{ text: "Keep the existing governance DOM intact.", fact_ids: [] }],
                            },
                            {
                              key: "risks_to_watch",
                              label: "Risks to watch",
                              bullets: [{ text: "No extra live risk callout for this browser proof.", fact_ids: [] }],
                            },
                          ],
                          evidence_lookup: {},
                        };
                        const originalLoadRuntime = window.loadRuntime;
                        window.__codexWarmBriefLoadRuntimeCalls__ = 0;
                        window.loadRuntime = async (state) => {
                          window.__codexWarmBriefLoadRuntimeCalls__ += 1;
                          const runtime = await originalLoadRuntime(state);
                          const payload = runtime && runtime.payload && typeof runtime.payload === "object"
                            ? JSON.parse(JSON.stringify(runtime.payload))
                            : null;
                          if (!payload) return runtime;
                          const standupBrief = payload.standup_brief && typeof payload.standup_brief === "object"
                            ? payload.standup_brief
                            : {};
                          standupBrief["24h"] = readyBrief;
                          payload.generated_utc = readyBrief.generated_utc;
                          payload.standup_brief = standupBrief;
                          return Object.assign({}, runtime, { payload });
                        };
                    }"""
                )

                page.wait_for_function(
                    """() => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const digest = doc && doc.querySelector("#digest-list");
                        if (!digest || !digest.dataset) return false;
                        return (digest.dataset.briefStatus || "") === "ready"
                          && (digest.dataset.briefSource || "") === "provider";
                    }""",
                    timeout=15000,
                )
                page.wait_for_timeout(250)

                assert program_section.evaluate("(node) => node.dataset.codexWarmBriefProbe") == "1"
                assert program_section.evaluate("(node) => node.hasAttribute('open')") is True
                assert "The live brief warmed successfully." in compass.locator("#digest-list").inner_text()
                assert compass.locator("body").evaluate("() => window.__codexWarmBriefLoadRuntimeCalls__") == 1

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_shell_safe_compass_refresh_artifacts_enqueue_background_warm_without_foreground_provider(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    shutil.rmtree(runtime_dir / "history", ignore_errors=True)
    for path in (runtime_dir / "current.v1.json", runtime_dir / "current.v1.js"):
        path.unlink(missing_ok=True)

    provider = _CompassProvider()
    spawned: list[str] = []

    def _provider_from_config(  # noqa: ANN001
        config: odylith_reasoning.ReasoningConfig,
        *,
        repo_root=None,
        require_auto_mode=True,
        allow_implicit_local_provider=False,
    ):
        assert repo_root == fixture_root
        assert require_auto_mode is False
        assert allow_implicit_local_provider is True
        return provider

    monkeypatch.setattr(odylith_reasoning, "provider_from_config", _provider_from_config)
    monkeypatch.setattr(
        render_compass_dashboard.compass_standup_brief_maintenance,
        "maybe_spawn_background",
        lambda **kwargs: spawned.append(str(kwargs["repo_root"])) or 4321,
    )

    rc = render_compass_dashboard.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/compass/compass.html",
        ]
    )
    assert rc == 0
    assert provider.calls == 0
    assert spawned == [str(fixture_root.resolve())]
    request_payload = json.loads(
        compass_standup_brief_maintenance.maintenance_request_path(repo_root=fixture_root).read_text(encoding="utf-8")
    )
    assert sorted((request_payload.get("global") or {}).keys()) == ["24h", "48h"]
    result = compass_standup_brief_maintenance.run_pending_request(repo_root=fixture_root)
    assert sorted(result["globals"]) == ["24h", "48h"]
    assert provider.calls >= 1
    _render_tooling_shell_fixture(fixture_root)

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _assert_compass_live_state(compass, window_token="24h")
                _wait_for_compass_brief_state(
                    page,
                    window_token="24h",
                    scope_label="Global",
                    statuses=("ready",),
                )
                meta_24h = _compass_brief_metadata(compass)
                assert meta_24h["source"] == "provider"
                assert meta_24h["hasNotice"] == "false"

                scope_value = _first_non_default_option(compass, "#scope-select", excluded={""})
                assert re.fullmatch(r"B-\d{3,}", scope_value)
                compass.locator("#scope-select").select_option(scope_value)
                _wait_for_shell_query_param(page, tab="compass", key="scope", value=scope_value)
                _wait_for_compass_brief_state(
                    page,
                    window_token="24h",
                    scope_label=scope_value,
                    statuses=("ready", "unavailable"),
                )
                scoped_meta_24h = _compass_brief_metadata(compass)
                assert scoped_meta_24h["status"] == "ready"
                assert scoped_meta_24h["source"] in {"provider", "cache"}

                compass.locator('button[data-window="48h"]').click()
                _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
                _assert_compass_live_state(compass, window_token="48h")
                _wait_for_compass_brief_state(
                    page,
                    window_token="48h",
                    scope_label=scope_value,
                    statuses=("ready", "unavailable"),
                )
                scoped_meta_48h = _compass_brief_metadata(compass)
                assert scoped_meta_48h["status"] == "ready"
                assert scoped_meta_48h["source"] in {"provider", "cache"}

                _reset_select_to_first_option(compass, "#scope-select")
                _wait_for_compass_brief_state(
                    page,
                    window_token="48h",
                    scope_label="Global",
                    statuses=("ready",),
                )
                meta_48h = _compass_brief_metadata(compass)
                assert meta_48h["source"] == "provider"
                assert meta_48h["hasNotice"] == "false"

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_scoped_provider_deferred_shows_global_live_brief_with_notice(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    scoped_24h = (payload.get("standup_brief_scoped") or {}).get("24h")
    assert isinstance(scoped_24h, dict) and scoped_24h
    scope_value = next(iter(scoped_24h.keys()))
    payload["standup_brief"]["24h"] = {
        "status": "ready",
        "source": "provider",
        "fingerprint": "global-live-24h",
        "generated_utc": "2026-04-10T22:10:00Z",
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [{"text": "Good one to get over the line.", "fact_ids": []}],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "bullets": [{"text": "The main pressure is still trust.", "fact_ids": []}],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "bullets": [{"text": "Line the surfaces back up.", "fact_ids": []}],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "bullets": [{"text": "This is still the seam to watch.", "fact_ids": []}],
            },
        ],
        "evidence_lookup": {},
    }
    scoped_24h[scope_value] = {
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": "scoped-provider-deferred",
        "generated_utc": "",
        "sections": [],
        "diagnostics": {
            "reason": "provider_deferred",
            "title": "Standup brief unavailable",
            "message": "Compass is still warming this scoped brief.",
        },
        "evidence_lookup": {},
    }
    payload["standup_brief_scoped"]["24h"] = scoped_24h
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&window=24h&date=live&scope={scope_value}",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _wait_for_shell_query_param(page, tab="compass", key="scope", value=scope_value)
                page.wait_for_function(
                    """({ windowToken, scopeLabel }) => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const target = doc && doc.querySelector("#digest-list");
                        if (!target || !target.dataset) return false;
                        return (target.dataset.briefStatus || "") === "ready"
                          && (target.dataset.briefWindow || "") === windowToken
                          && (target.dataset.briefScope || "") === scopeLabel
                          && (target.dataset.briefHasNotice || "") === "true";
                    }""",
                    arg={"windowToken": "24h", "scopeLabel": scope_value},
                    timeout=15000,
                )
                scoped_meta = _compass_brief_metadata(compass)
                assert scoped_meta["status"] == "ready"
                assert scoped_meta["source"] in {"provider", "cache"}
                assert scoped_meta["hasNotice"] == "true"
                assert scoped_meta["noticeReason"] == "scoped_provider_deferred_showing_global"
                assert "Showing the global live brief" in compass.locator("#digest-list").inner_text()
                copy_state = compass.locator("#copy-brief").evaluate(
                    """(node) => ({
                        hidden: node.classList.contains("hidden"),
                        disabled: Boolean(node.disabled),
                    })"""
                )
                assert copy_state == {"hidden": False, "disabled": False}
                assert compass.locator(".borrowed-global-brief").count() == 0

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_scoped_provider_deferred_can_borrow_wider_global_live_brief(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    scoped_24h = (payload.get("standup_brief_scoped") or {}).get("24h")
    assert isinstance(scoped_24h, dict) and scoped_24h
    scope_value = next(iter(scoped_24h.keys()))
    payload["standup_brief"]["24h"] = {
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": "global-24h-credits",
        "generated_utc": "2026-04-10T22:10:00Z",
        "sections": [],
        "diagnostics": {
            "reason": "credits_exhausted",
            "title": "Brief is waiting on Codex CLI budget",
            "message": "Compass could not warm this brief because the last narration attempt through Codex CLI using gpt-5.3-codex-spark may have hit a credit or budget limit. It will retry on backoff.",
            "provider": "codex-cli",
            "provider_model": "gpt-5.3-codex-spark",
        },
        "evidence_lookup": {},
    }
    payload["standup_brief"]["48h"] = {
        "status": "ready",
        "source": "provider",
        "fingerprint": "global-live-48h",
        "generated_utc": "2026-04-10T22:15:00Z",
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [{"text": "A wider global brief is still available.", "fact_ids": []}],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "bullets": [{"text": "The 48-hour summary is the safe fallback here.", "fact_ids": []}],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "bullets": [{"text": "Let the narrow scoped lane catch back up.", "fact_ids": []}],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "bullets": [{"text": "The narrower 24-hour narration is still budget constrained.", "fact_ids": []}],
            },
        ],
        "evidence_lookup": {},
    }
    scoped_24h[scope_value] = {
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": "scoped-provider-deferred",
        "generated_utc": "",
        "sections": [],
        "diagnostics": {
            "reason": "provider_deferred",
            "title": "Standup brief unavailable",
            "message": "Compass is still warming this scoped brief.",
        },
        "evidence_lookup": {},
    }
    payload["standup_brief_scoped"]["24h"] = scoped_24h
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&window=24h&date=live&scope={scope_value}",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _wait_for_shell_query_param(page, tab="compass", key="scope", value=scope_value)
                page.wait_for_function(
                    """({ windowToken, scopeLabel }) => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const target = doc && doc.querySelector("#digest-list");
                        if (!target || !target.dataset) return false;
                        return (target.dataset.briefStatus || "") === "ready"
                          && (target.dataset.briefWindow || "") === windowToken
                          && (target.dataset.briefScope || "") === scopeLabel
                          && (target.dataset.briefHasNotice || "") === "true";
                    }""",
                    arg={"windowToken": "24h", "scopeLabel": scope_value},
                    timeout=15000,
                )
                scoped_meta = _compass_brief_metadata(compass)
                assert scoped_meta["status"] == "ready"
                assert scoped_meta["source"] in {"provider", "cache"}
                assert scoped_meta["hasNotice"] == "true"
                assert scoped_meta["noticeReason"] == "scoped_provider_deferred_showing_wider_global"
                assert "48-hour global live brief" in compass.locator("#digest-list").inner_text()

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_casebook_detail_stacks_cleanly_in_compact_viewport(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)

    first_bug = casebook.locator("button.bug-row").first
    bug_route = str(first_bug.get_attribute("data-bug") or "").strip()
    bug_title = first_bug.locator(".bug-row-title").inner_text().strip()
    assert bug_route
    assert bug_title

    first_bug.click()
    _wait_for_shell_query_param(page, tab="casebook", key="bug", value=bug_route)
    casebook.locator("#detailPane .detail-title", has_text=bug_title).wait_for(timeout=15000)
    casebook.locator("#detailPane .detail-section-human").wait_for(timeout=15000)
    casebook.locator("#detailPane .detail-section-agent").wait_for(timeout=15000)

    layout = casebook.locator("#detailPane").evaluate(
        """(node) => {
            const human = node.querySelector('.detail-section-human');
            const agent = node.querySelector('.detail-section-agent');
            const humanBox = human ? human.getBoundingClientRect() : null;
            const agentBox = agent ? agent.getBoundingClientRect() : null;
            return {
              clientWidth: node.clientWidth,
              scrollWidth: node.scrollWidth,
              humanTop: humanBox ? humanBox.top : 0,
              humanBottom: humanBox ? humanBox.bottom : 0,
              agentTop: agentBox ? agentBox.top : 0,
              briefCardCount: node.querySelectorAll('.brief-card').length,
              agentBlockCount: node.querySelectorAll('.agent-band-block').length,
            };
        }"""
    )
    assert layout["briefCardCount"] >= 1
    assert layout["agentBlockCount"] >= 1
    assert layout["scrollWidth"] - layout["clientWidth"] <= 16
    assert layout["agentTop"] >= layout["humanBottom"] - 2

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_live_window_anchors_to_loaded_snapshot_time(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    history_dir = fixture_root / "odylith" / "compass" / "runtime" / "history"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    event = dict((payload.get("timeline_events") or [])[0])
    event["id"] = "stale-anchor:event"
    event["kind"] = "implementation"
    event["summary"] = "Stale-anchor implementation event."
    event["ts_iso"] = "2020-01-02T08:45:00-08:00"
    event["author"] = "assistant"
    event["files"] = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js"]
    event["workstreams"] = []

    transaction = dict((payload.get("timeline_transactions") or [])[0])
    transaction["id"] = "stale-anchor:tx"
    transaction["transaction_id"] = "stale-anchor:tx"
    transaction["headline"] = "Stale-anchor transaction"
    transaction["start_ts_iso"] = "2020-01-02T08:00:00-08:00"
    transaction["end_ts_iso"] = "2020-01-02T08:45:00-08:00"
    transaction["event_count"] = 1
    transaction["files_count"] = 1
    transaction["files"] = list(event["files"])
    transaction["workstreams"] = []
    transaction["events"] = [event]

    payload["generated_utc"] = "2020-01-02T16:45:00Z"
    payload["now_local_iso"] = "2020-01-02T08:45:00-08:00"
    payload["timeline_events"] = [event]
    payload["timeline_transactions"] = [transaction]
    history = payload.get("history") if isinstance(payload.get("history"), dict) else {}
    history["dates"] = ["2020-01-02", "2020-01-01", "2019-12-31"]
    history["restored_dates"] = []
    payload["history"] = history

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    for token in ("2020-01-01", "2019-12-31"):
        snapshot = dict(payload)
        snapshot["timeline_events"] = []
        snapshot["timeline_transactions"] = []
        snapshot["history"] = {
            "retention_days": 15,
            "dates": ["2020-01-02", "2020-01-01", "2019-12-31"],
            "restored_dates": [],
            "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
        }
        (history_dir / f"{token}.v1.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=48h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                page.wait_for_function(
                    """() => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const banner = doc && doc.querySelector("#status-banner");
                        return Boolean(
                          banner
                          && !banner.classList.contains("hidden")
                          && (banner.textContent || "").includes("Compass snapshot")
                        );
                    }""",
                    timeout=15000,
                )
                assert "ask agent `Refresh Compass runtime for this repo.`" in compass.locator("#status-banner").inner_text()
                assert compass.locator("#status-banner").evaluate("node => getComputedStyle(node).whiteSpace") == "nowrap"
                assert compass.locator("#timeline").evaluate("node => getComputedStyle(node).minHeight") == "0px"
                assert compass.locator("#timeline").evaluate("node => getComputedStyle(node).alignContent") == "start"
                assert compass.locator("#timeline .timeline-day").first.evaluate("node => getComputedStyle(node).alignContent") == "start"
                compass.locator("#timeline .tx-headline", has_text="Stale-anchor implementation event.").wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text="2020-01-02").wait_for(timeout=15000)
                compass.locator("#timeline .empty", has_text="No audit events in this scope and window.").wait_for(state="detached", timeout=15000)

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_legacy_archived_timeline_day_is_ignored(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    history_dir = runtime_dir / "history"
    archive_dir = history_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    history_js_path = history_dir / "embedded.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    archived_day = "2026-04-04"
    live_day = "2026-04-05"
    files = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js"]

    archived_event = dict((payload.get("timeline_events") or [])[0])
    archived_event["id"] = "archived:event"
    archived_event["kind"] = "implementation"
    archived_event["summary"] = "Archived Compass timeline event."
    archived_event["ts_iso"] = "2026-04-04T11:20:00-07:00"
    archived_event["author"] = "assistant"
    archived_event["files"] = list(files)
    archived_event["workstreams"] = []

    archived_tx = dict((payload.get("timeline_transactions") or [])[0])
    archived_tx["id"] = "archived:tx"
    archived_tx["transaction_id"] = "archived:tx"
    archived_tx["headline"] = "Archived Compass timeline transaction"
    archived_tx["start_ts_iso"] = "2026-04-04T11:00:00-07:00"
    archived_tx["end_ts_iso"] = "2026-04-04T11:20:00-07:00"
    archived_tx["event_count"] = 1
    archived_tx["files_count"] = len(files)
    archived_tx["files"] = list(files)
    archived_tx["workstreams"] = []
    archived_tx["events"] = [archived_event]

    live_payload = dict(payload)
    live_payload["generated_utc"] = "2026-04-05T20:20:00Z"
    live_payload["now_local_iso"] = "2026-04-05T13:20:00-07:00"
    live_payload["history"] = {
        "retention_days": 1,
        "dates": [live_day],
        "restored_dates": [],
        "archive": {
            "compressed": True,
            "path": "archive",
            "count": 1,
            "dates": [archived_day],
            "newest_date": archived_day,
            "oldest_date": archived_day,
        },
    }

    archived_payload = dict(payload)
    archived_payload["generated_utc"] = "2026-04-04T18:20:00Z"
    archived_payload["now_local_iso"] = "2026-04-04T11:20:00-07:00"
    archived_payload["timeline_events"] = [archived_event]
    archived_payload["timeline_transactions"] = [archived_tx]
    archived_payload["history"] = dict(live_payload["history"])

    runtime_json_path.write_text(json.dumps(live_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(live_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    (archive_dir / f"{archived_day}.v1.json.gz").write_bytes(
        gzip.compress((json.dumps(archived_payload, indent=2) + "\n").encode("utf-8"), compresslevel=9)
    )
    history_js_path.write_text(
        "window.__ODYLITH_COMPASS_HISTORY__ = " + json.dumps(
            {
                "version": "v1",
                "generated_utc": live_payload["generated_utc"],
                "retention_days": 1,
                "dates": [archived_day],
                "restored_dates": [],
                "archive": live_payload["history"]["archive"],
                "snapshots": {
                    archived_day: archived_payload,
                },
            },
            separators=(",", ":"),
        ) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&window=24h&date={archived_day}",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                page.wait_for_function(
                    """() => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        if (!doc) return false;
                        return doc.querySelectorAll("#timeline .tx-card, #timeline .empty, #timeline .timeline-day-title, #timeline .hour-empty").length > 0;
                    }""",
                    timeout=15000,
                )
                compass.locator("#status-banner").wait_for(timeout=15000)
                assert "No snapshot available for this day" in compass.locator("#status-banner").inner_text().strip()
                assert compass.locator("#timeline .tx-headline", has_text=archived_tx["headline"]).count() == 0

                assert not [
                    entry for entry in failed_requests
                    if entry.endswith(f"/odylith/compass/runtime/history/{archived_day}.v1.json")
                ]
                assert not [
                    entry for entry in bad_responses
                    if entry.endswith(f"/odylith/compass/runtime/history/{archived_day}.v1.json")
                ]
                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_timeline_mixed_local_batch_falls_back_to_transaction_headline(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    source_truth_path = fixture_root / "odylith" / "compass" / "compass-source-truth.v1.json"
    traceability_path = fixture_root / "odylith" / "radar" / "traceability-graph.v1.json"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    scope_id = "B-020"
    scope_row = dict((payload.get("current_workstreams") or [])[0])
    scope_row["idea_id"] = scope_id
    scope_row["status"] = "implementation"
    scope_row["title"] = "Timeline audit headline trust"
    payload["current_workstreams"] = [scope_row]

    files = [
        "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
        "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js",
        "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-surface.v1.css",
        "tests/integration/runtime/test_surface_browser_deep.py",
    ]
    event_specs = (
        ("mixed-local:event:1", "Modified src/odylith/runtime/evaluation/odylith_benchmark_runner.py", "2026-04-02T13:59:34-07:00", files[0]),
        ("mixed-local:event:2", "Modified src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js", "2026-04-02T13:59:44-07:00", files[1]),
        ("mixed-local:event:3", "Modified src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-surface.v1.css", "2026-04-02T13:59:52-07:00", files[2]),
        ("mixed-local:event:4", "Modified tests/integration/runtime/test_surface_browser_deep.py", "2026-04-02T14:00:05-07:00", files[3]),
    )
    events = []
    base_event = dict((payload.get("timeline_events") or [])[0])
    for event_id, summary, ts_iso, file_path in event_specs:
        event = dict(base_event)
        event["id"] = event_id
        event["kind"] = "local_change"
        event["summary"] = summary
        event["ts_iso"] = ts_iso
        event["author"] = "local"
        event["files"] = [file_path]
        event["workstreams"] = [scope_id]
        events.append(event)

    transaction = dict((payload.get("timeline_transactions") or [])[0])
    transaction["id"] = "mixed-local:tx"
    transaction["transaction_id"] = "mixed-local:tx"
    transaction["headline"] = "Updated product code + integration tests for B-020"
    transaction["start_ts_iso"] = "2026-04-02T13:59:34-07:00"
    transaction["end_ts_iso"] = "2026-04-02T14:00:05-07:00"
    transaction["event_count"] = len(events)
    transaction["files_count"] = len(files)
    transaction["files"] = list(files)
    transaction["workstreams"] = [scope_id]
    transaction["events"] = list(reversed(events))

    payload["generated_utc"] = "2026-04-02T21:00:22Z"
    payload["now_local_iso"] = "2026-04-02T14:00:22-07:00"
    payload["timeline_events"] = list(reversed(events))
    payload["timeline_transactions"] = [transaction]
    payload["history"] = {
        "retention_days": 15,
        "dates": ["2026-04-02"],
        "restored_dates": [],
        "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
    }

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#timeline .tx-headline", has_text=transaction["headline"]).wait_for(timeout=15000)
                timeline_text = compass.locator("#timeline").inner_text()
                assert "Advanced shared infra and env-manifest wiring in the latest audit." not in timeline_text
                assert "Reworked Compass's inline audit narrative." not in timeline_text

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_timeline_transaction_chips_keep_checkpoint_anchor_workstream(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    event = {
        "id": "checkpoint-anchor:event",
        "kind": "implementation",
        "summary": (
            "Captured B-071 checkpoint: completed Compass quiet-scope failures "
            "were not just Compass bugs; they exposed a broader product problem."
        ),
        "context": "",
        "ts": dt.datetime.fromisoformat("2026-04-09T18:48:00-07:00"),
        "ts_iso": "2026-04-09T18:48:00-07:00",
        "author": "local",
        "files": ["src/odylith/runtime/governance/delivery/scope_signal_ladder.py"],
        "workstreams": ["B-001", "B-003", "B-004", "B-025", "B-027"],
        "source": "local",
        "session_id": "",
        "transaction_id": "",
        "transaction_seq": 0,
        "transaction_boundary": "",
        "headline_hint": "",
    }
    transaction = compass_transaction_runtime._build_prompt_transactions(events=[event])[0]

    payload["generated_utc"] = "2026-04-10T01:48:30Z"
    payload["now_local_iso"] = "2026-04-09T18:48:30-07:00"
    payload["timeline_events"] = list(transaction.get("events") or [])
    payload["timeline_transactions"] = [transaction]
    payload["history"] = {
        "retention_days": 15,
        "dates": ["2026-04-09"],
        "restored_dates": [],
        "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
    }

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=48h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                tx_card = compass.locator("#timeline .tx-card").first
                tx_card.locator(".tx-headline", has_text="Captured B-071 checkpoint").wait_for(timeout=15000)
                chip_labels = tx_card.locator(".chips a").evaluate_all(
                    "nodes => nodes.map(node => String(node.textContent || '').trim()).filter(Boolean)"
                )
                assert "B-071" in chip_labels

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_scoped_live_view_prefers_latest_non_empty_audit_day(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    source_truth_path = fixture_root / "odylith" / "compass" / "compass-source-truth.v1.json"
    traceability_path = fixture_root / "odylith" / "radar" / "traceability-graph.v1.json"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    scope_id = "B-777"
    scope_row = dict((payload.get("current_workstreams") or [])[0])
    scope_row["idea_id"] = scope_id
    scope_row["status"] = "implementation"
    scope_row["title"] = "Scoped audit-day fallback regression"
    payload["current_workstreams"] = [scope_row]
    payload["workstream_catalog"] = [scope_row]

    event = dict((payload.get("timeline_events") or [])[0])
    event["id"] = "scoped-fallback:event"
    event["kind"] = "implementation"
    event["summary"] = "Scoped fallback implementation event."
    event["ts_iso"] = "2026-04-01T10:15:00-07:00"
    event["author"] = "assistant"
    event["workstreams"] = [scope_id]
    event["files"] = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js"]

    transaction = dict((payload.get("timeline_transactions") or [])[0])
    transaction["id"] = "scoped-fallback:tx"
    transaction["transaction_id"] = "scoped-fallback:tx"
    transaction["headline"] = "Scoped fallback transaction"
    transaction["start_ts_iso"] = "2026-04-01T10:00:00-07:00"
    transaction["end_ts_iso"] = "2026-04-01T10:15:00-07:00"
    transaction["event_count"] = 1
    transaction["files_count"] = 1
    transaction["files"] = list(event["files"])
    transaction["workstreams"] = [scope_id]
    transaction["events"] = [event]

    payload["generated_utc"] = "2026-04-02T19:13:23Z"
    payload["now_local_iso"] = "2026-04-02T12:13:23-07:00"
    payload["timeline_events"] = [event]
    payload["timeline_transactions"] = [transaction]
    payload["verified_scoped_workstreams"] = {
        "24h": [scope_id],
        "48h": [scope_id],
    }
    payload["promoted_scoped_workstreams"] = {
        "24h": [scope_id],
        "48h": [scope_id],
    }
    payload["window_scope_signals"] = {
        "24h": {scope_id: {"promoted_default": True, "budget_class": "primary"}},
        "48h": {scope_id: {"promoted_default": True, "budget_class": "primary"}},
    }
    payload["history"] = {
        "retention_days": 15,
        "dates": ["2026-04-02", "2026-04-01"],
        "restored_dates": [],
        "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
    }

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    source_truth_path.unlink(missing_ok=True)
    traceability_payload = json.loads(traceability_path.read_text(encoding="utf-8"))
    traceability_payload["generated_utc"] = "2026-04-01T00:00:00Z"
    traceability_path.write_text(json.dumps(traceability_payload, indent=2) + "\n", encoding="utf-8")

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&scope={scope_id}&window=48h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#scope-pill", has_text=scope_id).wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text="2026-04-01").wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text="2026-04-02").wait_for(state="detached", timeout=15000)
                compass.locator("#timeline", has_text="Scoped fallback implementation event.").wait_for(timeout=15000)

                console_errors[:] = [row for row in console_errors if "compass-source-truth.v1.json" not in row]
                console_errors[:] = [row for row in console_errors if "404 (File not found)" not in row]
                bad_responses[:] = [row for row in bad_responses if "compass-source-truth.v1.json" not in row]
                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_live_timeline_keeps_prior_window_day_while_hiding_future_hours(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    previous_day = "2026-04-04"
    current_day = "2026-04-05"
    files = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js"]

    event = dict((payload.get("timeline_events") or [0])[0] if (payload.get("timeline_events") or []) else {})
    if not event:
        event = {"id": "", "kind": "", "summary": "", "ts_iso": "", "author": "", "files": [], "workstreams": []}
    event["id"] = "live-horizon:event"
    event["kind"] = "implementation"
    event["summary"] = "Live current-day hour horizon event."
    event["ts_iso"] = "2026-04-05T00:29:00-07:00"
    event["author"] = "assistant"
    event["files"] = list(files)
    event["workstreams"] = ["B-004"]

    previous_event = dict(event)
    previous_event["id"] = "live-horizon:previous-event"
    previous_event["summary"] = "Live prior-day window event."
    previous_event["ts_iso"] = "2026-04-04T23:41:00-07:00"

    transaction = dict((payload.get("timeline_transactions") or [0])[0] if (payload.get("timeline_transactions") or []) else {})
    if not transaction:
        transaction = {
            "id": "",
            "transaction_id": "",
            "headline": "",
            "start_ts_iso": "",
            "end_ts_iso": "",
            "event_count": 0,
            "files_count": 0,
            "files": [],
            "workstreams": [],
            "events": [],
        }
    transaction["id"] = "live-horizon:tx"
    transaction["transaction_id"] = "live-horizon:tx"
    transaction["headline"] = "Live current-day Compass horizon transaction"
    transaction["start_ts_iso"] = "2026-04-05T00:17:00-07:00"
    transaction["end_ts_iso"] = "2026-04-05T00:29:00-07:00"
    transaction["event_count"] = 1
    transaction["files_count"] = len(files)
    transaction["files"] = list(files)
    transaction["workstreams"] = ["B-004"]
    transaction["events"] = [event]

    previous_transaction = dict(transaction)
    previous_transaction["id"] = "live-horizon:previous-tx"
    previous_transaction["transaction_id"] = "live-horizon:previous-tx"
    previous_transaction["headline"] = "Live prior-day Compass window transaction"
    previous_transaction["start_ts_iso"] = "2026-04-04T23:33:00-07:00"
    previous_transaction["end_ts_iso"] = "2026-04-04T23:41:00-07:00"
    previous_transaction["events"] = [previous_event]

    payload["generated_utc"] = "2026-04-05T07:29:00Z"
    payload["now_local_iso"] = "2026-04-05T00:29:00-07:00"
    payload["timeline_events"] = [event, previous_event]
    payload["timeline_transactions"] = [transaction, previous_transaction]
    payload["history"] = {
        "retention_days": 15,
        "dates": [current_day, previous_day],
        "restored_dates": [],
        "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
    }

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&window=48h&date=live&audit_day={current_day}",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text=current_day).wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text=previous_day).wait_for(timeout=15000)
                page.wait_for_function(
                    """({ currentDay, previousDay }) => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        if (!doc) return false;
                        const sections = Array.from(doc.querySelectorAll("#timeline .timeline-day"));
                        const findSection = (token) => sections.find((section) => {
                            const title = section.querySelector(".timeline-day-title");
                            return Boolean(title) && (title.textContent || "").includes(token);
                        });
                        const current = findSection(currentDay);
                        const previous = findSection(previousDay);
                        if (!current || !previous) return false;
                        const currentLabels = Array.from(current.querySelectorAll(".hour-label")).map((node) => (node.textContent || "").trim());
                        const previousLabels = Array.from(previous.querySelectorAll(".hour-label")).map((node) => (node.textContent || "").trim());
                        return currentLabels.includes("00:00")
                          && !currentLabels.includes("01:00")
                          && previousLabels.includes("23:00");
                    }""",
                    arg={"currentDay": current_day, "previousDay": previous_day},
                    timeout=15000,
                )
                compass.locator("#timeline", has_text=event["summary"]).wait_for(timeout=15000)
                compass.locator("#timeline", has_text=previous_event["summary"]).wait_for(timeout=15000)

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_reload_prefers_fresher_runtime_json_over_stale_preloaded_js(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    compass_tz = ZoneInfo("America/Los_Angeles")
    now_utc = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0)
    old_utc = now_utc - dt.timedelta(hours=4)
    fresh_local = now_utc.astimezone(compass_tz)
    old_local = old_utc.astimezone(compass_tz)
    day_token = fresh_local.date().isoformat()

    base_event = dict((payload.get("timeline_events") or [])[0])
    base_transaction = dict((payload.get("timeline_transactions") or [])[0])
    files = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js"]

    def _payload_variant(*, label: str, event_time: dt.datetime, generated_time: dt.datetime) -> dict[str, object]:
        event = dict(base_event)
        event["id"] = f"{label}:event"
        event["kind"] = "implementation"
        event["summary"] = f"{label} Compass runtime event."
        event["ts_iso"] = event_time.isoformat()
        event["author"] = "assistant"
        event["files"] = list(files)
        event["workstreams"] = []

        transaction = dict(base_transaction)
        transaction["id"] = f"{label}:tx"
        transaction["transaction_id"] = f"{label}:tx"
        transaction["headline"] = f"{label} Compass runtime transaction"
        transaction["start_ts_iso"] = (event_time - dt.timedelta(minutes=10)).isoformat()
        transaction["end_ts_iso"] = event_time.isoformat()
        transaction["event_count"] = 1
        transaction["files_count"] = len(files)
        transaction["files"] = list(files)
        transaction["workstreams"] = []
        transaction["events"] = [event]

        variant = dict(payload)
        variant["generated_utc"] = generated_time.isoformat().replace("+00:00", "Z")
        variant["now_local_iso"] = generated_time.astimezone(compass_tz).isoformat()
        variant["timeline_events"] = [event]
        variant["timeline_transactions"] = [transaction]
        variant["history"] = {
            "retention_days": 15,
            "dates": [day_token],
            "restored_dates": [],
            "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
        }
        return variant

    stale_payload = _payload_variant(label="Stale JS", event_time=old_local, generated_time=old_utc)
    fresh_payload = _payload_variant(label="Fresh JSON", event_time=fresh_local, generated_time=now_utc)

    runtime_json_path.write_text(json.dumps(stale_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(stale_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#timeline", has_text="Stale JS Compass runtime event.").wait_for(timeout=15000)

                runtime_json_path.write_text(json.dumps(fresh_payload, indent=2) + "\n", encoding="utf-8")

                page.reload(wait_until="domcontentloaded")
                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#timeline", has_text="Fresh JSON Compass runtime event.").wait_for(timeout=15000)
                compass.locator("#timeline", has_text="Stale JS Compass runtime event.").wait_for(state="detached", timeout=15000)
                page.wait_for_function(
                    """() => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const banner = doc && doc.querySelector("#status-banner");
                        return Boolean(banner && (banner.classList.contains("hidden") || !(banner.textContent || "").includes("Compass snapshot")));
                    }""",
                    timeout=15000,
                )

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_reconciles_release_targets_from_live_traceability_when_runtime_snapshot_is_stale(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    traceability_path = fixture_root / "odylith" / "radar" / "traceability-graph.v1.json"
    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    source_truth_path = fixture_root / "odylith" / "compass" / "compass-source-truth.v1.json"

    traceability_payload = json.loads(traceability_path.read_text(encoding="utf-8"))
    traceability_payload["generated_utc"] = "2026-04-10T12:00:00Z"
    for release in traceability_payload.get("releases", []):
        if str(release.get("release_id", "")).strip() != "release-0-1-11":
            continue
        release["active_workstreams"] = ["B-068"]
        release["completed_workstreams"] = ["B-061", "B-062", "B-063", "B-067"]
    if isinstance(traceability_payload.get("current_release"), dict):
        traceability_payload["current_release"]["active_workstreams"] = ["B-068"]
        traceability_payload["current_release"]["completed_workstreams"] = ["B-061", "B-062", "B-063", "B-067"]
    for row in traceability_payload.get("workstreams", []):
        idea_id = str(row.get("idea_id", "")).strip()
        if idea_id == "B-067":
            row["status"] = "finished"
            row["active_release_id"] = ""
            row["active_release"] = {}
            row["release_history_summary"] = "Removed from 0.1.11"
        if idea_id == "B-068":
            row["status"] = "implementation"
            row["active_release_id"] = "release-0-1-11"
            row["active_release"] = {
                "release_id": "release-0-1-11",
                "status": "active",
                "version": "0.1.11",
                "tag": "v0.1.11",
                "display_label": "0.1.11",
                "aliases": ["current"],
                "active_workstreams": ["B-068"],
                "completed_workstreams": ["B-061", "B-062", "B-063", "B-067"],
            }
            row["release_history_summary"] = "Active: 0.1.11 · Added to 0.1.11"
    traceability_path.write_text(json.dumps(traceability_payload, indent=2) + "\n", encoding="utf-8")

    assert render_compass_dashboard.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/compass/compass.html",
        ]
    ) == 0
    assert tooling_dashboard_renderer.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/index.html",
        ]
    ) == 0
    runtime_payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    runtime_payload["release_summary"] = {
        "catalog": [
            {
                "release_id": "release-0-1-11",
                "display_label": "0.1.11",
                "status": "active",
                "aliases": ["current"],
                "active_workstreams": ["B-067"],
                "completed_workstreams": ["B-061", "B-062", "B-063"],
            }
        ],
        "current_release": {
            "release_id": "release-0-1-11",
            "display_label": "0.1.11",
            "status": "active",
            "aliases": ["current"],
            "active_workstreams": ["B-067"],
            "completed_workstreams": ["B-061", "B-062", "B-063"],
        },
        "next_release": {},
        "summary": {"active_assignment_count": 1},
    }
    runtime_payload["current_workstreams"] = [
        {
            "idea_id": "B-067",
            "title": "Context Engine Module Decomposition and Boundary Hardening",
            "status": "implementation",
            "release": {
                "release_id": "release-0-1-11",
                "display_label": "0.1.11",
                "aliases": ["current"],
                "active_workstreams": ["B-067"],
                "completed_workstreams": ["B-061", "B-062", "B-063"],
            },
            "release_history_summary": "Active: 0.1.11 · Added to 0.1.11",
            "plan": {"progress_ratio": 0.0},
        }
    ]
    runtime_payload["workstream_catalog"] = list(runtime_payload["current_workstreams"])
    runtime_payload["generated_utc"] = "2026-04-09T12:00:00Z"
    runtime_json_path.write_text(json.dumps(runtime_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(runtime_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    source_truth_path.unlink(missing_ok=True)

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#status-banner").wait_for(timeout=15000)
                banner_text = compass.locator("#status-banner").inner_text().strip()
                assert "Release truth for 0.1.11 now targets B-068" in banner_text
                assert "B-067" in banner_text

                release_section = compass.locator("#release-groups details.execution-wave-section").filter(
                    has=compass.locator(".execution-wave-section-title", has_text="0.1.11")
                ).first
                release_section.wait_for(timeout=15000)
                if release_section.get_attribute("open") is None:
                    release_section.locator("summary").first.click()
                release_section.locator(".execution-wave-panel").first.wait_for(timeout=15000)
                release_text = release_section.inner_text().strip()
                assert "B-068" in release_text
                assert "B-067" in release_text
                b068_card = compass.locator("#release-groups .execution-wave-card", has_text="B-068").first
                b068_card.wait_for(timeout=15000)
                b068_text = b068_card.inner_text().strip()
                assert "0% progress" not in b068_text

                console_errors[:] = [row for row in console_errors if "compass-source-truth.v1.json" not in row]
                console_errors[:] = [row for row in console_errors if "404 (File not found)" not in row]
                bad_responses[:] = [row for row in bad_responses if "compass-source-truth.v1.json" not in row]
                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_release_targets_show_checklist_label_instead_of_fake_zero_progress(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")
    _write_fixture_current_release_assignments(fixture_root, "B-068")
    _rewrite_fixture_workstream_status(fixture_root, idea_id="B-068", status="implementation")
    traceability_path = fixture_root / "odylith" / "radar" / "traceability-graph.v1.json"
    plan_path = (
        fixture_root
        / "odylith"
        / "technical-plans"
        / "done"
        / "2026-04"
        / "2026-04-08-odylith-context-engine-benchmark-family-and-grounding-quality-gates.md"
    )
    traceability_payload = json.loads(traceability_path.read_text(encoding="utf-8"))
    for release in traceability_payload.get("releases", []):
        if str(release.get("release_id", "")).strip() != "release-0-1-11":
            continue
        release["active_workstreams"] = ["B-068"]
        release["completed_workstreams"] = ["B-061", "B-062", "B-063", "B-067", "B-069"]
    if isinstance(traceability_payload.get("current_release"), dict):
        traceability_payload["current_release"]["active_workstreams"] = ["B-068"]
        traceability_payload["current_release"]["completed_workstreams"] = ["B-061", "B-062", "B-063", "B-067", "B-069"]
    for row in traceability_payload.get("workstreams", []):
        if str(row.get("idea_id", "")).strip() != "B-068":
            continue
        row["status"] = "implementation"
        row["active_release_id"] = "release-0-1-11"
        row["active_release"] = {
            "release_id": "release-0-1-11",
            "status": "active",
            "version": "0.1.11",
            "tag": "v0.1.11",
            "display_label": "0.1.11",
            "aliases": ["current"],
            "active_workstreams": ["B-068"],
            "completed_workstreams": ["B-061", "B-062", "B-063", "B-067", "B-069"],
        }
        row["release_history_summary"] = "Active: 0.1.11 · Added to 0.1.11"
    traceability_path.write_text(json.dumps(traceability_payload, indent=2) + "\n", encoding="utf-8")
    plan_path.write_text(
        plan_path.read_text(encoding="utf-8").replace("- [x]", "- [ ]"),
        encoding="utf-8",
    )

    assert render_compass_dashboard.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/compass/compass.html",
        ]
    ) == 0
    assert tooling_dashboard_renderer.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/index.html",
        ]
    ) == 0

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                release_section = compass.locator("#release-groups details.execution-wave-section").filter(
                    has=compass.locator(".execution-wave-section-title", has_text="0.1.11")
                ).first
                release_section.wait_for(timeout=15000)
                if release_section.get_attribute("open") is None:
                    release_section.locator("summary").first.click()
                release_section.locator(".execution-wave-panel").first.wait_for(timeout=15000)
                release_text = release_section.inner_text().strip()
                assert "B-068" in release_text
                b068_card = compass.locator("#release-groups .execution-wave-card", has_text="B-068").first
                b068_card.wait_for(timeout=15000)
                b068_text = b068_card.inner_text().strip()
                assert re.search(r"Checklist 0/\d+", b068_text)
                assert "0% progress" not in b068_text

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_release_targets_show_tracked_execution_percent_for_partial_progress(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")
    _write_fixture_current_release_assignments(fixture_root, "B-068")
    _rewrite_fixture_workstream_status(fixture_root, idea_id="B-068", status="implementation")
    traceability_path = fixture_root / "odylith" / "radar" / "traceability-graph.v1.json"
    plan_path = (
        fixture_root
        / "odylith"
        / "technical-plans"
        / "done"
        / "2026-04"
        / "2026-04-08-odylith-context-engine-benchmark-family-and-grounding-quality-gates.md"
    )
    traceability_payload = json.loads(traceability_path.read_text(encoding="utf-8"))
    for release in traceability_payload.get("releases", []):
        if str(release.get("release_id", "")).strip() != "release-0-1-11":
            continue
        release["active_workstreams"] = ["B-068"]
        release["completed_workstreams"] = ["B-061", "B-062", "B-063", "B-067", "B-069"]
    if isinstance(traceability_payload.get("current_release"), dict):
        traceability_payload["current_release"]["active_workstreams"] = ["B-068"]
        traceability_payload["current_release"]["completed_workstreams"] = ["B-061", "B-062", "B-063", "B-067", "B-069"]
    for row in traceability_payload.get("workstreams", []):
        if str(row.get("idea_id", "")).strip() != "B-068":
            continue
        row["status"] = "implementation"
        row["active_release_id"] = "release-0-1-11"
        row["active_release"] = {
            "release_id": "release-0-1-11",
            "status": "active",
            "version": "0.1.11",
            "tag": "v0.1.11",
            "display_label": "0.1.11",
            "aliases": ["current"],
            "active_workstreams": ["B-068"],
            "completed_workstreams": ["B-061", "B-062", "B-063", "B-067", "B-069"],
        }
        row["release_history_summary"] = "Active: 0.1.11 · Added to 0.1.11"
    traceability_path.write_text(json.dumps(traceability_payload, indent=2) + "\n", encoding="utf-8")
    plan_text = plan_path.read_text(encoding="utf-8")
    plan_text = plan_text.replace(
        "- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`",
        "- [ ] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`",
        1,
    )
    plan_text = plan_text.replace(
        "- [x] `git diff --check`",
        "- [ ] `git diff --check`",
        1,
    )
    plan_path.write_text(plan_text, encoding="utf-8")

    assert render_compass_dashboard.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/compass/compass.html",
        ]
    ) == 0
    assert tooling_dashboard_renderer.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/index.html",
        ]
    ) == 0

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                release_section = compass.locator("#release-groups details.execution-wave-section").filter(
                    has=compass.locator(".execution-wave-section-title", has_text="0.1.11")
                ).first
                release_section.wait_for(timeout=15000)
                if release_section.get_attribute("open") is None:
                    release_section.locator("summary").first.click()
                release_section.locator(".execution-wave-panel").first.wait_for(timeout=15000)
                release_text = release_section.inner_text().strip()
                assert "B-068" in release_text
                b068_card = compass.locator("#release-groups .execution-wave-card", has_text="B-068").first
                b068_card.wait_for(timeout=15000)
                b068_text = b068_card.inner_text().strip()
                assert re.search(r"\d+% progress", b068_text)
                assert "Checklist" not in b068_text

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()
