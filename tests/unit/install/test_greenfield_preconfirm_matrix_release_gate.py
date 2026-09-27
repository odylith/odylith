"""Focused fail-closed qualification tests for the Greenfield release matrix."""

from __future__ import annotations

import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_preconfirm_matrix import _release_outcome_statistics_passed


@pytest.mark.parametrize(
    ("statistics", "expected"),
    (
        ({"status": "passed", "passed": True}, True),
        ({"status": "passed", "passed": False}, False),
        ({"status": "passed"}, False),
        ({"status": "failed", "passed": True}, False),
        ({"status": "failed", "passed": False}, False),
    ),
)
def test_release_requires_both_statistics_decisions(
    statistics: dict[str, object], expected: bool
) -> None:
    assert _release_outcome_statistics_passed(
        proof_tier="release",
        outcome_statistics=statistics,
    ) is expected


def test_discovery_does_not_claim_release_statistics_qualification() -> None:
    assert _release_outcome_statistics_passed(
        proof_tier="discovery",
        outcome_statistics={},
    ) is True
