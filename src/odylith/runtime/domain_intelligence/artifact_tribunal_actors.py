"""Visible Tribunal actor projection from Domain Intelligence graphs."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.artifact_graph import DomainIntelligenceGraph
from odylith.runtime.domain_intelligence.artifact_graph import domain_graph_from_workstream
from odylith.runtime.domain_intelligence.greenfield_actor_labels import accepted_actor_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import restore_source_acronym_number_tokens
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


TRIBUNAL_STABLE_ROLES = (
    "beneficiary_advocate",
    "domain_operator",
    "risk_owner",
    "evidence_owner",
    "implementation_owner",
    "release_owner",
)


def tribunal_actor_projection(proposal: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Return domain-specific visible Tribunal actors for a proposal."""

    first_graph = _first_domain_graph(proposal)
    actor_names = _domain_actor_names(first_graph, proposal=proposal)
    responsibilities = {
        "beneficiary_advocate": "Protects the person or team receiving the value.",
        "domain_operator": "Checks that the workflow is operationally coherent.",
        "risk_owner": "Owns loss, harm, compliance, safety, or operational exposure.",
        "evidence_owner": "Decides what proof is strong enough to trust.",
        "implementation_owner": "Owns source paths, interfaces, and build sequence.",
        "release_owner": "Owns release boundary, rollback, and promotion readiness.",
    }
    return tuple(
        {
            "stable_role": role,
            "visible_actor": actor_names[role],
            "responsibility": responsibilities[role],
        }
        for role in TRIBUNAL_STABLE_ROLES
    )


def _first_domain_graph(proposal: Mapping[str, Any]) -> DomainIntelligenceGraph:
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    for row in rows:
        intelligence = row.get("domain_intelligence")
        if isinstance(intelligence, Mapping):
            return domain_graph_from_workstream(intelligence, row=row, proposal=proposal)
    return domain_graph_from_workstream({}, row=rows[0] if rows else {}, proposal=proposal)


def _domain_actor_names(graph: DomainIntelligenceGraph, *, proposal: Mapping[str, Any]) -> dict[str, str]:
    compact = _compact_lens_name(graph, proposal=proposal)
    proposal_actors = _proposal_actor_candidates(proposal)
    actors = _role_candidates([*proposal_actors, *graph.actors])
    first_path_actor = _first_path_contract_actor(proposal)
    operators = _role_specific_candidates(
        [*proposal_actors, *graph.operators, *graph.actors],
        ("operator", "ops", "workflow", "maintainer", "coordinator", "lead"),
        ownerish_fallback=False,
    )
    risk_owners = _role_specific_candidates(
        [*proposal_actors, *graph.risk_owners, *graph.actors],
        ("risk", "safety", "compliance", "loss"),
        ownerish_fallback=False,
    )
    evidence_owners = _role_specific_candidates(
        [*proposal_actors, *graph.evidence_types, *graph.proof_standards, *graph.actors],
        ("proof", "evidence", "validation"),
        ownerish_fallback=False,
    )
    implementation_owners = _role_specific_candidates(
        [*proposal_actors, *graph.invariants, *graph.validation_obligations, *graph.actors],
        ("build", "builder", "implementation", "source", "engineer"),
        ownerish_fallback=False,
    ) or _role_specific_candidates(
        [*proposal_actors, *graph.invariants, *graph.validation_obligations, *graph.actors],
        ("maintainer",),
        ownerish_fallback=False,
    )
    names = {
        "beneficiary_advocate": _actor_label(actors, fallback=f"{compact} beneficiary advocate"),
        "domain_operator": _actor_label(operators, fallback=first_path_actor or f"{compact} operator"),
        "risk_owner": _actor_label(risk_owners, fallback=f"{compact} risk reviewer"),
        "evidence_owner": _actor_label(
            evidence_owners,
            fallback=_derived_role_label(
                [*implementation_owners, *actors],
                explicit_tokens=("proof", "evidence", "validation"),
                fallback_lens=compact,
                role_suffix="proof reviewer",
            ),
        ),
        "implementation_owner": _actor_label(implementation_owners, fallback=f"{compact} build owner"),
        "release_owner": _derived_role_label(
            [
                *implementation_owners,
                *evidence_owners,
                *risk_owners,
                *operators,
                *actors,
            ],
            explicit_tokens=("release", "promotion", "readiness", "rollback", "launch", "delivery"),
            fallback_lens=compact,
            role_suffix="release reviewer",
        ),
    }
    return _dedupe_visible_actor_names(names)


