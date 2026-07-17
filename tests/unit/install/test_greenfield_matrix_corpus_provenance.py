from __future__ import annotations

import hashlib
import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _modules():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return (
        importlib.import_module("greenfield_matrix_corpus_provenance"),
        importlib.import_module("greenfield_preconfirm_matrix_cases"),
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _release_corpus(tmp_path: Path):
    provenance, cases_module = _modules()
    cases = []
    audits = []
    stressors = tuple(importlib.import_module("greenfield_matrix_stressors").DEFAULT_HIGH_VARIANCE_STRESSORS)
    input_styles = (
        "direct_request",
        "edited_confirmation",
        "pasted_brief",
        "research_evidence",
        "thin_request",
    )
    for index in range(200):
        source_index = index // 2 if index < 40 else index
        source = tmp_path / "evidence" / f"source-{source_index:03d}.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        source_text = (
            f"Public source artifact {source_index} baseline context.\n"
            f"Public source artifact {source_index} variant context.\n"
        )
        source.write_text(source_text, encoding="utf-8")
        source_path = source.relative_to(tmp_path).as_posix()
        span = "line 1" if index % 2 == 0 else "line 2"
        source_excerpt = source_text.splitlines()[0 if span == "line 1" else 1]
        prompt = (
            f"Create a proposal for locus{index} nexus{index * 7} evidence review where operator{index} "
            f"records signal{index * 13}, approves checkpoint{index * 19}, preserves proof{index * 23}, "
            f"and reads back outcome{index * 29}."
        )
        case_id = f"release-{index:03d}"
        source_hash = _sha256(source_text)
        case = cases_module.GreenfieldMatrixCase(
            name=f"release corpus case {index}",
            prompt=prompt,
            required_terms=(f"locus{index}",),
            leakage_terms=(f"nexus{index * 7}",),
            case_id=case_id,
            tags=(f"family-{index % 10}", "release"),
            stressors=(stressors[index % len(stressors)],),
            input_style=input_styles[index % len(input_styles)],
            input_style_declared=True,
            metamorphic_group=f"source-pair-{index // 2:03d}" if index < 40 else "",
            metamorphic_transform=("baseline" if index % 2 == 0 else "source_variant") if index < 40 else "",
            provenance=provenance.GreenfieldCaseProvenance(
                corpus_tier="source_provenanced",
                schema_version=provenance.CASE_PROVENANCE_VERSION,
                source_id=f"public-source-{index:03d}",
                source_uri=f"https://example.org/source/{index}",
                source_artifact_path=source_path,
                source_artifact_sha256=source_hash,
                source_span=span,
                source_span_sha256=_sha256(span),
                source_excerpt=source_excerpt,
                source_excerpt_sha256=_sha256(source_excerpt),
                retrieved_on="2026-07-14",
                license_or_consent="public-domain",
                source_family=f"family-{index % 10}",
                derivation_method="bounded-manual-abstraction-v1",
                derived_prompt_sha256=_sha256(prompt),
                derivation_author="corpus-curator",
            ),
        )
        cases.append(case)
        if index < 40:
            review_evidence = tmp_path / "evidence" / "reviews" / f"review-{index:03d}.txt"
            review_evidence.parent.mkdir(parents=True, exist_ok=True)
            review_text = f"review {index}"
            review_evidence.write_text(review_text, encoding="utf-8")
            audits.append(
                provenance.GreenfieldReleaseAudit(
                    case_id=case_id,
                    prompt_sha256=_sha256(prompt),
                    source_artifact_sha256=source_hash,
                    source_excerpt_sha256=_sha256(source_excerpt),
                    reviewer_id="independent-reviewer",
                    reviewed_on="2026-07-14",
                    review_status="approved",
                    independent=True,
                    review_evidence_path=review_evidence.relative_to(tmp_path).as_posix(),
                    review_evidence_sha256=_sha256(review_text),
                )
            )
    return provenance, tuple(cases), tuple(audits)


def test_release_corpus_requires_source_provenance_not_synthetic_prompts(tmp_path: Path) -> None:
    provenance, cases_module = _modules()
    evaluation = provenance.evaluate_release_corpus(
        (
            cases_module.GreenfieldMatrixCase(
                name="synthetic",
                prompt="Create a proposal for synthetic evidence review.",
                required_terms=("synthetic",),
                leakage_terms=("synthetic evidence",),
            ),
        ),
        repo_root=tmp_path,
    )

    assert not evaluation.passed
    assert "requires at least 200 source-provenanced cases" in "\n".join(evaluation.issues)
    assert "corpus_tier must be source_provenanced" in "\n".join(evaluation.issues)


def test_release_corpus_accepts_audited_source_provenanced_diverse_evidence(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)

    evaluation = provenance.evaluate_release_corpus(cases, audits, repo_root=tmp_path)

    assert evaluation.passed, evaluation.issues
    assert evaluation.summary["case_count"] == 200
    assert evaluation.summary["source_family_count"] == 10
    assert evaluation.summary["source_id_count"] == 200
    assert evaluation.summary["source_uri_count"] == 200
    assert evaluation.summary["audit_count"] == 40


def test_release_corpus_rejects_implicit_input_style_and_incomplete_metamorphic_pair(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)
    unlabeled = replace(cases[0], input_style_declared=False)
    unpaired = replace(cases[1], metamorphic_transform="baseline")

    evaluation = provenance.evaluate_release_corpus(
        (unlabeled, unpaired, *cases[2:]),
        audits,
        repo_root=tmp_path,
    )

    issues = "\n".join(evaluation.issues)
    assert not evaluation.passed
    assert "without an explicit input_style" in issues
    assert "incomplete metamorphic groups" in issues


