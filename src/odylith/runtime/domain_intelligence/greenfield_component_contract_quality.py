"""Quality gates for generated greenfield component contracts and specs."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_component_term_index import TERM_STOPWORDS
from odylith.runtime.domain_intelligence.greenfield_component_term_index import ordered_domain_terms
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
    ("bad proof boundary splice", re.compile(r"\bchecks\s+(?:A|An|The)\s+(?:first\s+release|release|proof|accepted)\b")),
    ("bad path proof splice", re.compile(r"\bexercises\s+(?:A|An|The)\s+.+?\s+and\s+checks\s+(?:A|An|The)\b")),
    ("bad state inspection splice", re.compile(r"\binspect\s+(?:the\s+)?(?:core\s+)?state\s+is\b", re.IGNORECASE)),
    ("malformed verb pair", re.compile(r"\b(?:preserves\s+handles|maintains\s+defines)\b", re.IGNORECASE)),
    ("malformed ownership verb pair", re.compile(r"\bowns\s+maintains\b", re.IGNORECASE)),
    ("malformed prevents/can clause", re.compile(r"\bprevents\s+[^.]{1,120}\bcan\s+\w+", re.IGNORECASE)),
    ("provisional title qualifier", re.compile(r"(?:[\(\[]\s*)?(?:working\s+title|placeholder\s+title|title\s+tbd|tbd)(?:\s*[\)\]])?", re.IGNORECASE)),
    ("token-soup proof phrase", re.compile(r"\bdone,\s*path,\s*mean,\s*person,\s*create,\s*view,\s*edit\b", re.IGNORECASE)),
    ("mechanical first-action scaffold", re.compile(r"\bfirst\s+accepted\s+action\b", re.IGNORECASE)),
    ("mechanical first-path-entry scaffold", re.compile(r"\bfirst\s+path\s+entry\b", re.IGNORECASE)),
    ("mechanical actor-path scaffold", re.compile(r"\bcan\s+act\s+where\s+the\s+accepted\s+path\s+requires\b", re.IGNORECASE)),
    ("generic local-output scaffold", re.compile(r"\bexpected\s+local\s+output\s*:", re.IGNORECASE)),
    ("malformed ownership sentence", re.compile(r"\bit\s+owns\s+for\b", re.IGNORECASE)),
    ("malformed ownership sentence", re.compile(r"\bit\s+owns\s+the\s+central\s+object\s+is\b", re.IGNORECASE)),
    ("duplicated evidence word", re.compile(r"\bevidence\s+evidence\b", re.IGNORECASE)),
    ("clipped out-of-scope sentence", re.compile(r"\bmulti-user\s+roles\s+are\s*[.]?$", re.IGNORECASE)),
    (
        "handoff verb leaked as artifact noun",
        re.compile(r"\bhand\s+[a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,4}\s+(?:identity|state|evidence|result|record)\b", re.IGNORECASE),
    ),
    ("dangling close-parenthesis token", re.compile(r"\b[a-z][a-z-]*\b(?:metrics?|state|input|output|record|proof)[)](?:\s|[.,;:]|$)", re.IGNORECASE)),
    ("clipped later phrase", re.compile(r"\bas\s+a\s+later\s*[.]?$", re.IGNORECASE)),
    ("clipped stale transition", re.compile(r"\bvalid\s+transition\s+display,\s*stale\s*[.]?$", re.IGNORECASE)),
    ("clipped evidence phrase", re.compile(r"\brejected\s+or\s+blocked\s+cases,\s*evidence\s*[.]?$", re.IGNORECASE)),
    ("doubled refusal phrase", re.compile(r"\brefuses\b[^.]{0,140}\brefuses\b", re.IGNORECASE)),
    ("clipped scoring fragment", re.compile(r"\bscor(?:[\s.,;:!?]|$)", re.IGNORECASE)),
    ("clipped eligibility phrase", re.compile(r"\baccepting\s+eligible\b", re.IGNORECASE)),
    ("clipped product fragment", re.compile(r"\bwithout\s+the\s+prod(?:[\s.,;:!?]|$)", re.IGNORECASE)),
    ("raw proof target splice", re.compile(r"\bproof\s+target\s+is\s+(?:A|An|The)\s+first\s+release\b")),
    ("generic input-output filler", re.compile(r"\binputs\s+and\s+produced\s+outputs\b", re.IGNORECASE)),
    ("generic accepted-path actor filler", re.compile(r"\bsupports\s+the\s+accepted\s+path\b", re.IGNORECASE)),
    (
        "generic governance posture filler",
        re.compile(
            r"\b(?:user\s+path,\s+state,\s+evidence,\s+decision,\s+and\s+follow-up|"
            r"entry,\s+actions,\s+feedback,\s+and\s+handoff|"
            r"state\s+profile,\s+the\s+first-path\s+outcome,\s+visible\s+blockers,\s+risk\s+posture)\b",
            re.IGNORECASE,
        ),
    ),
    ("accepted-items summary leaked", re.compile(r"\badditional\s+accepted\s+(?:items|systems)\s+remain\s+in\s+the\s+intent\b", re.IGNORECASE)),
    (
        "check-in tracking misread as checklist",
        re.compile(r"\b(?:owns|maintains|accepts|produces|recorded)\s+and\s+check\b", re.IGNORECASE),
    ),
    ("dangling weak sentence", re.compile(r"\bIt\s+should\s*[.]?$", re.IGNORECASE)),
    ("clipped proof clause", re.compile(r"\bby\s+accepting\s*[.]?$", re.IGNORECASE)),
    ("missing sentence boundary before proof obligation", re.compile(r"(?<![.!?])\s+Its\s+proof\s+obligation\b")),
    (
        "missing object after quantified action",
        re.compile(
            r"\b(?:receives?|gets?|shows?|produces?|records?|exports?|deletes?)\s+"
            r"(?:at\s+least|at\s+most|exactly)\s+(?:one|two|three|four|five|\d+)\s*[.]$",
            re.IGNORECASE,
        ),
    ),
    (
        "verb phrase inserted into contract artifact slot",
        re.compile(
            r"\b(?:accepts?|produces?|blocks?|proves?|coverage\s+for)\s+"
            r"(?:recomputes|computes?|calculates?|generates?|derives?|exports?|deletes?|records?|tracks?|validates?)\s+"
            r"[^.]{0,120}\b(?:input|result|output|state)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unnormalized recompute artifact phrase",
        re.compile(r"\brecomputes\s+[^.]{0,100}\b(?:input|result|output|state)\b", re.IGNORECASE),
    ),
    ("mechanical component planning note", re.compile(r"\bComponent planning record for\b", re.IGNORECASE)),
    ("mechanical runtime-boundary role", re.compile(r"\bruntime ownership boundary\b", re.IGNORECASE)),
    (
        "mechanical structured-contract narration",
        re.compile(r"\bstructured contract below keeps state, inputs, outputs, transitions, and refusals separate\b", re.IGNORECASE),
    ),
    ("mechanical failure-testability narration", re.compile(r"\bIt exists to make this failure testable\b", re.IGNORECASE)),
    ("context-clause leak", re.compile(r"\bRelated path\s*:", re.IGNORECASE)),
    ("malformed done-mean fragment", re.compile(r"\bDone\s+mean(?:s)?\b", re.IGNORECASE)),
    ("malformed mean-subject fragment", re.compile(r"\bMean\s+[a-z][^.]{0,80}", re.IGNORECASE)),
    ("malformed required-producing fragment", re.compile(r"\bRequired\s+producing\b", re.IGNORECASE)),
    ("malformed validated-producing fragment", re.compile(r"\bValidated\s+producing\b", re.IGNORECASE)),
    ("mechanical refusal bucket", re.compile(r"\bRefused domain responsibilities\s*:", re.IGNORECASE)),
    ("mechanical authority bucket", re.compile(r"\bForbidden runtime authorities\s*:", re.IGNORECASE)),
    ("mechanical boundary placeholder", re.compile(r"\bresponsibilities\s+not\s+named\s+by\s+(?:this\s+)?component\s+boundary\b", re.IGNORECASE)),
    ("parser action debris", re.compile(r"\bguide\s+(?:the\s+)?first\s+path\b", re.IGNORECASE)),
    ("parser action debris", re.compile(r"\bcapture\s+allowed\s+commands?\b", re.IGNORECASE)),
    ("parser action debris", re.compile(r"\bexposes?\s+blocked\s+states?\b", re.IGNORECASE)),
    ("mechanical dependency scaffold", re.compile(r"\bbefore\s+this\s+component\s+can\s+guide\b", re.IGNORECASE)),
    ("mechanical component section heading", re.compile(r"^##\s+Component Brief\s*$", re.IGNORECASE | re.MULTILINE)),
    ("mechanical component section heading", re.compile(r"^##\s+Boundary Narrative\s*$", re.IGNORECASE | re.MULTILINE)),
    ("mechanical component section heading", re.compile(r"^##\s+First Release Proof\s*$", re.IGNORECASE | re.MULTILINE)),
    ("mechanical component section heading", re.compile(r"^##\s+Implementation Starting Point\s*$", re.IGNORECASE | re.MULTILINE)),
    ("mechanical component question heading", re.compile(r"^###\s+(?:Owns|Accepts|Produces|Refuses)\s*$", re.IGNORECASE | re.MULTILINE)),
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
            if not _pattern_applies_to_path(label=label, path=path):
                continue
            if pattern.search(text):
                issues.append(f"generated prose uses {label} at {path}")
        if _has_dangling_tail(text):
            issues.append(f"generated prose appears clipped or unfinished at {path}")
    return dedupe_text(issues)


def rendered_component_spec_quality_issues(
    specs: Mapping[str, str],
    *,
    project_title: str = "",
    max_overlap: float = 0.82,
) -> list[str]:
    """Fail generic Registry specs whose content survives component-name swaps."""

    issues: list[str] = []
    names = tuple(specs.keys())
    name_term_lookup = {name: domain_terms(name) for name in names}
    all_name_terms = {term for terms in name_term_lookup.values() for term in terms}
    repeated_name_terms = {
        term
        for term in all_name_terms
        if sum(1 for terms in name_term_lookup.values() if term in terms) > 1
    }
    spec_term_lookup = {name: domain_terms(text) for name, text in specs.items()}
    all_spec_terms = tuple(spec_term_lookup.values())
    normalized_lines = {
        name: _normalized_spec_lines(text, project_title=project_title, names=names)
        for name, text in specs.items()
    }
    heading_sequences = {name: _visible_spec_headings(text) for name, text in specs.items()}
    for name, text in specs.items():
        for issue in public_prose_quality_issues(text):
            issues.append(f"`{name}` {issue}")
        issues.extend(_section_overlap_issues(name=name, text=text))
        local_terms = _local_domain_terms(
            text_terms=spec_term_lookup.get(name, set()),
            name_terms=name_term_lookup.get(name, set()),
            all_text_terms=all_spec_terms,
            repeated_name_terms=repeated_name_terms,
        )
        if len(local_terms) < 4:
            issues.append(f"component spec `{name}` does not contain at least four component-local domain terms")
    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            left_lines = normalized_lines[left_name]
            right_lines = normalized_lines[right_name]
            if not left_lines or not right_lines:
                continue
            if min(len(left_lines), len(right_lines)) < 10:
                continue
            overlap = len(left_lines & right_lines) / max(1, min(len(left_lines), len(right_lines)))
            if overlap > max_overlap:
                issues.append(
                    f"component specs `{left_name}` and `{right_name}` are too interchangeable after masking names "
                    f"({overlap:.2f} line overlap)"
                )
            left_headings = heading_sequences[left_name]
            right_headings = heading_sequences[right_name]
            if left_headings and left_headings == right_headings and len(left_headings) >= 3:
                issues.append(
                    f"component specs `{left_name}` and `{right_name}` reuse the same visible section skeleton"
                )
    return dedupe_text(issues)


def domain_terms(text: str) -> set[str]:
    """Return normalized, non-structural terms from public component prose."""

    return set(ordered_domain_terms(text))


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
            "source_title",
        )
    )


def _pattern_applies_to_path(*, label: str, path: str) -> bool:
    """Keep slot-filling checks scoped to generated contract/proof fields."""

    if label not in {
        "verb phrase inserted into contract artifact slot",
        "unnormalized recompute artifact phrase",
    }:
        return True
    lowered = path.casefold()
    return any(
        marker in lowered
        for marker in (
            "component_contract",
            ".validation",
            ".test_strategy",
            "semantic_model.components",
            "proof_obligations",
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


def _visible_spec_headings(text: str) -> tuple[str, ...]:
    headings: list[str] = []
    for raw in str(text or "").splitlines():
        line = _clean(raw)
        if not line.startswith("##"):
            continue
        heading = line.lstrip("# ").strip().casefold()
        if heading in {"feature history"}:
            continue
        headings.append(re.sub(r"\s+", " ", heading))
    return tuple(headings)


def _substantive_spec_line(line: str) -> bool:
    if not line or line.startswith("#") or line.startswith("|") or line.startswith("- `./.odylith"):
        return False
    lowered = line.casefold()
    if any(
        marker in lowered
        for marker in (
            "component planning record for",
            "planned from user-stated intent",
            "no source-backed claim is made yet",
            "runtime ownership boundary",
            "structured contract below keeps state",
            "actor identity",
            "bind this component to a technical plan",
            "validation context",
            "upstream handoff",
            "blocker signal",
            "component record, implementation plan",
            "create a radar-linked implementation plan",
            "domain risk: missing proof",
            "downstream consumer:",
            "review rationale",
            "downstream handoff",
            "promote this component from candidate",
            "promotion requires source-backed",
            "refused domain responsibilities:",
            "remains candidate until",
            "security and policy posture:",
            "start inside",
            "upstream truth:",
            "local blockers",
            "handoff evidence for",
        )
    ):
        return False
    if line in {
        "### Owns",
        "### Accepts",
        "### Produces",
        "### Refuses",
        "### Outside Boundary",
        "### Collaborators And Dependencies",
        "### Definition Of Done",
        "### Operator Verification",
    }:
        return False
    return len(domain_terms(line)) >= 4


def _section_overlap_issues(*, name: str, text: str, max_overlap: float = 0.80) -> list[str]:
    sections = _spec_sections(text)
    issues: list[str] = []
    structured_contract = not re.search(
        r"\b(?:the\s+)?first implementation plan must name accepted inputs\b",
        text,
        flags=re.IGNORECASE,
    )
    for left_index, (left_name, left_body) in enumerate(sections):
        left_terms = _section_terms(left_body)
        if len(left_terms) < 10:
            continue
        for right_name, right_body in sections[left_index + 1 :]:
            if not structured_contract and "Component Role" in {left_name, right_name}:
                continue
            right_terms = _section_terms(right_body)
            if len(right_terms) < 10:
                continue
            overlap = len(left_terms & right_terms) / max(1, min(len(left_terms), len(right_terms)))
            if overlap > max_overlap:
                issues.append(
                    f"component spec `{name}` repeats section content between `{left_name}` and `{right_name}` ({overlap:.2f} token overlap)"
                )
    return issues


def _spec_sections(text: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    current_name = ""
    current_lines: list[str] = []
    for raw in str(text or "").splitlines():
        line = _clean(raw)
        if line.startswith("## "):
            if current_name and current_lines:
                result.append((current_name, "\n".join(current_lines)))
            current_name = line.lstrip("# ").strip()
            current_lines = []
            continue
        if line.startswith("|") or line.startswith("#") or not line:
            continue
        if current_name in {"Component Snapshot", "Feature History"}:
            continue
        current_lines.append(line)
    if current_name and current_lines:
        result.append((current_name, "\n".join(current_lines)))
    return result


def _section_terms(text: str) -> set[str]:
    return {
        token
        for token in ordered_domain_terms(text)
        if token
        not in {
            "accept",
            "accepted",
            "block",
            "boundary",
            "candidate",
            "component",
            "contract",
            "field",
            "first",
            "handoff",
            "input",
            "local",
            "output",
            "proof",
            "refus",
            "runtime",
            "source-backed",
            "structured",
        }
    }


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


def _local_domain_terms(
    *,
    text_terms: set[str],
    name_terms: set[str],
    all_text_terms: Sequence[set[str]],
    repeated_name_terms: set[str],
) -> set[str]:
    own_name_terms = name_terms - repeated_name_terms
    terms = text_terms - repeated_name_terms
    counts: dict[str, int] = {}
    for candidate in terms:
        counts[candidate] = sum(1 for body_terms in all_text_terms if candidate in body_terms)
    majority = 1 if len(all_text_terms) <= 1 else max(2, len(all_text_terms) // 2)
    return own_name_terms | {term for term in terms if counts.get(term, 0) <= majority and term not in TERM_STOPWORDS}


def _label(row: Mapping[str, Any]) -> str:
    return _clean(row.get("label")) or _clean(row.get("name")) or _clean(row.get("component_id")) or "Component"


def _has_dangling_tail(value: str) -> bool:
    text = _clean(value)
    if len(text.split()) < 6:
        return False
    tail = text.rstrip(".;:, ").split()[-1].casefold()
    return tail in _DANGLING_WORDS


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _sentence(value: Any) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    if re.match(
        r"^(?:Operator|Maintainer|Reviewer|Primary user|Project operator|Domain reviewer|Implementation owner|Evidence owner|Workflow operator|Risk reviewer|Proof reviewer)(?:\s|:|[-–—]|$)",
        text,
    ):
        text = f"local {text[:1].lower()}{text[1:]}"
    return text[:1].upper() + text[1:] + "."


__all__ = [
    "CONTRACT_KEYS",
    "component_contract_issues",
    "contract_is_complete",
    "dedupe_text",
    "domain_terms",
    "normalize_contract",
    "public_prose_quality_issues",
    "rendered_component_spec_quality_issues",
]
