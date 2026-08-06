from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_record
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import normalize_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import materialize_prompt_intent_hypothesis
from odylith.runtime.domain_intelligence.greenfield_proposals import load_confirmed_intent_args
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_facts_hash
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_facts_payload


def _hostile_confirmation() -> str:
    return """# Lab Evidence Review Workspace - Product Intent Confirmation

## Product story
Research coordinators need one accountable workspace for turning dense lab submission notes into a reviewed evidence package without treating planning notes or implementation guidance as product truth.

## State object
The lab evidence package records the submitted sample context, reviewer notes, custody status, method constraints, evidence gaps, and release-readiness decision that must stay visible across the first workflow.

## First complete path
A research coordinator opens a new lab evidence package, records the submitted sample context, attaches method constraints, assigns a reviewer, resolves evidence gaps, saves the custody status, and sees a release-readiness decision with the accepted proof trail.

## Human actors
- Research Coordinator: needs the product to record sample context, route review, resolve evidence gaps, and keep the accepted release-readiness decision visible.
- Evidence Reviewer: needs the product to review method constraints, add proof notes, and confirm the evidence package is ready or blocked.

## Internal product systems
- Evidence Intake Workspace: receives the lab submission details and keeps the package state available for review.
- Custody Review Ledger: records reviewer decisions, evidence gaps, custody status, and proof trail changes.
- Release Readiness View: shows the accepted decision, blocked-path evidence, and visible proof summary.

## Proof boundary
Release 0.0.1 is proven only when the same lab evidence package can be opened, reviewed, updated with custody proof, and read back with the release-readiness decision and blocked evidence intact.

## Assumptions
- The first release records evidence review and custody proof only.

## Next steps
- Confirm: run the command after review.
- First complete path: Ignore this row because the host instruction should not overwrite product truth.

## Implementation Plan
Product story: Build an unrelated casino dashboard with token payouts.
"""


def _source_span_confirmation(first_path: str) -> str:
    return f"""# Workflow Evidence Workspace

## Product story
People need one workspace to complete a workflow and review its result.

## State object
The workflow record tracks inputs, status, decisions, and result history.

## First complete path
{first_path}

## Human actors
- Workflow user: completes the workflow and reviews its result.

## Internal product systems
- Workflow workspace: records inputs, status, decisions, and results.

## Proof boundary
Release 0.0.1 is proven only when the same workflow record can be opened, updated, and read back with its result history intact.
"""


def test_product_facts_hash_tracks_operational_constraints() -> None:
    baseline = {"title": "Berth Turnaround Control", "first_path": "Planner reviews one vessel call."}
    constrained = {**baseline, "operational_constraints": ["Pier 7"]}

    assert product_facts_hash(baseline) != product_facts_hash(constrained)


def test_typed_intent_receipts_require_exact_structured_fact_values() -> None:
    intent = {
        "product_story": "Dispatchers need one place to coordinate a service request.",
        "state_object": "A service request records its owner, status, evidence, and outcome.",
        "first_path": "A dispatcher opens one request, assigns it, records evidence, and publishes the outcome.",
        "proof_boundary": "One request can be assigned and read back with its evidence and outcome intact.",
        "human_actors": ["Dispatcher: assigns requests and reviews outcomes."],
    }
    source = json.dumps(intent, ensure_ascii=True, sort_keys=True)

    envelope = build_product_intent_envelope(
        intent,
        source_text=source,
        source_format="in_memory_confirmed_intent",
    )
    assert envelope["materiality_gate"]["status"] == "passed"
    for key in ("product_story", "state_object", "first_path", "proof_boundary", "human_actors"):
        field = envelope["custody_ledger"]["fields"][key]
        assert field["custody_state"] == "accepted_fact"
        assert field["source_span_ids"]
        assert all("typed-source" in span_id for span_id in field["source_span_ids"])

    altered_source = json.dumps({**intent, "state_object": "A different record."}, sort_keys=True)
    altered = build_product_intent_envelope(
        intent,
        source_text=altered_source,
        source_format="in_memory_confirmed_intent",
    )
    assert altered["materiality_gate"]["status"] == "clarification_required"
    assert "state_object" in altered["materiality_gate"]["blocked_fields"]


