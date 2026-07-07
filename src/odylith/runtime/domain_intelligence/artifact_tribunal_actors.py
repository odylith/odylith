"""Visible Tribunal actor projection from Domain Intelligence graphs."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.artifact_graph import DomainIntelligenceGraph
from odylith.runtime.domain_intelligence.artifact_graph import domain_graph_from_workstream
from odylith.runtime.domain_intelligence.greenfield_actor_labels import accepted_actor_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import restore_source_acronym_number_tokens
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import restore_source_token_casing
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label
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

TRIBUNAL_JUDGMENT_ROLES = (
    "beneficiary_advocate",
    "domain_operator",
    "risk_owner",
    "evidence_owner",
)

_JUDGMENT_ROLE_SUFFIXES = {
    "beneficiary_advocate": ("beneficiary advocate",),
    "domain_operator": ("workflow operator",),
    "risk_owner": ("risk reviewer", "safety reviewer", "compliance reviewer"),
    "evidence_owner": ("proof reviewer", "evidence reviewer", "audit reviewer", "auditor", "evidence owner"),
}
_JUDGMENT_ROLE_REPAIR_SUFFIX = {
    "beneficiary_advocate": "beneficiary advocate",
    "domain_operator": "workflow operator",
    "risk_owner": "risk reviewer",
    "evidence_owner": "proof reviewer",
}

_GENERIC_ACTOR_ROLE_LABELS = {
    "actor",
    "actors",
    "beneficiary advocate",
    "build owner",
    "domain operator",
    "domain reviewer",
    "evidence owner",
    "human actors",
    "implementation owner",
    "main human actors",
    "maintainer",
    "owner",
    "primary user",
    "project operator",
    "proof owner",
    "proof reviewer",
    "release owner",
    "release reviewer",
    "result reviewer",
    "reviewer",
    "risk owner",
    "risk reviewer",
    "state object",
    "team",
    "user",
    "workflow operator",
}


def tribunal_actor_projection(proposal: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Return domain-specific visible Tribunal actors for a proposal."""

    first_graph = _first_domain_graph(proposal)
    actor_names = _domain_actor_names(first_graph, proposal=proposal)
    explicit_actor_label_keys = _explicit_actor_label_keys(proposal)
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
            "actor_source": "explicit_intent_actor"
            if _label_key(actor_names[role]) in explicit_actor_label_keys
            else "generated_role_projection",
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
    explicit_actor_label_keys = _explicit_actor_label_keys(proposal)
    actors = _role_candidates([*proposal_actors, *graph.actors])
    actor_pool = actors or _role_candidates(proposal_actors)
    first_path_actor = _first_path_contract_actor(proposal)
    operators = unique_text(
        [
            *_role_specific_candidates(
                [*proposal_actors, *graph.operators, *graph.actors],
                ("operator", "ops", "workflow", "maintainer", "coordinator", "lead"),
                ownerish_fallback=False,
            ),
            *_role_candidates(graph.operators),
        ]
    )
    risk_owners = _role_specific_candidates(
        [*proposal_actors, *graph.risk_owners, *graph.actors],
        ("risk", "safety", "compliance", "loss"),
        ownerish_fallback=False,
    )
    evidence_owners = _role_specific_candidates(
        [*proposal_actors, *graph.actors],
        ("proof", "evidence", "validation", "audit", "auditor"),
        ownerish_fallback=False,
    ) or _role_specific_candidates(
        [*proposal_actors, *graph.actors],
        ("reviewer", "inspector", "analyst"),
        ownerish_fallback=False,
    )
    implementation_owners = _role_specific_candidates(
        proposal_actors,
        ("build", "builder", "implementation", "source", "engineer"),
        ownerish_fallback=False,
    ) or _role_specific_candidates(
        proposal_actors,
        ("maintainer",),
        ownerish_fallback=False,
    )
    primary_actor = _actor_label(actor_pool, fallback=first_path_actor or f"{compact} beneficiary advocate")
    operator_fallback_lens = _actor_label_prefix(primary_actor) or compact
    judgment_fallback_lens = (
        _actor_label_prefix(primary_actor)
        if _incompatible_judgment_role_suffix(label=primary_actor, role="beneficiary_advocate")
        else compact
    )
    domain_operator = _actor_label(
        operators,
        fallback=_best_role_actor(
            actor_pool,
            ("operator", "coordinator", "lead", "dispatcher", "liaison", "manager", "officer"),
            fallback=_role_suffixed_label(operator_fallback_lens, _JUDGMENT_ROLE_REPAIR_SUFFIX["domain_operator"]),
        ),
    )
    names = {
        "beneficiary_advocate": primary_actor,
        "domain_operator": domain_operator,
        "risk_owner": _actor_label(
            risk_owners,
            fallback=_best_role_actor(
                actor_pool,
                ("commander", "chief", "director", "authority", "risk", "safety", "compliance", "security", "privacy", "manager", "owner", "officer", "lead"),
                fallback=_role_suffixed_label(judgment_fallback_lens, _JUDGMENT_ROLE_REPAIR_SUFFIX["risk_owner"]),
            ),
        ),
        "evidence_owner": _actor_label(
            evidence_owners,
            fallback=_best_role_actor(
                actor_pool,
                ("commander", "proof", "evidence", "validation", "audit", "auditor", "inspector", "reviewer", "analyst", "information", "officer"),
                fallback=_role_suffixed_label(compact, _JUDGMENT_ROLE_REPAIR_SUFFIX["evidence_owner"]),
            ),
        ),
        "implementation_owner": _actor_label(implementation_owners, fallback="Project implementation owner"),
        "release_owner": _actor_label(
            _role_specific_candidates(
                [
                    *proposal_actors,
                    *implementation_owners,
                    *evidence_owners,
                    *risk_owners,
                    *operators,
                    *actors,
                ],
                ("release", "promotion", "readiness", "rollback", "launch", "delivery"),
                ownerish_fallback=False,
            ),
            fallback=_best_role_actor(
                actor_pool,
                ("commander", "chief", "director", "release", "promotion", "rollback", "launch", "delivery", "manager", "owner", "readiness", "lead"),
                fallback="Project release owner",
            ),
        ),
    }
    return _dedupe_visible_actor_names(names, explicit_actor_label_keys=explicit_actor_label_keys)


