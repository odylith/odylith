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


def _authored_contract_module():
    return _load_module(
        SCRIPTS_ROOT / "greenfield_browser_authored_contract.py",
        "greenfield_browser_authored_contract",
    )


def test_browser_surface_proof_scope_is_generated_state_matrix() -> None:
    module = _module()

    assert module.BROWSER_SURFACE_PROOF_SCOPE == "per_case_headless_generated_surface_state_matrix"
    assert set(module.BROWSER_VIEWPORTS) == {"desktop", "mobile"}
    assert {
        surface for _viewport, surface, _state in module.BROWSER_REQUIRED_COVERAGE
    } == {"project", "radar", "registry", "casebook", "atlas", "compass", "shell"}
    assert ("mobile", "casebook", "empty") in module.BROWSER_REQUIRED_COVERAGE
    assert ("mobile", "shell", "invalid-recovery") in module.BROWSER_REQUIRED_COVERAGE


def test_browser_surface_proof_fails_closed_when_a_required_cell_is_skipped() -> None:
    module = _module()
    skipped = ("mobile", "registry", "normal")

    issues = module._missing_coverage_issues(set(module.BROWSER_REQUIRED_COVERAGE) - {skipped})

    assert issues == ("browser surface proof skipped required coverage cell: mobile/registry/normal",)


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


def test_browser_state_screenshot_is_captured_with_and_without_assertion_issues(tmp_path: Path) -> None:
    module = _module()

    clean_page = _FakePage()
    covered = set()
    _, clean_issues = module._new_page(
        _FakeContext(clean_page),
        issue_prefix="clean state",
        screenshot_output_dir=tmp_path / "clean",
        coverage_cells=(("desktop", "project", "normal"), ("desktop", "shell", "normal")),
        covered=covered,
    )
    assert clean_issues() == ()
    assert (tmp_path / "clean/desktop-project-normal.png").read_bytes() == b"png"
    assert (tmp_path / "clean/desktop-shell-normal.png").read_bytes() == b"png"
    assert covered == {("desktop", "project", "normal"), ("desktop", "shell", "normal")}

    failed_page = _FakePage()
    _, failed_issues = module._new_page(
        _FakeContext(failed_page),
        issue_prefix="failed state",
        screenshot_output_dir=tmp_path / "failed",
        screenshot_name="invalid-route",
    )
    failed_page.handlers["pageerror"]("assertion failed")
    assert "failed state page error: assertion failed" in failed_issues()
    assert (tmp_path / "failed/invalid-route.png").read_bytes() == b"png"
    assert not module._is_expected_local_abort(
        url="http://127.0.0.1:12345/odylith/radar/radar.html",
        error_text="net::ERR_FAILED",
        resource_type="document",
    )

    duplicate_cell = ("mobile", "atlas", "normal")
    duplicate_dir = tmp_path / "duplicate"
    duplicate_dir.mkdir()
    (duplicate_dir / "mobile-atlas-normal.png").write_bytes(b"existing")
    duplicate_covered = set()
    _, duplicate_issues = module._new_page(
        _FakeContext(_FakePage()),
        issue_prefix="duplicate state",
        screenshot_output_dir=duplicate_dir,
        coverage_cells=(duplicate_cell,),
        covered=duplicate_covered,
    )
    assert "duplicate state screenshot capture failed: RuntimeError: browser screenshot already exists: mobile-atlas-normal" in duplicate_issues()
    assert duplicate_cell not in duplicate_covered