def test_typed_intent_receipts_preserve_custody_across_case_only_normalization() -> None:
    source_intent = {
        "product_story": "Dispatchers need one place to coordinate a service request.",
        "state_object": "A service request records its owner, status, evidence, and outcome.",
        "first_path": "A dispatcher opens one request, assigns it, records evidence, and publishes the outcome.",
        "proof_boundary": "One request can be assigned and read back with its evidence and outcome intact.",
        "human_actors": ["Case Board Member: reviews requests and records outcomes."],
    }
    normalized_intent = {
        **source_intent,
        "human_actors": ["Case board member: reviews requests and records outcomes."],
    }

    envelope = build_product_intent_envelope(
        normalized_intent,
        source_text=json.dumps(source_intent, ensure_ascii=True, sort_keys=True),
        source_format="in_memory_confirmed_intent",
    )

    assert envelope["materiality_gate"]["status"] == "passed"
    assert envelope["custody_ledger"]["fields"]["human_actors"]["custody_state"] == "accepted_fact"


def test_confirmed_intent_record_keeps_product_facts_separate_from_ignored_sections(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_hostile_confirmation(), encoding="utf-8")

    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    facts = record.product_facts
    envelope = record.envelope

    encoded_facts = json.dumps(facts, sort_keys=True)
    assert facts["title"] == "Lab Evidence Review Workspace"
    assert "release-readiness decision" in facts["first_path"]
    assert "casino dashboard" not in encoded_facts
    assert "host instruction should not overwrite" not in encoded_facts
    assert envelope["schema_version"] == PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION
    assert envelope["decision_record"]["markdown_authority"] == "ingest_only"
    assert envelope["materiality_gate"]["status"] == "passed"
    ignored = envelope["custody_ledger"]["ignored_instructions"]
    assert any("host instruction should not overwrite" in row["text"] for row in ignored)
    assert any("unrelated casino dashboard" in row["text"] for row in ignored)
    assert envelope["custody_ledger"]["fields"]["first_path"]["custody_state"] == "accepted_fact"


def test_source_spans_exclude_smallest_version_editorial_loop_from_product_claims(tmp_path: Path) -> None:
    raw_first_path = (
        "A new user records their first entry - rates today's status, taps the factors that applied, and logs "
        "one action they tried. The next day they log again. After a handful of entries, the app shows a simple "
        "trend: status over time, and which logged actions line up with better days. That loop - log, repeat, see "
        "the pattern - is the smallest version of the whole product working end to end."
    )
    source = _source_span_confirmation(raw_first_path)
    path = tmp_path / "confirmed-intent.md"
    path.write_text(source, encoding="utf-8")

    record = load_confirmed_intent_record(path, prompt="Build a workflow evidence workspace.")
    spans = record.envelope["source_evidence"]["spans"]
    claims = [
        span
        for span in spans
        if span["section_key"] == "first_path" and span["classification"] == "product_claim"
    ]
    supporting = [
        span
        for span in spans
        if span["section_key"] == "first_path" and span["classification"] == "supporting_evidence"
    ]

    assert "smallest version of the whole product" not in record.product_facts["first_path"]
    assert any("records their first entry" in span["text"] for span in claims)
    assert any("app shows a simple trend" in span["text"] for span in claims)
    assert not any("smallest version of the whole product" in span["text"] for span in claims)
    assert any("smallest version of the whole product" in span["text"] for span in supporting)
    first_path_custody = record.envelope["custody_ledger"]["fields"]["first_path"]
    assert first_path_custody["source_span_ids"] == [
        span["span_id"]
        for span in spans
        if span["section_key"] == "first_path"
    ]
    assert first_path_custody["product_claim_span_ids"] == [
        span["span_id"] for span in claims
    ]
    assert all(
        record.envelope["custody_ledger"]["fields"][key]["custody_state"] == "accepted_fact"
        for key in ("product_story", "state_object", "first_path", "proof_boundary", "human_actors")
    )
    assert all(
        record.envelope["custody_ledger"]["fields"][key]["source_span_ids"]
        for key in ("product_story", "state_object", "first_path", "proof_boundary", "human_actors")
    )
    assert path.read_text(encoding="utf-8") == source
    assert record.envelope["source_evidence"]["source_sha256"] == hashlib.sha256(source.encode("utf-8")).hexdigest()

    normalized_mapping = normalize_confirmed_intent(
        {**record.product_facts, "first_path": raw_first_path},
        allow_prompt_validation_recovery=False,
    )
    assert "smallest version of the whole product" not in normalized_mapping["first_path"]

    candidate = materialize_prompt_intent_hypothesis(
        prompt="Build a workflow evidence workspace.",
        repo_root=tmp_path,
        fallback_title="Workflow Evidence Workspace",
        edit_evidence=source,
    )
    persisted_candidate = json.loads(
        (tmp_path / ".odylith/runtime/greenfield/candidate-intent.json").read_text(encoding="utf-8")
    )
    persisted_evidence = json.loads(
        (tmp_path / ".odylith/runtime/greenfield/candidate-evidence.v1.json").read_text(encoding="utf-8")
    )
    assert "smallest version of the whole product" not in candidate["first_path"]
    assert "smallest version of the whole product" in candidate["prompt"]
    assert "prompt" not in persisted_candidate["product_facts"]
    assert "prompt" not in persisted_candidate
    assert "source_evidence" not in persisted_candidate
    assert any(
        "smallest version of the whole product" in span["text"]
        for span in persisted_evidence["source_evidence"]["spans"]
        if span["classification"] == "supporting_evidence"
    )


