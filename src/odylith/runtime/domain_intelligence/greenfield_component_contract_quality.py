"""Quality gates for generated greenfield component contracts and specs."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


CONTRACT_KEYS = (
    "owned_state",
    "accepted_inputs",
    "produced_outputs",
    "states_or_transitions",
    "outside_boundary",
    "local_proof",
    "upstream_truth",
    "downstream_consumers",
    "unique_failure",
)

_BANNED_PROSE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "repeated responsibility template",
        re.compile(r"\bowns\s+the\s+.+?\s+responsibility\s+and\s+keeps\s+it\s+tied\b", re.IGNORECASE),
    ),
    ("bad capitalized object splice", re.compile(r"\binspect\s+The\b")),
    ("actor heading leaked into field", re.compile(r"\bHuman\s+actors\s*:", re.IGNORECASE)),
    ("summary elision leaked into governed record", re.compile(r"\bplus\s+\d+\s+more\b", re.IGNORECASE)),
    ("clipped required-doc phrase", re.compile(r"\bwith\s+clear\s+ownership,\s+protected\s+access,\s+required\b", re.IGNORECASE)),
    ("sentence connector splice", re.compile(r"\.\s+(?:and|or)\b", re.IGNORECASE)),
    (
        "full-sentence path spliced after infinitive",
        re.compile(
            r"\bto\s+complete\s+(?:a|an|the)\s+(?!accepted\s+first\s+path\b)[a-z][^,.;!?]*"
            r"\b(?:creates?|submits?|moves?|records?|opens?|uploads?|reviews?|chooses?|sends?|tracks?|generates?|"
            r"receives?|accepts?|declines?|requests?|schedules?|completes?|imports?|exports?|shows?|runs?|files?|approves?|rejects?)\b",
            re.IGNORECASE,
        ),
    ),
    ("dangling path clause", re.compile(r"\bwhen\s+the\s+path\s+is\s*\.", re.IGNORECASE)),
    ("bad capitalized proof splice", re.compile(r"\bverifies\s+that\s+The\b")),
    ("bad proof status splice", re.compile(r"\bshows\s+whether\s+The\b")),
    ("bad state inspection splice", re.compile(r"\binspect\s+(?:the\s+)?(?:core\s+)?state\s+is\b", re.IGNORECASE)),
    ("malformed verb pair", re.compile(r"\b(?:preserves\s+handles|maintains\s+defines)\b", re.IGNORECASE)),
    ("doubled refusal phrase", re.compile(r"\brefuses\b[^.]{0,140}\brefuses\b", re.IGNORECASE)),
    ("clipped scoring fragment", re.compile(r"\bscor\b", re.IGNORECASE)),
    ("clipped eligibility phrase", re.compile(r"\baccepting\s+eligible\b", re.IGNORECASE)),
)

_DANGLING_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "of",
    "or",
    "the",
    "to",
    "with",
}

_STRUCTURAL_TERMS = {
    "accepted",
    "actor",
    "application",
    "boundary",
    "candidate",
    "change",
    "component",
    "contract",
    "current",
    "detail",
    "evidence",
    "field",
    "first",
    "greenfield",
    "handoff",
    "handle",
    "implementation",
    "input",
    "local",
    "normal",
    "operator",
    "output",
    "owner",
    "planned",
    "product",
    "behavior",
    "prove",
    "service",
    "proof",
    "record",
    "release",
    "review",
    "reviewer",
    "source",
    "state",
    "status",
    "system",
    "technical",
    "traceable",
    "traced",
    "validation",
    "workstream",
}

_TERM_STOPWORDS = _STRUCTURAL_TERMS | {
    "about",
    "after",
    "also",
    "before",
    "between",
    "does",
    "each",
    "into",
    "must",
    "that",
    "this",
    "when",
    "where",
    "which",
    "while",
    "without",
}


def normalize_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a component contract into sentence-shaped public text."""

    normalized: dict[str, Any] = {}
    for key in CONTRACT_KEYS:
        raw = value.get(key)
        if key == "local_proof":
            normalized[key] = [_sentence(item) for item in text_values(raw) if _clean(item)]
        else:
            normalized[key] = _sentence(_clean(raw))
    return normalized


