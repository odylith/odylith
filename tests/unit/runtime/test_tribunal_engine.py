from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.governance import operator_readout
from odylith.runtime.reasoning import tribunal_engine


def _scope(
    *,
    scope_id: str,
    status: str,
    scenario: str = "unsafe_closeout",
    scope_type: str = "workstream",
    code_references: list[str] | None = None,
    linked_components: list[str] | None = None,
    linked_surfaces: list[str] | None = None,
    live_actionable: bool = True,
    render_drift: bool = False,
    evidence_refs: list[dict[str, str]] | None = None,
    proof_refs: list[dict[str, str]] | None = None,
    decision_debt: int = 80,
    governance_lag: int = 60,
    blast_radius_severity: int = 0,
    severity: str | None = None,
) -> dict[str, object]:
    return {
        "scope_key": f"{scope_type}:{scope_id}",
        "scope_type": scope_type,
        "scope_id": scope_id,
        "scope_label": f"Scope {scope_id}",
        "posture_mode": "closure_hardening",
        "trajectory": "stalled",
        "confidence": "High",
        "scores": {
            "decision_debt": decision_debt,
            "governance_lag": governance_lag,
            "blast_radius_severity": blast_radius_severity,
        },
        "explanation_facts": [f"{scope_id} has newer activity than the last explicit checkpoint."],
        "evidence_context": {
            "latest_event_ts_iso": "2026-03-07T10:17:57-08:00",
            "latest_explicit_ts_iso": "2026-03-01T21:38:40-08:00",
            "linked_workstreams": [scope_id],
            "linked_components": linked_components if linked_components is not None else ["odylith"],
            "linked_diagrams": ["D-010"],
            "linked_surfaces": linked_surfaces if linked_surfaces is not None else ["atlas", "dashboard", "radar"],
            "code_references": code_references if code_references is not None else ["src/odylith/runtime/surfaces/render_tooling_dashboard.py"],
            "changed_artifacts": ["odylith/index.html"],
        },
        "diagnostics": {
            "status": status,
            "idea_file": f"odylith/radar/source/ideas/2026-03/{scope_id.lower()}.md",
            "plan_path": f"odylith/technical-plans/in-progress/2026-03-07-{scope_id.lower()}.md",
            "live_actionable": live_actionable,
            "live_reason": "Clearance remains pending.",
            "render_drift": render_drift,
        },
        "operator_readout": {
            "primary_scenario": scenario,
            "secondary_scenarios": [],
            "severity": severity or ("blocker" if status == "finished" else "watch"),
            "issue": f"{scope_id} has stale closeout risk.",
            "why_hidden": "The newest activity outruns the last explicit checkpoint.",
            "action": f"Inspect {scope_id}.",
            "action_kind": "refresh_authority",
            "proof_refs": proof_refs
            or [
                operator_readout.build_proof_ref(
                    kind="workstream",
                    value=scope_id,
                    label=f"{scope_id} timeline audit",
                    surface="compass",
                    anchor="timeline-audit",
                )
            ],
            "requires_approval": True,
            "source": "deterministic",
        },
        "evidence_refs": evidence_refs or [],
    }


def _delivery_payload(*, scopes: list[dict[str, object]]) -> dict[str, object]:
    return {
        "version": "v4",
        "scopes": scopes,
    }


class _ProviderStub:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_finding(self, *, prompt_payload):  # noqa: ANN001
        self.calls.append(dict(prompt_payload))
        evidence_ids = [
            str(row.get("id", "")).strip()
            for row in prompt_payload.get("evidence_items", [])
            if isinstance(row, dict) and str(row.get("id", "")).strip()
        ]
        cited = evidence_ids[:2] or ["E1"]
        return {
            "leading_explanation": {"text": "Validated leading explanation.", "evidence_ids": cited},
            "strongest_rival": {"text": "Validated strongest rival.", "evidence_ids": cited},
            "risk_if_wrong": {"text": "Validated risk if wrong.", "evidence_ids": cited},
            "discriminating_next_check": {"text": "Validated next check.", "evidence_ids": cited},
            "maintainer_brief": {"text": "Validated maintainer brief.", "evidence_ids": cited},
        }


class _TimeoutProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.last_failure_code = ""
        self.last_failure_detail = ""

    def generate_finding(self, *, prompt_payload):  # noqa: ANN001
        _ = prompt_payload
        self.calls += 1
        self.last_failure_code = "timeout"
        self.last_failure_detail = "Codex CLI exceeded 20.0s."
        return None


def test_build_tribunal_payload_assigns_expected_special_case_headlines(tmp_path: Path) -> None:
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(scope_id="B-033", status="finished"),
                _scope(
                    scope_id="B-037",
                    status="implementation",
                    code_references=[],
                    linked_components=["atlas", "compass", "dashboard", "radar", "registry", "odylith"],
                    linked_surfaces=["atlas", "compass", "radar", "registry", "odylith"],
                ),
                _scope(
                    scope_id="B-061",
                    status="implementation",
                    code_references=["src/odylith/runtime/reasoning/odylith_reasoning.py"],
                ),
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
    )

    headlines = {row["scope_id"]: row["headline"] for row in payload["case_queue"]}
    assert headlines["B-033"] == "Decide whether this belongs to successor work"
    assert headlines["B-037"] == "Cross-surface ownership is not proven yet"
    assert "moving the evaluator" in headlines["B-061"]
    assert payload["systemic_brief"]["headline"]


