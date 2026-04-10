from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import plan_progress


def test_collect_plan_progress_excludes_non_goal_traceability_and_impacted_area_tasks_from_next_tasks(
    tmp_path: Path,
) -> None:
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(
        "Status: In progress\n\n"
        "Created: 2026-03-13\n\n"
        "Updated: 2026-03-13\n\n"
        "## Success Criteria\n"
        "- [ ] Land the primary runtime slice.\n"
        "## Non-Goals\n"
        "- [ ] Migrate every service in the repo.\n"
        "## Impacted Areas\n"
        "- [ ] /Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md\n"
        "## Traceability\n"
        "### Runbooks\n"
        "- [ ] /Users/freedom/code/odylith/odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md\n"
        "## Rollout/Communication\n"
        "- [ ] Document rollout steps for maintainers.\n",
        encoding="utf-8",
    )

    progress = plan_progress.collect_plan_progress(plan_path)

    assert progress["all_total_tasks"] == 5
    assert progress["all_done_tasks"] == 0
    assert progress["total_tasks"] == 2
    assert progress["done_tasks"] == 0
    assert progress["progress_basis"] == "execution_checklist"
    assert progress["next_tasks"] == [
        "Land the primary runtime slice.",
        "Document rollout steps for maintainers.",
    ]


def test_collect_plan_progress_counts_only_execution_sections(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(
        "Status: In progress\n\n"
        "Created: 2026-04-09\n\n"
        "Updated: 2026-04-09\n\n"
        "## Learnings\n"
        "- [x] Something already learned.\n"
        "## Must-Ship\n"
        "- [x] Ship the core slice.\n"
        "- [ ] Ship the regression tests.\n"
        "## Defer\n"
        "- [ ] A deferred item.\n"
        "## Open Questions\n"
        "- [ ] A remaining question.\n"
        "## Validation\n"
        "- [x] `pytest -q tests/unit/test_core.py`\n",
        encoding="utf-8",
    )

    progress = plan_progress.collect_plan_progress(plan_path)

    assert progress["all_total_tasks"] == 6
    assert progress["all_done_tasks"] == 3
    assert progress["total_tasks"] == 3
    assert progress["done_tasks"] == 2
    assert progress["progress_ratio"] == 0.6667
    assert progress["next_tasks"] == [
        "Ship the regression tests.",
    ]