def _first_path_contract_actor(proposal: Mapping[str, Any]) -> str:
    semantic_model = proposal.get("semantic_model")
    if not isinstance(semantic_model, Mapping):
        return ""
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return ""
    actor = _actor_candidate_label(clean_text(contract.get("actor")))
    return actor if actor and _looks_like_actor_label(actor) else ""


def _explicit_actor_label_keys(proposal: Mapping[str, Any]) -> set[str]:
    """Return actor labels grounded directly in accepted intent, not role fallback text."""

    labels = list(_proposal_actor_candidates(proposal))
    first_path_actor = _first_path_contract_actor(proposal)
    if first_path_actor:
        labels.append(first_path_actor)
    return {_label_key(label) for label in labels if clean_text(label)}


def _dedupe_visible_actor_names(
    names: Mapping[str, str],
    *,
    explicit_actor_label_keys: set[str],
) -> dict[str, str]:
    """Keep intentional shared actors while separating generated judgment roles."""

    result: dict[str, str] = {}
    seen_judgment_labels: set[str] = set()
    for role in TRIBUNAL_STABLE_ROLES:
        label = clean_text(names.get(role, ""))
        if role in TRIBUNAL_JUDGMENT_ROLES:
            label = _role_specific_judgment_label(
                role=role,
                label=label,
                seen_labels=seen_judgment_labels,
                explicit_actor_label_keys=explicit_actor_label_keys,
            )
            seen_judgment_labels.add(_label_key(label))
        result[role] = label
    return result


def _role_specific_judgment_label(
    *,
    role: str,
    label: str,
    seen_labels: set[str],
    explicit_actor_label_keys: set[str],
) -> str:
    text = clean_text(label).strip(" .")
    if not text:
        return _role_suffixed_label("Project", _JUDGMENT_ROLE_REPAIR_SUFFIX[role])
    key = _label_key(text)
    if (
        key in explicit_actor_label_keys
        and _can_keep_explicit_actor_for_role(label=text, role=role)
        and (key not in seen_labels or role == "domain_operator")
    ):
        return text
    if (
        _incompatible_judgment_role_suffix(label=text, role=role)
        or key in seen_labels
        or not _compatible_judgment_role_suffix(label=text, role=role)
    ):
        base = _actor_label_prefix(text) or text
        text = _role_suffixed_label(base, _JUDGMENT_ROLE_REPAIR_SUFFIX[role])
    return text


