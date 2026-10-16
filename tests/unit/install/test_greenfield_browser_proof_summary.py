from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"


def _module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return importlib.import_module("greenfield_browser_proof_summary")


def test_browser_proof_summary_marks_verified_clarification_as_not_applicable() -> None:
    module = _module()
    result = SimpleNamespace(
        name="assay drift prediction model",
        evidence={"case": {"expectation": "clarification_required"}},
        quality=SimpleNamespace(passed=True),
        browser_surface_proof_attempted=False,
        browser_surface_issues=(),
    )

    summary = module.browser_proof_summary((result,), include_browser_proof=True)

    assert summary["status"] == "passed"
    assert summary["applicable_case_count"] == 0
    assert summary["not_applicable_case_count"] == 1
    assert summary["issues"] == []
    assert summary["cases"] == [
        {
            "name": "assay drift prediction model",
            "status": "not_applicable",
            "attempted": False,
            "issues": [],
            "reason": "clarification-required flow verified without a committed governed surface",
        }
    ]


def test_browser_proof_summary_rejects_browser_attempt_for_clarification() -> None:
    module = _module()
    result = SimpleNamespace(
        name="security disclosure council",
        evidence={"case": {"expectation": "clarification_required"}},
        quality=SimpleNamespace(passed=True),
        browser_surface_proof_attempted=True,
        browser_surface_issues=(),
    )

    summary = module.browser_proof_summary((result,), include_browser_proof=True)

    assert summary["status"] == "failed"
    assert summary["cases"] == [
        {
            "name": "security disclosure council",
            "status": "failed",
            "attempted": True,
            "issues": ["browser proof ran for a clarification-required no-write case"],
        }
    ]


def test_browser_proof_summary_rejects_failed_no_write_clarification() -> None:
    module = _module()
    result = SimpleNamespace(
        name="assay drift prediction model",
        evidence={"case": {"expectation": "clarification_required"}},
        quality=SimpleNamespace(passed=False),
        browser_surface_proof_attempted=False,
        browser_surface_issues=(),
    )

    summary = module.browser_proof_summary((result,), include_browser_proof=True)

    assert summary["status"] == "failed"
    assert summary["cases"] == [
        {
            "name": "assay drift prediction model",
            "status": "failed",
            "attempted": False,
            "issues": ["clarification-required no-write contract did not pass"],
        }
    ]
