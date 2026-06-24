from __future__ import annotations

from types import SimpleNamespace

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues


def test_repetition_gate_allows_shared_release_wave_labels() -> None:
    package = SimpleNamespace(
        proposal={},
        backlog_result={
            "idea_files": {
                "B-001.md": "## Planning\nRelease wave: Harbor Incident Coordination state and evidence boundary.\n",
                "B-002.md": "## Planning\nRelease wave: Harbor Incident Coordination state and evidence boundary.\n",
            }
        },
        rendered_component_specs={
            "coordination.md": "## Trace Links\nRelease wave: Harbor Incident Coordination state and evidence boundary.\n",
        },
        rendered_atlas_sources={},
        project_brief_preview={},
        next_steps_preview={},
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert "repeats a noncanonical sentence" not in "\n".join(issues)
