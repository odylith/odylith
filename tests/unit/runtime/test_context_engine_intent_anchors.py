from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_store as store


def _resolve_session_scope(tmp_path: Path, monkeypatch, *, intent: str) -> dict[str, object]:
    store._PROCESS_PATH_SCOPE_CACHE.clear()  # noqa: SLF001
    source_root = tmp_path / "src" / "odylith" / "runtime" / "context_engine"
    source_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(store.governance, "collect_meaningful_changed_paths", lambda **kwargs: [])  # noqa: ARG005
    monkeypatch.setattr(store, "_load_session_state", lambda **kwargs: None)
    return store._resolve_changed_path_scope_context(  # noqa: SLF001
        repo_root=tmp_path,
        explicit_paths=(),
        use_working_tree=False,
        working_tree_scope="session",
        session_id="session-1",
        intent=intent,
    )


def test_session_scope_accepts_planned_new_src_file_anchor_paths(tmp_path: Path, monkeypatch) -> None:
    payload = _resolve_session_scope(
        tmp_path,
        monkeypatch,
        intent="Create src/odylith/runtime/context_engine/new_startup_probe.py for startup routing.",
    )

    assert payload["intent_anchor_paths"] == ["src/odylith/runtime/context_engine/new_startup_probe.py"]
    assert payload["analysis_paths"] == ["src/odylith/runtime/context_engine/new_startup_probe.py"]


def test_session_scope_rejects_untrusted_planned_path_extensions(tmp_path: Path, monkeypatch) -> None:
    payload = _resolve_session_scope(
        tmp_path,
        monkeypatch,
        intent="Create src/odylith/runtime/context_engine/new_startup_probe.tmp for startup routing.",
    )

    assert payload["intent_anchor_paths"] == []
    assert payload["analysis_paths"] == []