def contract_is_complete(value: Mapping[str, Any]) -> bool:
    """Return whether every component contract field has usable text."""

    return all(text_values(value.get(key)) for key in CONTRACT_KEYS)


def component_contract_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Return proposal-level failures for component contracts and public prose."""

    issues: list[str] = []
    components = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    require_contracts = _requires_component_contracts(proposal)
    for index, row in enumerate(components, start=1):
        label = _label(row) or f"component {index}"
        contract = row.get("component_contract")
        if not isinstance(contract, Mapping):
            if require_contracts:
                issues.append(f"component row {index} `{label}` is missing component_contract")
            continue
        normalized = normalize_contract(contract)
        for key in CONTRACT_KEYS:
            values = text_values(normalized.get(key))
            if not values:
                issues.append(f"component row {index} `{label}` component_contract.{key} is empty")
        terms = domain_terms(" ".join(text_values(normalized)))
        if len(terms) < 8:
            issues.append(f"component row {index} `{label}` component_contract is too generic to guide implementation")
    issues.extend(public_prose_quality_issues(proposal))
    return dedupe_text(issues)


def public_prose_quality_issues(value: Any) -> list[str]:
    """Catch malformed generated prose before it becomes governed truth."""

    issues: list[str] = []
    for path, text in _text_leaves(value):
        if _is_path_excluded(path):
            continue
        for label, pattern in _BANNED_PROSE_PATTERNS:
            if pattern.search(text):
                issues.append(f"generated prose uses {label} at {path}")
        if _has_dangling_tail(text):
            issues.append(f"generated prose appears clipped or unfinished at {path}")
    return dedupe_text(issues)


def rendered_component_spec_quality_issues(
    specs: Mapping[str, str],
    *,
    project_title: str = "",
    max_overlap: float = 0.65,
) -> list[str]:
    """Fail generic Registry specs whose content survives component-name swaps."""

    issues: list[str] = []
    names = tuple(specs.keys())
    all_name_terms = _name_terms(names)
    normalized_lines = {
        name: _normalized_spec_lines(text, project_title=project_title, names=names)
        for name, text in specs.items()
    }
    for name, text in specs.items():
        for issue in public_prose_quality_issues(text):
            issues.append(f"`{name}` {issue}")
        local_terms = _local_domain_terms(
            text,
            all_texts=tuple(specs.values()),
            names=names,
            all_name_terms=all_name_terms,
        )
        if len(local_terms) < 4:
            issues.append(f"component spec `{name}` does not contain at least four component-local domain terms")
    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            left_lines = normalized_lines[left_name]
            right_lines = normalized_lines[right_name]
            if not left_lines or not right_lines:
                continue
            overlap = len(left_lines & right_lines) / max(1, min(len(left_lines), len(right_lines)))
            if overlap > max_overlap:
                issues.append(
                    f"component specs `{left_name}` and `{right_name}` are too interchangeable after masking names "
                    f"({overlap:.2f} line overlap)"
                )
    return dedupe_text(issues)


def ordered_domain_terms(text: str) -> list[str]:
    """Return stable, non-structural terms suitable for component-local prose."""

    result: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _clean(text).casefold()):
        token = _term_token(raw)
        if token and token not in seen:
            seen.add(token)
            result.append(token)
    return result


def domain_terms(text: str) -> set[str]:
    """Return normalized, non-structural terms from public component prose."""

    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _clean(text).casefold()):
        token = _term_token(raw)
        if token:
            terms.add(token)
    return terms


def dedupe_text(values: Sequence[str]) -> list[str]:
    """Return text values with order preserved and empty rows removed."""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _requires_component_contracts(proposal: Mapping[str, Any]) -> bool:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    if str(intent.get("reasoning_mode", "")).strip() == "odylith_confirmed_governed_proposal":
        return True
    return any(isinstance(row, Mapping) and isinstance(row.get("component_contract"), Mapping) for row in proposal.get("components", []))


def _text_leaves(value: Any, *, path: tuple[str, ...] = ()) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        rows: list[tuple[str, str]] = []
        for key, nested in value.items():
            rows.extend(_text_leaves(nested, path=(*path, str(key))))
        return tuple(rows)
    if isinstance(value, (list, tuple, set)):
        rows = []
        for index, nested in enumerate(value):
            rows.extend(_text_leaves(nested, path=(*path, str(index))))
        return tuple(rows)
    text = _clean(value)
    return ((".".join(path) or "<root>", text),) if text else ()


def _is_path_excluded(path: str) -> bool:
    lowered = path.casefold()
    return any(
        lowered.endswith(suffix)
        for suffix in (
            "_id",
            "_ids",
            "_path",
            "_paths",
            "_slug",
            "_slugs",
            "component_id",
            "diagram_id",
            "source_mmd",
            "source_png",
            "source_svg",
        )
    )


def _normalized_spec_lines(text: str, *, project_title: str, names: Sequence[str]) -> set[str]:
    lines: set[str] = set()
    for raw in str(text or "").splitlines():
        line = _clean(raw)
        if not _substantive_spec_line(line):
            continue
        masked = _mask_spec_line(line, project_title=project_title, names=names)
        if masked:
            lines.add(masked)
    return lines


def _substantive_spec_line(line: str) -> bool:
    if not line or line.startswith("#") or line.startswith("|") or line.startswith("- `./.odylith"):
        return False
    if line in {"### Owns", "### Outside Boundary", "### Collaborators And Dependencies", "### Definition Of Done", "### Operator Verification"}:
        return False
    return len(domain_terms(line)) >= 4


def _mask_spec_line(line: str, *, project_title: str, names: Sequence[str]) -> str:
    masked = line.casefold()
    for name in [project_title, *names]:
        for token in _name_variants(name):
            if token:
                masked = masked.replace(token, "<name>")
    masked = re.sub(r"\bB-\d+\b", "<workstream>", masked, flags=re.IGNORECASE)
    masked = re.sub(r"\bD-\d+\b", "<diagram>", masked, flags=re.IGNORECASE)
    masked = re.sub(r"\brelease\s+\d+(?:\.\d+){1,2}\b", "release <version>", masked)
    masked = re.sub(r"`[^`]+`", "<path>", masked)
    masked = re.sub(r"src/[a-z0-9_/-]+", "<path>", masked)
    masked = re.sub(r"\s+", " ", masked).strip(" .")
    return masked


def _name_variants(name: str) -> tuple[str, ...]:
    text = _clean(name).casefold()
    slug = slugify(text)
    return tuple(unique_text([text, slug, slug.replace("-", " "), slug.replace("-", "_")]))


def _name_terms(names: Sequence[str]) -> set[str]:
    terms: set[str] = set()
    for name in names:
        terms.update(domain_terms(name))
    return terms


def _local_domain_terms(
    text: str,
    *,
    all_texts: Sequence[str],
    names: Sequence[str],
    all_name_terms: set[str],
) -> set[str]:
    terms = domain_terms(text) - all_name_terms
    counts: dict[str, int] = {}
    for candidate in terms:
        counts[candidate] = sum(1 for body in all_texts if candidate in domain_terms(body))
    majority = max(1, len(all_texts) // 2)
    return {term for term in terms if counts.get(term, 0) <= majority and term not in _TERM_STOPWORDS}


def _label(row: Mapping[str, Any]) -> str:
    return _clean(row.get("label")) or _clean(row.get("name")) or _clean(row.get("component_id")) or "Component"


def _has_dangling_tail(value: str) -> bool:
    text = _clean(value)
    if len(text.split()) < 6:
        return False
    tail = text.rstrip(".;:, ").split()[-1].casefold()
    return tail in _DANGLING_WORDS


def _term_token(value: str) -> str:
    token = value.strip("-_")
    if len(token) < 4 or token in _TERM_STOPWORDS:
        return ""
    if token.endswith("ies") and len(token) > 5:
        token = f"{token[:-3]}y"
    elif token.endswith("ing") and len(token) > 6:
        token = token[:-3]
    elif token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
        token = token[:-1]
    return token if token not in _TERM_STOPWORDS else ""


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _sentence(value: Any) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    return text[:1].upper() + text[1:] + "."


__all__ = [
    "CONTRACT_KEYS",
    "component_contract_issues",
    "contract_is_complete",
    "dedupe_text",
    "domain_terms",
    "normalize_contract",
    "ordered_domain_terms",
    "public_prose_quality_issues",
    "rendered_component_spec_quality_issues",
]
