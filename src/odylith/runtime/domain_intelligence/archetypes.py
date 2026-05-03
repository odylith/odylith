"""Provider-free domain archetypes for Odylith greenfield proposals.

The catalog is intentionally data-first. Adding a future project domain should
mean adding an archetype here, not branching host-specific proposal logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentBlueprint:
    component_id: str
    label: str
    kind: str
    path_suffix: str
    responsibility: str


@dataclass(frozen=True)
class DiagramBlueprint:
    slug_suffix: str
    title_suffix: str
    summary: str
    kind: str = "flowchart"


@dataclass(frozen=True)
class WaveBlueprint:
    label: str
    goal: str
    validation: str


@dataclass(frozen=True)
class Archetype:
    archetype_id: str
    label: str
    keywords: tuple[str, ...]
    components: tuple[ComponentBlueprint, ...]
    diagrams: tuple[DiagramBlueprint, ...]
    waves: tuple[WaveBlueprint, ...]
    validation_focus: tuple[str, ...]
    risks: tuple[str, ...]


_SCIENCE_VALIDATION = (
    "Pin reproducible inputs, random seeds, units, and environment metadata before comparing results.",
    "Define tolerance bands for numerical outputs instead of exact equality where floating point drift is expected.",
    "Keep benchmark datasets and reference outputs versioned so future sessions can distinguish algorithm changes from data drift.",
)


_PRODUCT_WAVES = (
    WaveBlueprint("Discovery", "Confirm users, first workflow, and success metrics.", "Backlog and topology reviewed before writes."),
    WaveBlueprint("Foundation", "Create the minimum source skeleton and component contracts.", "Smoke tests and ownership checks pass."),
    WaveBlueprint("First Slice", "Ship one end-to-end user workflow through the named components.", "Acceptance proof covers the slice."),
    WaveBlueprint("Hardening", "Add failure handling, security, observability, and release proof.", "Regression and browser/runtime proof pass."),
)


_RESEARCH_WAVES = (
    WaveBlueprint("Research Framing", "Record assumptions, reference material, and correctness oracles.", "Claims stay separated from project structure."),
    WaveBlueprint("Model And Data", "Create model, data, and provenance boundaries.", "Units, fixtures, and seeds are pinned."),
    WaveBlueprint("Execution And Validation", "Implement solver, experiment, or proof execution with reviewable outputs.", "Tolerance, invariant, and reference-output checks pass."),
    WaveBlueprint("Reproducibility", "Package notebooks, reports, and publication artifacts.", "Fresh checkout can reproduce the stated result envelope."),
)


_FORMAL_PROOF_WAVES = (
    WaveBlueprint("Formal Framing", "Choose proof assistant, source text, definitions, and theorem scope.", "Statements and definitions are reviewed before proof work starts."),
    WaveBlueprint("Theory Core", "Build reusable definitions, notation, and theorem dependency boundaries.", "The theory core compiles with no admitted hidden assumptions."),
    WaveBlueprint("Proof Coverage", "Formalize lemmas, proof scripts, tactics, and checker harness.", "The proof checker compiles every claimed theorem and flags admitted lemmas."),
    WaveBlueprint("Review And Reproducibility", "Package review notes, examples, and fresh-environment proof checks.", "Fresh checkout reproduces the proof-checker result envelope."),
)


_NOTEBOOK_WAVES = (
    WaveBlueprint("Analysis Framing", "Record research question, datasets, statistical assumptions, and expected outputs.", "Exploratory claims stay separate from accepted analysis outputs."),
    WaveBlueprint("Data And Environment", "Pin datasets, cleaning rules, kernel, dependencies, and execution order.", "A clean environment can load the declared inputs."),
    WaveBlueprint("Reusable Analysis", "Extract reusable analysis code and notebook execution harness.", "Notebooks run top-to-bottom against reference outputs."),
    WaveBlueprint("Report Reproducibility", "Package figures, tables, reports, and review notes.", "Fresh checkout reproduces the published result envelope."),
)


_SIMULATION_WAVES = (
    WaveBlueprint("Model Framing", "Record equations, parameters, units, and scenario assumptions.", "Units and model assumptions are reviewable before solver work starts."),
    WaveBlueprint("Solver Baseline", "Implement the first solver path and scenario runner.", "Analytic or benchmark cases execute with declared tolerance bands."),
    WaveBlueprint("Numerical Validation", "Add convergence, stability, conservation, and reference-output checks.", "Validation fixtures catch solver drift before optimization."),
    WaveBlueprint("Reproducible Reporting", "Package diagnostics, plots, runs, and reproducibility metadata.", "Fresh checkout reproduces the accepted simulation envelope."),
)


_SCIENTIFIC_PIPELINE_WAVES = (
    WaveBlueprint("Data Provenance", "Record raw sources, instruments, metadata, and licensing boundaries.", "Raw inputs and provenance are reviewable before processing starts."),
    WaveBlueprint("Pipeline Baseline", "Create staged processing, quality control, and artifact boundaries.", "Each stage has fixtures, schemas, and quality gates."),
    WaveBlueprint("Analysis Validation", "Connect domain analysis to benchmark datasets and reference outputs.", "Stage outputs match accepted fixtures and anomaly checks."),
    WaveBlueprint("Reproducibility Pack", "Package workflow locks, reports, exports, and rerun instructions.", "Fresh checkout reproduces the accepted pipeline output envelope."),
)


_GEOSPATIAL_WAVES = (
    WaveBlueprint("Spatial Evidence", "Record datasets, CRS, units, extents, temporal coverage, and licenses.", "Spatial inputs and assumptions are reviewable before processing starts."),
    WaveBlueprint("Geoprocessing Baseline", "Create CRS normalization, spatial joins, tiling, and feature derivation.", "Reference regions prove transforms, extents, and joins."),
    WaveBlueprint("Map And Analysis Validation", "Add map-layer, temporal, anomaly, and export checks.", "Reference maps and sample outputs catch spatial drift."),
    WaveBlueprint("Publication Reproducibility", "Package maps, reports, exports, and provenance notes.", "Fresh checkout reproduces accepted maps and reports."),
)


_ML_EXPERIMENT_WAVES = (
    WaveBlueprint("Experiment Framing", "Record task, datasets, splits, labels, metrics, and promotion thresholds.", "Accuracy claims stay blocked until evaluation criteria are accepted."),
    WaveBlueprint("Training Baseline", "Create training configuration, environment, checkpoints, and lineage capture.", "A baseline model trains reproducibly on pinned data."),
    WaveBlueprint("Evaluation Gates", "Add metrics, error slices, drift, latency, cost, and safety checks.", "Promotion gates block weak or unreviewed model candidates."),
    WaveBlueprint("Model Release", "Package registry, inference, monitoring, rollback, and review evidence.", "Approved model artifacts carry lineage and release proof."),
)


_MATH_EDUCATION_WAVES = (
    WaveBlueprint("Curriculum Framing", "Record learner level, prerequisites, concepts, and review ownership.", "Mathematical truth and progression assumptions are reviewed."),
    WaveBlueprint("Exercise Baseline", "Create lessons, worked examples, hints, and answer-check contracts.", "Exercise fixtures cover correct, incorrect, and misconception paths."),
    WaveBlueprint("Learner Experience", "Build the first interactive learning session and feedback loop.", "Rendered UX, accessibility, progress, and recovery proof pass."),
    WaveBlueprint("Classroom Readiness", "Package teacher review, assessment exports, and content governance.", "Human review and learner-state evidence are complete."),
)


ARCHETYPES: tuple[Archetype, ...] = (
    Archetype(
        archetype_id="commerce",
        label="Commerce Application",
        keywords=("ecommerce", "e-commerce", "commerce", "store", "shop", "marketplace", "checkout", "cart"),
        components=(
            ComponentBlueprint("storefront", "Storefront", "application", "apps/web", "Customer-facing catalog, cart, and checkout UI."),
            ComponentBlueprint("catalog", "Product Catalog", "service", "src/catalog", "Product, inventory, price, and merchandising boundary."),
            ComponentBlueprint("cart", "Cart", "service", "src/cart", "Session and saved-cart state boundary."),
            ComponentBlueprint("orders", "Orders", "service", "src/orders", "Order lifecycle, fulfillment handoff, and status history."),
            ComponentBlueprint("payments", "Payments Boundary", "integration", "src/payments", "Payment-provider adapter and payment-state contract."),
            ComponentBlueprint("customers", "Customer Accounts", "service", "src/customers", "Identity, profile, account, and consent boundary."),
        ),
        diagrams=(
            DiagramBlueprint("system-context", "System Context", "Show shoppers, admins, payment providers, catalog, cart, and order boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show discovery, foundation, first-slice, and hardening wave order."),
            DiagramBlueprint("checkout-runtime", "Checkout Runtime Flow", "Show cart-to-payment-to-order transitions and failure boundaries."),
            DiagramBlueprint("commerce-data-flow", "Commerce Data Flow", "Show catalog, cart, customer, payment, and order data movement."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Checkout happy path and payment-failure recovery.",
            "Catalog price/inventory consistency under concurrent cart updates.",
            "Order idempotency across retry and webhook flows.",
        ),
        risks=(
            "Payment, identity, and order state must not be collapsed into one vague application bucket.",
            "Inventory and price snapshots need explicit consistency rules before implementation starts.",
        ),
    ),
    Archetype(
        archetype_id="formal_proof",
        label="Formal Math Or Proof Project",
        keywords=(
            "formal math", "formal proof", "proof library", "theorem", "lemma", "proof assistant",
            "lean", "coq", "isabelle", "agda", "proof", "formalize",
        ),
        components=(
            ComponentBlueprint("theory-core", "Theory Core", "library", "src/theory", "Definitions, axioms, theorem statements, and reusable mathematical structures."),
            ComponentBlueprint("proof-engine", "Proof Engine", "library", "src/proofs", "Proof scripts, tactics, lemmas, and formal derivation boundaries."),
            ComponentBlueprint("exercise-catalog", "Exercise Catalog", "content", "src/exercises", "Problem statements, hints, grading metadata, and topic progression."),
            ComponentBlueprint("checker-harness", "Checker Harness", "test", "tests/proofs", "Proof compilation, theorem coverage, counterexample, and regression checks."),
            ComponentBlueprint("review-notes", "Review Notes", "docs", "docs/review", "Human-readable derivation notes, references, and proof-review artifacts."),
        ),
        diagrams=(
            DiagramBlueprint("proof-topology", "Proof Topology", "Show definitions, theorem statements, proof scripts, checker harness, and review artifacts."),
            DiagramBlueprint("proof-program-waves", "Proof Program Waves", "Show formalization framing, theory core, proof coverage, and review waves."),
            DiagramBlueprint("proof-validation-flow", "Proof Validation Flow", "Show theorem compile checks, dependency coverage, counterexamples, and review notes."),
        ),
        waves=_FORMAL_PROOF_WAVES,
        validation_focus=(
            "Compile every theorem and lemma with the proof checker in a fresh environment before claiming correctness.",
            "Map informal statements to formal definitions, proof obligations, and review notes.",
            "Track unproven assumptions, admitted lemmas, and counterexample search separately from completed proofs.",
            "Use dependency coverage and minimal-example exercises to catch accidental theorem drift.",
        ),
        risks=(
            "Do not translate mathematical claims into completed theorem status until the proof checker verifies them.",
            "Definitions, notation, exercises, and proof scripts need separate ownership so pedagogy does not obscure correctness.",
        ),
    ),
    Archetype(
        archetype_id="computational_notebook",
        label="Computational Notebook Or Analysis Project",
        keywords=(
            "notebook", "jupyter", "analysis notebook", "statistics", "econometrics", "statistical",
            "data analysis", "exploratory analysis", "research notebook", "report", "reproducible notebook",
        ),
        components=(
            ComponentBlueprint("notebook-workflows", "Notebook Workflows", "application", "notebooks", "Exploratory notebooks, report notebooks, and execution order contracts."),
            ComponentBlueprint("analysis-core", "Analysis Core", "library", "src/analysis", "Reusable statistics, econometrics, feature, and transformation code."),
            ComponentBlueprint("dataset-provenance", "Dataset Provenance", "library", "data", "Dataset manifests, source citations, cleaning rules, and version pins."),
            ComponentBlueprint("environment-lock", "Environment Lock", "platform", "env", "Runtime, dependency, container, and kernel reproducibility boundary."),
            ComponentBlueprint("reporting", "Reporting", "docs", "reports", "Rendered tables, figures, narrative outputs, and publication artifacts."),
            ComponentBlueprint("validation-suite", "Validation Suite", "test", "tests/analysis", "Reference outputs, snapshot checks, and statistical sanity tests."),
        ),
        diagrams=(
            DiagramBlueprint("analysis-pipeline", "Analysis Pipeline", "Show dataset intake, cleaning, reusable analysis, notebooks, and report outputs."),
            DiagramBlueprint("notebook-reproducibility", "Notebook Reproducibility Flow", "Show environment lock, ordered notebook execution, reference outputs, and reports."),
            DiagramBlueprint("analysis-program-waves", "Analysis Program Waves", "Show data inventory, reusable core extraction, notebook proof, and publication waves."),
        ),
        waves=_NOTEBOOK_WAVES,
        validation_focus=(
            "Execute notebooks top-to-bottom from a clean environment with pinned inputs.",
            "Separate reusable analysis code from exploratory notebook cells before release claims.",
            "Version datasets, cleaning rules, figures, tables, and random seeds.",
            "Use reference outputs and statistical sanity checks to detect data or environment drift.",
        ),
        risks=(
            "Notebook order, hidden state, and local files can fabricate reproducibility unless execution is clean-room tested.",
            "Exploratory findings must stay labeled as analysis outputs, not source-backed scientific claims.",
        ),
    ),
    Archetype(
        archetype_id="simulation_modeling",
        label="Numerical Simulation Or Modeling Project",
        keywords=(
            "simulation", "simulator", "numerical", "physics", "solver", "ode", "pde",
            "differential equation", "differential-equation", "finite element", "finite difference",
            "modeling", "modelling", "climate model", "fluid", "trajectory",
        ),
        components=(
            ComponentBlueprint("model-spec", "Model Spec", "library", "src/model", "Equations, parameters, units, assumptions, and scenario definitions."),
            ComponentBlueprint("solver-engine", "Solver Engine", "library", "src/solver", "Numerical methods, stepping, convergence, and stability boundaries."),
            ComponentBlueprint("scenario-runner", "Scenario Runner", "application", "src/scenarios", "Scenario orchestration, run metadata, and batch execution."),
            ComponentBlueprint("reference-cases", "Reference Cases", "test", "tests/reference", "Analytic cases, benchmark fixtures, tolerance bands, and regression outputs."),
            ComponentBlueprint("visualization", "Visualization", "application", "src/visualization", "Plots, diagnostics, animations, and result inspection outputs."),
        ),
        diagrams=(
            DiagramBlueprint("simulation-topology", "Simulation Topology", "Show model spec, solver, scenarios, reference cases, and visualization boundaries."),
            DiagramBlueprint("solver-validation-flow", "Solver Validation Flow", "Show inputs, units, stepping, convergence, reference checks, and diagnostics."),
            DiagramBlueprint("simulation-program-waves", "Simulation Program Waves", "Show model framing, solver baseline, benchmark validation, and reporting waves."),
        ),
        waves=_SIMULATION_WAVES,
        validation_focus=_SCIENCE_VALIDATION
        + (
            "Add convergence, conservation-law, unit-consistency, and analytic-reference checks before performance tuning.",
        ),
        risks=(
            "Numerical outputs require explicit tolerance, stability, and unit contracts before correctness is claimed.",
            "Solver, model, scenario, and visualization ownership must stay separate to keep regressions diagnosable.",
        ),
    ),
    Archetype(
        archetype_id="scientific_pipeline",
        label="Scientific Data Pipeline",
        keywords=(
            "computational biology", "bioinformatics", "genomics", "variant analysis", "scientific pipeline",
            "image processing", "data processing", "data product", "analysis pipeline", "pipeline",
        ),
        components=(
            ComponentBlueprint("data-ingestion", "Data Ingestion", "service", "src/ingestion", "Source datasets, instruments, metadata, and raw artifact capture."),
            ComponentBlueprint("processing-pipeline", "Processing Pipeline", "pipeline", "src/pipeline", "Cleaning, alignment, transformation, and staged processing steps."),
            ComponentBlueprint("quality-control", "Quality Control", "test", "tests/quality", "Sample quality, completeness, anomaly, and provenance checks."),
            ComponentBlueprint("analysis-core", "Analysis Core", "library", "src/analysis", "Domain analysis algorithms, metrics, and result derivation."),
            ComponentBlueprint("reproducibility-pack", "Reproducibility Pack", "platform", "reproducibility", "Environment, dataset manifest, workflow lock, and rerun instructions."),
            ComponentBlueprint("results-portal", "Results Portal", "application", "reports", "Reports, maps, figures, exports, and stakeholder review outputs."),
        ),
        diagrams=(
            DiagramBlueprint("scientific-data-flow", "Scientific Data Flow", "Show raw data, processing stages, quality control, analysis, and reports."),
            DiagramBlueprint("provenance-flow", "Provenance Flow", "Show dataset versions, pipeline steps, QC evidence, result artifacts, and review exports."),
            DiagramBlueprint("scientific-program-waves", "Scientific Program Waves", "Show data inventory, pipeline baseline, QC validation, and reproducibility waves."),
        ),
        waves=_SCIENTIFIC_PIPELINE_WAVES,
        validation_focus=(
            "Version raw inputs, metadata, cleaning rules, and derived artifacts.",
            "Run quality-control fixtures for completeness, anomalies, schema drift, and provenance.",
            "Keep benchmark datasets and reference outputs for every major pipeline stage.",
            "Prove reruns from a clean environment before treating outputs as review-ready.",
        ),
        risks=(
            "Pipeline results can look authoritative while hiding weak data provenance or missing quality checks.",
            "Scientific interpretation must stay separate from generated project structure until reviewed evidence exists.",
        ),
    ),
    Archetype(
        archetype_id="geospatial_environmental",
        label="Geospatial Or Environmental Analysis Project",
        keywords=(
            "geospatial", "gis", "climate", "earth science", "environmental science",
            "remote sensing", "satellite data", "spatial", "geography", "weather model",
            "map analysis", "raster", "vector tiles",
        ),
        components=(
            ComponentBlueprint("spatial-data-catalog", "Spatial Data Catalog", "platform", "data/spatial", "Raster, vector, temporal, projection, and source-license manifests."),
            ComponentBlueprint("geoprocessing-pipeline", "Geoprocessing Pipeline", "pipeline", "src/geoprocessing", "CRS normalization, spatial joins, resampling, tiling, and feature derivation."),
            ComponentBlueprint("temporal-analysis", "Temporal Analysis", "library", "src/temporal", "Time-window, seasonality, anomaly, and scenario analysis boundaries."),
            ComponentBlueprint("map-visualization", "Map Visualization", "application", "apps/maps", "Map layers, legends, exploratory views, and publication/export surfaces."),
            ComponentBlueprint("spatial-validation", "Spatial Validation", "test", "tests/spatial", "CRS, unit, extent, sample-fixture, and reference-map checks."),
        ),
        diagrams=(
            DiagramBlueprint("geospatial-data-flow", "Geospatial Data Flow", "Show source datasets, CRS normalization, geoprocessing, analysis, maps, and exports."),
            DiagramBlueprint("spatial-validation-flow", "Spatial Validation Flow", "Show projection checks, extents, temporal coverage, reference maps, and review outputs."),
            DiagramBlueprint("environmental-program-waves", "Environmental Program Waves", "Show data inventory, geoprocessing baseline, analysis validation, and publication waves."),
        ),
        waves=_GEOSPATIAL_WAVES,
        validation_focus=(
            "Version spatial datasets, coordinate reference systems, units, extents, and temporal coverage.",
            "Test CRS transforms, spatial joins, raster/vector conversions, and map-layer rendering against reference fixtures.",
            "Separate environmental interpretation from data processing until provenance and review evidence exist.",
            "Prove reproducible exports from a clean environment before maps or reports become release evidence.",
        ),
        risks=(
            "Projection, unit, and temporal-coverage mistakes can make polished maps scientifically wrong.",
            "Environmental claims must remain review-bound and provenance-backed rather than inferred from prompt wording.",
        ),
    ),
    Archetype(
        archetype_id="ml_experiment_platform",
        label="ML Experiment Platform",
        keywords=(
            "ml experiment", "machine learning experiment", "training", "model registry", "feature store",
            "inference", "evaluation harness", "computer vision", "biology images", "experiment platform",
            "mlops", "model monitoring",
        ),
        components=(
            ComponentBlueprint("dataset-registry", "Dataset Registry", "platform", "src/datasets", "Dataset versions, splits, labels, provenance, and access boundaries."),
            ComponentBlueprint("training-pipeline", "Training Pipeline", "pipeline", "src/training", "Training jobs, configuration, checkpoints, and reproducible execution."),
            ComponentBlueprint("evaluation-harness", "Evaluation Harness", "test", "tests/evaluation", "Metrics, baselines, error slices, fairness/drift checks, and regression gates."),
            ComponentBlueprint("model-registry", "Model Registry", "platform", "src/models", "Model artifacts, lineage, approval, rollback, and release gates."),
            ComponentBlueprint("inference-runtime", "Inference Runtime", "service", "src/inference", "Serving path, latency, batching, monitoring, and safety controls."),
        ),
        diagrams=(
            DiagramBlueprint("ml-lifecycle", "ML Lifecycle Topology", "Show datasets, training, evaluation, registry, inference, and monitoring."),
            DiagramBlueprint("experiment-flow", "Experiment Flow", "Show config, data split, training, metrics, approval, and model promotion."),
            DiagramBlueprint("ml-program-waves", "ML Program Waves", "Show dataset baseline, training harness, evaluation gates, and release-readiness waves."),
        ),
        waves=_ML_EXPERIMENT_WAVES,
        validation_focus=(
            "Pin dataset versions, splits, labels, random seeds, and environment metadata.",
            "Track baseline metrics, error slices, drift checks, and promotion thresholds.",
            "Require reproducible training and evaluation before model registry promotion.",
            "Measure latency, cost, and safety behavior separately from accuracy metrics.",
        ),
        risks=(
            "Model accuracy claims are invalid without dataset lineage, evaluation gates, and reproducibility proof.",
            "Training, evaluation, registry, and inference boundaries must stay distinct to prevent unreviewed promotion.",
        ),
    ),
    Archetype(
        archetype_id="math_education",
        label="Math Education Experience",
        keywords=(
            "math education", "mathematics education", "math app", "topology exercises", "lesson",
            "student", "teacher", "tutor", "exercise", "quiz", "worked example", "learning",
            "undergraduate", "curriculum", "classroom",
        ),
        components=(
            ComponentBlueprint("learning-shell", "Learning Shell", "application", "apps/learning", "Student-facing lessons, navigation, and interaction state."),
            ComponentBlueprint("concept-model", "Concept Model", "library", "src/concepts", "Definitions, learning objectives, prerequisites, and topic progression."),
            ComponentBlueprint("exercise-engine", "Exercise Engine", "library", "src/exercises", "Problem generation, hints, attempts, feedback, and scoring."),
            ComponentBlueprint("assessment", "Assessment", "test", "tests/assessment", "Rubrics, answer checks, misconception fixtures, and mastery evidence."),
            ComponentBlueprint("teacher-review", "Teacher Review", "application", "apps/review", "Instructor views, curriculum review, and progress exports."),
        ),
        diagrams=(
            DiagramBlueprint("learning-topology", "Learning Topology", "Show lessons, concepts, exercises, assessment, and teacher review boundaries."),
            DiagramBlueprint("learning-session-flow", "Learning Session Flow", "Show lesson start, exercise attempt, feedback, mastery update, and review."),
            DiagramBlueprint("education-program-waves", "Education Program Waves", "Show curriculum framing, exercise baseline, feedback quality, and classroom-readiness waves."),
        ),
        waves=_MATH_EDUCATION_WAVES,
        validation_focus=(
            "Check exercise answers, hints, worked examples, and rubrics against reviewed mathematical truth.",
            "Test misconception cases, accessibility, progress recovery, and student feedback loops.",
            "Keep curriculum sequencing and prerequisite claims reviewable by a human subject-matter owner.",
        ),
        risks=(
            "Pedagogical polish must not mask wrong mathematics or unreviewed prerequisite claims.",
            "Student progress and assessment state need explicit recovery and privacy boundaries.",
        ),
    ),
    Archetype(
        archetype_id="science_math",
        label="Science Or Math Project",
        keywords=(
            "science", "scientific", "math", "mathematics", "research codebase",
            "research project", "chemistry", "scientific model", "mathematical model",
        ),
        components=(
            ComponentBlueprint("model-core", "Model Core", "library", "src/model", "Mathematical model, assumptions, equations, and domain objects."),
            ComponentBlueprint("solver-engine", "Solver Engine", "library", "src/solver", "Numerical, symbolic, or proof-search execution boundary."),
            ComponentBlueprint("experiment-runner", "Experiment Runner", "application", "src/experiments", "Reproducible experiment orchestration and run metadata."),
            ComponentBlueprint("data-io", "Data IO", "library", "src/data", "Dataset, fixture, import/export, and provenance boundary."),
            ComponentBlueprint("validation-suite", "Validation Suite", "test", "tests/validation", "Reference checks, tolerances, invariants, and benchmark fixtures."),
            ComponentBlueprint("visualization", "Visualization", "application", "src/visualization", "Plots, reports, notebooks, and explainability outputs."),
        ),
        diagrams=(
            DiagramBlueprint("research-system-context", "Research System Context", "Show inputs, model, solver, experiment runner, validation, and publication outputs."),
            DiagramBlueprint("research-waves", "Research Program Waves", "Show framing, model/data, execution/validation, and reproducibility wave order."),
            DiagramBlueprint("experiment-pipeline", "Experiment Pipeline", "Show data loading, model setup, execution, validation, and result capture."),
            DiagramBlueprint("validation-flow", "Validation Flow", "Show reference data, tolerances, benchmark runs, and review artifacts."),
        ),
        waves=_RESEARCH_WAVES,
        validation_focus=_SCIENCE_VALIDATION
        + (
            "Trace equations or proof obligations to tests, notebooks, or review notes before claiming scientific correctness.",
        ),
        risks=(
            "Scientific claims must not be invented from the prompt; only project structure and validation obligations are proposed.",
            "Numerical tolerances, units, datasets, and reproducibility metadata are first-class governance surfaces.",
        ),
    ),
    Archetype(
        archetype_id="data_platform",
        label="Data Platform",
        keywords=("data platform", "pipeline", "etl", "elt", "ingestion", "warehouse", "analytics", "streaming", "lakehouse"),
        components=(
            ComponentBlueprint("ingestion", "Ingestion", "service", "src/ingestion", "Source connectors, validation, and raw event capture."),
            ComponentBlueprint("transformations", "Transformations", "pipeline", "src/transforms", "Data normalization, enrichment, and quality checks."),
            ComponentBlueprint("storage", "Storage Boundary", "platform", "src/storage", "Warehouse, lake, retention, and schema lifecycle boundary."),
            ComponentBlueprint("serving", "Serving Layer", "service", "src/serving", "APIs, marts, exports, and downstream contracts."),
            ComponentBlueprint("observability", "Data Observability", "platform", "src/observability", "Freshness, volume, quality, and lineage monitoring."),
        ),
        diagrams=(
            DiagramBlueprint("data-flow", "Data Flow", "Show source systems, ingestion, transformation, storage, serving, and monitoring boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show ingestion, quality, serving, and observability delivery order."),
            DiagramBlueprint("lineage-topology", "Lineage Topology", "Show dataset ownership, schema contracts, and downstream consumers."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Schema compatibility and backfill safety.",
            "Freshness, duplicate, null-rate, and volume anomaly checks.",
            "Lineage from source records to served datasets.",
        ),
        risks=(
            "Pipeline ownership must separate ingestion, transformation, storage, and serving contracts.",
            "Backfills and schema changes need explicit forward-fix and rollback posture.",
        ),
    ),
    Archetype(
        archetype_id="ai_agent",
        label="AI Agent System",
        keywords=("ai agent", "agent", "assistant", "copilot", "rag", "retrieval", "llm", "memory", "tool use", "workflow agent"),
        components=(
            ComponentBlueprint("conversation-runtime", "Conversation Runtime", "service", "src/conversation", "Prompt/session orchestration and response lifecycle."),
            ComponentBlueprint("tool-router", "Tool Router", "service", "src/tools", "Tool selection, permissions, retries, and result shaping."),
            ComponentBlueprint("memory-retrieval", "Memory Retrieval", "service", "src/memory", "Hot/cold memory, retrieval, ranking, and provenance."),
            ComponentBlueprint("policy-guard", "Policy Guard", "library", "src/policy", "Safety, scope, and execution policy boundary."),
            ComponentBlueprint("evaluation", "Evaluation", "test", "tests/evaluation", "Benchmarks, regressions, scoring, and drift checks."),
        ),
        diagrams=(
            DiagramBlueprint("agent-runtime", "Agent Runtime Topology", "Show conversation, tools, memory, policy, and evaluation boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show memory, tools, policy, evaluation, and release waves."),
            DiagramBlueprint("retrieval-flow", "Retrieval And Tool Flow", "Show retrieval, tool invocation, policy gates, and response synthesis."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Prompt fixtures for routing, memory recall, tool denial, and recovery behavior.",
            "Regression benchmarks for recall, precision, cost, and latency.",
            "Audit trail for tool use, memory provenance, and policy decisions.",
        ),
        risks=(
            "Memory and tool results must carry provenance so the agent does not overclaim.",
            "Latency and credit burn require benchmark gates, not anecdotal checks.",
        ),
    ),
    Archetype(
        archetype_id="cloud_infra",
        label="Cloud Or Infrastructure Platform",
        keywords=("cloud", "infra", "infrastructure", "kubernetes", "devops", "observability", "security", "platform engineering", "ci/cd", "serverless"),
        components=(
            ComponentBlueprint("control-plane", "Control Plane", "platform", "src/control_plane", "Operator API, desired state, and orchestration boundary."),
            ComponentBlueprint("runtime-plane", "Runtime Plane", "platform", "src/runtime", "Workers, schedulers, execution, and isolation boundary."),
            ComponentBlueprint("delivery-pipeline", "Delivery Pipeline", "platform", "src/delivery", "Build, release, deployment, and rollback contract."),
            ComponentBlueprint("observability", "Observability", "platform", "src/observability", "Metrics, traces, logs, SLOs, and incident evidence."),
            ComponentBlueprint("security-policy", "Security Policy", "library", "src/security", "Identity, authorization, secrets, and compliance controls."),
        ),
        diagrams=(
            DiagramBlueprint("platform-topology", "Platform Topology", "Show control plane, runtime plane, delivery, observability, and security boundaries."),
            DiagramBlueprint("delivery-flow", "Delivery Flow", "Show build, deploy, rollback, and evidence capture order."),
            DiagramBlueprint("incident-flow", "Incident Flow", "Show detection, triage, remediation, and postmortem evidence."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Provisioning, rollback, and disaster-recovery rehearsal.",
            "SLO, alert, trace, and audit evidence for critical paths.",
            "Security and policy tests before exposing privileged operations.",
        ),
        risks=(
            "Infrastructure projects need clear control-plane and runtime-plane separation from day one.",
            "Operational safety cannot depend on dashboards without runnable recovery proof.",
        ),
    ),
    Archetype(
        archetype_id="security_compliance",
        label="Security Or Compliance Program",
        keywords=("security", "compliance", "soc2", "audit", "privacy", "iam", "threat model", "risk", "scanner", "policy"),
        components=(
            ComponentBlueprint("asset-inventory", "Asset Inventory", "platform", "src/assets", "Systems, data, identities, and control ownership inventory."),
            ComponentBlueprint("policy-engine", "Policy Engine", "library", "src/policy", "Rules, exceptions, approval, and enforcement boundary."),
            ComponentBlueprint("detection", "Detection", "service", "src/detection", "Signals, findings, triage, and alerting boundary."),
            ComponentBlueprint("evidence-store", "Evidence Store", "platform", "src/evidence", "Audit evidence, retention, provenance, and export contract."),
            ComponentBlueprint("remediation", "Remediation", "service", "src/remediation", "Fix workflow, ownership assignment, and verification boundary."),
            ComponentBlueprint("reporting", "Reporting", "application", "src/reporting", "Controls, audit views, risk dashboards, and stakeholder readouts."),
        ),
        diagrams=(
            DiagramBlueprint("trust-boundary", "Trust Boundary", "Show actors, assets, policy, evidence, detection, and remediation boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show inventory, controls, evidence, remediation, and audit-readiness waves."),
            DiagramBlueprint("evidence-flow", "Evidence Flow", "Show signal capture, control mapping, evidence storage, and audit export."),
            DiagramBlueprint("response-flow", "Response Flow", "Show finding triage, assignment, remediation, verification, and closeout."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Threat model and control mapping for each protected boundary.",
            "Evidence provenance, retention, and export tests.",
            "Detection and remediation workflow fixtures with negative cases.",
        ),
        risks=(
            "Compliance labels must map to actual controls and evidence, not generated prose.",
            "Security workflows need explicit ownership and denial paths before automation broadens.",
        ),
    ),
    Archetype(
        archetype_id="iot_instrumentation",
        label="IoT, Robotics, Or Scientific Instrument Workflow",
        keywords=("iot", "embedded", "device", "sensor", "robot", "robotics", "instrument", "telemetry", "edge", "calibration"),
        components=(
            ComponentBlueprint("device-runtime", "Device Runtime", "runtime", "src/device", "Firmware, embedded runtime, or device control boundary."),
            ComponentBlueprint("edge-gateway", "Edge Gateway", "service", "src/edge", "Local buffering, command mediation, and offline behavior."),
            ComponentBlueprint("telemetry-ingestion", "Telemetry Ingestion", "service", "src/telemetry", "Measurements, event capture, and time-series ingest boundary."),
            ComponentBlueprint("control-api", "Control API", "service", "src/control", "Command authorization, safety interlocks, and operator controls."),
            ComponentBlueprint("calibration-validation", "Calibration Validation", "test", "tests/calibration", "Calibration fixtures, tolerances, drift checks, and hardware-in-loop proof."),
            ComponentBlueprint("operations-dashboard", "Operations Dashboard", "application", "apps/dashboard", "Live device, telemetry, alert, and operator workflow surface."),
        ),
        diagrams=(
            DiagramBlueprint("device-edge-cloud", "Device Edge Cloud Topology", "Show device, gateway, ingestion, control, dashboard, and validation boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show simulation, device integration, telemetry, control safety, and field-readiness waves."),
            DiagramBlueprint("telemetry-flow", "Telemetry Flow", "Show measurement capture, buffering, ingest, validation, and dashboard readout."),
            DiagramBlueprint("command-safety-flow", "Command Safety Flow", "Show operator command, authorization, interlock, device action, and rollback."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Simulation, hardware-in-loop, and offline recovery tests.",
            "Calibration, unit, tolerance, and sensor-drift checks.",
            "Latency, packet-loss, authorization, and safety-interlock proof.",
        ),
        risks=(
            "Device and control paths need safety gates before live actuation is proposed.",
            "Telemetry correctness depends on units, calibration, and clock/provenance metadata.",
        ),
    ),
    Archetype(
        archetype_id="saas_application",
        label="SaaS Application",
        keywords=("saas", "crm", "dashboard", "admin", "internal tool", "b2b", "tenant", "workflow", "portal"),
        components=(
            ComponentBlueprint("web-app", "Web App", "application", "apps/web", "User-facing screens, navigation, and client state."),
            ComponentBlueprint("api", "API", "service", "src/api", "HTTP/API contract, validation, and request orchestration."),
            ComponentBlueprint("domain-core", "Domain Core", "library", "src/domain", "Business rules, workflow state, and domain invariants."),
            ComponentBlueprint("persistence", "Persistence", "platform", "src/persistence", "Database access, migrations, and data contracts."),
            ComponentBlueprint("auth", "Authentication", "service", "src/auth", "Identity, tenancy, permissions, and session boundary."),
        ),
        diagrams=(
            DiagramBlueprint("system-context", "System Context", "Show users, admins, API, domain, persistence, auth, and external systems."),
            DiagramBlueprint("program-waves", "Program Waves", "Show discovery, foundation, first workflow, and hardening release order."),
            DiagramBlueprint("runtime-topology", "Runtime Topology", "Show web, API, domain, persistence, and auth request flow."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Core workflow acceptance tests across role and tenancy boundaries.",
            "Permission and data-isolation tests.",
            "Migration and rollback tests for persisted state.",
        ),
        risks=(
            "Tenant, auth, and domain boundaries need explicit ownership before implementation broadens.",
            "Dashboard UX should be proved with browser tests, not only unit tests.",
        ),
    ),
    Archetype(
        archetype_id="mobile_game_education",
        label="Mobile, Game, Or Education Experience",
        keywords=("mobile", "ios", "android", "game", "learning", "education", "course", "lesson", "student", "interactive"),
        components=(
            ComponentBlueprint("experience-shell", "Experience Shell", "application", "apps/client", "Primary interaction surface, navigation, and local state."),
            ComponentBlueprint("content-model", "Content Model", "library", "src/content", "Lessons, scenes, levels, exercises, and progression rules."),
            ComponentBlueprint("interaction-engine", "Interaction Engine", "library", "src/interactions", "Input, feedback, scoring, and session mechanics."),
            ComponentBlueprint("progress-sync", "Progress Sync", "service", "src/progress", "User progress, saves, achievements, and recovery."),
            ComponentBlueprint("quality-harness", "Quality Harness", "test", "tests/experience", "Device, browser, accessibility, and gameplay/lesson proof."),
        ),
        diagrams=(
            DiagramBlueprint("experience-topology", "Experience Topology", "Show client, content, interaction, progress, and quality boundaries."),
            DiagramBlueprint("session-flow", "Session Flow", "Show user session start, interaction, feedback, save, and recovery order."),
            DiagramBlueprint("program-waves", "Program Waves", "Show prototype, core loop, content, and launch-readiness waves."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "End-to-end interaction proof on target devices or browser viewports.",
            "Accessibility, save/recovery, and progression-state tests.",
            "Content correctness or gameplay-loop regression fixtures.",
        ),
        risks=(
            "Experience quality needs rendered proof, not just source-level tests.",
            "Progress and content boundaries should be explicit before adding many lessons or levels.",
        ),
    ),
    Archetype(
        archetype_id="cli_library",
        label="CLI Or Library Project",
        keywords=("cli", "command line", "library", "sdk", "package", "tool", "developer tool"),
        components=(
            ComponentBlueprint("command-surface", "Command Surface", "cli", "src/cli", "CLI commands, arguments, output, and error contracts."),
            ComponentBlueprint("core-library", "Core Library", "library", "src/core", "Reusable runtime behavior and public API."),
            ComponentBlueprint("config", "Configuration", "library", "src/config", "Configuration loading, validation, and defaults."),
            ComponentBlueprint("tests", "Contract Tests", "test", "tests", "CLI, API, and compatibility regression suite."),
        ),
        diagrams=(
            DiagramBlueprint("command-topology", "Command Topology", "Show CLI, core library, configuration, and test contracts."),
            DiagramBlueprint("program-waves", "Program Waves", "Show API contract, CLI contract, compatibility, and release waves."),
            DiagramBlueprint("execution-flow", "Execution Flow", "Show command parsing, core execution, output, and failure handling."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Golden CLI output and error-code tests.",
            "Public API compatibility tests.",
            "Install/import smoke tests across supported environments.",
        ),
        risks=(
            "CLI output and API contracts should stay stable before downstream users depend on them.",
            "Configuration defaults must be explicit to avoid hidden environment coupling.",
        ),
    ),
    Archetype(
        archetype_id="general_application",
        label="General Software Project",
        keywords=("app", "application", "project", "platform", "system", "website", "service", "product", "build"),
        components=(
            ComponentBlueprint("user-experience", "User Experience", "application", "apps/web", "Primary user workflow and interface boundary."),
            ComponentBlueprint("application-core", "Application Core", "service", "src/app", "Core use cases, orchestration, and domain state."),
            ComponentBlueprint("data-boundary", "Data Boundary", "platform", "src/data", "Persistence, data access, and schema lifecycle."),
            ComponentBlueprint("integration-boundary", "Integration Boundary", "integration", "src/integrations", "External APIs, adapters, and integration contracts."),
            ComponentBlueprint("validation", "Validation", "test", "tests", "Acceptance, contract, runtime, and regression proof."),
        ),
        diagrams=(
            DiagramBlueprint("system-context", "System Context", "Show users, core application, data, integrations, and validation boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show discovery, foundation, first slice, and hardening release order."),
            DiagramBlueprint("component-topology", "Component Topology", "Show proposed component ownership and intended source paths."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Acceptance tests for the first user workflow.",
            "Contract tests at external boundaries.",
            "Browser or runtime proof for user-facing behavior.",
        ),
        risks=(
            "The first slice needs a real user workflow so governance does not become a generic bucket.",
            "External integrations should stay behind named boundaries from the beginning.",
        ),
    ),
)


def _words(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", str(value or "").casefold()) if token}


def _score_archetype(prompt: str, archetype: Archetype) -> int:
    normalized = " ".join(str(prompt or "").casefold().split())
    score = 0
    for keyword in archetype.keywords:
        token = str(keyword).casefold()
        if token in normalized:
            score += 3 if " " in token else 2
    prompt_words = _words(normalized)
    for keyword in archetype.keywords:
        key_words = _words(keyword)
        if key_words and key_words <= prompt_words:
            score += len(key_words)
    return score


def select_archetype(prompt: str) -> tuple[Archetype, float]:
    """Return the highest-scoring archetype and a bounded confidence score."""

    ranked = sorted(
        ((_score_archetype(prompt, archetype), archetype) for archetype in ARCHETYPES),
        key=lambda row: (row[0], 0 if row[1].archetype_id == "general_application" else 1, row[1].archetype_id),
        reverse=True,
    )
    score, archetype = ranked[0]
    if score <= 0:
        archetype = next(item for item in ARCHETYPES if item.archetype_id == "general_application")
        return archetype, 0.42
    return archetype, min(0.92, 0.48 + (score * 0.06))
