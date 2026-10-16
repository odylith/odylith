"""Working-only restoration authority, admission, and interrupted retry controls."""

from __future__ import annotations

import importlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import stat
import subprocess
import sys
import tempfile

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets


TARGETS = ("odylith/radar/one.json", "odylith/atlas/two.json")
AUTHORED = "odylith/radar/source/intent.md"


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _published_repo(base: Path) -> Path:
    repo, staged = base / "repo", base / "staged"
    for token, data in {
        "odylith/index.html": b"<!doctype html><title>Published shell</title>\n",
        TARGETS[0]: b"published one\n",
        TARGETS[1]: b"published two\n",
        AUTHORED: b"published intent\n",
    }.items():
        _write(repo / token, data)
    shutil.copytree(repo, staged)
    write_set = write_sets.compile_greenfield_repository_write_set(source_root=repo, staged_root=staged)
    generation = generations.materialize_immutable_greenfield_generation(
        repo_root=repo, write_set=write_set,
        manifest_text=generations.compile_greenfield_generation_manifest(write_set),
    )
    entry = publication.compile_greenfield_publication_entry(
        write_set_hash=generation.write_set_hash, generation_manifest_sha256=generation.manifest_sha256,
    )
    generations.publish_greenfield_generation(
        repo_root=repo, generation=generation, write_set=write_set, publication_entry_text=entry,
    )
    shutil.copy2(generation.repository_root / "odylith/index.html", repo / "odylith/tooling-shell.html")
    for token in TARGETS:
        _write(repo / token, b"unpublished generated drift\n")
    _write(repo / AUTHORED, b"new authored intent, preserve me\n")
    return repo


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _published_repo(tmp_path)


@pytest.fixture
def restore():
    return importlib.import_module("odylith.runtime.governance.restore_published_files")


def _snapshot(repo: Path) -> dict:
    return {
        "managed": write_sets.greenfield_managed_fingerprints(repo),
        "publication": publication.active_generation_identity(repo),
        "carrier": (repo / "odylith/index.html").read_bytes(),
    }


def test_preview_and_apply_restore_only_selected_files_and_repeat_writes_nothing(repo, restore, monkeypatch):
    before = _snapshot(repo)
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    assert _snapshot(repo) == before
    assert preview["status"] == "previewed"
    assert {row["path"] for row in preview["targets"]} == set(TARGETS)
    result = restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert result["status"] == "restored"
    pinned = generations.pin_active_greenfield_generation(repo)
    for token in TARGETS:
        assert (repo / token).read_bytes() == (pinned.repository_root / token).read_bytes()
    assert (repo / AUTHORED).read_bytes() == b"new authored intent, preserve me\n"
    assert publication.active_generation_identity(repo) == before["publication"]
    assert (repo / "odylith/index.html").read_bytes() == before["carrier"]
    monkeypatch.setattr(restore, "atomic_write_bytes", lambda *a, **k: pytest.fail("repeated apply wrote"))
    assert restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])["status"] == "already_restored"


@pytest.mark.parametrize("change", ["target", "target_mode", "non_target", "non_target_mode", "new_file", "new_directory", "publication"])
def test_changed_state_refuses_before_admission(repo, restore, change):
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    if change == "target":
        (repo / TARGETS[0]).write_bytes(b"new target edit")
    elif change == "target_mode":
        (repo / TARGETS[0]).chmod(0o700)
    elif change == "non_target":
        (repo / AUTHORED).write_bytes(b"later authored intent")
    elif change == "non_target_mode":
        (repo / AUTHORED).chmod(0o700)
    elif change == "new_file":
        _write(repo / "odylith/radar/new.md", b"new intent")
    elif change == "new_directory":
        (repo / "odylith/radar/empty").mkdir()
    else:
        (repo / "odylith/index.html").write_bytes(b"not a publication")
    selected_before = [(repo / path).read_bytes() for path in TARGETS]
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert [(repo / path).read_bytes() for path in TARGETS] == selected_before
    assert not (Path(preview["receipt_path"]) / "admitted.json").exists()


