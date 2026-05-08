"""Host-facing schema contract for greenfield proposal authoring."""

from __future__ import annotations

from typing import Any

from odylith.runtime.domain_intelligence import greenfield_programs

DEFAULT_GREENFIELD_RELEASE_SELECTOR = greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR

GREENFIELD_ENGINE_ACTIVATION_LAYERS: tuple[dict[str, str], ...] = (
    {
        "layer": "context_engine",
        "activation": "Resolve repo source posture, exact anchors, Registry owners, and narrowing before any write.",
    },
    {
        "layer": "execution_engine",
        "activation": "Carry the target component handshake, route readiness, and validation posture into execution planning.",
    },
    {
        "layer": "tribunal",
        "activation": "Adjudicate Radar, Registry, Atlas, waves, release targeting, and proof topology before source truth changes.",
    },
    {
        "layer": "intervention_engine",
        "activation": "Keep propose/apply host-agnostic and low latency while preserving visible readiness/status proof for host UX.",
    },
    {
        "layer": "governance",
        "activation": "Write only confirmed Radar, Registry, Atlas, Compass, release, assumption, risk, and validation records.",
    },
    {
        "layer": "subagent_orchestration",
        "activation": "Expose bounded delegation readiness without requiring greenfield proposal generation to spawn workers.",
    },
    {
        "layer": "discipline",
        "activation": "Keep the path local, zero-credit, provider-free by default, and tied to the Discipline validator.",
    },
    {
        "layer": "surface_dags",
        "activation": "Refresh owned generated surfaces once after accepted source truth reaches a coherent post-apply state.",
    },
    {
        "layer": "delivery",
        "activation": "Return concise text or machine-clean JSON with apply commands, recovery-safe errors, and no partial-success theater.",
    },
    {
        "layer": "analysis",
        "activation": "Require domain-proportional risks, proof gates, open questions, and correctness/security review posture.",
    },
    {
        "layer": "memory_substrate",
        "activation": "Record accepted proposal memory after confirmed writes so future sessions inherit the program context.",
    },
    {
        "layer": "topology",
        "activation": "Require mutual traceability across workstreams, planned components, dependencies, diagrams, and releases.",
    },
    {
        "layer": "taxonomies_fsms",
        "activation": "Use open-world classification plus explicit proposal, confirmation, release, wave, and apply state transitions.",
    },
    {
        "layer": "greenfield_domain_intelligence",
        "activation": "Let the host author domain content while Odylith owns normalization, validation, Tribunal, rollback, and apply.",
    },
    {
        "layer": "overall_ux",
        "activation": "Make the operator sequence clear: draft, review, confirm, apply, render, and recover without hand cleanup.",
    },
)


