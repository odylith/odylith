"""Leakage-custody helpers for installed greenfield release matrix proof."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
import platform_domain_leakage_check as platform_domain_leakage


def case_preflight_leakage_terms(case: GreenfieldMatrixCase) -> tuple[str, ...]:
    return platform_domain_leakage.case_leakage_term_candidates(case)


def case_declared_leakage_terms(case: GreenfieldMatrixCase) -> tuple[str, ...]:
    value = getattr(case, "leakage_terms", ())
    if isinstance(value, (str, bytes)):
        raw_terms = (str(value),)
    else:
        raw_terms = tuple(str(term) for term in value) if isinstance(value, Sequence) else ()
    return platform_domain_leakage.domain_leakage_terms_from_terms(raw_terms)


def case_generated_leakage_terms(
    *,
    case: GreenfieldMatrixCase,
    generated_text: str,
    platform_baseline_terms: Sequence[str] = (),
) -> tuple[str, ...]:
    declared_terms = case_declared_leakage_terms(case)
    candidate_terms = platform_domain_leakage.case_leakage_term_candidates(case)
    native_terms = frozenset(str(term).strip() for term in platform_baseline_terms if str(term).strip())
    declared_present = tuple(
        term for term in declared_terms if term not in native_terms and term_present(generated_text, term)
    )
    if declared_present:
        return tuple(dict.fromkeys(declared_present))
    supplemental_present = tuple(
        term
        for term in candidate_terms
        if term_present(generated_text, term)
        and term not in declared_terms
        and term not in native_terms
    )
    return tuple(dict.fromkeys((*declared_present, *supplemental_present)))


def source_evidence_custody_issues(*, case: GreenfieldMatrixCase, generated_text: str) -> tuple[str, ...]:
    """Reject raw source sentinels that cross into rendered product artifacts."""

    provenance = getattr(case, "provenance", None)
    if str(getattr(provenance, "corpus_tier", "") or "").strip() != "source_provenanced":
        return ()
    terms = tuple(
        dict.fromkeys(
            str(term).strip()
            for term in getattr(case, "leakage_terms", ())
            if str(term).strip()
        )
    )
    return tuple(
        f"source evidence identifier leaked into product artifacts: `{term}`"
        for term in terms
        if term_present(generated_text, term)
    )


def platform_baseline_required_terms(
    *,
    repo_root: Path,
    release_dir: Path,
    cases: Sequence[GreenfieldMatrixCase],
) -> tuple[str, ...]:
    terms = tuple(
        sorted(
            {
                term
                for case in cases
                for term in platform_domain_leakage.case_leakage_term_candidates(case)
            }
        )
    )
    if not terms:
        return ()
    findings = platform_domain_leakage.scan_platform_custody(
        repo_root=repo_root,
        dist_dir=release_dir,
        terms=terms,
    )
    return tuple(sorted({str(finding.term).strip() for finding in findings if str(finding.term).strip()}))


def with_platform_leakage_issues(
    *,
    repo_root: Path,
    results: Sequence[GreenfieldMatrixResult],
    release_dir: Path,
) -> tuple[GreenfieldMatrixResult, ...]:
    checked_terms = tuple(
        sorted(
            {
                str(term).strip()
                for result in results
                for term in result.platform_leakage_terms
                if str(term).strip()
            }
        )
    )
    if not checked_terms:
        return tuple(results)
    findings = platform_domain_leakage.scan_platform_custody(
        repo_root=repo_root,
        dist_dir=release_dir,
        terms=checked_terms,
    )
    if not findings:
        return tuple(results)
    issues_by_term: dict[str, list[str]] = {}
    for finding in findings:
        issues_by_term.setdefault(str(finding.term).strip(), []).append(_platform_leakage_issue(finding))
    return tuple(
        _result_with_platform_leakage_issues(
            result=result,
            issues=tuple(
                dict.fromkeys(
                    issue
                    for term in result.platform_leakage_terms
                    for issue in issues_by_term.get(str(term).strip(), ())
                )
            ),
        )
        for result in results
    )


def term_present(text: str, term: str) -> bool:
    text_tokens = _tokenize(text)
    term_tokens = _tokenize(term)
    if not text_tokens or not term_tokens or len(term_tokens) > len(text_tokens):
        return False
    width = len(term_tokens)
    return any(
        all(
            _token_matches(source_token, term_token)
            for source_token, term_token in zip(text_tokens[index : index + width], term_tokens, strict=True)
        )
        for index in range(len(text_tokens) - width + 1)
    )


def _result_with_platform_leakage_issues(
    *,
    result: GreenfieldMatrixResult,
    issues: Sequence[str],
) -> GreenfieldMatrixResult:
    leakage_issues = tuple(
        dict.fromkeys(str(issue).strip() for issue in issues if str(issue).strip())
    )
    if not leakage_issues:
        return result
    quality_issues = tuple(dict.fromkeys((*result.quality.issues, *leakage_issues)))
    score_explanation = tuple(
        dict.fromkeys(
            (
                "platform domain leakage proof failed; generated terms appeared in protected platform custody",
                *result.quality.score_explanation,
            )
        )
    )
    return replace(
        result,
        status="failed",
        quality=replace(
            result.quality,
            passed=False,
            issues=quality_issues,
            score=0,
            score_explanation=score_explanation,
        ),
        platform_leakage_issues=leakage_issues,
    )


def _platform_leakage_issue(finding: platform_domain_leakage.LeakageFinding) -> str:
    return (
        "platform domain leakage after generated artifact readback: "
        f"{finding.location}:{finding.line} leaked `{finding.term}`"
    )


def _token_matches(source_token: str, term_token: str) -> bool:
    return bool(set(_token_forms(source_token)) & set(_token_forms(term_token)))


def _token_forms(token: str) -> tuple[str, ...]:
    value = str(token or "").casefold()
    forms = [value]
    if len(value) > 2:
        forms.append(f"{value}s")
    if len(value) > 3 and value.endswith("y"):
        forms.append(f"{value[:-1]}ies")
    if len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
        forms.append(value[:-1])
    if len(value) > 4 and value.endswith("ies"):
        forms.append(f"{value[:-3]}y")
    return tuple(dict.fromkeys(form for form in forms if form))


def _tokenize(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    for char in str(text or "").casefold():
        if char.isalnum():
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tuple(tokens)