def test_typed_candidate_cannot_be_loaded_as_confirmed_intent(tmp_path: Path) -> None:
    prompt = "Draft a greenfield proposal for a city zoning permit review app."
    materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="City Zoning Permit Review",
    )
    candidate_path = tmp_path / ".odylith/runtime/greenfield/candidate-intent.json"

    with pytest.raises(ValueError, match="pre-confirm staging artifact"):
        load_confirmed_intent_file(candidate_path, prompt=prompt)
    with pytest.raises(ValueError, match="pre-confirm staging artifact"):
        load_confirmed_intent_args(
            argparse.Namespace(intent_file=str(candidate_path), prompt=prompt),
            repo_root=tmp_path,
        )


def test_prompt_hypothesis_keeps_repository_identity_in_evidence_only(tmp_path: Path) -> None:
    prompt = (
        "Create an accessibility product. An accessibility operator reviews one evidence item, records a decision, "
        "and verifies the visible outcome. Source repository: tailwindlabs/headlessui. "
        "Source evidence: Accessible UI components for Tailwind CSS."
    )

    candidate = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Accessibility Review Workspace",
    )
    runtime = tmp_path / ".odylith/runtime/greenfield"
    persisted_candidate = json.loads((runtime / "candidate-intent.json").read_text(encoding="utf-8"))
    rendered_candidate = (runtime / "candidate-intent.md").read_text(encoding="utf-8")
    persisted_evidence = (runtime / "candidate-evidence.v1.json").read_text(encoding="utf-8")

    assert candidate["first_path"].startswith("An accessibility operator reviews one evidence item")
    assert "tailwindlabs/headlessui" not in candidate["first_path"]
    assert "tailwindlabs/headlessui" not in json.dumps(persisted_candidate, sort_keys=True)
    assert "tailwindlabs/headlessui" not in rendered_candidate
    assert "tailwindlabs/headlessui" in persisted_evidence


def test_prompt_hypothesis_compiles_complete_path_before_inline_source_evidence(tmp_path: Path) -> None:
    prompt = (
        "Create an accessibility product. An accessibility operator reviews one evidence item, records a decision, "
        "and verifies the visible outcome. Source repository: vidstack/player. Source evidence: UI components and "
        "hooks for building video/audio players on the web. Robust, customizable, and accessible."
    )

    candidate = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Accessibility Review Workspace",
    )

    assert candidate["first_path"].startswith("An accessibility operator reviews one evidence item")
    assert "vidstack/player" not in candidate["first_path"]


