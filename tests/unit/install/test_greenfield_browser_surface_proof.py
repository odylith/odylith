from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _load_module(path: Path, name: str):
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module():
    return _load_module(SCRIPTS_ROOT / "greenfield_browser_surface_proof.py", "greenfield_browser_surface_proof")


def test_browser_surface_proof_scope_is_generated_state_matrix() -> None:
    module = _module()

    assert module.BROWSER_SURFACE_PROOF_SCOPE == "per_case_headless_generated_surface_state_matrix"


def test_browser_surface_proof_expected_abort_filter_stays_local_and_narrow() -> None:
    module = _module()

    assert module._is_expected_local_abort(
        url="http://127.0.0.1:12345/odylith/radar/radar.html",
        error_text="net::ERR_ABORTED",
        resource_type="document",
    )
    assert module._is_expected_local_abort(
        url="http://127.0.0.1:12345/odylith/compass/runtime/current.v1.json",
        error_text="net::ERR_ABORTED",
        resource_type="xhr",
    )
    assert module._is_expected_local_abort(
        url="http://127.0.0.1:12345/odylith/casebook/casebook-detail-shard-001.v1.js",
        error_text="net::ERR_ABORTED",
        resource_type="script",
    )
    assert not module._is_expected_local_abort(
        url="http://127.0.0.1:12345/odylith/radar/backlog-payload.v1.js",
        error_text="net::ERR_ABORTED",
        resource_type="script",
    )
    assert not module._is_expected_local_abort(
        url="https://cdn.example.test/odylith/radar/radar.html",
        error_text="net::ERR_ABORTED",
        resource_type="document",
    )
    assert not module._is_expected_local_abort(
        url="http://127.0.0.1:12345/odylith/radar/radar.html",
        error_text="net::ERR_FAILED",
        resource_type="document",
    )


def test_atlas_state_assertion_requires_generated_diagram_state() -> None:
    module = _module()

    issues = module._atlas_state_assertion_issues(
        diagram_count=4,
        stat_total_text="4",
        active_diagram="D-003",
        displayed_diagram="D-003",
        displayed_title="Evidence Flow Diagram",
        image_src="http://127.0.0.1:8123/odylith/atlas/source/evidence-flow.svg",
        image_loaded=True,
    )

    assert issues == ()


def test_atlas_state_assertion_rejects_heading_only_or_unloaded_state() -> None:
    module = _module()

    issues = module._atlas_state_assertion_issues(
        diagram_count=0,
        stat_total_text="0",
        active_diagram="",
        displayed_diagram="",
        displayed_title="Atlas",
        image_src="http://127.0.0.1:8123/odylith/atlas/atlas.html",
        image_loaded=False,
    )

    assert "browser surface atlas rendered no generated diagram buttons" in issues
    assert "browser surface atlas viewer did not load a generated diagram asset" in issues
    assert "browser surface atlas generated diagram asset did not finish loading" in issues


def test_project_state_assertion_requires_persisted_prompt_state() -> None:
    module = _module()
    story_rows = _graph_story_rows()
    prompt_rows = _graph_prompt_rows()

    assert (
        module._project_state_assertion_issues(
            payload_origin="accepted greenfield project",
            payload_prompt_count=5,
            empty_payload_prompts=0,
            rendered_prompt_count=5,
            has_prompt_grid=True,
            has_blank_state=False,
            max_prompt_overflow=0,
            pane_overflow=0,
            clipped_text_count=0,
            rendered_story_rows=story_rows,
            payload_story_rows=story_rows,
            rendered_prompt_rows=prompt_rows,
            payload_prompt_rows=prompt_rows,
        )
        == ()
    )

    issues = module._project_state_assertion_issues(
        payload_origin="greenfield proposal",
        payload_prompt_count=3,
        empty_payload_prompts=1,
        rendered_prompt_count=2,
        has_prompt_grid=False,
        has_blank_state=True,
        max_prompt_overflow=20,
        pane_overflow=16,
        clipped_text_count=3,
        rendered_story_rows=story_rows[:1],
        payload_story_rows=story_rows,
        rendered_prompt_rows=prompt_rows[:1],
        payload_prompt_rows=prompt_rows,
    )

    assert "browser surface project payload is not accepted greenfield project state" in issues
    assert "browser surface project payload contains empty implementation prompt text" in issues
    assert "browser surface project handoff prompts drift from the accepted typed dashboard" in issues
    assert "browser surface project rendered the blank project state after commit-only create" in issues
    assert "browser surface project story cards drift from the accepted typed dashboard" in issues
    assert "browser surface project clips visible text" in issues