def tribunal_visible_actor_quality_issues(
    visible_actors: Sequence[Mapping[str, str]],
) -> tuple[str, ...]:
    """Return quality issues for visible Tribunal role projections."""

    role_to_row = {
        str(row.get("stable_role", "")).strip(): row
        for row in visible_actors
        if isinstance(row, Mapping)
    }
    role_to_label = {
        role: clean_text(row.get("visible_actor", "")).strip()
        for role, row in role_to_row.items()
    }
    issues: list[str] = []
    label_roles: dict[str, list[str]] = {}
    for role in TRIBUNAL_JUDGMENT_ROLES:
        label = role_to_label.get(role, "")
        if not label:
            issues.append(f"Tribunal visible actor missing for {role}")
            continue
        key = _label_key(label)
        label_roles.setdefault(key, []).append(role)
        incompatible = _incompatible_judgment_role_suffix(label=label, role=role)
        shared_explicit_actor = _allows_shared_explicit_actor(role_to_row.get(role), label=label)
        if incompatible and not shared_explicit_actor:
            issues.append(
                f"Tribunal visible actor for {role} uses {incompatible} role language: {label}"
            )
        if not shared_explicit_actor and not _compatible_judgment_role_suffix(label=label, role=role):
            issues.append(
                f"Tribunal generated visible actor for {role} lacks role-specific judgment language: {label}"
            )
    for roles in label_roles.values():
        if len(roles) <= 1:
            continue
        label = role_to_label.get(roles[0], "")
        if _allows_shared_explicit_judgment_overlap(roles=roles, role_to_row=role_to_row, label=label):
            continue
        issues.append(
            "Tribunal visible actors collapse distinct judgment roles "
            + ", ".join(roles)
            + f" into {label}"
        )
    return tuple(dict.fromkeys(issues))


def _allows_shared_explicit_actor(row: Mapping[str, Any] | None, *, label: str) -> bool:
    if not isinstance(row, Mapping):
        return False
    return (
        clean_text(row.get("actor_source")).casefold() == "explicit_intent_actor"
        and _can_be_shared_explicit_actor_label(label)
    )


def _allows_shared_explicit_judgment_overlap(
    *,
    roles: Sequence[str],
    role_to_row: Mapping[str, Mapping[str, Any]],
    label: str,
) -> bool:
    role_set = set(roles)
    if len(role_set) > 2:
        return False
    if not role_set <= {"beneficiary_advocate", "domain_operator"}:
        return False
    return all(_allows_shared_explicit_actor(role_to_row.get(role), label=label) for role in role_set)


def _can_be_shared_explicit_actor_label(label: str) -> bool:
    text = clean_text(label).strip(" .")
    lowered = text.casefold()
    if not text:
        return False
    if _incompatible_shared_explicit_label(lowered):
        return False
    return _looks_like_actor_label(text)


def _can_keep_explicit_actor_for_role(*, label: str, role: str) -> bool:
    text = clean_text(label).strip(" .")
    lowered = text.casefold()
    if not text:
        return False
    if _incompatible_shared_explicit_label(lowered):
        return False
    if _incompatible_judgment_role_suffix(label=text, role=role):
        return False
    if _compatible_judgment_role_suffix(label=text, role=role):
        return True
    if role in {"beneficiary_advocate", "domain_operator"} and _looks_like_actor_label(text):
        return True
    return False


def _incompatible_shared_explicit_label(lowered: str) -> bool:
    if any(
        token in lowered
        for token in (
            "proof reviewer",
            "evidence reviewer",
            "risk reviewer",
            "workflow operator",
            "beneficiary advocate",
            "release owner",
            "implementation owner",
            "system",
            "platform",
            "workspace",
            "service",
            "ledger",
            "board",
        )
    ):
        return True
    return False


def _label_key(value: str) -> str:
    return clean_text(value).casefold()


