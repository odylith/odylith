from __future__ import annotations

from pathlib import Path

from odylith.runtime.analysis_engine import incremental_import_graph


def _write_python_repo(repo_root: Path) -> None:
    pkg = repo_root / "src" / "sample"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "alpha.py").write_text("from sample import beta\n", encoding="utf-8")
    (pkg / "beta.py").write_text("VALUE = 1\n", encoding="utf-8")


def test_incremental_import_graph_reuses_cached_parse_rows(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write_python_repo(repo_root)

    artifacts, edges, ctx = incremental_import_graph.build_import_graph(repo_root, ["Python"])

    assert len(artifacts) == 3
    assert len(edges) == 1
    assert ctx.file_count == 3
    assert (repo_root / ".odylith" / "runtime" / "latency-cache" / "show-import-graph" / "manifest.v1.json").is_file()

    original = incremental_import_graph._parse_source_file  # noqa: SLF001
    calls = {"count": 0}

    def _counting_parse(**kwargs):  # noqa: ANN003
        calls["count"] += 1
        return original(**kwargs)

    monkeypatch.setattr(incremental_import_graph, "_parse_source_file", _counting_parse)
    incremental_import_graph.build_import_graph(repo_root, ["Python"])

    assert calls["count"] == 0

    (repo_root / "src" / "sample" / "beta.py").write_text("VALUE = 2\n", encoding="utf-8")
    incremental_import_graph.build_import_graph(repo_root, ["Python"])

    assert calls["count"] == 1
