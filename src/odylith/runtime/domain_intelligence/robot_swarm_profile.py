"""Prompt-visible robot swarm logistics profile for greenfield scaffolds."""

from __future__ import annotations

from typing import Any, Mapping


def is_robot_swarm_logistics_prompt(prompt: str) -> bool:
    lowered = str(prompt or "").casefold()
    robot_terms = ("robot", "amr", "autonomous mobile robot", "fleet", "swarm")
    logistics_terms = ("logistics", "warehouse", "fulfillment", "yard", "inventory", "pick", "putaway")
    return any(term in lowered for term in robot_terms) and any(term in lowered for term in logistics_terms)


def apply_robot_swarm_logistics_profile(
    proposal: dict[str, Any],
    *,
    title: str,
    selector: str,
    experience_component: str,
    domain_component: str,
    validation_component: str,
    diagram_slugs: Mapping[str, str],
) -> None:
    """Specialize the deterministic scaffold using only prompt-visible domain facts."""

    proposal["assumptions"] = _assumptions()
    proposal["open_questions"] = _open_questions()
    proposal["risks"] = _risks()
    proposal["security_compliance"] = _security_compliance(title)
    proposal["validation_strategy"] = _validation_strategy()
    proposal["program"]["waves"] = _waves(
        experience_component=experience_component,
        domain_component=domain_component,
        validation_component=validation_component,
    )
    proposal["release_plan"].update(_release_plan_updates(title=title, selector=selector))
    _apply_backlog_rows(proposal["backlog"], title=title, diagram_slugs=diagram_slugs)
    _apply_components(proposal["components"], diagram_slugs=diagram_slugs)
    _apply_diagrams(
        proposal["diagrams"],
        experience_component=experience_component,
        domain_component=domain_component,
        validation_component=validation_component,
        diagram_slugs=diagram_slugs,
    )


def _assumptions() -> list[dict[str, str]]:
    return [
        {
            "id": "A1",
            "evidence_tier": "odylith_assumption",
            "statement": "The first release stays simulation-first and does not claim live hardware control until hardware-in-the-loop proof exists.",
        },
        {
            "id": "A2",
            "evidence_tier": "odylith_assumption",
            "statement": "A human operator console is the first visible surface for dispatch, fleet state, and safe intervention.",
        },
        {
            "id": "A3",
            "evidence_tier": "odylith_assumption",
            "statement": "Robot identity, telemetry, task assignment, and coordination state are explicit contracts before vendor SDK integration.",
        },
    ]


def _open_questions() -> list[dict[str, str]]:
    return [
        {
            "id": "Q1",
            "evidence_tier": "user_intent",
            "question": "Is the first operating environment indoor warehouse, outdoor yard, or mixed-site logistics?",
        },
        {
            "id": "Q2",
            "evidence_tier": "user_intent",
            "question": "What first fleet scale should the simulator prove: 10s, 100s, or 1000s of robots?",
        },
        {
            "id": "Q3",
            "evidence_tier": "user_intent",
            "question": "Should the first integration target a specific robot vendor SDK, a generic MQTT/gRPC telemetry contract, or simulation only?",
        },
    ]


def _risks() -> list[dict[str, str]]:
    return [
        {
            "id": "R1",
            "evidence_tier": "odylith_assumption",
            "statement": "Multi-robot coordination can deadlock, livelock, or degrade throughput when shared zones are reserved naively.",
            "mitigation": "Start with deterministic simulation scenarios covering conflict, congestion, lost telemetry, and retry behavior.",
        },
        {
            "id": "R2",
            "evidence_tier": "odylith_assumption",
            "statement": "Operator commands and autonomous actuation are safety-sensitive even before hardware integration.",
            "mitigation": "Keep the first release simulation-only, audit every override, and require explicit safety gates before live control.",
        },
        {
            "id": "R3",
            "evidence_tier": "odylith_assumption",
            "statement": "Vendor-specific telemetry and capability models can leak into core scheduling logic.",
            "mitigation": "Use canonical robot identity, capability, telemetry, task, and reservation contracts at the domain boundary.",
        },
    ]


