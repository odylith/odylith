"""Prompt-visible robot swarm logistics profile for greenfield scaffolds."""

from __future__ import annotations

from typing import Any


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
    _apply_backlog_rows(proposal["backlog"], title=title)
    _apply_components(proposal["components"])
    _apply_diagrams(
        proposal["diagrams"],
        title=title,
        experience_component=experience_component,
        domain_component=domain_component,
        validation_component=validation_component,
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
        "Refresh Compass, Radar, Registry, and Atlas after apply and after the first source-backed implementation slice.",
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
            "Promote only after the simulation-backed dispatch path, robot domain contracts, Atlas render, "
            "Registry specs, Radar, and Compass all agree."
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
            "Registry, Atlas, Radar, and Compass refresh cleanly and show the same robot swarm first-wave lane.",
            "No live hardware, production credentials, or safety claim is made before the hardening wave.",
        ],
    }


def _apply_backlog_rows(rows: list[dict[str, Any]], *, title: str) -> None:
    rows[1].update(_dispatch_backlog_row(title))
    rows[2].update(_contract_backlog_row(title))
    rows[3].update(_simulation_backlog_row(title))


def _dispatch_backlog_row(title: str) -> dict[str, Any]:
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
            "Every operator-visible state links back to the first Radar workstream and Registry component.",
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
        "domain_risk": "A misleading console can hide robot state, assignment ambiguity, or unsafe operator assumptions.",
        "security_posture": "Operator commands are role-gated, override attempts are confirmation-gated, and fixtures contain no production credentials.",
    }


def _contract_backlog_row(title: str) -> dict[str, Any]:
    return {
        "title": "Define robot task, telemetry, and coordination contract",
        "problem": f"{title} cannot safely coordinate robots unless identity, capabilities, task state, telemetry, and reservation semantics are explicit.",
        "customer": "Coordination, simulation, telemetry, safety, and operator-console implementation owners.",
        "opportunity": "Define the canonical robot logistics contract before scheduler, simulator, or vendor SDK details harden into accidental architecture.",
        "product_view": "A domain contract owns robot identity, capability tags, logistics task state, telemetry health, and simple reservation outcomes.",
        "recommended_first_slice": "Implement the robot task/telemetry contract and tests for valid assignment, invalid capability, lost telemetry, and idempotent retry.",
        "success_metrics": [
            "Contract tests prove valid assignment, invalid capability rejection, lost telemetry, and idempotent retry behavior.",
            "Registry records the domain component dependencies, interfaces, and verification commands.",
            "Atlas diagrams show how console, domain core, and simulator exchange task and telemetry state.",
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
        "domain_risk": "Loose robot state contracts can double-assign work, hide lost telemetry, or couple core logic to one vendor.",
        "security_posture": "Per-robot identity and command replay protection are planned before any live transport is introduced.",
    }


def _simulation_backlog_row(title: str) -> dict[str, Any]:
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
            "Compass/Radar/Registry/Atlas refresh after proof and show the same first release lane.",
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
        "domain_risk": "Non-deterministic simulation hides coordination regressions and weakens safety review evidence.",
        "security_posture": "Simulator fixtures contain no production credentials and cannot contact live robot transports by default.",
    }


def _apply_components(components: list[dict[str, Any]]) -> None:
    components[0].update(
        {
            "label": "Fleet Operations Console",
            "responsibility": "Own the operator dispatch/read workflow, fleet state presentation, degraded telemetry states, and confirmation-gated overrides.",
            "boundary": "Owns the human-visible dispatch and fleet-status experience; excludes robot coordination policy, simulator runtime, and vendor SDK adapters.",
            "dependencies": ["Depends on the coordination core contract and simulation harness for robot/task state fixtures."],
            "interfaces": ["Dispatch route or command, fleet-state read model, override confirmation event, degraded telemetry view contract."],
            "validation": ["Browser or UI proof for normal dispatch, empty fleet, degraded telemetry, rejected override, and audit-link visibility."],
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
        }
    )


def _apply_diagrams(
    diagrams: list[dict[str, Any]],
    *,
    title: str,
    experience_component: str,
    domain_component: str,
    validation_component: str,
) -> None:
    diagrams[0].update(
        {
            "title": f"{title} Simulation-First Atlas Overview",
            "summary": "Topology connecting operator console, robot coordination core, deterministic simulation harness, audit proof, and Odylith surfaces.",
            "components": [
                {"name": experience_component, "description": "Fleet operations console for dispatch, fleet state, and safe override UX."},
                {"name": domain_component, "description": "Robot task, telemetry, capability, and reservation contract owner."},
                {"name": validation_component, "description": "Deterministic simulator and safety smoke proof owner."},
            ],
            "mermaid_source": _overview_mermaid(),
        }
    )
    diagrams[1].update(
        {
            "title": f"{title} Dispatch And Telemetry Flow",
            "summary": "Sequence for one simulated logistics task moving from operator dispatch through coordination contract, simulator telemetry, audit, and surface refresh.",
            "components": [
                {"name": experience_component, "description": "Starts dispatch and renders robot/task progress plus fallback states."},
                {"name": domain_component, "description": "Validates assignment, telemetry health, and reservation semantics."},
                {"name": validation_component, "description": "Runs simulation replay and captures smoke/audit evidence."},
            ],
            "mermaid_source": _slice_mermaid(),
        }
    )


def _overview_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Operator[Operator<br/>dispatch]:::actor --> Console[Fleet Operations<br/>Console]:::ux\n"
        "  Console --> Core[Robot Coordination<br/>Core]:::core\n"
        "  Core --> Sim[Simulation And<br/>Safety Harness]:::proof\n"
        "  Sim --> Telemetry[Telemetry<br/>Replay]:::core\n"
        "  Telemetry --> Console\n"
        "  Sim --> Audit[(Audit<br/>Evidence)]:::proof\n"
        "  Audit --> Surfaces[Odylith<br/>Surfaces]:::governance\n"
        "  Surfaces --> Radar[Radar Registry<br/>Atlas Compass]:::governance\n"
        "  classDef actor fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
        "  classDef ux fill:#fff7df,stroke:#d7a93d,color:#52390a;\n"
        "  classDef core fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef governance fill:#f1f5f9,stroke:#94a3b8,color:#1f2937;\n"
    )


def _slice_mermaid() -> str:
    return (
        "sequenceDiagram\n"
        "  participant Operator as Operator\n"
        "  participant Console as Fleet Operations Console\n"
        "  participant Core as Robot Coordination Core\n"
        "  participant Sim as Simulation Harness\n"
        "  participant Audit as Audit Evidence\n"
        "  participant Surfaces as Odylith Surfaces\n"
        "  Operator->>Console: dispatch one logistics task\n"
        "  Console->>Core: assign task request\n"
        "  Core-->>Console: robot assignment and task state\n"
        "  Core->>Sim: run seeded robot scenario\n"
        "  Sim-->>Core: telemetry and completion event\n"
        "  Sim->>Audit: record assignment, telemetry loss, override checks\n"
        "  Audit->>Surfaces: refresh proof references\n"
        "  Surfaces-->>Operator: show release lane and first workstream\n"
    )


__all__ = ["apply_robot_swarm_logistics_profile", "is_robot_swarm_logistics_prompt"]
