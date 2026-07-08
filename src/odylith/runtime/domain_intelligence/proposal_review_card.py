"""Short host-visible greenfield proposal review cards."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.project_intelligence.intent_confirmation import format_confirmation_choice_lines

DEFAULT_GREENFIELD_RELEASE_SELECTOR = greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR


def format_visible_proposal_card_text(
    proposal: Mapping[str, Any],
    *,
    request_context: Mapping[str, Any],
) -> str:
    """Render the default greenfield review card.

    This is intentionally short enough to stay visible in Claude/Codex tool
    transcripts after product intent is confirmed. The longer text gate stays
    behind ``--confirm-intent --detail full``. The governed package is compiled
    into a ProductCreateTransaction before ``greenfield create`` commits it.
    """

    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = _visible_title(str(intent.get("title", "Greenfield Project")).strip())
    source = proposal.get("observed_source", {}) if isinstance(proposal.get("observed_source"), Mapping) else {}
    source_posture = str(source.get("source_posture", "unknown")).strip()
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    release_selector = _release_selector(release_plan)
    release_display = greenfield_programs.compact_release_target_label(release_selector)
    project_intelligence = (
        proposal.get("project_intelligence", {}) if isinstance(proposal.get("project_intelligence"), Mapping) else {}
    )
    project_brief = proposal.get("project_brief", {}) if isinstance(proposal.get("project_brief"), Mapping) else {}

    lines = [
        f"Greenfield proposal preview: {title}",
        f"No files changed. Source evidence: {source_posture}. Writes happen only after explicit confirmation.",
        "",
        "Project shape",
    ]
    product_line = _intent_value(project_intelligence, "Project objective:")
    if product_line:
        lines.append(f"- Product: {_visible_review_text(product_line)}")
    outcome_line = _intent_value(project_intelligence, "User or stakeholder outcome:")
    proof_line = _visible_first_proof_line(proposal) or _intent_value(project_intelligence, "Success condition:")
    if outcome_line:
        lines.append(f"- User outcome: {_visible_review_text(outcome_line)}")
    if proof_line:
        lines.append(f"- First proof: {_visible_review_text(proof_line)}")
    non_goal_line = _intent_value(project_intelligence, "Non-goals:")
    if non_goal_line:
        lines.append(f"- Not in first release: {_visible_review_text(non_goal_line)}")

    choice_lines = _visible_choice_lines(project_brief.get("customization_options"), limit=4)
    if choice_lines:
        lines.extend(["", "Decisions before confirmation"])
        lines.extend(f"- {line}" for line in choice_lines)

    lines.extend(
        [
            "",
            "Records after transaction commit",
            f"- {_visible_records_line(proposal, release_display=release_display)}",
            "",
            *format_confirmation_choice_lines(
                (
                    (
                        "CONFIRM",
                        "Accept this preview so Odylith can compile the ProductCreateTransaction and show the transaction hash before any records are written.",
                    ),
                    ("EDIT", "Put corrections after EDIT; Odylith treats them as new evidence before rerunning greenfield propose."),
                    ("REJECT", "Stop. No governed records are written."),
                )
            ),
            "",
            "Odylith system action after **CONFIRM**",
            "- Do not paste this command in your reply. Start your reply with exactly one of CONFIRM, EDIT, or REJECT.",
            f"- Compile transaction: {_visible_compile_command(proposal, request_context=request_context, release_selector=release_selector)}",
            "- Full review: add --confirm-intent --detail full for the long contract; export JSON only when explicitly requested.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _release_selector(release_plan: Mapping[str, Any]) -> str:
    selector = str(release_plan.get("selector", "")).strip()
    return selector or DEFAULT_GREENFIELD_RELEASE_SELECTOR


def _intent_value(project_intelligence: Mapping[str, Any], prefix: str) -> str:
    intent_rows = project_intelligence.get("intent", [])
    rows = [str(item).strip() for item in intent_rows if str(item).strip()] if isinstance(intent_rows, list) else []
    for row in rows:
        if row.startswith(prefix):
            return row[len(prefix) :].strip()
    return ""


def _visible_first_proof_line(proposal: Mapping[str, Any]) -> str:
    rows = proposal.get("backlog", [])
    backlog = rows if isinstance(rows, list) else []
    for row in backlog:
        if not isinstance(row, Mapping):
            continue
        title = str(row.get("title", "")).strip()
        first_slice = str(row.get("recommended_first_slice", "")).strip()
        if first_slice and not title.startswith("Govern "):
            return first_slice
    for row in backlog:
        if isinstance(row, Mapping):
            first_slice = str(row.get("recommended_first_slice", "")).strip()
            if first_slice:
                return first_slice
    return ""


def _visible_choice_lines(value: Any, *, limit: int) -> list[str]:
    rows = value if isinstance(value, list) else []
    lines: list[str] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        decision = str(row.get("decision", "")).strip()
        recommended = str(row.get("recommended", "")).strip()
        if decision and recommended:
            lines.append(f"{decision}: {_visible_review_text(recommended, max_chars=220)}")
    if lines:
        return lines
    return ["Confirm the first user, runtime, data boundary, release ambition, and proof threshold."]


def _visible_review_text(value: str, *, max_chars: int = 300) -> str:
    text = " ".join(str(value or "").split()).strip()
    if text.casefold().startswith("govern "):
        text = text[len("govern ") :].strip()
        if text:
            text = text[:1].upper() + text[1:]
    if len(text) <= max_chars:
        return text
    for separator in (". ", "; ", " before ", " while ", " without ", " until "):
        head = text.split(separator, 1)[0].strip()
        if 60 <= len(head) <= max_chars:
            return head + "." if separator == ". " else head.rstrip(" ,;") + "."
    words = text.split()
    if len(words) <= 18:
        return text
    return " ".join(words[:18]).rstrip(" ,;:") + "."


def _visible_title(value: str) -> str:
    title = " ".join(str(value or "").split()).strip(" ,.;:")
    return title or "Greenfield Project"


def _visible_records_line(proposal: Mapping[str, Any], *, release_display: str) -> str:
    backlog_count = len([row for row in proposal.get("backlog", []) if isinstance(row, Mapping)])
    component_count = len([row for row in proposal.get("components", []) if isinstance(row, Mapping)])
    diagram_count = len([row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)])
    pieces: list[str] = []
    if backlog_count:
        pieces.append(f"{backlog_count} workstreams")
    if component_count:
        pieces.append(f"{component_count} component boundaries")
    if diagram_count:
        pieces.append(f"{diagram_count} Atlas review views")
    if not pieces:
        pieces.append("accepted project direction")
    return ", ".join(pieces) + f", release {release_display}."


def _visible_compile_command(
    proposal: Mapping[str, Any],
    *,
    request_context: Mapping[str, Any],
    release_selector: str,
) -> str:
    commands = request_context.get("apply_commands", [])
    if isinstance(commands, list):
        command = next((str(item) for item in commands if str(item).startswith("odylith greenfield compile-transaction")), "")
        if command:
            return command
    return (
        "odylith greenfield compile-transaction --repo-root . --prompt '<confirmed request>' "
        "--intent-file .odylith/runtime/greenfield/confirmed-intent.md "
        "--output .odylith/runtime/greenfield/product-create-transaction.v1.json "
        f"--release {release_selector}"
    )