def _security_compliance(title: str) -> dict[str, str]:
    return {
        "domain": (
            f"{title} is a safety-sensitive robotics logistics proposal with user-intent evidence only; "
            "first-release claims stay bounded to simulation and governance proof."
        ),
        "security": (
            "Planned controls include operator role boundaries, per-robot identity, authenticated telemetry ingress, "
            "replay-resistant task commands, secret-free simulator fixtures, and audited manual overrides."
        ),
        "policy": (
            "Safety, accessibility, data retention, incident audit, and hardware-in-the-loop review remain release gates "
            "before any production or live-robot claim."
        ),
    }


def _validation_strategy() -> list[str]:
    return [
        "Run deterministic simulation proof for a single logistics task and then a two-robot conflict scenario before source promotion.",
        "Contract-test robot identity, capability metadata, telemetry envelopes, task assignment, and reservation semantics.",
        "Prove operator console normal, empty-fleet, degraded-telemetry, and rejected-override states with browser or UI tests.",
        "Audit every task assignment, override, simulated e-stop, and coordination conflict in test fixtures.",
        "Refresh release evidence after apply and after the first source-backed implementation slice.",
    ]


def _waves(
    *,
    experience_component: str,
    domain_component: str,
    validation_component: str,
) -> list[dict[str, Any]]:
    return [
        {
            "wave_id": "W1",
            "label": "Simulation-backed fleet foundations",
            "goal": "Prove a narrow operator-dispatched logistics task through simulated robot telemetry and coordination contracts.",
            "validation_gate": "One simulated robot task is visible in the console, normalized through domain contracts, and replayable in CI.",
            "workstreams": ["WS-01", "WS-02"],
            "component_focus": [experience_component, domain_component],
            "evidence_tier": "odylith_assumption",
        },
        {
            "wave_id": "W2",
            "label": "Coordination and safety hardening",
            "goal": "Add multi-robot conflict proof, degraded telemetry behavior, safety audit, and release-readiness checks.",
            "validation_gate": "Two-robot conflict, lost telemetry, rejected override, and audit replay scenarios pass deterministically.",
            "workstreams": ["WS-03"],
            "component_focus": [validation_component],
            "evidence_tier": "odylith_assumption",
        },
    ]


def _release_plan_updates(*, title: str, selector: str) -> dict[str, Any]:
    _ = title
    return {
        "strategy": (
            "Promote only after the simulation-backed dispatch path, robot domain contracts, architecture render, "
            "component specs and release records all agree."
        ),
        "release_stages": [
            {
                "release": selector,
                "label": "Simulation-backed fleet foundations",
                "exit_criteria": (
                    "Operator dispatch, robot identity, telemetry, task state, and deterministic simulation proof "
                    "are all source-backed."
                ),
            }
        ],
        "promotion_criteria": [
            "One simulated logistics task completes from operator dispatch through robot state update under CI proof.",
            "Release evidence refreshes cleanly and shows the same robot swarm first-wave lane.",
            "No live hardware, production credentials, or safety claim is made before the hardening wave.",
        ],
    }


def _apply_backlog_rows(rows: list[dict[str, Any]], *, title: str, diagram_slugs: Mapping[str, str]) -> None:
    all_diagrams = _robot_diagram_values(diagram_slugs)
    rows[0].update({"related_diagram_slugs": all_diagrams})
    rows[1].update(_dispatch_backlog_row(title, diagram_slugs=diagram_slugs))
    rows[2].update(_contract_backlog_row(title, diagram_slugs=diagram_slugs))
    rows[3].update(_simulation_backlog_row(title, diagram_slugs=diagram_slugs))


