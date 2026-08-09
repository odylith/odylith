"""Deterministic semantic release scoring against blinded atomic annotations."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import hashlib
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import ATOMIC_CATEGORY_FIELDS
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import atomic_claim_units
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import atomic_fact_ledger_hash
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import require_atomic_fact_ledger

from greenfield_matrix_statistics import wilson_interval
from greenfield_matrix_types import GreenfieldMatrixResult


SEMANTIC_RELEASE_SCORE_VERSION = "odylith.greenfield.semantic-release-score.v1"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "before",
        "by",
        "can",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "one",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "with",
    }
)
_VALID_MATERIAL_CUSTODY = frozenset({"accepted_fact", "bounded_interpretation"})
_INDEPENDENT_PRODUCT_EVIDENCE_HEADINGS = frozenset(
    {
        "ambiguities",
        "assumptions",
        "component responsibilities",
        "customer",
        "external systems",
        "first complete path",
        "first path",
        "human actors",
        "internal product systems",
        "internal systems",
        "non goals",
        "non-goals",
        "open questions",
        "operational constraints",
        "operator edit evidence",
        "operator prompt evidence",
        "opportunity",
        "problem",
        "product name",
        "product story",
        "product view",
        "proof boundary",
        "state",
        "state object",
        "success metrics",
        "title",
    }
)
_SOURCE_METADATA_LABEL_RE = re.compile(
    r"\b(?:source\s+evidence|source\s+repository|repository\s+description)\s*(?::|-)\s*",
    flags=re.IGNORECASE,
)
_SOURCE_METADATA_BOUNDARY_PUNCTUATION = (".", "!", "?", "-", ";", ":", ",")


def evaluate_semantic_release(
    *,
    cases: Sequence[Any],
    annotations: Mapping[str, Mapping[str, Any]],
    results: Sequence[GreenfieldMatrixResult],
    floors: Mapping[str, Any],
    _include_model_profiles: bool = True,
    _allow_not_applicable_metrics: bool = False,
) -> dict[str, Any]:
    """Score result semantics without returning blinded evidence text."""

    case_ids = [_case_id(case) for case in cases]
    result_ids = [_result_case_id(result) for result in results]
    duplicate_case_ids = _duplicates(case_ids)
    duplicate_result_ids = _duplicates(result_ids)
    results_by_id = {case_id: result for case_id, result in zip(result_ids, results, strict=False) if case_id}
    metric_counts: dict[str, list[int]] = {
        "accepted_fact_custody": [0, 0],
        "critical_constraint_recall": [0, 0],
        "explicit_system_recall": [0, 0],
        "material_question_recall": [0, 0],
        "unnecessary_question_rate": [0, 0],
        "first_path_comprehension": [0, 0],
    }
    case_outcomes: list[dict[str, Any]] = []
    p0_findings: list[dict[str, str]] = []
    missing_case_ids: list[str] = []
    for case in cases:
        case_id = _case_id(case)
        annotation = annotations.get(case_id)
        result = results_by_id.get(case_id)
        if annotation is None or result is None:
            missing_case_ids.append(case_id)
            continue
        outcome = _score_case(
            case=case,
            annotation=annotation,
            result=result,
            metric_counts=metric_counts,
        )
        case_outcomes.append(outcome)
        p0_findings.extend(outcome["p0_findings"])

    metrics = {name: _metric(name, *counts) for name, counts in metric_counts.items()}
    passed_count = sum(1 for outcome in case_outcomes if outcome["passed"])
    sample_count = len(case_outcomes)
    overall = _metric("overall_case_success", passed_count, sample_count)
    lower, upper = wilson_interval(passed_count, sample_count)
    overall["confidence_interval_95"] = _interval_payload(lower, upper)
    slices = _slice_rows(cases=cases, outcomes=case_outcomes)
    worst_slice = min(
        slices,
        key=lambda row: (float(row["point_estimate"]), str(row["dimension"]), str(row["value"])),
        default={},
    )
    checks = _floor_checks(
        floors=floors,
        metrics=metrics,
        overall=overall,
        worst_slice=worst_slice,
        p0_findings=p0_findings,
        allow_not_applicable_metrics=_allow_not_applicable_metrics,
    )
    issues = [
        str(check["issue"])
        for check in checks
        if check["status"] in {"failed", "unproven"} and str(check.get("issue") or "").strip()
    ]
    if missing_case_ids:
        issues.append("semantic release results are incomplete")
    if duplicate_case_ids:
        issues.append("semantic release cases contain duplicate IDs")
    if duplicate_result_ids:
        issues.append("semantic release results contain duplicate IDs")
    model_profiles = (
        _model_profile_reports(
            cases=cases,
            annotations=annotations,
            results=results,
            floors=floors,
        )
        if _include_model_profiles
        else []
    )
    for profile in model_profiles:
        if profile["status"] != "passed":
            issues.append(f"model profile `{profile['profile']}` failed the semantic release floors")
    return {
        "version": SEMANTIC_RELEASE_SCORE_VERSION,
        "status": "passed" if not issues else "failed",
        "passed": not issues,
        "sample_count": sample_count,
        "selected_case_count": len(cases),
        "missing_case_ids": missing_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "duplicate_result_ids": duplicate_result_ids,
        "metrics": metrics,
        "overall_case_success": overall,
        "worst_slice": worst_slice,
        "slices": slices,
        "p0_count": len(p0_findings),
        "p0_findings": p0_findings,
        "floor_checks": checks,
        "issues": list(dict.fromkeys(issues)),
        "model_profiles": model_profiles,
        "case_outcomes": [
            {
                "case_id": row["case_id"],
                "passed": row["passed"],
                "expected_outcome": row["expected_outcome"],
                "observed_outcome": row["observed_outcome"],
                "failed_dimensions": row["failed_dimensions"],
            }
            for row in case_outcomes
        ],
    }


def _model_profile_reports(
    *,
    cases: Sequence[Any],
    annotations: Mapping[str, Mapping[str, Any]],
    results: Sequence[GreenfieldMatrixResult],
    floors: Mapping[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for case in cases:
        profile = _model_profile(case)
        if profile:
            grouped[profile].append(case)
    results_by_id = {_result_case_id(result): result for result in results}
    reports: list[dict[str, Any]] = []
    for profile, profile_cases in sorted(grouped.items()):
        case_ids = {_case_id(case) for case in profile_cases}
        report = evaluate_semantic_release(
            cases=profile_cases,
            annotations={case_id: annotations[case_id] for case_id in case_ids if case_id in annotations},
            results=[results_by_id[case_id] for case_id in case_ids if case_id in results_by_id],
            floors=floors,
            _include_model_profiles=False,
            _allow_not_applicable_metrics=True,
        )
        reports.append(
            {
                "profile": profile,
                "status": report["status"],
                "passed": report["passed"],
                "sample_count": report["sample_count"],
                "metrics": report["metrics"],
                "overall_case_success": report["overall_case_success"],
                "worst_slice": report["worst_slice"],
                "p0_count": report["p0_count"],
                "floor_checks": report["floor_checks"],
                "issues": report["issues"],
            }
        )
    return reports


def _model_profile(case: Any) -> str:
    profiles = [
        str(tag).partition(":")[2]
        for tag in getattr(case, "tags", ()) or ()
        if str(tag).startswith("model-profile:")
    ]
    return profiles[0] if len(profiles) == 1 else ""


def _score_case(
    *,
    case: Any,
    annotation: Mapping[str, Any],
    result: GreenfieldMatrixResult,
    metric_counts: Mapping[str, list[int]],
) -> dict[str, Any]:
    case_id = _case_id(case)
    expected = str(annotation.get("expected_outcome") or "").strip()
    evidence = _mapping(result.evidence)
    clarification = _mapping(evidence.get("clarification"))
    receipt = _mapping(evidence.get("preconfirm_dry_run"))
    snapshot = _mapping(receipt.get("semantic_snapshot"))
    facts = _mapping(snapshot.get("facts"))
    if str(clarification.get("mode") or "") == "clarification_required":
        observed = "clarify"
    else:
        observed = "commit" if snapshot else "failed"
    failed_dimensions: list[str] = []
    p0: list[dict[str, str]] = []
    if expected != observed or result.status != "passed" or not result.quality.passed:
        failed_dimensions.append("outcome")
    if expected == "clarify" and observed == "commit":
        p0.append(_p0(case_id, "material_ambiguity_ignored"))

    if expected == "commit":
        metric_counts["unnecessary_question_rate"][1] += 1
        if observed == "clarify":
            metric_counts["unnecessary_question_rate"][0] += 1
        if snapshot:
            _score_commit_semantics(
                case_id=case_id,
                annotation=annotation,
                snapshot=snapshot,
                facts=facts,
                prompt_text=str(getattr(case, "prompt", "") or "").strip(),
                confirmed_intent_markdown=str(
                    getattr(case, "confirmed_intent_markdown", "") or ""
                ).strip(),
                metric_counts=metric_counts,
                failed_dimensions=failed_dimensions,
                p0=p0,
            )
    elif expected == "clarify":
        metric_counts["material_question_recall"][1] += 1
        expected_fields = {_question_field_key(value) for value in _strings(annotation.get("expected_question_fields"))}
        observed_fields = {_question_field_key(value) for value in _strings(clarification.get("required_fields"))}
        question_recalled = observed == "clarify" and (not expected_fields or expected_fields <= observed_fields)
        if question_recalled:
            metric_counts["material_question_recall"][0] += 1
        else:
            failed_dimensions.append("material_question_recall")

    return {
        "case_id": case_id,
        "expected_outcome": expected,
        "observed_outcome": observed,
        "passed": not failed_dimensions and not p0,
        "failed_dimensions": list(dict.fromkeys(failed_dimensions)),
        "p0_findings": p0,
    }


def _score_commit_semantics(
    *,
    case_id: str,
    annotation: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    facts: Mapping[str, Any],
    prompt_text: str,
    confirmed_intent_markdown: str,
    metric_counts: Mapping[str, list[int]],
    failed_dimensions: list[str],
    p0: list[dict[str, str]],
) -> None:
    atomic_facts = _validated_atomic_facts(
        snapshot,
        facts=facts,
        prompt_text=prompt_text,
        confirmed_intent_markdown=confirmed_intent_markdown,
    )
    if atomic_facts is None:
        atomic_facts = ()
        failed_dimensions.append("atomic_custody_invalid")
        p0.append(_p0(case_id, "atomic_custody_invalid"))
    for category in _atomic_categories():
        for item in _items(annotation.get(category)):
            if str(item.get("expected_custody") or "") != "accepted_fact":
                continue
            metric_counts["accepted_fact_custody"][1] += 1
            if _claim_has_custody(
                category=category,
                value=item.get("value"),
                expected_custody="accepted_fact",
                facts=facts,
                atomic_facts=atomic_facts,
            ):
                metric_counts["accepted_fact_custody"][0] += 1
            else:
                failed_dimensions.append("accepted_fact_custody")

    constraint_claims = _atomic_claim_values(atomic_facts) or _fact_claim_values(facts)
    for value in _expected_values(annotation.get("critical_constraints")):
        metric_counts["critical_constraint_recall"][1] += 1
        if _claim_recalled_in(value, constraint_claims):
            metric_counts["critical_constraint_recall"][0] += 1
        else:
            failed_dimensions.append("critical_constraint_recall")
            p0.append(_p0(case_id, "critical_constraint_missing"))

    system_claims = _atomic_claim_values(
        atomic_facts,
        categories=frozenset({"dependencies"}),
    ) or _fact_claim_values(
        facts,
        fields=("external_systems", "internal_systems", "component_responsibilities"),
    )
    for value in _expected_values(annotation.get("explicit_systems")):
        metric_counts["explicit_system_recall"][1] += 1
        if _claim_recalled_in(value, system_claims):
            metric_counts["explicit_system_recall"][0] += 1
        else:
            failed_dimensions.append("explicit_system_recall")
            p0.append(_p0(case_id, "explicit_system_missing"))

    first_path_text = _flatten_text(
        {
            "human_actors": facts.get("human_actors"),
            "state_object": facts.get("state_object"),
            "first_path": facts.get("first_path"),
            "proof_boundary": facts.get("proof_boundary"),
        }
    )
    first_path_items = [
        item
        for category in ("actors", "actions", "states", "outputs")
        for item in _items(annotation.get(category))
        if str(item.get("materiality") or "") == "material"
    ]
    for item in first_path_items:
        metric_counts["first_path_comprehension"][1] += 1
        if _claim_recalled(item.get("value"), first_path_text):
            metric_counts["first_path_comprehension"][0] += 1
        else:
            failed_dimensions.append("first_path_comprehension")


def _floor_checks(
    *,
    floors: Mapping[str, Any],
    metrics: Mapping[str, Mapping[str, Any]],
    overall: Mapping[str, Any],
    worst_slice: Mapping[str, Any],
    p0_findings: Sequence[Mapping[str, str]],
    allow_not_applicable_metrics: bool,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "no_observed_p0_contradiction",
            not p0_findings,
            "observed P0 semantic contradiction",
        )
    )
    for name in (
        "accepted_fact_custody",
        "critical_constraint_recall",
        "explicit_system_recall",
        "material_question_recall",
        "first_path_comprehension",
    ):
        checks.append(
            _metric_floor_check(
                name,
                metrics[name],
                floors.get(name),
                allow_not_applicable=allow_not_applicable_metrics,
            )
        )
    checks.append(
        _metric_ceiling_check(
            "unnecessary_question_rate",
            metrics["unnecessary_question_rate"],
            floors.get("unnecessary_question_rate_ceiling"),
            allow_not_applicable=allow_not_applicable_metrics,
        )
    )
    checks.append(
        _metric_floor_check(
            "overall_case_success",
            overall,
            floors.get("overall_case_success"),
            allow_not_applicable=False,
        )
    )
    worst_rate = worst_slice.get("point_estimate") if worst_slice else None
    checks.append(
        _check_threshold(
            "worst_slice_success",
            observed=worst_rate,
            expected=floors.get("worst_slice_success"),
            direction="floor",
        )
    )
    return checks


def _metric_floor_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = metric.get("rate") if metric.get("status") == "measured" else None
    return _check_threshold(name, observed=observed, expected=expected, direction="floor")


def _metric_ceiling_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = metric.get("rate") if metric.get("status") == "measured" else None
    return _check_threshold(name, observed=observed, expected=expected, direction="ceiling")


def _not_applicable_check(name: str, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": "not_applicable",
        "observed": None,
        "expected": expected,
        "issue": "",
    }


def _check_threshold(name: str, *, observed: Any, expected: Any, direction: str) -> dict[str, Any]:
    if not isinstance(expected, (int, float)) or isinstance(expected, bool):
        return {
            "name": name,
            "status": "unproven",
            "observed": observed,
            "expected": expected,
            "issue": f"{name} has no frozen threshold",
        }
    if not isinstance(observed, (int, float)) or isinstance(observed, bool):
        return {
            "name": name,
            "status": "unproven",
            "observed": observed,
            "expected": expected,
            "issue": f"{name} is unproven (0 of 0 is not a pass)",
        }
    passed = observed >= expected if direction == "floor" else observed <= expected
    symbol = ">=" if direction == "floor" else "<="
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "observed": observed,
        "expected": expected,
        "issue": "" if passed else f"{name} {observed:.6f} does not satisfy {symbol} {expected:.6f}",
    }


def _check(name: str, passed: bool, issue: str) -> dict[str, Any]:
    return {"name": name, "status": "passed" if passed else "failed", "issue": "" if passed else issue}


def _metric(name: str, numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "name": name,
        "status": "measured" if denominator else "not_applicable",
        "numerator": int(numerator),
        "denominator": int(denominator),
        "rate": round(numerator / denominator, 6) if denominator else None,
    }


def _slice_rows(*, cases: Sequence[Any], outcomes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    outcome_by_id = {str(row["case_id"]): bool(row["passed"]) for row in outcomes}
    grouped: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for case in cases:
        case_id = _case_id(case)
        if case_id not in outcome_by_id:
            continue
        for dimension, value in _case_slices(case):
            grouped[(dimension, value)].append(outcome_by_id[case_id])
    rows: list[dict[str, Any]] = []
    for (dimension, value), values in sorted(grouped.items()):
        passed = sum(values)
        total = len(values)
        lower, upper = wilson_interval(passed, total)
        rows.append(
            {
                "dimension": dimension,
                "value": value,
                "sample_count": total,
                "passed_count": passed,
                "failed_count": total - passed,
                "point_estimate": round(passed / total, 6),
                "confidence_interval_95": _interval_payload(lower, upper),
            }
        )
    return rows


def _case_slices(case: Any) -> tuple[tuple[str, str], ...]:
    rows = [
        ("input_style", str(getattr(case, "input_style", "") or "unspecified")),
        ("expectation", str(getattr(case, "expectation", "") or "transaction_committed")),
    ]
    for tag in getattr(case, "tags", ()) or ():
        token = str(tag or "").strip()
        if ":" in token:
            dimension, _, value = token.partition(":")
            if dimension in {"complexity", "model-profile", "host-profile", "slice"}:
                rows.append((dimension.replace("-", "_"), value or "unspecified"))
    return tuple(dict.fromkeys(rows))


def _claim_has_custody(
    *,
    category: str,
    value: Any,
    expected_custody: str,
    facts: Mapping[str, Any],
    atomic_facts: Sequence[Mapping[str, Any]],
) -> bool:
    allowed_fields = set(ATOMIC_CATEGORY_FIELDS.get(category, ()))
    for atom in atomic_facts:
        if category not in _strings(atom.get("categories")):
            continue
        custody_state = str(atom.get("custody_state") or "")
        if custody_state != expected_custody or custody_state not in _VALID_MATERIAL_CUSTODY:
            continue
        if not _claim_recalled(value, str(atom.get("normalized_value") or "")):
            continue
        for link in _items(atom.get("projection_links")):
            field = str(link.get("field") or "")
            if field in allowed_fields and _claim_recalled(value, _flatten_text(facts.get(field))):
                return True
    return False


def _validated_atomic_facts(
    snapshot: Mapping[str, Any],
    *,
    facts: Mapping[str, Any],
    prompt_text: str,
    confirmed_intent_markdown: str,
) -> tuple[Mapping[str, Any], ...] | None:
    value = snapshot.get("atomic_facts")
    try:
        require_atomic_fact_ledger(value, facts=facts)
    except ValueError:
        return None
    rows = _items(value)
    if str(snapshot.get("atomic_custody_sha256") or "") != atomic_fact_ledger_hash(rows):
        return None
    source_units = _independent_source_units(
        prompt_text=prompt_text,
        confirmed_intent_markdown=confirmed_intent_markdown,
    )
    source_by_hash = {
        _sha256_text(unit): unit
        for unit in source_units
    }
    for atom in rows:
        if atom.get("custody_state") != "accepted_fact":
            continue
        claim = str(atom.get("normalized_value") or "")
        refs = _items(atom.get("source_span_refs"))
        if not refs or not any(
            (source := source_by_hash.get(str(ref.get("text_sha256") or ""))) is not None
            and _ordered_source_entailment(source=source, claim=claim)
            for ref in refs
        ):
            return None
    return rows


def _independent_source_units(
    *,
    prompt_text: str,
    confirmed_intent_markdown: str,
) -> tuple[str, ...]:
    texts = (
        _independent_product_evidence_text(prompt_text),
        _independent_product_evidence_text(confirmed_intent_markdown),
    )
    units: list[str] = []
    for text in texts:
        for line in text.splitlines():
            cleaned_line = " ".join(line.strip().split()).strip()
            if not cleaned_line or cleaned_line.startswith(("```", "<!--")):
                continue
            units.append(cleaned_line)
            for sentence in re.split(r"(?<=[.!?])\s+|;\s*", cleaned_line):
                sentence = sentence.strip(" .;:")
                if not sentence:
                    continue
                units.append(sentence)
                units.extend(
                    clause
                    for row in re.split(r"[,:]\s*", sentence)
                    if (clause := " ".join(row.strip().split()).strip(" .;:"))
                )
    return tuple(dict.fromkeys(units))


def _independent_product_evidence_text(value: str) -> str:
    rows: list[str] = []
    source = str(value or "")
    has_markdown_heading = any(_independent_heading_key(row) for row in source.splitlines())
    collecting = not has_markdown_heading
    for row in source.splitlines():
        heading = _independent_heading_key(row)
        if heading:
            collecting = heading in _INDEPENDENT_PRODUCT_EVIDENCE_HEADINGS
            continue
        if collecting:
            rows.append(row)
    text = "\n".join(rows).strip()
    for label in _SOURCE_METADATA_LABEL_RE.finditer(text):
        prefix = text[: label.start()]
        if not prefix or prefix.rstrip().endswith(_SOURCE_METADATA_BOUNDARY_PUNCTUATION):
            return prefix.rstrip(" \t-;:,")
    return text


def _independent_heading_key(value: str) -> str:
    match = re.match(r"^\s{0,3}#{1,6}\s+(?P<label>.+?)\s*$", str(value or ""))
    if not match:
        return ""
    return " ".join(match.group("label").strip().rstrip(":").casefold().split())


def _ordered_source_entailment(*, source: str, claim: str) -> bool:
    source_tokens = _semantic_sequence(source)
    claim_tokens = _semantic_sequence(claim)
    if not claim_tokens or len(claim_tokens) > len(source_tokens):
        return False
    size = len(claim_tokens)
    return any(source_tokens[index : index + size] == claim_tokens for index in range(len(source_tokens) - size + 1))


def _semantic_sequence(value: Any) -> tuple[str, ...]:
    return tuple(
        _stem_token(token)
        for token in _TOKEN_RE.findall(str(value or "").casefold())
        if token not in _STOPWORDS
    )


def _stem_token(value: str) -> str:
    if len(value) > 5 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 5 and value.endswith("ing"):
        stem = value[:-3]
        return stem[:-1] if len(stem) > 3 and stem[-1:] == stem[-2:-1] else stem
    if len(value) > 4 and value.endswith("ed"):
        stem = value[:-2]
        return stem[:-1] if len(stem) > 3 and stem[-1:] == stem[-2:-1] else stem
    if len(value) > 4 and value.endswith("es") and value[:-2].endswith(("ch", "o", "s", "sh", "x", "z")):
        value = value[:-2]
    elif len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
        value = value[:-1]
    if len(value) > 5 and value.endswith("e"):
        return value[:-1]
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _claim_recalled(expected: Any, observed: str) -> bool:
    expected_tokens = _tokens(expected)
    if not expected_tokens:
        return False
    observed_tokens = _tokens(observed)
    return expected_tokens <= observed_tokens and _is_negated(expected) == _is_negated(observed)


def _claim_recalled_in(expected: Any, observed_claims: Sequence[str]) -> bool:
    return any(
        _claim_recalled(expected, unit)
        for claim in observed_claims
        for unit in atomic_claim_units(claim)
    )


def _atomic_claim_values(
    atomic_facts: Sequence[Mapping[str, Any]],
    *,
    categories: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    claims: list[str] = []
    for atom in atomic_facts:
        if str(atom.get("custody_state") or "") not in _VALID_MATERIAL_CUSTODY:
            continue
        atom_categories = set(_strings(atom.get("categories")))
        if categories and not categories & atom_categories:
            continue
        claim = str(atom.get("normalized_value") or "").strip()
        if claim:
            claims.append(claim)
    return tuple(dict.fromkeys(claims))


def _fact_claim_values(
    facts: Mapping[str, Any],
    *,
    fields: Sequence[str] = (),
) -> tuple[str, ...]:
    claims: list[str] = []
    selected = fields or tuple(str(field) for field in facts)
    for field in selected:
        claims.extend(_value_claims(facts.get(field)))
    return tuple(dict.fromkeys(claims))


def _value_claims(value: Any) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        return tuple(
            claim
            for child in value.values()
            for claim in _value_claims(child)
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(
            claim
            for child in value
            for claim in _value_claims(child)
        )
    claim = str(value or "").strip()
    return (claim,) if claim else ()


def _question_field_key(value: Any) -> str:
    return "_".join(_TOKEN_RE.findall(str(value or "").casefold()))


def _is_negated(value: Any) -> bool:
    tokens = set(_TOKEN_RE.findall(str(value or "").casefold()))
    return bool(tokens & {"no", "not", "never", "without"})


def _tokens(value: Any) -> frozenset[str]:
    return frozenset(
        token
        for token in _TOKEN_RE.findall(str(value or "").casefold())
        if token not in _STOPWORDS
    )


def _flatten_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def _items(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _expected_values(value: Any) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            text = str(item.get("value") or "").strip() if isinstance(item, Mapping) else str(item or "").strip()
            if text:
                values.append(text)
    return tuple(values)


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item or "").strip() for item in value if str(item or "").strip())


def _atomic_categories() -> tuple[str, ...]:
    return (
        "actors",
        "actions",
        "states",
        "outputs",
        "constraints",
        "dependencies",
        "assumptions",
        "ambiguities",
        "non_goals",
    )


def _duplicates(values: Sequence[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _interval_payload(lower: float, upper: float) -> dict[str, Any]:
    return {
        "method": "wilson",
        "lower": lower,
        "upper": upper,
        "inference_scope": "descriptive fixed-corpus score interval; not a population user-utility claim",
    }


def _p0(case_id: str, category: str) -> dict[str, str]:
    return {"case_id": case_id, "category": category}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _case_id(case: Any) -> str:
    return str(getattr(case, "case_id", "") or getattr(case, "slug", "")).strip()


def _result_case_id(result: GreenfieldMatrixResult) -> str:
    case = _mapping(_mapping(result.evidence).get("case"))
    return str(case.get("id") or "").strip()


__all__ = ["SEMANTIC_RELEASE_SCORE_VERSION", "evaluate_semantic_release"]