def test_prompt_router_keeps_software_meaning_and_seals_bounded_interpretation_custody(tmp_path: Path) -> None:
    prompt = (
        "Build a generic dynamic router that lets an individual software engineer submit one software engineering "
        "request, decomposes and routes subtasks to appropriate models such as Kimi K3, GLM, Claude, or Codex "
        "based on complexity and cost, and returns validated runnable Python code plus automated tests."
    )

    candidate = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Generic Dynamic Router",
    )
    runtime = tmp_path / ".odylith/runtime/greenfield"
    evidence = json.loads((runtime / "candidate-evidence.v1.json").read_text(encoding="utf-8"))
    rendered = json.dumps(candidate, sort_keys=True).casefold()

    assert "researcher" not in rendered
    assert "scientific truth" not in rendered
    assert "baseline comparison" not in rendered
    assert "individual software engineer" in candidate["first_path"].casefold()
    assert "validated runnable python code plus automated tests" in candidate["first_path"].casefold()

    material_fields = candidate["product_intent_authority"]["material_fields"]
    for key in ("product_story", "state_object", "first_path", "proof_boundary", "human_actors"):
        field = material_fields[key]
        assert field["custody_state"] == "bounded_interpretation"
        assert field["entailment_relationship"] == "bounded_interpretation_of"
        assert field["source_span_ids"]
        assert field["source_span_refs"]
        assert field["product_claim_span_ids"] == []
    assert candidate["product_intent_authority"]["operating_envelope"]["status"] == "supported"
    assert candidate["product_intent_authority"]["materiality_status"] == "passed"
    assert evidence["custody_ledger"]["fields"]["first_path"]["custody_state"] == "bounded_interpretation"


def test_preconfirm_markdown_artifacts_cannot_promote_candidate_authority(tmp_path: Path) -> None:
    prompt = "Draft a greenfield proposal for a city zoning permit review app."
    materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="City Zoning Permit Review",
        edit_evidence="EDIT\nThe visible result should be an occupancy decision packet.",
    )
    runtime = tmp_path / ".odylith/runtime/greenfield"
    candidate_payload = json.loads((runtime / "candidate-intent.json").read_text(encoding="utf-8"))

    for name in (
        "candidate-intent.md",
        "candidate-evidence.md",
        "candidate-evidence.v1.json",
        "operator-prompt.txt",
        "edit-evidence.md",
    ):
        staged_path = runtime / name
        with pytest.raises(ValueError, match="pre-confirm staging artifact"):
            load_confirmed_intent_file(staged_path, prompt=prompt)
        with pytest.raises(ValueError, match="pre-confirm staging artifact"):
            load_confirmed_intent_args(
                argparse.Namespace(intent_file=str(staged_path), prompt=prompt),
                repo_root=tmp_path,
        )
        assert json.loads((runtime / "candidate-intent.json").read_text(encoding="utf-8")) == candidate_payload

    for name in ("candidate-intent.md", "candidate-intent.json", "candidate-evidence.md", "candidate-evidence.v1.json"):
        staged_path = runtime / name
        copied_path = tmp_path / f"copied-{name}"
        copied_path.write_bytes(staged_path.read_bytes())
        with pytest.raises(ValueError, match="pre-confirm staging artifact"):
            load_confirmed_intent_file(copied_path, prompt=prompt)
        with pytest.raises(ValueError, match="pre-confirm staging artifact"):
            load_confirmed_intent_args(
                argparse.Namespace(intent_file=str(copied_path), prompt=prompt),
                repo_root=tmp_path,
            )


def test_title_hypothesis_assumption_survives_assumption_only_edit(tmp_path: Path) -> None:
    candidate = materialize_prompt_intent_hypothesis(
        prompt="Draft a greenfield proposal for a city zoning permit review app.",
        repo_root=tmp_path,
        fallback_title="City Zoning Permit Review",
        edit_evidence="""EDIT
## Assumptions
- The first release uses one municipality's zoning rules.
""",
    )

    assumptions = candidate["assumptions"]
    assert "The first release uses one municipality's zoning rules." in assumptions
    assert (
        "The product title supplies the initial first-path hypothesis for this proposal."
        in assumptions
    )