def _dispatch_backlog_row(title: str, *, diagram_slugs: Mapping[str, str]) -> dict[str, Any]:
    return {
        "title": "Dispatch and observe one simulated logistics task",
        "problem": f"{title} needs an operator-visible dispatch path before broader fleet automation can be trusted or reviewed.",
        "customer": "Warehouse or yard operators, supervisors, and engineers validating the first robot logistics workflow.",
        "opportunity": (
            "Create a thin console workflow that dispatches one simulated logistics task and shows robot state, "
            "task progress, and degraded telemetry behavior."
        ),
        "product_view": (
            "An operator selects or submits one logistics task, sees the simulated robot assignment, observes progress, "
            "and gets a clear empty or degraded state without claiming full fleet orchestration."
        ),
        "recommended_first_slice": (
            "Implement a simulation-backed dispatch/read path that shows one robot, one logistics task, progress, "
            "completion, empty-fleet state, and degraded telemetry state."
        ),
        "success_metrics": [
            "Browser or UI proof covers normal dispatch, empty fleet, degraded telemetry, and rejected override states.",
            "The console reads robot/task state through the domain contract rather than direct simulator internals.",
            "Every operator-visible state links back to the first workstream and component candidate.",
        ],
        "dependencies": [
            "Depends on the robot task and telemetry contract from WS-02 before adding vendor SDK integration.",
            "Depends on the simulation harness for deterministic robot/task fixtures.",
        ],
        "interfaces": [
            "Operator console route or command for dispatching one simulated logistics task.",
            "Read model for robot identity, task state, telemetry health, and operator-visible fallback states.",
        ],
        "validation": [
            "Browser or UI test for normal dispatch, empty fleet, degraded telemetry, and rejected override paths.",
            "Contract assertion that console state is derived from the domain contract.",
        ],
        "related_diagram_slugs": [
            diagram_slugs["overview"],
            diagram_slugs["slice"],
            diagram_slugs["component_map"],
            _robot_diagram_slug(diagram_slugs, "telemetry-contract"),
            _robot_diagram_slug(diagram_slugs, "observability-audit-loop"),
        ],
        "domain_risk": "A misleading console can hide robot state, assignment ambiguity, or unsafe operator assumptions.",
        "security_posture": "Operator commands are role-gated, override attempts are confirmation-gated, and fixtures contain no production credentials.",
    }


def _contract_backlog_row(title: str, *, diagram_slugs: Mapping[str, str]) -> dict[str, Any]:
    return {
        "title": "Define robot task, telemetry, and coordination contract",
        "problem": f"{title} cannot safely coordinate robots unless identity, capabilities, task state, telemetry, and reservation semantics are explicit.",
        "customer": "Coordination, simulation, telemetry, safety, and operator-console implementation owners.",
        "opportunity": "Define the canonical robot logistics contract before scheduler, simulator, or vendor SDK details harden into accidental architecture.",
        "product_view": "A domain contract owns robot identity, capability tags, logistics task state, telemetry health, and simple reservation outcomes.",
        "recommended_first_slice": "Implement the robot task/telemetry contract and tests for valid assignment, invalid capability, lost telemetry, and idempotent retry.",
        "success_metrics": [
            "Contract tests prove valid assignment, invalid capability rejection, lost telemetry, and idempotent retry behavior.",
            "Component records capture the domain dependencies, interfaces, and verification commands.",
            "Architecture diagrams show how console, coordination core, and simulator exchange task and telemetry state.",
        ],
        "dependencies": [
            "Depends on the first operator workflow semantics and defers vendor-specific robot SDK choices until planning.",
            "Feeds the simulation harness and operator console through canonical contracts.",
        ],
        "interfaces": [
            "Robot identity and capability schema.",
            "Logistics task assignment command and status query.",
            "Telemetry health event and simple zone or reservation state.",
        ],
        "validation": [
            "Contract tests cover assignment, invalid capability, lost telemetry, idempotent retry, and reservation-state rejection.",
            "Schema fixtures are deterministic and do not contact live robots or vendor services.",
        ],
        "related_diagram_slugs": [
            diagram_slugs["component_map"],
            diagram_slugs["domain_state"],
            _robot_diagram_slug(diagram_slugs, "telemetry-contract"),
            _robot_diagram_slug(diagram_slugs, "multi-robot-conflict"),
        ],
        "domain_risk": "Loose robot state contracts can double-assign work, hide lost telemetry, or couple core logic to one vendor.",
        "security_posture": "Per-robot identity and command replay protection are planned before any live transport is introduced.",
    }


