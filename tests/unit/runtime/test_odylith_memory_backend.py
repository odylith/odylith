from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.common import derivation_provenance
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.memory import odylith_memory_backend


class _FakeAsyncConnection:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class _FakeArrowTable:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def to_pylist(self) -> list[dict[str, object]]:
        return list(self._rows)


class _FakeNativeTable:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class _FakeSearch:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def where(self, _clause: str) -> "_FakeSearch":
        return self

    def limit(self, _limit: int) -> "_FakeSearch":
        return self

    def to_list(self) -> list[dict[str, object]]:
        return list(self._rows)


class _FakeTable:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self._table = _FakeNativeTable()

    def count_rows(self) -> int:
        return len(self._rows)

    def search(self, *_args: object) -> _FakeSearch:
        return _FakeSearch(self._rows)

    def to_arrow(self) -> _FakeArrowTable:
        return _FakeArrowTable(self._rows)


class _FakeLanceConnection:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self._conn = _FakeAsyncConnection()
        self._rows = list(rows or [])
        self.created_tables: list[dict[str, object]] = []
        self.opened_tables: list[_FakeTable] = []

    def open_table(self, _table_name: str) -> _FakeTable:
        table = _FakeTable(self._rows)
        self.opened_tables.append(table)
        return table

    def create_table(
        self,
        table_name: str,
        *,
        data: list[dict[str, object]] | None = None,
        schema: object | None = None,
        mode: str | None = None,
    ) -> None:
        self.created_tables.append(
            {
                "table_name": table_name,
                "data": list(data or []),
                "schema": schema,
                "mode": mode,
            }
        )


def test_create_lance_tables_closes_underlying_async_connection(monkeypatch, tmp_path: Path) -> None:
    backend_root = odylith_memory_backend.local_backend_root(repo_root=tmp_path)
    backend_root.mkdir(parents=True, exist_ok=True)
    connections: list[_FakeLanceConnection] = []

    def _fake_open_lance_connection(*, lance_root: Path) -> _FakeLanceConnection:
        lance_root.mkdir(parents=True, exist_ok=True)
        connection = _FakeLanceConnection()
        connections.append(connection)
        return connection

    monkeypatch.setattr(odylith_memory_backend, "_open_lance_connection", _fake_open_lance_connection)

    odylith_memory_backend._create_lance_tables(  # noqa: SLF001
        repo_root=tmp_path,
        documents=[{"doc_key": "doc-1"}],
        edges=[{"edge_key": "edge-1"}],
    )

    assert len(connections) == 1
    assert connections[0]._conn.closed == 1
    assert odylith_memory_backend.local_lance_root(repo_root=tmp_path).is_dir()


def test_exact_lookup_closes_underlying_async_connection(monkeypatch, tmp_path: Path) -> None:
    rows = [
        {
            "doc_key": "code:src/example.py",
            "kind": "code",
            "entity_id": "src/example.py",
            "title": "example",
            "path": "src/example.py",
            "content": "",
            "entity_id_lower": "src/example.py",
            "title_lower": "example",
            "path_lower": "src/example.py",
        }
    ]
    connections: list[_FakeLanceConnection] = []

    def _fake_open_lance_connection(*, lance_root: Path) -> _FakeLanceConnection:
        lance_root.mkdir(parents=True, exist_ok=True)
        connection = _FakeLanceConnection(rows=rows)
        connections.append(connection)
        return connection

    monkeypatch.setattr(odylith_memory_backend, "local_backend_ready", lambda **_: True)
    monkeypatch.setattr(odylith_memory_backend, "_open_lance_connection", _fake_open_lance_connection)

    results = odylith_memory_backend.exact_lookup(
        repo_root=tmp_path,
        query="src/example.py",
        limit=1,
    )

    assert len(results) == 1
    assert results[0]["path"] == "src/example.py"
    assert len(connections) == 1
    assert connections[0]._conn.closed == 1
    assert len(connections[0].opened_tables) == 1
    assert connections[0].opened_tables[0]._table.closed == 1


