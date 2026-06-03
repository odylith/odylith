"""Participant card helpers for greenfield Project dashboards."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.artifact_enrichment import domain_graph_from_workstream
from odylith.runtime.domain_intelligence.artifact_enrichment import tribunal_actor_projection
from odylith.runtime.project_intelligence.greenfield_project_text import _capitalize_first
from odylith.runtime.project_intelligence.greenfield_project_text import _partition_casefold
from odylith.runtime.project_intelligence.participants import participant_body
from odylith.runtime.project_intelligence.participants import participant_key
from odylith.runtime.project_intelligence.participants import participant_title
from odylith.runtime.project_intelligence.participants import participant_title_and_body
from odylith.runtime.project_intelligence.utils import dict_value, display_text, list_value, sanitize_actor_body, sentence, short, strings


def _accepted_validation_gate(accepted: Mapping[str, Any]) -> Mapping[str, Any]:
    gate = dict_value(accepted.get("validation_gate"))
    if gate:
        return gate
    return dict_value(accepted.get("tribunal"))

def _actors(project: Mapping[str, Any], *, proposal: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    project_rows = _project_actor_rows(project=project, proposal=proposal)
    if project_rows:
        return project_rows[:6]

    accepted = dict_value(proposal.get("_accepted_project"))
    validation_gate = _accepted_validation_gate(accepted)
    visible_actors = [dict(row) for row in list_value(validation_gate.get("visible_actors")) if isinstance(row, Mapping)]
    if not visible_actors:
        visible_actors = [dict(row) for row in tribunal_actor_projection(proposal)]
    if visible_actors:
        owner_responsibilities = {**_proposal_actor_responsibility_map(proposal), **_owner_responsibility_map(project)}
        rows = [
            (
                "",
                sentence(row.get("visible_actor"), "Project actor"),
                short(
                    owner_responsibilities.get(sentence(row.get("visible_actor")).casefold())
                    or row.get("responsibility"),
                    limit=145,
                ),
            )
            for row in visible_actors[:6]
            if _is_project_actor_label(sentence(row.get("visible_actor")))
        ]
        if rows:
            return _dedupe_actor_rows(rows)[:6]
    rows = []
    for value in strings(project.get("owners"))[:6]:
        head, _, body = value.partition(":")
        title = sentence(head, "Owner")
        if _is_project_actor_label(title):
            rows.append(("", title, short(body or value, limit=145)))
    for value in strings(project.get("operators"))[:3]:
        head, _, body = value.partition(":")
        title = sentence(head, "Product decision owner")
        if _is_project_actor_label(title):
            rows.append(("", title, short(body or value, limit=145)))
    return _dedupe_actor_rows(rows)[:6] or [
        ("", "Product decision owner", "Reviews and accepts or revises the product direction before implementation.")
    ]


def _project_actor_rows(
    *,
    project: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> list[tuple[str, str, str]]:
    """Return Project-facing actors before internal Tribunal role projections."""

    direct_rows: list[tuple[str, str, str]] = []
    direct_rows.extend(_intent_actor_rows(proposal=proposal))
    direct_rows.extend(_domain_actor_rows(proposal=proposal))
    if direct_rows:
        return _dedupe_actor_rows(direct_rows)

    rows: list[tuple[str, str, str]] = []
    rows.extend(_customer_actor_rows(proposal=proposal))
    for value in [*strings(project.get("owners")), *strings(project.get("operators"))]:
        title, body = _actor_title_and_body(value)
        if _is_project_actor_label(title):
            rows.append(("", title, short(body, limit=145)))
    return _dedupe_actor_rows(rows)


def _domain_actor_rows(*, proposal: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for item in list_value(proposal.get("backlog")):
        if not isinstance(item, Mapping):
            continue
        intelligence = dict_value(item.get("domain_intelligence"))
        for value in strings(intelligence.get("actors")):
            title, body = _actor_title_and_body(value)
            if _is_project_actor_label(title):
                rows.append(("", title, short(body, limit=145)))
    return _dedupe_actor_rows(rows)


def _intent_actor_rows(*, proposal: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    intent = dict_value(proposal.get("intent"))
    context = sentence(intent.get("product_story") or intent.get("summary"))
    for value in strings(intent.get("human_actors")):
        title, body = participant_title_and_body(value, context=context)
        if title and _is_project_actor_label(title):
            rows.append(("", title, body))
    return rows


def _customer_actor_rows(*, proposal: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    backlog_items = [item for item in list_value(proposal.get("backlog")) if isinstance(item, Mapping)]
    backlog_items.sort(key=lambda item: 1 if sentence(item.get("title")).casefold().startswith("govern ") else 0)
    for item in backlog_items:
        customer = sentence(item.get("customer"))
        if not customer:
            continue
        context = sentence(item.get("opportunity") or item.get("problem") or item.get("product_view"))
        segments = _customer_segments(customer)
        actor_list = _customer_segments_are_actor_list(customer, segments)
        for segment in segments:
            title = _customer_actor_title(segment)
            if "," in title and not actor_list:
                continue
            if not _is_project_actor_label(title):
                continue
            body = _customer_actor_body(segment=segment, context="" if actor_list else context)
            rows.append(("", title, body))
    return rows


def _customer_segments(value: str) -> list[str]:
    text = display_text(value)
    pieces = [piece.strip(" .") for piece in re.split(r";|\s+;\s+", text) if piece.strip(" .")]
    if len(pieces) == 1 and "," in text:
        comma_pieces = [
            re.sub(r"^(?:and\s+)", "", piece.strip(" ."), flags=re.IGNORECASE)
            for piece in text.split(",")
            if piece.strip(" .")
        ]
        if len(comma_pieces) >= 2 and all(1 <= len(piece.split()) <= 5 for piece in comma_pieces):
            pieces = comma_pieces
    return pieces or ([text] if text else [])


def _customer_segments_are_actor_list(value: str, segments: Sequence[str]) -> bool:
    """Return true when a customer field is only a compact list of roles."""

    text = display_text(value)
    if len(segments) < 2 or "," not in text:
        return False
    for segment in segments:
        clean = display_text(segment)
        if not clean or len(clean.split()) > 6:
            return False
        if _role_description_parts(clean)[1]:
            return False
    return True


def _customer_actor_title(value: str) -> str:
    text = display_text(value).strip(" .")
    text = re.sub(r"^(?:the|a|an)\s+", "", text, flags=re.IGNORECASE)
    role, _body = _role_description_parts(text)
    if role:
        return short(participant_title(role) or _capitalize_first(role), limit=70)
    for marker in (
        " asking ",
        " auditing ",
        " authorizing ",
        " completing ",
        " configuring ",
        " entering ",
        " filing ",
        " filling ",
        " following up",
        " integrating ",
        " opening ",
        " producing ",
        " reading ",
        " receiving ",
        " registering ",
        " reviewing ",
        " selecting ",
        " submitting ",
        " running ",
        " using ",
        " who ",
        " at ",
    ):
        head, sep, _tail = _partition_casefold(text, marker)
        if sep and head.strip():
            text = head.strip(" .")
            break
    return short(participant_title(_capitalize_first(text)) or _capitalize_first(text), limit=70)


def _customer_actor_body(*, segment: str, context: str) -> str:
    text = display_text(segment).strip(" .")
    title, detail = _role_description_parts(text)
    if not title:
        title = _customer_actor_title(text)
        detail = text
        if title and text.casefold().startswith(title.casefold()):
            detail = text[len(title) :].strip(" .")
    if detail:
        return participant_body(title=title, body=_capitalize_first(detail), context=context)
    return participant_body(title=title, context=context or _default_actor_body(title))


def _actor_title_and_body(value: object) -> tuple[str, str]:
    text = display_text(value)
    if not text:
        return "", ""
    role, role_body = _role_description_parts(text)
    if role:
        title = participant_title(role) or role
        return title, participant_body(title=title, body=role_body, context=_default_actor_body(title))
    head, sep, body = text.partition(":")
    title = participant_title(head) or sentence(head)
    detail = sentence(body if sep else text)
    if not detail or detail.casefold() == title.casefold():
        detail = participant_body(title=title, context=_default_actor_body(title))
    elif detail:
        detail = participant_body(title=title, body=detail[:1].upper() + detail[1:])
    return title, detail


def _role_description_parts(value: str) -> tuple[str, str]:
    text = display_text(value).strip(" .")
    for separator in (" — ", " – ", " - "):
        head, sep, body = text.partition(separator)
        if sep and head.strip() and body.strip():
            return sentence(head), sentence(body)
    head, sep, body = text.partition(":")
    if sep and head.strip() and body.strip() and len(head.split()) <= 10:
        return sentence(head), sentence(body)
    return "", ""


def _default_actor_body(title: str) -> str:
    lowered = title.casefold()
    if any(token in lowered for token in ("owner", "advocate", "user", "customer", "client")):
        return "Uses the product outcome to decide what should happen next."
    if any(token in lowered for token in ("operator", "coordinator", "caretaker", "maintainer")):
        return "Coordinates exceptions and keeps the right people aligned around the product outcome."
    if any(token in lowered for token in ("risk", "safety", "compliance", "privacy")):
        return "Owns the harm, policy, or operational exposure that can block adoption."
    if any(token in lowered for token in ("proof", "evidence", "quality", "validation", "reviewer")):
        return "Decides whether the outcome is clear, explainable, and trustworthy enough to use."
    if any(token in lowered for token in ("build", "implementation", "engineer", "developer")):
        return "Owns the implementation path after the project direction is accepted."
    return "Has a distinct stake in the product outcome and needs enough context to act responsibly."


def _is_project_actor_label(value: str) -> bool:
    label = sentence(value)
    if not label:
        return False
    if len(label.split()) > 10:
        return False
    lowered = label.casefold().replace("_", " ")
    if re.match(
        r"^(?:and|or|where|when|if|because|so|that|which|what|why|how|with|against|from|until|before|after)\b",
        lowered,
    ):
        return False
    if lowered in {
        "actor",
        "other accepted items",
        "beneficiary advocate",
        "domain operator",
        "risk owner",
        "evidence owner",
        "implementation owner",
        "release owner",
        "project actor",
        "primary user",
    }:
        return False
    if lowered.startswith(("the first-release actors are", "actors involved in")):
        return False
    if "accepted items" in lowered and "intent" in lowered:
        return False
    internal_markers = (
        "program boundary",
        "safety envelope",
        "project intelligence",
        "governance artifact",
        "release gate",
        "proof gate",
        "source boundary",
        "topology spine",
    )
    if any(marker in lowered for marker in internal_markers):
        return False
    system_markers = (
        "unit",
        "core",
        "controller",
        "engine",
        "harness",
        "interface",
        "registry",
        "atlas",
        "radar",
        "compass",
        "casebook",
        "diagram",
    )
    human_markers = (
        "advocate",
        "analyst",
        "approver",
        "caretaker",
        "client",
        "coordinator",
        "customer",
        "engineer",
        "maintainer",
        "operator",
        "owner",
        "person",
        "observer",
        "reviewer",
        "steward",
        "team",
        "user",
        "verifier",
    )
    if any(marker in lowered for marker in system_markers) and not any(
        marker in lowered for marker in human_markers
    ):
        return False
    return True


def _dedupe_actor_rows(rows: Sequence[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    seen: dict[str, int] = {}
    for role, title, body in rows:
        clean_title, clean_body = _actor_display_parts(title=title, body=body)
        key = _actor_dedupe_key(clean_title)
        if not clean_title:
            continue
        if key in seen:
            existing_index = seen[key]
            existing_role, existing_title, existing_body = result[existing_index]
            if _should_replace_actor_body(
                title=existing_title,
                existing_body=existing_body,
                candidate_body=clean_body,
            ):
                result[existing_index] = (
                    existing_role or sentence(role),
                    existing_title,
                    clean_body,
                )
            continue
        seen[key] = len(result)
        result.append((sentence(role), clean_title, clean_body))

    return result


def _should_replace_actor_body(*, title: str, existing_body: str, candidate_body: str) -> bool:
    if not candidate_body:
        return False
    if _is_default_actor_body(title=title, body=existing_body) and not _is_default_actor_body(
        title=title, body=candidate_body
    ):
        return True
    if _looks_generated_actor_context(existing_body) and not _looks_generated_actor_context(candidate_body):
        return True
    return len(candidate_body) > len(existing_body)


def _is_default_actor_body(*, title: str, body: str) -> bool:
    return _repeat_key(body) == _repeat_key(_default_actor_body(title))


def _looks_generated_actor_context(value: str) -> bool:
    lowered = sentence(value).casefold()
    return lowered.startswith(("build the ", "implement ", "turn the confirmed ")) or any(
        marker in lowered
        for marker in (
            "can fail when the first material path action",
            "cannot support release review unless",
            "review output with validation results",
            "as the state and handoff boundary",
        )
    )


def _actor_display_parts(*, title: object, body: object) -> tuple[str, str]:
    clean_title = participant_title(title) or display_text(title)
    clean_body = participant_body(title=clean_title, body=sanitize_actor_body(body))
    role, role_body = _role_description_parts(clean_title)
    if role:
        clean_title = participant_title(role) or role
        if role_body and (not clean_body or clean_body.casefold() == role.casefold()):
            clean_body = participant_body(title=clean_title, body=_capitalize_first(role_body))
    if not clean_body:
        clean_body = _default_actor_body(clean_title)
    return clean_title, clean_body


def _actor_dedupe_key(value: str) -> str:
    key = participant_key(value)
    return key or sentence(value).casefold().strip(" .")


def _dedupe_text(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = sentence(value)
        key = " ".join(text.casefold().split())
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _repeat_key(value: object) -> str:
    text = sentence(value).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _proposal_actor_responsibility_map(proposal: Mapping[str, Any]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for item in list_value(proposal.get("backlog")):
        if not isinstance(item, Mapping):
            continue
        intelligence = dict_value(item.get("domain_intelligence"))
        for value in strings(intelligence.get("actors")):
            actor, sep, body = display_text(value).partition(":")
            if sep and actor.strip() and body.strip():
                rows.setdefault(actor.strip().casefold(), body.strip()[:1].upper() + body.strip()[1:])
    return rows


def _owner_responsibility_map(project: Mapping[str, Any]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for value in strings(project.get("owners")):
        text = sentence(value)
        if not text:
            continue
        actor = text
        body = text
        for marker in (" owns ", " is responsible for ", " reviews "):
            before, sep, after = text.partition(marker)
            if sep and before.strip() and after.strip():
                actor = before.strip()
                verb = marker.strip().split()[0].capitalize()
                body = f"{verb} {after.strip()}"
                break
        rows[actor.casefold()] = body
    return rows
