from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import confirmed_project_brief
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import _first_path_step_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_project_brief import normalize_project_brief
from odylith.runtime.domain_intelligence.greenfield_project_brief import project_brief_issues
from odylith.runtime.domain_intelligence.greenfield_project_brief import render_project_brief_lines


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def _proposal_from_guidance_prompt(prompt: str) -> dict[str, object]:
    intent_text = f"""Product Intent Confirmation needed
No files changed. Source posture: empty_or_no_app_source.

Visible format contract
- Render the visible confirmation as sectioned Markdown.

Original user intent
{prompt}
Next step
- Confirm.
"""
    intent = parse_confirmed_intent_text(intent_text, prompt=prompt)
    return build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=str(intent["title"]),
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )


def test_confirmed_project_brief_checkpoint_done_when_text_is_checkpoint_specific() -> None:
    brief = confirmed_project_brief(
        label="Shelter Capacity Router",
        prompt="Create a shelter capacity router.",
        release="0.0.1",
        state_object="Shelter intake status record",
        evidence_record="Resident routing proof record",
        product_story="City staff need one place to route residents to available shelter capacity.",
        first_path="A staff member records capacity, blocks an unsafe intake, and routes a family to an available shelter.",
        proof_boundary="Release 0.0.1 proves one reviewable shelter routing handoff with replay evidence.",
        human_actors=["City emergency staff", "Shelter coordinator"],
        internal_systems=["Capacity intake service", "Routing review workspace", "Proof ledger"],
    )

    done_when = [row["done_when"] for row in brief["pre_coding_checkpoints"]]

    assert len(done_when) == len(set(done_when))
    assert "The answer is visible in the accepted proposal" not in json.dumps(brief)


def test_project_brief_rendering_stays_in_project_brief_owner() -> None:
    proposal_source = (DOMAIN_INTELLIGENCE / "proposal_rendering.py").read_text(encoding="utf-8")
    owner_source = (DOMAIN_INTELLIGENCE / "greenfield_project_brief.py").read_text(encoding="utf-8")

    assert (
        "from odylith.runtime.domain_intelligence.greenfield_project_brief import render_project_brief_lines"
        in proposal_source
    )
    assert "def render_project_brief_lines(" in owner_source
    assert "def _project_brief_lines(" not in proposal_source
    for moved in (
        "def _blueprint_section_lines(",
        "def _project_option_lines(",
        "def _project_checkpoint_lines(",
        "def _project_path_lines(",
    ):
        assert moved not in proposal_source
        assert moved in owner_source
    assert "from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows" in owner_source


def test_project_brief_rendering_uses_shared_row_coercion_and_keeps_plain_lines() -> None:
    brief = {
        "project_outcome": "Residents can submit repair requests and see a reviewable status trail.",
        "operating_principle": "Write only the first path that proves the accepted product promise.",
        "review_posture": "Review the product direction before implementation starts.",
        "blueprint_sections": [
            {
                "section": "First repair path",
                "must_capture": "Resident request, staff triage, status update, and review result.",
                "why_it_matters": "It proves the workflow without wider property-management scope.",
            },
            "not a row",
        ],
        "customization_options": [
            {
                "decision": "Proof depth",
                "recommended": "Require a status timeline before coding.",
                "choices": ["timeline", "notification", ""],
                "impact": "Changes the first release gate.",
            }
        ],
        "customization_prompts": ["Focus the first release on blocked-input recovery."],
        "pre_coding_checkpoints": [
            {
                "checkpoint": "Status evidence",
                "operator_question": "Which status proves the request is reviewable?",
                "done_when": "Done when the first release names that status and its reviewer.",
            }
        ],
        "coding_readiness_gates": ["The first path has a blocked-input and recovery proof."],
        "host_independent_paths": [
            {
                "path": "Review the creation-ready transaction",
                "command": "odylith greenfield propose --repo-root . --prompt 'resident repair workspace'",
                "works_in": "Codex and Claude Code",
                "use_when": "Odylith compiles and validates the package before showing CONFIRM, EDIT, and REJECT.",
            }
        ],
    }

    lines = render_project_brief_lines(brief)

    assert "## Project Design Board" in lines
    assert "## Governance Package" in lines
    assert (
        "- First repair path: Resident request, staff triage, status update, and review result. "
        "Why: It proves the workflow without wider property-management scope."
    ) in lines
    assert "  - Proof depth: Require a status timeline before coding.\n    - Options: timeline, notification.\n    - Impact: Changes the first release gate." in lines
    assert (
        "  - Status evidence: Which status proves the request is reviewable; "
        "done when the first release names that status and its reviewer."
    ) in lines
    assert "done when Done when" not in "\n".join(lines)
    assert (
        "  - Review the creation-ready transaction: `odylith greenfield propose --repo-root . --prompt "
        "'resident repair workspace'` (Codex and Claude Code)"
    ) in lines
    assert not any("greenfield compile-transaction" in line for line in lines)
    assert not any("odylith greenfield create" in line for line in lines)
    assert all("not a row" not in line for line in lines)


