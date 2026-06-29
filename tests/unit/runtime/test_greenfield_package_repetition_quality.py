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


def test_repetition_gate_rejects_repeated_accepted_intent_story_prose() -> None:
    story = (
        "Hospital pharmacists need one governed workspace to review urgent neonatal medication exceptions "
        "with dose evidence, prescriber approval, and bedside release readiness."
    )
    proof = (
        "Release succeeds when one exception can be reviewed with dose evidence, approval history, "
        "and bedside readiness proof before medication release."
    )
    package = SimpleNamespace(
        proposal={
            "intent": {
                "title": "Neonatal medication exception desk",
                "product_story": story,
                "proof_boundary": proof,
            },
            "semantic_model": {
                "domain_ontology": {"state_object": "Medication exception"},
                "first_path_contract": {
                    "raw_path": "A pharmacist reviews one exception and publishes bedside readiness proof.",
                    "events": [
                        {"text": "A pharmacist reviews one exception and publishes bedside readiness proof"}
                    ],
                },
            },
        },
        backlog_result={
            "idea_files": {
                "B-001.md": f"## Product story\n{story}\n\n## Proof boundary\n{proof}\n",
                "B-002.md": f"## Product story\n{story}\n\n## Proof boundary\n{proof}\n",
            }
        },
        rendered_component_specs={
            "exception-review.md": f"## Product story\n{story}\n\n## Proof boundary\n{proof}\n",
        },
        rendered_atlas_sources={},
        project_brief_preview={"product_story": story, "proof_boundary": proof},
        next_steps_preview={"summary": story, "proof": proof},
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert "repeats noncanonical prose" in "\n".join(issues)


def test_repetition_gate_allows_section_qualified_first_path_event_custody() -> None:
    event = "Publish a reviewed evacuation readiness state with accountable assignments and public update proof"
    compact_event = "Publish a reviewed evacuation readiness state with accountable assignments"
    package = SimpleNamespace(
        proposal={
            "intent": {
                "first_path": (
                    "County coordinators ingest source reports, then publish a reviewed evacuation readiness "
                    "state with accountable assignments."
                )
            },
            "semantic_model": {
                "domain_ontology": {"state_object": "Evacuation readiness state"},
                "first_path_contract": {
                    "raw_path": (
                        "County coordinators ingest source reports, then publish a reviewed evacuation readiness "
                        "state with accountable assignments."
                    ),
                    "events": [{"text": event}],
                },
            },
        },
        backlog_result={
            "idea_files": {
                f"B-{index:03d}.md": f"## First path\n- {compact_event}.\n"
                for index in range(1, 4)
            }
        },
        rendered_component_specs={},
        rendered_atlas_sources={},
        project_brief_preview={"first_path": compact_event},
        next_steps_preview={"implementation_prompt": compact_event},
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert "repeats noncanonical prose" not in "\n".join(issues)


def test_repetition_gate_still_rejects_first_path_event_without_semantic_custody() -> None:
    event = "Publish a reviewed evacuation readiness state with accountable assignments"
    package = SimpleNamespace(
        proposal={},
        backlog_result={
            "idea_files": {
                f"B-{index:03d}.md": f"## First path\n- {event}.\n"
                for index in range(1, 4)
            }
        },
        rendered_component_specs={},
        rendered_atlas_sources={},
        project_brief_preview={"first_path": event},
        next_steps_preview={"implementation_prompt": event},
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert "repeats noncanonical prose" in "\n".join(issues)


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