def test_project_state_assertion_rejects_wrong_semantic_story_slot() -> None:
    module = _module()

    issues = module._project_state_assertion_issues(
        payload_origin="accepted greenfield project",
        payload_prompt_count=5,
        empty_payload_prompts=0,
        rendered_prompt_count=5,
        has_prompt_grid=True,
        has_blank_state=False,
        max_prompt_overflow=0,
        pane_overflow=0,
        rendered_story_rows=[
            {
                "label": "Product Boundary",
                "semantic_slot": "first_path",
                "body": "A clerk submits one request and the workspace returns one reviewed result.",
            }
        ],
        payload_story_rows=_graph_story_rows(),
        rendered_prompt_rows=_graph_prompt_rows(),
        payload_prompt_rows=_graph_prompt_rows(),
    )

    assert "browser surface project story cards drift from the accepted typed dashboard" in issues


def test_project_state_assertion_accepts_css_transformed_story_labels() -> None:
    module = _module()

    issues = module._project_state_assertion_issues(
        payload_origin="accepted greenfield project",
        payload_prompt_count=5,
        empty_payload_prompts=0,
        rendered_prompt_count=5,
        has_prompt_grid=True,
        has_blank_state=False,
        max_prompt_overflow=0,
        pane_overflow=0,
        clipped_text_count=0,
        rendered_story_rows=[
            {**row, "label": row["label"].upper()} for row in _graph_story_rows()
        ],
        payload_story_rows=_graph_story_rows(),
        rendered_prompt_rows=_graph_prompt_rows(),
        payload_prompt_rows=_graph_prompt_rows(),
    )

    assert issues == ()


def test_project_state_assertion_rejects_confusable_uppercase_story_label() -> None:
    module = _module()

    issues = module._project_state_assertion_issues(
        payload_origin="accepted greenfield project",
        payload_prompt_count=5,
        empty_payload_prompts=0,
        rendered_prompt_count=5,
        has_prompt_grid=True,
        has_blank_state=False,
        max_prompt_overflow=0,
        pane_overflow=0,
        rendered_story_rows=[
            {**_graph_story_rows()[0], "label": "WORKFLOW FACT"},
            *_graph_story_rows()[1:],
        ],
        payload_story_rows=_graph_story_rows(),
        rendered_prompt_rows=_graph_prompt_rows(),
        payload_prompt_rows=_graph_prompt_rows(),
    )

    assert "browser surface project story cards drift from the accepted typed dashboard" in issues


def _graph_story_rows() -> list[dict[str, str]]:
    return [
        {
            "label": "Workflow Facts",
            "semantic_slot": "workflow_facts",
            "body": "Submit request; review request",
        },
        {
            "label": "Visible Outputs",
            "semantic_slot": "visible_outputs",
            "body": "Decision notice",
        },
        {
            "label": "Component Boundaries",
            "semantic_slot": "component_boundaries",
            "body": "Review Service",
        },
    ]


def _graph_prompt_rows() -> list[dict[str, str]]:
    return [
        {
            "step_id": "review_project",
            "label": "Review accepted project",
            "when": "Use this step only after the preceding graph-bound gate passes.",
            "prompt": "Review the accepted graph and release scope.",
            "result": "Evidence for the next graph-bound decision.",
            "stop": "Stop on contradiction, missing evidence, or scope drift.",
        },
        {
            "step_id": "create_plan",
            "label": "Create first implementation plan",
            "when": "Use this step only after the preceding graph-bound gate passes.",
            "prompt": "Create the first implementation plan from the accepted graph.",
            "result": "Evidence for the next graph-bound decision.",
            "stop": "Stop on contradiction, missing evidence, or scope drift.",
        },
    ]