def build_proposal_contract() -> dict[str, Any]:
    return {
        "engine_activation_layers": list(GREENFIELD_ENGINE_ACTIVATION_LAYERS),
        "required_top_level_keys": [
            "schema_version",
            "mode",
            "intent",
            "observed_source",
            "assumptions",
            "open_questions",
            "risks",
            "security_compliance",
            "validation_strategy",
            "program",
            "release_plan",
            "backlog",
            "components",
            "diagrams",
        ],
        "evidence_rules": [
            "Use observed_source only for facts found in the repo.",
            "Use user_intent for facts stated or directly implied by the operator prompt.",
            "Use odylith_assumption for useful architecture choices that need confirmation.",
            "Never mark source-backed ownership or scientific/math correctness from prompt text alone.",
        ],
        "minimum_content": {
            "backlog": (
                "an explicit parent/umbrella program workstream plus child workstreams when the project has multiple meaningful boundaries; "
                "every child should carry first-slice, validation, component_focus, and related_diagram_slugs "
                "or enough specific language for Odylith to infer the topology; every row must carry structured "
                "domain_intelligence covering intent, ontology, state, operators, constraints, source of truth, "
                "evidence, assumptions, topology, invariants, risks, validation, artifacts, authority, memory, "
                "metrics, change rules, conflict rules, and reusable priors"
            ),
            "components": (
                "candidate Registry components with component_id, label, intended_path, responsibility, "
                "boundary/interfaces/dependencies where known, evidence_tier, status, and qualification"
            ),
            "diagrams": (
                "a purposeful Atlas view suite such as system context, first-slice sequence, component ownership, "
                "domain state/data contract, validation/release topology, operational risk, or a better "
                "domain-specific set; each diagram must name related components and workstream/backlog focus, "
                "and flowcharts must use subtle diagram-internal colors plus wrapped labels"
            ),
            "program": "wave plan with goals, validation gates, component focus, and evidence tier",
            "implementation_runway": (
                "post-apply handoff that names the first child workstream, first wave, release target, proof gates, "
                "repo-native validation expectations, and dashboard surfaces to inspect before advancing waves"
            ),
            "release_plan": (
                "provisional release selector, first-target workstreams, stages, milestones, and promotion criteria; "
                "default selector and label are exactly 0.0.1 unless the operator supplies a different release target"
            ),
            "security_compliance": (
                "domain-relevant security, privacy, compliance, abuse, data-retention, accessibility, and "
                "operational risk posture; keep it concrete and proportional to the project"
            ),
            "tribunal": (
                "apply runs a deterministic proposal Tribunal before writes; proposals fail if Radar, Registry, "
                "Atlas, program waves, or release targeting do not form a coherent topology"
            ),
        },
        "quality_bar": [
            "Reason from the actual prompt, not from a fixed in-code domain list.",
            "Prefer fewer high-quality boundaries over many generic buckets.",
            (
                "Choose diagram types because they clarify the project, and for greenfield architecture favor a "
                "multi-view suite that covers topology, sequence, ownership, state/data, validation, and operational risk."
            ),
            "Each diagram must include host-authored mermaid_source; Odylith validates it but does not invent topology.",
            (
                "For flowchart mermaid_source, use classDef/style colors inside the diagram for semantic grouping "
                "and <br/> to wrap long labels so text stays readable. Use subgraph lanes only where they clarify "
                "the topology; never rely on viewer background treatment."
            ),
            "For sequenceDiagram mermaid_source, keep message text parser-safe: use words instead of semicolons in arrow labels.",
            (
                "Child workstreams must not be title-only tickets; include concrete first-slice proof, impacted "
                "candidate components, topology/dependency hints, and validation gates."
            ),
            (
                "Greenfield Radar workstreams must be domain-intelligent control surfaces, not task labels: "
                "capture domain vocabulary, allowed operations, state transitions, constraints, source-of-truth "
                "hierarchy, evidence grammar, risks, validation obligations, execution memory, change rules, "
                "conflict rules, and transfer priors with project-specific terms."
            ),
            (
                "Registry components must read like planned ownership specs, not labels; include boundary, "
                "responsibility, interface, dependency, and proof expectations where the prompt supports them."
            ),
            "Atlas diagrams and Radar workstreams must be mutually traceable through related workstream/component hints.",
            "For science and math, propose validation obligations and review gates; do not invent claims or results.",
            (
                "For consumer apps, account for security, privacy, abuse, accessibility, data retention, "
                "auditability, and compliance risks in proportion to the data and domain."
            ),
            (
                "For regulated or safety-sensitive domains, name the compliance or review posture explicitly "
                "instead of hiding it in generic risk language."
            ),
            "For simple projects, keep the plan small; for complex projects, form waves and release gates.",
            (
                "Default the first greenfield release target to exactly 0.0.1; do not prefix it with the project "
                "name, wave name, or any other words."
            ),
            (
                "Name the first release target workstreams from the first wave so Compass can show a concrete "
                "release lane without pretending every child belongs to the first release."
            ),
            (
                "Make the proposal easy to operate: name the program, waves, release selector, first target "
                "workstreams, impacted components, diagrams, and proof gates in plain language."
            ),
            (
                "Make the post-apply coding sequence explicit: which child workstream starts first, what proof "
                "must pass before the next wave, and which surfaces the operator should open to verify the program."
            ),
            (
                "Candidate Registry specs must carry an implementation runway: first child workstream, wave, release, "
                "first coding slice, definition of done, and verification commands. The umbrella parent is context, "
                "not the first coding anchor."
            ),
            (
                "Never let the first child workstream masquerade as the program parent; use WS-00 or a clearly "
                "titled umbrella such as `Govern <Project>` for the parent and WS-01+ for implementation children."
            ),
            (
                "Carry the engine activation layers: Context, Execution, Tribunal, Intervention, Governance, "
                "Subagent Orchestration, Discipline, Surface DAGs, Delivery, Analysis, Memory, Topology, "
                "Taxonomies/FSMs, Greenfield Domain Intelligence, and Overall UX."
            ),
            (
                "Expect a Tribunal gate: child workstreams need component and diagram references, components need "
                "boundary/interface/dependency/proof expectations, and diagrams need workstream plus component traceability."
            ),
        ],
    }