def _simulation_backlog_row(title: str, *, diagram_slugs: Mapping[str, str]) -> dict[str, Any]:
    return {
        "title": "Add deterministic simulation and safety smoke",
        "problem": f"{title} needs repeatable fleet proof before coordination, safety, and operator behavior can be trusted beyond a demo.",
        "customer": "Maintainers, safety reviewers, and engineers validating robot coordination changes.",
        "opportunity": "Create a deterministic simulator and smoke harness that proves dispatch, telemetry loss, conflict, and audit behavior quickly.",
        "product_view": "A simulation harness runs a seedable robot world, emits canonical telemetry, exercises a two-robot conflict, and records audit evidence.",
        "recommended_first_slice": "Create a deterministic single-robot dispatch smoke, then extend fixtures for lost telemetry and two-robot slot conflict.",
        "success_metrics": [
            "Fixed seed replay produces byte-identical or semantically identical task/telemetry output across two runs.",
            "Smoke proof covers lost telemetry, two-robot conflict, rejected override, and audit output.",
            "Release evidence refreshes after proof and shows the same first release lane.",
        ],
        "dependencies": [
            "Depends on WS-01 console behavior and WS-02 robot task/telemetry contract before hardening expands scope.",
        ],
        "interfaces": [
            "Scenario runner CLI, fixture inputs, telemetry output, audit record output, and CI smoke report.",
        ],
        "validation": [
            "Seeded simulation smoke runs under the repo-native toolchain with no live network or hardware contact.",
            "Fault fixtures fail closed when telemetry, assignment, or audit records are missing.",
        ],
        "related_diagram_slugs": [
            diagram_slugs["validation_release"],
            _robot_diagram_slug(diagram_slugs, "multi-robot-conflict"),
            _robot_diagram_slug(diagram_slugs, "safety-envelope"),
            _robot_diagram_slug(diagram_slugs, "deployment-boundaries"),
            _robot_diagram_slug(diagram_slugs, "observability-audit-loop"),
        ],
        "domain_risk": "Non-deterministic simulation hides coordination regressions and weakens safety review evidence.",
        "security_posture": "Simulator fixtures contain no production credentials and cannot contact live robot transports by default.",
    }


def _apply_components(components: list[dict[str, Any]], *, diagram_slugs: Mapping[str, str]) -> None:
    components[0].update(
        {
            "label": "Fleet Operations Console",
            "responsibility": "Own the operator dispatch/read workflow, fleet state presentation, degraded telemetry states, and confirmation-gated overrides.",
            "boundary": "Owns the human-visible dispatch and fleet-status experience; excludes robot coordination policy, simulator runtime, and vendor SDK adapters.",
            "dependencies": ["Depends on the coordination core contract and simulation harness for robot/task state fixtures."],
            "interfaces": ["Dispatch route or command, fleet-state read model, override confirmation event, degraded telemetry view contract."],
            "validation": ["Browser or UI proof for normal dispatch, empty fleet, degraded telemetry, rejected override, and audit-link visibility."],
            "related_diagram_slugs": [
                diagram_slugs["overview"],
                diagram_slugs["slice"],
                diagram_slugs["component_map"],
                _robot_diagram_slug(diagram_slugs, "observability-audit-loop"),
            ],
        }
    )
    components[1].update(
        {
            "label": "Robot Coordination Core",
            "responsibility": "Own robot identity, capability, task assignment, telemetry health, reservation semantics, and invariants for the first dispatch flow.",
            "boundary": "Owns canonical robot logistics contracts and invariant enforcement; excludes presentation, simulation engine internals, and live vendor SDKs.",
            "dependencies": ["Depends on confirmed first workflow semantics and exposes stable contracts to console and simulator."],
            "interfaces": ["Robot identity schema, capability schema, task assignment command, status query, telemetry health event, reservation state."],
            "validation": ["Contract tests for assignment, invalid capability, lost telemetry, idempotent retry, and reservation-state rejection."],
            "related_diagram_slugs": [
                diagram_slugs["overview"],
                diagram_slugs["component_map"],
                diagram_slugs["domain_state"],
                _robot_diagram_slug(diagram_slugs, "telemetry-contract"),
                _robot_diagram_slug(diagram_slugs, "multi-robot-conflict"),
                _robot_diagram_slug(diagram_slugs, "safety-envelope"),
            ],
        }
    )
    components[2].update(
        {
            "label": "Simulation And Safety Harness",
            "responsibility": "Own deterministic robot-world fixtures, seeded replay, lost-telemetry and conflict scenarios, safety smoke, and release proof reports.",
            "boundary": "Owns simulation and proof fixtures; excludes production robot control and product runtime behavior.",
            "dependencies": ["Depends on the coordination core contract and first console workflow; uses no live robot transports by default."],
            "interfaces": ["Scenario runner CLI, fixture inputs, telemetry output stream, audit event output, CI smoke report."],
            "validation": ["Seeded replay proof, single-robot dispatch smoke, lost-telemetry fixture, two-robot conflict fixture, audit output check."],
            "related_diagram_slugs": [
                diagram_slugs["overview"],
                diagram_slugs["validation_release"],
                _robot_diagram_slug(diagram_slugs, "multi-robot-conflict"),
                _robot_diagram_slug(diagram_slugs, "deployment-boundaries"),
                _robot_diagram_slug(diagram_slugs, "observability-audit-loop"),
            ],
        }
    )