def test_all_documents_closes_underlying_async_connection(monkeypatch, tmp_path: Path) -> None:
    rows = [
        {
            "doc_key": "code:src/example.py",
            "kind": "code",
            "entity_id": "src/example.py",
            "title": "example",
            "path": "src/example.py",
            "content": "body",
            "content_hash": "hash",
            "provenance_json": "{}",
            "embedding": [0.1, 0.2],
        }
    ]
    connections: list[_FakeLanceConnection] = []

    def _fake_open_lance_connection(*, lance_root: Path) -> _FakeLanceConnection:
        lance_root.mkdir(parents=True, exist_ok=True)
        connection = _FakeLanceConnection(rows=rows)
        connections.append(connection)
        return connection

    monkeypatch.setattr(odylith_memory_backend, "local_backend_ready", lambda **_: True)
    monkeypatch.setattr(odylith_memory_backend, "_open_lance_connection", _fake_open_lance_connection)

    results = odylith_memory_backend.all_documents(repo_root=tmp_path, include_embedding=True)

    assert len(results) == 1
    assert results[0]["embedding"] == [0.1, 0.2]
    assert len(connections) == 1
    assert connections[0]._conn.closed == 1
    assert len(connections[0].opened_tables) == 1
    assert connections[0].opened_tables[0]._table.closed == 1


def test_lance_documents_table_closes_native_table_and_connection(monkeypatch, tmp_path: Path) -> None:
    connections: list[_FakeLanceConnection] = []
    opened_tables: list[_FakeTable] = []

    class _TrackingConnection(_FakeLanceConnection):
        def open_table(self, _table_name: str) -> _FakeTable:
            table = _FakeTable([])
            opened_tables.append(table)
            return table

    def _fake_open_lance_connection(*, lance_root: Path) -> _TrackingConnection:
        lance_root.mkdir(parents=True, exist_ok=True)
        connection = _TrackingConnection()
        connections.append(connection)
        return connection

    monkeypatch.setattr(odylith_memory_backend, "_open_lance_connection", _fake_open_lance_connection)

    with odylith_memory_backend._lance_documents_table(repo_root=tmp_path):  # noqa: SLF001
        pass

    assert len(connections) == 1
    assert connections[0]._conn.closed == 1
    assert len(opened_tables) == 1
    assert opened_tables[0]._table.closed == 1


def test_load_manifest_restores_ready_state_from_live_backend_when_manifest_is_stale(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest_path = odylith_memory_backend.local_manifest_path(repo_root=tmp_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "projection_fingerprint": "fp-1",
                "projection_scope": "reasoning",
                "input_fingerprint": "input-1",
                "document_count": 3,
                "edge_count": 1,
                "ready": False,
                "status": "dependencies_missing",
            }
        ),
        encoding="utf-8",
    )
    odylith_memory_backend.local_lance_root(repo_root=tmp_path).mkdir(parents=True, exist_ok=True)
    odylith_memory_backend.local_tantivy_root(repo_root=tmp_path).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(odylith_memory_backend, "backend_dependencies_available", lambda: True)
    monkeypatch.setattr(
        odylith_memory_backend,
        "dependency_snapshot",
        lambda: {
            "lancedb": {"available": True, "version": "1"},
            "pyarrow": {"available": True, "version": "1"},
            "tantivy": {"available": True, "version": "1"},
        },
    )
    monkeypatch.setattr(odylith_memory_backend, "_backend_operational_check", lambda **_: (True, ""))
    monkeypatch.setattr(
        odylith_memory_backend.odylith_projection_bundle,
        "load_bundle_manifest",
        lambda **_: {
            "ready": True,
            "projection_fingerprint": "fp-1",
            "projection_scope": "reasoning",
            "input_fingerprint": "input-1",
            "document_count": 3,
            "edge_count": 1,
        },
    )

    manifest = odylith_memory_backend.load_manifest(repo_root=tmp_path)

    assert manifest["ready"] is True
    assert manifest["status"] == "ready"
    assert manifest["storage"] == "lance_local_columnar"
    assert manifest["sparse_recall"] == "tantivy_sparse_recall"
    assert odylith_memory_backend.local_backend_ready(repo_root=tmp_path) is True
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert persisted["ready"] is True
    assert persisted["status"] == "ready"


