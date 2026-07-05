"""Known, unknown, claim, and risk card helpers for greenfield Project dashboards."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks_from_proposal
from odylith.runtime.domain_intelligence.greenfield_product_risks import risk_text_has_framework_leak
from odylith.runtime.project_intelligence.greenfield_project_text import _clean_display_title
from odylith.runtime.project_intelligence.greenfield_project_text import _dashboard_excerpt
from odylith.runtime.project_intelligence.greenfield_project_text import _partition_casefold
from odylith.runtime.project_intelligence.greenfield_project_text import _proof_answer_body
from odylith.runtime.project_intelligence.greenfield_project_text import _risk_without_embedded_path
from odylith.runtime.project_intelligence.greenfield_project_text import _title_case
from odylith.runtime.project_intelligence.utils import dict_value, list_value, sentence, short, tidy_fragment

def _known(
    *,
    title: str,
    first_path: str,
    release: str,
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    accepted: bool = False,
) -> list[str]:
    rows = [
        "Product direction accepted for planning." if accepted else "Product direction available for review.",
        f"Release target: {release}.",
    ]
    if sentence(first_path):
        rows.append("First path: summarized in the first-path scenario above.")
    shape = _planned_shape_summary(components=components, diagrams=diagrams)
    if shape:
        rows.append(shape)
    if accepted:
        rows.append("Build trust: still requires implementation evidence and validation.")
    return rows


def _unknown(
    *,
    questions: Sequence[str],
    assumptions: Sequence[str],
    risks: Sequence[str],
    non_goals: Sequence[str],
) -> list[str]:
    rows: list[str] = []
    if questions:
        rows.append(f"Decisions still open: {_join_boundary_values([_boundary_summary_item(row) for row in questions[:2]], total=len(questions))}.")
    if non_goals:
        rows.append(f"Outside first release: {_join_boundary_values([_boundary_summary_item(row) for row in non_goals[:3]], total=len(non_goals))}.")
    if assumptions:
        rows.append(f"Assumptions to confirm: {_join_boundary_values([_boundary_summary_item(row) for row in assumptions[:2]], total=len(assumptions))}.")
    if risks:
        rows.append(f"Build risks to control: {_join_boundary_values(_boundary_risk_labels(risks[:3]), total=len(risks))}.")
    return [tidy_fragment(short(row, limit=155)) for row in rows if row][:6] or ["No explicit unresolved proposal item found."]


def _planned_shape_summary(*, components: Sequence[Mapping[str, Any]], diagrams: Sequence[Mapping[str, Any]]) -> str:
    parts: list[str] = []
    if components:
        noun = "component boundary" if len(components) == 1 else "component boundaries"
        parts.append(f"{len(components)} {noun}")
    if diagrams:
        noun = "review view" if len(diagrams) == 1 else "review views"
        parts.append(f"{len(diagrams)} {noun}")
    if not parts:
        return ""
    return f"Planned shape: {' and '.join(parts)}."


def _join_boundary_values(values: Sequence[str], *, total: int) -> str:
    clean_values = [value.strip(" .") for value in values if sentence(value)]
    if not clean_values:
        return "not specified"
    joined = "; ".join(clean_values)
    remaining = max(0, total - len(clean_values))
    if remaining:
        noun = "point" if remaining == 1 else "points"
        verb = "needs" if remaining == 1 else "need"
        joined = f"{joined}; {remaining} more {noun} {verb} review"
    return joined


def _boundary_summary_item(value: object) -> str:
    text = sentence(value)
    text = re.sub(r"^(?:Not in the first release|Non-goal|Assumption|Question|Risk)\s*:\s*", "", text, flags=re.IGNORECASE)
    for separator in (". ", ": "):
        head, sep, _tail = text.partition(separator)
        if sep and 12 <= len(head.strip()) <= 62:
            text = head
            break
    for marker in (" stay ", " until ", " before ", " for "):
        head, sep, _tail = _partition_casefold(text, marker)
        if sep and 20 <= len(head.strip()) <= 70:
            text = head
            break
    text = _dashboard_excerpt(text, limit=62)
    text = text.strip(" .")
    return tidy_fragment(text) or "unresolved item"


def _boundary_risk_labels(risks: Sequence[str]) -> list[str]:
    labels: list[str] = []
    used: set[str] = set()
    for risk in risks:
        label = _risk_label(_risk_meaning(risk), used=used)
        used.add(label.casefold())
        labels.append(label)
    return labels


def _claim_evidence(
    *,
    title: str,
    intro: str,
    first_path: str,
    validation: Sequence[str],
    questions: Sequence[str],
    observed: Mapping[str, Any],
    accepted: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    source = sentence(observed.get("source_posture"), "greenfield proposal")
    rows = [
        {"claim": "Project identity", "value": title, "evidence": "user-stated", "freshness": "proposal", "owner": "Product decision owner", "source": source},
        {"claim": "Project explanation", "value": short(intro, limit=130), "evidence": "user-stated", "freshness": "proposal", "owner": "Product decision owner", "source": source},
        {"claim": "First path", "value": "Captured in the first-path scenario section.", "evidence": "inferred", "freshness": "proposal", "owner": "Accepted product direction", "source": source},
        {"claim": "Validation path", "value": short(_proof_answer_body(validation=validation, first_path=first_path), limit=130), "evidence": "needs validation", "freshness": "proposal", "owner": "Implementation plan", "source": source},
        {"claim": "Open questions", "value": str(len(questions)), "evidence": "user-stated", "freshness": "proposal", "owner": "Product decision owner", "source": source},
    ]
    accepted_record = dict_value(accepted or {})
    validation_gate = _accepted_validation_gate(accepted_record)
    if validation_gate:
        rows.insert(
            1,
            {
                "claim": "Accepted product check",
                "value": sentence(validation_gate.get("status"), "unknown"),
                "evidence": "governed",
                "freshness": sentence(accepted_record.get("accepted_at"), "accepted project"),
                "owner": "Product acceptance",
                "source": sentence(accepted_record.get("source_path"), "accepted project source"),
            },
        )
    return rows


def _accepted_validation_gate(accepted: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the accepted-project validation result, including legacy records."""
    gate = dict_value(accepted.get("validation_gate"))
    if gate:
        return gate
    return dict_value(accepted.get("tribunal"))