def _apply_diagrams(
    diagrams: list[dict[str, Any]],
    *,
    experience_component: str,
    domain_component: str,
    validation_component: str,
    diagram_slugs: Mapping[str, str],
) -> None:
    common_components = _diagram_components(
        experience_component=experience_component,
        domain_component=domain_component,
        validation_component=validation_component,
    )
    updates = [
        {
            "title": "Simulation-First Architecture Overview",
            "summary": "Topology connecting operator console, robot coordination core, deterministic simulation harness, audit proof, and release-readiness evidence.",
            "components": common_components,
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "mermaid_source": _overview_mermaid(),
        },
        {
            "title": "Dispatch And Telemetry Flow",
            "summary": "Sequence for one simulated logistics task moving from operator dispatch through coordination contract, simulator telemetry, audit, and proof report.",
            "components": common_components,
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "mermaid_source": _slice_mermaid(),
        },
        {
            "title": "Component Responsibility Map",
            "summary": "Ownership map separating operator UX, robot coordination contracts, simulation proof, safety audit, and release-readiness evidence.",
            "components": common_components,
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "mermaid_source": _component_map_mermaid(),
        },
        {
            "title": "Robot Task State Machine",
            "summary": "State model for a robot task, including assignment, execution, telemetry loss, fault, recovery, audit, and completion paths.",
            "components": common_components,
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "mermaid_source": _robot_state_mermaid(),
        },
        {
            "title": "Release Proof Topology",
            "summary": "Validation topology for simulator replay, browser proofs, contract tests, audit assertions, release evidence, and release promotion.",
            "components": common_components,
            "related_workstreams": ["WS-00", "WS-03"],
            "mermaid_source": _validation_release_mermaid(),
        },
    ]
    for row, update in zip(diagrams, updates, strict=False):
        row.update(update)
    diagrams.extend(
        _robot_extra_diagrams(
            diagram_slugs=diagram_slugs,
            components=common_components,
        )
    )


def _diagram_components(
    *,
    experience_component: str,
    domain_component: str,
    validation_component: str,
) -> list[dict[str, str]]:
    return [
        {"name": experience_component, "description": "Fleet operations console for dispatch, fleet state, and safe override UX."},
        {"name": domain_component, "description": "Robot task, telemetry, capability, and reservation contract owner."},
        {"name": validation_component, "description": "Deterministic simulator, safety smoke, and release proof owner."},
    ]


def _project_prefix(diagram_slugs: Mapping[str, str]) -> str:
    overview = str(diagram_slugs.get("overview", "")).strip()
    if overview.endswith("-system-overview"):
        return overview.removesuffix("-system-overview")
    return "robot-swarm-logistics"


def _robot_diagram_slug(diagram_slugs: Mapping[str, str], suffix: str) -> str:
    return f"{_project_prefix(diagram_slugs)}-{suffix}"


def _robot_diagram_values(diagram_slugs: Mapping[str, str]) -> list[str]:
    return [
        diagram_slugs["overview"],
        diagram_slugs["slice"],
        diagram_slugs["component_map"],
        diagram_slugs["domain_state"],
        diagram_slugs["validation_release"],
        _robot_diagram_slug(diagram_slugs, "multi-robot-conflict"),
        _robot_diagram_slug(diagram_slugs, "safety-envelope"),
        _robot_diagram_slug(diagram_slugs, "telemetry-contract"),
        _robot_diagram_slug(diagram_slugs, "deployment-boundaries"),
        _robot_diagram_slug(diagram_slugs, "observability-audit-loop"),
    ]


