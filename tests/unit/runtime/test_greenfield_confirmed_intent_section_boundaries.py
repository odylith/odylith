from __future__ import annotations

import json

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text


def test_confirmed_intent_ignores_noncanonical_sections_and_prose_next_step() -> None:
    intent = parse_confirmed_intent_text(
        """# Quantum Annealing Research Lab - Product Intent Confirmation

## Product Story
Build a combined software and physical research lab for professional quantum annealing operations. The product lets a research team plan experiments, manage backend access, compare annealing results with classical baselines, and preserve evidence for reproducible research.

## State Object
An experiment package tracks research question, QUBO or Ising formulation, source data, backend target, annealing parameters, result samples, baseline comparison, reviewer notes, reproducibility evidence, physical lab context, blockers, and version history.

## First Complete Path
A researcher defines a small optimization problem, formulates it for annealing, selects D-Wave Leap or a simulator fallback, records parameters, submits or imports a run, compares the result to a classical baseline, and produces a review package another researcher can reproduce or reject.

## Human Actors
- Research scientist: designs experiments, interprets results, and owns scientific claims.
- Lab operator: manages backend access, workstation readiness, credentials, run scheduling, and operational blockers.
- Reviewer or collaborator: audits methods, baselines, assumptions, and repeatability.

## External Systems
- D-Wave Leap for quantum annealing and hybrid solver access.
- D-Wave Ocean SDK for model submission and result handling.
- Classical optimizer baseline tooling for comparison.

## Internal Product Systems
- Experiment registry for research questions, model versions, owners, and status.
- Backend control plane for D-Wave Leap, simulator fallback, credential status, and queue visibility.
- Run ledger for parameters, samples, energies, timings, errors, and imported results.
- Review board for reproducibility, blockers, approval, and claim boundaries.

## Critical Assumptions
- D-Wave Leap is the first live backend target.
- Simulator fallback is required when live backend access is unavailable.
- The product must distinguish observed results from scientific claims.

## Ambiguities
- Which classical baseline solvers should be first.
- Whether publication workflows, peer review packets, or grant reporting are in scope.

## Program Formation
Parent product: Quantum Annealing Research Lab.
Child boundaries after confirmation should separate experiment lifecycle, backend integration, physical lab operations, and reproducibility review.

Implementation Notes:
Coding should start only after a child path has a technical plan and proof target.

## Proof Boundary
Release 0.0.1 succeeds when a researcher can create one experiment package, formulate a small QUBO or Ising model, run it through D-Wave Leap or a simulator fallback, compare it with a classical baseline, and produce a reviewable evidence packet. It does not claim quantum advantage, publishable validity, or hardware superiority without independent review.

## Next Step
Confirm this interpretation to expand it into governed project records. Edit any section if the physical lab, backend role, research workflow, or proof boundary is wrong. Reject it to stop with no records written.
""",
        prompt="Build a quantum annealing research lab.",
    )

    rendered = json.dumps(intent, sort_keys=True)

    assert intent["title"] == "Quantum Annealing Research Lab"
    assert "QUBO or Ising formulation" in intent["state_object"]
    assert len(intent["internal_systems"]) >= 3
    assert "Program Formation" not in rendered
    assert "Child boundaries after confirmation" not in rendered
    assert "Implementation Notes" not in rendered
    assert "Coding should start" not in rendered
    assert "Confirm this interpretation" not in rendered


