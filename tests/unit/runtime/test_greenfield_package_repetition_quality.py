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


def test_repetition_gate_rejects_repeated_markdown_section_boilerplate() -> None:
    package = SimpleNamespace(
        proposal={},
        backlog_result={
            "idea_files": {
                f"B-{index:03d}.md": "## Migration/Compatibility\n- No migration impact recorded yet.\n"
                for index in range(1, 4)
            }
        },
        rendered_component_specs={},
        rendered_atlas_sources={},
        project_brief_preview={},
        next_steps_preview={},
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert "repeats noncanonical prose" in "\n".join(issues)
