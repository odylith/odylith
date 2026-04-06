from __future__ import annotations

from odylith.runtime.evaluation import odylith_benchmark_live_execution as live_execution


def test_release_publication_validator_backed_completion_accepts_already_reflects_report_summary() -> None:
    assert live_execution._validator_backed_completion_satisfied(  # noqa: SLF001
        scenario={
            "family": "release_publication",
            "allow_noop_completion": True,
            "changed_paths": ["README.md"],
            "required_paths": ["README.md"],
            "needs_write": True,
        },
        structured_output={
            "summary": "The copied artifacts and publication docs already reflect the validated report, so no publication changes were needed.",
            "validation_summary": "Focused publication validators already pass on the current tree.",
        },
        status="blocked",
        candidate_write_paths=[],
        validators_passed=True,
        required_path_misses=[],
    )