def test_build_tribunal_payload_provider_prompt_receives_full_actor_roster(tmp_path: Path) -> None:
    provider = _ProviderStub()
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(
                    scope_id="B-037",
                    status="implementation",
                    code_references=[
                        "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                        "src/odylith/runtime/governance/sync_workstream_artifacts.py",
                    ],
                    linked_components=["atlas", "compass", "dashboard", "radar", "registry", "odylith"],
                    linked_surfaces=["atlas", "compass", "radar", "registry"],
                )
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
        config=SimpleNamespace(scope_cap=5, provider="codex-cli", model="Codex-Spark 5.3"),
        provider=provider,
    )

    assert payload["cases"]
    assert len(provider.calls) == 1
    assert {row["actor"] for row in provider.calls[0]["actor_memos"]} == {
        "observer",
        "ownership_resolver",
        "causal_analyst",
        "policy_judge",
        "normative_judge",
        "adversary",
        "counterfactual_analyst",
        "gap_analyst",
        "risk_analyst",
        "prescriber",
    }


def test_build_tribunal_payload_disables_provider_after_timeout_in_same_run(tmp_path: Path) -> None:
    provider = _TimeoutProvider()

    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(scope_id="B-101", status="implementation"),
                _scope(scope_id="B-102", status="implementation", scenario="orphan_activity"),
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
        config=SimpleNamespace(scope_cap=5, provider="codex-cli", model="gpt-5.4"),
        provider=provider,
    )

    assert provider.calls == 1
    assert payload["degraded_reason"] == "ai-provider-timeout"
    assert payload["provider_runtime_failure_code"] == "timeout"
    assert payload["cases"][0]["reasoning"]["provider_failure_code"] == "timeout"
    assert payload["cases"][1]["reasoning"]["provider_used"] is False
    assert payload["cases"][1]["reasoning"]["deterministic_reason"] == "provider unavailable"
    assert "earlier provider failure" in payload["cases"][1]["reasoning"]["deterministic_reason_detail"].lower()


def test_build_tribunal_payload_can_emit_insufficient_evidence_form(tmp_path: Path) -> None:
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(
                    scope_id="B-099",
                    status="implementation",
                    scenario="orphan_activity",
                    code_references=[],
                    linked_components=[],
                    linked_surfaces=[],
                )
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
    )

    assert payload["cases"][0]["adjudication"]["form"] == "insufficient_evidence"


def test_build_tribunal_payload_editor_brief_avoids_raw_paths(tmp_path: Path) -> None:
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(scope_id="B-033", status="finished"),
                _scope(
                    scope_id="B-061",
                    status="implementation",
                    code_references=["src/odylith/runtime/reasoning/odylith_reasoning.py"],
                ),
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
    )

    briefs = [str(case["maintainer_brief"]) for case in payload["cases"]]
    assert briefs
    assert all(not operator_readout.RAW_PATH_RE.search(brief) for brief in briefs)


def test_build_tribunal_payload_emits_actor_influence_telemetry(tmp_path: Path) -> None:
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(
                    scope_id="B-037",
                    status="implementation",
                    code_references=[
                        "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                        "src/odylith/runtime/governance/sync_workstream_artifacts.py",
                    ],
                    linked_components=["atlas", "compass", "dashboard", "radar", "registry", "odylith"],
                    linked_surfaces=["atlas", "compass", "radar", "registry"],
                )
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
    )

    case = payload["cases"][0]
    influence = case["reasoning"]["actor_influence"]
    assert influence["form"]["actors"] == [
        "observer",
        "ownership_resolver",
        "causal_analyst",
        "policy_judge",
        "normative_judge",
        "adversary",
        "counterfactual_analyst",
        "gap_analyst",
        "risk_analyst",
        "prescriber",
    ]
    assert influence["field_influencers"]["strongest_rival"] == ["adversary", "counterfactual_analyst"]
    assert influence["editor_output"]["actors"] == [
        "causal_analyst",
        "ownership_resolver",
        "adversary",
        "gap_analyst",
        "risk_analyst",
        "prescriber",
    ]


def test_build_tribunal_payload_finished_scope_brief_is_concise_and_no_template_leak(tmp_path: Path) -> None:
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(
                    scope_id="B-015",
                    status="finished",
                    linked_components=["atlas"],
                    linked_surfaces=["atlas", "radar", "compass"],
                )
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
    )

    brief = str(payload["cases"][0]["maintainer_brief"])
    assert "if rival else" not in brief
    assert "The strongest explanation is" not in brief
    assert "The strongest challenge is" not in brief
    assert "Risk if wrong:" not in brief
    assert "Do now:" not in brief
    assert "stayed closed" in brief
    assert "Strongest rival:" in brief
    assert "Use successor attribution" in brief