def _robot_extra_diagrams(
    *,
    diagram_slugs: Mapping[str, str],
    components: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        _robot_diagram_row(
            slug=_robot_diagram_slug(diagram_slugs, "multi-robot-conflict"),
            title="Multi-Robot Conflict Resolution",
            kind="sequenceDiagram",
            summary="Two-robot slot contention sequence showing reservation, bounded wait, release, replay proof, and audit evidence.",
            components=components,
            related_workstreams=["WS-02", "WS-03"],
            mermaid_source=_multi_robot_conflict_mermaid(),
        ),
        _robot_diagram_row(
            slug=_robot_diagram_slug(diagram_slugs, "safety-envelope"),
            title="Safety Envelope And E-Stop Flow",
            kind="flowchart",
            summary="Safety view for geofence breach, e-stop fan-out, operator confirmation, simulator proof, and incident audit.",
            components=components,
            related_workstreams=["WS-02", "WS-03"],
            mermaid_source=_safety_envelope_mermaid(),
        ),
        _robot_diagram_row(
            slug=_robot_diagram_slug(diagram_slugs, "telemetry-contract"),
            title="Telemetry Contract And Data Flow",
            kind="flowchart",
            summary="Data-contract view from simulator and future robots through canonical telemetry, identity, task state, console read model, and audit.",
            components=components,
            related_workstreams=["WS-01", "WS-02"],
            mermaid_source=_telemetry_contract_mermaid(),
        ),
        _robot_diagram_row(
            slug=_robot_diagram_slug(diagram_slugs, "deployment-boundaries"),
            title="Cloud Edge Simulation Boundaries",
            kind="flowchart",
            summary="Deployment-boundary view separating operator UI, control-plane contracts, simulator-only proof, future edge agent, and blocked live hardware paths.",
            components=components,
            related_workstreams=["WS-00", "WS-03"],
            mermaid_source=_deployment_boundaries_mermaid(),
        ),
        _robot_diagram_row(
            slug=_robot_diagram_slug(diagram_slugs, "observability-audit-loop"),
            title="Observability And Audit Loop",
            kind="flowchart",
            summary="Operational evidence view tying telemetry health, operator action logs, simulator replay artifacts, audit assertions, and release handoff.",
            components=components,
            related_workstreams=["WS-01", "WS-03"],
            mermaid_source=_observability_audit_mermaid(),
        ),
    ]


def _robot_diagram_row(
    *,
    slug: str,
    title: str,
    kind: str,
    summary: str,
    components: list[dict[str, str]],
    related_workstreams: list[str],
    mermaid_source: str,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "title": title,
        "kind": kind,
        "summary": summary,
        "link_state": "architecture_first_draft",
        "components": components,
        "related_workstreams": related_workstreams,
        "evidence_tier": "user_intent",
        "mermaid_source": mermaid_source,
    }


def _overview_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Operator[Operator<br/>dispatch]:::actor --> Console[Fleet Operations<br/>Console]:::ux\n"
        "  Console --> Core[Robot Coordination<br/>Core]:::core\n"
        "  Core --> Sim[Simulation And<br/>Safety Harness]:::proof\n"
        "  Sim --> Telemetry[Telemetry<br/>Replay]:::core\n"
        "  Telemetry --> Console\n"
        "  Sim --> Audit[(Audit<br/>Evidence)]:::proof\n"
        "  Audit --> Review[Release readiness<br/>review]:::planning\n"
        "  classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef ux fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef core fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
        "  classDef planning fill:#FBFDFF,stroke:#D8E5F4,color:#17233A;\n"
    )


def _slice_mermaid() -> str:
    return (
        "sequenceDiagram\n"
        "  participant Operator as Operator\n"
        "  participant Console as Fleet Operations Console\n"
        "  participant Core as Robot Coordination Core\n"
        "  participant Sim as Simulation Harness\n"
        "  participant Audit as Audit Evidence\n"
        "  Operator->>Console: dispatch one logistics task\n"
        "  Console->>Core: assign task request\n"
        "  Core-->>Console: robot assignment and task state\n"
        "  Core->>Sim: run seeded robot scenario\n"
        "  Sim-->>Core: telemetry and completion event\n"
        "  Sim->>Audit: record assignment, telemetry loss, override checks\n"
        "  Audit-->>Operator: proof report and release gate evidence\n"
    )


