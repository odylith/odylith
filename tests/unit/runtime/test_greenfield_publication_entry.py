from __future__ import annotations

import hashlib
import json

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets


WRITE_SET = "a" * 64
MANIFEST = "b" * 64


def test_publication_entry_is_exact_and_does_not_require_its_outer_transaction():
    entry = publication.compile_greenfield_publication_entry(
        write_set_hash=WRITE_SET, generation_manifest_sha256=MANIFEST,
    )
    identity = publication.require_sealed_greenfield_publication_entry(
        entry, write_set_hash=WRITE_SET, generation_manifest_sha256=MANIFEST,
    )
    assert identity == {
        "write_set_hash": WRITE_SET,
        "generation_manifest_sha256": MANIFEST,
        "publication_sha256": hashlib.sha256(entry.encode()).hexdigest(),
    }
    assert "transaction_hash" not in entry
    assert "browser-snapshots" not in entry
    assert "active-generation.v1.json" not in entry
    assert "cache: 'no-store'" in entry
    assert "location.replace" in entry


@pytest.mark.parametrize("change", ["prefix", "suffix", "spacing", "write_set", "manifest", "extra", "duplicate", "malformed", "null"])
def test_publication_entry_rejects_changed_bytes_or_identity(change):
    entry = publication.compile_greenfield_publication_entry(
        write_set_hash=WRITE_SET, generation_manifest_sha256=MANIFEST,
    )
    if change == "prefix":
        entry = " " + entry
    elif change == "suffix":
        entry += "\n"
    elif change == "spacing":
        entry = entry.replace('"write_set_hash":', '"write_set_hash": ')
    elif change == "write_set":
        entry = entry.replace(WRITE_SET, "c" * 64)
    elif change == "manifest":
        entry = entry.replace(MANIFEST, "c" * 64)
    elif change == "extra":
        entry = entry.replace('{"generation_manifest_sha256":', '{"extra":true,"generation_manifest_sha256":', 1)
    elif change == "duplicate":
        entry = entry.replace('{"generation_manifest_sha256":', '{"write_set_hash":' + json.dumps(WRITE_SET) + ',"generation_manifest_sha256":', 1)
    else:
        raw = json.dumps({"generation_manifest_sha256": MANIFEST, "version": publication.PUBLICATION_ENTRY_VERSION,
                          "write_set_hash": WRITE_SET}, sort_keys=True, separators=(",", ":"))
        entry = entry.replace(raw, "{" if change == "malformed" else "null")
    with pytest.raises(ValueError, match="publication"):
        publication.require_sealed_greenfield_publication_entry(
            entry, write_set_hash=WRITE_SET, generation_manifest_sha256=MANIFEST,
        )


def test_publication_validation_does_not_call_its_compiler(monkeypatch):
    entry = publication.compile_greenfield_publication_entry(
        write_set_hash=WRITE_SET, generation_manifest_sha256=MANIFEST,
    )

    def forbidden(**kwargs):
        raise AssertionError("publication compilation after CONFIRM")

    monkeypatch.setattr(publication, "compile_greenfield_publication_entry", forbidden)
    publication.require_sealed_greenfield_publication_entry(
        entry, write_set_hash=WRITE_SET, generation_manifest_sha256=MANIFEST,
    )


def _entry(write_hash=WRITE_SET, manifest_hash=MANIFEST):
    return publication.compile_greenfield_publication_entry(
        write_set_hash=write_hash, generation_manifest_sha256=manifest_hash,
    )


def _install_entry(root, entry):
    path = root / "odylith/index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(entry, encoding="utf-8")
    return path


def test_active_reader_and_matcher_bind_exact_publication_hash(tmp_path):
    entry = _entry()
    _install_entry(tmp_path, entry)
    identity = publication.read_active_publication(tmp_path)
    assert identity == {
        "write_set_hash": WRITE_SET, "generation_manifest_sha256": MANIFEST,
        "publication_sha256": hashlib.sha256(entry.encode("utf-8")).hexdigest(),
    }
    assert publication.active_publication_matches(repo_root=tmp_path, expected_publication=identity)
    for field in identity:
        wrong = {**identity, field: "c" * 64}
        assert not publication.active_publication_matches(repo_root=tmp_path, expected_publication=wrong)
    assert publication.active_generation_identity(tmp_path) == {"status": publication.ACTIVE, **identity}


@pytest.mark.parametrize("kind", ["record", "malformed", "dangling_symlink"])
def test_legacy_json_is_rejected_and_preserved_even_with_valid_entry(tmp_path, kind):
    entry = _install_entry(tmp_path, _entry())
    legacy = tmp_path / ".odylith/runtime/greenfield/active-generation.v1.json"
    legacy.parent.mkdir(parents=True)
    if kind == "dangling_symlink":
        legacy.symlink_to(tmp_path / "missing-state")
    else:
        legacy.write_text("{}" if kind == "record" else "{broken", encoding="utf-8")
    before = legacy.read_bytes() if not legacy.is_symlink() else legacy.readlink()
    with pytest.raises(RuntimeError, match="JSON publication state requires explicit migration"):
        publication.read_active_publication(tmp_path)
    assert (legacy.read_bytes() if not legacy.is_symlink() else legacy.readlink()) == before
    assert entry.read_text(encoding="utf-8") == _entry()