def test_local_backend_ready_for_projection_requires_matching_scope_and_fingerprint(
    monkeypatch,
    tmp_path: Path,
) -> None:
    provenance = derivation_provenance.build_derivation_provenance(
        repo_root=tmp_path,
        projection_scope="reasoning",
        projection_fingerprint="fp-1",
        sync_generation=0,
        code_version="backend-v1",
        flags={"backend_dependencies_available": True, "storage": "lance_local_columnar"},
    )
    manifest_path = odylith_memory_backend.local_manifest_path(repo_root=tmp_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "projection_fingerprint": "fp-1",
                "projection_scope": "reasoning",
                "provenance": provenance,
                "ready": True,
                "status": "ready",
            }
        ),
        encoding="utf-8",
    )
    odylith_memory_backend.local_lance_root(repo_root=tmp_path).mkdir(parents=True, exist_ok=True)
    odylith_memory_backend.local_tantivy_root(repo_root=tmp_path).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(odylith_memory_backend, "backend_dependencies_available", lambda: True)

    assert (
        odylith_memory_backend.local_backend_ready_for_projection(
            repo_root=tmp_path,
            projection_fingerprint="fp-1",
            projection_scope="reasoning",
            provenance=provenance,
        )
        is True
    )
    assert (
        odylith_memory_backend.local_backend_ready_for_projection(
            repo_root=tmp_path,
            projection_fingerprint="fp-2",
            projection_scope="reasoning",
            provenance=provenance,
        )
        is False
    )
    assert (
        odylith_memory_backend.local_backend_ready_for_projection(
            repo_root=tmp_path,
            projection_fingerprint="fp-1",
            projection_scope="full",
            provenance=provenance,
        )
        is False
    )
    assert (
        odylith_memory_backend.local_backend_ready_for_projection(
            repo_root=tmp_path,
            projection_fingerprint="fp-1",
            projection_scope="reasoning",
            provenance={**provenance, "code_version": "backend-v2"},
        )
        is False
    )


def test_projection_scope_satisfies_compatible_superset_rules() -> None:
    assert odylith_memory_backend.compatible_projection_scopes(requested_scope="default") == (
        "default",
        "reasoning",
        "full",
    )
    assert odylith_memory_backend.compatible_projection_scopes(requested_scope="reasoning") == (
        "reasoning",
        "full",
    )
    assert odylith_memory_backend.projection_scope_satisfies(
        available_scope="full",
        requested_scope="reasoning",
    )
    assert odylith_memory_backend.projection_scope_satisfies(
        available_scope="reasoning",
        requested_scope="default",
    )
    assert not odylith_memory_backend.projection_scope_satisfies(
        available_scope="reasoning",
        requested_scope="full",
    )


def test_materialize_local_backend_reuses_compatible_full_backend_for_default_request(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest_path = odylith_memory_backend.local_manifest_path(repo_root=tmp_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "projection_fingerprint": "fp-full",
                "projection_scope": "full",
                "input_fingerprint": "input-1",
                "ready": True,
                "status": "ready",
                "storage": "lance_local_columnar",
                "sparse_recall": "tantivy_sparse_recall",
            }
        ),
        encoding="utf-8",
    )
    odylith_memory_backend.local_lance_root(repo_root=tmp_path).mkdir(parents=True, exist_ok=True)
    odylith_memory_backend.local_tantivy_root(repo_root=tmp_path).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(odylith_memory_backend, "backend_dependencies_available", lambda: True)
    monkeypatch.setattr(odylith_memory_backend, "_backend_operational_check", lambda **_: (True, ""))
    monkeypatch.setattr(
        odylith_memory_backend,
        "load_compiled_materialization_inputs",
        lambda **_: {
            "documents": [],
            "edges": [],
            "document_count": 0,
            "edge_count": 0,
            "input_fingerprint": "input-1",
            "compiler_manifest": {
                "ready": True,
                "projection_scope": "full",
                "projection_fingerprint": "fp-full",
            },
        },
    )
    monkeypatch.setattr(
        store,
        "projection_input_fingerprint",
        lambda **kwargs: {
            "default": "fp-default",
            "reasoning": "fp-reasoning",
            "full": "fp-full",
        }[kwargs["scope"]],
    )
    monkeypatch.setattr(
        odylith_memory_backend,
        "_create_lance_tables",
        lambda **_: (_ for _ in ()).throw(AssertionError("compatible manifest should be reused")),
    )
    monkeypatch.setattr(
        odylith_memory_backend,
        "_create_tantivy_index",
        lambda **_: (_ for _ in ()).throw(AssertionError("compatible manifest should be reused")),
    )

    summary = odylith_memory_backend.materialize_local_backend(
        repo_root=tmp_path,
        projection_fingerprint="fp-default",
        projection_scope="default",
    )

    assert summary["reused"] is True
    assert summary["projection_scope"] == "full"
    assert summary["reused_projection_scope"] == "full"
    assert summary["requested_projection_scope"] == "default"
