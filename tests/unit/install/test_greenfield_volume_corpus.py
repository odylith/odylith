from __future__ import annotations

import importlib
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
CORPUS_ROOT = REPO_ROOT / "tests" / "fixtures" / "greenfield-volume"
CASE_FILES = (
    "public-health-education.v1.json",
    "science-deeptech.v1.json",
    "finance-legal-enterprise.v1.json",
    "logistics-infrastructure.v1.json",
    "developer-data-security.v1.json",
    "consumer-creative-community.v1.json",
)


def _modules():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return (
        importlib.import_module("greenfield_matrix_case_file"),
        importlib.import_module("greenfield_matrix_campaign"),
    )


def test_volume_corpus_is_prompt_grounded_diverse_and_campaign_ready() -> None:
    case_file, campaign = _modules()
    cases = tuple(
        case
        for file_name in CASE_FILES
        for case in case_file.load_case_file(CORPUS_ROOT / file_name)
    )

    assert len(cases) == 240
    assert len({case.name.casefold() for case in cases}) == 240
    assert all(len(case.prompt.split()) >= 55 for case in cases)
    assert all(len(case.required_terms) >= 4 for case in cases)
    assert all(len(case.leakage_terms) >= 3 for case in cases)
    assert all(len(case.tags) >= 2 for case in cases)
    assert all(len(case.stressors) >= 3 for case in cases)

    coverage = campaign.stressor_coverage(cases, campaign.DEFAULT_HIGH_VARIANCE_STRESSORS)
    variance = campaign.variance_evaluation(cases, campaign.DEFAULT_HIGH_VARIANCE_STRESSORS)

    assert coverage["missing_required"] == []
    assert coverage["cases_without_stressors"] == []
    assert variance["status"] == "passed"
    assert variance["score"] == 10


def test_volume_corpus_is_discovery_only_until_it_carries_explicit_axis_and_source_evidence() -> None:
    case_file, _campaign = _modules()
    cases = tuple(
        case
        for file_name in CASE_FILES
        for case in case_file.load_case_file(CORPUS_ROOT / file_name)
    )

    assert all(not case.input_style_declared for case in cases)
    assert all(not case.metamorphic_group and not case.metamorphic_transform for case in cases)
    assert {case.provenance.corpus_tier for case in cases} == {"synthetic_regression"}
