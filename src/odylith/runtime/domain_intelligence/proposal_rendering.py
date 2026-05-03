"""Operator-facing rendering for greenfield proposal payloads."""

from __future__ import annotations

from typing import Any, Mapping


def shell_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def build_apply_commands(proposal: Mapping[str, Any]) -> list[str]:
    backlog = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    components = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    diagrams = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    release_selector = str(release_plan.get("selector", "")).strip()
    release_arg = f" --release {shell_quote(release_selector)}" if release_selector else ""
    commands = [
        "odylith greenfield propose --repo-root . --prompt "
        + shell_quote(str(proposal.get("intent", {}).get("prompt", "new project")))
        + " --format json > odylith-greenfield-proposal.json",
        "odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm"
        + release_arg,
    ]
    if backlog:
        commands.append("# apply will create Radar backlog records after validating grounded proposal fields")
    if components:
        commands.append("# apply will register planned candidate Registry components with user_intent evidence")
    if diagrams:
        commands.append("# apply will scaffold draft Atlas topology with atlas_first_draft link state")
    return commands


def format_proposal_text(proposal: Mapping[str, Any]) -> str:
    """Render a concise operator-facing proposal."""

    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "Greenfield Project")).strip()
    label = str(intent.get("archetype_label", "General Project")).strip()
    confidence = str(intent.get("confidence", "")).strip()
    source = proposal.get("observed_source", {}) if isinstance(proposal.get("observed_source"), Mapping) else {}
    source_posture = str(source.get("source_posture", "unknown")).strip()
    lines = [
        f"Odylith greenfield proposal: {title}",
        f"- archetype: {label} ({confidence} confidence)",
        f"- source evidence: {source_posture}; writes stay confirmation-gated",
        f"- provider_calls: {proposal.get('provider_calls', 0)}",
    ]
    classification = proposal.get("classification", {}) if isinstance(proposal.get("classification"), Mapping) else {}
    alternatives = classification.get("alternatives", []) if isinstance(classification.get("alternatives"), list) else []
    if alternatives:
        rendered = ", ".join(
            f"{row.get('archetype_label')} ({row.get('confidence')})"
            for row in alternatives
            if isinstance(row, Mapping) and row.get("archetype_label")
        )
        if rendered:
            lines.append(f"- alternate fits: {rendered}")
    ux = proposal.get("greenfield_ux", {}) if isinstance(proposal.get("greenfield_ux"), Mapping) else {}
    if ux:
        lines.extend(
            [
                "",
                "Greenfield UX",
                f"- mode: {ux.get('mode', 'consumer_greenfield_proposal')}",
                f"- guardrail: {ux.get('write_guardrail', 'confirm before governed writes')}",
                f"- next: {ux.get('next_best_action', 'confirm or revise the proposed first wave')}",
            ]
        )
    lines.extend(["", "Backlog proposal"])
    for row in proposal.get("backlog", []):
        if isinstance(row, Mapping):
            lines.append(f"- {row.get('title')}: {row.get('recommended_first_slice')}")
    program = proposal.get("program", {}) if isinstance(proposal.get("program"), Mapping) else {}
    blueprint = program.get("blueprint", {}) if isinstance(program.get("blueprint"), Mapping) else {}
    if blueprint:
        lines.extend(
            [
                "",
                "Program formation",
                f"- type: {blueprint.get('program_type')}",
                f"- parent: {blueprint.get('parent_workstream')}",
                f"- wave policy: {blueprint.get('wave_to_workstream_policy')}",
                f"- release strategy: {blueprint.get('release_strategy')}",
            ]
        )
    lines.extend(["", "Program waves"])
    for row in program.get("waves", []) if isinstance(program.get("waves"), list) else []:
        if isinstance(row, Mapping):
            lines.append(f"- Wave {row.get('wave')}: {row.get('label')} - {row.get('goal')} Proof: {row.get('validation')}")
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    lines.extend(["", "Release plan"])
    lines.append(
        f"- target: {release_plan.get('selector', 'next')} "
        f"({release_plan.get('label', 'First governed release')}; {release_plan.get('provisional_release_id', 'release-greenfield-first')})"
    )
    lines.append(f"- strategy: {release_plan.get('strategy', 'confirm before release targeting')}")
    for row in release_plan.get("release_stages", []) if isinstance(release_plan.get("release_stages"), list) else []:
        if isinstance(row, Mapping):
            lines.append(f"- {row.get('stage')}: {row.get('label')} gate - {row.get('release_gate')}")
    for row in release_plan.get("milestones", []) if isinstance(release_plan.get("milestones"), list) else []:
        if isinstance(row, Mapping):
            lines.append(f"- {row.get('name')}: {row.get('exit_criteria')}")
    lines.extend(["", "Planned Registry components"])
    for row in proposal.get("components", []):
        if isinstance(row, Mapping):
            lines.append(
                f"- {row.get('component_id')}: {row.get('label')} -> {row.get('intended_path')} "
                f"({row.get('evidence_tier')})"
            )
    lines.extend(["", "Draft Atlas diagrams"])
    for row in proposal.get("diagrams", []):
        if isinstance(row, Mapping):
            lines.append(f"- {row.get('slug')}: {row.get('title')} ({row.get('link_state')})")
    lines.extend(["", "Validation focus"])
    for item in proposal.get("validation_strategy", []):
        lines.append(f"- {item}")
    lines.extend(["", "Assumptions"])
    for item in proposal.get("assumptions", []):
        lines.append(f"- {item}")
    lines.extend(["", "Open questions"])
    for item in proposal.get("open_questions", []):
        lines.append(f"- {item}")
    lines.extend(["", "Apply"])
    lines.append("No files changed. To write this proposal, review the assumptions and run:")
    lines.append("  " + str(proposal.get("apply_commands", [""])[1]))
    return "\n".join(lines).rstrip() + "\n"
