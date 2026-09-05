"""Exact-memory proof for the model-authored Greenfield projection."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import proposal_memory
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    GreenfieldAuthoredSemanticsError,
    authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)


FIRST_PATH = (
    "  Registry Custodian **QuOrates** one Æther packet;  "
    "Meridian Engine vitrifies it into Ω-Receipt.  "
)
EVENT_ONE = "Registry Custodian **QuOrates** one Æther packet"
EVENT_TWO = "Meridian Engine vitrifies it into Ω-Receipt"


def _relation(
    *,
    order: int,
    event: str,
    actor_kind: str,
    actor: str,
    action: str,
    target: str,
    visible_result: str = "",
) -> dict[str, object]:
    path_bytes = FIRST_PATH.encode("utf-8")
    event_bytes = event.encode("utf-8")
    start = path_bytes.index(event_bytes)
    return {
        "order": order,
        "source_start_byte": start,
        "source_end_byte": start + len(event_bytes),
        "event_start_byte": start,
        "event_end_byte": start + len(event_bytes),
        "actor_kind": actor_kind,
        "actor_quote": actor,
        "actor_is_carried": False,
        "actor_fact_path": (
            "/internal_systems/0" if actor_kind == "product" else "/human_actors/0"
        ),
        "actor_fact_quote": (
            "Meridian Engine" if actor_kind == "product" else "Registry Custodian"
        ),
        "owner_system_path": "/internal_systems/0" if actor_kind == "product" else "",
        "owner_system_quote": "Meridian Engine" if actor_kind == "product" else "",
        "event_quote": event,
        "action_verb_quote": action,
        "target_quote": target,
        "visible_result_quote": visible_result,
    }


def _proposal() -> dict[str, object]:
    relations = (
        _relation(
            order=1,
            event=EVENT_ONE,
            actor_kind="human",
            actor="Registry Custodian",
            action="QuOrates",
            target="one Æther packet",
        ),
        _relation(
            order=2,
            event=EVENT_TWO,
            actor_kind="product",
            actor="Meridian Engine",
            action="vitrifies",
            target="it",
            visible_result="Ω-Receipt",
        ),
    )
    independent_context_start = len(FIRST_PATH.encode("utf-8")) + 1
    return {
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "intent": {
            "title": "eXact Ω **Forge**",
            "product_story": "Keep APIv7 and café custody exact.",
            "first_path": FIRST_PATH,
            "proof_boundary": "Reviewer observes Ω-Receipt?!",
            "human_actors": ["Registry Custodian"],
            "internal_systems": ["Meridian Engine"],
            "evidence_requirements": ["  Keep **APIv7** evidence byte-exact.  "],
            "operational_constraints": ["Preserve café casing"],
            "non_goals": ["Do not infer batch migration"],
            "authored_semantics": authored_semantics_mapping(
                relations,
                (
                    {
                        "responsibility_path": "/first_path",
                        "responsibility_quote": "Ω-Receipt",
                        "owner_system_path": "/internal_systems/0",
                        "owner_system_quote": "Meridian Engine",
                        "first_path_event_order": 2,
                        "responsibility_source": "terminal_visible_result",
                    },
                ),
                first_path_context_relations=(
                    {
                        "context_kind": "operational_constraint",
                        "fact_path": "/operational_constraints/0",
                        "fact_quote": "Preserve café casing",
                        "source_start_byte": independent_context_start,
                        "source_end_byte": independent_context_start
                        + len("Preserve café casing".encode("utf-8")),
                        "first_path_event_order": 0,
                    },
                ),
            ),
        },
        "observed_source": {"source_posture": "operator prompt"},
        "assumptions": [],
        "open_questions": [],
        "project_brief": {
            "project_outcome": "Ω-Receipt",
            "operating_principle": "Keep APIv7 and café custody exact.",
            "blueprint_sections": [
                {
                    "section": "First path",
                    "must_capture": FIRST_PATH,
                    "why_it_matters": "Exact authored custody.",
                }
            ],
            "coding_readiness_gates": [
                "Reviewer observes Ω-Receipt?!",
                "  Keep **APIv7** evidence byte-exact.  ",
            ],
            "host_independent_paths": [],
        },
    }


def test_authored_memory_preserves_exact_contract_without_legacy_reconstruction(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    proposal = _proposal()
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = {
        "private_source": "operator evidence stays outside accepted memory"
    }
    for name in (
        "_event_summary",
        "_event_context",
        "_normalize_accepted_memory_copy",
        "_strip_memory_public_copy_emphasis",
        "normalize_first_path",
        "base_adverbial_note_action",
        "normalize_terminal_punctuation",
    ):
        assert not hasattr(proposal_memory, name)
    assert not hasattr(proposal_memory, "greenfield_source_casing")

    source_launch = {
        "start_workstream_id": "B-701",
        "implementation_prompt": "  Preserve **APIv7** and Ω exactly.  ",
        "coding_readiness_gates": ["  Keep **APIv7** evidence byte-exact.  "],
        "coding_readiness_contract": {
            "schema_version": "odylith.greenfield.coding-readiness.v1",
            "source_facts": {"accepted_first_path": FIRST_PATH},
        },
        "verification_commands": ["verify-Ω --APIv7"],
    }
    event = proposal_memory.build_greenfield_acceptance_event_preview(
        proposal=proposal,
        backlog_items=[{"idea_id": "B-701", "idea_path": "odylith/radar/source/B-701.md"}],
        component_items=[{"component_id": "meridian-engine"}],
        diagram_ids=["D-701"],
        release_selector="0.0.1",
        release_id="release-0-0-1",
        repo_root=tmp_path,
    )
    accepted = proposal_memory.build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=[{"idea_id": "B-701", "idea_path": "odylith/radar/source/B-701.md"}],
        component_items=[{"component_id": "meridian-engine"}],
        diagram_ids=["D-701"],
        release_selector="0.0.1",
        release_id="release-0-0-1",
        validation_gate={"status": "passed"},
        source_launch_context=source_launch,
        repo_root=tmp_path,
    )
    brief = proposal_memory.build_project_brief_source_markdown(
        proposal=proposal,
        backlog_items=[{"idea_id": "B-701"}],
        component_items=[{"component_id": "meridian-engine"}],
        diagram_ids=["D-701"],
        release_selector="0.0.1",
        release_id="release-0-0-1",
    )

    assert event["summary"] == "Accepted the sealed model-authored Greenfield package."
    assert event["headline_hint"] == "Greenfield package accepted: eXact Ω **Forge**"
    assert accepted["title"] == "eXact Ω **Forge**"
    assert accepted["proposal"]["intent"]["first_path"] == FIRST_PATH  # type: ignore[index]
    assert accepted["proposal"]["intent"]["authored_semantics"] == proposal["intent"][  # type: ignore[index]
        "authored_semantics"
    ]
    assert PRODUCT_INTENT_AUTHORITY_KEY not in accepted["proposal"]
    assert PRODUCT_INTENT_AUTHORITY_KEY in proposal
    assert accepted["source_launch"] == source_launch
    assert FIRST_PATH.strip() in brief
    assert "**APIv7**" in brief


def test_authored_memory_marker_without_typed_relations_fails_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    proposal = deepcopy(_proposal())
    proposal["intent"]["authored_semantics"] = {}  # type: ignore[index]

    with pytest.raises(GreenfieldAuthoredSemanticsError):
        proposal_memory.build_accepted_project_source_payload(
            proposal=proposal,
            backlog_items=[],
            component_items=[],
            diagram_ids=[],
            release_selector="0.0.1",
            release_id="release-0-0-1",
            validation_gate={"status": "passed"},
            repo_root=tmp_path,
        )


def test_authored_memory_rejects_relation_free_proposals(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        proposal_memory.build_accepted_project_source_payload(
            proposal={"intent": {"title": "Legacy"}},
            backlog_items=[],
            component_items=[],
            diagram_ids=[],
            release_selector="0.0.1",
            release_id="release-0-0-1",
            validation_gate={"status": "passed"},
            repo_root=tmp_path,
        )


def test_authored_acceptance_memory_keeps_every_artifact_without_count_clipping(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    backlog_items = [
        {
            "idea_id": f"B-{index:03d}",
            "idea_path": f"odylith/radar/source/B-{index:03d}.md",
        }
        for index in range(1, 16)
    ]
    event = proposal_memory.build_greenfield_acceptance_event_preview(
        proposal=_proposal(),
        backlog_items=backlog_items,
        component_items=[],
        diagram_ids=[],
        release_selector="0.0.1",
        release_id="release-0-0-1",
        repo_root=tmp_path,
    )

    assert event["artifacts"] == [
        proposal_memory.PROJECT_BRIEF_SOURCE_PATH,
        *[row["idea_path"] for row in backlog_items],
    ]


def test_compiled_authored_memory_commit_writes_exact_preconfirmed_records(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # type: ignore[no-untyped-def]
    proposal = _proposal()
    accepted_at = "2026-09-01T12:00:00-07:00"
    backlog_items = [
        {"idea_id": "B-701", "idea_path": "odylith/radar/source/B-701.md"}
    ]
    component_items = [
        {
            "component_id": "meridian-engine",
            "spec_path": "odylith/registry/source/components/meridian-engine/CURRENT_SPEC.md",
        }
    ]
    accepted = proposal_memory.build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=component_items,
        diagram_ids=["D-701"],
        release_selector="0.0.1",
        release_id="release-0-0-1",
        validation_gate={"status": "passed"},
        accepted_at=accepted_at,
        repo_root=tmp_path,
    )
    event = proposal_memory.build_greenfield_acceptance_event_preview(
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=component_items,
        diagram_ids=["D-701"],
        release_selector="0.0.1",
        release_id="release-0-0-1",
        accepted_at=accepted_at,
        repo_root=tmp_path,
    )
    brief = proposal_memory.build_project_brief_source_markdown(
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=component_items,
        diagram_ids=["D-701"],
        release_selector="0.0.1",
        release_id="release-0-0-1",
        accepted_at=accepted_at,
    )

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("compiled memory commit must not reopen authored semantics")

    monkeypatch.setattr(proposal_memory, "_require_authored_relations", forbidden)
    result = proposal_memory.record_compiled_greenfield_acceptance(
        repo_root=tmp_path,
        accepted_project_preview=accepted,
        project_brief_record_text=brief,
        compass_memory_preview=event,
    )
    replay = proposal_memory.record_compiled_greenfield_acceptance(
        repo_root=tmp_path,
        accepted_project_preview=accepted,
        project_brief_record_text=brief,
        compass_memory_preview=event,
    )

    assert result["event"] == event
    assert replay["reused_existing"] is True
    assert json.loads(
        (tmp_path / proposal_memory.ACCEPTED_PROJECT_SOURCE_PATH).read_text(
            encoding="utf-8"
        )
    ) == accepted
    assert (
        tmp_path / proposal_memory.PROJECT_BRIEF_SOURCE_PATH
    ).read_text(encoding="utf-8") == brief
    stream_path = Path(str(result["stream"]))
    assert [
        json.loads(line)
        for line in stream_path.read_text(encoding="utf-8").splitlines()
    ] == [event]
