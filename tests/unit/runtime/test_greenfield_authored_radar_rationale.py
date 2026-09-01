"""Exact-custody Radar rationale coverage for model-authored Greenfield."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_authored_radar_ordering import (
    AUTHORED_ORDERING_DECISION_VERSION,
    authored_ordering_decision,
    render_authored_ordering_rationale,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    RESCUE_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.governance import backlog_authoring
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)


def _authored_proposal(tmp_path: Path, *, non_goals: list[str]) -> dict[str, object]:
    first_path = "Dock attendant records berth occupancy and sees a signed berth receipt"
    intent = {
        "title": "Harbor Desk",
        "product_story": "Dock attendants receive a reviewable berth receipt.",
        "state_object": "berth occupancy",
        "first_path": first_path,
        "proof_boundary": "Verify the signed receipt and retained berth occupancy.",
        "problem": "Berth occupancy is hard to review.",
        "customer": "Dock attendants",
        "opportunity": "Provide one reviewable berth workflow.",
        "product_view": "Harbor Desk records berth occupancy.",
        "success_metrics": ["The dock attendant sees a signed berth receipt."],
        "evidence_requirements": ["Retain berth occupancy evidence."],
        "operational_constraints": [],
        "component_responsibilities": ["Record berth occupancy."],
        "human_actors": ["Dock attendant"],
        "external_systems": [],
        "internal_systems": [],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": non_goals,
    }
    relations = (
        {
            "actor_kind": "human",
            "actor_quote": "Dock attendant",
            "owner_system_quote": "",
            "event_quote": first_path,
            "action_verb_quote": "records",
            "target_quote": "berth occupancy",
            "visible_result_quote": "sees a signed berth receipt",
            "recovery_path": False,
        },
    )
    prompt = "\n".join(
        str(value)
        for value in (
            *[intent[key] for key in ("title", "product_story", "state_object", "first_path", "proof_boundary")],
            *[intent[key] for key in ("problem", "customer", "opportunity", "product_view")],
            *intent["success_metrics"],
            *intent["evidence_requirements"],
            *intent["component_responsibilities"],
            *intent["human_actors"],
            *intent["internal_systems"],
            *non_goals,
        )
    )
    candidate = materialize_model_authored_intent(
        prompt=prompt,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                first_path_relations=relations,
                component_responsibility_owners=["Harbor Desk"],
            )
        ),
        authoring_timeout_seconds=84.0,
        authoring_profile_id=RESCUE_PROFILE_ID,
    )
    proposal = build_authored_greenfield_proposal(
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=candidate,
    )
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = candidate[PRODUCT_INTENT_AUTHORITY_KEY]
    assert AUTHORED_SEMANTICS_KEY in proposal["intent"]
    return proposal


def test_authored_backlog_rationale_reaches_rendering_without_placeholder_copy(
    tmp_path: Path,
) -> None:
    non_goal = "Do not automate harbor billing in the first release."
    proposal = _authored_proposal(tmp_path, non_goals=[non_goal])

    assert not hasattr(greenfield_proposals, "_greenfield_ordering_rationale")
    assert not hasattr(greenfield_proposals, "_greenfield_rationale_lines")
    args = greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1")
    first = proposal["backlog"][0]
    assert isinstance(first, dict)
    title = str(first["title"])

    row_args = backlog_authoring._title_specific_args(title=title, args=args)
    rationale_lines = tuple(row_args.rationale_lines)
    decision = authored_ordering_decision(first["ordering_decision"])

    assert decision["version"] == AUTHORED_ORDERING_DECISION_VERSION
    assert decision["tradeoff"] == ""
    assert decision["deferred_scope"] == [non_goal]
    assert decision["ranking_basis"] == (
        "Dock attendant records berth occupancy and sees a signed berth receipt"
    )
    assert row_args.ordering_rationale == decision["ranking_basis"]
    assert rationale_lines[0] == "- why now: Provide one reviewable berth workflow."
    assert rationale_lines[1] == (
        "- expected outcome: Harbor Desk records berth occupancy."
    )
    assert rationale_lines[2] == f"- deferred for now: {non_goal}"
    assert rationale_lines[3].endswith(
        "Dock attendant records berth occupancy and sees a signed berth receipt"
    )
    assert "TBD" not in "\n".join(rationale_lines)
    sections = first["radar_sections"]
    assert [row["workstream_role"] for row in proposal["backlog"]] == ["project"]
    assert non_goal in sections["Non-Goals"]
    assert non_goal not in sections["Risks"]
    assert non_goal not in sections["Migration/Compatibility"]

    item = backlog_authoring.CreatedBacklogItem(
        idea_id="B-001",
        title=title,
        idea_path=tmp_path / "idea.md",
        ordering_score=1,
        founder_override=False,
        rationale_lines=rationale_lines,
    )
    rendered_rationale = backlog_authoring._build_rationale_lines(
        item=item,
        override_note="",
        override_review_date="",
    )
    assert rendered_rationale == list(rationale_lines)

    index_path = tmp_path / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Radar",
                "",
                "Last updated (UTC): 2026-01-01",
                "",
                "## Ranked Active Backlog",
                "",
                "| Rank | Idea ID |",
                "| --- | --- |",
                "",
                "## Reorder Rationale Log",
                "",
                "## Queue",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rendered_index = backlog_authoring._rewrite_active_backlog_section(
        backlog_index_path=index_path,
        active_rows=(),
        reorder_sections=((item.idea_id, "B-001 (rank 1)", rendered_rationale),),
        today=dt.date(2026, 8, 31),
    )

    assert "TBD" not in rendered_index
    assert non_goal in rendered_index


def test_authored_backlog_rationale_omits_absent_optional_lines(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path, non_goals=[])
    first = proposal["backlog"][0]
    assert isinstance(first, dict)

    decision = authored_ordering_decision(first["ordering_decision"])
    assert decision["tradeoff"] == ""
    assert decision["deferred_scope"] == []
    rendered = render_authored_ordering_rationale(decision)
    assert len(rendered) == 3
    assert all("tradeoff:" not in line for line in rendered)
    assert all("deferred for now:" not in line for line in rendered)
