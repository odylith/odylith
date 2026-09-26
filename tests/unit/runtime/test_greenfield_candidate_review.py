"""Complete-candidate admission: immutable inputs, one call, shared deadlines."""

import hashlib
import json
from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence import greenfield_candidate_review as review
from odylith.runtime.domain_intelligence import (
    greenfield_model_intent_authoring as author,
)
from odylith.runtime.domain_intelligence import (
    greenfield_participant_first_authoring as participant_authoring,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    RemainingCandidateProvider,
    StructuredAuthoringProvider,
    authored_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source

ADMITTED = {
    "outcome": "admitted",
    "issue": None,
    "clarification": None,
    "admission_witness": {
        "participant_fact": {"field": "human_actors", "row": 1},
        "task_event_order": 1,
        "result_event_order": 3,
    },
}


class Clock:
    value = 0.0

    def __call__(self):
        return self.value


class Reviewer(StructuredAuthoringProvider):
    def __init__(self, response, clock, duration=0.0, mutation=None):
        super().__init__(response)
        self.clock, self.duration, self.mutation = clock, duration, mutation

    def generate_structured(self, *, request):
        self.clock.value += self.duration
        if self.mutation:
            self.mutation(request.prompt_payload)
        return super().generate_structured(request=request)


def run_review(provider, clock, *, deadline=55.0, observation=None, factory=None):
    source = _source()
    authored = author.validate_greenfield_authoring_response(
        _response(source), evidence_text=source, elapsed_seconds=0.0,
        provider={"provider": "codex-cli", "model": "gpt-6-astra", "reasoning_effort": "medium"},
        profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=55.0,
        semantic_model_call_count=2,
    )
    return review.review_greenfield_candidate(
        evidence_text=source, candidate=_response(source)["result"], source_spans=authored.source_spans,
        profile_id=STANDARD_PROFILE_ID, provider_factory=factory or (lambda: provider),
        deadline=deadline, clock=clock,
        observation=observation if observation is not None else {},
    )


def test_partition_preserves_every_value_and_binds_complete_candidate():
    source = _source()
    candidate = _response(source)["result"]
    original = deepcopy(candidate)
    spans = author.validate_greenfield_authoring_response(
        _response(source), evidence_text=source, elapsed_seconds=0.0,
        provider={}, profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=55.0,
        semantic_model_call_count=2,
    ).source_spans
    payload = review.candidate_review_payload(source, candidate, source_spans=spans)
    assert {**payload["candidate"]["accepted_source"], **payload["candidate"]["proposed_decisions"]} == original
    assert payload["source"] == source
    assert payload["resolved_source_custody"]
    state_object_role = payload["role_definitions"]["state_object"]
    assert state_object_role == review.STATE_OBJECT_ROLE_DEFINITION
    assert state_object_role == author._AUTHORED_FACTS_SCHEMA["properties"][
        "state_object"
    ]["description"]
    assert "performer merely because it performs" in state_object_role
    proof_role = payload["role_definitions"]["proof_boundary"]
    assert proof_role == review.PROOF_BOUNDARY_ROLE_DEFINITION
    assert proof_role == author._AUTHORED_FACTS_SCHEMA["properties"]["proof_boundary"]["description"]
    assert "phrase or complete statement" in proof_role
    assert "do not reject a longer faithful span" in proof_role
    assert "purpose without an identified result is not proof" in proof_role
    product_story_role = payload["role_definitions"]["product_story"]
    assert product_story_role == review.PRODUCT_STORY_ROLE_DEFINITION
    assert product_story_role == author._AUTHORED_FACTS_SCHEMA["properties"][
        "product_story"
    ]["description"]
    assert "operator request" in product_story_role
    assert "title or category label" in product_story_role
    internal_role = payload["role_definitions"]["internal_systems"]
    assert internal_role == review.INTERNAL_SYSTEM_ROLE_DEFINITION
    assert internal_role == author._AUTHORED_FACTS_SCHEMA["properties"]["internal_systems"]["description"]
    assert "same owner, not a new component" in internal_role
    assert "Do not infer product ownership from a mere mention" in internal_role
    constraint_role = payload["role_definitions"]["operational_constraints"]
    assert constraint_role == review.OPERATIONAL_CONSTRAINT_ROLE_DEFINITION
    assert constraint_role == author._AUTHORED_FACTS_SCHEMA["properties"][
        "operational_constraints"
    ]["description"]
    assert "Each quote is projected independently" in constraint_role
    assert "governed subject" in constraint_role
    assert "required, prohibited or permitted behavior" in constraint_role
    assert "condition or scope" in constraint_role
    assert "contiguous source context before or after" in constraint_role
    assert "Do not require an explicit subject" in constraint_role
    assert "capability description alone is not an operational constraint" in constraint_role
    assert "source-custody control" in constraint_role
    assert "not by selecting or restating it as a product fact" in constraint_role
    assert "supplied source evidence, fixture, or candidate" in constraint_role
    assert "manages evidence, provenance, or source identity as domain data" in constraint_role
    assert "actual governed system and outcome" in constraint_role
    participant_role = payload["role_definitions"]["human_actors"]
    assert participant_role == author._AUTHORED_FACTS_SCHEMA["properties"]["human_actors"]["description"]
    assert "source-stated beneficiaries" in participant_role
    assert "does not establish a performing actor" in participant_role
    assert "Do not turn an activity or output purpose into a person." in payload["role_definitions"]["customer"]
    clock = Clock()
    provider = Reviewer(ADMITTED, clock, 7.0)
    receipt = run_review(provider, clock)
    assert candidate == original
    assert receipt["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    encoded = json.dumps(payload["candidate"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert receipt["candidate_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert receipt["elapsed_seconds"] == 7.0
    assert provider.calls == 1
    assert provider.requests[0].schema_name == "greenfield_candidate_review"


def test_review_request_makes_selected_source_location_authoritative():
    clock = Clock()
    provider = Reviewer(ADMITTED, clock)
    run_review(provider, clock)

    prompt = provider.requests[0].system_prompt
    assert "resolved_source_custody is the authoritative resolution" in prompt
    assert "Judge its semantic role at those exact byte offsets and surrounding context" in prompt
    assert "support from another occurrence of the same quote does not cure" in prompt


def test_review_request_does_not_invent_events_for_unowned_timing_conditions():
    clock = Clock()
    provider = Reviewer(ADMITTED, clock)
    run_review(provider, clock)

    prompt = provider.requests[0].system_prompt
    assert "both ordered sides are source-supported" in prompt
    assert "accepted events with actor/action ownership" in prompt
    assert "lack such event ownership as operational constraints" in prompt
    assert "never invent an event, action, or performer" in prompt
    assert "explicitly owns a disjunctive branch decision" in prompt
    assert "one accepted event owns both alternatives" in prompt
    assert "action_quote keeps only one branch verb" in prompt
    assert "complete joined action must remain one event" in prompt
    assert "nonempty substring is\nnot sufficient semantic custody" in prompt


def test_review_request_owns_coherent_branch_completeness():
    clock = Clock()
    provider = Reviewer(ADMITTED, clock)
    run_review(provider, clock)

    prompt = provider.requests[0].system_prompt
    assert "one coherent\nexecutable branch" in prompt
    assert "omits a source event required to complete that\nbranch" in prompt
    assert "concatenates mutually exclusive outcomes" in prompt
    assert "belong only to alternate branches" in prompt


def test_review_request_keeps_source_custody_out_of_product_meaning():
    clock = Clock()
    provider = Reviewer(ADMITTED, clock)
    run_review(provider, clock)

    prompt = provider.requests[0].system_prompt
    assert "supplied source evidence, fixture, or candidate as inputs" in prompt
    assert "source-custody controls, not product meaning" in prompt
    assert "restates or\nparaphrases it as an assumption, component, workstream" in prompt
    assert "product workflows that manage evidence" in prompt
    assert "actual\ngoverned system and outcome" in prompt


def test_human_subject_state_object_keeps_source_and_performer_custody_separate():
    source = "Harbor intake helps city staff register displaced residents."
    event = "city staff register displaced residents"
    intent = {
        "title": "Harbor intake",
        "product_story": source[:-1],
        "state_object": "displaced residents",
        "first_path": event,
        "proof_boundary": "displaced residents",
        "customer": "city staff",
        "human_actors": ["city staff", "displaced residents"],
        "assumptions": [
            {"applies_to": "problem", "statement": "Registration needs one intake path."},
            {"applies_to": "opportunity", "statement": "One intake path can reduce handoffs."},
            {"applies_to": "product_view", "statement": "Staff use one intake view."},
        ],
    }
    response = authored_response(
        intent,
        evidence_text=source,
        first_path_relations=[{
            "actor_kind": "human",
            "actor_fact_quote": "city staff",
            "event_quote": event,
            "action_verb_quote": "register",
            "target_quote": "displaced residents",
            "visible_result_quote": "displaced residents",
        }],
    )
    authored = author.validate_greenfield_authoring_response(
        response,
        evidence_text=source,
        elapsed_seconds=0.0,
        provider={},
        profile_id=STANDARD_PROFILE_ID,
        effective_timeout_seconds=55.0,
        semantic_model_call_count=2,
    )
    payload = review.candidate_review_payload(
        source,
        response["result"],
        source_spans=authored.source_spans,
    )

    accepted = payload["candidate"]["accepted_source"]
    assert accepted["facts"]["state_object"] == {
        "quote": "displaced residents",
        "prefix": "",
        "anchor_occurrence": 1,
    }
    assert accepted["events"][0] == {
        "actor_fact": {"field": "human_actors", "row": 1},
        "action_quote": "register",
        "target_quote": "displaced residents",
    }
    assert accepted["events"][0]["actor_fact"] != {"field": "human_actors", "row": 2}
    assert any(
        row["field"] == "state_object" and row["quote"] == "displaced residents"
        for row in payload["resolved_source_custody"]
    )


def test_title_actor_address_stays_hash_bound_before_canonical_product_translation():
    source = "Case Desk records a report for case staff."
    event = "Case Desk records a report"
    intent = {
        "title": "Case Desk",
        "product_story": source[:-1],
        "state_object": "a report",
        "first_path": event,
        "proof_boundary": "a report",
        "customer": "case staff",
        "assumptions": [
            {"applies_to": "problem", "statement": "Staff need a reviewable report."},
            {"applies_to": "opportunity", "statement": "One desk can reduce handoffs."},
            {"applies_to": "product_view", "statement": "Staff review one report view."},
        ],
    }
    response = authored_response(
        intent,
        evidence_text=source,
        first_path_relations=[{
            "actor_kind": "product",
            "actor_fact_path": "/title",
            "owner_system_quote": "Case Desk",
            "event_quote": event,
            "action_verb_quote": "records",
            "target_quote": "a report",
            "visible_result_quote": "a report",
        }],
    )
    authored = author.validate_greenfield_authoring_response(
        response,
        evidence_text=source,
        elapsed_seconds=0.0,
        provider={},
        profile_id=STANDARD_PROFILE_ID,
        effective_timeout_seconds=55.0,
        semantic_model_call_count=2,
    )
    payload = review.candidate_review_payload(
        source,
        response["result"],
        source_spans=authored.source_spans,
    )
    clock = Clock()
    admitted = deepcopy(ADMITTED)
    admitted["admission_witness"] = {
        "participant_fact": {"field": "customer", "row": 1},
        "task_event_order": 1,
        "result_event_order": 1,
    }
    receipt = review.review_greenfield_candidate(
        evidence_text=source,
        candidate=response["result"],
        source_spans=authored.source_spans,
        profile_id=STANDARD_PROFILE_ID,
        provider_factory=lambda: Reviewer(admitted, clock),
        deadline=55.0,
        clock=clock,
        observation={},
    )

    assert payload["candidate"]["accepted_source"]["events"] == [{
        "actor_fact": {"field": "title", "row": 1},
        "action_quote": "records",
        "target_quote": "a report",
    }]
    assert receipt["candidate_sha256"] == hashlib.sha256(
        json.dumps(
            payload["candidate"], sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()
    assert receipt["admission_witness"] == admitted["admission_witness"]
    relation = authored.first_path_relations[0]
    assert (relation["actor_kind"], relation["actor_fact_path"], relation["owner_system_path"]) == (
        "product", "/title", "/title",
    )


@pytest.mark.parametrize("constraint", [
    "The oversight team consists of auditors. They have read-only access.",
    "Auditors must never alter requests.",
    "The oversight team has read-only access only during intake.",
    "Never delete published notices.",
])
def test_self_contained_constraints_keep_exact_custody_without_a_new_shape(constraint):
    source = _source() + " " + constraint
    response = _response(_source())
    response["result"]["facts"]["operational_constraints"].append(
        {"quote": constraint, "occurrence": 1}
    )
    original = deepcopy(response)
    authored = author.validate_greenfield_authoring_response(
        response, evidence_text=source, elapsed_seconds=0.0,
        provider={}, profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=165.0,
        semantic_model_call_count=2,
    )
    assert authored.intent["operational_constraints"][-1] == constraint
    payload = review.candidate_review_payload(
        source, response["result"], source_spans=authored.source_spans,
    )
    constraint_spans = [row for row in payload["resolved_source_custody"]
                        if row["field"] == "operational_constraints"]
    span = constraint_spans[-1]
    assert span["quote"] == constraint
    assert source.encode()[span["source_start_byte"]:span["source_end_byte"]] == constraint.encode()
    schema = deepcopy(author._AUTHORED_FACTS_SCHEMA["properties"]["operational_constraints"])
    schema.pop("description")
    assert schema == author._TYPED_FACTS_SCHEMA["properties"]["operational_constraints"]
    assert response == original


def test_unknown_authority_is_not_silently_dropped():
    candidate = _response(_source())["result"]
    candidate["unclassified_authority"] = {}
    with pytest.raises(ValueError, match="authority"):
        review.candidate_review_payload(_source(), candidate, source_spans=())


def _span(source, quote, *, field="first_path", row=1, start=None):
    encoded, quoted = source.encode(), quote.encode()
    start = encoded.find(quoted) if start is None else start
    return {
        "section_key": field, "row_index": row, "text": quote,
        "source_start_byte": start, "source_end_byte": start + len(quoted),
    }


def test_utf8_context_is_bounded_by_characters_while_coordinates_remain_bytes():
    source = "é" * 70 + " target " + "文" * 70
    payload = review.candidate_review_payload(
        source, _response(_source())["result"], source_spans=(_span(source, "target"),),
    )
    custody = payload["resolved_source_custody"][0]
    assert custody["source_start_byte"] == len(("é" * 70 + " ").encode())
    assert custody["context_before"] == "é" * 63 + " "
    assert custody["context_after"] == " " + "文" * 63


def test_overlapping_source_spans_remain_distinct_context_rows():
    source = "prefix abcde suffix"
    first = _span(source, "abcd", row=1)
    second = _span(source, "cde", row=2, start=first["source_start_byte"] + 2)
    payload = review.candidate_review_payload(
        source, _response(_source())["result"], source_spans=(first, second),
    )
    assert [(row["row"], row["quote"]) for row in payload["resolved_source_custody"]] == [
        (1, "abcd"), (2, "cde"),
    ]


@pytest.mark.parametrize("mutation", [
    {"source_start_byte": -1}, {"source_end_byte": 10_000}, {"text": "other"},
    {"row_index": True}, {"section_key": ""},
])
def test_malformed_or_mutated_source_spans_fail_before_provider_dispatch(mutation):
    source = _source()
    span = _span(source, "training coordinators") | mutation
    provider = Reviewer(ADMITTED, Clock())
    with pytest.raises(ValueError, match="source span"):
        review.review_greenfield_candidate(
            evidence_text=source, candidate=_response(source)["result"], source_spans=(span,),
            profile_id=STANDARD_PROFILE_ID, provider_factory=lambda: provider,
            deadline=55.0, clock=Clock(), observation={},
        )
    assert provider.calls == 0


@pytest.mark.parametrize("verdict", [
    None, {}, {"admissible": "true", "issues": []}, {"admissible": True, "issues": [], "repair": {}},
    {"admissible": True, "issues": [{"path": "x", "reason": "y"}]},
    {"admissible": False, "issues": []},
    {"admissible": False, "issues": [{"path": "", "reason": "y"}]},
    {"admissible": False, "issues": [{"path": "x", "reason": "y"}] * 2},
    {"admissible": False, "issues": [{"path": "candidate.accepted_source", "reason": "Missing source constraint"}]},
])
def test_denial_or_malformed_verdict_never_repairs_or_retries(verdict):
    clock = Clock()
    provider = Reviewer(verdict, clock)
    observation = {}
    with pytest.raises(RuntimeError):
        run_review(provider, clock, observation=observation)
    assert provider.calls == 1
    assert observation["dispatched"] is True


def test_source_insufficient_actor_task_or_result_maps_to_first_path_clarification() -> None:
    clock = Clock()
    provider = Reviewer(
        {
            "outcome": "clarification_required",
            "issue": None,
            "clarification": {"material_dimension": "first_path"},
            "admission_witness": None,
        },
        clock,
    )
    with pytest.raises(review.GreenfieldCandidateClarificationRequired) as raised:
        run_review(provider, clock)

    assert raised.value.material_dimension == "first_path"
    assert raised.value.receipt["status"] == "clarification_required"
    assert set(raised.value.receipt) >= {"source_sha256", "candidate_sha256"}
    assert provider.calls == 1
    prompt = provider.requests[0].system_prompt
    assert (
        "first decide whether the source supplies the actor, usable-task, and\n"
        "visible-result facts"
    ) in prompt
    assert "candidate that omits or misrepresents\nthe fact is `denied`" in prompt
    assert "either leaves the fact absent or fills that gap" in prompt
    assert "select\n`first_path`;" in provider.requests[0].system_prompt
    assert "do not select `component_ownership`" in provider.requests[0].system_prompt
    assert "result needed to complete that path" in provider.requests[0].system_prompt
    assert "must participate in or benefit\nfrom the witnessed path" in prompt


def test_climate_source_without_user_result_is_reviewed_as_first_path_clarification() -> None:
    source = (
        "Create a reviewed climate product. Source repository: meteostat/meteostat. "
        "Source evidence: climate. Repository description: Access and analyze historical "
        "weather and climate data with Python."
    )
    candidate = {
        "status": "authored",
        "facts": {
            "title": {"quote": "climate product", "context": "reviewed climate product"},
            "product_story": {
                "quote": "Access and analyze historical weather and climate data with Python",
                "context": "Access and analyze historical weather and climate data with Python.",
            },
            "state_object": {
                "quote": "historical weather and climate data",
                "context": "Access and analyze historical weather and climate data with Python.",
            },
            "human_actors": [],
        },
        "events": [
            {"actor_kind": "product", "action_quote": "Access"},
            {"actor_kind": "product", "action_quote": "analyze"},
        ],
        "components": [],
        "terminal": None,
        "source_precedence": [],
        "consistency": {"status": "consistent", "evidence_quotes": []},
        "ambiguities": ["The source does not state who uses the product or what result they see."],
        "assumptions": [],
        "provisional_design": {},
    }
    clock = Clock()
    provider = Reviewer(
        {
            "outcome": "clarification_required",
            "issue": None,
            "clarification": {"material_dimension": "first_path"},
            "admission_witness": None,
        },
        clock,
    )

    with pytest.raises(review.GreenfieldCandidateClarificationRequired) as raised:
        review.review_greenfield_candidate(
            evidence_text=source,
            candidate=candidate,
            source_spans=(
                _span(
                    source,
                    "Access and analyze historical weather and climate data with Python",
                    field="product_story",
                ),
            ),
            profile_id=STANDARD_PROFILE_ID,
            provider_factory=lambda: provider,
            deadline=55.0,
            clock=clock,
            observation={},
        )

    assert raised.value.material_dimension == "first_path"
    assert raised.value.receipt["status"] == "clarification_required"
    assert provider.calls == 1
    assert provider.requests[0].prompt_payload["source"] == source
    reviewed = provider.requests[0].prompt_payload["candidate"]
    assert {**reviewed["accepted_source"], **reviewed["proposed_decisions"]} == candidate


def test_source_without_participant_or_terminal_cannot_be_admitted_by_fabricated_witness() -> None:
    source = (
        "Create a reviewed healthcare product. Source evidence: healthcare. "
        "Repository description: Unify wearable health data."
    )
    candidate = {
        "status": "authored",
        "facts": {
            "title": {"quote": "healthcare product"},
            "product_story": {"quote": "Unify wearable health data"},
            "state_object": {"quote": "wearable health data"},
            "customer": None,
            "human_actors": [],
            "external_systems": [],
        },
        "events": [{"actor_kind": "product", "action_quote": "Unify"}],
        "components": [],
        "terminal": None,
        "source_precedence": [],
        "consistency": {"status": "consistent", "evidence_quotes": []},
        "ambiguities": [],
        "assumptions": [
            {"applies_to": "customer", "statement": "A developer uses the product."},
        ],
        "provisional_design": {},
    }
    clock = Clock()
    provider = Reviewer(
        {
            "outcome": "admitted",
            "issue": None,
            "clarification": None,
            "admission_witness": {
                "participant_fact": {"field": "human_actors", "row": 1},
                "task_event_order": 1,
                "result_event_order": 1,
            },
        },
        clock,
    )

    with pytest.raises(RuntimeError, match="invalid admission witness"):
        review.review_greenfield_candidate(
            evidence_text=source,
            candidate=candidate,
            source_spans=(
                _span(source, "healthcare product", field="title"),
                _span(
                    source,
                    "Unify wearable health data",
                    field="product_story",
                ),
                _span(
                    source,
                    "wearable health data",
                    field="state_object",
                ),
            ),
            profile_id=STANDARD_PROFILE_ID,
            provider_factory=lambda: provider,
            deadline=55.0,
            clock=clock,
            observation={},
        )

    assert provider.calls == 1


@pytest.mark.parametrize("scope", ["source", "resolved_source_custody", "accepted_source", "proposed_decisions"])
def test_review_cannot_mutate_evidence_or_either_authority(scope):
    def mutate(payload):
        if scope == "source":
            payload["source"] += "New authority"
        elif scope == "resolved_source_custody":
            payload[scope][0]["quote"] += "New authority"
        else:
            payload["candidate"][scope]["extra"] = "New authority"
    clock = Clock()
    provider = Reviewer(ADMITTED, clock, mutation=mutate)
    with pytest.raises(RuntimeError, match="changed"):
        run_review(provider, clock)


def test_reviewer_setup_and_dispatch_use_remaining_absolute_deadline():
    clock = Clock()
    clock.value = 45.0
    provider = Reviewer(ADMITTED, clock, 5.0)
    def factory():
        clock.value += 2.0
        return provider
    receipt = run_review(provider, clock, factory=factory)
    assert provider.requests[0].timeout_seconds == 8.0
    assert receipt["elapsed_seconds"] == 5.0
    assert clock.value == 52.0


def test_reviewer_dispatch_elapsed_excludes_setup_but_keeps_shared_deadline():
    clock = Clock()
    provider = Reviewer(ADMITTED, clock, 3.0)
    observation = {}

    def factory():
        clock.value += 6.0
        return provider

    receipt = run_review(
        provider, clock, factory=factory, deadline=10.0, observation=observation,
    )
    assert provider.requests[0].timeout_seconds == 4.0
    assert receipt["elapsed_seconds"] == 3.0
    assert observation["elapsed_seconds"] == 3.0
    assert clock.value == 9.0


@pytest.mark.parametrize("setup", [False, True])
def test_no_budget_means_no_review_dispatch(setup):
    clock = Clock()
    clock.value = 54.5 if not setup else 53.0
    provider = Reviewer(ADMITTED, clock)
    def factory():
        clock.value += 1.5
        return provider
    observation = {}
    with pytest.raises(RuntimeError, match="time"):
        run_review(provider, clock, factory=factory, observation=observation)
    assert provider.calls == 0
    assert "dispatched" not in observation


def test_review_can_use_more_than_twenty_seconds_inside_the_shared_deadline():
    clock = Clock()
    provider = Reviewer(ADMITTED, clock, 23.0)
    receipt = run_review(provider, clock)
    assert receipt["elapsed_seconds"] == 23.0
    assert provider.requests[0].timeout_seconds == 55.0


@pytest.mark.parametrize("duration", [55.001, 60.0])
def test_late_response_fails_after_one_actual_call(duration):
    clock = Clock()
    provider = Reviewer(ADMITTED, clock, duration)
    with pytest.raises(RuntimeError, match="time window"):
        run_review(provider, clock)
    assert provider.calls == 1


@pytest.mark.parametrize("started,duration", [(0.0, 55.001), (45.0, 10.001)])
@pytest.mark.parametrize("response", [None, ADMITTED])
def test_late_review_retains_provider_evidence_without_admitting_or_retrying(started, duration, response):
    clock = Clock()
    clock.value = started
    provider = Reviewer(response, clock, duration)
    provider.last_failure_code = "timeout" if response is None else ""
    provider.last_failure_detail = "Codex CLI exceeded its request budget." if response is None else ""
    observation = {}
    with pytest.raises(RuntimeError, match="exceeded its model time window"):
        run_review(provider, clock, observation=observation)
    assert provider.calls == 1
    assert observation["response"] == response
    assert observation["provider"] == review.odylith_reasoning.provider_failure_metadata(provider)
    assert observation["provider"]["model"] == "gpt-6-astra"
    assert observation["provider"]["reasoning_effort"] == "medium"
    assert observation["provider"]["code"] == ("timeout" if response is None else "")
    assert observation["elapsed_seconds"] == pytest.approx(duration)


def test_native_author_requires_admission_and_preserves_source_and_design():
    source = _source()
    response = _response(source)
    clock = Clock()
    provider = RemainingCandidateProvider(response)
    participant = provider.participant_provider()
    reviewer = Reviewer(ADMITTED, clock, 4.0)
    result = participant_authoring.author_greenfield_intent(
        evidence_text=source, provider=provider,
        participant_provider_factory=lambda: participant,
        clock=clock, review_provider_factory=lambda: reviewer,
    )
    assert participant.calls == provider.calls == reviewer.calls == 1
    assert result.semantic_model_call_count == 3
    assert result.provisional_design == response["result"]["provisional_design"]
    assert result.source_sha256 == result.candidate_review["source_sha256"]
    assert result.elapsed_seconds == 4.0


def test_no_review_provider_cannot_return_authored_success():
    with pytest.raises(author.GreenfieldModelAuthoringError, match="unavailable"):
        provider = RemainingCandidateProvider(_response(_source()))
        participant_authoring.author_greenfield_intent(
            evidence_text=_source(), provider=provider,
            participant_provider_factory=provider.participant_provider,
        )


def test_structural_validation_cannot_change_the_reviewed_candidate(monkeypatch):
    validate = author.validate_greenfield_authoring_response
    def mutate(response, **kwargs):
        authored = validate(response, **kwargs)
        response["result"]["assumptions"].append({"applies_to": "general", "statement": "Altered"})
        return authored
    monkeypatch.setattr(participant_authoring, "validate_greenfield_authoring_response", mutate)
    with pytest.raises(author.GreenfieldModelAuthoringError, match="validation changed"):
        provider = RemainingCandidateProvider(_response(_source()))
        participant_authoring.author_greenfield_intent(
            evidence_text=_source(), provider=provider,
            participant_provider_factory=provider.participant_provider,
            review_provider_factory=AdmittingReviewProvider,
        )


def test_review_postvalidation_deadline_is_enforced(monkeypatch):
    clock = Clock()
    provider = Reviewer(ADMITTED, clock, 19.0)
    validate = review.require_greenfield_model_profile_observation
    def slow_validation(**kwargs):
        result = validate(**kwargs)
        if provider.calls:
            clock.value += 2.0
        return result
    monkeypatch.setattr(review, "require_greenfield_model_profile_observation", slow_validation)
    with pytest.raises(RuntimeError, match="exceeded.*time window"):
        run_review(provider, clock, deadline=20.0)
    assert provider.calls == 1


def test_review_finalization_cannot_admit_a_late_role():
    ticks = iter((0.0, 0.0, 54.9, 54.9, 54.9, 55.1))
    clock = lambda: next(ticks, 55.1)
    provider = StructuredAuthoringProvider(ADMITTED)
    observation = {}
    with pytest.raises(RuntimeError, match="exceeded its model time window"):
        run_review(provider, clock, observation=observation)
    assert provider.calls == 1
    assert observation["elapsed_seconds"] == pytest.approx(0.2)


@pytest.mark.parametrize("role", ["participant", "author", "reviewer"])
def test_actual_dispatch_count_survives_provider_exception(monkeypatch, role):
    class Unavailable(StructuredAuthoringProvider):
        def generate_structured(self, *, request):
            self.calls += 1
            raise TimeoutError("Provider did not return")
    observations = []
    monkeypatch.setattr(
        participant_authoring,
        "emit_greenfield_model_proof_observation",
        lambda **kwargs: observations.append(kwargs),
    )
    provider = (
        Unavailable(_response(_source()))
        if role == "author"
        else RemainingCandidateProvider(_response(_source()))
    )
    participant_factory = (
        (lambda: Unavailable(None))
        if role == "participant"
        else provider.participant_provider
    )
    with pytest.raises(author.GreenfieldModelAuthoringError):
        participant_authoring.author_greenfield_intent(
            evidence_text=_source(), provider=provider,
            participant_provider_factory=participant_factory,
            review_provider_factory=(
                (lambda: Unavailable(None)) if role == "reviewer" else AdmittingReviewProvider
            ),
        )
    assert observations[-1]["semantic_model_call_count"] == {
        "participant": 1,
        "author": 2,
        "reviewer": 3,
    }[role]