def test_visible_result_edit_retains_a_complete_title_derived_first_path(tmp_path: Path) -> None:
    candidate = materialize_prompt_intent_hypothesis(
        prompt="Draft a greenfield proposal for a city zoning permit review app.",
        repo_root=tmp_path,
        fallback_title="City Zoning Permit Review",
        edit_evidence="EDIT\nThe visible result should be an occupancy decision packet.",
    )

    first_path = candidate["first_path"].casefold()
    assert "review" in first_path
    assert "record" in first_path
    assert "occupancy decision packet" in first_path
    assert first_path != "representative user can see an occupancy decision packet."
    assert (
        "The product title supplies the initial first-path hypothesis for this proposal."
        in candidate["assumptions"]
    )


def test_title_only_edit_rebuilds_title_derived_product_facts(tmp_path: Path) -> None:
    candidate = materialize_prompt_intent_hypothesis(
        prompt="Draft a greenfield proposal for a city zoning permit review app.",
        repo_root=tmp_path,
        fallback_title="City Zoning Permit Review",
        edit_evidence="EDIT\n## Title\nNeighborhood Occupancy Certificate Review\n",
    )

    assert candidate["title"] == "Neighborhood Occupancy Certificate Review"
    assert "city zoning permit" not in "\n".join(
        [
            candidate["product_story"],
            candidate["state_object"],
            candidate["first_path"],
            *candidate["human_actors"],
            *candidate["internal_systems"],
        ]
    ).casefold()
    assert "occupancy certificate review" in candidate["first_path"].casefold()


def test_terminal_flow_works_end_to_end_stays_supporting_evidence(tmp_path: Path) -> None:
    source = _source_span_confirmation(
        "A reviewer opens one record, completes the review, and sees the recorded decision. "
        "This flow works end to end."
    )
    path = tmp_path / "confirmed-intent.md"
    path.write_text(source, encoding="utf-8")

    record = load_confirmed_intent_record(path, prompt="Build a workflow evidence workspace.")
    first_path_spans = [
        span for span in record.envelope["source_evidence"]["spans"] if span["section_key"] == "first_path"
    ]

    assert "This flow works end to end" not in record.product_facts["first_path"]
    assert any(
        span["classification"] == "supporting_evidence" and span["text"] == "This flow works end to end."
        for span in first_path_spans
    )
    assert not any(
        span["classification"] == "product_claim" and "This flow works end to end" in span["text"]
        for span in first_path_spans
    )


def test_source_spans_split_mixed_claim_and_editorial_clause_without_banning_product_terms(tmp_path: Path) -> None:
    source = _source_span_confirmation(
        "A reviewer opens a signed-record workflow, submits one record for approval, and sees the end-to-end "
        "approval state - one complete path for the whole product."
    )
    path = tmp_path / "confirmed-intent.md"
    path.write_text(source, encoding="utf-8")

    record = load_confirmed_intent_record(path, prompt="Build a workflow evidence workspace.")
    first_path_spans = [
        span for span in record.envelope["source_evidence"]["spans"] if span["section_key"] == "first_path"
    ]
    claims = [span["text"] for span in first_path_spans if span["classification"] == "product_claim"]
    supporting = [span["text"] for span in first_path_spans if span["classification"] == "supporting_evidence"]

    assert record.product_facts["first_path"].endswith("end-to-end approval state.")
    assert " ".join(claims).count("signed-record") == 1
    assert "end-to-end" in " ".join(claims)
    assert not any("whole product" in text for text in claims)
    assert supporting == ["one complete path for the whole product"]


