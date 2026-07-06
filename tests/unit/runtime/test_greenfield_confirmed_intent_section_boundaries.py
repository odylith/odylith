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
    assert "benchmark datasets" in intent["first_path"]
    assert intent["human_actors"][0].startswith("Analyst:")
    assert "citation" not in rendered
    assert "streamlit" not in rendered
    assert "coding agent" not in rendered


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
