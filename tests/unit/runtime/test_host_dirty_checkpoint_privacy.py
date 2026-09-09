"""Deferred governance needs paths, never a second copy of shell input."""

from pathlib import Path

from odylith.runtime.surfaces import codex_host_post_bash_checkpoint as checkpoint
from odylith.runtime.surfaces import host_dirty_checkpoint as dirty


def test_checkpoint_keeps_scope_without_persisting_inline_content(tmp_path: Path, monkeypatch) -> None:
    paths = ["odylith/radar/source/INDEX.md"]
    monkeypatch.setattr(checkpoint, "inferred_command_paths", lambda **kwargs: paths)
    monkeypatch.setattr(checkpoint, "command_scoped_governed_paths", lambda **kwargs: paths)
    inline_content = "synthetic-private-content-never-to-persist"
    event_id = checkpoint.record_deferred_checkpoint_event(
        project_dir=tmp_path,
        command=f"apply_patch <<'PATCH'\n+{inline_content}\nPATCH",
        session_id="privacy-control",
    )

    rows = dirty.read_dirty_events(repo_root=tmp_path, session_id="privacy-control")
    assert len(rows) == 1
    assert rows[0]["id"] == event_id
    assert rows[0]["paths"] == paths
    assert dirty.deduped_governed_paths(rows) == paths
    assert "command" not in rows[0]
    assert inline_content not in dirty.event_store_path(tmp_path).read_text()
    assert dirty.clear_dirty_events(repo_root=tmp_path, event_ids=[event_id])
    assert dirty.read_dirty_events(repo_root=tmp_path) == []
