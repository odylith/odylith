from __future__ import annotations

import inspect
import json
import re

from odylith.runtime.domain_intelligence import greenfield_confirmed_title_repair
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import normalize_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_mapping_with_authority


ACTIVITY_WATCHLIST_INTENT = """Product story
A researcher wants to follow public activity signals for selected people, compare those signals with a private watchlist, and decide whether each signal deserves more research. The product keeps source evidence, confidence, notes, and personal follow or ignore decisions together without claiming a guaranteed outcome.

State object
The core state is a tracked person profile connected to public activity signals, source evidence, timestamps, confidence, user notes, and the user's follow, watch, or ignore decision.

First complete path
A user adds a person to follow, chooses approved public data sources, sees recent activity signals with source links, reviews risk and context summaries, adds selected items to a watchlist, and records whether they plan to research, ignore, or act later.

Human actors
- Research user
- Public person being tracked through lawful records
- Administrator managing data-source quality
- Policy reviewer for privacy boundaries

External systems
- Public data provider
- Disclosure source
- News feed
- Authentication service

Internal product systems
- Person follow list
- Activity ingestion and source attribution
- Signal confidence and deduplication
- Watchlist and decision journal
- Risk, disclaimer, and policy guardrails
- Alerts and notification preferences

Critical assumptions
- The app tracks only lawful public records, licensed data, or data provided with explicit permission.
- Users make their own decisions and can record rationale before acting.

Ambiguities
- Which public people are in scope first?
- Which jurisdictions matter at launch?

Proof boundary
A first release is successful if a user can follow lawful public activity for selected people, inspect source-backed signals, add items to a personal watchlist, and make a documented research decision without the product overstating certainty or hiding risk.
"""


def test_confirmed_intent_parser_preserves_bare_first_line_title() -> None:
    intent = parse_confirmed_intent_text(
        "People-Driven Activity Watchlist\n\n" + ACTIVITY_WATCHLIST_INTENT,
        prompt="Draft a product-first greenfield proposal for a people activity tracker.",
    )

    assert intent["title"] == "People-Driven Activity Watchlist"


def test_confirmed_intent_parser_accepts_title_after_confirmation_heading() -> None:
    intent = parse_confirmed_intent_text(
        "Product Intent Confirmation\n\nPeople-Driven Activity Watchlist\n\n" + ACTIVITY_WATCHLIST_INTENT,
        prompt="Draft a product-first greenfield proposal for a people activity tracker.",
    )

    assert intent["title"] == "People-Driven Activity Watchlist"


def test_confirmed_create_repairs_prompt_shaped_title_before_quality_gate(tmp_path) -> None:
    prompt = (
        "Draft a product-first greenfield proposal for a people activity tracker app that captures "
        "what specific people are doing so that we can follow the same and make money."
    )
    fallback_title = greenfield_proposals.intent_title(prompt)
    intent = parse_confirmed_intent_text(
        ACTIVITY_WATCHLIST_INTENT,
        prompt=prompt,
        fallback_title=fallback_title,
    )

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )

    title = str(proposal["intent"]["title"])
    encoded = json.dumps(proposal)
    assert title != fallback_title
    assert len(title.split()) <= 6
    assert title.split()[-1].casefold() not in {"a", "an", "and", "for", "from", "of", "or", "the", "to", "with"}
    assert "That Captures What Specific People" not in encoded
    assert "So That We Can Follow" not in encoded
    assert "Doing So That" not in encoded
    assert "checks A first release" not in encoded
    assert "and checks A" not in encoded
    assert not re.search(r"without the prod(?:[\\s.,;:!?]|$)", encoded)
    assert "The proof target is A first release" not in encoded
    assert not greenfield_quality_issues(proposal)


def test_intent_title_uses_prompt_boundary_instead_of_clipped_target_tail() -> None:
    prompt = (
        "Design an end-to-end export-control and data-handling compliance workflow for a research lab "
        "processing mixed classified and unclassified files, including review gates, audit trail, "
        "incident response, and least-privilege automation."
    )

    title = greenfield_proposals.intent_title(prompt)

    assert title.casefold() == "end-to-end export-control and data-handling compliance workflow"
    assert "Research Lab Processing" not in title
    assert "Unclassified Files" not in title


def test_confirmed_create_keeps_list_signal_journal_and_guardrail_components_local(tmp_path) -> None:
    prompt = (
        "Draft a product-first greenfield proposal for a people activity tracker app that captures "
        "what specific people are doing so that we can follow the same and make money."
    )
    intent = parse_confirmed_intent_text(
        "People-Driven Activity Watchlist\n\n" + ACTIVITY_WATCHLIST_INTENT,
        prompt=prompt,
    )

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    contracts = {str(row["label"]): row["component_contract"] for row in proposal["components"]}
    encoded = json.dumps(proposal)

    follow = contracts["Person Follow List Service"]
    assert "person follow list" in str(follow["owned_state"]).casefold()
    assert "recent activity signal" in str(follow["owned_state"]).casefold()
    assert "dashboard view" not in str(follow).casefold()
    assert "search query" not in str(follow).casefold()

    confidence = contracts["Signal Confidence and Deduplication Service"]
    assert "signal confidence" in str(confidence["owned_state"]).casefold()
    assert "deduplication" in str(confidence["owned_state"]).casefold()
    assert "derived condition model" not in str(confidence).casefold()

    journal = contracts["Watchlist and Decision Journal Service"]
    assert "watchlist" in str(journal["owned_state"]).casefold()
    assert "research decision" in str(journal["owned_state"]).casefold()
    assert "final approval state" not in str(journal).casefold()

    guardrails = contracts["Risk, Disclaimer, and Policy Guardrails Service"]
    assert "risk" in str(guardrails["owned_state"]).casefold()
    assert "policy guardrails" in str(guardrails["owned_state"]).casefold()
    assert "alert rule" not in str(guardrails).casefold()

    assert "Filtered result set" not in encoded
    assert "dashboard renders filtered results" not in encoded
    assert "Derived condition model" not in encoded


