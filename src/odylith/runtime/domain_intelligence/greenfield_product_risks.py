"""Product-risk narration for confirmed greenfield projects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language
from odylith.runtime.domain_intelligence.greenfield_text import text_values


_FRAMEWORK_RISK_RE = re.compile(
    r"\b(?:accepted\s+first\s+path|accepted\s+proof\s+boundary|proof\s+boundar(?:y|ies)|"
    r"release\s+records?|governance\s+records?|state\s+transitions?|implementation\s+plans?|"
    r"governed\s+records?|proposal\s+risk|component\s+ownership|radar|registry|atlas|compass|casebook)\b",
    re.IGNORECASE,
)

_POLICY_RE = re.compile(
    r"\b(?:approval|approved|blocked|compliance|eligib|law|legal|limit|policy|qualification|regulated|"
    r"review|rule|threshold)\b",
    re.IGNORECASE,
)
_SENSITIVE_RE = re.compile(
    r"\b(?:account|address|age|care|credential|customer|financial|health|identity|location|medical|"
    r"payment|personal|private|profile|safety|secure|sensitive|user)\b",
    re.IGNORECASE,
)
_EXTERNAL_RE = re.compile(r"\b(?:api|device|external|import|integration|ledger|portal|provider|source|upload)\b", re.IGNORECASE)

_RISK_TERM_STOPWORDS = {
    "about",
    "accepted",
    "after",
    "before",
    "between",
    "cannot",
    "could",
    "every",
    "first",
    "from",
    "have",
    "into",
    "must",
    "product",
    "release",
    "result",
    "state",
    "system",
    "their",
    "there",
    "these",
    "they",
    "this",
    "through",
    "until",
    "users",
    "when",
    "where",
    "which",
    "without",
}


@dataclass(frozen=True)
class _RiskContext:
    title: str
    story: str
    problem: str
    first_path: str
    state_object: str
    proof_boundary: str
    primary_actor: str
    downstream_actor: str
    input_focus: str
    outcome: str
    external_focus: str
    non_goal_focus: str
    release: str


def build_product_risks(
    *,
    title: str,
    product_story: str,
    problem: str = "",
    first_path: str,
    state_object: str,
    proof_boundary: str,
    human_actors: Sequence[str] = (),
    external_systems: Sequence[str] = (),
    internal_systems: Sequence[str] = (),
    non_goals: Sequence[str] = (),
    release: str = "",
) -> list[dict[str, str]]:
    """Return product-facing risks derived only from the accepted intent."""

    del internal_systems
    ctx = _risk_context(
        title=title,
        product_story=product_story,
        problem=problem,
        first_path=first_path,
        state_object=state_object,
        proof_boundary=proof_boundary,
        human_actors=human_actors,
        external_systems=external_systems,
        non_goals=non_goals,
        release=release,
    )
    rows = [
        _result_reliability(ctx),
        _trust_and_explanation(ctx),
        _policy_or_input_quality(ctx),
        _operational_or_external_fit(ctx),
        _privacy_or_misuse(ctx),
    ]
    selected: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for row in rows:
        repaired = _quality_gate(row, ctx=ctx)
        title_key = repaired["title"].casefold()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        selected.append(
            {
                "id": f"RISK-{len(selected) + 1:03d}",
                "title": repaired["title"],
                "statement": repaired["statement"],
                "severity": repaired["severity"],
                "mitigation": repaired["mitigation"],
            }
        )
        if len(selected) >= 4:
            break
    return selected


def build_product_risks_from_proposal(proposal: Mapping[str, Any], *, release: str = "") -> list[dict[str, str]]:
    """Rebuild product risks from a proposal-like mapping during repair passes."""

    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    project = proposal.get("project_intelligence") if isinstance(proposal.get("project_intelligence"), Mapping) else {}
    return build_product_risks(
        title=_first_text(intent, "title") or _first_text(project, "title") or "Greenfield Project",
        product_story=_first_text(intent, "product_story", "summary") or _project_line(project, "intent"),
        problem=_project_line(project, "intent"),
        first_path=_first_text(intent, "first_path") or _project_line(project, "scope"),
        state_object=(
            _first_text(intent, "state_object")
            or _project_line(project, "state")
            or _project_line(project, "source_of_truth_map")
            or _project_line(project, "ontology")
        ),
        proof_boundary=_first_text(intent, "proof_boundary") or _project_line(project, "evidence"),
        human_actors=text_values(project.get("operators")),
        external_systems=text_values(project.get("scope")),
        internal_systems=[],
        non_goals=text_values(project.get("constraints")),
        release=release,
    )


def risk_text_has_framework_leak(value: Any) -> bool:
    """Return true when a risk talks about Odylith process instead of product reality."""

    text = _risk_text(value)
    return bool(_FRAMEWORK_RISK_RE.search(text))


def _risk_context(
    *,
    title: str,
    product_story: str,
    problem: str,
    first_path: str,
    state_object: str,
    proof_boundary: str,
    human_actors: Sequence[str],
    external_systems: Sequence[str],
    non_goals: Sequence[str],
    release: str,
) -> _RiskContext:
    actor_labels = [_actor_label(row) for row in human_actors if _actor_label(row)]
    story = _sentence(product_story)
    path = _sentence(first_path)
    state = _sentence(state_object)
    proof = _sentence(proof_boundary)
    return _RiskContext(
        title=compact_text(title) or title_label(title) or "Greenfield Project",
        story=story,
        problem=_sentence(problem),
        first_path=path,
        state_object=state,
        proof_boundary=proof,
        primary_actor=actor_labels[0] if actor_labels else "the primary user",
        downstream_actor=(actor_labels[1] if len(actor_labels) > 1 else actor_labels[-1] if actor_labels else "the next participant"),
        input_focus=_input_focus(path, fallback=state),
        outcome=_outcome_focus(story=story, first_path=path, proof_boundary=proof, state_object=state),
        external_focus=_external_focus(external_systems),
        non_goal_focus=_non_goal_focus(non_goals),
        release=compact_text(release) or "the first release",
    )


def _result_reliability(ctx: _RiskContext) -> dict[str, str]:
    statement = (
        f"{ctx.outcome} can be wrong or misleading when the information behind it is incomplete, stale, inconsistent, "
        f"or interpreted incorrectly. The weak inputs are {ctx.input_focus}; {ctx.primary_actor} may then act on a result "
        "that does not match the real situation."
    )
    return {
        "title": _title_from_terms("Result reliability", ctx.outcome),
        "statement": statement,
        "severity": "high",
        "mitigation": (
            "Check the required inputs, calculation or review behavior, and visible result together before trusting the product in real use."
        ),
    }


def _trust_and_explanation(ctx: _RiskContext) -> dict[str, str]:
    statement = (
        f"{ctx.primary_actor} may not understand why the product produced {ctx.outcome}. If the product cannot explain the result "
        "in plain language, people can dispute it, abandon the workflow, or work around the product."
    )
    return {
        "title": "User trust",
        "statement": statement,
        "severity": "high",
        "mitigation": f"Show the result, the important reasons behind it, and the next useful action for {ctx.primary_actor}.",
    }


def _policy_or_input_quality(ctx: _RiskContext) -> dict[str, str]:
    source = " ".join([ctx.story, ctx.first_path, ctx.state_object, ctx.proof_boundary])
    if _POLICY_RE.search(source):
        return {
            "title": "Policy drift",
            "statement": (
                f"The criteria behind {ctx.outcome} can drift away from the real-world policy or operating rule it is "
                "supposed to represent. The product can then appear confident while producing results that no longer match reality."
            ),
            "severity": "high",
            "mitigation": "Keep the criteria, thresholds, exceptions, and explanation shown by the product aligned with the current operating policy.",
        }
    return {
        "title": "Input quality",
        "statement": (
            f"The product can receive missing, inconsistent, or hard-to-interpret information while {_input_activity(ctx)}. "
            f"When that happens, {ctx.outcome} may look complete while hiding uncertainty that should change the user decision."
        ),
        "severity": "medium",
        "mitigation": "Validate required information, show incomplete or questionable inputs clearly, and keep correction paths visible.",
    }


def _operational_or_external_fit(ctx: _RiskContext) -> dict[str, str]:
    source = " ".join([ctx.external_focus, ctx.story, ctx.first_path])
    if ctx.external_focus and _EXTERNAL_RE.search(source):
        return {
            "title": "External dependency",
            "statement": (
                f"{ctx.title} may depend on {ctx.external_focus} being present, current, and understandable. "
                f"If those inputs are late, wrong, or unavailable, {ctx.downstream_actor} may receive a result that looks ready but cannot be trusted."
            ),
            "severity": "medium",
            "mitigation": "Treat missing, stale, or contradictory external information as visible product uncertainty instead of a normal successful result.",
        }
    return {
        "title": "Operational adoption",
        "statement": (
            f"{ctx.downstream_actor} may ignore or duplicate the product result if it arrives without enough context, priority, or follow-up detail. "
            f"The product would shift work between people instead of improving the real operating path."
        ),
        "severity": "medium",
        "mitigation": f"Make the handoff useful to {ctx.downstream_actor}: show what happened, why it matters, and what should happen next.",
    }


def _privacy_or_misuse(ctx: _RiskContext) -> dict[str, str]:
    source = " ".join([ctx.story, ctx.first_path, ctx.state_object, ctx.problem])
    if _SENSITIVE_RE.search(source):
        return {
            "title": "Sensitive data exposure",
            "statement": (
                f"{ctx.title} may collect or display information that people would not expect to spread beyond the product path. "
                "If access, retention, and sharing behavior are unclear, the product can create privacy, safety, or reputational harm."
            ),
            "severity": "medium",
            "mitigation": "Limit access to the people who need the information, explain sharing behavior, and retain only what the product outcome requires.",
        }
    excluded = ctx.non_goal_focus or "nearby outcomes that users may assume are included"
    return {
        "title": "Misuse and overreach",
        "statement": (
            f"People may use {ctx.title} for {excluded} before the product is ready for those outcomes. "
            "That can create misplaced confidence, unsupported decisions, or work that the product is not meant to carry yet."
        ),
        "severity": "medium",
        "mitigation": "State the limits in user-facing language and keep unsupported outcomes out of the first operating flow.",
    }


def _quality_gate(row: Mapping[str, str], *, ctx: _RiskContext) -> dict[str, str]:
    title = title_label(row.get("title", "")) or "Product risk"
    statement = _ensure_sentence(short_summary(row.get("statement", ""), limit=420))
    mitigation = _ensure_sentence(short_summary(row.get("mitigation", ""), limit=260))
    if _FRAMEWORK_RISK_RE.search(" ".join([title, statement, mitigation])) or _too_generic(statement, ctx):
        statement = _ensure_sentence(
            f"{ctx.outcome} can fail in the real world if the information behind it is wrong, missing, misunderstood, or used by the wrong person. "
            f"{ctx.primary_actor} and {ctx.downstream_actor} need a result they can understand and act on."
        )
        mitigation = _ensure_sentence(
            f"Validate the user-visible result, the information behind it, and the handoff to {ctx.downstream_actor} together."
        )
    return {"title": title, "statement": statement, "severity": row.get("severity", "medium"), "mitigation": mitigation}


def _too_generic(statement: str, ctx: _RiskContext) -> bool:
    terms = set(
        ordered_terms(
            " ".join([ctx.title, ctx.story, ctx.problem, ctx.first_path, ctx.state_object, ctx.outcome]),
            stopwords=_RISK_TERM_STOPWORDS,
        )
    )
    present = set(ordered_terms(statement, stopwords=_RISK_TERM_STOPWORDS))
    return len(statement.split()) < 16 or (bool(terms) and len(terms & present) < 2)


def _input_focus(first_path: str, *, fallback: str) -> str:
    clauses = _clauses(first_path)
    input_clauses = [
        clause
        for clause in clauses
        if re.search(
            r"\b(?:adds?|answers?|captures?|chooses?|completes?|connects?|enters?|fills?|imports?|logs?|records?|selects?|submits?|uploads?)\b",
            clause,
            re.IGNORECASE,
        )
        and not re.search(r"\b(?:display|review|return|see|show|summarize)\b", clause, re.IGNORECASE)
    ]
    input_objects = [_input_clause_object(clause) for clause in input_clauses[:1]]
    input_objects = [value for value in input_objects if value]
    if len(input_objects) == 2:
        selected = f"{input_objects[0]} and {input_objects[1]}"
    else:
        selected = ", ".join(input_objects or input_clauses[:2]).strip(" .")
    if selected:
        return _lower_first(short_summary(selected, limit=180))
    label = domain_object_label(fallback, fallback="the information the product needs")
    return _lower_label(label)


def _input_activity(ctx: _RiskContext) -> str:
    focus = compact_text(ctx.input_focus).strip(" .")
    if not focus:
        return f"{_lower_first(ctx.primary_actor)} provides the required information"
    if re.match(r"^(?:a|an|the|one)\s+", focus, flags=re.IGNORECASE):
        return focus
    if re.match(r"^(?:adds?|answers?|captures?|chooses?|completes?|connects?|enters?|fills?|imports?|logs?|records?|selects?|submits?|uploads?)\b", focus, flags=re.IGNORECASE):
        return f"{_lower_first(ctx.primary_actor)} {focus}"
    if re.match(r"^(?:their|his|her|its|our|my)\b", focus, flags=re.IGNORECASE):
        verb = "connects" if re.search(r"\bconnects?\b", ctx.first_path, flags=re.IGNORECASE) else "provides"
        return f"{_lower_first(ctx.primary_actor)} {verb} {focus}"
    if len(focus.split()) <= 6:
        return f"{_lower_first(ctx.primary_actor)} provides {focus}"
    return focus


def _outcome_focus(*, story: str, first_path: str, proof_boundary: str, state_object: str) -> str:
    model = first_path_model(first_path)
    if model.visible_outcome:
        return _outcome_clause_as_noun(model.visible_outcome)
    for source in (first_path, story, proof_boundary):
        outcome = _last_outcome_clause(source)
        if outcome:
            return _outcome_clause_as_noun(outcome)
    label = domain_object_label(state_object, fallback="the product result")
    return _lower_first(label)


def _outcome_clause_as_noun(value: str) -> str:
    text = normalize_visible_result_language(compact_text(value)).strip(" .")
    text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.IGNORECASE).strip(" .")
    text = re.sub(r"^(?:and|then|finally)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:her|his|its|our|their|your)\s+", "", text, flags=re.IGNORECASE)
    subject_verb = re.match(
        r"^(?:a|an|the)\s+[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?\s+"
        r"(?:can\s+)?(?:acts?\s+on|approves?|blocks?|decides?|displays?|explains?|gets?|inspects?|receives?|reviews?|sees?|shows?|uses?)\s+"
        r"(?P<object>(?:a|an|the|one)\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if subject_verb:
        return _lower_first(short_summary(subject_verb.group("object"), limit=200))
    product_verb = re.match(
        r"^(?:product|system|app|application|service)\s+"
        r"(?:displays?|explains?|makes?|produces?|records?|returns?|shows?)\s+"
        r"(?P<object>(?:a|an|the|one)\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if product_verb:
        return _lower_first(short_summary(product_verb.group("object"), limit=200))
    verb_first = re.match(
        r"^(?:displays?|explains?|makes?|produces?|records?|returns?|shows?)\s+"
        r"(?P<object>(?:a|an|the|one)\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if verb_first:
        return _lower_first(short_summary(verb_first.group("object"), limit=200))
    return _lower_first(short_summary(text, limit=200))


def _last_outcome_clause(value: str) -> str:
    markers = (
        r"\b(?:act|answer|approved?|available|blocked|completed?|decide|decision|deliver|display|explain|"
        r"handoff|outcome|produce|ready|receive|recommend|reject|result|review|show|summary|trust|visible)\b"
    )
    clauses = _clauses(value)
    for clause in reversed(clauses):
        if re.search(markers, clause, re.IGNORECASE):
            return clause
    return ""


def _clauses(value: str) -> list[str]:
    text = compact_text(value).strip(" .")
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+|,\s+|\bthen\b|\band then\b", text, flags=re.IGNORECASE)
    rows = []
    for part in parts:
        clause = re.sub(r"^(?:and|then|finally)\s+", "", compact_text(part).strip(" ."), flags=re.IGNORECASE)
        if clause:
            rows.append(clause)
    return rows


def _actor_label(value: str) -> str:
    text = compact_text(value).strip(" .")
    text = re.sub(r"^actors\s+involved\s+[^:.;]*?\s+are\s+", "", text, flags=re.IGNORECASE).strip(" .")
    text = re.split(r"\s+[—-]\s+|:\s+", text, maxsplit=1)[0].strip(" .:-")
    text = re.split(r",\s+|\s+and\s+", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .,:;")
    text = re.split(r"\b(?:who|that|with|and)\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .,:;")
    words = text.split()
    if len(words) > 6:
        text = " ".join(words[:6])
    return text[:1].upper() + text[1:] if text else ""


def _input_clause_object(value: str) -> str:
    text = compact_text(value).strip(" .")
    subject_verb = re.match(
        r"^(?:a|an|the)\s+[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?\s+"
        r"(?:adds?|answers?|captures?|chooses?|completes?|connects?|enters?|fills?|imports?|logs?|records?|selects?|submits?|uploads?)\s+"
        r"(?P<object>(?:a|an|the|one|their|his|her|its|our|my)\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if subject_verb:
        return _lower_first(short_summary(subject_verb.group("object"), limit=110))
    verb_first = re.match(
        r"^(?:adds?|answers?|captures?|chooses?|completes?|connects?|enters?|fills?|imports?|logs?|records?|selects?|submits?|uploads?)\s+"
        r"(?P<object>(?:a|an|the|one|their|his|her|its|our|my)\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if verb_first:
        return _lower_first(short_summary(verb_first.group("object"), limit=110))
    return _lower_first(short_summary(text, limit=110))


def _external_focus(values: Sequence[str]) -> str:
    labels = []
    candidates = [value for value in values if re.search(r"\bexternal\s+systems?\s*:", compact_text(value), flags=re.IGNORECASE)]
    for value in candidates or values:
        text = compact_text(value)
        if re.search(r"\bexternal\s+systems?\s*:", text, flags=re.IGNORECASE):
            text = re.split(r"\bexternal\s+systems?\s*:\s*", text, maxsplit=1, flags=re.IGNORECASE)[1]
        head = re.split(r"\s+[—-]\s+|:\s+", text, maxsplit=1)[0].strip(" .:-")
        for label in re.split(r",\s+|\s+and\s+", head):
            label = label.strip(" .:-")
            if label:
                labels.append(label)
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:2])}, and related outside information"


def _non_goal_focus(values: Sequence[str]) -> str:
    rows = [short_summary(value, limit=120).strip(" .") for value in values if short_summary(value, limit=120)]
    if not rows:
        return ""
    return _lower_first(rows[0])


def _title_from_terms(default: str, value: str) -> str:
    lowered = value.casefold()
    if any(term in lowered for term in ("decision", "recommend", "approval", "qualified", "eligible")):
        return "Decision accuracy"
    if any(term in lowered for term in ("summary", "report", "timeline", "view")):
        return "Summary accuracy"
    return default


def _project_line(project: Mapping[str, Any], key: str) -> str:
    values = text_values(project.get(key))
    return values[0] if values else ""


def _first_text(mapping: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = compact_text(mapping.get(key))
        if value:
            return value
    return ""


def _risk_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(compact_text(nested) for nested in value.values())
    return compact_text(value)


def _sentence(value: Any) -> str:
    return compact_text(value).strip(" .")


def _ensure_sentence(value: str) -> str:
    text = compact_text(value).strip()
    if not text:
        return ""
    text = f"{text[:1].upper()}{text[1:]}" if text else text
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _lower_first(value: str) -> str:
    text = compact_text(value)
    return f"{text[:1].lower()}{text[1:]}" if text else ""


def _lower_label(value: str) -> str:
    text = compact_text(value)
    return text.casefold() if text else ""


__all__ = [
    "build_product_risks",
    "build_product_risks_from_proposal",
    "risk_text_has_framework_leak",
]