def _first_path_contract_actor(proposal: Mapping[str, Any]) -> str:
    semantic_model = proposal.get("semantic_model")
    if not isinstance(semantic_model, Mapping):
        return ""
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return ""
    actor = _actor_candidate_label(clean_text(contract.get("actor")))
    return actor if actor and _looks_like_actor_label(actor) else ""


def _dedupe_visible_actor_names(names: Mapping[str, str]) -> dict[str, str]:
    """Keep visible Tribunal roles distinct even when one human owns many hats."""

    suffixes = {
        "beneficiary_advocate": "beneficiary advocate",
        "domain_operator": "workflow operator",
        "risk_owner": "risk reviewer",
        "evidence_owner": "proof reviewer",
        "implementation_owner": "build owner",
        "release_owner": "release reviewer",
    }
    result: dict[str, str] = {}
    seen: set[str] = set()
    for role in TRIBUNAL_STABLE_ROLES:
        label = clean_text(names.get(role, ""))
        key = label.casefold()
        if key and key in seen:
            prefix = _actor_label_prefix(label) or label
            suffix = suffixes.get(role, "reviewer")
            label = f"{prefix} {suffix}".strip()
            key = label.casefold()
        if key and key in seen:
            label = f"{label} for {role.replace('_', ' ')}"
            key = label.casefold()
        if key:
            seen.add(key)
        result[role] = label
    return result


def _proposal_actor_candidates(proposal: Mapping[str, Any]) -> tuple[str, ...]:
    """Prefer accepted project actors over internal role fallbacks."""

    values: list[str] = []
    for item in proposal.get("backlog", []):
        if not isinstance(item, Mapping):
            continue
        intelligence = item.get("domain_intelligence")
        if isinstance(intelligence, Mapping):
            values.extend(_actor_segments(intelligence.get("actors")))
    project = proposal.get("project_intelligence")
    if isinstance(project, Mapping):
        for key in ("actors", "owners", "operators"):
            values.extend(_actor_segments(project.get(key)))
    for item in proposal.get("backlog", []):
        if not isinstance(item, Mapping):
            continue
        values.extend(_actor_segments(item.get("customer")))
    return unique_text(_actor_candidate_label(value) for value in values if value)


def _actor_segments(value: Any) -> tuple[str, ...]:
    rows: list[str] = []
    for raw in text_values(value, split_scalar=True, strip_bullets=True):
        text = clean_text(raw).strip(" .")
        if not text:
            continue
        head, sep, tail = text.partition(":")
        if sep and "actor" in head.casefold() and tail.strip():
            text = tail.strip(" .")
        rows.extend(text_values(text, split_scalar=True, strip_bullets=True))
    return unique_text(rows)


