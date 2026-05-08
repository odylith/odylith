"""Operator-facing rendering for greenfield proposal payloads."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.domain_intelligence import greenfield_programs

DEFAULT_GREENFIELD_RELEASE_SELECTOR = greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR


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
        commands.append("# apply will create Radar backlog records after validation and Tribunal review")
    if components:
        commands.append("# apply will register planned candidate Registry components with user_intent evidence")
    if diagrams:
        commands.append("# apply will scaffold draft Atlas topology with atlas_first_draft link state")
    commands.append("# apply will refresh Radar, Registry, Atlas, and Compass after all artifacts are written")
    return commands


def format_proposal_text(proposal: Mapping[str, Any]) -> str:
    """Render a concise operator-facing proposal from the apply-ready object."""

    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "Greenfield Project")).strip()
    if proposal.get("mode") == "host_reasoned_proposal_request":
        canonical = proposal.get("canonical_proposal")
        if isinstance(canonical, Mapping):
            return _format_apply_ready_proposal_text(canonical, request_context=proposal)
        source = proposal.get("observed_source", {}) if isinstance(proposal.get("observed_source"), Mapping) else {}
        ux = proposal.get("greenfield_ux", {}) if isinstance(proposal.get("greenfield_ux"), Mapping) else {}
        contract = proposal.get("reasoning_contract", {}) if isinstance(proposal.get("reasoning_contract"), Mapping) else {}
        lines = [
            f"Odylith greenfield reasoning brief: {title}",
            f"- source evidence: {source.get('source_posture', 'unknown')}; writes stay confirmation-gated",
            "- proposal authorship: active host reasoning required",
            f"- provider_calls_by_odylith_cli: {proposal.get('provider_calls', 0)}",
            f"- default_release_selector: {DEFAULT_GREENFIELD_RELEASE_SELECTOR} unless the operator supplies another target",
            f"- canonical_proposal_gate: {proposal.get('canonical_proposal_gate', {}).get('status', 'unknown') if isinstance(proposal.get('canonical_proposal_gate'), Mapping) else 'unknown'}",
            "- apply gate: deterministic proposal Tribunal before writes",
            "- visibility: Radar, Registry, Atlas, and Compass refresh after accepted artifacts are written",
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
        template = proposal.get("proposal_template", {}) if isinstance(proposal.get("proposal_template"), Mapping) else {}
        release_plan = template.get("release_plan", {}) if isinstance(template.get("release_plan"), Mapping) else {}
        lines.extend(
            [
                "",
                "Canonical apply JSON shape",
                f"- mode: {template.get('mode', 'host_reasoned_greenfield_proposal')} (not greenfield and not host_reasoned_proposal_request)",
                f"- release_plan.selector: {release_plan.get('selector', DEFAULT_GREENFIELD_RELEASE_SELECTOR)}",
                f"- release_plan.label: {release_plan.get('label', DEFAULT_GREENFIELD_RELEASE_SELECTOR)}",
                "- components[].qualification: candidate; use components[].validation for proof expectations",
                "- diagrams[].kind plus diagrams[].mermaid_source; related_workstreams may use proposal-local WS ids",
                "- apply normalizes common aliases, but canonical fields avoid review-loop churn",
            ]
        )
        lines.extend(["", "Quality bar"])
        for rule in contract.get("quality_bar", []) if isinstance(contract.get("quality_bar"), list) else []:
            lines.append(f"- {rule}")
        lines.extend(["", "Apply"])
        lines.append("No files changed. To let Odylith own proposal, Tribunal, apply, refresh, and handoff in one path, run:")
        commands = proposal.get("apply_commands", [])
        if isinstance(commands, list) and commands:
            lines.append("  " + str(commands[0]))
        lines.append("After the operator accepts a host-reasoned proposal file, run:")
        if isinstance(commands, list) and len(commands) > 1:
            lines.append("  " + str(commands[1]))
        return "\n".join(lines).rstrip() + "\n"

    return _format_apply_ready_proposal_text(proposal)


def _format_apply_ready_proposal_text(
    proposal: Mapping[str, Any],
    *,
    request_context: Mapping[str, Any] | None = None,
) -> str:
    """Render the canonical proposal that apply can consume directly."""

    request_context = request_context or {}
    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "Greenfield Project")).strip()
    source = proposal.get("observed_source", {}) if isinstance(proposal.get("observed_source"), Mapping) else {}
    source_posture = str(source.get("source_posture", "unknown")).strip()
    gate = request_context.get("canonical_proposal_gate", {})
    gate_status = str(gate.get("status", "not-run")).strip() if isinstance(gate, Mapping) else "not-run"
    lines = [
        f"Odylith greenfield proposal: {title}",
        f"- source evidence: {source_posture}; writes stay confirmation-gated",
        f"- apply-ready JSON: built, normalized, validated, Tribunal {gate_status}",
        f"- mode: {proposal.get('mode', 'host_reasoned_greenfield_proposal')}",
        "- shared artifact: this text and `--format json` are rendered from the same canonical proposal",
        f"- provider_calls_by_odylith_cli: {proposal.get('provider_calls', 0)}",
    ]
    summary = str(intent.get("summary", "")).strip()
    if summary:
        lines.extend(["", "Intent", f"- {summary}"])

    label = str(intent.get("fit_label", "General Project")).strip()
    confidence = str(intent.get("confidence", "")).strip()
    if label and confidence:
        lines.append(f"- fit: {label} ({confidence} confidence)")
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
    if not ux and isinstance(request_context.get("greenfield_ux"), Mapping):
        ux = request_context.get("greenfield_ux", {})  # type: ignore[assignment]
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
            wave_id = row.get("wave") or row.get("wave_id") or row.get("id")
            gate_text = row.get("validation") or row.get("validation_gate") or row.get("exit_gate")
            lines.append(f"- Wave {wave_id}: {row.get('label') or row.get('name')} - {row.get('goal') or row.get('summary')} Proof: {gate_text}")
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    release_selector = _release_selector(release_plan)
    release_display = greenfield_programs.compact_release_target_label(release_selector)
    lines.extend(["", "Release plan"])
    lines.append(f"- target: {release_display}")
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
            stage = row.get("stage") or row.get("release") or "release"
            gate = row.get("release_gate") or row.get("exit_criteria") or row.get("gate")
            lines.append(f"- {stage}: {row.get('label')} gate - {gate}")
    for row in release_plan.get("milestones", []) if isinstance(release_plan.get("milestones"), list) else []:
        if isinstance(row, Mapping):
            lines.append(f"- {row.get('name')}: {row.get('exit_criteria')}")
    lines.extend(["", "Planned Registry components"])
    for row in proposal.get("components", []):
        if isinstance(row, Mapping):
            lines.append(
                f"- {row.get('component_id')}: {row.get('label')} -> {row.get('intended_path')} "
                f"({row.get('evidence_tier')}) Boundary: {row.get('boundary')}"
            )
    lines.extend(["", "Draft Atlas diagrams"])
    for row in proposal.get("diagrams", []):
        if isinstance(row, Mapping):
            lines.append(f"- {row.get('slug')}: {row.get('title')} ({row.get('link_state')})")
    lines.extend(["", "Validation focus"])
    for item in proposal.get("validation_strategy", []):
        lines.append(f"- {item}")
    risks = proposal.get("risks", []) if isinstance(proposal.get("risks"), list) else []
    if risks:
        lines.extend(["", "Risks"])
        for item in risks:
            if isinstance(item, Mapping):
                statement = str(item.get("statement") or item.get("title") or "").strip()
                mitigation = str(item.get("mitigation", "")).strip()
                if statement:
                    lines.append(f"- {statement}{f' Mitigation: {mitigation}' if mitigation else ''}")
            elif str(item).strip():
                lines.append(f"- {item}")
    lines.extend(["", "Apply gates"])
    lines.append("- deterministic proposal Tribunal must pass before any source-truth writes")
    lines.append("- final dashboard refresh makes Radar, Registry, Atlas, and Compass visible after writes")
    lines.extend(["", "Assumptions"])
    for item in proposal.get("assumptions", []):
        rendered = _render_evidence_item(item, "statement")
        if rendered:
            lines.append(f"- {rendered}")
    lines.extend(["", "Open questions"])
    for item in proposal.get("open_questions", []):
        rendered = _render_evidence_item(item, "question")
        if rendered:
            lines.append(f"- {rendered}")
    lines.extend(["", "Apply"])
    lines.append("No files changed. One-command confirmed path:")
    request_commands = request_context.get("apply_commands", [])
    create_command = ""
    if isinstance(request_commands, list):
        create_command = next((str(item) for item in request_commands if str(item).startswith("odylith greenfield create")), "")
    if not create_command:
        release_selector = _release_selector(release_plan)
        create_command = (
            "odylith greenfield create --repo-root . --prompt "
            + shell_quote(str(intent.get("prompt", "new project")))
            + f" --release {shell_quote(release_selector)} --confirm"
        )
    lines.append("  " + create_command)
    commands = proposal.get("apply_commands", [])
    if isinstance(commands, list) and len(commands) >= 2:
        lines.append("Or review/apply the canonical JSON explicitly:")
        lines.append("  " + str(commands[0]))
        lines.append("  " + str(commands[1]))
    return "\n".join(lines).rstrip() + "\n"


def _render_evidence_item(item: Any, preferred_key: str) -> str:
    if isinstance(item, Mapping):
        text = str(item.get(preferred_key) or item.get("statement") or item.get("question") or item.get("claim") or "").strip()
        tier = str(item.get("evidence_tier", "")).strip()
        return f"{text} ({tier})" if text and tier else text
    return str(item).strip()
