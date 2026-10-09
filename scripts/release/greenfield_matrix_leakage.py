"""Leakage-custody helpers for installed greenfield release matrix proof."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import collect_rendered_package_artifacts
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import GreenfieldModelAuthoringError
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
    resolve_source_citation,
)

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


def case_required_leakage_terms(case: GreenfieldMatrixCase) -> tuple[str, ...]:
    value = getattr(case, "required_terms", ())
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


def source_evidence_custody_issues(
    *, case: GreenfieldMatrixCase, generated_text: str = "", package: Any = None,
) -> tuple[str, ...]:
    """Check product claims while retaining exact, separately labeled source evidence."""

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
    citation_issues: list[str] = []
    if package is not None:
        generated_text = _product_claim_text(case=case, package=package, citation_issues=citation_issues)
    issues = (*citation_issues, *(
        f"source evidence identifier leaked into product artifacts: `{term}`"
        for term in terms
        if term_present(generated_text, term)
    ))
    excerpt = " ".join(str(getattr(provenance, "source_excerpt", "") or "").split())
    if len(excerpt.split()) >= 3 and term_present(generated_text, excerpt):
        issues += ("source evidence text leaked into product artifacts",)
    return issues


def _source_citations(
    value: Any, evidence: bytes, *, issues: list[str], path: str,
) -> set[tuple[str, int]]:
    """Collect structurally typed references; source bytes grant no product authority."""

    citations: set[tuple[str, int]] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if key == "source_refs":
                if not isinstance(child, list):
                    issues.append(f"invalid source reference container at {child_path}: expected a list")
                    continue
                for index, ref in enumerate(child):
                    ref_path = f"{child_path}/{index}"
                    if not isinstance(ref, Mapping) or not isinstance(ref.get("quote"), str) or not ref["quote"].strip():
                        issues.append(f"invalid source reference at {ref_path}: expected a nonempty quote")
                        continue
                    quote, occurrence = ref["quote"], ref.get("occurrence")
                    try:
                        resolve_source_citation(
                            evidence, {"quote": quote, "prefix": "", "anchor_occurrence": occurrence},
                            state_object=True,
                        )
                    except GreenfieldModelAuthoringError:
                        issues.append(f"invalid source reference at {ref_path}: quote or exact integer occurrence does not resolve")
                        continue
                    if "context" in ref:
                        try:
                            located = canonical_citation_from_host_selection(
                                evidence, {"quote": quote, "context": ref["context"]},
                            )
                        except GreenfieldModelAuthoringError:
                            issues.append(f"invalid source reference at {ref_path}: supplied context does not resolve")
                            continue
                        if located != {"quote": quote, "occurrence": occurrence}:
                            issues.append(f"invalid source reference at {ref_path}: context selects a different occurrence")
                            continue
                    citations.add((quote, occurrence))
            citations.update(_source_citations(child, evidence, issues=issues, path=child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            citations.update(_source_citations(child, evidence, issues=issues, path=f"{path}/{index}"))
    return citations


def _typed_claim_texts(value: Any, citations: set[tuple[str, int]], evidence: str) -> list[str]:
    if isinstance(value, Mapping):
        texts: list[str] = []
        for key, child in value.items():
            if key == "source_refs" and isinstance(child, list):
                for ref in child:
                    if (
                        isinstance(ref, Mapping) and isinstance(ref.get("quote"), str)
                        and type(ref.get("occurrence")) is int
                        and (ref["quote"], ref["occurrence"]) in citations
                    ):
                        excluded = {"quote"}
                        context = ref.get("context")
                        if isinstance(context, str):
                            try:
                                located = canonical_citation_from_host_selection(
                                    evidence.encode("utf-8"), {"quote": ref["quote"], "context": context},
                                )
                            except GreenfieldModelAuthoringError:
                                pass
                            else:
                                if located == {"quote": ref["quote"], "occurrence": ref["occurrence"]}:
                                    excluded.add("context")
                        ref = {key: text for key, text in ref.items() if key not in excluded}
                    texts.extend(_typed_claim_texts(ref, citations, evidence))
            elif key == "radar_sections" and isinstance(child, Mapping):
                texts.extend(
                    _without_labeled_citations(f"\n## {heading}\n{body}", citations)
                    for heading, body in child.items()
                )
            else:
                texts.extend(_typed_claim_texts(child, citations, evidence))
        return texts
    if isinstance(value, (list, tuple)):
        return [text for child in value for text in _typed_claim_texts(child, citations, evidence)]
    return [value] if isinstance(value, str) else []


def _without_labeled_citations(text: str, citations: set[tuple[str, int]]) -> str:
    """Exclude only exact citation blocks in the existing source detail sections."""

    fragments = {
        fragment
        for quote, occurrence in citations
        for fragment in (
            f"Source citation (occurrence {occurrence}): {quote}",
            f"Source citation (occurrence {occurrence}):\n\n" + "\n".join(f"> {line}" for line in quote.splitlines()),
        )
    }
    for fragment in sorted(fragments, key=len, reverse=True):
        cursor = 0
        while (start := text.find(fragment, cursor)) >= 0:
            end = start + len(fragment)
            heading_start = text.rfind("\n## ", 0, start)
            heading = text[heading_start + 4:].splitlines()[0].casefold() if heading_start >= 0 else ""
            if (
                heading in {"source boundaries", "source conditional guards", "source proof duties", "source state lifecycle"}
                and (start == 0 or text[start - 1] == "\n")
                and (end == len(text) or text[end] in "\r\n")
            ):
                text = text[:start] + text[end:]
                cursor = start
            else:
                cursor = end
    return text


def _product_claim_text(*, case: GreenfieldMatrixCase, package: Any, citation_issues: list[str]) -> str:
    evidence = case.initial_prompt.encode("utf-8")
    proposal = getattr(package, "proposal", None)
    claims: dict[str, Any] = {
        "source_launch": getattr(package, "source_launch_readback", None),
        "project": getattr(package, "project_dashboard_preview", None),
        "atlas_catalog": getattr(package, "atlas_catalog_rows", None),
    }
    if isinstance(proposal, Mapping):
        claims["proposal"] = {
            key: child for key, child in proposal.items() if key not in {"intent", "observed_source"}
        }
        intent = proposal.get("intent")
        authored = intent.get("authored_semantics") if isinstance(intent, Mapping) else None
        if isinstance(intent, Mapping):
            claims["intent"] = {
                key: child for key, child in intent.items() if key not in {"prompt", "authored_semantics"}
            }
        if isinstance(authored, Mapping):
            claims["authored_semantics"] = {
                key: child for key, child in authored.items() if key != "source_duty"
            }
            source_duty = authored.get("source_duty")
            if isinstance(source_duty, Mapping):
                # The retained ledger is source custody; its projected lifecycle is product truth.
                claims["source_duty_lifecycle"] = source_duty.get("lifecycle")
    accepted = getattr(package, "accepted_project_preview", None)
    if isinstance(accepted, Mapping):
        claims["accepted"] = {
            key: accepted.get(key) for key in ("title", "source_launch", "created")
        }
    citations: set[tuple[str, int]] = set()
    for name, value in claims.items():
        citations.update(_source_citations(value, evidence, issues=citation_issues, path=name))
    texts = [
        _without_labeled_citations(artifact.text, citations)
        if artifact.surface in {"Radar workstream", "Registry component spec"}
        else artifact.text
        for artifact in collect_rendered_package_artifacts(package)
    ]
    for value in claims.values():
        texts.extend(_typed_claim_texts(value, citations, case.initial_prompt))
    return "\n".join(texts)


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