def _component_map_mermaid() -> str:
    return (
        "flowchart TB\n"
        "  subgraph ux[Operator<br/>experience]\n"
        "    Console[Fleet Operations<br/>Console]:::ux\n"
        "    Fallback[Empty fleet degraded<br/>telemetry rejected override]:::ux\n"
        "  end\n"
        "  subgraph core[Coordination<br/>contract]\n"
        "    Identity[Robot identity<br/>and capabilities]:::core\n"
        "    Task[Task assignment<br/>and reservation state]:::core\n"
        "    Telemetry[Telemetry health<br/>and progress model]:::core\n"
        "  end\n"
        "  subgraph proof[Simulation<br/>and safety proof]\n"
        "    Replay[Seeded scenario<br/>replay]:::proof\n"
        "    Faults[Lost telemetry conflict<br/>and override fixtures]:::proof\n"
        "    Audit[Audit evidence<br/>for release gates]:::proof\n"
        "  end\n"
        "  Console --> Identity --> Task --> Telemetry --> Console\n"
        "  Replay --> Task\n"
        "  Faults --> Telemetry\n"
        "  Faults --> Audit\n"
        "  Audit --> Gate[Simulation release<br/>readiness gate]:::planning\n"
        "  classDef ux fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef core fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
        "  classDef planning fill:#FBFDFF,stroke:#D8E5F4,color:#17233A;\n"
    )


def _robot_state_mermaid() -> str:
    return (
        "stateDiagram-v2\n"
        "  [*] --> Registered\n"
        "  Registered --> Idle: simulator starts\n"
        "  Idle --> Assigned: task accepted\n"
        "  Assigned --> Reserving: request slot\n"
        "  Reserving --> Executing: reservation granted\n"
        "  Reserving --> Waiting: bounded wait\n"
        "  Waiting --> Executing: slot released\n"
        "  Executing --> Completed: telemetry complete\n"
        "  Executing --> Degraded: telemetry lost\n"
        "  Degraded --> Recovering: retry or replay\n"
        "  Recovering --> Executing: telemetry restored\n"
        "  Degraded --> Faulted: safety gate trips\n"
        "  Faulted --> Audited: incident recorded\n"
        "  Completed --> Audited: task recorded\n"
        "  Audited --> Idle: next task allowed\n"
    )


def _validation_release_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Plan[Workstream plan<br/>B-002 first slice]:::planning --> Browser[Console browser<br/>normal empty degraded]:::proof\n"
        "  Plan --> Contract[Robot contract<br/>assignment telemetry retry]:::proof\n"
        "  Plan --> Replay[Seeded simulator<br/>replay proof]:::proof\n"
        "  Browser --> Gate[Release gate<br/>simulation only]:::release\n"
        "  Contract --> Gate\n"
        "  Replay --> Gate\n"
        "  Gate --> Evidence[Release evidence<br/>browser contract replay]:::proof\n"
        "  Evidence --> Handoff[Next wave<br/>conflict and safety]:::release\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
        "  classDef planning fill:#FBFDFF,stroke:#D8E5F4,color:#17233A;\n"
        "  classDef release fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
    )


def _multi_robot_conflict_mermaid() -> str:
    return (
        "sequenceDiagram\n"
        "  participant RobotA as Robot A\n"
        "  participant RobotB as Robot B\n"
        "  participant Core as Coordination Core\n"
        "  participant Sim as Simulation Harness\n"
        "  participant Audit as Audit Evidence\n"
        "  RobotA->>Core: reserve shared slot\n"
        "  RobotB->>Core: reserve same slot\n"
        "  Core-->>RobotA: reservation granted\n"
        "  Core-->>RobotB: bounded wait queued\n"
        "  RobotA->>Sim: enter slot and emit telemetry\n"
        "  Sim-->>Core: slot occupied event\n"
        "  RobotA->>Core: release shared slot\n"
        "  Core-->>RobotB: reservation granted after release\n"
        "  RobotB->>Sim: enter slot and emit telemetry\n"
        "  Core->>Audit: record conflict decision and wait bound\n"
    )