def test_confirmed_intent_completion_does_not_splice_proof_boundary_into_actor_rows() -> None:
    intent = parse_confirmed_intent_text(
        "People-Driven Activity Watchlist\n\n" + ACTIVITY_WATCHLIST_INTENT,
        prompt="Draft a product-first greenfield proposal for a people activity tracker.",
    )

    actor_text = "\n".join(intent["human_actors"])
    assert "first release is successful" not in actor_text
    assert "can own a named responsibility" not in actor_text
    assert "Research User: uses People-Driven Activity Watchlist" in actor_text
    assert "Public Person Being Tracked Through Lawful Records: is represented by lawful source records" in actor_text
    assert "Policy Reviewer for Privacy Boundaries: reviews access, privacy, policy, risk, and evidence boundaries" in actor_text


def test_confirmed_json_intent_repairs_prompt_shaped_title() -> None:
    prompt = (
        "Draft a product-first greenfield proposal for a people activity tracker app that captures "
        "what specific people are doing so that we can follow the same and make money."
    )
    intent = normalize_confirmed_intent(
        {
            "title": greenfield_proposals.intent_title(prompt),
            "product_story": (
                "A researcher wants to follow public activity signals for selected people, compare those signals "
                "with a private watchlist, and decide whether each signal deserves more research. The product keeps "
                "source evidence, confidence, notes, and personal follow or ignore decisions together."
            ),
            "state_object": "The core state is a tracked person profile connected to activity signals, source evidence, timestamps, confidence, user notes, and follow decisions.",
            "first_path": "A user adds a person to follow, chooses approved public data sources, sees recent activity signals with source links, adds selected items to a watchlist, and records a research decision.",
            "human_actors": ["Research user", "Policy reviewer", "Administrator"],
            "external_systems": ["Public data provider", "Authentication service"],
            "internal_systems": [
                "Person follow list",
                "Activity ingestion and source attribution",
                "Signal confidence and deduplication",
                "Watchlist and decision journal",
            ],
            "assumptions": ["Only lawful public records, licensed data, or permissioned data are tracked."],
            "ambiguities": ["Which people are in scope first?"],
            "proof_boundary": "A first release is successful if a user can follow lawful public activity for selected people, inspect source-backed signals, add items to a personal watchlist, and make a documented research decision without overstating certainty.",
        },
        prompt=prompt,
    )

    assert intent["title"] == "Tracked Person Profile Watchlist"


def test_confirmed_title_repair_uses_shared_label_terms_for_display_tokens(tmp_path) -> None:
    source = inspect.getsource(greenfield_confirmed_title_repair)

    assert "greenfield_domain_term_index import label_terms" in source
    assert 're.findall(r"[A-Za-z0-9]+", text)' not in source
    assert 're.findall(r"[A-Za-z0-9]+", candidate)' not in source
    assert label_terms("AI/ML Review Workspace") == ["AI", "ML", "Review", "Workspace"]

    prompt = (
        "Draft a product-first greenfield proposal for a people activity tracker app that captures "
        "what specific people are doing so that we can follow the same and make money."
    )
    intent = parse_confirmed_intent_text(
        "People-Driven Activity Watchlist\n\n" + ACTIVITY_WATCHLIST_INTENT,
        prompt=prompt,
    )
    proposal = greenfield_proposals.build_confirmed_greenfield_proposal(
        prompt=prompt,
        title="People-Driven Activity Watchlist",
        observed_source={"root": str(tmp_path)},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    stale_title = greenfield_proposals.intent_title(prompt)
    proposal["intent"]["title"] = stale_title
    proposal["release_plan"]["label"] = "Ship AI/ML Review Workspace First Release"

    repaired = complete_confirmed_proposal(proposal, release_selector="0.0.1")

    assert repaired["intent"]["title"] == "AI/ML Review Workspace"


def test_confirmed_completion_repairs_stale_prompt_shaped_title_bindings(tmp_path) -> None:
    prompt = (
        "Draft a product-first greenfield proposal for a people activity tracker app that captures "
        "what specific people are doing so that we can follow the same and make money."
    )
    intent = parse_confirmed_intent_text(
        "People-Driven Activity Watchlist\n\n" + ACTIVITY_WATCHLIST_INTENT,
        prompt=prompt,
    )
    proposal = greenfield_proposals.build_confirmed_greenfield_proposal(
        prompt=prompt,
        title="People-Driven Activity Watchlist",
        observed_source={"root": str(tmp_path)},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    stale_title = greenfield_proposals.intent_title(prompt)
    proposal["intent"]["title"] = stale_title
    proposal["intent"]["project_slug"] = "people-activity-tracker-app-that-captures-what-specific-people-are-doing-so-that-we-can-follow"
    proposal["artifact_derivation"] = {
        "project_title": stale_title,
        "root": "project_intelligence",
        "root_schema_version": "odylith.greenfield.project_intelligence.v1",
    }
    proposal["backlog"][0]["project_intelligence_binding"] = {"project_title": stale_title}

    repaired = complete_confirmed_proposal(proposal, release_selector="0.0.1")
    encoded = json.dumps(repaired)

    assert repaired["intent"]["title"] == "People-Driven Activity Watchlist"
    assert "That Captures What Specific People" not in encoded
    assert "So That We Can Follow" not in encoded
