from __future__ import annotations

import json

from odylith.runtime.surfaces import compass_standup_brief_substrate as substrate


def _fact_packet(*, freshness_bucket: str = "recent") -> dict[str, object]:
    sections = [
        {
            "key": "completed",
            "label": "Completed in this window",
            "facts": [
                {
                    "id": "F-001",
                    "section_key": "completed",
                    "kind": "plan_completion",
                    "source": "plan",
                    "priority": 3,
                    "text": "Verified plan closeout landed.",
                    "workstreams": ["B-025"],
                }
            ],
        },
        {
            "key": "current_execution",
            "label": "Current execution",
            "facts": [
                {
                    "id": "F-002",
                    "section_key": "current_execution",
                    "kind": "direction",
                    "source": "execution_highlight",
                    "priority": 3,
                    "text": "Compass and browser proof are converging on the same live story.",
                    "workstreams": ["B-025"],
                },
                {
                    "id": "F-003",
                    "section_key": "current_execution",
                    "kind": "signal",
                    "source": "transaction_or_event",
                    "priority": 1,
                    "text": "A low-signal implementation note arrived.",
                    "workstreams": ["B-025"],
                },
                {
                    "id": "F-004",
                    "section_key": "current_execution",
                    "kind": "freshness",
                    "source": "freshness",
                    "priority": 1,
                    "text": f"Freshness bucket is {freshness_bucket} at 2026-04-10T20:00:00Z.",
                    "workstreams": ["B-025"],
                },
            ],
        },
        {
            "key": "next_planned",
            "label": "Next planned",
            "facts": [
                {
                    "id": "F-005",
                    "section_key": "next_planned",
                    "kind": "forcing_function",
                    "source": "plan",
                    "priority": 2,
                    "text": "Land the next verified runtime checkpoint.",
                    "workstreams": ["B-025"],
                }
            ],
        },
        {
            "key": "risks_to_watch",
            "label": "Risks to watch",
            "facts": [
                {
                    "id": "F-006",
                    "section_key": "risks_to_watch",
                    "kind": "risk_posture",
                    "source": "traceability_risk",
                    "priority": 2,
                    "text": "If Compass drifts again, the live brief loses trust quickly.",
                    "workstreams": ["B-025"],
                }
            ],
        },
    ]
    facts = [fact for section in sections for fact in section["facts"]]
    return {
        "version": "v1",
        "window": "24h",
        "scope": {
            "mode": "global",
            "idea_id": "",
            "label": "Global",
            "status": "",
        },
        "summary": {
            "window_hours": 24,
            "use_story": "Operators need Compass to sound grounded on first read.",
            "architecture_consequence": "Keeping the brief human lowers coordination risk.",
            "freshness": {
                "bucket": freshness_bucket,
                "latest_evidence_utc": "2026-04-10T20:00:00Z",
                "source": "transaction",
            },
            "storyline": {
                "direction": "Compass and browser proof are converging on the same live story.",
                "proof": "The runtime evidence is finally anchored to the same packet.",
                "forcing_function": "Land the next verified runtime checkpoint.",
                "use_story": "Operators need Compass to sound grounded on first read.",
                "architecture_consequence": "Keeping the brief human lowers coordination risk.",
                "watch_item": "If Compass drifts again, the live brief loses trust quickly.",
            },
            "self_host": {
                "repo_role": "product_repo",
                "posture": "pinned_release",
                "runtime_source": "pinned_runtime",
                "pinned_version": "0.1.10",
                "active_version": "0.1.10",
                "launcher_present": True,
                "release_eligible": True,
            },
        },
        "facts": facts,
        "sections": sections,
    }


def test_build_narration_substrate_caps_global_fact_budget() -> None:
    packet = _fact_packet()
    built = substrate.build_narration_substrate(
        fact_packet=packet,
        schema_version="v24",
    )

    assert built["budgets"]["total_fact_cap"] == substrate.GLOBAL_TOTAL_FACT_CAP
    assert built["budgets"]["selected_fact_count"] <= substrate.GLOBAL_TOTAL_FACT_CAP
    assert len(built["sections"][1]["facts"]) <= substrate.GLOBAL_SECTION_FACT_CAPS["current_execution"]


def test_narration_substrate_fingerprint_ignores_freshness_wording_and_timestamp_drift() -> None:
    baseline_packet = _fact_packet(freshness_bucket="recent")
    variant_packet = json.loads(json.dumps(baseline_packet))
    variant_packet["summary"]["freshness"]["latest_evidence_utc"] = "2026-04-10T21:00:00Z"
    variant_packet["sections"][1]["facts"][2]["text"] = "Freshness bucket is recent at 2026-04-10T21:00:00Z."

    baseline = substrate.build_narration_substrate(fact_packet=baseline_packet, schema_version="v24")
    variant = substrate.build_narration_substrate(fact_packet=variant_packet, schema_version="v24")

    assert baseline["fingerprint"] == variant["fingerprint"]


