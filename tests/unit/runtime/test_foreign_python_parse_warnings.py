from __future__ import annotations

import ast
from pathlib import Path
import warnings

from odylith.runtime.analysis_engine import import_graph
from odylith.runtime.common.python_source_parse import (
    parse_python_source_for_static_analysis,
)
from odylith.runtime.context_engine import (
    odylith_context_engine_code_graph_runtime as code_graph_runtime,
)
from odylith.runtime.context_engine import (
    odylith_context_engine_projection_query_runtime as projection_query_runtime,
)
from odylith.runtime.evaluation import odylith_benchmark_runner as benchmark_runner


def test_static_analysis_parser_suppresses_foreign_python_warnings() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        tree = parse_python_source_for_static_analysis(
            '"""warning-heavy consumer docstring with \\$ escape"""\nVALUE = 1\n',
            filename="consumer.py",
        )

    assert isinstance(tree, ast.Module)
    assert caught == []


def test_import_graph_build_stays_quiet_for_warning_heavy_python(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    pkg = repo_root / "src" / "sample"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "beta.py").write_text("VALUE = 1\n", encoding="utf-8")
    (pkg / "alpha.py").write_text(
        '"""warning-heavy consumer docstring with \\$ escape"""\nimport sample.beta\n',
        encoding="utf-8",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        artifacts, edges, ctx = import_graph.build_import_graph(repo_root, ["Python"])

    assert caught == []
    assert ctx.file_count == 3
    assert any(artifact.path == "src/sample/alpha.py" for artifact in artifacts)
    assert any(
        edge.source_path == "src/sample/alpha.py"
        and edge.target_path == "src/sample/beta.py"
        for edge in edges
    )


def test_code_graph_python_artifact_parse_stays_quiet_for_warning_heavy_python(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    pkg = repo_root / "src" / "sample"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "beta.py").write_text("VALUE = 1\n", encoding="utf-8")
    (pkg / "alpha.py").write_text(
        '"""warning-heavy consumer docstring with \\$ escape"""\nimport sample.beta\n',
        encoding="utf-8",
    )
    module_index = {
        "sample.alpha": "src/sample/alpha.py",
        "sample.beta": "src/sample/beta.py",
    }

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        artifact, edges = code_graph_runtime._parse_python_artifact(  # noqa: SLF001
            repo_root=repo_root,
            rel_path="src/sample/alpha.py",
            module_name="sample.alpha",
            module_index=module_index,
        )

    assert caught == []
    assert artifact["imports"] == ["src/sample/beta.py"]
    assert any(
        edge["source_path"] == "src/sample/alpha.py"
        and edge["target_path"] == "src/sample/beta.py"
        for edge in edges
    )


def test_projection_test_graph_stays_quiet_for_warning_heavy_tests(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    pkg = repo_root / "src" / "sample"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "beta.py").write_text("VALUE = 1\n", encoding="utf-8")
    test_path = repo_root / "tests" / "test_warning_heavy.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(
        '"""warning-heavy consumer docstring with \\$ escape"""\n'
        "import sample.beta\n\n"
        "def test_warning_heavy() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = projection_query_runtime._load_test_graph(  # noqa: SLF001
            repo_root=repo_root,
            code_artifacts=[{"module_name": "sample.beta", "path": "src/sample/beta.py"}],
        )

    assert caught == []
    assert len(rows) == 1
    assert rows[0]["node_id"] == "tests/test_warning_heavy.py::test_warning_heavy"
    assert rows[0]["target_paths"] == ["src/sample/beta.py"]


def test_benchmark_companion_scan_stays_quiet_for_warning_heavy_python(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    pkg = repo_root / "src" / "sample"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "beta.py").write_text("VALUE = 1\n", encoding="utf-8")
    docs_path = repo_root / "docs" / "guide.md"
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text("# Guide\n", encoding="utf-8")
    validation_path = repo_root / "tests" / "test_warning_heavy.py"
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.write_text(
        '"""warning-heavy consumer docstring with \\$ escape"""\n'
        "import sample.beta\n\n"
        "GUIDE = 'docs/guide.md'\n",
        encoding="utf-8",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        paths = benchmark_runner._validation_companion_file_paths(  # noqa: SLF001
            repo_root=repo_root,
            validation_paths=["tests/test_warning_heavy.py"],
        )

    assert caught == []
    assert "docs/guide.md" in paths
    assert "src/sample/beta.py" in paths
