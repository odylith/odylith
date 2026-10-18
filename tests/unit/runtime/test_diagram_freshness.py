import hashlib
from pathlib import Path

from odylith.runtime.common import diagram_freshness


def test_normalize_mermaid_render_source_ignores_review_comments() -> None:
    definition = "%% Reviewed 2026-04-09\nflowchart TD\n  A-->B  \n"

    normalized = diagram_freshness.normalize_mermaid_render_source(definition)

    assert normalized == "flowchart TD\n  A-->B\n"


def test_mermaid_render_fingerprint_includes_atlas_render_style(tmp_path: Path) -> None:
    source_mmd = tmp_path / "demo.mmd"
    source_mmd.write_text("%% Reviewed 2026-05-03\nflowchart TD\n  A-->B\n", encoding="utf-8")
    normalized = diagram_freshness.normalize_mermaid_render_source(source_mmd.read_text(encoding="utf-8"))
    raw_source_fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    fingerprint = diagram_freshness.ContentFingerprintCache().mermaid_render_fingerprint(source_mmd)

    assert diagram_freshness.mermaid_render_style_fingerprint()
    assert fingerprint != raw_source_fingerprint


def test_mermaid_render_style_fingerprint_includes_worker_polish(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    config_path = tmp_path / "mermaid_render_config.json"
    worker_path = tmp_path / "mermaid_cli_worker.mjs"
    config_path.write_text('{"theme": "base"}\n', encoding="utf-8")
    worker_path.write_text("const clusterPalette = [];\n", encoding="utf-8")
    monkeypatch.setattr(diagram_freshness, "_MERMAID_RENDER_CONFIG_PATH", config_path)
    monkeypatch.setattr(diagram_freshness, "_MERMAID_RENDER_WORKER_PATH", worker_path)

    first = diagram_freshness.mermaid_render_style_fingerprint()
    worker_path.write_text("const clusterPalette = ['changed'];\n", encoding="utf-8")
    second = diagram_freshness.mermaid_render_style_fingerprint()

    assert first != second


def test_watched_path_fingerprints_ignore_mtime_only_churn(tmp_path: Path) -> None:
    watched_path = tmp_path / "README.md"
    watched_path.write_text("# Demo\n", encoding="utf-8")
    cache = diagram_freshness.ContentFingerprintCache()

    first = diagram_freshness.watched_path_fingerprints(
        repo_root=tmp_path,
        watched_paths=("README.md",),
        resolve_path=lambda token: (tmp_path / token).resolve(),
        cache=cache,
    )
    watched_path.touch()
    second = diagram_freshness.watched_path_fingerprints(
        repo_root=tmp_path,
        watched_paths=("README.md",),
        resolve_path=lambda token: (tmp_path / token).resolve(),
        cache=diagram_freshness.ContentFingerprintCache(),
    )

    assert first == second


def test_watched_path_fingerprints_ignore_python_bytecode_cache(tmp_path: Path) -> None:
    watched_dir = tmp_path / "src" / "odylith" / "runtime" / "intervention_engine"
    module_path = watched_dir / "value_engine.py"
    bytecode_path = watched_dir / "__pycache__" / "value_engine.cpython-313.pyc"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("def value_engine() -> str:\n    return 'ok'\n", encoding="utf-8")
    bytecode_path.parent.mkdir(parents=True, exist_ok=True)
    bytecode_path.write_bytes(b"compiled")

    first = diagram_freshness.watched_path_fingerprints(
        repo_root=tmp_path,
        watched_paths=("src/odylith/runtime/intervention_engine",),
        resolve_path=lambda token: (tmp_path / token).resolve(),
        cache=diagram_freshness.ContentFingerprintCache(),
    )
    bytecode_path.unlink()
    bytecode_path.parent.rmdir()
    second = diagram_freshness.watched_path_fingerprints(
        repo_root=tmp_path,
        watched_paths=("src/odylith/runtime/intervention_engine",),
        resolve_path=lambda token: (tmp_path / token).resolve(),
        cache=diagram_freshness.ContentFingerprintCache(),
    )

    assert first == second


def test_directory_fingerprints_ignore_finder_metadata_changes(tmp_path: Path) -> None:
    watched_dir = tmp_path / "runtime"
    nested_dir = watched_dir / "nested"
    nested_dir.mkdir(parents=True)
    module = watched_dir / "module.py"
    module.write_text("value = 1\n", encoding="utf-8")

    def fingerprint() -> str:
        return diagram_freshness.ContentFingerprintCache().path_fingerprint(watched_dir)

    original = fingerprint()
    for metadata in (watched_dir / ".DS_Store", nested_dir / ".DS_Store"):
        metadata.write_bytes(b"Finder metadata")
        assert fingerprint() == original
        metadata.write_bytes(b"Changed Finder metadata")
        assert fingerprint() == original
        metadata.unlink()
        assert fingerprint() == original

    module.write_text("value = 2\n", encoding="utf-8")
    assert fingerprint() != original


def test_directory_fingerprints_keep_similarly_named_source_entries(tmp_path: Path) -> None:
    for index, source in enumerate((".DS_Store.json", ".hidden.py", ".DS_Store/module.py")):
        watched_dir = tmp_path / str(index)
        watched_dir.mkdir()
        original = diagram_freshness.ContentFingerprintCache().path_fingerprint(watched_dir)
        entry = watched_dir / source
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text("value = 1\n", encoding="utf-8")

        assert diagram_freshness.ContentFingerprintCache().path_fingerprint(watched_dir) != original


def test_directory_fingerprints_keep_finder_named_symlinks(tmp_path: Path) -> None:
    watched_dir = tmp_path / "runtime"
    watched_dir.mkdir()
    target = tmp_path / "source.py"
    target.write_text("value = 1\n", encoding="utf-8")
    (watched_dir / ".DS_Store").symlink_to(target)
    original = diagram_freshness.ContentFingerprintCache().path_fingerprint(watched_dir)

    target.write_text("value = 2\n", encoding="utf-8")

    assert diagram_freshness.ContentFingerprintCache().path_fingerprint(watched_dir) != original
