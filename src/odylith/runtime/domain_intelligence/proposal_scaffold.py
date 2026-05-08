"""Deterministic apply-ready greenfield proposal scaffolding."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.proposal_rendering import build_apply_commands
from odylith.runtime.domain_intelligence.robot_swarm_profile import apply_robot_swarm_logistics_profile
from odylith.runtime.domain_intelligence.robot_swarm_profile import is_robot_swarm_logistics_prompt


def build_apply_ready_proposal(
    *,
    prompt: str,
    intent_title: str,
    project_slug: str,
    observed_source: Mapping[str, Any],
    release_selector: str = "",
) -> dict[str, Any]:
    """Build a conservative proposal object that can pass apply gates."""

    selector = str(release_selector or "").strip() or greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR
    title = str(intent_title or "").strip() or "Greenfield Project"
    slug = slugify(str(project_slug or "").strip() or title) or "greenfield-project"
    robot_swarm_logistics = is_robot_swarm_logistics_prompt(prompt)
    components = _component_ids(slug=slug, robot_swarm_logistics=robot_swarm_logistics)
    diagrams = _diagram_ids(slug=slug)
    proposal: dict[str, Any] = {
        "schema_version": "odylith.greenfield.host_reasoned.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "proposal_first_confirm_before_apply",
        "intent": _intent(prompt=prompt, title=title, slug=slug, robot_swarm_logistics=robot_swarm_logistics),
        "observed_source": dict(observed_source),
        "assumptions": _base_assumptions(),
        "open_questions": _base_open_questions(),
        "risks": _base_risks(),
        "security_compliance": _base_security_compliance(title),
        "validation_strategy": _base_validation_strategy(),
        "program": _program(title=title, components=components),
        "release_plan": _release_plan(
            selector=selector,
            slug=slug,
            experience_component=components["experience"],
            domain_component=components["domain"],
        ),
        "backlog": _backlog(
            title=title,
            selector=selector,
            components=components,
            diagrams=diagrams,
        ),
        "components": _components(components, diagrams=diagrams),
        "diagrams": _diagrams(title=title, components=components, diagrams=diagrams),
    }
    if robot_swarm_logistics:
        apply_robot_swarm_logistics_profile(
            proposal,
            title=title,
            selector=selector,
            experience_component=components["experience"],
            domain_component=components["domain"],
            validation_component=components["validation"],
            diagram_slugs=diagrams,
        )
    proposal["apply_commands"] = build_apply_commands(proposal)
    return proposal


def _component_ids(*, slug: str, robot_swarm_logistics: bool) -> dict[str, str]:
    suffixes = (
        ("fleet-console", "coordination-core", "simulation-harness")
        if robot_swarm_logistics
        else ("experience", "domain-core", "verification-harness")
    )
    return {
        "experience": f"{slug}-{suffixes[0]}",
        "domain": f"{slug}-{suffixes[1]}",
        "validation": f"{slug}-{suffixes[2]}",
    }


def _diagram_ids(*, slug: str) -> dict[str, str]:
    return {
        "overview": f"{slug}-system-overview",
        "slice": f"{slug}-first-slice-flow",
        "component_map": f"{slug}-component-ownership-map",
        "domain_state": f"{slug}-domain-state-model",
        "validation_release": f"{slug}-validation-release-topology",
    }


def _intent(*, prompt: str, title: str, slug: str, robot_swarm_logistics: bool) -> dict[str, Any]:
    summary = (
        "Govern a simulation-first robot swarm logistics platform with operator dispatch, fleet telemetry, "
        "coordination contracts, and safety proof before hardware or production claims."
        if robot_swarm_logistics
        else f"Turn `{prompt}` into a governed greenfield program before source-backed implementation starts."
    )
    return {
        "prompt": prompt,
        "title": title,
        "project_slug": slug,
        "summary": summary,
        "reasoning_mode": "odylith_apply_ready_scaffold",
        "evidence_tier": "user_intent",
    }


def _base_assumptions() -> list[dict[str, str]]:
    return [
        {
            "id": "A1",
            "evidence_tier": "odylith_assumption",
            "statement": "The first release should prove a narrow operator-visible workflow before broad source architecture is claimed.",
        },
        {
            "id": "A2",
            "evidence_tier": "odylith_assumption",
            "statement": "Implementation starts with repository-native tests and one Odylith-governed technical plan per child workstream.",
        },
    ]


def _base_open_questions() -> list[dict[str, str]]:
    return [
        {
            "id": "Q1",
            "evidence_tier": "user_intent",
            "question": "Which runtime, deployment target, and user role should constrain the first implementation slice?",
        },
        {
            "id": "Q2",
            "evidence_tier": "user_intent",
            "question": "Which data, safety, privacy, or compliance constraints materially change the first release gate?",
        },
    ]


def _base_risks() -> list[dict[str, str]]:
    return [
        {
            "id": "R1",
            "evidence_tier": "odylith_assumption",
            "statement": (
                "Starting implementation without a named product spine, component ownership, and proof gates can "
                "create disconnected source slices."
            ),
            "mitigation": (
                "Apply this proposal only after the operator confirms the first wave, then bind each source change "
                "to the created Radar workstream."
            ),
        },
        {
            "id": "R2",
            "evidence_tier": "odylith_assumption",
            "statement": "Security, privacy, accessibility, and operational risks can be under-modeled in broad greenfield prompts.",
            "mitigation": "Keep the first release scoped to explicit role, data, audit, abuse, and recovery checks before production claims.",
        },
    ]


def _base_security_compliance(title: str) -> dict[str, str]:
    return {
        "domain": f"{title} is at proposal stage with user-intent evidence only; domain and delivery risk stay explicit until source exists.",
        "security": (
            "Security posture starts with authentication or operator access boundaries, least-privilege writes, "
            "secret-free fixtures, abuse checks, and auditability for important actions."
        ),
        "policy": (
            "Policy posture tracks privacy, retention, accessibility, safety or regulatory review needs, and "
            "operator-visible fallback behavior before release promotion."
        ),
    }


def _base_validation_strategy() -> list[str]:
    return [
        "First-wave workstreams must define source-backed behavior proof before implementation starts.",
        "Registry candidate specs must name interfaces, dependencies, first coding slice, definition of done, and verification commands.",
        "Atlas diagrams must render after apply and remain traceable to Radar workstreams and Registry components.",
        "Compass and Radar must show the first release lane, active wave, start workstream, and proof gates after apply.",
    ]


def _program(*, title: str, components: Mapping[str, str]) -> dict[str, Any]:
    return {
        "name": title,
        "waves": [
            {
                "wave_id": "W1",
                "label": "First governed slice",
                "goal": "Prove the smallest coherent product workflow with source-backed validation.",
                "validation_gate": (
                    "The first workstream has a technical plan, behavior proof, refreshed Radar/Registry/Atlas/"
                    "Compass surfaces, and release-target validation."
                ),
                "workstreams": ["WS-01", "WS-02"],
                "component_focus": [components["experience"], components["domain"]],
                "evidence_tier": "odylith_assumption",
            },
            {
                "wave_id": "W2",
                "label": "Hardening and operations",
                "goal": "Add operational proof, fallback behavior, and release-readiness checks after the first slice works.",
                "validation_gate": (
                    "Operational, accessibility, security, and recovery checks pass without widening the first release scope."
                ),
                "workstreams": ["WS-03"],
                "component_focus": [components["validation"]],
                "evidence_tier": "odylith_assumption",
            },
        ],
    }


def _release_plan(
    *,
    selector: str,
    slug: str,
    experience_component: str,
    domain_component: str,
) -> dict[str, Any]:
    return {
        "selector": selector,
        "label": greenfield_programs.compact_release_target_label(selector),
        "provisional_release_id": f"release-{slug}-{slugify(selector)}",
        "strategy": "Promote only after the first governed slice has source-backed tests and refreshed Odylith surfaces.",
        "target_workstreams": ["WS-01", "WS-02"],
        "release_stages": [
            {
                "release": selector,
                "label": "First governed slice",
                "exit_criteria": "Product workflow, domain contract, Atlas render, Registry specs, Compass, and Radar all agree.",
            }
        ],
        "promotion_criteria": [
            "First workstream has a technical plan and repository-native behavior proof.",
            "Registry, Atlas, Radar, and Compass refresh cleanly after source changes.",
        ],
        "component_focus": [experience_component, domain_component],
        "evidence_tier": "odylith_assumption",
    }


def _backlog(*, title: str, selector: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> list[dict[str, Any]]:
    return [
        _umbrella_backlog_row(title=title, selector=selector, components=components, diagrams=diagrams),
        _workflow_backlog_row(title=title, components=components, diagrams=diagrams),
        _domain_backlog_row(title=title, components=components, diagrams=diagrams),
        _verification_backlog_row(title=title, components=components, diagrams=diagrams),
    ]


def _umbrella_backlog_row(
    *,
    title: str,
    selector: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "id": "WS-00",
        "title": f"Govern {title}",
        "workstream_type": "umbrella",
        "problem": (
            f"{title} needs a governed execution spine before source exists, otherwise first-wave implementation "
            "choices will not trace to product intent, components, diagrams, release gates, or validation proof."
        ),
        "customer": "The project operator, implementation agents, reviewers, and maintainers who need one trusted program view before code starts.",
        "opportunity": (
            "Create one umbrella program that ties user intent, first wave, release target, Radar workstreams, "
            "Registry candidates, Atlas topology, and proof gates together."
        ),
        "product_view": f"A proposal-first Odylith program for {title} with one active first wave, a {selector} release target, candidate components, and diagram traceability.",
        "recommended_first_slice": "Confirm the first governed slice, then open the first child workstream and author the technical plan before editing source.",
        "success_metrics": [
            "Compass shows the umbrella, first wave, and release target after apply.",
            "Radar, Registry, and Atlas all link the first-wave workstreams to the same component and diagram boundaries.",
            "The start workstream includes validation gates and a first implementation prompt.",
        ],
        "component_focus": [components["experience"], components["domain"], components["validation"]],
        "related_diagram_slugs": [
            diagrams["overview"],
            diagrams["slice"],
            diagrams["component_map"],
            diagrams["domain_state"],
            diagrams["validation_release"],
        ],
        "dependencies": ["Child workstreams depend on this umbrella for wave membership, release targeting, and proof sequencing."],
        "interfaces": ["Compass, Radar, Registry, and Atlas expose one shared greenfield program topology."],
        "validation": ["Greenfield apply Tribunal passes and all four dashboard surfaces refresh."],
        "domain_risk": "Greenfield governance can mislead source implementation if the first wave, component ownership, release target, or proof gates are vague.",
        "security_posture": "Security, privacy, accessibility, abuse, audit, and recovery posture stay explicit until source-backed implementation narrows them.",
        "priority": "P1",
        "sizing": "L",
        "complexity": "High",
        "evidence_tier": "user_intent",
    }


def _workflow_backlog_row(*, title: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> dict[str, Any]:
    return {
        "id": "WS-01",
        "title": "Define first operator workflow",
        "problem": f"{title} needs one concrete operator-visible workflow before implementation can avoid generic scaffolding.",
        "customer": "Primary users or operators of the proposed product and the engineers implementing the first slice.",
        "opportunity": "Turn broad intent into a narrow behavior path that can be implemented, tested, and reviewed without claiming the whole system is done.",
        "product_view": "The first workflow owns entry, happy path, empty or degraded state, and user-visible completion criteria.",
        "recommended_first_slice": "Implement the smallest operator-visible path with normal, empty, and degraded/error state proof.",
        "success_metrics": [
            "The first workflow has a source-backed test or browser proof before the next wave starts.",
            "The workflow boundary appears in Registry and Atlas with linked Radar traceability.",
        ],
        "component_focus": [components["experience"], components["domain"]],
        "related_diagram_slugs": [diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
        "dependencies": ["Depends on the domain contract workstream for the data and command boundary used by the first workflow."],
        "interfaces": ["Defines the first user-facing route, command, CLI, or service entrypoint plus visible fallback states."],
        "validation": ["Repository-native behavior proof covers the first workflow normal path and at least one degraded or empty state."],
        "priority": "P1",
        "sizing": "M",
        "complexity": "Medium",
        "evidence_tier": "user_intent",
    }


def _domain_backlog_row(*, title: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> dict[str, Any]:
    return {
        "id": "WS-02",
        "title": "Define domain contract and ownership",
        "problem": f"{title} cannot scale beyond the first workflow without a named domain contract for state, commands, ownership, and invariants.",
        "customer": "Engineers implementing source boundaries and reviewers checking correctness of data and state transitions.",
        "opportunity": "Make the domain core explicit before storage, API, worker, or UI choices harden into accidental architecture.",
        "product_view": "A domain component owns the first state model, commands, invariants, and integration handoff used by the operator workflow.",
        "recommended_first_slice": "Write the domain contract and minimal implementation that the first workflow consumes.",
        "success_metrics": [
            "Domain contract tests prove the first state transition and invalid input rejection.",
            "Registry records the domain component interfaces, dependencies, and verification commands.",
        ],
        "component_focus": [components["domain"]],
        "related_diagram_slugs": [diagrams["component_map"], diagrams["domain_state"], diagrams["slice"]],
        "dependencies": ["Depends on confirmed first-workflow semantics and defers storage selection until technical planning."],
        "interfaces": ["Defines the initial command, query, event, or file contract consumed by the first workflow."],
        "validation": ["Contract tests cover valid transition, invalid input, and idempotent or retry behavior where relevant."],
        "priority": "P1",
        "sizing": "M",
        "complexity": "Medium",
        "evidence_tier": "odylith_assumption",
    }


def _verification_backlog_row(*, title: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> dict[str, Any]:
    return {
        "id": "WS-03",
        "title": "Add release proof and operations harness",
        "problem": f"{title} needs repeatable proof, fallback checks, and release-readiness evidence before the first slice can be promoted.",
        "customer": "Maintainers, reviewers, and future operators who need reproducible validation instead of a one-off manual demo.",
        "opportunity": "Capture the first release verification commands, smoke fixtures, and dashboard refresh proof while the program is still small.",
        "product_view": "A verification harness records the first release smoke, regression checks, accessibility or safety gates, and operational recovery expectations.",
        "recommended_first_slice": "Create the first smoke or regression harness around the operator workflow and domain contract.",
        "success_metrics": [
            "Release proof runs locally with deterministic fixtures and no production credentials.",
            "Compass/Radar/Registry/Atlas refresh after the proof and show the same first release lane.",
        ],
        "component_focus": [components["validation"]],
        "related_diagram_slugs": [diagrams["validation_release"], diagrams["domain_state"]],
        "dependencies": ["Depends on WS-01 and WS-02 behavior proof before hardening expands scope."],
        "interfaces": ["Defines local smoke commands, fixture inputs, report output, and release-readiness checks."],
        "validation": ["Smoke proof runs under the repo-native toolchain and fails closed on missing fixtures or stale surfaces."],
        "priority": "P2",
        "sizing": "M",
        "complexity": "Medium",
        "evidence_tier": "odylith_assumption",
    }


def _components(components: Mapping[str, str], *, diagrams: Mapping[str, str]) -> list[dict[str, Any]]:
    return [
        _component_row(
            component_id=components["experience"],
            label="Experience Boundary",
            kind="application",
            path=f"src/{components['experience']}",
            responsibility="Own the first operator-visible workflow, view or command entrypoint, visible states, and interaction proof.",
            boundary="Owns entry, normal path, empty/degraded/error states, and human-facing behavior for the first workflow.",
            dependencies=["Depends on the domain core contract and the verification harness for source-backed proof."],
            interfaces=["User-facing route, command, CLI, or service entrypoint plus visible state contract."],
            validation=["Behavior or browser proof for normal, empty, and degraded/error states."],
            diagrams=[diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
        ),
        _component_row(
            component_id=components["domain"],
            label="Domain Core",
            kind="service",
            path=f"src/{components['domain']}",
            responsibility="Own the first domain state model, command or query contract, invariants, and integration handoff.",
            boundary="Owns domain state and invariant enforcement; excludes presentation and release harness ownership.",
            dependencies=[
                "Depends on confirmed first-workflow semantics; no storage or external provider dependency is claimed before source planning."
            ],
            interfaces=["Initial command, query, event, or file contract consumed by the experience boundary."],
            validation=["Contract tests for valid transition, invalid input rejection, and retry or idempotency behavior."],
            diagrams=[diagrams["overview"], diagrams["slice"], diagrams["component_map"], diagrams["domain_state"]],
        ),
        _component_row(
            component_id=components["validation"],
            label="Verification Harness",
            kind="tooling",
            path=f"tests/{components['validation']}",
            responsibility="Own deterministic first-release proof, fixtures, validation command documentation, and surface-refresh checks.",
            boundary="Owns local proof fixtures and release-readiness checks; excludes product runtime behavior.",
            dependencies=[
                "Depends on WS-01 and WS-02 source proof and uses no production credentials or live external systems by default."
            ],
            interfaces=["Local smoke command, fixture inputs, report output, and Odylith surface refresh verification."],
            validation=["Smoke, lint, typecheck, build, and dashboard refresh proof named by the first technical plan."],
            diagrams=[diagrams["overview"], diagrams["validation_release"]],
        ),
    ]


def _component_row(
    *,
    component_id: str,
    label: str,
    kind: str,
    path: str,
    responsibility: str,
    boundary: str,
    dependencies: list[str],
    interfaces: list[str],
    validation: list[str],
    diagrams: list[str],
) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "label": label,
        "kind": kind,
        "intended_path": path,
        "status": "planned",
        "qualification": "candidate",
        "responsibility": responsibility,
        "boundary": boundary,
        "dependencies": dependencies,
        "interfaces": interfaces,
        "validation": validation,
        "related_diagram_slugs": diagrams,
        "evidence_tier": "user_intent",
    }


def _diagrams(*, title: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "slug": diagrams["overview"],
            "title": f"{title} System Overview",
            "kind": "flowchart",
            "summary": "Top-level greenfield topology from operator intent through experience, domain core, verification harness, and Odylith surfaces.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["experience"], "description": "Owns the first operator-visible workflow and visible states."},
                {"name": components["domain"], "description": "Owns the first domain contract, state model, and invariants."},
                {"name": components["validation"], "description": "Owns deterministic first-release proof and refresh checks."},
            ],
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _overview_mermaid(),
        },
        {
            "slug": diagrams["slice"],
            "title": f"{title} First Slice Flow",
            "kind": "sequenceDiagram",
            "summary": "Sequence for the first operator workflow flowing through experience, domain core, proof harness, and governance refresh.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["experience"], "description": "Starts the operator-visible first workflow."},
                {"name": components["domain"], "description": "Validates state and command semantics for the workflow."},
                {"name": components["validation"], "description": "Runs proof and captures release-readiness evidence."},
            ],
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _slice_mermaid(),
        },
        {
            "slug": diagrams["component_map"],
            "title": f"{title} Component Ownership Map",
            "kind": "flowchart",
            "summary": "Ownership view showing which planned component owns experience, domain state, proof fixtures, and governance handoff.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["experience"], "description": "Owns the human-facing first workflow boundary and fallback behavior."},
                {"name": components["domain"], "description": "Owns domain state, command semantics, and invariant enforcement."},
                {"name": components["validation"], "description": "Owns deterministic proof fixtures and release-readiness reports."},
            ],
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _component_map_mermaid(),
        },
        {
            "slug": diagrams["domain_state"],
            "title": f"{title} Domain State Model",
            "kind": "stateDiagram",
            "summary": "State view for the first domain contract, including valid completion, rejection, retry, and degraded handling paths.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["domain"], "description": "Owns the domain states and valid transitions for the first slice."},
                {"name": components["experience"], "description": "Renders accepted, rejected, completed, and degraded states to the operator."},
                {"name": components["validation"], "description": "Exercises state transitions through deterministic contract proof."},
            ],
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _domain_state_mermaid(),
        },
        {
            "slug": diagrams["validation_release"],
            "title": f"{title} Validation And Release Topology",
            "kind": "flowchart",
            "summary": "Release-readiness view tying repo-native proof, Odylith surface refresh, Compass lane, and operator handoff together.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["validation"], "description": "Owns the proof command, fixtures, and release-readiness evidence."},
                {"name": components["experience"], "description": "Supplies behavior proof for normal, empty, and degraded states."},
                {"name": components["domain"], "description": "Supplies contract proof for state, commands, and invariant failures."},
            ],
            "related_workstreams": ["WS-00", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _validation_release_mermaid(),
        },
    ]


def _overview_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Intent[Operator<br/>intent] --> Experience[Experience<br/>boundary]\n"
        "  Experience --> Domain[Domain<br/>core]\n"
        "  Domain --> Harness[Verification<br/>harness]\n"
        "  Harness --> Surfaces[Odylith<br/>surfaces]\n"
        "  Surfaces --> Review[Operator<br/>review]\n"
        "  classDef actor fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
        "  classDef service fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  class Intent,Review actor;\n"
        "  class Experience,Domain service;\n"
        "  class Harness,Surfaces proof;\n"
    )


def _slice_mermaid() -> str:
    return (
        "sequenceDiagram\n"
        "  participant Operator as Operator\n"
        "  participant Experience as Experience Boundary\n"
        "  participant Domain as Domain Core\n"
        "  participant Harness as Verification Harness\n"
        "  participant Surfaces as Odylith Surfaces\n"
        "  Operator->>Experience: start first workflow\n"
        "  Experience->>Domain: execute command or query\n"
        "  Domain-->>Experience: validated state result\n"
        "  Harness->>Experience: run behavior proof\n"
        "  Harness->>Domain: run contract proof\n"
        "  Harness->>Surfaces: refresh Radar Registry Atlas Compass\n"
        "  Surfaces-->>Operator: show first wave and release lane\n"
    )


def _component_map_mermaid() -> str:
    return (
        "flowchart TB\n"
        "  subgraph experience[Experience<br/>ownership]\n"
        "    Entry[First workflow<br/>entrypoint]:::ux\n"
        "    States[Visible normal empty<br/>and degraded states]:::ux\n"
        "  end\n"
        "  subgraph domain[Domain<br/>ownership]\n"
        "    Contract[Command query<br/>and event contract]:::core\n"
        "    Invariants[State invariants<br/>and rejection rules]:::core\n"
        "  end\n"
        "  subgraph proof[Proof<br/>ownership]\n"
        "    Fixtures[Deterministic<br/>fixtures]:::proof\n"
        "    Report[Release readiness<br/>report]:::proof\n"
        "  end\n"
        "  Entry --> Contract --> Invariants --> States\n"
        "  Fixtures --> Contract\n"
        "  Fixtures --> Entry\n"
        "  Report --> Surfaces[Compass Radar<br/>Registry Atlas]:::governance\n"
        "  classDef ux fill:#fff7df,stroke:#d7a93d,color:#52390a;\n"
        "  classDef core fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef governance fill:#f1f5f9,stroke:#94a3b8,color:#1f2937;\n"
    )


def _domain_state_mermaid() -> str:
    return (
        "stateDiagram-v2\n"
        "  [*] --> Draft\n"
        "  Draft --> Accepted: valid command\n"
        "  Draft --> Rejected: invalid input\n"
        "  Accepted --> InProgress: workflow starts\n"
        "  InProgress --> Completed: success proof\n"
        "  InProgress --> Degraded: dependency missing\n"
        "  Degraded --> Retried: retry allowed\n"
        "  Retried --> Completed: recovery succeeds\n"
        "  Retried --> Rejected: retry exhausted\n"
        "  Completed --> [*]\n"
        "  Rejected --> [*]\n"
    )


def _validation_release_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Plan[Technical plan<br/>for first workstream]:::governance --> Behavior[Behavior proof<br/>normal empty degraded]:::proof\n"
        "  Plan --> Contract[Contract proof<br/>state and invariants]:::proof\n"
        "  Behavior --> Harness[Verification<br/>harness]:::proof\n"
        "  Contract --> Harness\n"
        "  Harness --> Refresh[Surface refresh<br/>Radar Registry Atlas Compass]:::governance\n"
        "  Refresh --> Lane[Compass lane<br/>release 0.0.1]:::release\n"
        "  Lane --> Handoff[Operator handoff<br/>next command and gates]:::release\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef governance fill:#f1f5f9,stroke:#94a3b8,color:#1f2937;\n"
        "  classDef release fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
    )


__all__ = ["build_apply_ready_proposal"]
