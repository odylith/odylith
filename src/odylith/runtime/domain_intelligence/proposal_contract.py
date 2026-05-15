"""Schema contract notes for confirmed greenfield proposal construction."""

from __future__ import annotations

from typing import Any

from odylith.runtime.domain_intelligence import greenfield_programs

DEFAULT_GREENFIELD_RELEASE_SELECTOR = greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR

GREENFIELD_ENGINE_ACTIVATION_LAYERS: tuple[dict[str, str], ...] = (
    {
        "layer": "context_engine",
        "activation": "Resolve repo source posture, exact anchors, component owners, and narrowing before any write.",
    },
    {
        "layer": "execution_engine",
        "activation": "Carry the target component handshake, route readiness, and validation posture into execution planning.",
    },
    {
        "layer": "tribunal",
        "activation": "Adjudicate workstreams, component specs, architecture diagrams, waves, release targeting, and proof topology before source truth changes.",
    },
    {
        "layer": "intervention_engine",
        "activation": "Keep propose/apply host-agnostic and low latency while preserving visible readiness/status proof for host UX.",
    },
    {
        "layer": "governance",
        "activation": "Write only confirmed workstream, component, architecture, progress, release, assumption, risk, and validation records.",
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
        "activation": "Let the host narrate product intent while Odylith owns confirmed proposal construction, normalization, validation, Tribunal, rollback, and apply.",
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
            "project_brief",
            "project_intelligence",
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
        "post_confirmation_handoff": {
            "complete_authoring_surface": True,
            "intent_confirmation_authorizes_apply_attempt": True,
            "contract_use": [
                "Use greenfield create --confirm as the normal post-confirmation path.",
                "Use --confirm-intent --format json only when an explicit review artifact is requested.",
                "Do not inspect Odylith source files, Python modules, local examples, or generated runtime files to discover schema fields.",
            ],
            "forbidden_host_steps": [
                "Do not search src/odylith, .odylith, odylith/skills, or installed bundle files for greenfield schema after intent confirmation.",
                "Do not create a proposal by copying local examples or template fixtures.",
                "Do not ask the operator to inspect proposal JSON as the normal approval step.",
                "Do not write governed records unless confirmed create/apply passes validation and Tribunal.",
            ],
            "allowed_host_steps": [
                "Run greenfield create --confirm from the confirmed product intent and observed source posture.",
                "Keep product story, actors, systems, workstreams, components, diagrams, risks, proof, and release gates project-specific.",
                "Let Odylith build the apply-ready proposal; the create/apply command is the validation and Tribunal gate.",
                "Surface only the human-readable created-record summary or the validation/Tribunal issues.",
            ],
            "canonical_files": [
                {
                    "path": "odylith-greenfield-proposal.json",
                    "purpose": "optional exported apply-ready review artifact when explicitly requested",
                    "governed_record": False,
                }
            ],
            "canonical_commands": [
                "odylith greenfield create --repo-root . --prompt \"<confirmed request>\" --confirm --release 0.0.1",
                "odylith greenfield propose --repo-root . --prompt \"<confirmed request>\" --confirm-intent --format json > odylith-greenfield-proposal.json",
                "odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm --release 0.0.1",
            ],
            "failure_policy": [
                "If validation or Tribunal rejects the proposal, do not write records; summarize the blocking issues in product language.",
                "If the operator explicitly asks for a review artifact, export the proposal JSON; otherwise keep it internal.",
            ],
        },
        "minimum_content": {
            "backlog": (
                "an explicit parent/umbrella program workstream plus child workstreams when the project has multiple meaningful boundaries; "
                "every child should carry first-slice, validation, component_focus, and related_diagram_slugs "
                "or enough specific language for Odylith to infer the topology; every row must carry structured "
                "domain_intelligence covering intent, scope, ontology, state, operators, constraints, source of truth, "
                "evidence, assumptions, topology, invariants, risks, validation, artifacts, authority, owners, memory, "
                "metrics, change rules, invalidation rules, conflict rules, and reusable priors"
            ),
            "components": (
                "candidate component specs with component_id, label, intended_path, responsibility, "
                "boundary/interfaces/dependencies where known, evidence_tier, status, and qualification"
            ),
            "diagrams": (
                "a purposeful architecture view suite such as system context, first-slice sequence, component ownership, "
                "domain state/data contract, validation/release topology, operational risk, or a better "
                "domain-specific set; each diagram must name related components and workstream/backlog focus, "
                "and flowcharts must use subtle diagram-internal colors plus wrapped labels"
            ),
            "program": "wave plan with goals, validation gates, component focus, and evidence tier",
            "project_brief": (
                "a project-first blueprint with customization options, pre-coding checkpoints, coding readiness gates, "
                "and host-independent commands; it must make clear that greenfield apply accepts project direction before "
                "the first source-backed implementation plan starts"
            ),
            "project_intelligence": (
                "the deep project object that captures intent, scope, ontology, state, allowed operators, constraints, "
                "truth map, evidence grammar, decisions, assumptions, topology, invariants, risks, validation obligations, "
                "artifacts, owners, execution memory, metrics, change rules, invalidation rules, conflict rules, and transfer priors before coding"
            ),
            "implementation_runway": (
                "post-apply handoff that names the project parent, first wave, release target, direction choices, "
                "coding-readiness gates, eventual first child workstream, proof gates, repo-native validation "
                "expectations, and dashboard surfaces to inspect before coding or advancing waves"
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
                "apply runs a deterministic proposal Tribunal before writes; proposals fail if workstreams, components, "
                "diagrams, program waves, or release targeting do not form a coherent topology"
            ),
        },
        "quality_bar": [
            "Reason from the actual prompt, not from a fixed in-code domain list.",
            "Prefer fewer high-quality boundaries over many generic buckets.",
            (
                "Choose diagram types because they clarify the project, and for greenfield architecture favor a "
                "multi-view suite that covers topology, sequence, ownership, state/data, validation, and operational risk."
            ),
                "Each diagram must include proposal-supplied mermaid_source; Odylith validates it but does not invent topology.",
            (
                "For flowchart mermaid_source, use the Atlas semantic classDef/style color language for node state "
                "and restrained neutral containers, plus <br/> to wrap long labels so text stays readable. Use "
                "subgraph lanes only where they clarify the topology; never rely on viewer background treatment."
            ),
            "For sequenceDiagram mermaid_source, keep message text parser-safe: use words instead of semicolons in arrow labels.",
            (
                "Child workstreams must not be title-only tickets; include concrete first-slice proof, impacted "
                "candidate components, topology/dependency hints, and validation gates."
            ),
            (
                "Greenfield workstreams must be domain-intelligent control surfaces, not task labels: "
                "capture domain vocabulary, allowed operations, state transitions, constraints, source-of-truth "
                "hierarchy, evidence grammar, risks, validation obligations, owners, execution memory, change rules, invalidation rules, "
                "conflict rules, and transfer priors with project-specific terms."
            ),
            (
                "Component specs must read like planned ownership specs, not labels; include boundary, "
                "responsibility, interface, dependency, and proof expectations where the prompt supports them. "
                "Do not copy project-level risk, compliance, or product narrative into every component spec; "
                "each component dossier must stay scoped to that component's own boundary, collaborators, failure modes, and proof."
            ),
            "Architecture diagrams and workstreams must be mutually traceable through related workstream/component hints.",
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
                "Name the first release target workstreams from the first wave so the progress view can show "
                "a concrete release lane without pretending every child belongs to the first release."
            ),
            (
                "Greenfield UX is project-first: do not push the operator straight into coding. The proposal must "
                "offer direction choices, customization paths, architecture review checkpoints, and readiness gates "
                "that work the same from CLI, Codex, and Claude Code."
            ),
            (
                "Make the proposal easy to operate: name the program, waves, release selector, first target "
                "workstreams, impacted components, diagrams, and proof gates in plain language."
            ),
            (
                "Make the post-apply sequence explicit: which project brief to review first, which choices can be "
                "customized, when the eventual first child workstream may start, what proof must pass before the next "
                "wave, and which surfaces the operator should open to verify the program."
            ),
            (
                "Candidate component specs must carry an implementation runway: first child workstream, wave, release, "
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


__all__ = [
    "GREENFIELD_ENGINE_ACTIVATION_LAYERS",
    "build_proposal_contract",
]
