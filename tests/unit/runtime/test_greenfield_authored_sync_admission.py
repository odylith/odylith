"""Selected authored-edit admission through the real publication boundary.

The sync operation callbacks are deliberately synthetic: these controls prove
admission, exact selected intent, and publication, not CLI/renderer completeness.
"""

from pathlib import Path
import json
import stat

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
from odylith.runtime.domain_intelligence import greenfield_repository_lock as locks
from tests.unit.runtime.test_greenfield_baseline_activation import _activate, _complete


AUTHORED = "odylith/casebook/bugs/example.md"
OTHER_AUTHORED = "odylith/casebook/bugs/another.md"
INDEX = "odylith/casebook/bugs/INDEX.md"
PROJECTION = "odylith/casebook/casebook.html"
BEFORE = (
    "- Bug ID: CB-001\n"
    "- Created: 2026-09-10\n"
    "- Status: Open\n"
    "- Severity: P1\n"
    "- Reproducibility: High\n"
    "- Type: Product\n"
    "- Description: The original source-backed failure.\n"
    "- Impact: A failed refresh keeps the earlier view visible.\n"
)
EDITED = BEFORE.replace(
    "The original source-backed failure.",
    "The reproduced failure rejects a selected narrative before refresh.",
)


@pytest.fixture
def active_repo(tmp_path):
    _complete(tmp_path)
    for token, content in (
        (AUTHORED, BEFORE),
        (OTHER_AUTHORED, BEFORE.replace("CB-001", "CB-002")),
        (INDEX, "# Casebook\n\nCB-001 | Open\nCB-002 | Open\n"),
    ):
        target = tmp_path / token
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        target.chmod(0o644)
    _activate(tmp_path)
    generations.require_greenfield_working_generation(tmp_path)
    return tmp_path


def _tokens(*paths, options=()):
    return ("sync", "--impact-mode", "selective", *options, *paths)


def _run(root, tokens, operation):
    return boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=root, command_tokens=tokens, operation=operation,
    )


