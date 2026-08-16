from __future__ import annotations

import hashlib
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_corpus_provenance import GreenfieldCaseProvenance
from greenfield_matrix_metamorphic import evaluate_metamorphic_outputs
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from tests.unit.install.test_greenfield_matrix_metamorphic import _result


def test_independent_synthetic_pair_uses_sealed_authoring_and_transform_identity() -> None:
    cases = _synthetic_cases()

    evaluation = evaluate_metamorphic_outputs(cases=cases, results=tuple(_result(case) for case in cases))

    assert evaluation["status"] == "passed"


def test_source_provenanced_pair_still_requires_source_identity_and_hash() -> None:
    provenance = GreenfieldCaseProvenance(corpus_tier="source_provenanced")
    cases = _pair(provenance, provenance)

    evaluation = evaluate_metamorphic_outputs(cases=cases, results=tuple(_result(case) for case in cases))

    assert evaluation["status"] == "failed"
    assert any("does not have one source identity" in issue for issue in evaluation["issues"])
    assert any("does not have one source artifact hash" in issue for issue in evaluation["issues"])


def test_synthetic_schema_version_cannot_substitute_for_prompt_hash() -> None:
    provenance = GreenfieldCaseProvenance(
        corpus_tier="independent_synthetic_release_holdout",
        schema_version="odylith.greenfield.final-holdout.v1",
        derivation_method="independently-authored holdout transform",
    )
    cases = _pair(provenance, provenance)

    evaluation = evaluate_metamorphic_outputs(cases=cases, results=tuple(_result(case) for case in cases))

    assert evaluation["status"] == "failed"
    assert any("sealed transform hashes" in issue for issue in evaluation["issues"])


def _synthetic_cases() -> tuple[GreenfieldMatrixCase, GreenfieldMatrixCase]:
    prompts = ("A curator groups observation markers.", "Group observation markers for a curator.")
    provenances = tuple(
        GreenfieldCaseProvenance(
            corpus_tier="independent_synthetic_release_holdout",
            derivation_method="independently-authored holdout transform",
            derivation_author="sealed-holdout-author",
            derived_prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        )
        for prompt in prompts
    )
    return _pair(*provenances, prompts=prompts)


def _pair(
    left: GreenfieldCaseProvenance,
    right: GreenfieldCaseProvenance,
    *,
    prompts: tuple[str, str] = ("Create an evidence workspace.", "Create an evidence workspace from a topic."),
) -> tuple[GreenfieldMatrixCase, GreenfieldMatrixCase]:
    cases = tuple(
        GreenfieldMatrixCase(
            case_id=f"sealed-pair-{index}",
            name=f"sealed pair {index}",
            prompt=prompt,
            required_terms=("evidence",),
            provenance=provenance,
            metamorphic_group="sealed-authoring-pair",
            metamorphic_transform=transform,
        )
        for index, (prompt, provenance, transform) in enumerate(
            zip(prompts, (left, right), ("prose", "checklist"), strict=True),
            start=1,
        )
    )
    return cases[0], cases[1]
