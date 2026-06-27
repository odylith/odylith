from __future__ import annotations

from typing import Any

from odylith.runtime.reasoning.tribunal_patch_planner import (
    TRIBUNAL_PATCH_PLAN_VERSION,
    merge_patch_plan_into_request,
    plan_structured_patch,
    validate_structured_patch_plan,
)


def _patchset_request() -> dict[str, Any]:
    return {
        "version": "odylith.greenfield.post_confirm.patchset_request.v1",
        "status": "repairable",
        "operation_count": 1,
        "operations": [
            {
                "operation_id": "GF-PATCH-001",
                "target_layer": "semantic_model",
                "target_path": "semantic_model.first_path_contract",
                "semantic_node_id": "SemanticModelIR.first_path_contract",
                "issue_code": "semantic_alignment",
                "source_finding": "semantic_workstream_alignment",
                "affected_projections": ["radar", "project_brief"],
                "requested_action": "Return a semantic patch that corrects the accepted intent interpretation.",
                "replacement_fact": "",
                "decision_ledger_entry": "",
                "proof_obligation_delta": "",
                "rejected_interpretation": "first path omitted the user-visible result",
                "confidence": 0.2,
            }
        ],
    }


def _valid_plan_operation(**overrides: Any) -> dict[str, Any]:
    operation = {
        "operation_id": "GF-PATCH-001",
        "target_layer": "semantic_model",
        "target_path": "semantic_model.first_path_contract",
        "semantic_node_id": "SemanticModelIR.first_path_contract",
        "replacement_fact": {
            "actor": "accepted user",
            "action": "reviews",
            "object": "accepted state object",
            "visible_result": "accepted result is shown and saved",
        },
        "decision_ledger_entry": {
            "chosen_interpretation": "The first path is an end-to-end user action with a visible saved result.",
            "reason": "The accepted intent names review, state, and proof boundary as separate facts.",
        },
        "proof_obligation_delta": {"requires_visible_result": True},
        "rejected_interpretation": "first path is only a noun phrase",
        "confidence": 0.82,
    }
    operation.update(overrides)
    return operation


class _FakeProvider:
    provider_name = "fake-provider"
    last_failure_code = ""
    last_failure_detail = ""
    last_request_model = ""
    last_request_reasoning_effort = ""

    def __init__(self, payload: dict[str, Any] | None) -> None:
        self.payload = payload
        self.request = None

    def generate_structured(self, *, request: Any) -> dict[str, Any] | None:
        self.request = request
        self.last_request_model = request.model
        self.last_request_reasoning_effort = request.reasoning_effort
        return self.payload


def test_structured_patch_plan_preserves_request_custody_fields() -> None:
    patch_plan = validate_structured_patch_plan(
        {
            "version": TRIBUNAL_PATCH_PLAN_VERSION,
            "status": "planned",
            "decision_summary": "Repair the first path semantic fact.",
            "operations": [_valid_plan_operation()],
        },
        patchset_request=_patchset_request(),
    )

    assert patch_plan["status"] == "planned"
    assert patch_plan["operation_count"] == 1
    operation = patch_plan["operations"][0]
    assert operation["operation_id"] == "GF-PATCH-001"
    assert operation["target_layer"] == "semantic_model"
    assert operation["target_path"] == "semantic_model.first_path_contract"
    assert operation["semantic_node_id"] == "SemanticModelIR.first_path_contract"
    assert operation["affected_projections"] == ("radar", "project_brief")
    assert operation["replacement_fact"]["visible_result"] == "accepted result is shown and saved"
    assert not patch_plan["rejections"]


def test_structured_patch_plan_rejects_invented_or_moved_targets() -> None:
    patch_plan = validate_structured_patch_plan(
        {
            "version": TRIBUNAL_PATCH_PLAN_VERSION,
            "status": "planned",
            "decision_summary": "Unsafe expansion.",
            "operations": [
                _valid_plan_operation(operation_id="GF-PATCH-999"),
                _valid_plan_operation(target_path="proposal.backlog[0]"),
            ],
        },
        patchset_request=_patchset_request(),
    )

    assert patch_plan["status"] == "rejected"
    assert patch_plan["operation_count"] == 0
    assert [rejection["reason"] for rejection in patch_plan["rejections"]] == [
        "operation id is not in the PatchSet request",
        "target_path does not match the PatchSet request",
    ]


def test_plan_structured_patch_uses_schema_constrained_provider_request() -> None:
    provider = _FakeProvider(
        {
            "version": TRIBUNAL_PATCH_PLAN_VERSION,
            "status": "planned",
            "decision_summary": "Repair the first path semantic fact.",
            "operations": [_valid_plan_operation()],
        }
    )

    patch_plan = plan_structured_patch(
        provider=provider,
        patchset_request=_patchset_request(),
        review_report={"status": "failed"},
        evidence={"accepted_intent": {"title": "Accepted Project"}},
        model="reasoning-model",
        reasoning_effort="high",
        timeout_seconds=12.0,
    )

    assert patch_plan["status"] == "planned"
    assert provider.request is not None
    assert provider.request.schema_name == "tribunal_patch_plan"
    assert provider.request.output_schema["additionalProperties"] is False
    assert provider.request.prompt_payload["patchset_request"]["operations"][0]["operation_id"] == "GF-PATCH-001"
    assert provider.request.model == "reasoning-model"
    assert provider.request.reasoning_effort == "high"
    assert provider.request.timeout_seconds == 12.0


def test_merge_patch_plan_only_fills_planner_owned_fields() -> None:
    patch_plan = validate_structured_patch_plan(
        {
            "version": TRIBUNAL_PATCH_PLAN_VERSION,
            "status": "planned",
            "decision_summary": "Repair the first path semantic fact.",
            "operations": [_valid_plan_operation()],
        },
        patchset_request=_patchset_request(),
    )

    merged = merge_patch_plan_into_request(_patchset_request(), patch_plan)

    operation = merged["operations"][0]
    assert operation["operation_id"] == "GF-PATCH-001"
    assert operation["target_path"] == "semantic_model.first_path_contract"
    assert operation["replacement_fact"]["visible_result"] == "accepted result is shown and saved"
    assert operation["decision_ledger_entry"]["chosen_interpretation"].startswith("The first path")
    assert merged["tribunal_patch_plan"]["status"] == "planned"
