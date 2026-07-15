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
    for index in range(200):
        source = tmp_path / "evidence" / f"source-{index:03d}.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        source_text = f"Public source artifact {index} with unique domain reference {index * 17}.\n"
        source.write_text(source_text, encoding="utf-8")
        source_path = source.relative_to(tmp_path).as_posix()
        source_excerpt = source_text.strip()
        prompt = (
            f"Create a proposal for locus{index} nexus{index * 7} evidence review where operator{index} "
            f"records signal{index * 13}, approves checkpoint{index * 19}, preserves proof{index * 23}, "
            f"and reads back outcome{index * 29}."
        )
        span = "line 1"
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
                    review_evidence_sha256=_sha256(f"review {index}"),
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
    assert evaluation.summary["audit_count"] == 40


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


def test_release_corpus_rejects_an_excerpt_that_is_not_in_its_captured_artifact(tmp_path: Path) -> None:
    provenance, cases, audits = _release_corpus(tmp_path)
    fabricated_excerpt = "Fabricated excerpt that does not occur in the captured artifact."
    altered_provenance = replace(
        cases[0].provenance,
        source_excerpt=fabricated_excerpt,
        source_excerpt_sha256=_sha256(fabricated_excerpt),
    )
    altered_case = replace(cases[0], provenance=altered_provenance)
    altered_audit = replace(audits[0], source_excerpt_sha256=altered_provenance.source_excerpt_sha256)

    evaluation = provenance.evaluate_release_corpus(
        (altered_case, *cases[1:]),
        (altered_audit, *audits[1:]),
        repo_root=tmp_path,
    )

    assert not evaluation.passed
    assert "source_excerpt is not present in source_artifact_path" in "\n".join(evaluation.issues)


def test_release_audit_loader_rejects_nonversioned_payload(tmp_path: Path) -> None:
    provenance, _ = _modules()
    audit_file = tmp_path / "audit.json"
    audit_file.write_text(json.dumps({"audits": []}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="must declare version"):
        provenance.load_release_audit_file(audit_file)