@pytest.mark.parametrize("state", ["missing", "ordinary", "invalid_utf8", "directory"])
def test_retained_working_shell_makes_missing_or_replaced_entry_fail_closed(tmp_path, state):
    path = _install_entry(tmp_path, _entry())
    (path.parent / "tooling-shell.html").write_text("retained working shell", encoding="utf-8")
    if state == "missing":
        path.unlink()
    elif state == "ordinary":
        path.write_text("<h1>Unpublished shell</h1>", encoding="utf-8")
    elif state == "invalid_utf8":
        path.write_bytes(b"\xff")
    else:
        path.unlink()
        path.mkdir()
    with pytest.raises(RuntimeError, match="publication entry"):
        publication.read_active_publication(tmp_path)
    assert (path.parent / "tooling-shell.html").read_text() == "retained working shell"


def test_unactivated_repo_is_distinct_from_lost_publication(tmp_path):
    assert publication.read_active_publication(tmp_path) is None
    path = _install_entry(tmp_path, "<h1>Ordinary working shell</h1>")
    assert publication.active_generation_identity(tmp_path) == publication.no_active_generation_identity()
    (path.parent / "tooling-shell.html").symlink_to(tmp_path / "missing-working-shell")
    with pytest.raises(RuntimeError, match="replaced"):
        publication.read_active_publication(tmp_path)


@pytest.mark.parametrize("kind", ["entry", "dangling_entry", "parent"])
def test_publication_reader_rejects_symlink_paths(tmp_path, kind):
    repo = tmp_path / "repo"
    path = _install_entry(repo, _entry())
    outside = tmp_path / "outside"
    if kind == "parent":
        path.parent.rename(outside)
        path.parent.symlink_to(outside, target_is_directory=True)
    else:
        path.rename(outside)
        path.symlink_to(outside if kind == "entry" else tmp_path / "missing-entry")
    with pytest.raises(RuntimeError, match="unsafe symlink"):
        publication.read_active_publication(repo)


@pytest.mark.parametrize("raw", ["{", "null", "[]", '{"extra":true}',
                                    '{"write_set_hash":"' + WRITE_SET + '","write_set_hash":"' + WRITE_SET + '"}'])
def test_active_reader_rejects_malformed_or_noncanonical_record(tmp_path, raw):
    entry = _entry()
    original = json.dumps({"generation_manifest_sha256": MANIFEST, "version": publication.PUBLICATION_ENTRY_VERSION,
                           "write_set_hash": WRITE_SET}, sort_keys=True, separators=(",", ":"))
    _install_entry(tmp_path, entry.replace(original, raw))
    with pytest.raises(ValueError):
        publication.read_active_publication(tmp_path)


def test_stale_predecessor_and_same_publication_are_rejected_without_writes(tmp_path):
    empty = publication.no_active_generation_identity()
    first = publication.publish_sealed_publication(repo_root=tmp_path, expected_identity=empty, sealed_entry_text=_entry())
    path = tmp_path / "odylith/index.html"
    first_bytes = path.read_bytes()
    with pytest.raises(ValueError, match="active generation changed"):
        publication.publish_sealed_publication(repo_root=tmp_path, expected_identity=empty, sealed_entry_text=_entry("c" * 64))
    with pytest.raises(ValueError, match="fresh predecessor-bound transition"):
        publication.publish_sealed_publication(
            repo_root=tmp_path, expected_identity={"status": publication.ACTIVE, **first}, sealed_entry_text=_entry(),
        )
    assert path.read_bytes() == first_bytes


def test_unchanged_managed_bytes_cannot_reuse_prior_write_identity(tmp_path):
    # Carrier setup only; admitted journal history is tested by its own transaction suite.
    entry = _install_entry(tmp_path, _entry())
    (entry.parent / "tooling-shell.html").write_text("unchanged working shell", encoding="utf-8")
    before = write_sets.compile_greenfield_repository_write_set(source_root=tmp_path, staged_root=tmp_path)
    manifest = generations.compile_greenfield_generation_manifest(before)
    next_entry = _entry(before["write_set_hash"], hashlib.sha256(manifest.encode("utf-8")).hexdigest())
    publication.publish_sealed_publication(
        repo_root=tmp_path, expected_identity=before["active_generation_precondition"], sealed_entry_text=next_entry,
    )
    after = write_sets.compile_greenfield_repository_write_set(source_root=tmp_path, staged_root=tmp_path)
    assert after["after_image"] == before["after_image"]
    assert after["active_generation_precondition"] != before["active_generation_precondition"]
    assert after["write_set_hash"] != before["write_set_hash"]
    with pytest.raises(ValueError, match="active generation changed"):
        write_sets.require_greenfield_repository_preconditions(repo_root=tmp_path, write_set=before)