def _incompatible_judgment_role_suffix(*, label: str, role: str) -> str:
    lowered = clean_text(label).casefold()
    for other_role, suffixes in _JUDGMENT_ROLE_SUFFIXES.items():
        if other_role == role:
            continue
        if any(lowered == suffix or lowered.endswith(f" {suffix}") for suffix in suffixes):
            return other_role
    return ""


def _compatible_judgment_role_suffix(*, label: str, role: str) -> bool:
    lowered = clean_text(label).casefold()
    return any(
        lowered == suffix or lowered.endswith(f" {suffix}")
        for suffix in _JUDGMENT_ROLE_SUFFIXES.get(role, ())
    )


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
    if _looks_like_actor_list_bundle(text):
        return ""
    if _is_generic_actor_role_label(text):
        return ""
    direct = accepted_actor_label(text)
    if _is_generic_actor_role_label(direct):
        return ""
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
    if _is_generic_actor_role_label(normalized):
        return ""
    if normalized and _looks_like_actor_label(normalized):
        return normalized
    if _is_generic_actor_role_label(text):
        return ""
    return text if _looks_like_actor_label(text) else ""


def _is_generic_actor_role_label(value: str) -> bool:
    return clean_text(value).casefold().replace("_", " ") in _GENERIC_ACTOR_ROLE_LABELS


def _looks_like_actor_list_bundle(value: str) -> bool:
    text = clean_text(value).strip(" .")
    if "," not in text and ";" not in text:
        return False
    pieces = [piece.strip(" .") for piece in re.split(r"[,;]", text) if piece.strip(" .")]
    if len(pieces) < 2:
        return False
    actorish = [piece for piece in pieces if accepted_actor_label(piece) and _looks_like_actor_label(piece)]
    return len(actorish) >= 2


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
    if "evidence tier" in lowered or "invalidation trigger" in lowered:
        return False
    if " row " in f" {lowered} " and "names the owner" in lowered:
        return False
    if lowered.endswith((" proof", " proof record", " evidence", " evidence record", " validation", " release gate")):
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
        "resident",
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
    if 2 <= len(tokens) <= 5 and any(re.search(r"(?:er|or|ist|ian|ant|ee)$", token) for token in tokens):
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
    text = title_label(" ".join(words[:3]))
    return restore_source_token_casing(restore_source_acronym_number_tokens(text, source_title or label), source_title or label)


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


def _best_role_actor(values: Sequence[str], role_terms: Sequence[str], *, fallback: str) -> str:
    weights = {term.casefold(): len(role_terms) - index for index, term in enumerate(role_terms) if term}
    ranked: list[tuple[int, str]] = []
    for value in values:
        label = _actor_candidate_label(value)
        if not label:
            continue
        tokens = _actor_affinity_tokens(f"{value} {label}")
        score = sum(weight for token, weight in weights.items() if token in tokens)
        if score:
            ranked.append((score, label))
    if not ranked:
        return fallback
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def _actor_affinity_tokens(value: str) -> set[str]:
    return {
        token.strip(".,;:()[]{}").casefold()
        for token in clean_text(value).replace("-", " ").replace("/", " ").split()
        if token.strip(".,;:()[]{}")
    }


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
    return _role_suffixed_label(fallback_lens, role_suffix)


def _role_suffixed_label(prefix: str, suffix: str) -> str:
    label = clean_text(prefix).strip(" .")
    role_suffix = clean_text(suffix).strip(" .")
    if not label:
        return role_suffix
    if not role_suffix:
        return label
    lowered = label.casefold()
    suffix_lowered = role_suffix.casefold()
    if lowered.endswith(suffix_lowered):
        return label
    first, _separator, rest = role_suffix.partition(" ")
    if first and lowered.endswith(f" {first.casefold()}") and rest:
        return f"{label} {rest}".strip()
    return f"{label} {role_suffix}".strip()


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
        "proof",
        "reviewer",
        "risk",
        "team",
        "user",
        "workflow",
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
            and not _is_generic_actor_role_label(label)
            and label.casefold()
            not in {
                "evidence record",
                "evidence for this slice",
                "release gate",
                "the first-release actors are",
                "actors involved in the first release are",
                "proof for this slice",
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


__all__ = [
    "TRIBUNAL_JUDGMENT_ROLES",
    "TRIBUNAL_STABLE_ROLES",
    "tribunal_actor_projection",
    "tribunal_visible_actor_quality_issues",
]