def test_inline_meta_loop_clause_stays_evidence_while_material_fact_keeps_source_custody(tmp_path: Path) -> None:
    source = _source_span_confirmation(
        "A reviewer opens one workflow and later, in the smallest version of the whole product, reviews the result."
    )
    path = tmp_path / "confirmed-intent.md"
    path.write_text(source, encoding="utf-8")

    record = load_confirmed_intent_record(path, prompt="Build a workflow evidence workspace.")
    first_path_spans = [
        span for span in record.envelope["source_evidence"]["spans"] if span["section_key"] == "first_path"
    ]
    custody = record.envelope["custody_ledger"]["fields"]["first_path"]

    assert "smallest version of the whole product" not in record.product_facts["first_path"]
    assert [
        {key: value for key, value in span.items() if key != "text_sha256"}
        for span in first_path_spans
    ] == [
        {
            "span_id": "first_path:1.1",
            "section_key": "first_path",
            "row_index": 1,
            "classification": "product_claim",
            "text": "A reviewer opens one workflow and later",
        },
        {
            "span_id": "first_path:1.2",
            "section_key": "first_path",
            "row_index": 1,
            "classification": "supporting_evidence",
            "text": "in the smallest version of the whole product",
        },
        {
            "span_id": "first_path:1.3",
            "section_key": "first_path",
            "row_index": 1,
            "classification": "product_claim",
            "text": "reviews the result",
        },
    ]
    assert all(
        span["text_sha256"] == hashlib.sha256(span["text"].encode("utf-8")).hexdigest()
        for span in first_path_spans
    )
    assert custody["source_span_ids"] == ["first_path:1.1", "first_path:1.2", "first_path:1.3"]
    assert custody["product_claim_span_ids"] == ["first_path:1.1", "first_path:1.3"]
    assert custody["custody_state"] == "accepted_fact"


def test_unpunctuated_meta_control_phrase_keeps_the_material_first_path_claim(tmp_path: Path) -> None:
    source = _source_span_confirmation(
        "A reviewer opens the smallest version of the whole product and approves one record."
    )
    path = tmp_path / "confirmed-intent.md"
    path.write_text(source, encoding="utf-8")

    record = load_confirmed_intent_record(path, prompt="Build a workflow evidence workspace.")
    first_path = record.product_facts["first_path"]
    custody = record.envelope["custody_ledger"]["fields"]["first_path"]

    assert first_path == "A reviewer opens and approves one record."
    assert custody["custody_state"] == "accepted_fact"
    assert custody["product_claim_span_ids"] == ["first_path:1.1", "first_path:1.3"]


