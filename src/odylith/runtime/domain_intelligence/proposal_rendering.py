"""Operator-facing rendering for greenfield proposal payloads."""

from __future__ import annotations

from typing import Any, Mapping

DEFAULT_GREENFIELD_RELEASE_SELECTOR = "0.0.1"


def shell_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def _release_selector(release_plan: Mapping[str, Any]) -> str:
    selector = str(release_plan.get("selector", "")).strip()
    return selector or DEFAULT_GREENFIELD_RELEASE_SELECTOR


def build_apply_commands(proposal: Mapping[str, Any]) -> list[str]:
    backlog = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    components = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    diagrams = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    release_selector = _release_selector(release_plan)
    release_arg = f" --release {shell_quote(release_selector)}"
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
    if proposal.get("mode") == "host_reasoned_proposal_request":
        source = proposal.get("observed_source", {}) if isinstance(proposal.get("observed_source"), Mapping) else {}
        ux = proposal.get("greenfield_ux", {}) if isinstance(proposal.get("greenfield_ux"), Mapping) else {}
        contract = proposal.get("reasoning_contract", {}) if isinstance(proposal.get("reasoning_contract"), Mapping) else {}
        lines = [
            f"Odylith greenfield reasoning brief: {title}",
            f"- source evidence: {source.get('source_posture', 'unknown')}; writes stay confirmation-gated",
            "- proposal authorship: host model reasoning required",
            f"- provider_calls_by_odylith_cli: {proposal.get('provider_calls', 0)}",
            f"- default_release_selector: {DEFAULT_GREENFIELD_RELEASE_SELECTOR} unless the operator supplies another target",
            "",
            "Host reasoning task",
            f"- {proposal.get('host_instruction', 'Draft a concrete proposal from prompt and repo evidence.')}",
            f"- next: {ux.get('next_best_action', 'draft the proposal, then ask for confirmation before writes')}",
            "",
            "Required proposal sections",
        ]
        for key in contract.get("required_top_level_keys", []) if isinstance(contract.get("required_top_level_keys"), list) else []:
            lines.append(f"- {key}")
        lines.extend(["", "Evidence rules"])
        for rule in contract.get("evidence_rules", []) if isinstance(contract.get("evidence_rules"), list) else []:
            lines.append(f"- {rule}")
        lines.extend(["", "Quality bar"])
        for rule in contract.get("quality_bar", []) if isinstance(contract.get("quality_bar"), list) else []:
            lines.append(f"- {rule}")
        lines.extend(["", "Apply"])
        lines.append("No files changed. After the operator accepts a host-reasoned proposal, run:")
        commands = proposal.get("apply_commands", [])
        if isinstance(commands, list) and len(commands) > 1:
            lines.append("  " + str(commands[1]))
        return "\n".join(lines).rstrip() + "\n"

    label = str(intent.get("fit_label", "General Project")).strip()
    confidence = str(intent.get("confidence", "")).strip()
    source = proposal.get("observed_source", {}) if isinstance(proposal.get("observed_source"), Mapping) else {}
    source_posture = str(source.get("source_posture", "unknown")).strip()
    lines = [
        f"Odylith greenfield proposal: {title}",
        f"- fit: {label} ({confidence} confidence)",
        f"- source evidence: {source_posture}; writes stay confirmation-gated",
        f"- provider_calls: {proposal.get('provider_calls', 0)}",
    ]
    classification = proposal.get("classification", {}) if isinstance(proposal.get("classification"), Mapping) else {}
    alternatives = classification.get("alternatives", []) if isinstance(classification.get("alternatives"), list) else []
    if alternatives:
        rendered = ", ".join(
            f"{row.get('fit_label')} ({row.get('confidence')})"
            for row in alternatives
            if isinstance(row, Mapping) and row.get("fit_label")
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
    release_selector = _release_selector(release_plan)
    lines.extend(["", "Release plan"])
    lines.append(
        f"- target: {release_selector} "
        f"({release_plan.get('label', 'First governed release')}; {release_plan.get('provisional_release_id', 'release-greenfield-first')})"
    )
    if not str(release_plan.get("selector", "")).strip():
        lines.append("- default: greenfield proposals start at 0.0.1 when no release target is provided")
    target_refs = release_plan.get("target_workstreams") or release_plan.get("target_workstream_titles")
    if target_refs:
        if isinstance(target_refs, list):
            rendered_targets = ", ".join(str(item).strip() for item in target_refs if str(item).strip())
        else:
            rendered_targets = str(target_refs).strip()
        if rendered_targets:
            lines.append(f"- first target workstreams: {rendered_targets}")
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