def build_proposal_template(*, intent_title: str, project_slug: str, source_posture: str) -> dict[str, Any]:
    component_id = f"{project_slug}-core"
    diagram_slug = f"{project_slug}-system-context"
    return {
        "schema_version": "odylith.greenfield.host_reasoned.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "intent": {
            "title": intent_title,
            "project_slug": project_slug,
            "summary": "Replace with the host-reasoned project summary.",
        },
        "observed_source": {
            "evidence_tier": "observed_source",
            "summary": f"Repo source posture: {source_posture}.",
        },
        "assumptions": [
            {
                "id": "A1",
                "evidence_tier": "odylith_assumption",
                "statement": "Replace with a first-slice assumption.",
            },
        ],
        "open_questions": [
            {
                "id": "Q1",
                "evidence_tier": "user_intent",
                "question": "Replace with a question that changes the first slice.",
            },
        ],
        "risks": [
            {
                "id": "R1",
                "evidence_tier": "odylith_assumption",
                "statement": "Replace with a concrete risk.",
                "mitigation": "Replace with the mitigation.",
            },
        ],
        "security_compliance": {
            "domain": "Replace with the domain and data sensitivity assessment.",
            "security": "Replace with auth, access-control, abuse, secrets, and AI-agent guardrail posture.",
            "policy": "Replace with privacy, retention, accessibility, regulatory, or safety posture.",
        },
        "validation_strategy": [
            {
                "id": "V1",
                "evidence_tier": "odylith_assumption",
                "scope": "first_slice",
                "obligation": "Replace with focused behavior proof.",
            },
        ],
        "program": {
            "name": intent_title,
            "waves": [
                {
                    "wave_id": "W1",
                    "label": "First release slice",
                    "goal": "Replace with the first release goal.",
                    "validation_gate": "Replace with the first release gate.",
                    "workstreams": ["WS-01"],
                },
            ],
        },
        "release_plan": {
            "selector": DEFAULT_GREENFIELD_RELEASE_SELECTOR,
            "label": DEFAULT_GREENFIELD_RELEASE_SELECTOR,
            "provisional_release_id": f"release-{project_slug}-0-0-1",
            "target_workstreams": ["WS-01"],
            "release_stages": [
                {
                    "release": DEFAULT_GREENFIELD_RELEASE_SELECTOR,
                    "label": "First release slice",
                    "exit_criteria": "Replace with promotion criteria.",
                },
            ],
            "promotion_criteria": ["Replace with the release promotion proof."],
        },
        "backlog": [
            {
                "id": "WS-00",
                "title": f"{intent_title} program",
                "problem": "Replace with the grounded problem.",
                "customer": "Replace with the target customer.",
                "opportunity": "Replace with the opportunity.",
                "product_view": "Replace with the product view.",
                "recommended_first_slice": "Replace with the first slice.",
                "success_metrics": [
                    "Replace with a measurable success metric.",
                    "Replace with a second measurable success metric.",
                ],
                "evidence_tier": "user_intent",
            },
            {
                "id": "WS-01",
                "title": "First slice boundary",
                "problem": "Replace with the child workstream problem.",
                "customer": "Replace with the target customer.",
                "opportunity": "Replace with the child opportunity.",
                "product_view": "Replace with the child product view.",
                "recommended_first_slice": "Replace with the child first-slice proof.",
                "success_metrics": [
                    "Replace with a measurable child metric.",
                    "Replace with a second measurable child metric.",
                ],
                "component_focus": [component_id],
                "related_diagram_slugs": [diagram_slug],
                "dependencies": ["Replace with a dependency expectation."],
                "interfaces": ["Replace with an interface expectation."],
                "validation": ["Replace with validation proof."],
                "evidence_tier": "user_intent",
            },
        ],
        "components": [
            {
                "component_id": component_id,
                "label": "Core Boundary",
                "kind": "service",
                "intended_path": f"src/{component_id}",
                "status": "planned",
                "qualification": "candidate",
                "responsibility": "Replace with responsibility, boundary, and ownership summary.",
                "boundary": "Replace with what this component owns and excludes.",
                "interfaces": ["Replace with planned interfaces."],
                "dependencies": ["Replace with dependencies."],
                "validation": ["Replace with proof expectations."],
                "evidence_tier": "user_intent",
            },
        ],
        "diagrams": [
            {
                "slug": diagram_slug,
                "title": f"{intent_title} system context",
                "kind": "flowchart",
                "summary": "Replace with what the diagram clarifies.",
                "link_state": "atlas_first_draft",
                "components": [{"name": component_id, "description": "Replace with the component role."}],
                "related_workstreams": ["WS-00", "WS-01"],
                "evidence_tier": "user_intent",
                "mermaid_source": (
                    "flowchart LR\n"
                    "  User[User] --> Core[Core<br/>boundary]\n"
                    "  classDef actor fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
                    "  classDef service fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
                    "  class User actor;\n"
                    "  class Core service;"
                ),
            },
        ],
    }


__all__ = [
    "GREENFIELD_ENGINE_ACTIVATION_LAYERS",
    "build_proposal_contract",
    "build_proposal_template",
]