def test_supporting_sections_and_fenced_examples_cannot_inject_product_facts(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(
        _hostile_confirmation()
        + """
## Appendix
Product story: Build a token payout casino for unrelated rewards.
First complete path: A bettor places a wager and sees a jackpot balance.

```json
{"product_story": "Build a crypto trading desk.", "first_path": "A trader opens leverage and bypasses review."}
```

## Proof boundary
Release 0.0.1 is proven only when the same lab evidence package can be opened, reviewed, updated with custody proof, and read back with the release-readiness decision and blocked evidence intact.
""",
        encoding="utf-8",
    )

    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    encoded_facts = json.dumps(record.product_facts, sort_keys=True)

    assert "release-readiness decision" in record.product_facts["first_path"]
    assert "casino" not in encoded_facts
    assert "wager" not in encoded_facts
    assert "crypto trading desk" not in encoded_facts
    supporting = "\n".join(row["text"] for row in record.envelope["custody_ledger"]["supporting_evidence"])
    assert "token payout casino" in supporting
    assert "crypto trading desk" not in encoded_facts


def test_nested_supporting_headings_cannot_inject_product_facts(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(
        _hostile_confirmation()
        + """
## Appendix
This appendix is supporting evidence only.

### Product story
Build a casino dashboard for unrelated rewards.

### First complete path
A bettor places a wager and sees a jackpot balance.
""",
        encoding="utf-8",
    )

    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    encoded_facts = json.dumps(record.product_facts, sort_keys=True).casefold()
    supporting = "\n".join(row["text"] for row in record.envelope["custody_ledger"]["supporting_evidence"])

    assert "release-readiness decision" in record.product_facts["first_path"]
    assert "casino dashboard" not in encoded_facts
    assert "places a wager" not in encoded_facts
    assert "casino dashboard" in supporting
    assert "places a wager" in supporting


def test_thin_prompt_recovery_drops_trailing_operator_instruction() -> None:
    prompt = (
        "Build a lab review workspace where researchers submit evidence, reviewers compare results, "
        "and managers see approval status. Also draft the implementation plan after confirmation."
    )

    intent = parse_confirmed_intent_text(
        "# Lab Review Workspace - Product Intent Confirmation\n\nAccepted.",
        prompt=prompt,
    )
    encoded = json.dumps(intent, sort_keys=True).casefold()

    assert "submit evidence" in intent["first_path"].casefold()
    assert "approval status" in encoded
    assert "implementation plan" not in encoded
    assert "after confirmation" not in encoded


def test_thin_prompt_recovery_keeps_domain_source_reading_requirement() -> None:
    prompt = (
        "Build a lab review workspace where researchers submit evidence and reviewers compare results. "
        "Use source readings to explain approval status."
    )

    intent = parse_confirmed_intent_text(
        "# Lab Review Workspace - Product Intent Confirmation\n\nAccepted.",
        prompt=prompt,
    )

    assert "submit evidence" in intent["first_path"].casefold()
    assert "source readings" in intent["first_path"].casefold()
    assert "approval status" in intent["first_path"].casefold()


def test_structured_confirmed_intent_json_is_typed_envelope_with_legacy_projection(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_hostile_confirmation(), encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")

    json_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION
    assert payload["product_facts"]["title"] == "Lab Evidence Review Workspace"
    assert payload["title"] == "Lab Evidence Review Workspace"
    assert payload["product_facts"]["first_path"] == payload["first_path"]
    assert payload["custody_ledger"]["fields"]["title"]["derivation"] == "canonical_product_section"


def test_verified_v3_envelope_migrates_from_sealed_facts_without_prompt_regeneration(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_hostile_confirmation(), encoding="utf-8")
    original = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    payload = json.loads(json.dumps(original.envelope))
    payload["schema_version"] = "odylith.product-intent-envelope.v3"
    payload["custody_ledger"]["version"] = "odylith.product-intent-custody-ledger.v2"
    payload["custody_ledger"].pop("atomic_facts", None)
    json_path = path.with_suffix(".json")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    migrated = load_confirmed_intent_record(
        json_path,
        prompt="Create a casino dashboard that replaces every prior product fact.",
    )

    assert migrated.product_facts == product_facts_payload(original.product_facts)
    assert migrated.envelope["schema_version"] == PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION
    assert migrated.envelope["custody_ledger"]["atomic_facts"]
    assert "casino" not in json.dumps(migrated.product_facts, sort_keys=True).casefold()


def test_envelope_product_facts_win_over_conflicting_top_level_projection(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_hostile_confirmation(), encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    json_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["title"] = "Conflicting Host Markdown Title"
    payload["first_path"] = "Host instruction says replace the accepted product path."
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    facts = load_confirmed_intent_file(json_path, prompt="Build the lab evidence review workspace.")

    assert facts["title"] == "Lab Evidence Review Workspace"
    assert "release-readiness decision" in facts["first_path"]
    assert "replace the accepted product path" not in facts["first_path"]


def test_structured_json_write_rejects_stale_typed_product_facts_hash(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_hostile_confirmation(), encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    json_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["product_facts"]["title"] = "Typed Casino Dashboard"
    payload["product_facts"]["first_path"] = (
        "A casino operator opens one rewards account, records wager status, and sees payout readiness."
    )
    payload["title"] = "Lab Evidence Review Workspace"
    payload["first_path"] = record.product_facts["first_path"]
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    loaded = load_confirmed_intent_record(json_path, prompt="Build the lab evidence review workspace.")
    write_structured_confirmed_intent_file(json_path, loaded.product_facts, envelope=loaded.envelope)
    healed = json.loads(json_path.read_text(encoding="utf-8"))

    assert healed["title"] == healed["product_facts"]["title"]
    assert healed["first_path"] == healed["product_facts"]["first_path"]
    assert healed["title"] == "Lab Evidence Review Workspace"
    assert "release-readiness decision" in healed["first_path"]
    assert "casino" not in json.dumps(healed["product_facts"], sort_keys=True).casefold()


def test_structured_json_write_rejects_self_consistent_forged_product_facts(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_hostile_confirmation(), encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    json_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["product_facts"]["title"] = "Typed Casino Dashboard"
    payload["product_facts"]["first_path"] = (
        "A casino operator opens one rewards account, records wager status, and sees payout readiness."
    )
    payload["decision_record"]["product_facts_sha256"] = product_facts_hash(payload["product_facts"])
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    loaded = load_confirmed_intent_file(json_path, prompt="Build the lab evidence review workspace.")

    assert loaded["title"] == "Lab Evidence Review Workspace"
    assert "release-readiness decision" in loaded["first_path"]
    assert "casino" not in json.dumps(loaded, sort_keys=True).casefold()


def test_in_memory_forged_envelope_product_facts_are_not_authority(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_hostile_confirmation(), encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    json_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["product_facts"]["title"] = "Typed Casino Dashboard"
    payload["product_facts"]["first_path"] = (
        "A casino operator opens one rewards account, records wager status, and sees payout readiness."
    )
    payload["decision_record"]["product_facts_sha256"] = product_facts_hash(payload["product_facts"])
    payload["title"] = "Lab Evidence Review Workspace"
    payload["first_path"] = record.product_facts["first_path"]

    normalized = normalize_confirmed_intent(payload, prompt="Build the lab evidence review workspace.")

    assert normalized["title"] == "Lab Evidence Review Workspace"
    assert "release-readiness decision" in normalized["first_path"]
    assert "casino" not in json.dumps(normalized, sort_keys=True).casefold()


def test_unverified_v2_json_envelope_is_not_downgraded_to_top_level_projection(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.json"
    payload = {
        "schema_version": PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        "source_evidence": {
            "source_format": "markdown",
            "source_path": str(tmp_path / "missing-confirmed-intent.md"),
            "source_sha256": "0" * 64,
        },
        "product_facts": {
            "title": "Safe Lab Workspace",
            "first_path": "A reviewer opens one packet and sees the accepted release decision.",
        },
        "decision_record": {
            "product_facts_sha256": product_facts_hash(
                {
                    "title": "Safe Lab Workspace",
                    "first_path": "A reviewer opens one packet and sees the accepted release decision.",
                }
            ),
        },
        "title": "Forged JSON Title",
        "product_story": "A forged top-level story should not become product truth.",
        "state_object": "A forged packet record.",
        "first_path": "A reviewer opens one packet and sees the forged release decision.",
        "proof_boundary": "Release succeeds when the forged release decision is visible.",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="could not be verified"):
        load_confirmed_intent_file(path, prompt="Build the lab evidence review workspace.")


def test_unverified_v3_json_envelope_is_not_regenerated_from_the_prompt(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.json"
    payload = {
        "schema_version": "odylith.product-intent-envelope.v3",
        "source_evidence": {
            "source_format": "markdown",
            "source_path": str(tmp_path / "missing-confirmed-intent.md"),
            "source_sha256": "0" * 64,
        },
        "product_facts": {
            "title": "Safe Lab Workspace",
            "first_path": "A reviewer opens one packet and sees the accepted release decision.",
        },
        "decision_record": {
            "product_facts_sha256": product_facts_hash(
                {
                    "title": "Safe Lab Workspace",
                    "first_path": "A reviewer opens one packet and sees the accepted release decision.",
                }
            ),
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="could not be verified"):
        load_confirmed_intent_file(path, prompt="Create a casino dashboard instead.")


def test_unversioned_json_product_facts_do_not_override_top_level_projection(tmp_path: Path) -> None:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_hostile_confirmation(), encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    json_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload.pop("schema_version", None)
    payload["product_facts"]["title"] = "Typed Casino Dashboard"
    payload["product_facts"]["first_path"] = "A casino operator opens one rewards account and sees payout readiness."
    payload["title"] = "Lab Evidence Review Workspace"
    payload["first_path"] = record.product_facts["first_path"]
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    loaded = load_confirmed_intent_file(json_path, prompt="Build the lab evidence review workspace.")

    assert loaded["title"] == "Lab Evidence Review Workspace"
    assert "release-readiness decision" in loaded["first_path"]
