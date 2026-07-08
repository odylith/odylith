"""Operator-facing rendering for greenfield proposal payloads."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_command_text import shell_quote
from odylith.runtime.domain_intelligence.greenfield_project_brief import render_project_brief_lines
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import render_project_intelligence_section
from odylith.runtime.project_intelligence.intent_confirmation import format_confirmation_choice_lines

DEFAULT_GREENFIELD_RELEASE_SELECTOR = greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR
_PROJECT_REQUIREMENTS_TEXT_PREVIEW_LIMIT = 90


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
    prompt_arg = shell_quote(str(proposal.get("intent", {}).get("prompt", "new project")))
    commands = [
        "odylith greenfield compile-transaction --repo-root . --prompt "
        + prompt_arg
        + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json"
        + release_arg,
        "# after compile, confirm or reject the transaction-ready screen that shows the real hash",
        "# optional audit artifact: `greenfield compile-transaction --intent-file .odylith/runtime/greenfield/confirmed-intent.md --format json` prints the validated transaction payload",
    ]
    if backlog:
        commands.append("# commit will create project workstream records from the validated transaction")
    if components:
        commands.append("# commit will register planned candidate component specs with user_intent evidence")
    if diagrams:
        commands.append("# commit will scaffold draft architecture topology with review-draft link state")
    commands.append("# commit will refresh accepted product records after all artifacts are written")
    return commands


def format_proposal_text(proposal: Mapping[str, Any], *, detail: str = "brief") -> str:
    """Render a concise operator-facing proposal or no-write host contract."""

    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "Greenfield Project")).strip()
    if proposal.get("mode") == "host_reasoned_proposal_request":
        source = proposal.get("observed_source", {}) if isinstance(proposal.get("observed_source"), Mapping) else {}
        ux = proposal.get("greenfield_ux", {}) if isinstance(proposal.get("greenfield_ux"), Mapping) else {}
        contract = proposal.get("reasoning_contract", {}) if isinstance(proposal.get("reasoning_contract"), Mapping) else {}
        handoff = (
            contract.get("post_confirmation_handoff", {})
            if isinstance(contract.get("post_confirmation_handoff"), Mapping)
            else {}
        )
        commands = proposal.get("apply_commands", [])
        lines = [
            f"Greenfield Proposal Contract: {title}",
            f"- source posture: {source.get('source_posture', 'unknown')}",
            "- files changed: none",
            "- generated governance artifacts: none",
            "- proposal authorship: legacy reasoning-request mode; prefer confirmed create path",
            f"- provider calls by Odylith CLI: {proposal.get('provider_calls', 0)}",
            "- write gate: `greenfield compile-transaction` builds, repairs, validates, quality-gates, and hashes the package before confirmation; the transaction-ready screen owns the commit-only create command",
            "",
            "Host handoff",
        ]
        for rule in _contract_rows(handoff.get("contract_use"), limit=3):
            lines.append(f"- {rule}")
        for rule in _contract_rows(handoff.get("forbidden_host_steps"), limit=2):
            lines.append(f"- Stop: {rule}")
        lines.extend(
            [
                "- Use `odylith greenfield compile-transaction --repo-root . --prompt \"<confirmed request>\" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json --release 0.0.1`, then follow the transaction-ready confirmation screen.",
                "",
                "Confirmed create after intent confirmation",
            ]
        )
        for step in _contract_rows(handoff.get("allowed_host_steps"), limit=4):
            lines.append(f"- {step}")
        for step in _contract_rows(handoff.get("failure_policy"), limit=2):
            lines.append(f"- {step}")
        lines.extend(
            [
                "",
            "Host task",
            f"- {proposal.get('host_instruction', 'Draft a concrete proposal from prompt and repo evidence.')}",
            f"- next: {ux.get('next_best_action', 'draft the proposal, then ask for confirmation before writes')}",
            "",
            "Required proposal sections",
            ]
        )
        required_keys = contract.get("required_top_level_keys", []) if isinstance(contract.get("required_top_level_keys"), list) else []
        if detail == "full":
            for key in required_keys:
                lines.append(f"- {key}")
        else:
            lines.append("- " + ", ".join(str(key) for key in required_keys))
        lines.extend(["", "Evidence rules"])
        for rule in contract.get("evidence_rules", []) if isinstance(contract.get("evidence_rules"), list) else []:
            lines.append(f"- {rule}")
        if detail == "full":
            lines.extend(["", "Quality bar"])
            for rule in contract.get("quality_bar", []) if isinstance(contract.get("quality_bar"), list) else []:
                lines.append(f"- {rule}")
        lines.extend(["", "Confirmed create"])
        lines.append("After Product Intent is confirmed, run the confirmed create path; do not ask the operator to inspect proposal JSON.")
        if isinstance(commands, list):
            for command in commands:
                lines.append("  " + str(command))
        return "\n".join(lines).rstrip() + "\n"

    return _format_governed_proposal_text(proposal)


def _contract_rows(value: Any, *, limit: int) -> list[str]:
    rows = value if isinstance(value, list) else []
    return [" ".join(str(item).split()).strip() for item in rows[:limit] if str(item).strip()]


def _format_proposal_preview_text(
    proposal: Mapping[str, Any],
    *,
    request_context: Mapping[str, Any],
) -> str:
    """Render the default greenfield review gate without dumping the full record."""

    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "Greenfield Project")).strip()
    source = proposal.get("observed_source", {}) if isinstance(proposal.get("observed_source"), Mapping) else {}
    source_posture = str(source.get("source_posture", "unknown")).strip()
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    release_selector = _release_selector(release_plan)
    release_display = greenfield_programs.compact_release_target_label(release_selector)
    project_intelligence = (
        proposal.get("project_intelligence", {}) if isinstance(proposal.get("project_intelligence"), Mapping) else {}
    )
    project_brief = proposal.get("project_brief", {}) if isinstance(proposal.get("project_brief"), Mapping) else {}
    commands = request_context.get("apply_commands", [])
    apply_json_command = ""
    if isinstance(commands, list):
        apply_json_command = next((str(item) for item in commands if str(item).startswith("odylith greenfield compile-transaction")), "")
    if not apply_json_command:
        apply_json_command = "odylith greenfield compile-transaction --repo-root . --prompt '<confirmed request>' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json" + f" --release {shell_quote(release_selector)}"

    lines = [
        f"Greenfield proposal preview: {title}",
        f"- source evidence: {source_posture}; No files changed.",
        "- gate: preview only; product records are written only after explicit confirmation",
        "- proposal authorship: Odylith built the governed proposal from confirmed intent",
        "",
        "Gate 1 - Interpretation",
    ]
    lines.extend(_preview_project_intent_lines(project_intelligence))
    lines.extend(["", "Gate 2 - Clarify Before Confirmation"])
    lines.extend(_preview_option_lines(project_brief.get("customization_options"), limit=6))
    question_lines = _preview_question_lines(proposal.get("open_questions"), limit=3)
    if question_lines:
        lines.extend(["- Open questions that can change the proposal:"])
        lines.extend(f"  - {line}" for line in question_lines)
    lines.extend(["", "Gate 3 - Proposal Preview"])
    release_strategy = str(release_plan.get("strategy", "")).strip()
    lines.append(f"- First release: {release_display}" + (f" - {release_strategy}" if release_strategy else ""))
    workstream_lines = _preview_workstream_lines(proposal.get("backlog"), limit=4)
    if workstream_lines:
        lines.append("- Product workstreams:")
        lines.extend(f"  - {line}" for line in workstream_lines)
    component_lines = _preview_component_lines(proposal.get("components"), limit=3)
    if component_lines:
        lines.append("- Candidate product boundaries:")
        lines.extend(f"  - {line}" for line in component_lines)
    diagram_lines = _preview_architecture_lines(proposal.get("diagrams"), limit=5)
    if diagram_lines:
        lines.append("- Architecture review views:")
        lines.extend(f"  - {line}" for line in diagram_lines)
    lines.extend(
        [
            "",
            *format_confirmation_choice_lines(
                (
                    (
                        "CONFIRM",
                        "Accept this preview so Odylith can compile the ProductCreateTransaction and show the final hash confirmation before records are written.",
                    ),
                    (
                        "EDIT",
                        "Put corrections after EDIT; Odylith treats them as new evidence and rebuilds from the sharper intent.",
                    ),
                    ("REJECT", "Stop. No governed records are written."),
                )
            ),
            "- After the transaction is ready, Odylith shows the hash and the commit-only confirmation screen.",
            "Odylith system action after **CONFIRM**",
            "- Do not paste this command in your reply. Reply only with CONFIRM, EDIT, or REJECT.",
            f"- Compile transaction: {apply_json_command}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _preview_project_intent_lines(project_intelligence: Mapping[str, Any]) -> list[str]:
    intent_rows = project_intelligence.get("intent", [])
    rows = [str(item).strip() for item in intent_rows if str(item).strip()] if isinstance(intent_rows, list) else []
    preferred = (
        "Project objective:",
        "User or stakeholder outcome:",
        "Success condition:",
        "What breaks if it fails:",
        "Non-goals:",
    )
    rendered: list[str] = []
    for prefix in preferred:
        value = next((row for row in rows if row.startswith(prefix)), "")
        if value:
            rendered.append(f"- {_compact_text(value)}")
    if rendered:
        return rendered
    purpose = str(project_intelligence.get("purpose", "")).strip()
    return [f"- {_compact_text(purpose)}"] if purpose else ["- Review the inferred product objective, primary user, non-goals, and first proof target."]


def _preview_option_lines(value: Any, *, limit: int) -> list[str]:
    rows = value if isinstance(value, list) else []
    lines: list[str] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        decision = str(row.get("decision", "")).strip()
        recommended = str(row.get("recommended", "")).strip()
        impact = str(row.get("impact", "")).strip()
        if decision and recommended:
            line = f"- {decision}: {_compact_text(recommended, max_chars=170)}"
            if impact:
                line += f" Impact: {_compact_text(impact, max_chars=140)}"
            lines.append(line)
    if lines:
        return lines
    return ["- Confirm primary user, runtime, data boundary, first release ambition, and proof threshold before apply."]


def _preview_question_lines(value: Any, *, limit: int) -> list[str]:
    rows = value if isinstance(value, list) else []
    questions: list[str] = []
    for row in rows[:limit]:
        if isinstance(row, Mapping):
            question = str(row.get("question", "")).strip()
            impact = str(row.get("impact", "")).strip()
        else:
            question = str(row).strip()
            impact = ""
        if question:
            question_text = _compact_text(question, max_chars=180)
            if question_text[-1:] not in {".", "?", "!"}:
                question_text = f"{question_text}."
            line = f"Question: {question_text}"
            if impact:
                line += f" Impact: {_compact_text(impact.rstrip(' .'), max_chars=140)}."
            questions.append(line)
    return questions


def _preview_workstream_lines(value: Any, *, limit: int) -> list[str]:
    rows = value if isinstance(value, list) else []
    lines: list[str] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        title = str(row.get("title", "")).strip()
        first_slice = str(row.get("recommended_first_slice", "")).strip()
        if title and first_slice:
            lines.append(f"{title}: {_compact_text(first_slice)}")
        elif title:
            lines.append(title)
    return lines


def _preview_component_lines(value: Any, *, limit: int) -> list[str]:
    rows = value if isinstance(value, list) else []
    lines: list[str] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        label = str(row.get("label", "") or row.get("component_id", "")).strip()
        boundary = str(row.get("boundary", "")).strip()
        if label and boundary:
            lines.append(f"{label}: {_compact_text(boundary)}")
        elif label:
            lines.append(label)
    return lines


def _preview_architecture_lines(value: Any, *, limit: int) -> list[str]:
    rows = value if isinstance(value, list) else []
    lines: list[str] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        title = str(row.get("title", "")).strip()
        question = str(row.get("operator_question", "")).strip()
        if title and question:
            lines.append(f"{title}: {_compact_text(question, max_chars=180)}")
        elif title:
            lines.append(title)
    return lines


def _compact_text(value: str, *, max_chars: int = 220) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _format_governed_proposal_text(
    proposal: Mapping[str, Any],
    *,
    request_context: Mapping[str, Any] | None = None,
) -> str:
    """Render the governed proposal review without exposing internal normalization work."""

    request_context = request_context or {}
    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "Greenfield Project")).strip()
    source = proposal.get("observed_source", {}) if isinstance(proposal.get("observed_source"), Mapping) else {}
    source_posture = str(source.get("source_posture", "unknown")).strip()
    gate = request_context.get("proposal_gate", {})
    gate_status = str(gate.get("status", "not-run")).strip() if isinstance(gate, Mapping) else "not-run"
    lines = [
        f"Odylith greenfield proposal: {title}",
        f"- source evidence: {source_posture}; writes stay confirmation-gated",
        f"- governed proposal: built from confirmed intent, normalized, validated, proposal gate {gate_status}",
        f"- mode: {proposal.get('mode', 'host_reasoned_greenfield_proposal')}",
        "- review views: this text and `--format json` are rendered from the same governed proposal",
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
                f"- guardrail: {ux.get('write_guardrail', 'confirm before accepted product writes')}",
                f"- next: {ux.get('next_best_action', 'confirm or revise the proposed first wave')}",
            ]
        )
    project_brief = proposal.get("project_brief", {}) if isinstance(proposal.get("project_brief"), Mapping) else {}
    project_intelligence = (
        proposal.get("project_intelligence", {}) if isinstance(proposal.get("project_intelligence"), Mapping) else {}
    )
    intelligence_text = render_project_intelligence_section(project_intelligence, preview=True)
    if intelligence_text:
        lines.extend(["", "Project requirements"])
        lines.extend(
            _bounded_preview_lines(
                _indent_markdown_preview(intelligence_text),
                limit=_PROJECT_REQUIREMENTS_TEXT_PREVIEW_LIMIT,
                label="project requirement rows",
            )
        )
    brief_lines = render_project_brief_lines(project_brief)
    if brief_lines:
        lines.extend(["", "Project-first blueprint"])
        lines.extend(brief_lines)
    lines.extend(["", "Backlog proposal"])
    for row in proposal.get("backlog", []):
        if isinstance(row, Mapping):
            lines.append(f"- {row.get('title')}: {row.get('recommended_first_slice')}")
    intelligence_lines = _domain_intelligence_preview(proposal.get("backlog", []))
    if intelligence_lines:
        lines.extend(["", "Workstream domain intelligence"])
        lines.extend(intelligence_lines)
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
    lines.extend(["", "Planned components"])
    for row in proposal.get("components", []):
        if isinstance(row, Mapping):
            lines.append(
                f"- {row.get('component_id')}: {row.get('label')} -> {row.get('intended_path')} "
                f"({row.get('evidence_tier')}) Boundary: {row.get('boundary')}"
            )
    lines.extend(["", "Draft architecture diagrams"])
    for row in proposal.get("diagrams", []):
        if isinstance(row, Mapping):
            lines.extend(_atlas_diagram_lines(row))
    lines.extend(["", "Validation focus"])
    for item in proposal.get("validation_strategy", []):
        lines.append(f"- {item}")
    risks = proposal.get("risks", []) if isinstance(proposal.get("risks"), list) else []
    if risks:
        lines.extend(["", "Risks"])
        for item in risks:
            if isinstance(item, Mapping):
                statement = str(item.get("statement") or item.get("title") or "").strip()
                details = _risk_detail_segments(item)
                if statement:
                    line = f"- {statement}"
                    if details:
                        line += " " + " ".join(details)
                    lines.append(line)
            elif str(item).strip():
                lines.append(f"- {item}")
    lines.extend(["", "Write gates"])
    lines.append("- ProductCreateTransaction compilation must pass before confirmation")
    lines.append("- confirmed create verifies the transaction hash before any source-truth writes")
    lines.append("- final refresh publishes accepted product records after the commit-only write")
    lines.extend(["", "Assumptions"])
    for item in proposal.get("assumptions", []):
        rendered = _render_evidence_item(item, "statement")
        if rendered:
            lines.append(f"- {rendered}")
    lines.extend(["", "Open questions"])
    for item in proposal.get("open_questions", []):
        rendered = _render_evidence_item(item, "question")
        if rendered:
            lines.append(f"- Question: {rendered}")
    lines.extend(
        [
            "",
            *format_confirmation_choice_lines(
                (
                    (
                        "CONFIRM",
                        "Accept this proposal so Odylith can compile the ProductCreateTransaction and show the hash-ready final command before any records are written.",
                    ),
                    (
                        "EDIT",
                        "Put corrections after EDIT; Odylith treats them as new evidence and rebuilds before compiling a transaction.",
                    ),
                    ("REJECT", "Stop. No governed records are written."),
                )
            ),
        ]
    )
    lines.extend(["", "Transaction path"])
    lines.append("No governed records changed. Transaction path:")
    lines.append("- Do not paste the transaction command in your reply. Reply only with CONFIRM, EDIT, or REJECT.")
    request_commands = request_context.get("apply_commands", [])
    apply_command = ""
    if isinstance(request_commands, list):
        apply_command = next((str(item) for item in request_commands if str(item).startswith("odylith greenfield compile-transaction")), "")
    if not apply_command:
        release_selector = _release_selector(release_plan)
        apply_command = "odylith greenfield compile-transaction --repo-root . --prompt '<confirmed request>' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json" + f" --release {shell_quote(release_selector)}"
    lines.append("  # Odylith compiles and validates the transaction before hash confirmation")
    lines.append("  " + apply_command)
    commands = proposal.get("apply_commands", [])
    if isinstance(commands, list) and commands:
        visible_commands = [
            str(command)
            for command in commands
            if not str(command).startswith("odylith greenfield create")
        ]
        if visible_commands:
            lines.append("Review/compile commands from the proposal:")
            for command in visible_commands:
                lines.append("  " + command)
    return "\n".join(lines).rstrip() + "\n"


def _indent_markdown_preview(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            lines.append("")
        elif line.startswith("### "):
            lines.append(f"- {line[4:]}")
        elif line.startswith("- "):
            lines.append(f"  - {line[2:]}")
        else:
            lines.append(f"- {line}")
    return lines


def _bounded_preview_lines(lines: list[str], *, limit: int, label: str) -> list[str]:
    if len(lines) <= limit:
        return lines
    hidden = len(lines) - limit
    return [*lines[:limit], f"- plus {hidden} additional {label} in --format json"]


def _render_evidence_item(item: Any, preferred_key: str) -> str:
    if isinstance(item, Mapping):
        text = str(item.get(preferred_key) or item.get("statement") or item.get("question") or item.get("claim") or "").strip()
        tier = str(item.get("evidence_tier", "")).strip()
        return f"{text} ({tier})" if text and tier else text
    return str(item).strip()


def _risk_detail_segments(item: Mapping[str, Any]) -> list[str]:
    segments: list[str] = []
    for key, label in (
        ("risk_class", "Class"),
        ("severity", "Severity"),
        ("probability", "Probability"),
        ("blast_radius", "Blast radius"),
        ("trigger", "Trigger"),
        ("early_warning", "Early warning"),
        ("owner", "Owner"),
        ("evidence", "Evidence"),
        ("mitigation", "Mitigation"),
    ):
        value = str(item.get(key, "") or "").strip()
        if value:
            segments.append(f"{label}: {value}")
    return segments


def _atlas_diagram_lines(row: Mapping[str, Any]) -> list[str]:
    slug = str(row.get("slug", "")).strip()
    title = str(row.get("title", "")).strip()
    state = str(row.get("link_state", "")).strip()
    state_label = "first draft" if state in {"atlas_first_draft", "architecture_first_draft"} else state
    heading = f"- {slug}: {title} ({state_label})".strip()
    lines = [heading]
    gate = str(row.get("proof_gate", "")).strip()
    if gate:
        lines.append(f"  - gate: {gate}")
    return lines


def _domain_intelligence_preview(backlog: Any) -> list[str]:
    lines: list[str] = []
    rows = backlog if isinstance(backlog, list) else []
    for row in rows[:4]:
        if not isinstance(row, Mapping):
            continue
        intelligence = row.get("domain_intelligence")
        if not isinstance(intelligence, Mapping):
            continue
        title = str(row.get("title", "")).strip()
        ontology = _first_terms(intelligence.get("ontology"), limit=3)
        operators = _first_terms(intelligence.get("operators"), limit=2)
        validation = _first_terms(intelligence.get("validation_obligations"), limit=2)
        parts = []
        if ontology:
            parts.append("terms: " + "; ".join(ontology))
        if operators:
            parts.append("operators: " + "; ".join(operators))
        if validation:
            parts.append("proof: " + "; ".join(validation))
        if title and parts:
            lines.append(f"- {title}: " + " | ".join(parts))
    return lines


def _first_terms(value: Any, *, limit: int) -> list[str]:
    if isinstance(value, Mapping):
        candidates = [str(item).strip() for item in value.values()]
    elif isinstance(value, list):
        candidates = [str(item).strip() for item in value]
    else:
        candidates = [str(value).strip()] if str(value or "").strip() else []
    terms = []
    for item in candidates:
        if not item:
            continue
        head = item.split(".", 1)[0].strip()
        if len(head) > 140:
            head = head[:137].rstrip() + "..."
        terms.append(head)
        if len(terms) >= limit:
            break
    return terms