@pytest.mark.parametrize("paths", [[], [TARGETS[0], TARGETS[0]], ["../escape"], ["/tmp/escape"], ["odylith/radar/../index.html"], ["odylith//radar/one.json"], ["odylith/radar"], [AUTHORED + "/missing"], ["unmanaged.txt"], ["odylith/tooling-shell.html"]])
def test_preview_rejects_noncanonical_or_nonregular_targets(repo, restore, paths):
    before = _snapshot(repo)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.preview_restore(repo_root=repo, paths=paths)
    assert _snapshot(repo) == before


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink", "parent_symlink"])
def test_unsafe_selected_paths_refuse(repo, restore, tmp_path, unsafe):
    selected = repo / TARGETS[0]
    if unsafe == "parent_symlink":
        selected.parent.rename(tmp_path / "redirected-radar")
        selected.parent.symlink_to(tmp_path / "redirected-radar", target_is_directory=True)
    else:
        other = tmp_path / "aliased"
        selected.rename(other)
        if unsafe == "symlink":
            selected.symlink_to(other)
        else:
            os.link(other, selected)
    before = selected.read_bytes()
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.preview_restore(repo_root=repo, paths=TARGETS)
    assert selected.read_bytes() == before


@pytest.mark.parametrize("tamper", ["plan", "preimage", "generation", "admission", "extra_target"])
def test_corrupt_seals_refuse_without_target_write(repo, restore, tamper):
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    receipt = Path(preview["receipt_path"])
    if tamper == "generation":
        pinned = generations.pin_active_greenfield_generation(repo)
        (pinned.repository_root / TARGETS[0]).write_bytes(b"corrupt published bytes")
    elif tamper == "admission":
        (receipt / "admitted.json").write_text('{}\n')
    else:
        path = receipt / "plan.json"
        plan = json.loads(path.read_text())
        if tamper == "plan":
            plan["purpose"] = "old failure recovery provenance"
        elif tamper == "extra_target":
            plan["targets"].append(dict(plan["targets"][0], path=AUTHORED))
        else:
            plan["targets"][0]["current"]["content_base64"] = "bm90IHRoZSBwcmVpbWFnZQ=="
        path.write_text(json.dumps(plan))
    selected_before = [(repo / path).read_bytes() for path in TARGETS]
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert [(repo / path).read_bytes() for path in TARGETS] == selected_before


def test_pending_create_journal_refuses(repo, restore):
    _write(repo / ".odylith/runtime/greenfield/create-journal/pending/state.v1.json", b'{}')
    before = _snapshot(repo)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.preview_restore(repo_root=repo, paths=TARGETS)
    assert _snapshot(repo) == before


def test_logical_shell_restoration_does_not_replace_publication_carrier(repo, restore):
    carrier = (repo / "odylith/index.html").read_bytes()
    _write(repo / "odylith/tooling-shell.html", b"unpublished shell")
    preview = restore.preview_restore(repo_root=repo, paths=["odylith/index.html"])
    assert preview["targets"][0]["working_path"] == "odylith/tooling-shell.html"
    restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert (repo / "odylith/index.html").read_bytes() == carrier
    assert (repo / "odylith/tooling-shell.html").read_bytes() == b"<!doctype html><title>Published shell</title>\n"


def test_repository_identity_is_not_portable_with_copied_receipts(repo, restore, tmp_path):
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    copied = tmp_path / "copied"
    shutil.copytree(repo, copied)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.apply_restore(repo_root=copied, review_hash=preview["review_hash"])
    assert (copied / TARGETS[0]).read_bytes() == b"unpublished generated drift\n"


def test_public_cli_exposes_separate_preview_and_apply_help(capsys):
    from odylith import cli

    with pytest.raises(SystemExit) as stopped:
        cli.main(["governance", "restore-published-files", "--help"])
    assert stopped.value.code == 0
    help_text = capsys.readouterr().out
    assert "--preview" in help_text and "--apply" in help_text and "--path" in help_text


@pytest.mark.parametrize("arguments", [
    ["--preview"], ["--apply", "not-a-hash", "--path", TARGETS[0]],
    ["--preview", "--path", TARGETS[0], "--repo-root", "elsewhere"],
    ["--preview", "--path", TARGETS[0], "--apply", "a" * 64],
])
def test_cli_rejects_bad_grammar_before_lock_or_mutation(repo, restore, monkeypatch, arguments):
    from odylith import cli

    monkeypatch.setattr(restore, "greenfield_repository_lock", lambda *a, **k: pytest.fail("invalid CLI acquired lock"))
    with pytest.raises(SystemExit) as stopped:
        cli.main(["governance", "restore-published-files", "--repo-root", str(repo), *arguments])
    assert stopped.value.code == 2