def test_project_brief_rendering_splits_long_blueprint_rationale_rows() -> None:
    lines = render_project_brief_lines(
        {
            "blueprint_sections": [
                {
                    "section": "Product story",
                    "must_capture": (
                        "Homeowners need to compare roof fit, usage, incentives, quotes, financing, and savings "
                        "before selecting a solar installation plan"
                    ),
                    "why_it_matters": (
                        "Readers need to understand the product, user, problem, and real-world outcome before "
                        "implementation boundaries appear."
                    ),
                }
            ]
        }
    )
    rendered = "\n".join(lines)

    assert "Product story: Homeowners need to compare roof fit" in rendered
    assert "\n  - Why: Readers need to understand" in rendered
    assert "installation plan Why:" not in rendered


def test_project_brief_rendering_separates_rationale_after_unpunctuated_detail() -> None:
    lines = render_project_brief_lines(
        {
            "blueprint_sections": [
                {
                    "section": "First path",
                    "must_capture": "Permit reviewers can track applications and publish decisions",
                    "why_it_matters": "A narrow first path keeps the first release testable and prevents broad platform drift.",
                }
            ]
        }
    )

    assert (
        "- First path: Permit reviewers can track applications and publish decisions\n"
        "  - Why: A narrow first path keeps the first release testable and prevents broad platform drift."
    ) in lines
    assert not any("decisions Why:" in line for line in lines)


def test_confirmed_project_brief_does_not_clip_article_modifier_tail_from_broad_prompt() -> None:
    proposal = _proposal_from_guidance_prompt("Draft a greenfield proposal for a training roster readiness hub")
    brief = proposal["project_brief"]
    readiness_copy = json.dumps(brief["coding_readiness_gates"], sort_keys=True)

    assert "a reviewable." not in readiness_copy
    assert "product shows." not in readiness_copy
    assert "the product shows a result" not in readiness_copy
    assert generated_public_copy_issues("training roster project brief", brief) == ()