def test_browser_layout_assertions_reject_overflow_clipping_and_missing_copy() -> None:
    module = _module()

    assert module._layout_assertion_issues(
        label="registry", horizontal_overflow=4, clipped_text_count=0, visible_copy_length=12
    ) == ()
    issues = module._layout_assertion_issues(
        label="registry", horizontal_overflow=20, clipped_text_count=2, visible_copy_length=0
    )

    assert "browser surface registry overflows the viewport horizontally" in issues
    assert "browser surface registry clips visible status or content copy" in issues
    assert "browser surface registry does not expose meaningful visible copy" in issues


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

    assert (
        module._project_state_assertion_issues(
            payload_origin=module.AUTHORED_PROJECTION_ORIGIN,
            payload_prompt_count=5,
            empty_payload_prompts=0,
            rendered_prompt_count=5,
            has_prompt_grid=True,
            has_blank_state=False,
            has_implementation_prompts=True,
            max_prompt_overflow=0,
            pane_overflow=0,
            rendered_story_body_count=5,
            distinct_story_body_count=5,
            clipped_text_count=0,
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
        has_implementation_prompts=False,
        max_prompt_overflow=20,
        pane_overflow=16,
        rendered_story_body_count=5,
        distinct_story_body_count=2,
        clipped_text_count=3,
    )

    assert "browser surface project payload is not accepted greenfield project state" in issues
    assert "browser surface project payload exposes fewer than five implementation prompts" in issues
    assert "browser surface project payload contains empty implementation prompt text" in issues
    assert "browser surface project rendered fewer than five implementation prompt cards" in issues
    assert "browser surface project rendered the blank project state after commit-only create" in issues
    assert "browser surface project clips visible text" in issues


class _FakeContext:
    def __init__(self, page: "_FakePage") -> None:
        self.page = page

    def new_page(self):  # noqa: ANN201
        return self.page


class _FakePage:
    def __init__(self) -> None:
        self.handlers = {}

    def on(self, event: str, callback) -> None:  # noqa: ANN001
        self.handlers[event] = callback

    def screenshot(self, *, path: str, full_page: bool) -> None:
        assert full_page is True
        Path(path).write_bytes(b"png")


def test_project_state_assertion_rejects_wrong_semantic_story_slot() -> None:
    module = _module()

    issues = module._project_state_assertion_issues(
        payload_origin=module.AUTHORED_PROJECTION_ORIGIN,
        payload_prompt_count=5,
        empty_payload_prompts=0,
        rendered_prompt_count=5,
        has_prompt_grid=True,
        has_blank_state=False,
        has_implementation_prompts=True,
        max_prompt_overflow=0,
        pane_overflow=0,
        story_rows=[
            {
                "label": "Product Boundary",
                "semantic_slot": "first_path",
                "body": "A clerk submits one request and the workspace returns one reviewed result.",
            }
        ],
    )

    assert (
        "greenfield Project Product Story card is bound to the wrong semantic slot: "
        "`Product Boundary` uses `first_path` instead of `product_boundary`"
        in issues
    )


def test_project_state_assertion_accepts_css_transformed_story_labels() -> None:
    module = _module()

    issues = module._project_state_assertion_issues(
        payload_origin=module.AUTHORED_PROJECTION_ORIGIN,
        payload_prompt_count=5,
        empty_payload_prompts=0,
        rendered_prompt_count=5,
        has_prompt_grid=True,
        has_blank_state=False,
        has_implementation_prompts=True,
        max_prompt_overflow=0,
        pane_overflow=0,
        rendered_story_body_count=5,
        distinct_story_body_count=5,
        clipped_text_count=0,
        story_rows=[
            {"label": "USER PROBLEM", "semantic_slot": "user_problem", "body": "A reviewer needs a decision."},
            {"label": "FIRST PATH", "semantic_slot": "first_path", "body": "A reviewer submits one packet."},
            {
                "label": "PRODUCT BOUNDARY",
                "semantic_slot": "product_boundary",
                "body": "The product owns packet review but not the external archive.",
            },
            {
                "label": "OWNED CAPABILITIES",
                "semantic_slot": "owned_capabilities",
                "body": "The product validates, records, and displays the decision.",
            },
            {"label": "PROOF", "semantic_slot": "proof", "body": "A receipt proves the reviewed result."},
        ],
    )

    assert issues == ()


def test_project_state_assertion_compares_shared_source_facts_to_typed_payload() -> None:
    module = _module()
    rows = [
        {"label": "User Problem", "semantic_slot": "user_problem", "body": "One accepted fact."},
        {"label": "First Path", "semantic_slot": "first_path", "body": "One accepted path.\nThen another."},
        {"label": "Product Boundary", "semantic_slot": "product_boundary", "body": "One boundary."},
        {"label": "Owned Capabilities", "semantic_slot": "owned_capabilities", "body": "One capability."},
        {"label": "Proof", "semantic_slot": "proof", "body": "One accepted path. Then another."},
    ]
    rendered_rows = [dict(row) for row in rows]
    rendered_rows[1]["body"] = "One accepted path. Then another."

    issues = module._project_state_assertion_issues(
        payload_origin=module.AUTHORED_PROJECTION_ORIGIN,
        payload_prompt_count=5,
        empty_payload_prompts=0,
        rendered_prompt_count=5,
        has_prompt_grid=True,
        has_blank_state=False,
        has_implementation_prompts=True,
        max_prompt_overflow=0,
        pane_overflow=0,
        rendered_story_body_count=5,
        distinct_story_body_count=4,
        story_rows=rendered_rows,
        payload_story_rows=rows,
    )

    assert issues == ()
    drifted = [dict(row) for row in rendered_rows]
    drifted[-1]["body"] = "A different rendered claim."
    issues = module._project_state_assertion_issues(
        payload_origin=module.AUTHORED_PROJECTION_ORIGIN,
        payload_prompt_count=5,
        empty_payload_prompts=0,
        rendered_prompt_count=5,
        has_prompt_grid=True,
        has_blank_state=False,
        has_implementation_prompts=True,
        max_prompt_overflow=0,
        pane_overflow=0,
        rendered_story_body_count=5,
        distinct_story_body_count=5,
        story_rows=drifted,
        payload_story_rows=rows,
    )

    assert "browser surface project Product Story cards drifted from the sealed payload" in issues


def test_project_state_assertion_rejects_confusable_uppercase_story_label() -> None:
    module = _module()

    issues = module._project_state_assertion_issues(
        payload_origin=module.AUTHORED_PROJECTION_ORIGIN,
        payload_prompt_count=5,
        empty_payload_prompts=0,
        rendered_prompt_count=5,
        has_prompt_grid=True,
        has_blank_state=False,
        has_implementation_prompts=True,
        max_prompt_overflow=0,
        pane_overflow=0,
        story_rows=[
            {"label": "PROOFS", "semantic_slot": "proof", "body": "A receipt proves the reviewed result."}
        ],
    )

    assert "greenfield Project Product Story card has an unexpected semantic label: `PROOFS`" in issues
    assert "greenfield Project Product Story is missing its `Proof` card" in issues


def test_story_row_parity_defers_structured_card_bodies_to_typed_node_proof() -> None:
    module = _module()
    payload_rows = [
        {"label": "User Problem", "semantic_slot": "user_problem", "body": "A source fact."},
        {"label": "First Path", "semantic_slot": "first_path", "body": "Signal amber\nRecord receipt"},
        {"label": "Product Boundary", "semantic_slot": "product_boundary", "body": "Product-owned systems:\nFerry desk"},
        {"label": "Owned Capabilities", "semantic_slot": "owned_capabilities", "body": "Ferry desk: signal amber; record receipt"},
        {"label": "Proof", "semantic_slot": "proof", "body": "A reviewed receipt."},
    ]
    rendered_rows = [dict(row) for row in payload_rows]
    rendered_rows[1]["body"] = "1. Signal amber\n2. Record receipt"
    rendered_rows[3]["body"] = "Ferry desk: signal amber\nFerry desk: record receipt"

    assert module.story_rows_match_payload(
        rendered_rows,
        payload_rows,
        structured_slots=("first_path", "product_boundary", "owned_capabilities"),
    )
    rendered_rows[-1]["body"] = "A different proof claim."
    assert not module.story_rows_match_payload(
        rendered_rows,
        payload_rows,
        structured_slots=("first_path", "product_boundary", "owned_capabilities"),
    )


def test_authored_structure_requires_direct_typed_node_parity() -> None:
    module = _authored_contract_module()
    facts = {
        "first_path_relations": [
            {
                "order": 1,
                "event_quote": "Keeper signals amber ferry",
                "actor_kind": "human",
                "actor_fact_quote": "Keeper",
            },
            {
                "order": 2,
                "event_quote": "Relay writes blue receipt",
                "actor_kind": "product",
                "actor_fact_quote": "Relay",
            },
        ],
        "human_actors": ["Keeper"],
        "internal_systems": ["Relay", "Audit Console"],
        "component_responsibility_relations": [
            {
                "owner_system_quote": "Relay",
                "responsibility_quote": "Own blue-receipt custody.",
            }
        ],
        "external_systems": ["North Archive"],
        "non_goals": ["Do not claim live settlement."],
    }
    events = [
        {"order": 1, "text": "Keeper signals amber ferry"},
        {"order": 2, "text": "Relay writes blue receipt"},
    ]
    rendered = {
        "focus": events,
        "first_path": events,
        "actors": [{"actor": "Keeper", "events": events[:1]}],
        "capabilities": [
            {"owner": "Relay", "responsibility": "Own blue-receipt custody."}
        ],
        "boundary_groups": [
            {"key": "product_owned_systems", "items": ["Relay", "Audit Console"]},
            {"key": "external_systems", "items": ["North Archive"]},
            {"key": "non_goals", "items": ["Do not claim live settlement."]},
        ],
    }

    assert module.authored_structure_issues(rendered, facts) == ()

    collapsed = dict(rendered)
    collapsed["first_path"] = [
        {"order": 0, "text": "Keeper signals amber ferry Relay writes blue receipt"}
    ]
    assert module.authored_structure_issues(collapsed, facts) == (
        "browser surface project first path does not preserve typed event nodes",
    )


def test_project_state_assertion_fails_closed_when_authored_nodes_are_missing() -> None:
    module = _module()

    issues = module._project_state_assertion_issues(
        payload_origin=module.AUTHORED_PROJECTION_ORIGIN,
        payload_prompt_count=5,
        empty_payload_prompts=0,
        rendered_prompt_count=5,
        has_prompt_grid=True,
        has_blank_state=False,
        has_implementation_prompts=True,
        max_prompt_overflow=0,
        pane_overflow=0,
        authored_structure={},
        payload_authored_facts={"first_path_relations": []},
    )

    assert "browser surface project focus does not preserve typed event nodes" in issues
    assert "browser surface project first path does not preserve typed event nodes" in issues