def _dashboard_risk_source(proposal: Mapping[str, Any], *, release: str) -> Sequence[Any]:
    risks = list_value(proposal.get("risks"))
    if risks and not any(risk_text_has_framework_leak(row) for row in risks):
        return risks
    return build_product_risks_from_proposal(proposal, release=release)


def _risk_items(value: object) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    used: set[str] = set()
    for item in list_value(value)[:4]:
        if not isinstance(item, Mapping):
            continue
        meaning = _risk_meaning(
            item.get("statement")
            or item.get("description")
            or item.get("risk")
            or item.get("trigger")
        )
        if not meaning:
            continue
        title = _dashboard_risk_title(sentence(item.get("title")), meaning=meaning, used=used)
        used.add(title.casefold())
        rows.append({"risk": title, "meaning": meaning})
    return rows


def _dashboard_risk_title(value: str, *, meaning: str, used: set[str]) -> str:
    title = _clean_display_title(value)
    if not title or risk_text_has_framework_leak({"title": title}):
        title = _risk_label(meaning, used=used)
    else:
        title = _title_case(short(title, limit=48))
    return _dedupe_label(title, used=used, source=meaning)


def _risk_classes(risks: Sequence[str]) -> list[dict[str, str]]:
    rows = []
    used: set[str] = set()
    for risk in risks[:4]:
        meaning = _risk_meaning(risk)
        label = _risk_label(meaning, used=used)
        used.add(label.casefold())
        rows.append({"risk": label, "meaning": meaning})
    return rows or [{"risk": "Unvalidated proposal", "meaning": "No implementation proof exists yet."}]


def _risk_meaning(value: object) -> str:
    text = _risk_without_embedded_path(value)
    if text and not text.endswith((".", "!", "?")):
        text += "."
    if len(text) > 220:
        first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
        if len(first_sentence) >= 42:
            return first_sentence
    return short(text, limit=240, fallback="The product has a real-world risk that needs an owner and validation.")


def _risk_label(value: str, *, used: set[str]) -> str:
    lowered = value.casefold()
    checks = [
        (("concentration", "threshold", "limit", "volume", "capped", "bounded"), "Control limits"),
        (("signal", "reading", "calibration", "drift", "measurement", "sample"), "Measurement reliability"),
        (("compliance", "privacy", "security", "jurisdiction", "kyc", "kyb", "aml", "regulated", "legal"), "Compliance boundary"),
        (("integration", "external", "api", "provider", "dependency", "webhook", "connector"), "External dependency"),
        (("owner", "approval", "handoff", "review", "responsibility", "operator"), "Ownership clarity"),
        (("rollback", "retry", "recovery", "blocked", "fail", "fault"), "Recovery path"),
        (("claim", "mislead", "status", "confidence", "trust"), "User trust"),
        (("harm", "damage", "loss", "safety", "unsafe", "hazard"), "Safety boundary"),
    ]
    for needles, label in checks:
        if any(needle in lowered for needle in needles):
            return _dedupe_label(label, used=used, source=value)
    return _dedupe_label("Proposal risk", used=used, source=value)


_RISK_LABEL_TERM_STOPWORDS = frozenset(
    {
        "accepted",
        "additional",
        "before",
        "blocked",
        "clear",
        "confidence",
        "control",
        "evidence",
        "missing",
        "product",
        "release",
        "result",
        "risk",
        "state",
        "trust",
        "user",
        "users",
        "without",
    }
)


def _dedupe_label(label: str, *, used: set[str], source: str = "") -> str:
    if label.casefold() not in used:
        return label
    focus = _risk_label_focus(source)
    if focus:
        candidate = _join_label_phrase(focus, label)
        if candidate.casefold() not in used:
            return candidate
    return f"{label} {len(used) + 1}"


def _join_label_phrase(prefix: str, suffix: str) -> str:
    prefix_words = [word for word in sentence(prefix).strip(" .").split() if word]
    suffix_words = [word for word in sentence(suffix).strip(" .").split() if word]
    if not prefix_words:
        return " ".join(suffix_words)
    if not suffix_words:
        return " ".join(prefix_words)
    if prefix_words[-1].casefold().strip(".,;:") == suffix_words[0].casefold().strip(".,;:"):
        suffix_words = suffix_words[1:]
    return " ".join([*prefix_words, *suffix_words]).strip()


def _risk_label_focus(value: object) -> str:
    terms = ordered_terms(value, minimum=4, stopwords=_RISK_LABEL_TERM_STOPWORDS, stem_ing=True)
    selected = [term for term in terms if term.casefold() not in _RISK_LABEL_TERM_STOPWORDS][:2]
    if not selected:
        return ""
    return _title_case(" ".join(selected))