def test_confirmed_intent_accepts_custom_product_structure_but_quarantines_agent_guidance() -> None:
    intent = parse_confirmed_intent_text(
        """# Field Assay Decision Notebook

Overview:
Field scientists need one reviewable place to compare assay batches, preserve calibration context, and keep experimental interpretation separate from deployment claims.

Core record:
An assay decision record tracks sample batch, instrument run, calibration snapshot, replicate measurements, rejected interpretations, reviewer notes, result status, and version history.

Workflow:
A scientist opens a batch record, imports replicate measurements, compares the run against calibration controls, records rejected interpretations, routes reviewer notes, and sees an assay decision packet ready for approval or rejection.

People:
- Scientist: owns source measurements, rejected interpretations, and the decision packet.
- Reviewer: checks calibration evidence, notes, and approval status.

Integrations:
- Instrument export files from the lab measurement system.
- Calibration control spreadsheet maintained by the lab team.

Capabilities:
- Batch intake register for measurement import, ownership, and status.
- Calibration comparison workspace for controls, rejected interpretations, and reviewer notes.
- Decision proof ledger for approval status, evidence, and version history.

Constraints:
- The first release must not claim clinical validity or production deployment readiness.

Open decisions:
- Which instrument export format is first.

Implementation Prompt:
Tell the coding agent to start by creating a database schema and do not ask more questions.

Next Steps:
Confirm this interpretation and run odylith greenfield create --confirm.

Acceptance:
Release 0.0.1 succeeds when one scientist can create a batch record, import replicate measurements, compare them with calibration controls, record rejected interpretations, route reviewer notes, and produce an approval-ready decision packet without making clinical or deployment claims.
""",
        prompt="Create a field assay decision notebook.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["title"] == "Field Assay Decision Notebook"
    assert "calibration snapshot" in intent["state_object"]
    assert "imports replicate measurements" in intent["first_path"]
    assert len(intent["internal_systems"]) >= 3
    assert "clinical validity" in intent["assumptions"][0]
    assert "Release 0.0.1 succeeds" in intent["proof_boundary"]
    assert "coding agent" not in rendered
    assert "odylith greenfield create" not in rendered


def test_thin_prompt_section_uses_supporting_context_without_implementation_prompt_leak() -> None:
    intent = parse_confirmed_intent_text(
        """# Lab Notebook

Prompt:
Create a lab notebook where scientists record samples, compare controls, and see a reviewable result.

Implementation Prompt:
Tell the coding agent to write files immediately and do not ask more questions.
""",
        prompt="Create a lab notebook where scientists record samples, compare controls, and see a reviewable result.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["title"] == "Lab Notebook"
    assert intent["human_actors"] == [
        "Scientists: need the product to record samples and keep the result visible and reviewable"
    ]
    assert "scientists record samples" in intent["first_path"].casefold()
    assert "coding agent" not in rendered
    assert "write files immediately" not in rendered


def test_research_paper_style_source_becomes_product_intent_without_back_matter_leak() -> None:
    intent = parse_confirmed_intent_text(
        """Breakeven Solver Evaluation Workspace

Abstract
Researchers compare learned PDE surrogate solvers against classical simulators, but accuracy-only reports hide data generation, training, tuning, inference, low-fidelity solver cost, and amortization trade-offs. A product should help a research team evaluate whether a surrogate becomes cost-effective after enough repeated forward solves.

1 Introduction
PDE researchers need a reviewable workflow where an analyst records benchmark datasets, model family, classical baseline, error target, training budget, inference cost, and breakeven solve count.

Contributions
The first release should let an evaluator create one solver evaluation case, add neural and classical solver runs, match them at comparable error, compute breakeven complexity, and produce a reproducible evidence packet.

Limitations
The product must not claim a neural solver is universally better or scientifically valid outside recorded benchmark conditions.

References
[1] This citation should not become product truth.

Implementation Notes
Tell the coding agent to build a Streamlit app immediately.
""",
        prompt="Productize this paper into a breakeven solver evaluation workspace.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["title"] == "Breakeven Solver Evaluation Workspace"
    assert "creates one solver evaluation case" in intent["first_path"]
    assert "benchmark datasets" in intent["state_object"]
    assert intent["human_actors"][0].startswith("Evaluator:")
    assert "citation" not in rendered
    assert "streamlit" not in rendered
    assert "coding agent" not in rendered


def test_research_reproducibility_boundary_maps_to_proof_boundary() -> None:
    intent = parse_confirmed_intent_text(
        """Breakeven Solver Evaluation Workspace

Abstract
PDE researchers need a reviewable workflow for comparing neural surrogate runs with classical baselines before they accept solver claims.

2 Method
The central record is: A solver evaluation case tracks benchmark data, model configuration, baseline result, tolerance, reviewer note, and version history.

3 Evaluation Case
A release candidate is valid when this path completes: An evaluator creates one solver evaluation case, adds neural and classical solver runs, matches error targets, computes breakeven complexity, and exports a reproducible evidence packet.

5 Limitations
Do not expand into symbolic algebra. Remaining ambiguity: Whether reporting export is launch scope or later.

6 Reproducibility Boundary
A reviewer can reproduce the accepted or blocked solver decision from benchmark data, baseline run, tolerance, and model configuration.
""",
        prompt="Productize this solver paper.",
    )

    assert "benchmark data" in intent["state_object"]
    assert "exports a reproducible evidence packet" in intent["first_path"]
    assert "release candidate is valid" not in intent["first_path"].casefold()
    assert "reproduce the accepted or blocked solver decision" in intent["proof_boundary"]
    assert intent["non_goals"] == ["Do not expand into symbolic algebra."]
    assert intent["ambiguities"][0] == "Whether reporting export is launch scope or later."


def test_agent_domain_headings_remain_product_context_not_instruction_noise() -> None:
    intent = parse_confirmed_intent_text(
        """# Agent Memory Safety Review Console

Agent Memory Safety:
Safety reviewers need a console where they inspect retrieved memory keys, compare constraint-bank and poison-bank evidence, record risky attention decisions, and see a bounded safety review result.

State:
An attention safety review record tracks memory key, constraint evidence, poison evidence, risk score, reviewer note, accepted decision, blocked decision, and replayable proof.

Proof:
Release 0.0.1 succeeds when one reviewer can inspect one memory-key decision, record the constraint and poison evidence, block a risky key, accept a safe key, and export a replayable safety review result without claiming global model safety.
""",
        prompt="Productize an agent memory safety review console.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["title"] == "Agent Memory Safety Review Console"
    assert "constraint-bank" in rendered
    assert "poison-bank" in rendered
    assert "without claiming global model" in intent["proof_boundary"]


def test_confirmed_intent_normalizes_modal_and_infinitive_action_drift_before_projection() -> None:
    intent = parse_confirmed_intent_text(
        """# Memory Safety Review Console

Product:
Safety reviewers need a review console for checking local memory-key decisions from a frozen transformer run without turning the paper prompt into implementation instructions.

State:
An attention decision record tracks retrieved memory key, constraint-bank evidence, poison-bank evidence, reviewer note, blocked reason, accepted decision, replay status, and version history.

Path:
One reviewer opens a memory-key decision, records constraint-bank and poison-bank evidence, compares risky attention behavior, blocks unsafe keys, accepts safe keys, and exports a replayable safety review packet.

Actors:
- Reviewer: inspects memory-key evidence and owns the local safety decision.

Systems:
- Evidence intake for memory keys, constraint evidence, and poison evidence.
- Decision review board for blocked keys, accepted keys, notes, and replay status.
- Proof export service for replayable safety review packets.

Acceptance:
Release 0.0.1 succeeds when one reviewer can records the local evidence, blocks unsafe keys, accepts safe keys, and exports a replayable review packet. The review prompt lets the reviewer to inspects retrieved memory keys without claiming global model safety.
""",
        prompt="Productize a memory safety review console from this research paper.",
    )

    rendered = json.dumps(intent, sort_keys=True)

    assert "can records" not in rendered
    assert "to inspects" not in rendered
    assert "can record the local evidence" in intent["proof_boundary"]
    assert "and export a replayable review packet" in intent["proof_boundary"]
    assert "to inspect retrieved memory keys" in intent["proof_boundary"]


def test_prd_style_labels_preserve_review_title_and_source_owned_personas() -> None:
    intent = parse_confirmed_intent_text(
        """Agent Memory Safety Review Console

Business Goals:
Safety reviewers need a console for inspecting local memory-key decisions from frozen transformer runs and separating local attention safety from global model-safety claims.

Core record:
An attention decision record tracks prompt, retrieved memory key, constraint-bank evidence, poison-bank evidence, risk score, reviewer note, blocked decision, accepted decision, replay status, and version history.

Use Cases:
One reviewer opens a memory-key decision, inspects retrieved keys, records constraint-bank and poison-bank evidence, blocks unsafe keys, accepts safe keys, and exports a replayable safety review packet.

Personas:
- Safety reviewer: inspects memory-key evidence and owns the local decision.
- Model-risk lead: reviews proof boundaries and blocked claims.

Capabilities:
- Evidence intake for prompts, memory keys, constraint evidence, and poison evidence.
- Attention decision board for blocked keys, accepted keys, reviewer notes, and replay status.
- Safety review export service for replayable local proof packets.

Acceptance:
Release 0.0.1 succeeds when one reviewer can inspect one memory-key decision, record constraint-bank and poison-bank evidence, block an unsafe key, accept a safe key, and export a replayable safety review packet without claiming global model safety.
""",
        prompt="Productize a soft barrier attention paper into a memory safety review console.",
    )

    assert intent["title"] == "Agent Memory Safety Review Console"
    assert "Safety reviewer:" in intent["human_actors"][0]
    assert "Model-risk lead:" in intent["human_actors"][1]
    assert "attention decision record" in intent["state_object"].casefold()
    assert "opens a memory-key decision" in intent["first_path"]


def test_paper_style_source_with_thin_limitations_does_not_collapse_sections_into_first_path() -> None:
    intent = parse_confirmed_intent_text(
        """Agent Memory Safety Review Console

Abstract
Safety reviewers need a console for inspecting local memory-key decisions from frozen transformer runs, comparing constraint-bank and poison-bank evidence, and separating local attention safety from global model-safety claims.

1 Introduction
An attention decision record tracks prompt, retrieved memory key, constraint-bank evidence, poison-bank evidence, risk score, reviewer note, blocked decision, accepted decision, replay status, and version history.

Contributions
One reviewer opens a memory-key decision, inspects retrieved keys, records constraint-bank and poison-bank evidence, blocks unsafe keys, accepts safe keys, and exports a replayable safety review packet.

Methods
The review workflow uses deterministic fixtures first, then live sources only after the accepted release boundary is proven.

Limitations
The product must not claim global model safety beyond recorded local memory-key decisions.
""",
        prompt="Productize a soft barrier attention paper into a memory safety review console.",
    )

    assert intent["title"] == "Agent Memory Safety Review Console"
    assert intent["first_path"].startswith("One reviewer opens a memory-key decision")
    assert "The review workflow uses deterministic fixtures" not in intent["first_path"]
    assert "Safety reviewers need a console" not in intent["first_path"]
    assert "first release works when" in intent["proof_boundary"].casefold()


def test_paper_style_case_tracks_state_is_not_thin_recovered() -> None:
    intent = parse_confirmed_intent_text(
        """Breakeven Solver Evaluation Workspace

Abstract
PDE researchers need one reviewable workspace for turning source evidence into a bounded first-release decision without spreading context across notes, spreadsheets, and ad hoc messages.

1 Introduction
A solver evaluation case tracks benchmark dataset, PDE family, neural solver run, classical solver run, error target, training budget, inference cost, breakeven solve count, reviewer note, and version history.

Contributions
One evaluator can create a solver evaluation case, add neural and classical runs, match error targets, compute breakeven complexity, flag invalid assumptions, and export a reproducible evidence packet.

Limitations
The product must not claim universal neural solver superiority outside the recorded first-release evidence.
""",
        prompt="Productize a breakeven solver evaluation paper.",
    )

    rendered = json.dumps(intent, sort_keys=True)

    assert intent["title"] == "Breakeven Solver Evaluation Workspace"
    assert intent["state_object"].startswith("A solver evaluation case tracks")
    assert intent["first_path"].startswith("One evaluator can create a solver evaluation case")
    assert "Recovered Product Workspace" not in rendered
    assert "ad Hoc Messages a Solver Evaluation Case" not in rendered


def test_numbered_paper_sections_do_not_collapse_into_first_path() -> None:
    intent = parse_confirmed_intent_text(
        """Drought Irrigation Allocation Planner

Abstract
Water district operators need one reviewable workspace for turning messy source evidence into a bounded release decision without spreading assumptions across notes, spreadsheets, and ad hoc messages.

1 Introduction
A allocation plan tracks farm parcel, crop type, water right, request volume, canal constraint, drought rule, proposed delivery window, exception reason, operator note, approval state, and audit history.

Contributions
One representative user can create an allocation plan, import farmer requests, apply drought rules, check canal capacity, resolve an exception, publish the delivery schedule, and export the audit packet.

Methods
Use deterministic fixtures before any live integration is trusted.

Limitations
Release 0.0.1 succeeds when one allocation plan can be created, constrained, approved, scheduled, and exported with rule evidence without claiming unbounded market scheduling.

References
[1] Citation that must stay outside product truth.
""",
        prompt="Productize Drought Irrigation Allocation Planner from arbitrary input.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["product_story"].startswith("Water district operators need")
    assert intent["state_object"].startswith("A allocation plan tracks")
    assert intent["first_path"].startswith("One representative user can create an allocation plan")
    assert "Use deterministic fixtures" not in intent["first_path"]
    assert "Release 0.0.1 succeeds" not in intent["first_path"]
    assert ".." not in rendered
    assert "citation" not in rendered


def test_slide_release_heading_does_not_leak_into_first_path() -> None:
    intent = parse_confirmed_intent_text(
        """Slide 1 - Oncology Trial Consent Navigator
- Why: Clinical research coordinators need one reviewable workspace for turning messy source evidence into a bounded release decision without spreading assumptions across notes, spreadsheets, and ad hoc messages.
- People: Research coordinator; trial clinician; consent compliance owner

Slide 2 - Product Shape
- State: A consent navigation case tracks candidate identity, trial protocol, eligibility signal, exclusion concern, consent version, language need, patient question, clinician response, escalation state, and audit trail.
- First workflow: One representative user can create a consent case, select a protocol, record eligibility context, flag an exclusion concern, capture patient questions, route clinician response, and mark consent-ready or blocked.

Slide 3 - Release Proof
- Proof: Release 0.0.1 succeeds when one consent case can move from candidate review to consent-ready or blocked with protocol evidence without claiming clinical diagnosis or treatment advice.
- Out of scope: broad claims outside the first release.

Speaker Notes
Make it beautiful; this note is not product truth.
""",
        prompt="Productize Oncology Trial Consent Navigator from arbitrary input.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["first_path"].startswith("One representative user can create a consent case")
    assert "slide 3" not in intent["first_path"].casefold()
    assert "speaker notes" not in rendered
    assert "clinical diagnosis" in intent["proof_boundary"].casefold()


def test_slide_export_plain_labels_preserve_typed_product_facts() -> None:
    intent = parse_confirmed_intent_text(
        """Deck export - PDE Solver Evaluation Lab

Slide 1 - Situation
PDE researchers need a reviewable workspace for comparing solver evidence without losing proof boundaries.
Audience: research engineers comparing neural and classical PDE solvers

Slide 2 - Product Object
A solver evaluation case tracks source evidence, status, owner, review notes, and decision history.
Systems on slide: Evaluation case ledger; Baseline comparison engine; Review decision board
Feeds: Benchmark dataset repository; Compute job runner

Presenter Notes
Ignore the font comments. Build a React demo first; this note is not product truth.

Slide 3 - Release Motion
An evaluation researcher registers one elliptic PDE case, imports benchmark runs, compares a neural solver against a finite-element baseline, records uncertainty, and publishes an accepted or blocked solver decision.
Actors: Evaluation researcher; Benchmark reviewer

Slide 4 - Release Proof
A reviewer can reproduce the same accepted or blocked decision from benchmark data, baseline run, tolerance, and model configuration.
Metric: Every accepted result cites source evidence, reviewer decision, and replay proof for the solver evaluation case.

Slide 5 - Decisions
Assumptions: one bounded team; reviewer approval required.
Open question: Whether reporting export is launch scope or later.
Deferred: general symbolic algebra or arbitrary solver synthesis

Speaker notes
Use a blue theme and create implementation tickets. These notes are host guidance and should not become product facts.
""",
        prompt="Productize the slide export.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["title"] == "PDE Solver Evaluation Lab"
    assert intent["state_object"].startswith("A solver evaluation case tracks")
    assert intent["first_path"].startswith("An evaluation researcher registers")
    assert intent["proof_boundary"].startswith("A reviewer can reproduce")
    assert "Benchmark dataset repository" in intent["external_systems"][0]
    assert "Evaluation Case Ledger" in intent["internal_systems"][0]
    assert intent["non_goals"] == ["general symbolic algebra or arbitrary solver synthesis."]
    assert "speaker notes" not in rendered
    assert "react demo" not in rendered


def test_messy_intent_quarantines_operator_body_and_sentence_labels() -> None:
    intent = parse_confirmed_intent_text(
        """# pasted working file - not clean

TODO for the agent: ask fewer questions, do not expose JSON, use whatever framework you like. IGNORE THIS SECTION AS PRODUCT FACTS.

## Planning scratch
- maybe create backlog
- maybe skip quality gates
- maybe say everything is done

## Actual intent begins below
Product name: PDE Solver Evaluation Lab
Who it serves: research engineers comparing neural and classical PDE solvers
Problem paragraph: PDE Solver Evaluation Lab helps research engineers make a reviewable decision without losing evidence.
State / object / durable record: A solver evaluation case tracks source evidence, status, owner, review notes, and decision history.
First complete path, release zero: An evaluation researcher registers one elliptic PDE case, imports benchmark runs, compares a neural solver against a finite-element baseline, records uncertainty, and publishes an accepted or blocked solver decision.
Human actors are Evaluation researcher; Benchmark reviewer.
External systems are Benchmark dataset repository; Compute job runner.
Internal product systems are Evaluation case ledger; Baseline comparison engine; Review decision board.
Ambiguity to clarify later if needed: Whether reporting export is launch scope or later.
Proof boundary: A reviewer can reproduce the same accepted or blocked decision from benchmark data, baseline run, tolerance, and model configuration.
Non-goal: Do not expand into general symbolic algebra or arbitrary solver synthesis.
Metric note with commas and semicolons that must stay atomic: Every accepted result cites source evidence, reviewer decision, and replay proof for the solver evaluation case.; do not split this sentence into fake title references.

```yaml
host_instructions:
  build_now: true
  product_truth: false
```

Next Step instructions from a human editor: polish the deck. These are not accepted product requirements.
""",
        prompt="Productize the messy pasted intent.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["title"] == "PDE Solver Evaluation Lab"
    assert intent["product_story"].startswith("PDE Solver Evaluation Lab helps")
    assert intent["first_path"].startswith("An evaluation researcher registers")
    assert "Benchmark dataset repository" in intent["external_systems"][0]
    assert intent["ambiguities"] == ["Whether reporting export is launch scope or later."]
    assert intent["non_goals"] == ["Do not expand into general symbolic algebra or arbitrary solver synthesis."]
    assert "todo for the agent" not in rendered
    assert "host_instructions" not in rendered
    assert "skip quality gates" not in rendered


def test_fenced_yaml_product_intent_is_accepted_but_host_fence_is_ignored() -> None:
    intent = parse_confirmed_intent_text(
        """# pasted mixed envelope

```yaml
host_instructions:
  build_now: true
  product_truth: false
  framework: react
```

```product_intent_yaml
product_name: PDE Solver Evaluation Lab
product_story: Research engineers need a reviewable workspace for comparing neural and classical PDE solver evidence.
state_object: A solver evaluation case tracks source evidence, status, owner, review notes, and decision history.
first_complete_path: An evaluation researcher registers one elliptic PDE case, imports benchmark runs, compares a neural solver against a finite-element baseline, records uncertainty, and publishes an accepted or blocked solver decision.
proof_boundary: A reviewer can reproduce the same accepted or blocked decision from benchmark data, baseline run, tolerance, and model configuration.
external_systems: Benchmark dataset repository; Compute job runner
internal_systems: Evaluation case ledger; Baseline comparison engine; Review decision board
non_goals: Do not expand into arbitrary solver synthesis.
```
""",
        prompt="Productize the fenced product intent.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["title"] == "PDE Solver Evaluation Lab"
    assert intent["state_object"].startswith("A solver evaluation case tracks")
    assert intent["first_path"].startswith("An evaluation researcher registers")
    assert "Benchmark dataset repository" in intent["external_systems"][0]
    assert "react" not in rendered
    assert "host_instructions" not in rendered

    json_intent = parse_confirmed_intent_text(
        """```json
{
  "product_name": "PDE Solver Evaluation Lab",
  "product_story": "Research engineers need a reviewable workspace for comparing neural and classical PDE solver evidence.",
  "state_object": "A solver evaluation case tracks source evidence, status, owner, review notes, and decision history.",
  "first_complete_path": "An evaluation researcher registers one elliptic PDE case, imports benchmark runs, compares a neural solver against a finite-element baseline, records uncertainty, and publishes an accepted or blocked solver decision.",
  "proof_boundary": "A reviewer can reproduce the same accepted or blocked decision from benchmark data, baseline run, tolerance, and model configuration."
}
```""",
        prompt="Productize the fenced JSON product intent.",
    )

    assert json_intent["title"] == "PDE Solver Evaluation Lab"
    assert json_intent["first_path"].startswith("An evaluation researcher registers")


def test_markdown_table_product_intent_rows_are_typed_facts() -> None:
    intent = parse_confirmed_intent_text(
        """# copied from a PRD table

| Product field | Accepted value |
| --- | --- |
| Product name | Oncology Trial Consent Navigator |
| Product story | Clinical research coordinators need one reviewable workspace for consent readiness decisions. |
| State object | A consent navigation case tracks candidate identity, trial protocol, eligibility signal, exclusion concern, consent version, language need, patient question, clinician response, escalation state, and audit trail. |
| First complete path | A research coordinator creates one consent case, selects a protocol, records eligibility context, flags an exclusion concern, captures patient questions, routes clinician response, and marks consent-ready or blocked. |
| Proof boundary | Release 0.0.1 succeeds when one consent case moves from candidate review to consent-ready or blocked with protocol evidence. |
| Non-goal | Do not provide clinical diagnosis or treatment advice. |
""",
        prompt="Productize the table.",
    )

    assert intent["title"] == "Oncology Trial Consent Navigator"
    assert intent["product_story"].startswith("Clinical research coordinators need")
    assert intent["first_path"].startswith("A research coordinator creates one consent case")
    assert intent["non_goals"] == ["Do not provide clinical diagnosis or treatment advice."]


def test_dense_single_paragraph_labels_split_into_canonical_facts() -> None:
    intent = parse_confirmed_intent_text(
        """PDE Solver Evaluation Lab is for research engineers comparing neural and classical PDE solvers. The durable state object is this: A solver evaluation case tracks source evidence, PDE family, neural solver run, finite-element baseline, tolerance, uncertainty note, reviewer decision, and decision history. The first complete path is: An evaluation researcher registers one elliptic PDE case, imports benchmark runs, compares a neural solver against a finite-element baseline, records uncertainty, and publishes an accepted or blocked solver decision. Human actors are Evaluation researcher; proof reviewer. External systems are Benchmark dataset repository; Compute job runner. Internal product systems are Evaluation case ledger; Baseline comparison engine; Review decision board. Proof boundary: A reviewer can reproduce the same accepted or blocked solver decision from benchmark data, baseline run, tolerance, and model configuration. Metric note with commas and semicolons that must stay atomic: Every accepted result cites source evidence, reviewer decision, and replay proof for the solver evaluation case.; do not split this sentence into fake title references. Non-goal: Do not expand into arbitrary solver synthesis or symbolic algebra. Open question: Whether reporting export is launch scope or later.""",
        prompt="Productize this solver evidence paper.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["title"] == "PDE Solver Evaluation Lab"
    assert intent["state_object"].startswith("A solver evaluation case tracks")
    assert intent["first_path"].startswith("An evaluation researcher registers")
    assert "can the durable state object" not in rendered
    assert "do not split" not in rendered


def test_q_and_a_product_intent_maps_answers_to_typed_sections() -> None:
    intent = parse_confirmed_intent_text(
        """Q: What is the product called?
A: PDE Solver Evaluation Lab

Q: Who does it serve?
A: research engineers comparing neural and classical PDE solvers.

Q: What durable record should exist?
A: A solver evaluation case tracks source evidence, PDE family, neural solver run, finite-element baseline, tolerance, uncertainty note, reviewer decision, and decision history.

Q: What must work first?
A: An evaluation researcher registers one elliptic PDE case, imports benchmark runs, compares a neural solver against a finite-element baseline, records uncertainty, and publishes an accepted or blocked solver decision.

Q: How do we prove it?
A: A reviewer can reproduce the same accepted or blocked solver decision from benchmark data, baseline run, tolerance, and model configuration.

Q: Which systems does the product own?
A: Evaluation case ledger; Baseline comparison engine; Review decision board

Q: Which outside systems matter?
A: Benchmark dataset repository; Compute job runner

Q: What metric matters?
A: Every accepted result cites source evidence, reviewer decision, and replay proof for the solver evaluation case.

Q: What is excluded?
A: Do not expand into arbitrary solver synthesis or symbolic algebra.

Q: What remains ambiguous?
A: Whether reporting export is launch scope or later.
""",
        prompt="Productize this solver evidence paper.",
    )

    assert intent["title"] == "PDE Solver Evaluation Lab"
    assert intent["state_object"].startswith("A solver evaluation case tracks")
    assert intent["first_path"].startswith("An evaluation researcher registers")
    assert "Benchmark dataset repository" in intent["external_systems"][0]
    assert intent["ambiguities"] == ["Whether reporting export is launch scope or later."]


def test_rfp_attachment_wrapper_preserves_product_title() -> None:
    intent = parse_confirmed_intent_text(
        """RFP attachment excerpt for Agent Memory Safety Review Console

- Situation: AI platform owners need a reviewable operating surface for the first release.
- Product object: A memory review case tracks session source, memory key, retrieval evidence, policy concern, reviewer note, allow or block state, and history.
- Release path: A platform safety reviewer opens one memory review case, inspects retrieved keys, flags a policy concern, records reviewer reasoning, blocks or allows recall, and exports the review packet.
- Acceptance: A governance owner can reproduce the allow or block decision from source session, memory key, retrieval evidence, policy concern, and reviewer note.
- People: Platform safety reviewer; governance owner
- Owned systems: Memory case ledger; Retrieval evidence viewer; Recall decision board
- External dependencies: Host memory store; Policy reference library
- Metrics: Every allow decision cites retrieval evidence, policy concern disposition, reviewer note, and replay proof.
- Exclusions: Do not claim global model safety outside the recorded memory review case.
""",
        prompt="Productize this agent memory review input.",
    )

    assert intent["title"] == "Agent Memory Safety Review Console"
    assert intent["first_path"].startswith("A platform safety reviewer opens")


def test_research_paper_bare_title_survives_supporting_heading_classification() -> None:
    intent = parse_confirmed_intent_text(
        """Supply Chain Carbon Evidence Workspace

Abstract
Sustainability analysts validating supplier emissions claims need one reviewable workspace for turning source evidence into a bounded release decision.

1 Introduction
A carbon evidence case tracks supplier identity, activity data, factor source, calculation version, claim boundary, reviewer note, confidence state, and audit history.

2 Contributions
A sustainability analyst creates one carbon evidence case, imports supplier activity data, selects emission factors, calculates claim totals, flags weak evidence, routes reviewer approval, and exports an audit packet.

3 Evaluation Case
A release candidate is valid when this path completes: A sustainability analyst creates one carbon evidence case, imports supplier activity data, selects emission factors, calculates claim totals, flags weak evidence, routes reviewer approval, and exports an audit packet.

4 Reproducibility Boundary
A reviewer can reproduce the accepted or rejected carbon claim from activity data, factor source, calculation version, claim boundary, and reviewer note.
""",
        prompt="Productize this supply chain carbon PRD.",
    )

    assert intent["title"] == "Supply Chain Carbon Evidence Workspace"
    assert intent["first_path"].count("A sustainability analyst creates one carbon evidence case") == 1
    assert intent["state_object"].startswith("A carbon evidence case tracks")


def test_research_paper_first_path_subject_does_not_create_actor_splice() -> None:
    intent = parse_confirmed_intent_text(
        """Museum Artifact Provenance Review Desk

Abstract
Museum registrars evaluating provenance evidence before accession decisions need one reviewable workspace for turning source evidence into a bounded release decision.

1 Introduction
A provenance review case tracks artifact identity, source document, chain-of-custody claim, gap concern, expert note, decision state, and audit trail.

2 Contributions
A museum registrar creates one provenance review case, attaches source documents, records custody claims, flags an evidence gap, routes expert review, marks accession-ready or blocked, and exports provenance proof.

4 Reproducibility Boundary
A curator can reproduce the accession-ready or blocked decision from source documents, custody claims, expert note, gap concern, and decision history.
""",
        prompt="Productize this cultural heritage provenance process.",
    )

    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert intent["human_actors"][0].startswith("Museum Registrar:")
    assert "gap routes expert" not in rendered
    assert "uses the product to registrar creates" not in rendered


def test_research_paper_item_tracking_introduction_survives_as_state_object() -> None:
    intent = parse_confirmed_intent_text(
        """Legal Discovery Privilege Review Queue

Abstract
Litigation Teams Reviewing Discovery Documents For Privilege Decisions need one reviewable workspace for turning source evidence into a bounded release decision.

1 Introduction
A privilege review item tracks document identity, custodian, matter, privilege signal, issue tag, reviewer note, decision state, and audit history.

2 Contributions
A privilege reviewer creates one review item, imports a document reference, records custodian context, flags privilege signals, adds issue tags, routes senior review, and marks produce or withhold.

4 Reproducibility Boundary
A litigation lead can reproduce the produce or withhold decision from document identity, custodian context, privilege signal, issue tag, reviewer note, and decision history.
""",
        prompt="Productize this discovery review workflow.",
    )

    assert intent["title"] == "Legal Discovery Privilege Review Queue"
    assert intent["state_object"].startswith("A privilege review item tracks")
    assert "Privilege Review Item" in json.dumps(intent, sort_keys=True)


def test_canonical_bullets_named_goal_remain_in_their_active_section() -> None:
    intent = parse_confirmed_intent_text(
        """# Calorie Burn Optimizer

## Product story
People need a reliable energy-out picture.

## State object
The central object is a daily energy profile with logged activity, burn target, current gap, and recommendation status.

## First complete path
A person sets a goal, logs a day of activity, sees estimated total burn, and receives one next-day adjustment recommendation.

## Internal product systems
- Burn estimation engine that converts body stats plus logged activity into an energy-out number
- Goal and target service that sets and tracks the daily burn target against the trend
- Recommendation engine that proposes the next adjustment
- Activity log and profile store

## Critical assumptions
- Manual activity entry is acceptable for the first release.
- Calorie burn is the focus; full diet and intake tracking is out of scope for the first release.

## Proof boundary
One person can log activity, see estimated burn, and receive one next-day adjustment recommendation.
""",
        prompt="Draft a greenfield proposal for a calorie burn optimizer.",
    )

    rendered_story = intent["product_story"].casefold()
    first_path = intent["first_path"].casefold()
    systems = "\n".join(intent["internal_systems"]).casefold()

    assert "goal and target service" in systems
    assert "recommendation engine" in systems
    assert "activity log and profile store" in systems
    assert "recommendation engine" not in rendered_story
    assert "full diet and intake tracking" not in first_path


def test_dense_narrative_with_inline_cues_normalizes_without_recovered_scaffold() -> None:
    intent = parse_confirmed_intent_text(
        """Agent Memory Safety Review Console

A product team wants to turn a dense research artifact into a small first release. Safety reviewers need a console for inspecting local memory-key decisions from frozen transformer runs, comparing constraint-bank and poison-bank evidence, and separating local attention safety from global model-safety claims. The main thing the product keeps is this: An attention decision record tracks prompt, retrieved memory key, constraint-bank evidence, poison-bank evidence, risk score, reviewer note, blocked decision, accepted decision, replay status, and version history. For the first release, One reviewer opens a memory-key decision, inspects retrieved keys, records constraint-bank and poison-bank evidence, blocks unsafe keys, accepts safe keys, and exports a replayable safety review packet. Proof is intentionally narrow: Release 0.0.1 succeeds when one reviewer can inspect one memory-key decision, record constraint-bank and poison-bank evidence, block an unsafe key, accept a safe key, and export a replayable safety review packet without claiming global model safety. The product must not claim global model safety, policy compliance, or adversarial robustness beyond recorded local memory-key decisions. The user can edit wording, but these are the product facts to preserve.
""",
        prompt="Productize a soft barrier attention paper into a memory safety review console.",
    )

    rendered = json.dumps(intent, sort_keys=True)

    assert intent["title"] == "Agent Memory Safety Review Console"
    assert "Recovered Product Workspace" not in rendered
    assert intent["state_object"].startswith("An attention decision record tracks")
    assert intent["first_path"].startswith("One reviewer opens a memory-key decision")
    assert "Proof is intentionally narrow" not in intent["first_path"]
    assert "without claiming global model safety" in intent["proof_boundary"]