def test_confirmed_project_brief_drops_clipped_comma_list_tail_from_readiness_gate() -> None:
    brief = confirmed_project_brief(
        label="Multi-party Security Disclosure Council Workspace",
        prompt="Create a security disclosure council.",
        release="0.0.1",
        state_object="Disclosure council result record",
        evidence_record="Disclosure proof record",
        product_story=(
            "Multi-party Security Disclosure Council Workspace helps a multi-party security disclosure council "
            "workspace user complete a first path where a multi-party security disclosure council workspace user "
            "can coordinate external vulnerability reports, affected partner review, embargo decisions, evidence "
            "custody, legal signoff, and public advisory release readiness without personalized notification "
            "campaigns in the first release."
        ),
        first_path=(
            "A multi-party security disclosure council workspace user can coordinate external vulnerability "
            "reports, affected partner review, embargo decisions, evidence custody, legal signoff, and public "
            "advisory release readiness without personalized notification campaigns in the first release."
        ),
        proof_boundary=(
            "Release 0.0.1 succeeds when the disclosure council can review the release path with evidence, "
            "legal signoff, and replayable proof."
        ),
        human_actors=["Multi-party Security Disclosure Council Workspace User"],
        internal_systems=["Disclosure intake register", "Disclosure review workspace", "Disclosure proof ledger"],
    )
    readiness_copy = json.dumps(brief["coding_readiness_gates"], sort_keys=True)

    assert "reports, affected." not in readiness_copy
    assert "external vulnerability reports, affected partner review" in readiness_copy
    assert "without personalized notification campaigns in the first release." in readiness_copy
    assert generated_public_copy_issues("security disclosure project brief", brief) == ()