def test_public_cli_owns_recovery_lock_and_preserves_ordinary_admission(repo, restore, monkeypatch, capsys):
    from odylith import cli

    monkeypatch.setattr(cli.greenfield_managed_mutation_boundary, "run_with_greenfield_managed_mutation_boundary",
                        lambda **kwargs: pytest.fail("restore entered ordinary clean-working admission"))
    assert cli.main(["governance", "restore-published-files", "--repo-root", str(repo), "--preview",
                     "--path", TARGETS[0], "--json"]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert shlex.split(preview["apply_command"]) == [
        "odylith", "governance", "restore-published-files", "--repo-root", str(repo),
        "--apply", preview["review_hash"],
    ]
    assert cli.main(["governance", "restore-published-files", "--repo-root", str(repo), "--apply",
                     preview["review_hash"], "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "restored"


def test_busy_lock_refuses_before_receipt_or_target_write(repo, restore):
    from odylith.runtime.domain_intelligence.greenfield_repository_lock import (
        GreenfieldRepositoryBusyError, greenfield_repository_lock,
    )

    before = _snapshot(repo)
    with greenfield_repository_lock(repo), pytest.raises(GreenfieldRepositoryBusyError):
        restore.preview_restore(repo_root=repo, paths=TARGETS)
    assert _snapshot(repo) == before
    assert not (repo / restore._RECEIPTS).exists()


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink", "directory"])
def test_unsafe_lock_refuses_before_open(repo, restore, tmp_path, unsafe):
    path = repo / ".odylith/runtime/greenfield/create.lock"
    other = tmp_path / "other-lock"
    other.write_bytes(b"external lock")
    if unsafe == "symlink":
        path.symlink_to(other)
    elif unsafe == "hardlink":
        os.link(other, path)
    else:
        path.mkdir()
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.preview_restore(repo_root=repo, paths=TARGETS)
    assert other.read_bytes() == b"external lock"


def _interrupt_after_admission(repo, restore, monkeypatch):
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    write = restore.atomic_write_bytes

    def stop(path, *args, **kwargs):
        result = write(path, *args, **kwargs)
        if path.name == "admitted.json":
            raise InterruptedError("synthetic stop after durable admission")
        return result

    with monkeypatch.context() as local:
        local.setattr(restore, "atomic_write_bytes", stop)
        with pytest.raises(InterruptedError):
            restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    return preview


@pytest.mark.parametrize("change", ["third_target_state", "non_target", "empty_directory", "receipt", "admission", "publication", "generation", "hardlink", "symlink", "pending_create"])
def test_admitted_resume_refuses_every_unsealed_change(repo, restore, monkeypatch, tmp_path, change):
    preview = _interrupt_after_admission(repo, restore, monkeypatch)
    receipt = Path(preview["receipt_path"])
    if change == "third_target_state":
        (repo / TARGETS[0]).write_bytes(b"unreviewed third target state")
    elif change == "non_target":
        (repo / AUTHORED).write_bytes(b"later authored state")
    elif change == "empty_directory":
        (repo / "odylith/atlas/new-empty").mkdir()
    elif change == "receipt":
        (receipt / "plan.json").write_bytes(b"corrupt preimages")
    elif change == "admission":
        (receipt / "admitted.json").write_bytes(b"corrupt admission")
    elif change == "publication":
        (repo / "odylith/index.html").write_bytes(b"changed publication")
    elif change == "generation":
        pinned = generations.pin_active_greenfield_generation(repo)
        (pinned.repository_root / TARGETS[0]).write_bytes(b"changed generation")
    elif change == "pending_create":
        _write(repo / ".odylith/runtime/greenfield/create-journal/pending/state.v1.json", b'{}')
    else:
        path = repo / TARGETS[0]
        other = tmp_path / "external-alias"
        path.rename(other)
        os.link(other, path) if change == "hardlink" else path.symlink_to(other)
    selected_before = [(repo / path).read_bytes() for path in TARGETS]
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert [(repo / path).read_bytes() for path in TARGETS] == selected_before
    assert not (receipt / "closed.json").exists()


def test_pending_other_restoration_blocks_preview_and_apply(repo, restore, monkeypatch):
    other = restore.preview_restore(repo_root=repo, paths=[AUTHORED])
    own = _interrupt_after_admission(repo, restore, monkeypatch)
    with pytest.raises(ValueError, match="Another working-file restoration"):
        restore.preview_restore(repo_root=repo, paths=[AUTHORED])
    with pytest.raises(ValueError, match="Another working-file restoration"):
        restore.apply_restore(repo_root=repo, review_hash=other["review_hash"])
    assert restore.apply_restore(repo_root=repo, review_hash=own["review_hash"])["status"] == "restored"


def test_target_already_post_without_admission_is_not_adopted(repo, restore):
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    pinned = generations.pin_active_greenfield_generation(repo)
    shutil.copy2(pinned.repository_root / TARGETS[0], repo / TARGETS[0])
    with pytest.raises(ValueError, match="target changed"):
        restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert not (Path(preview["receipt_path"]) / "admitted.json").exists()


def test_target_mode_restored_and_target_preimage_preserved(repo, restore):
    (repo / TARGETS[0]).chmod(0o711)
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    path = Path(preview["receipt_path"]) / "plan.json"
    sealed_preimages = path.read_bytes()
    restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    pinned = generations.pin_active_greenfield_generation(repo)
    assert stat.S_IMODE((repo / TARGETS[0]).stat().st_mode) == stat.S_IMODE((pinned.repository_root / TARGETS[0]).stat().st_mode)
    assert path.read_bytes() == sealed_preimages


def test_normalized_kernel_fingerprint_keeps_existing_tree_contract(repo):
    for path in ("odylith/radar/a-b/file", "odylith/radar/a/file", "odylith/radar/a.thing"):
        _write(repo / path, b"ordering control")
    (repo / "odylith/atlas/empty").mkdir()
    baseline = write_sets.greenfield_managed_fingerprints(repo)
    assert write_sets.greenfield_managed_fingerprints_with_file_states(repo, file_states={}) == baseline
    target = repo / TARGETS[0]
    original = {"sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "mode": stat.S_IMODE(target.stat().st_mode)}
    target.write_bytes(b"partial apply")
    assert write_sets.greenfield_managed_fingerprints_with_file_states(repo, file_states={TARGETS[0]: original}) == baseline


def test_explicit_authored_target_is_new_intent_without_renderer_or_publication(repo, restore, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("working-only restore called generation or publication mutation")

    monkeypatch.setattr(generations, "publish_greenfield_generation", forbidden)
    monkeypatch.setattr(generations, "materialize_immutable_greenfield_generation", forbidden)
    monkeypatch.setattr(write_sets, "apply_compiled_greenfield_repository_write_set", forbidden)
    before = _snapshot(repo)
    preview = restore.preview_restore(repo_root=repo, paths=[AUTHORED])
    restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert (repo / AUTHORED).read_bytes() == b"published intent\n"
    assert all((repo / token).read_bytes() == b"unpublished generated drift\n" for token in TARGETS)
    assert publication.active_generation_identity(repo) == before["publication"]


@pytest.mark.parametrize("change", ["target_preimage", "closed_receipt", "admission_missing"])
def test_completed_receipt_cannot_reauthorize_new_changes(repo, restore, change):
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    receipt = Path(preview["receipt_path"])
    if change == "target_preimage":
        (repo / TARGETS[0]).write_bytes(b"unpublished generated drift\n")
    elif change == "closed_receipt":
        (receipt / "closed.json").write_bytes(b'{}')
    else:
        (receipt / "admitted.json").unlink()
    selected = [(repo / token).read_bytes() for token in TARGETS]
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert [(repo / token).read_bytes() for token in TARGETS] == selected


@pytest.mark.parametrize("location", ["plan", "admission", "generation_file", "generation_manifest"])
def test_receipt_and_generation_hardlinks_refuse(repo, restore, tmp_path, location):
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    pinned = generations.pin_active_greenfield_generation(repo)
    receipt = Path(preview["receipt_path"])
    if location == "admission":
        path = receipt / "admitted.json"
        path.write_bytes(restore._canonical(restore._marker(preview["review_hash"], "admitted")))
    else:
        path = {"plan": receipt / "plan.json", "generation_file": pinned.repository_root / TARGETS[0],
                "generation_manifest": pinned.generation_root / "generation-manifest.v1.json"}[location]
    os.link(path, tmp_path / "hardlink-alias")
    before = [(repo / token).read_bytes() for token in TARGETS]
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert [(repo / token).read_bytes() for token in TARGETS] == before


@pytest.mark.parametrize("kill_after", [0, 1, 2])
@pytest.mark.parametrize("aliased_parent", [False, True], ids=["direct-parent", "symlink-parent"])
def test_sigkill_resume_uses_durable_admission_and_exact_pre_post_states(restore, monkeypatch, kill_after, aliased_parent):
    # Deliberately outside pytest's tmp_path lifecycle, retaining even failed/nonterminal proof roots.
    parent = os.environ.get("ODYLITH_RESTORE_PROOF_ROOT")
    base = Path(tempfile.mkdtemp(prefix=f"restore-sigkill-{kill_after}-", dir=parent))
    if aliased_parent:
        physical = base / "physical"
        physical.mkdir()
        alias = base / "alias"
        alias.symlink_to(physical.resolve(), target_is_directory=True)
        base = Path(tempfile.mkdtemp(prefix="fixture-", dir=alias))
        assert base != base.resolve()
    # Match the writer's canonical root before comparing paths in either process.
    base = base.resolve()
    repo = _published_repo(base)
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    receipt = Path(preview["receipt_path"])
    before = _snapshot(repo)
    preimages = (receipt / "plan.json").read_bytes()
    child = """
import os, signal, sys
from pathlib import Path
from odylith.runtime.governance import restore_published_files as restore
root, review_hash, kill_after = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
write = restore.atomic_write_bytes
completed = 0
def killing_write(path, *args, **kwargs):
    global completed
    result = write(path, *args, **kwargs)
    if path.name == 'admitted.json' and kill_after == 0:
        os.kill(os.getpid(), signal.SIGKILL)
    if path in (root / 'odylith/radar/one.json', root / 'odylith/atlas/two.json'):
        completed += 1
        if completed == kill_after:
            os.kill(os.getpid(), signal.SIGKILL)
    return result
restore.atomic_write_bytes = killing_write
restore.apply_restore(repo_root=root, review_hash=review_hash)
"""
    process = subprocess.run([sys.executable, "-c", child, str(repo), preview["review_hash"], str(kill_after)],
                             cwd=Path(__file__).resolve().parents[3], capture_output=True, text=True, timeout=30)
    assert process.returncode == -9, process.stdout + process.stderr
    assert (receipt / "admitted.json").is_file()
    assert not (receipt / "closed.json").exists()
    pinned = generations.pin_active_greenfield_generation(repo)
    assert sum((repo / token).read_bytes() == (pinned.repository_root / token).read_bytes() for token in TARGETS) == kill_after
    assert publication.active_generation_identity(repo) == before["publication"]
    assert (repo / "odylith/index.html").read_bytes() == before["carrier"]
    assert (repo / AUTHORED).read_bytes() == b"new authored intent, preserve me\n"
    actual_write, writes = restore.atomic_write_bytes, []

    def count_write(path, *args, **kwargs):
        writes.append(path)
        return actual_write(path, *args, **kwargs)

    with monkeypatch.context() as local:
        local.setattr(restore, "atomic_write_bytes", count_write)
        result = restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    assert result["status"] == "restored"
    assert sum(path in (repo / token for token in TARGETS) for path in writes) == 2 - kill_after
    assert (receipt / "plan.json").read_bytes() == preimages
    assert (receipt / "closed.json").is_file()
    assert (repo / AUTHORED).read_bytes() == b"new authored intent, preserve me\n"
    assert publication.active_generation_identity(repo) == before["publication"]
    print(f"Retained SIGKILL proof root: {base}")


@pytest.mark.parametrize("raw", [b"[]\n", b"{}\n", b"not json"])
def test_malformed_receipt_is_a_structured_cli_refusal(repo, restore, capsys, raw):
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    (Path(preview["receipt_path"]) / "plan.json").write_bytes(raw)
    before = _snapshot(repo)
    assert restore.main(["--repo-root", str(repo), "--apply", preview["review_hash"]]) == 1
    assert "Working-file restoration refused:" in capsys.readouterr().err
    assert _snapshot(repo) == before


@pytest.mark.parametrize("temporary", [False, True])
def test_sigkill_interrupted_preview_does_not_block_future_review(restore, capsys, temporary):
    base = Path(tempfile.mkdtemp(prefix="restore-preview-kill-", dir=os.environ.get("ODYLITH_RESTORE_PROOF_ROOT")))
    repo = _published_repo(base)
    before = _snapshot(repo)
    child = """
import os, signal, sys
from pathlib import Path
from odylith.runtime.governance import restore_published_files as restore
mkdir = restore._mkdir_durable
def stop(root, path):
    mkdir(root, path)
    os.kill(os.getpid(), signal.SIGKILL)
restore._mkdir_durable = stop
restore.preview_restore(repo_root=Path(sys.argv[1]), paths=['odylith/radar/one.json', 'odylith/atlas/two.json'])
"""
    process = subprocess.run([sys.executable, "-c", child, str(repo)], cwd=Path(__file__).resolve().parents[3],
                             capture_output=True, text=True, timeout=30)
    assert process.returncode == -9, process.stdout + process.stderr
    receipt, = (repo / restore._RECEIPTS).iterdir()
    assert not list(receipt.iterdir())
    if temporary:
        # Also characterize a killed atomic plan write before its final rename.
        (receipt / ".plan.json.interrupted.tmp").write_bytes(b"partial unadmitted plan")
    assert _snapshot(repo) == before
    assert restore.main(["--repo-root", str(repo), "--apply", receipt.name]) == 1
    assert "Working-file restoration refused:" in capsys.readouterr().err
    other = restore.preview_restore(repo_root=repo, paths=[AUTHORED])
    assert other["review_hash"] != receipt.name
    assert not (receipt / "plan.json").exists()
    resumed = restore.preview_restore(repo_root=repo, paths=TARGETS)
    assert resumed["review_hash"] == receipt.name
    assert (receipt / "plan.json").is_file()
    assert not (receipt / "admitted.json").exists()
    if temporary:
        assert (receipt / ".plan.json.interrupted.tmp").read_bytes() == b"partial unadmitted plan"
    assert _snapshot(repo) == before
    print(f"Retained interrupted-preview proof root: {base}")


@pytest.mark.parametrize("identity", [
    None, {}, [], "active", publication.no_active_generation_identity(),
    {"status": "active"},
    {"status": "active", "write_set_hash": "bad", "publication_sha256": "a" * 64, "generation_manifest_sha256": "b" * 64},
])
def test_new_review_hash_cannot_authorize_invalid_publication_identity(repo, restore, identity):
    preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
    receipt = Path(preview["receipt_path"])
    plan = json.loads((receipt / "plan.json").read_bytes())
    plan["publication"] = identity
    del plan["review_hash"]
    review_hash = hashlib.sha256(restore._canonical(plan)).hexdigest()
    plan["review_hash"] = review_hash
    malformed = receipt.parent / review_hash
    malformed.mkdir()
    (malformed / "plan.json").write_bytes(restore._canonical(plan))
    before = _snapshot(repo)
    with pytest.raises(ValueError):
        restore.apply_restore(repo_root=repo, review_hash=review_hash)
    assert _snapshot(repo) == before
    assert not (malformed / "admitted.json").exists()


def _kill_restoration_before_close(root, restore, paths):
    preview = restore.preview_restore(repo_root=root, paths=paths)
    code = """
import os, signal, sys
from pathlib import Path
from odylith.runtime.governance import restore_published_files as restore
write = restore.atomic_write_bytes
def stop(path, *args, **kwargs):
    if path.name == 'closed.json':
        os.kill(os.getpid(), signal.SIGKILL)
    return write(path, *args, **kwargs)
restore.atomic_write_bytes = stop
restore.apply_restore(repo_root=Path(sys.argv[1]), review_hash=sys.argv[2])
"""
    process = subprocess.run([sys.executable, "-B", "-c", code, str(root), preview["review_hash"]],
                             cwd=Path(__file__).resolve().parents[3], capture_output=True, text=True, timeout=30)
    assert process.returncode == -9, process.stdout + process.stderr
    receipt = Path(preview["receipt_path"])
    assert (receipt / "admitted.json").exists() and not (receipt / "closed.json").exists()
    return preview


@pytest.mark.parametrize("writer", ["ordinary_clean", "authored_frozen", "authored_later"])
def test_real_writer_is_fenced_after_preclose_sigkill_without_losing_restoration(restore, monkeypatch, writer):
    from odylith.runtime.domain_intelligence import greenfield_authored_sync_admission as admission
    from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
    from odylith.runtime.domain_intelligence import greenfield_repository_lock as locks
    from tests.unit.runtime import test_greenfield_authored_sync_admission as authored

    base = Path(tempfile.mkdtemp(prefix=f"restore-fenced-{writer}-", dir=os.environ.get("ODYLITH_RESTORE_PROOF_ROOT")))
    if writer == "ordinary_clean":
        root = _published_repo(base)
        pinned = generations.pin_active_greenfield_generation(root)
        shutil.copy2(pinned.repository_root / AUTHORED, root / AUTHORED)
        selected, tokens, projection = TARGETS, ["radar", "refresh"], TARGETS[0]
    else:
        root = authored.active_repo.__wrapped__(base)
        (root / authored.PROJECTION).write_bytes(b"unpublished projection")
        selected, tokens, projection = [authored.PROJECTION], authored._tokens(authored.AUTHORED), authored.PROJECTION
        if writer == "authored_frozen":
            (root / authored.AUTHORED).write_text(authored.EDITED)
    preview = _kill_restoration_before_close(root, restore, selected)
    if writer == "authored_later":
        (root / authored.AUTHORED).write_text(authored.EDITED)
    before = _snapshot(root)
    receipt = Path(preview["receipt_path"])
    preserved = {name: (receipt / name).read_bytes() for name in ("plan.json", "admitted.json")}
    marker = restore._has_marker
    observed = []

    def locked_marker(*args):
        with pytest.raises(locks.GreenfieldRepositoryBusyError), locks.greenfield_repository_lock(root):
            pytest.fail("restoration fence ran without the repository lock")
        observed.append(True)
        return marker(*args)

    def forbidden(*args, **kwargs):
        pytest.fail("pending restoration reached recovery, authored admission, operation, or publication")

    with monkeypatch.context() as local:
        local.setattr(restore, "_has_marker", locked_marker)
        local.setattr(boundary.GreenfieldCommitJournal, "recover_pending_journals", forbidden)
        local.setattr(admission, "require_authored_sync_admission", forbidden)
        local.setattr(generations, "publish_greenfield_generation", forbidden)
        with pytest.raises(generations.GreenfieldWorkingGenerationDriftError, match="RECOVERY_REQUIRED.*restoration"):
            boundary.run_with_greenfield_managed_mutation_boundary(repo_root=root, command_tokens=tokens, operation=forbidden)
    assert observed and _snapshot(root) == before
    assert {name: (receipt / name).read_bytes() for name in preserved} == preserved
    if writer == "authored_later":
        # A later manual source edit is not silently adopted into the older review.
        with pytest.raises(ValueError, match="non-target"):
            restore.apply_restore(repo_root=root, review_hash=preview["review_hash"])
        assert (root / authored.AUTHORED).read_text() == authored.EDITED
        assert not (receipt / "closed.json").exists()
    else:
        assert restore.apply_restore(repo_root=root, review_hash=preview["review_hash"])["status"] == "restored"
        assert _snapshot(root) == before

        def operation(descriptor):
            assert isinstance(descriptor, int)
            (root / projection).write_bytes(b"new completed writer projection")
            return 0

        assert boundary.run_with_greenfield_managed_mutation_boundary(repo_root=root, command_tokens=tokens, operation=operation) == 0
        assert publication.active_generation_identity(root) != before["publication"]
        generations.require_greenfield_working_generation(root)
        assert restore.preview_restore(repo_root=root, paths=selected)["status"] == "previewed"
        if writer == "authored_frozen":
            assert (root / authored.AUTHORED).read_text() == authored.EDITED
    print(f"Retained writer-fence proof root: {base}")


@pytest.mark.parametrize("entrypoint", ["commit", "activate", "recover", "activate_locked"])
def test_direct_greenfield_admission_fences_before_recovery_or_managed_write(repo, restore, monkeypatch, entrypoint):
    from odylith.runtime.domain_intelligence import greenfield_create_baseline as baseline
    from odylith.runtime.domain_intelligence import greenfield_create_commit as commit
    from odylith.runtime.domain_intelligence import greenfield_repository_lock as locks

    _interrupt_after_admission(repo, restore, monkeypatch)
    before = _snapshot(repo)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        pytest.fail("direct writer crossed pending-restoration admission")

    monkeypatch.setattr(restore.GreenfieldCommitJournal, "recover_pending_journals", forbidden)
    monkeypatch.setattr(commit, "load_sealed_product_create_commit", forbidden)
    monkeypatch.setattr(baseline, "_restore_missing_baseline_shell", forbidden)
    with pytest.raises(RuntimeError, match="restoration") as refused:
        if entrypoint == "commit":
            commit.commit_greenfield_create_transaction(
                repo_root=repo, transaction_file=repo / "not-opened.json", transaction_hash="a" * 64, confirm=True,
            )
        elif entrypoint == "activate_locked":
            with locks.greenfield_repository_lock(repo):
                baseline.activate_completed_greenfield_baseline_locked(repo_root=repo, required_surface_outputs=[])
        else:
            operation = baseline.activate_completed_greenfield_baseline if entrypoint == "activate" else baseline.recover_published_greenfield_baseline
            operation(repo_root=repo, required_surface_outputs=[])
    if entrypoint == "commit":
        assert refused.value.rollback_status == "not_started"
    assert calls == []
    assert _snapshot(repo) == before


def test_ordinary_admission_reads_only_small_history_markers(repo, restore, monkeypatch):
    from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary

    pinned = generations.pin_active_greenfield_generation(repo)
    shutil.copy2(pinned.repository_root / AUTHORED, repo / AUTHORED)
    for index in range(4):
        (repo / TARGETS[0]).write_bytes(str(index).encode() + b"x" * 100_000)
        preview = restore.preview_restore(repo_root=repo, paths=TARGETS)
        restore.apply_restore(repo_root=repo, review_hash=preview["review_hash"])
    restore.preview_restore(repo_root=repo, paths=[AUTHORED])
    orphan = repo / restore._RECEIPTS / ("a" * 64)
    orphan.mkdir()
    (orphan / ".plan.json.interrupted.tmp").write_bytes(b"unadmitted preview")
    original = Path.read_bytes
    history_reads = []

    def bounded_read(path):
        if repo / restore._RECEIPTS in path.parents:
            assert path.name in {"admitted.json", "closed.json"}, "ordinary admission decoded historical plan payload"
            history_reads.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", bounded_read)
    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["radar", "refresh"], operation=lambda descriptor: 0,
    ) == 0
    assert len(history_reads) == 8
    print("Writer history control: 4 closed receipts, 1 preview, 1 orphan; 8 small marker reads, 0 plan payload reads")


@pytest.mark.parametrize("damage", ["admitted", "closed", "closed_only", "missing_plan", "foreign_hash"])
def test_corrupt_restoration_admission_fences_ordinary_writers(repo, restore, monkeypatch, damage):
    from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary

    preview = _interrupt_after_admission(repo, restore, monkeypatch)
    receipt = Path(preview["receipt_path"])
    if damage == "missing_plan":
        (receipt / "plan.json").unlink()
    elif damage == "closed_only":
        (receipt / "admitted.json").unlink()
        (receipt / "closed.json").write_bytes(restore._canonical(restore._marker(preview["review_hash"], "closed")))
    elif damage == "foreign_hash":
        (receipt / "admitted.json").write_bytes(restore._canonical(restore._marker("b" * 64, "admitted")))
    else:
        (receipt / f"{damage}.json").write_bytes(b"{}")
    before = _snapshot(repo)

    def forbidden(*args, **kwargs):
        pytest.fail("corrupt admission reached journal recovery or callback")

    monkeypatch.setattr(boundary.GreenfieldCommitJournal, "recover_pending_journals", forbidden)
    with pytest.raises(generations.GreenfieldWorkingGenerationDriftError, match="RECOVERY_REQUIRED.*restoration"):
        boundary.run_with_greenfield_managed_mutation_boundary(repo_root=repo, command_tokens=["radar", "refresh"], operation=forbidden)
    assert _snapshot(repo) == before


def test_restore_admission_dependency_is_in_postconfirm_runtime_inventory():
    from odylith.runtime.domain_intelligence import greenfield_commit_transaction as commit

    assert commit._POSTCONFIRM_RUNTIME_SOURCE_FILES.count("runtime/governance/restore_published_files.py") == 1


def test_pending_restoration_cli_refusal_is_structured_before_dispatch(repo, restore, monkeypatch, capsys):
    from odylith import cli

    _interrupt_after_admission(repo, restore, monkeypatch)
    before = _snapshot(repo)
    monkeypatch.setattr(cli, "_dispatch_main", lambda *a, **k: pytest.fail("pending restoration reached CLI dispatch"))
    assert cli.main(["radar", "refresh", "--repo-root", str(repo)]) == 1
    assert "RECOVERY_REQUIRED: working-file restoration" in capsys.readouterr().err
    assert _snapshot(repo) == before


def test_pending_restoration_keeps_read_only_commands_available(repo, restore, monkeypatch):
    from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary

    _interrupt_after_admission(repo, restore, monkeypatch)
    before = _snapshot(repo)
    descriptors = []
    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["version"], operation=lambda descriptor: descriptors.append(descriptor) or 0,
    ) == 0
    assert descriptors == [None] and _snapshot(repo) == before
