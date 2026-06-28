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


def test_repetition_gate_rejects_repeated_risk_prose_across_child_artifacts() -> None:
    repeated_risk = "Combining cart, payment, and order state would hide failure recovery."
    package = SimpleNamespace(
        proposal={},
        backlog_result={
            "idea_files": {
                f"B-{index:03d}.md": f"## Risks\n- {repeated_risk}\n"
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


def test_repetition_gate_allows_shared_customer_metadata() -> None:
    package = SimpleNamespace(
        proposal={},
        backlog_result={
            "idea_files": {
                f"B-{index:03d}.md": "## Customer\nSemiconductor lab operators who need custody evidence.\n"
                for index in range(1, 4)
            }
        },
        rendered_component_specs={},
        rendered_atlas_sources={},
        project_brief_preview={},
        next_steps_preview={},
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert "repeats noncanonical prose" not in "\n".join(issues)


def test_repetition_gate_allows_complete_semantic_event_custody() -> None:
    event = "A supervisor reviews the decision package with traceable documents, comments, checks, and final status"
    package = SimpleNamespace(
        proposal={
            "semantic_model": {
                "domain_ontology": {},
                "first_path_contract": {
                    "events": [{"text": event}],
                },
            }
        },
        backlog_result={},
        rendered_component_specs={},
        rendered_atlas_sources={},
        project_brief_preview={"first_path": event},
        next_steps_preview={"implementation_prompt": event},
        accepted_project_preview={"source_launch": {"implementation_prompt": event}},
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert "repeats noncanonical prose" not in "\n".join(issues)


def test_rendered_package_quality_rejects_malformed_connector_sequences() -> None:
    package = SimpleNamespace(
        proposal={},
        backlog_result={
            "idea_files": {
                "B-001.md": "## Boundary\nKeep this slice bounded and or defer broader automation.\n",
            }
        },
        rendered_component_specs={},
        rendered_atlas_sources={},
        project_brief_preview={},
        next_steps_preview={},
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert "malformed connector sequence" in "\n".join(issues)