def _safety_envelope_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Telemetry[Telemetry health<br/>and zone position]:::core --> Safety[Safety envelope<br/>policy checks]:::safety\n"
        "  Operator[Operator override<br/>attempt]:::ux --> Confirm[Confirmation and<br/>role gate]:::ux\n"
        "  Confirm --> Safety\n"
        "  Safety -->|safe| Continue[Continue simulated<br/>task execution]:::core\n"
        "  Safety -->|breach| Estop[E-stop fan out<br/>simulation only]:::safety\n"
        "  Estop --> Audit[Incident audit<br/>and replay artifact]:::proof\n"
        "  Audit --> Review[Safety review<br/>before hardware claim]:::governance\n"
        "  classDef ux fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef core fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
        "  classDef safety fill:#FFF1F0,stroke:#F7B4AE,color:#17233A;\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
        "  classDef governance fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
    )


def _telemetry_contract_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Sim[Simulation Harness<br/>seeded robot events]:::proof --> Ingress[Telemetry ingress<br/>sim topic]:::core\n"
        "  Future[Future robot edge<br/>blocked in release one]:::edge -. planned .-> Ingress\n"
        "  Ingress --> Envelope[Canonical telemetry<br/>envelope]:::core\n"
        "  Envelope --> Identity[Robot identity<br/>capability lookup]:::core\n"
        "  Envelope --> Task[Task status<br/>and progress model]:::core\n"
        "  Task --> ReadModel[Console read<br/>model]:::ux\n"
        "  Identity --> ReadModel\n"
        "  Envelope --> Audit[Replayable audit<br/>fixture]:::proof\n"
        "  classDef edge fill:#FFF8E6,stroke:#F6D98B,color:#17233A;\n"
        "  classDef ux fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef core fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
    )


def _deployment_boundaries_mermaid() -> str:
    return (
        "flowchart TB\n"
        "  subgraph local[Local developer<br/>and CI lane]\n"
        "    CLI[Scenario runner<br/>CLI]:::proof\n"
        "    Tests[Browser and contract<br/>tests]:::proof\n"
        "  end\n"
        "  subgraph control[Control plane<br/>proposal target]\n"
        "    Console[Fleet console<br/>application]:::ux\n"
        "    Core[Coordination core<br/>contracts]:::core\n"
        "  end\n"
        "  subgraph edge[Future edge<br/>not release one]\n"
        "    Agent[Robot edge agent<br/>vendor adapters]:::edge\n"
        "    Hardware[Live robot<br/>hardware]:::blocked\n"
        "  end\n"
        "  CLI --> Core\n"
        "  Tests --> Console\n"
        "  Console --> Core\n"
        "  Agent -. planned integration .-> Core\n"
        "  Hardware -. blocked until HIL proof .-> Agent\n"
        "  Core --> Evidence[Release evidence<br/>simulation only]:::proof\n"
        "  classDef ux fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef core fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
        "  classDef edge fill:#FFF8E6,stroke:#F6D98B,color:#17233A;\n"
        "  classDef blocked fill:#FFF8E6,stroke:#F6D98B,color:#17233A;\n"
    )


def _observability_audit_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Operator[Operator action<br/>dispatch or override]:::ux --> EventLog[Operator event<br/>log]:::proof\n"
        "  Telemetry[Telemetry health<br/>stream]:::core --> Metrics[Health metrics<br/>and lost signal]:::core\n"
        "  Sim[Seeded replay<br/>artifact]:::proof --> Audit[Audit assertion<br/>bundle]:::proof\n"
        "  EventLog --> Audit\n"
        "  Metrics --> Audit\n"
        "  Audit --> Report[Release evidence<br/>normal degraded blocked]:::proof\n"
        "  Audit --> Review[Operator review<br/>before next wave]:::planning\n"
        "  classDef ux fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef core fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
        "  classDef planning fill:#FBFDFF,stroke:#D8E5F4,color:#17233A;\n"
    )


__all__ = ["apply_robot_swarm_logistics_profile", "is_robot_swarm_logistics_prompt"]