def test_worth_calling_provider_returns_false_for_freshness_only_change() -> None:
    baseline = substrate.build_narration_substrate(fact_packet=_fact_packet(freshness_bucket="recent"), schema_version="v24")
    changed = substrate.build_narration_substrate(fact_packet=_fact_packet(freshness_bucket="aging"), schema_version="v24")

    should_call, reason, delta = substrate.worth_calling_provider(current=changed, previous=baseline)

    assert should_call is False
    assert reason == "exact_substrate_match"
    assert delta["freshness_changed"] is True


def test_worth_calling_provider_returns_false_for_nonwinner_summary_churn() -> None:
    baseline_packet = _fact_packet()
    baseline_packet["summary"]["touched_workstreams"] = 3
    changed_packet = json.loads(json.dumps(baseline_packet))
    changed_packet["summary"]["touched_workstreams"] = 4

    baseline = substrate.build_narration_substrate(fact_packet=baseline_packet, schema_version="v24")
    changed = substrate.build_narration_substrate(fact_packet=changed_packet, schema_version="v24")

    should_call, reason, delta = substrate.worth_calling_provider(current=changed, previous=baseline)

    assert baseline["fingerprint"] != changed["fingerprint"]
    assert should_call is False
    assert reason == "no_winner_change"
    assert delta["changed_fact_keys"] == []


def test_worth_calling_provider_returns_true_when_winner_facts_change() -> None:
    baseline_packet = _fact_packet()
    changed_packet = json.loads(json.dumps(baseline_packet))
    changed_packet["sections"][1]["facts"][0]["text"] = "Compass and browser proof split again and need hard repair."
    changed_packet["facts"][1]["text"] = "Compass and browser proof split again and need hard repair."

    baseline = substrate.build_narration_substrate(fact_packet=baseline_packet, schema_version="v24")
    changed = substrate.build_narration_substrate(fact_packet=changed_packet, schema_version="v24")

    should_call, reason, delta = substrate.worth_calling_provider(current=changed, previous=baseline)

    assert should_call is True
    assert reason == "winner_facts_changed"
    assert delta["changed_fact_keys"]


def test_build_narration_substrate_trims_storyline_and_omits_healthy_self_host() -> None:
    built = substrate.build_narration_substrate(
        fact_packet=_fact_packet(),
        schema_version="v25",
    )

    storyline = built["summary"]["storyline"]

    assert "use_story" not in storyline
    assert "architecture_consequence" not in storyline
    assert "self_host" not in built["summary"]


def test_build_narration_substrate_penalizes_meta_current_execution_facts() -> None:
    packet = _fact_packet()
    packet["sections"][1]["facts"] = [
        {
            "id": "F-002",
            "section_key": "current_execution",
            "kind": "direction",
            "source": "workstream_metadata",
            "priority": 3,
            "text": "Claude parity is the flagship lane because Claude support is already part of the product claim.",
            "workstreams": ["B-083"],
        },
        {
            "id": "F-003",
            "section_key": "current_execution",
            "kind": "signal",
            "source": "transaction_or_event",
            "priority": 3,
            "text": "Claude repo-root guidance is now installed alongside AGENTS.md, so the first-run path finally matches the product promise.",
            "workstreams": ["B-083"],
        },
        {
            "id": "F-004",
            "section_key": "current_execution",
            "kind": "self_host_status",
            "source": "self_host",
            "priority": 3,
            "text": "Live self-host posture check passed: pinned runtime and repo pin are aligned.",
            "workstreams": ["B-083"],
        },
        {
            "id": "F-007",
            "section_key": "current_execution",
            "kind": "portfolio_posture",
            "source": "portfolio",
            "priority": 3,
            "text": "Planning and implementation are running in parallel across active lanes.",
            "workstreams": ["B-083", "B-025"],
        },
        {
            "id": "F-008",
            "section_key": "current_execution",
            "kind": "freshness",
            "source": "freshness",
            "priority": 3,
            "text": "Freshness bucket is stale at 2026-04-10T20:00:00Z.",
            "workstreams": ["B-083"],
        },
    ]
    packet["facts"] = [fact for section in packet["sections"] for fact in section["facts"]]
    packet["summary"]["freshness"]["bucket"] = "stale"

    built = substrate.build_narration_substrate(
        fact_packet=packet,
        schema_version="v25",
    )

    selected_kinds = [fact["kind"] for fact in built["sections"][1]["facts"]]

    assert "portfolio_posture" not in selected_kinds
    assert "self_host_status" not in selected_kinds