def test_release_corpus_rejects_duplicate_prompt_and_unreviewed_audit_coverage(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)
    duplicate = cases[1].__class__(
        name="renamed duplicate",
        prompt=cases[0].prompt,
        required_terms=cases[1].required_terms,
        leakage_terms=cases[1].leakage_terms,
        case_id="release-duplicate",
        tags=cases[1].tags,
        stressors=cases[1].stressors,
        provenance=cases[1].provenance,
    )

    evaluation = provenance.evaluate_release_corpus((*cases, duplicate), audits, repo_root=tmp_path)

    message = "\n".join(evaluation.issues)
    assert "duplicate prompts" in message
    assert "derived_prompt_sha256 does not match the case prompt" in message
    assert "approved independent audits" in message


def test_release_corpus_rejects_an_excerpt_outside_its_declared_source_span(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)
    off_span_excerpt = "Public source artifact 0 variant context."
    altered_provenance = replace(
        cases[0].provenance,
        source_excerpt=off_span_excerpt,
        source_excerpt_sha256=_sha256(off_span_excerpt),
    )
    altered_case = replace(cases[0], provenance=altered_provenance)
    altered_audit = replace(audits[0], source_excerpt_sha256=altered_provenance.source_excerpt_sha256)

    evaluation = provenance.evaluate_release_corpus(
        (altered_case, *cases[1:]),
        (altered_audit, *audits[1:]),
        repo_root=tmp_path,
    )

    assert not evaluation.passed
    assert "source_excerpt is not present in declared source_span" in "\n".join(evaluation.issues)


def test_release_corpus_rejects_an_unresolvable_declared_source_span(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)
    unresolved_span = "lines 2-3"
    altered_case = replace(
        cases[0],
        provenance=replace(
            cases[0].provenance,
            source_span=unresolved_span,
            source_span_sha256=_sha256(unresolved_span),
        ),
    )

    evaluation = provenance.evaluate_release_corpus(
        (altered_case, *cases[1:]), audits, repo_root=tmp_path
    )

    assert not evaluation.passed
    assert "source_span does not resolve against source_artifact_path" in "\n".join(evaluation.issues)


def test_release_corpus_requires_stored_hash_matched_review_evidence(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)
    missing_evidence = replace(audits[0], review_evidence_path="evidence/reviews/missing.txt")
    missing_evaluation = provenance.evaluate_release_corpus(
        cases, (missing_evidence, *audits[1:]), repo_root=tmp_path
    )
    mismatched_evidence = replace(audits[0], review_evidence_sha256=_sha256("different review"))
    mismatched_evaluation = provenance.evaluate_release_corpus(
        cases, (mismatched_evidence, *audits[1:]), repo_root=tmp_path
    )

    assert not missing_evaluation.passed
    assert "review_evidence_path does not exist" in "\n".join(missing_evaluation.issues)
    assert not mismatched_evaluation.passed
    assert "review_evidence_sha256 does not match review_evidence_path" in "\n".join(
        mismatched_evaluation.issues
    )


def test_release_corpus_rejects_review_evidence_outside_the_repository_root(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)
    escaped_evidence = replace(audits[0], review_evidence_path="../review.txt")

    evaluation = provenance.evaluate_release_corpus(
        cases, (escaped_evidence, *audits[1:]), repo_root=tmp_path
    )

    assert not evaluation.passed
    assert "must use a repository-relative review_evidence_path" in "\n".join(evaluation.issues)


def test_release_corpus_rejects_non_boolean_audit_independence(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)
    untyped_audit = replace(audits[0], independent="false")

    evaluation = provenance.evaluate_release_corpus(
        cases, (untyped_audit, *audits[1:]), repo_root=tmp_path
    )

    assert not evaluation.passed
    assert "must define independent as a boolean" in "\n".join(evaluation.issues)


def test_release_corpus_rejects_reused_source_id_and_uri(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)
    duplicated_source = replace(
        cases[1].provenance,
        source_id=cases[0].provenance.source_id,
        source_uri=cases[0].provenance.source_uri,
    )
    duplicated_case = replace(cases[1], provenance=duplicated_source)

    evaluation = provenance.evaluate_release_corpus(
        (cases[0], duplicated_case, *cases[2:]), audits, repo_root=tmp_path
    )

    issues = "\n".join(evaluation.issues)
    assert not evaluation.passed
    assert "source_id `public-source-000` has 2 cases" in issues
    assert "source_uri `https://example.org/source/0` has 2 cases" in issues


def test_release_audit_loader_rejects_nonversioned_payload(tmp_path: Path) -> None:
    provenance, _ = _modules()
    audit_file = tmp_path / "audit.json"
    audit_file.write_text(json.dumps({"audits": []}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="must declare version"):
        provenance.load_release_audit_file(audit_file)


def test_release_audit_loader_requires_json_boolean_independence(tmp_path: Path) -> None:
    provenance, _ = _modules()
    audit_file = tmp_path / "audit.json"
    audit_file.write_text(
        json.dumps(
            {
                "version": provenance.RELEASE_AUDIT_VERSION,
                "audits": [{"case_id": "release-000", "independent": "false"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="independent as a JSON boolean"):
        provenance.load_release_audit_file(audit_file)