def _working_image(root):
    """Observe only this tiny fixture, without following a negative symlink."""
    result = {}
    for path in sorted((root / "odylith").rglob("*")):
        token = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[token] = ("symlink", str(path.readlink()))
        elif path.is_file():
            result[token] = ("file", path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
        else:
            result[token] = ("directory",)
    return result


def _assert_refused_without_dispatch(root, tokens):
    expected = _working_image(root)
    old = publication.read_active_publication(root)
    called = []
    with pytest.raises((RuntimeError, ValueError)):
        _run(root, tokens, lambda _fd: called.append(True) or 0)
    assert called == []
    assert _working_image(root) == expected
    assert publication.read_active_publication(root) == old


def test_selected_description_edit_dispatches_under_lock_and_publishes_exact_intent(active_repo):
    root = active_repo
    previous = generations.pin_active_greenfield_generation(root)
    previous_entry = (root / "odylith/index.html").read_bytes()
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    selected_mode = stat.S_IMODE((root / AUTHORED).stat().st_mode)
    called = []

    def synthetic_sync(descriptor):
        assert isinstance(descriptor, int)
        with pytest.raises(locks.GreenfieldRepositoryBusyError):
            with locks.greenfield_repository_lock(root):
                pytest.fail("selected source admission did not retain the repository lease")
        assert (root / "odylith/index.html").read_bytes() == previous_entry
        assert generations.pin_active_greenfield_generation(root).write_set_hash == previous.write_set_hash
        assert (previous.repository_root / AUTHORED).read_text(encoding="utf-8") == BEFORE
        assert (root / AUTHORED).read_text(encoding="utf-8") == EDITED
        (root / PROJECTION).write_text("<!doctype html><title>Selected source rendered</title>\n")
        called.append(True)
        return 0

    assert _run(root, _tokens(AUTHORED), synthetic_sync) == 0
    assert called == [True]
    current = generations.require_greenfield_working_generation(root)
    assert current.write_set_hash != previous.write_set_hash
    assert (current.repository_root / AUTHORED).read_bytes() == EDITED.encode()
    assert stat.S_IMODE((current.repository_root / AUTHORED).stat().st_mode) == selected_mode
    assert (previous.repository_root / AUTHORED).read_bytes() == BEFORE.encode()
    assert (current.repository_root / PROJECTION).read_bytes() == (root / PROJECTION).read_bytes()

    entry_after = ((root / "odylith/index.html").read_bytes(), (root / "odylith/index.html").stat().st_mtime_ns)
    assert _run(root, _tokens(AUTHORED), lambda _fd: 0) == 0
    assert generations.require_greenfield_working_generation(root).write_set_hash == current.write_set_hash
    assert ((root / "odylith/index.html").read_bytes(), (root / "odylith/index.html").stat().st_mtime_ns) == entry_after


@pytest.mark.parametrize("extra_drift", (OTHER_AUTHORED, INDEX, PROJECTION))
def test_selected_edit_does_not_authorize_other_source_or_generated_drift(active_repo, extra_drift):
    (active_repo / AUTHORED).write_text(EDITED, encoding="utf-8")
    with (active_repo / extra_drift).open("a", encoding="utf-8") as handle:
        handle.write("\nUnselected change.\n")
    _assert_refused_without_dispatch(active_repo, _tokens(AUTHORED))


@pytest.mark.parametrize("selected", (INDEX, PROJECTION))
def test_explicit_generated_file_selection_is_not_authored_edit_authority(active_repo, selected):
    (active_repo / selected).write_text("Changed generated output.\n", encoding="utf-8")
    _assert_refused_without_dispatch(active_repo, _tokens(selected))


@pytest.mark.parametrize(
    "tokens",
    (
        _tokens("odylith/casebook/bugs"),
        _tokens(),
        _tokens(options=("--force",)),
        _tokens(AUTHORED, options=("--force",)),
        _tokens(AUTHORED, options=("--check-only",)),
        _tokens(AUTHORED, options=("--dry-run",)),
        ("sync", "--impact-mode", "full", AUTHORED),
    ),
    ids=("directory", "no-selection", "force-without-selection", "force-with-selection", "check-only", "dry-run", "full-mode"),
)
def test_non_authorizing_sync_forms_do_not_admit_dirty_source(active_repo, tokens):
    (active_repo / AUTHORED).write_text(EDITED, encoding="utf-8")
    _assert_refused_without_dispatch(active_repo, tokens)


@pytest.mark.parametrize(
    ("before", "after"),
    (("CB-001", "CB-099"), ("- Status: Open", "- Status: Closed"), ("2026-09-10", "2026-09-11")),
    ids=("identity", "status", "created-date"),
)
def test_narrative_selection_does_not_waive_record_metadata(active_repo, before, after):
    (active_repo / AUTHORED).write_text(EDITED.replace(before, after), encoding="utf-8")
    _assert_refused_without_dispatch(active_repo, _tokens(AUTHORED))


def test_selected_authored_file_mode_change_is_not_narrative_authority(active_repo):
    (active_repo / AUTHORED).write_text(EDITED, encoding="utf-8")
    (active_repo / AUTHORED).chmod(0o755)
    _assert_refused_without_dispatch(active_repo, _tokens(AUTHORED))


def test_selected_authored_symlink_is_refused_without_following_or_replacing_it(active_repo):
    outside = active_repo / "outside-authored.md"
    outside.write_text(EDITED, encoding="utf-8")
    selected = active_repo / AUTHORED
    selected.unlink()
    selected.symlink_to(outside)
    _assert_refused_without_dispatch(active_repo, _tokens(AUTHORED))
    assert outside.read_text(encoding="utf-8") == EDITED


@pytest.mark.parametrize("kind", ("new", "deleted"))
def test_selected_paths_must_be_existing_published_files(active_repo, kind):
    selected = AUTHORED
    if kind == "new":
        selected = "odylith/casebook/bugs/new.md"
        (active_repo / selected).write_text(EDITED.replace("CB-001", "CB-003"), encoding="utf-8")
    else:
        (active_repo / selected).unlink()
    _assert_refused_without_dispatch(active_repo, _tokens(selected))


def test_failed_admitted_sync_preserves_authored_intent_and_previous_publication(active_repo):
    root = active_repo
    previous = generations.pin_active_greenfield_generation(root)
    entry = (root / "odylith/index.html").read_bytes()
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    called = []

    def failed_synthetic_sync(_descriptor):
        called.append(True)
        (root / PROJECTION).write_text("Failed partial generated output.\n", encoding="utf-8")
        return 1

    assert _run(root, _tokens(AUTHORED), failed_synthetic_sync) == 1
    assert called == [True]
    assert (root / AUTHORED).read_bytes() == EDITED.encode()
    assert (root / "odylith/index.html").read_bytes() == entry
    assert generations.pin_active_greenfield_generation(root).write_set_hash == previous.write_set_hash
    assert (previous.repository_root / AUTHORED).read_bytes() == BEFORE.encode()


def test_sync_callback_cannot_change_the_exact_selected_intent_before_publication(active_repo):
    root = active_repo
    old = publication.read_active_publication(root)
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    called = []

    def changed_intent(_descriptor):
        called.append(True)
        (root / AUTHORED).write_text(EDITED + "\nAn unapproved additional narrative.\n", encoding="utf-8")
        return 0

    with pytest.raises((RuntimeError, ValueError)) as failure:
        _run(root, _tokens(AUTHORED), changed_intent)
    assert called == [True]
    assert publication.read_active_publication(root) == old
    assert "this admission did not publish a successor" in str(failure.value)
    assert "operation was not run" not in str(failure.value)
    assert (root / AUTHORED).read_text(encoding="utf-8") == EDITED + "\nAn unapproved additional narrative.\n"


@pytest.mark.parametrize("suffix", ("\n", "\n- Bug ID: CB-099\n", "\n- status: Closed\n"))
def test_normalization_and_ambiguous_metadata_are_refused_before_dispatch(active_repo, suffix):
    (active_repo / AUTHORED).write_text(EDITED + suffix, encoding="utf-8")
    _assert_refused_without_dispatch(active_repo, _tokens(AUTHORED))


@pytest.mark.parametrize("token", ("../example.md", "/tmp/example.md", "odylith/casebook/bugs/../example.md"))
def test_noncanonical_selectors_are_not_intent_authority(active_repo, token):
    (active_repo / AUTHORED).write_text(EDITED, encoding="utf-8")
    _assert_refused_without_dispatch(active_repo, _tokens(token))


def test_selected_description_through_actual_cli_sync_and_casebook_renderer(active_repo, monkeypatch):
    """Real CLI dispatch, sync plan, index, renderer and publication; no browser claim."""
    from odylith.runtime.reasoning import odylith_reasoning

    def forbid_provider(*_args, **_kwargs):
        pytest.fail("authored Casebook selective sync must not construct a model provider")

    monkeypatch.setattr(odylith_reasoning, "provider_from_config", forbid_provider)
    root = active_repo
    previous = generations.pin_active_greenfield_generation(root)
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    assert cli.main([
        "sync", "--repo-root", str(root), "--impact-mode", "selective",
        "--runtime-mode", "standalone", AUTHORED,
    ]) == 0
    current = generations.require_greenfield_working_generation(root)
    assert current.write_set_hash != previous.write_set_hash
    assert (current.repository_root / AUTHORED).read_bytes() == EDITED.encode()
    assert (previous.repository_root / AUTHORED).read_bytes() == BEFORE.encode()
    assert "CB-001" in (root / INDEX).read_text(encoding="utf-8")
    html = (root / PROJECTION).read_text(encoding="utf-8")
    payload = root / "odylith/casebook/casebook-payload.v1.js"
    assert "casebook-payload.v1.js" in html
    assert "The reproduced failure rejects a selected narrative before refresh." in payload.read_text(encoding="utf-8")
    assert (current.repository_root / payload.relative_to(root)).read_bytes() == payload.read_bytes()
    assert (current.repository_root / PROJECTION).read_bytes() == (root / PROJECTION).read_bytes()


def test_actual_cli_sync_failure_keeps_authored_input_and_old_publication(active_repo, monkeypatch):
    """Inject failure after the real renderer; ordinary failed-writer recovery is not asserted."""
    from odylith.runtime.governance import sync_command_execution as execution

    root = active_repo
    previous = generations.pin_active_greenfield_generation(root)
    entry = (root / "odylith/index.html").read_bytes()
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    run_command = execution.run_command
    called = []

    def fail_after_render(**kwargs):
        assert kwargs["args"][2] == "odylith.runtime.surfaces.render_casebook_dashboard"
        assert run_command(**kwargs) == 0
        called.append(True)
        return 1

    monkeypatch.setattr(execution, "run_command", fail_after_render)
    assert cli.main([
        "sync", "--repo-root", str(root), "--impact-mode", "selective",
        "--runtime-mode", "standalone", AUTHORED,
    ]) != 0
    assert called == [True]
    assert (root / AUTHORED).read_bytes() == EDITED.encode()
    assert (root / "odylith/index.html").read_bytes() == entry
    assert generations.pin_active_greenfield_generation(root).write_set_hash == previous.write_set_hash
    assert (previous.repository_root / AUTHORED).read_bytes() == BEFORE.encode()


PLAN = "odylith/technical-plans/in-progress/example.md"
PLAN_BEFORE = (
    "# Example\n\nStatus: In progress\nCreated: 2026-09-10\nUpdated: 2026-09-10\nBacklog: B-001\n\n"
    "## Goal\n\nPreserve the original intent.\n"
)
SPEC = "odylith/registry/source/components/example/CURRENT_SPEC.md"
SPEC_BEFORE = (
    "# Example\n\nLast updated: 2026-09-10\n\n## Responsibility\n\nPreserve the original intent.\n\n"
    "## Requirements Trace\n\nOwned preamble.\n\n<!-- registry-requirements:start -->\n"
    "- Generated requirement.\n<!-- registry-requirements:end -->\n\nManual trace note.\n"
)
DIAGRAM = "odylith/atlas/source/example.mmd"
DIAGRAM_BEFORE = "flowchart LR\n  A[Original intent] --> B[Visible proof]\n"


def _active_authored_source(root, token, source, *, mapping=True):
    _complete(root)
    files = {token: source}
    if token == SPEC and mapping:
        files["odylith/registry/source/component_registry.v1.json"] = json.dumps({
            "components": [{"component_id": "example", "spec_ref": SPEC}],
        }) + "\n"
    if token == DIAGRAM and mapping:
        files["odylith/atlas/source/catalog/diagrams.v1.json"] = json.dumps({
            "diagrams": [{"diagram_id": "D-001", "source_mmd": DIAGRAM}],
        }) + "\n"
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        path.chmod(0o644)
    _activate(root)
    return root


@pytest.mark.parametrize(("token", "before", "after"), (
    (PLAN, PLAN_BEFORE, PLAN_BEFORE.replace("original intent", "source-backed authored intent")),
    (SPEC, SPEC_BEFORE, SPEC_BEFORE.replace("original intent", "source-backed authored intent").replace(
        "Last updated: 2026-09-10", "Last updated: 2026-09-11")),
    (SPEC, SPEC_BEFORE, SPEC_BEFORE.replace("Manual trace note.", "New source-backed manual trace note.")),
    (DIAGRAM, DIAGRAM_BEFORE, DIAGRAM_BEFORE.replace("A[Original intent]", "Author[Selected intent]")),
))
def test_other_authored_owners_admit_exact_body_bytes_with_synthetic_operation(tmp_path, token, before, after):
    """Owner/boundary proof only; does not stand in for the real plan/spec/Atlas sync."""
    root = _active_authored_source(tmp_path, token, before)
    previous = generations.pin_active_greenfield_generation(root)
    (root / token).write_text(after, encoding="utf-8")
    assert _run(root, _tokens(token), lambda _fd: 0) == 0
    current = generations.require_greenfield_working_generation(root)
    assert (current.repository_root / token).read_bytes() == after.encode()
    assert (previous.repository_root / token).read_bytes() == before.encode()


@pytest.mark.parametrize(("token", "before", "after"), (
    (PLAN, PLAN_BEFORE, PLAN_BEFORE.replace("Status: In progress", "Status: Done")),
    (PLAN, PLAN_BEFORE, PLAN_BEFORE + "\n## Risks\n\n- Missing causal proof.\n"),
    (SPEC, SPEC_BEFORE, SPEC_BEFORE.replace("Generated requirement", "Unapproved generated claim")),
    (SPEC, SPEC_BEFORE, SPEC_BEFORE.replace("Owned preamble", "Authored generated preamble")),
    (SPEC, SPEC_BEFORE, SPEC_BEFORE + "\n## Requirements Trace\n\nDuplicate region.\n"),
    (SPEC, SPEC_BEFORE, SPEC_BEFORE + "\n<!-- registry-requirements:end -->\n"),
))
def test_other_authored_owners_refuse_owned_regions_and_normalization(tmp_path, token, before, after):
    root = _active_authored_source(tmp_path, token, before)
    (root / token).write_text(after, encoding="utf-8")
    _assert_refused_without_dispatch(root, _tokens(token))


@pytest.mark.parametrize(("token", "before"), ((SPEC, SPEC_BEFORE), (DIAGRAM, DIAGRAM_BEFORE)))
def test_spec_and_diagram_require_existing_published_ownership(tmp_path, token, before):
    root = _active_authored_source(tmp_path, token, before, mapping=False)
    (root / token).write_text(before + "\nAuthored addition.\n", encoding="utf-8")
    _assert_refused_without_dispatch(root, _tokens(token))


def test_failed_sync_does_not_turn_generated_drift_into_retry_authority(active_repo):
    root = active_repo
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")

    def fail_after_render(_fd):
        (root / PROJECTION).write_text("Partial generated output.\n", encoding="utf-8")
        return 1

    assert _run(root, _tokens(AUTHORED), fail_after_render) == 1
    _assert_refused_without_dispatch(root, _tokens(AUTHORED))
    assert (root / AUTHORED).read_bytes() == EDITED.encode()


@pytest.mark.parametrize("writer", ("compass", "sync"))
def test_clean_writers_do_not_enter_authored_admission(active_repo, monkeypatch, writer):
    from odylith.runtime.domain_intelligence import greenfield_authored_sync_admission as admission

    monkeypatch.setattr(admission, "require_authored_sync_admission", lambda **_: pytest.fail("clean slow path"))
    tokens = _tokens(AUTHORED) if writer == "sync" else ("compass", "log")
    assert _run(active_repo, tokens, lambda _fd: 0) == 0


@pytest.mark.parametrize("moment", ("before-admission-capture", "after-admission-capture", "successor-capture"))
def test_compile_capture_detects_changes_around_admission_and_successor(active_repo, monkeypatch, moment):
    from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets

    root = active_repo
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    old = publication.read_active_publication(root)
    compile_write_set = write_sets.compile_greenfield_repository_write_set
    captures = []
    dispatched = []

    def capture(**kwargs):
        captures.append(True)
        if moment == "before-admission-capture" and len(captures) == 1:
            (root / PROJECTION).write_text("Concurrent generated drift.\n", encoding="utf-8")
        if moment == "successor-capture" and len(captures) == 2:
            (root / AUTHORED).write_text(EDITED + "Changed after intent check.\n", encoding="utf-8")
        result = compile_write_set(**kwargs)
        if moment == "after-admission-capture" and len(captures) == 1:
            (root / PROJECTION).write_text("Concurrent generated drift.\n", encoding="utf-8")
        return result

    monkeypatch.setattr(write_sets, "compile_greenfield_repository_write_set", capture)
    with pytest.raises((RuntimeError, ValueError)):
        _run(root, _tokens(AUTHORED), lambda _fd: dispatched.append(True) or 0)
    assert dispatched == ([True] if moment == "successor-capture" else [])
    assert publication.read_active_publication(root) == old


def test_changed_publication_anchor_cannot_publish_admitted_intent(active_repo, monkeypatch):
    root = active_repo
    old = publication.read_active_publication(root)
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    identity = publication.active_generation_identity
    dispatched = []

    def change_observed_anchor(_fd):
        dispatched.append(True)
        monkeypatch.setattr(publication, "active_generation_identity", lambda _root: {
            **identity(root), "write_set_hash": "a" * 64,
        })
        return 0

    with pytest.raises(RuntimeError, match="published base changed"):
        _run(root, _tokens(AUTHORED), change_observed_anchor)
    assert dispatched == [True]
    assert publication.read_active_publication(root) == old


def test_mutated_immutable_preimage_refuses_admission(active_repo):
    root = active_repo
    pinned = generations.pin_active_greenfield_generation(root)
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    (pinned.repository_root / AUTHORED).write_text("Corrupt published preimage.\n", encoding="utf-8")
    _assert_refused_without_dispatch(root, _tokens(AUTHORED))


def test_sync_target_must_match_the_admission_repository(active_repo):
    (active_repo / AUTHORED).write_text(EDITED, encoding="utf-8")
    _assert_refused_without_dispatch(active_repo, _tokens(AUTHORED, options=("--repo-root", str(active_repo.parent))))


def test_existing_field_parser_keeps_multiline_values_and_duplicate_occurrences(tmp_path):
    from odylith.runtime.governance import sync_casebook_bug_index as casebook

    text = "# Incident\n\n- Description: First line.\n  Continuation.\n\n- Status: Open\n- Status: Closed\n"
    path = tmp_path / "example.md"
    path.write_text(text, encoding="utf-8")
    blocks = casebook.parse_bug_field_blocks(text)
    assert blocks == (
        ("Description", "First line.\n  Continuation.", "- Description: First line.\n  Continuation.\n\n"),
        ("Status", "Open", "- Status: Open\n"),
        ("Status", "Closed", "- Status: Closed\n"),
    )
    assert casebook._parse_bug_fields(path) == {"Description": "First line.\n  Continuation.", "Status": "Closed"}


def test_actual_generation_transition_between_pin_and_identity_refuses_old_baseline(active_repo, monkeypatch):
    """Inject a non-cooperating carrier transition between two real sealed generations."""
    root = active_repo
    old = generations.pin_active_greenfield_generation(root)
    entry = root / "odylith/index.html"
    old_entry = entry.read_bytes()
    projection = root / PROJECTION
    old_projection = projection.read_bytes()
    newer_projection = b"<!doctype html><title>Newer published projection</title>\n"

    def publish_newer_projection(_fd):
        projection.write_bytes(newer_projection)
        return 0

    assert _run(root, ("casebook", "refresh"), publish_newer_projection) == 0
    newer = generations.pin_active_greenfield_generation(root)
    newer_entry = entry.read_bytes()
    assert newer.write_set_hash != old.write_set_hash
    # Private fixture setup retains both valid immutable generations, then
    # restores P0's working tree and carrier before the injected P1 transition.
    projection.write_bytes(old_projection)
    entry.write_bytes(old_entry)
    assert generations.require_greenfield_working_generation(root).write_set_hash == old.write_set_hash
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    pin = generations.pin_active_greenfield_generation
    pins = []

    def pin_then_transition(repo_root):
        pinned = pin(repo_root)
        pins.append(pinned.write_set_hash)
        if len(pins) == 2:  # The first pin belongs to ordinary clean admission.
            entry.write_bytes(newer_entry)
        return pinned

    monkeypatch.setattr(generations, "pin_active_greenfield_generation", pin_then_transition)
    called = []
    with pytest.raises(RuntimeError, match="pinned generation differs from the active publication"):
        _run(root, _tokens(AUTHORED), lambda _fd: called.append(True) or 0)
    assert called == []
    assert pins == [old.write_set_hash, old.write_set_hash]
    assert entry.read_bytes() == newer_entry
    assert pin(root).write_set_hash == newer.write_set_hash
    assert (newer.repository_root / PROJECTION).read_bytes() == newer_projection
    assert projection.read_bytes() == old_projection
    assert (root / AUTHORED).read_bytes() == EDITED.encode()


def test_manifest_identity_must_match_the_pinned_generation_before_dispatch(active_repo, monkeypatch):
    root = active_repo
    (root / AUTHORED).write_text(EDITED, encoding="utf-8")
    identity = publication.active_generation_identity
    monkeypatch.setattr(publication, "active_generation_identity", lambda repo_root: {
        **identity(repo_root), "generation_manifest_sha256": "a" * 64,
    })
    _assert_refused_without_dispatch(root, _tokens(AUTHORED))
