from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_intervention_and_host_surfaces_use_shared_normalization_and_join_helpers() -> None:
    visibility_paths = (
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "alignment_context.py",
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "alignment_evidence.py",
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "visibility_replay.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "host_intervention_status.py",
    )
    for path in visibility_paths:
        text = path.read_text(encoding="utf-8")
        assert "normalize_string as _normalize_string" in text, f"shared normalization alias missing in {path.relative_to(ROOT)}"
        assert "normalize_token as _normalize_token" in text, f"shared token alias missing in {path.relative_to(ROOT)}"
        assert "def _normalize_string(" not in text, f"duplicate normalize_string helper resurfaced in {path.relative_to(ROOT)}"
        assert "def _normalize_token(" not in text, f"duplicate normalize_token helper resurfaced in {path.relative_to(ROOT)}"
        if path.name == "alignment_context.py":
            assert "normalize_string_list as _normalize_string_list" in text
            assert "def _normalize_string_list(" not in text

    codex_checkpoint_paths = (
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "codex_host_post_bash_checkpoint.py",
    )
    for path in codex_checkpoint_paths:
        text = path.read_text(encoding="utf-8")
        assert "host_intervention_support.join_sections(" in text, f"shared join helper missing in {path.relative_to(ROOT)}"
        assert "def _parts(" not in text, f"duplicate section-join helper resurfaced in {path.relative_to(ROOT)}"

    silent_checkpoint_paths = (
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "claude_host_post_bash_checkpoint.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "claude_host_post_edit_checkpoint.py",
    )
    for path in silent_checkpoint_paths:
        text = path.read_text(encoding="utf-8")
        assert "def _parts(" not in text, f"duplicate section-join helper resurfaced in {path.relative_to(ROOT)}"
        assert "host_intervention_support.join_sections(" not in text, f"silent checkpoint should not assemble live sections in {path.relative_to(ROOT)}"

    prompt_stop_paths = (
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "claude_host_prompt_context.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "codex_host_prompt_context.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "claude_host_stop_summary.py",
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "codex_host_stop_summary.py",
    )
    for path in prompt_stop_paths:
        text = path.read_text(encoding="utf-8")
        if "prompt_context" in path.name:
            assert "host_intervention_support.render_prompt_bundle_text(" in text
        else:
            assert "host_intervention_support.build_stop_conversation_bundle(" in text
            assert "host_intervention_support.render_stop_bundle_text(" in text

    delivery_runtime_text = (
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "delivery_runtime.py"
    ).read_text(encoding="utf-8")
    assert "def _dedupe_strings(" not in delivery_runtime_text
    assert "visibility_contract.normalize_string_list(rows)" in delivery_runtime_text


def test_conversation_closeout_ownership_stays_decomposed() -> None:
    conversation_runtime_text = (
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "conversation_runtime.py"
    ).read_text(encoding="utf-8")
    conversation_closeout_text = (
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "conversation_closeout.py"
    ).read_text(encoding="utf-8")
    conversation_artifacts_text = (
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "conversation_artifacts.py"
    ).read_text(encoding="utf-8")
    host_support_text = (
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "host_intervention_support.py"
    ).read_text(encoding="utf-8")
    host_visible_text = (
        ROOT / "src" / "odylith" / "runtime" / "surfaces" / "host_visible_intervention.py"
    ).read_text(encoding="utf-8")

    assert len(conversation_runtime_text.splitlines()) < 800
    assert "def compose_closeout_assist(" not in conversation_runtime_text
    assert "def visibility_feedback_requested(" not in conversation_runtime_text
    assert "def _visibility_feedback_phrase(" not in conversation_runtime_text
    assert "_artifact_ref = conversation_artifacts." not in conversation_runtime_text
    assert "_field = conversation_common." not in conversation_runtime_text
    assert "def compose_closeout_assist(" in conversation_closeout_text
    assert "def visibility_feedback_requested(" in conversation_closeout_text
    assert "def resolve_updated_artifacts(" in conversation_artifacts_text
    assert "prompt_signal_runtime.visibility_feedback_requested(" in conversation_closeout_text
    assert "prompt_signal_runtime.visibility_feedback_requested(" in host_support_text
    assert "conversation_closeout.visibility_feedback_requested(" in host_visible_text
    assert "conversation_closeout.visibility_feedback_requested(" not in host_support_text
    assert "conversation_runtime.visibility_feedback_requested(" not in host_support_text
    assert "conversation_runtime.visibility_feedback_requested(" not in host_visible_text


def test_conversation_surface_signal_selection_ownership_stays_decomposed() -> None:
    conversation_surface_text = (
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "conversation_surface.py"
    ).read_text(encoding="utf-8")
    signal_selection_text = (
        ROOT
        / "src"
        / "odylith"
        / "runtime"
        / "intervention_engine"
        / "conversation_surface_signal_selection.py"
    ).read_text(encoding="utf-8")

    assert len(conversation_surface_text.splitlines()) < 800
    assert "conversation_surface_signal_selection as signal_selection" in conversation_surface_text
    assert "def _ambient_payload_candidates(" not in conversation_surface_text
    assert "def _ambient_candidate_id(" not in conversation_surface_text
    assert "def _value_selection_decision(" not in conversation_surface_text
    assert "def _value_option_from_observation(" not in conversation_surface_text
    assert "def _value_option_from_proposal(" not in conversation_surface_text
    assert "_ambient_payload_candidates = signal_selection." not in conversation_surface_text
    assert "_ambient_candidate_id = signal_selection." not in conversation_surface_text
    assert "def ambient_payload_candidates(" in signal_selection_text
    assert "def ambient_candidate_id(" in signal_selection_text
    assert "def value_selection_decision(" in signal_selection_text
    assert "def value_payload_fields(" in signal_selection_text


def test_intervention_engine_proposal_action_ownership_stays_decomposed() -> None:
    engine_text = (
        ROOT / "src" / "odylith" / "runtime" / "intervention_engine" / "engine.py"
    ).read_text(encoding="utf-8")
    proposal_action_text = (
        ROOT
        / "src"
        / "odylith"
        / "runtime"
        / "intervention_engine"
        / "proposal_action_selection.py"
    ).read_text(encoding="utf-8")

    assert len(engine_text.splitlines()) < 800
    assert "proposal_action_selection.proposal_actions(" in engine_text
    assert "proposal_action_selection.derive_title(" in engine_text
    assert "def _proposal_actions(" not in engine_text
    assert "def _radar_create_payload(" not in engine_text
    assert "def _matching_workstream_by_title(" not in engine_text
    assert "def _matching_component_by_title_or_id(" not in engine_text
    assert "def _matching_bug_by_title(" not in engine_text
    assert "_proposal_actions = proposal_action_selection." not in engine_text
    assert "from odylith.runtime.governance import bug_authoring" not in engine_text
    assert "def proposal_actions(" in proposal_action_text
    assert "def derive_title(" in proposal_action_text
    assert "def slugify(" in proposal_action_text
    assert "bug_authoring.missing_capture_requirements(" in proposal_action_text