def _actor_candidate_label(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    direct = accepted_actor_label(text)
    if direct and _looks_like_actor_label(direct):
        return direct
    for separator in (" \u2014 ", " \u2013 ", " - ", ":"):
        head, sep, _body = text.partition(separator)
        if sep and head.strip():
            text = head.strip(" .")
            break
    lowered = text.casefold()
    for marker in (
        " who ",
        " that ",
        " using ",
        " with ",
        " needing ",
        " responsible for ",
        " accountable for ",
        " receiving ",
        " reviewing ",
        " deciding ",
    ):
        head, sep, _tail = lowered.partition(marker)
        if sep and head.strip():
            text = text[: len(head)].strip(" .")
            break
    if len(text.split()) > 6:
        role_phrase = _role_phrase_label(text)
        if role_phrase:
            text = role_phrase
    normalized = accepted_actor_label(text)
    if normalized and _looks_like_actor_label(normalized):
        return normalized
    if clean_text(text).casefold() in {
        "primary user",
        "project operator",
        "domain reviewer",
        "workflow operator",
        "risk reviewer",
        "proof reviewer",
    }:
        return ""
    return text


def _looks_like_actor_label(value: str) -> bool:
    lowered = clean_text(value).casefold()
    if not lowered or lowered in {"evidence for this slice", "proof for this slice"}:
        return False
    if re.search(r"\b(?:runtime|product|system|workflow)\s+behavior\s+to\s+\w+\b", lowered):
        return False
    if re.search(r"\bto\s+(?:exercise|validate|verify|build|implement)\b", lowered):
        return False
    if re.search(
        r"\b(?:owns|must show|source of truth|proof evidence|validate|assemble|actors include|actors involved|review ownership follows)\b",
        lowered,
    ):
        return False
    if lowered.endswith((" proof record", " evidence record", " release gate")):
        return False
    role_words = {
        "admin",
        "administrator",
        "advocate",
        "analyst",
        "applicant",
        "approver",
        "auditor",
        "author",
        "beneficiary",
        "chair",
        "client",
        "coach",
        "coordinator",
        "customer",
        "editor",
        "engineer",
        "evaluator",
        "guardian",
        "inspector",
        "lead",
        "learner",
        "manager",
        "operator",
        "owner",
        "participant",
        "parent",
        "people",
        "person",
        "planner",
        "preparer",
        "recipient",
        "requester",
        "researcher",
        "reviewer",
        "specialist",
        "submitter",
        "support",
        "trainer",
        "user",
    }
    words = {word.strip(".,;:()") for word in lowered.split()}
    if words & role_words:
        return True
    tokens = [word.strip(".,;:()") for word in lowered.split() if word.strip(".,;:()")]
    if 1 <= len(tokens) <= 5 and any(re.search(r"(?:er|or|ist|ian|ant|ee)$", token) for token in tokens):
        return True
    return False


def _role_phrase_label(label: str) -> str:
    role_words = {
        "advocate",
        "builder",
        "coordinator",
        "engineer",
        "lead",
        "maintainer",
        "manufacturer",
        "operator",
        "owner",
        "reviewer",
        "user",
    }
    connectors = {"and", "or", "/", "&"}
    words = [word.strip(".,;:()") for word in clean_text(label).replace("/", " / ").split()]
    for index, word in enumerate(words):
        if word.casefold() not in role_words:
            continue
        start = index
        if index > 0 and words[index - 1].casefold() not in connectors:
            start = index - 1
        end = index + 1
        if (
            end + 1 < len(words)
            and words[end].casefold() in connectors
            and words[end + 1].casefold() in role_words
        ):
            end += 2
        phrase = " ".join(words[start:end]).strip()
        if phrase.casefold() in role_words:
            return ""
        return phrase
    return ""


def _compact_lens_name(graph: DomainIntelligenceGraph, *, proposal: Mapping[str, Any] | None = None) -> str:
    label = clean_text(graph.primary_lens).split(":", 1)[0].strip()
    if not label:
        return "Project"
    source_title = ""
    if isinstance(proposal, Mapping):
        intent = proposal.get("intent")
        if isinstance(intent, Mapping):
            source_title = clean_text(intent.get("title"))
        if not source_title:
            source_title = clean_text(proposal.get("title"))
    source_label = _source_title_lens(source_title)
    if source_label and _looks_like_role_lens(label):
        label = source_label
    words = label.replace("_", " ").split()
    text = " ".join(word[:1].upper() + word[1:] for word in words[:3])
    return restore_source_acronym_number_tokens(text, source_title or label)


def _looks_like_role_lens(value: str) -> bool:
    lowered = clean_text(value).casefold()
    return bool(re.search(r"\b(?:build|evidence|owner|proof|release|reviewer|risk|validation)\b", lowered))


def _source_title_lens(value: str) -> str:
    text = re.split(r"\s+[—–]\s+|:", clean_text(value), maxsplit=1)[0].strip(" .")
    return text


def _role_candidates(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for value in values:
        label = _actor_candidate_label(value)
        if label:
            rows.append(label)
    return unique_text(rows)


def _ownerish_candidates(values: Sequence[str]) -> list[str]:
    candidates = []
    for value in values:
        label = _actor_candidate_label(value)
        if not label:
            continue
        lowered = label.casefold()
        if any(token in lowered for token in ("owner", "reviewer", "operator", "maintainer", "lead")):
            candidates.append(label)
    return unique_text(candidates)


def _role_specific_candidates(
    values: Sequence[str],
    tokens: Sequence[str],
    *,
    ownerish_fallback: bool = True,
) -> list[str]:
    candidates = []
    for value in values:
        source = clean_text(value)
        label = _actor_candidate_label(source)
        if not label:
            continue
        lowered = source.casefold()
        if any(token in lowered for token in tokens):
            candidates.append(label)
    return unique_text(candidates) or (_ownerish_candidates(values) if ownerish_fallback else [])


def _derived_role_label(
    values: Sequence[str],
    *,
    explicit_tokens: Sequence[str],
    fallback_lens: str,
    role_suffix: str,
) -> str:
    explicit = _role_specific_candidates(values, explicit_tokens, ownerish_fallback=False)
    label = _actor_label(explicit, fallback="")
    if label:
        return label
    return f"{fallback_lens} {role_suffix}"


def _actor_label_prefix(label: str) -> str:
    text = clean_text(label).strip(" .")
    if not text:
        return ""
    role_words = {
        "advocate",
        "beneficiary",
        "builder",
        "coordinator",
        "engineer",
        "lead",
        "maintainer",
        "manufacturer",
        "operator",
        "owner",
        "reviewer",
        "team",
        "user",
    }
    words = text.replace("/", " ").split()
    while words and words[-1].strip(".,;:()").casefold() in role_words:
        words.pop()
    return " ".join(words[:4]).strip()


def _actor_label(values: Sequence[str], *, fallback: str) -> str:
    for value in values:
        label = clean_text(value)
        if (
            label
            and _looks_like_actor_label(label)
            and label.casefold()
            not in {
                "actor",
                "actors",
                "human actors",
                "main human actors",
                "maintainer",
                "owner",
                "reviewer",
                "state object",
                "team",
                "user",
                "evidence record",
                "evidence for this slice",
                "release gate",
                "the first-release actors are",
                "actors involved in the first release are",
                "build owner",
                "domain operator",
                "evidence owner",
                "implementation owner",
                "proof owner",
                "proof for this slice",
                "proof reviewer",
                "release owner",
                "release reviewer",
                "result reviewer",
                "risk owner",
                "risk reviewer",
                "workflow operator",
                "check",
                "confirm",
                "prove",
                "review",
                "test",
                "validate",
                "verify",
            }
            and len(label.split()) <= 14
        ):
            return _normalize_role_suffix_case(label)
    return fallback


def _normalize_role_suffix_case(label: str) -> str:
    text = clean_text(label)
    suffixes = (
        "Beneficiary Advocate",
        "Workflow Operator",
        "Risk Reviewer",
        "Proof Reviewer",
        "Build Owner",
        "Release Reviewer",
    )
    for suffix in suffixes:
        if text.endswith(suffix):
            return f"{text[: -len(suffix)]}{suffix.casefold()}"
    return text


__all__ = ["TRIBUNAL_STABLE_ROLES", "tribunal_actor_projection"]