def test_build_tribunal_payload_without_owned_artifacts_stays_honest(tmp_path: Path) -> None:
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(
                    scope_id="B-015",
                    status="finished",
                    code_references=[],
                    linked_components=["atlas"],
                    linked_surfaces=["atlas", "radar", "compass"],
                )
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
    )

    case = payload["cases"][0]
    observations = case["dossier"]["observations"]
    assert observations["ownership_evidence_state"] == "insufficient"
    assert observations["semantic_diff_ready"] is False
    assert case["adjudication"]["form"] == "insufficient_evidence"
    assert "semantic diff against B-015's declared artifacts" not in case["adjudication"]["discriminating_next_check"]
    assert "Evidence is insufficient for semantic diff review" in case["adjudication"]["discriminating_next_check"]


def test_build_tribunal_payload_avoids_queue_trust_question_for_non_evaluator_finished_scope(tmp_path: Path) -> None:
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(
                    scope_id="B-041",
                    status="finished",
                    code_references=[
                        "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                        "src/odylith/runtime/surfaces/render_registry_dashboard.py",
                    ],
                    linked_components=["atlas", "registry", "odylith"],
                    linked_surfaces=["atlas", "compass", "radar", "registry"],
                )
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
    )

    decision = str(payload["case_queue"][0]["decision_at_stake"])
    assert not decision.startswith("Can Odylith's current queue be trusted")
    assert "reopened" in decision or "reopen" in decision


def test_build_tribunal_payload_semantic_review_question_mentions_latest_delta(tmp_path: Path) -> None:
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(
                    scope_id="B-037",
                    status="implementation",
                    code_references=[
                        "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                        "src/odylith/runtime/governance/sync_workstream_artifacts.py",
                    ],
                    linked_components=["atlas", "compass", "dashboard", "radar", "registry", "odylith"],
                    linked_surfaces=["atlas", "compass", "radar", "registry"],
                )
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
    )

    queue_row = payload["case_queue"][0]
    decision = str(queue_row["decision_at_stake"]).lower()
    assert "moving the evaluator" in str(queue_row["headline"]).lower()
    assert "latest" in decision or "newest" in decision
    assert "queue be trusted" not in decision


def test_build_tribunal_payload_keeps_proof_routes_surface_specific(tmp_path: Path) -> None:
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(
            scopes=[
                _scope(
                    scope_id="B-015",
                    status="finished",
                    evidence_refs=[
                        {"kind": "workstream", "value": "B-015", "label": "B-015"},
                        {"kind": "component", "value": "atlas", "label": "atlas"},
                    ],
                    proof_refs=[
                        operator_readout.build_proof_ref(
                            kind="workstream",
                            value="B-015",
                            label="B-015 timeline audit",
                            surface="compass",
                            anchor="timeline-audit",
                        ),
                        operator_readout.build_proof_ref(
                            kind="component",
                            value="component:atlas",
                            label="atlas forensic evidence",
                            surface="registry",
                            anchor="forensic-evidence",
                        ),
                    ],
                )
            ]
        ),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
    )

    queue_row = payload["case_queue"][0]
    assert queue_row["proof_routes"]
    assert all(str(row.get("surface", "")).strip() for row in queue_row["proof_routes"])
    assert queue_row["proof_routes"][0]["surface"] == "compass"
    assert all("surface" in row for row in queue_row["proof_routes"])


def test_build_tribunal_payload_ignores_cache_from_older_actor_policy_version(tmp_path: Path) -> None:
    previous_payload = {
        "actor_policy_version": "tribunal-v1",
        "cache": [
            {
                "scope_key": "workstream:B-033",
                "evidence_fingerprint": "stale",
                "case": {
                    "scope_key": "workstream:B-033",
                    "maintainer_brief": "stale cached brief",
                    "queue_row": {"brief": "stale cached brief"},
                },
            }
        ],
    }

    payload = tribunal_engine.build_tribunal_payload(
        repo_root=tmp_path,
        delivery_payload=_delivery_payload(scopes=[_scope(scope_id="B-033", status="finished")]),
        posture={"clearance": {"state": "pending"}, "policy": {"breaches": []}},
        previous_payload=previous_payload,
    )

    assert payload["stats"]["reused_count"] == 0
    assert payload["cases"][0]["maintainer_brief"] != "stale cached brief"


def test_candidate_scope_keys_skip_non_live_clear_path_and_unsupported_scope_types() -> None:
    clear_path_scope = _scope(scope_id="B-090", status="implementation", scenario="clear_path")
    non_live_scope = _scope(scope_id="B-091", status="implementation", live_actionable=False)
    unsupported_scope = _scope(scope_id="B-092", status="implementation", scope_type="surface")
    valid_scope = _scope(scope_id="B-093", status="implementation", scenario="orphan_activity")

    keys = tribunal_engine._candidate_scope_keys(  # noqa: SLF001
        _delivery_payload(scopes=[clear_path_scope, non_live_scope, unsupported_scope, valid_scope]),
        scope_cap=5,
    )

    assert keys == ["workstream:B-093"]