def test_confirmed_project_brief_skips_short_scope_preface_for_project_outcome() -> None:
    intent = {
        "title": "Project Coordination Workspace",
        "product_story": (
            "This workspace helps operators turn a broad objective into a coordinated project path with "
            "visible state, validation, review, and handoff evidence."
        ),
        "state_object": (
            "A project execution record that tracks the objective, task assignments, validation results, "
            "review decisions, blockers, and final handoff."
        ),
        "first_path": (
            "An operator submits an objective, the workspace creates a bounded plan, assigned roles complete "
            "tasks, validation checks the result, and a reviewer approves the final handoff."
        ),
        "proof_boundary": (
            "The proof should not claim production readiness yet. The first credible proof is one complete "
            "workflow where an operator submits an objective, the system records state, validation catches "
            "or confirms outcomes, and a reviewer can approve the result."
        ),
        "human_actors": [
            "Operator: submits the objective and watches progress",
            "Reviewer: approves or rejects the final handoff",
        ],
        "internal_systems": [
            "Planning Workspace",
            "Task Assignment Register",
            "Validation Evidence Ledger",
        ],
    }

    proposal = build_confirmed_greenfield_proposal(
        prompt="a workspace for coordinated project execution",
        title="Project Coordination Workspace",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    brief = proposal["project_brief"]

    assert "one complete workflow" in brief["project_outcome"]
    assert word_count(brief["project_outcome"]) >= 10
    assert project_brief_issues(brief) == []


def test_project_brief_normalization_repairs_shallow_outcome_from_accepted_intent() -> None:
    normalized = normalize_project_brief(
        {"project_outcome": "The proof should not claim production readiness yet."},
        intent={
            "title": "Project Coordination Workspace",
            "first_path": "An operator submits an objective and reviews a validated handoff.",
            "proof_boundary": (
                "The proof should not claim production readiness yet. The first credible proof is a complete "
                "reviewable path with accepted input, visible state, validation evidence, and an approved result."
            ),
            "state_object": "Project execution record",
        },
        release_selector="0.0.1",
    )

    assert "complete reviewable path" in normalized["project_outcome"]
    assert word_count(normalized["project_outcome"]) >= 10


def test_project_brief_normalization_repairs_raw_prompt_echoes() -> None:
    raw_prompt = "Build an ecommerce checkout recovery product"
    normalized = normalize_project_brief(
        {
            "purpose": (
                "Build An Ecommerce Checkout Recovery Product helps the first user complete one reviewable "
                "product path without losing state, owner, failure, or evidence context."
            ),
            "project_outcome": (
                "A reviewer can inspect the Build An Ecommerce Checkout Recovery Product first path, state "
                "change, evidence, non-goals, and release decision before implementation expands scope."
            ),
            "coding_readiness_gates": [
                "Build An Ecommerce Checkout Recovery Product has an accepted product story with actors, systems, first path, and unresolved assumptions.",
                "The first implementation lane maps to one workstream, one component boundary, one diagram path, and one proof gate.",
                "Every external dependency is fixture-backed, sandboxed, source-backed, or explicitly deferred before source edits start.",
                "The release plan names promotion criteria and does not claim production readiness beyond the accepted first path.",
            ],
        },
        intent={
            "prompt": raw_prompt,
            "title": "Build An Ecommerce Checkout Recovery Product",
            "first_path": "A shopper resumes checkout, fixes payment or address errors, and sees a saved recovery result.",
            "proof_boundary": "Release 0.0.1 proves one checkout recovery path with replay and blocked-input evidence.",
            "state_object": "Checkout recovery record",
        },
        release_selector="0.0.1",
    )

    encoded = json.dumps(
        {
            "purpose": normalized["purpose"],
            "project_outcome": normalized["project_outcome"],
            "coding_readiness_gates": normalized["coding_readiness_gates"],
        },
        sort_keys=True,
    ).casefold()
    assert raw_prompt.casefold() not in encoded
    assert "Ecommerce Checkout Recovery Product" in normalized["purpose"]
    assert "Release 0.0.1 proves Ecommerce Checkout Recovery Product" in normalized["project_outcome"]
    assert project_brief_issues(
        {
            **normalized,
            "operating_principle": "Every release claim stays tied to state, result, evidence, recovery, and review.",
            "blueprint_sections": [
                {"section": "Story", "must_capture": "Accepted product facts", "why_it_matters": "Avoids prompt leakage."}
            ]
            * 4,
            "customization_options": [
                {
                    "id": f"option-{index}",
                    "decision": "Boundary",
                    "recommended": "Keep the first path narrow.",
                    "choices": ["narrow", "broad"],
                    "impact": "Controls release proof.",
                }
                for index in range(5)
            ],
            "customization_prompts": [
                "Change the first user if this actor is wrong.",
                "Change the state object if ownership is wrong.",
                "Change the proof boundary if release evidence is wrong.",
            ],
            "pre_coding_checkpoints": [
                {
                    "checkpoint": f"Checkpoint {index}",
                    "operator_question": "Is the accepted path still true?",
                    "done_when": "The answer is recorded.",
                }
                for index in range(4)
            ],
            "host_independent_paths": [
                {"path": "Confirm", "command": "odylith greenfield propose", "works_in": "shell", "use_when": "Before writes."}
            ]
            * 3,
        }
    ) == []


def test_project_brief_long_outcome_uses_state_object_label_not_state_sentence() -> None:
    normalized = normalize_project_brief(
        {
            "project_outcome": (
                "A participant records symptoms, triggers, chosen practice steps, check-in results, safety boundaries, "
                "and progress evidence before the first release proves the accepted path."
            )
        },
        intent={
            "title": "Daily Comfort Practice Coach",
            "first_path": (
                "A participant records symptoms, triggers, chosen practice steps, check-in results, safety boundaries, "
                "and progress evidence."
            ),
            "proof_boundary": "Release 0.0.1 proves one accepted Daily Comfort Practice Coach path.",
            "state_object": "A daily comfort practice coach result record tracks the actor, source, status, result, and recovery context.",
        },
        release_selector="0.0.1",
    )

    assert "and A daily comfort practice coach result record tracks" not in normalized["project_outcome"]
    assert "Daily Comfort Practice Coach Result Record" in normalized["project_outcome"]
    assert generated_public_copy_issues("project outcome", normalized["project_outcome"]) == ()


def test_project_brief_outcome_avoids_cross_sentence_title_state_duplication() -> None:
    brief = confirmed_project_brief(
        label="Volcanic Ash Aviation",
        prompt="volcanic ash aviation advisory",
        release="0.0.1",
        state_object="An aviation advisory update record tracks status, owner, blocker, handoff, and evidence.",
        evidence_record="Volcanic Ash Aviation Proof Ledger",
        first_path=(
            "Aviation meteorologist can open the ash advisory episode, record satellite, plume, and dispersion "
            "evidence, escalate forecast review, resolve exceptions, and publish the aviation advisory update "
            "without automating expert judgment."
        ),
        proof_boundary=(
            "Release 0.0.1 succeeds when aviation meteorologist can open the ash advisory episode, record satellite, "
            "plume, and dispersion evidence, escalate forecast review, resolve exceptions, and publish the aviation "
            "advisory update without automating expert judgment. The product shows the aviation advisory update."
        ),
        human_actors=["Aviation Meteorologist"],
        internal_systems=("Volcanic Ash Aviation Intake Register", "Volcanic Ash Aviation Proof Ledger"),
    )

    assert "Aviation Aviation" not in brief["project_outcome"]
    assert "accepted first path for Volcanic Ash Aviation" in brief["project_outcome"]
    assert generated_public_copy_issues("project outcome", brief["project_outcome"]) == ()
    encoded = json.dumps(brief, sort_keys=True)
    assert "Volcanic Ash Aviation: Aviation meteorologist" not in encoded
    assert "Aviation Aviation" not in encoded


def test_project_brief_outcome_compacts_field_heavy_state_object() -> None:
    normalized = normalize_project_brief(
        {
            "project_outcome": (
                "Release 0.0.1 succeeds when one corridor request can be recorded, reviewed against landing "
                "and safety constraints, assigned a route readiness decision, replayed with evidence history, "
                "and published as a stakeholder-safe public status while deferred external feeds and autonomous "
                "flight control stay outside the claim."
            )
        },
        intent={
            "title": "Regional Drone Corridor Safety Console",
            "first_path": "A coordinator records a request and a reviewer publishes corridor status.",
            "proof_boundary": (
                "Release 0.0.1 succeeds when one corridor request can be recorded, reviewed against landing "
                "and safety constraints, assigned a route readiness decision, replayed with evidence history, "
                "and published as a stakeholder-safe public status while deferred external feeds and autonomous "
                "flight control stay outside the claim."
            ),
            "state_object": (
                "The core state object is a corridor readiness record with route segment, requesting organization, "
                "receiving site, operating window, restriction checks, landing-window status, waiver notes, "
                "decision owner, public status, and evidence history."
            ),
        },
        release_selector="0.0.1",
    )

    outcome = normalized["project_outcome"]
    assert outcome.endswith("review evidence together.")
    assert not outcome.rstrip(" .").endswith("and")
    assert "Corridor Readiness Record, blocked-path evidence" in outcome
    assert "Waiver Notes" not in outcome
    assert generated_public_copy_issues("project outcome", outcome) == ()


def test_project_brief_renderer_keeps_comma_heavy_story_as_coherent_sentence() -> None:
    lines = render_project_brief_lines(
        {
            "project_outcome": "Release 0.0.1 proves the accepted path.",
            "blueprint_sections": [
                {
                    "section": "Product story",
                    "must_capture": (
                        "Daily Comfort Practice Coach helps a participant complete a first path where a participant records symptoms, "
                        "triggers, chosen practice steps, check-in results, safety boundaries, and progress evidence. It keeps the "
                        "daily comfort practice coach result tied to source input and proof evidence so the next step is clear."
                    ),
                    "why_it_matters": "Readers need one coherent product story before implementation boundaries appear.",
                }
            ],
        }
    )
    rendered = "\n".join(lines)

    assert "\n  - Chosen practice steps" not in rendered
    assert "\n  - Check-in results" not in rendered
    assert "records symptoms, triggers, chosen practice steps, check-in results" in rendered


def test_project_brief_renderer_preserves_lower_first_source_symbol_at_fragment_start() -> None:
    lines = render_project_brief_lines(
        {
            "blueprint_sections": [
                {
                    "section": "Product story",
                    "must_capture": (
                        "mRNA Stability Batch Comparison Workspace helps a formulation scientist complete a first path "
                        "using accelerated-stability data, lipid ratio records, impurity profiles, storage excursions, "
                        "explicit expert review, auditable decisions, and a final recommendation."
                    ),
                    "why_it_matters": "Readers need the source-owned scientific symbol to stay legible.",
                }
            ],
        }
    )
    rendered = "\n".join(lines)

    assert "mRNA Stability Batch Comparison Workspace helps" in rendered
    assert "MRNA Stability" not in rendered


def test_confirmed_project_brief_keeps_evidence_list_out_of_sentence_splices() -> None:
    proposal = _proposal_from_guidance_prompt(
        "Create a greenfield proposal for autonomous shuttle disengagement. Focus on a governed workflow "
        "where the mobility operations lead turns an ambiguous disengagement event into a review-ready record "
        "using vehicle logs, scene annotation, remote-operator notes, weather context, explicit expert review, "
        "auditable decision ledger, and a final disengagement review recommendation. The request uses record "
        "both as an action and as a governed object, so ownership must be explicit. A product manager must see "
        "the first complete path, actor value, non-goals, and success metrics. The post-confirm create must "
        "finish all project and governance artifacts under the standard budget."
    )
    first_path = proposal["project_brief"]["blueprint_sections"][1]["must_capture"]

    assert "using vehicle logs, scene annotation, remote-operator notes, weather context" in first_path
    assert "explicit expert review" in first_path
    assert "final disengagement review recommendation" in first_path
    assert ". And" not in first_path
    assert ". Or" not in first_path
    assert "Explicit expert review, auditable decision ledger" not in first_path
    assert generated_public_copy_issues("project brief preview", proposal["project_brief"]) == ()


def test_first_path_summary_merges_connector_led_rows_before_sentence_join() -> None:
    summary = _first_path_step_summary(
        [
            "A coordinator handles an accept, decline",
            "Or more-info request",
            "And a final recommendation",
        ],
        limit=240,
    )

    assert summary == "A coordinator handles an accept, decline, or more-info request, and a final recommendation"
    assert ". Or" not in summary
    assert ". And" not in summary


def test_confirmed_project_brief_preserves_long_component_label_tails() -> None:
    component_labels = [
        "Annealing Result Review Console for QUBO models, Ising models, baseline comparisons, and reproducibility evidence",
        "Solver Access Control Plane for D-Wave Leap credentials, simulator fallback, queue visibility, and run imports",
        "Physical Lab Operations Register for workstations, access state, equipment notes, and operational handoffs",
    ]
    brief = confirmed_project_brief(
        label="Quantum Annealing Research Lab",
        prompt="quantum annealing research lab",
        release="0.0.1",
        state_object="An experiment package tracks model, backend, parameters, results, baseline, and review evidence.",
        evidence_record="Experiment review evidence packet",
        product_story=(
            "Research teams need one governed lab workflow for annealing experiments, physical lab readiness, "
            "baseline comparison, and reproducibility review."
        ),
        first_path=(
            "A researcher defines a small optimization problem, formulates it for annealing, records parameters, "
            "runs or imports results, compares them with a classical baseline, and publishes a review packet."
        ),
        proof_boundary=(
            "Release 0.0.1 succeeds when one experiment package can be reviewed with baseline comparison, "
            "uncertainty notes, and reproducibility evidence without claiming quantum advantage."
        ),
        human_actors=["Research scientist", "Lab operator", "Reviewer"],
        internal_systems=["Experiment registry", "Backend control plane", "Run ledger", "Review board"],
        component_labels=component_labels,
    )

    component_gate = next(
        gate for gate in brief["coding_readiness_gates"] if "components come from product systems" in gate
    )

    for label in component_labels:
        assert label in component_gate
    assert "Annealing Result Review Console, Solver Access Control Plane" not in component_gate
