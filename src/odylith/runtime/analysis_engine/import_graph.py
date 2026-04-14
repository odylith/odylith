"""Multi-language import graph analysis with single-pass file scanning.

Builds import graphs from Python AST, TypeScript/JS regex, Go regex, and Rust regex.
Collects TODOs and test-file flags during the same scan pass.
No domain-specific knowledge — works on any codebase.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path
from typing import Any

from odylith.runtime.analysis_engine.types import (
    ImportArtifact,
    ImportEdge,
    ScanContext,
    progress,
)
from odylith.runtime.analysis_engine.repo_analysis import NOISE_DIRS


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"}
_TEST_PATTERNS = {"test_", "_test.", ".test.", ".spec.", "__tests__"}
_TODO_RE = re.compile(r"(?:#|//)\s*\b(TODO|FIXME|HACK|XXX)\b[:\s]+(.*)", re.IGNORECASE)
_SKIP_PATH_TOKENS = {"bundle", "dist", "generated", "vendor", ".min."}

_TS_IMPORT_RE = re.compile(
    r"""import\s+(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)"""
    r"""\s+from\s+['"](\.[^'"]+)['"]"""
    r"""|require\(\s*['"](\.[^'"]+)['"]\s*\)""",
)
_GO_IMPORT_RE = re.compile(r'"([^"]+)"')
_RUST_USE_RE = re.compile(r"use\s+(?:crate|super|self)::([^\s;]+)")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_import_graph(
    repo_root: Path,
    languages: list[str],
) -> tuple[list[ImportArtifact], list[ImportEdge], ScanContext]:
    """Single-pass scanner. Builds import graph + collects TODOs and test flags."""
    progress("Building import graph...")

    ctx = ScanContext()
    artifacts: list[ImportArtifact] = []
    edges: list[ImportEdge] = []

    py_index: dict[str, str] = {}
    py_roots = _auto_detect_python_roots(repo_root) if "Python" in languages else []
    go_module_prefix = _detect_go_module_prefix(repo_root) if "Go" in languages else ""

    for entry in _iter_source_files(repo_root):
        rel_path = entry.relative_to(repo_root).as_posix()
        ctx.file_count += 1

        lang = _lang_for_ext(entry.suffix)
        ctx.language_counts[lang] = ctx.language_counts.get(lang, 0) + 1

        if any(p in entry.name.lower() for p in _TEST_PATTERNS):
            ctx.test_files.add(rel_path)

        try:
            source = entry.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # TODOs (skip generated files)
        if not any(t in rel_path.lower() for t in _SKIP_PATH_TOKENS):
            for line in source.splitlines():
                match = _TODO_RE.search(line)
                if match:
                    text = (match.group(2) or "").strip()
                    if len(text) > 10:
                        ctx.todos.append((rel_path, text))

        # Parse imports by language
        if entry.suffix == ".py":
            art, _ = _parse_python_file(rel_path, source, py_index, py_roots)
            if art:
                artifacts.append(art)
        elif entry.suffix in (".ts", ".tsx", ".js", ".jsx"):
            art, file_edges = _parse_typescript_file(rel_path, source, repo_root)
            if art:
                artifacts.append(art)
                edges.extend(file_edges)
        elif entry.suffix == ".go":
            art, file_edges = _parse_go_file(rel_path, source, go_module_prefix, repo_root)
            if art:
                artifacts.append(art)
                edges.extend(file_edges)
        elif entry.suffix == ".rs":
            art, file_edges = _parse_rust_file(rel_path, source, repo_root)
            if art:
                artifacts.append(art)
                edges.extend(file_edges)

    # Second pass: resolve Python imports against module index
    if py_index:
        resolved = _resolve_python_imports(artifacts, py_index)
        edges = [e for e in edges if _lang_for_ext(Path(e.source_path).suffix) != "python"]
        edges.extend(resolved)

    ctx.todos = ctx.todos[:10]
    return artifacts, edges, ctx


# ---------------------------------------------------------------------------
# File iteration
# ---------------------------------------------------------------------------

def _iter_source_files(repo_root: Path):
    try:
        for entry in repo_root.rglob("*"):
            if not entry.is_file() or entry.suffix not in _SOURCE_EXTS:
                continue
            if any(p in NOISE_DIRS or p.startswith(".") for p in entry.relative_to(repo_root).parts):
                continue
            yield entry
    except OSError:
        pass


def _lang_for_ext(ext: str) -> str:
    return {".py": "python", ".ts": "typescript", ".tsx": "typescript",
            ".js": "javascript", ".jsx": "javascript",
            ".go": "go", ".rs": "rust"}.get(ext, "unknown")


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

def _auto_detect_python_roots(repo_root: Path) -> list[tuple[str, str]]:
    """Auto-detect Python source roots. Returns (rel_root, module_root) pairs."""
    roots: list[tuple[str, str]] = []
    src_dir = repo_root / "src"
    if src_dir.is_dir():
        for child in sorted(src_dir.iterdir()):
            if child.is_dir() and not child.name.startswith(".") and not child.name.startswith("__"):
                if (child / "__init__.py").is_file() or any(child.rglob("*.py")):
                    roots.append((f"src/{child.name}", child.name))
    for name in ("app", "lib", "server", "backend", "api", "services"):
        candidate = repo_root / name
        if candidate.is_dir() and any(candidate.rglob("*.py")):
            roots.append((name, name))
    if not roots:
        for child in sorted(repo_root.iterdir()):
            if child.is_dir() and (child / "__init__.py").is_file() and child.name not in NOISE_DIRS and not child.name.startswith("."):
                roots.append((child.name, child.name))
    for name in ("tests", "test", "scripts"):
        candidate = repo_root / name
        if candidate.is_dir() and any(candidate.rglob("*.py")):
            roots.append((name, name))
    return roots


def _parse_python_file(
    rel_path: str, source: str,
    module_index: dict[str, str],
    py_roots: list[tuple[str, str]],
) -> tuple[ImportArtifact | None, list[ImportEdge]]:
    """Parse Python file with AST. Populates module_index."""
    module_name = ""
    for root_dir, module_root in py_roots:
        if rel_path.startswith(root_dir + "/"):
            inner = rel_path[len(root_dir) + 1:]
            inner_mod = Path(inner).with_suffix("").as_posix().replace("/", ".")
            module_name = f"{module_root}.{inner_mod}" if module_root else inner_mod
            break
    if not module_name:
        module_name = ".".join(Path(rel_path).with_suffix("").as_posix().replace("/", ".").split("."))
    if module_name.endswith(".__init__"):
        module_name = module_name[:-9]

    module_index[module_name] = rel_path

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError:
        return ImportArtifact(path=rel_path, module_name=module_name, language="python", imports=()), []

    raw_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                raw_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                raw_imports.append(node.module)
            elif node.module and node.level > 0:
                pkg_parts = module_name.split(".")
                trim = max(0, node.level - 1)
                base = ".".join(pkg_parts[:max(0, len(pkg_parts) - trim)])
                raw_imports.append(f"{base}.{node.module}" if base else node.module)

    return ImportArtifact(path=rel_path, module_name=module_name, language="python", imports=tuple(raw_imports)), []


def _resolve_python_imports(artifacts: list[ImportArtifact], module_index: dict[str, str]) -> list[ImportEdge]:
    edges: list[ImportEdge] = []
    for art in artifacts:
        if art.language != "python":
            continue
        for imp in art.imports:
            target = module_index.get(imp)
            if not target:
                parent = imp.rsplit(".", 1)[0] if "." in imp else ""
                target = module_index.get(parent)
            if target:
                edges.append(ImportEdge(source_path=art.path, target_path=target))
    return edges


# ---------------------------------------------------------------------------
# TypeScript/JavaScript
# ---------------------------------------------------------------------------

def _parse_typescript_file(rel_path: str, source: str, repo_root: Path) -> tuple[ImportArtifact | None, list[ImportEdge]]:
    imports, edges = [], []
    file_dir = (repo_root / rel_path).parent
    for match in _TS_IMPORT_RE.finditer(source):
        raw_path = match.group(1) or match.group(2)
        if not raw_path:
            continue
        resolved = _resolve_ts_path(file_dir, raw_path, repo_root)
        if resolved:
            imports.append(resolved)
            edges.append(ImportEdge(source_path=rel_path, target_path=resolved))
    mod = Path(rel_path).with_suffix("").as_posix().replace("/", ".")
    return ImportArtifact(path=rel_path, module_name=mod, language="typescript", imports=tuple(imports)), edges


def _resolve_ts_path(file_dir: Path, raw_path: str, repo_root: Path) -> str:
    candidate = (file_dir / raw_path).resolve()
    for ext in ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"):
        full = candidate.parent / (candidate.name + ext) if ext and not ext.startswith("/") else Path(str(candidate) + ext)
        if full.is_file():
            try:
                return full.relative_to(repo_root).as_posix()
            except ValueError:
                pass
    return ""


# ---------------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------------

def _detect_go_module_prefix(repo_root: Path) -> str:
    go_mod = repo_root / "go.mod"
    if not go_mod.is_file():
        return ""
    try:
        for line in go_mod.read_text(encoding="utf-8").splitlines():
            if line.startswith("module "):
                return line.split()[-1]
    except OSError:
        pass
    return ""


def _parse_go_file(rel_path: str, source: str, module_prefix: str, repo_root: Path) -> tuple[ImportArtifact | None, list[ImportEdge]]:
    imports, edges = [], []
    for match in _GO_IMPORT_RE.finditer(source):
        import_path = match.group(1)
        if not module_prefix or not import_path.startswith(module_prefix):
            continue
        local_path = import_path[len(module_prefix):].lstrip("/")
        if local_path and (repo_root / local_path).is_dir():
            imports.append(local_path)
            edges.append(ImportEdge(source_path=rel_path, target_path=local_path))
    mod = Path(rel_path).with_suffix("").as_posix().replace("/", ".")
    return ImportArtifact(path=rel_path, module_name=mod, language="go", imports=tuple(imports)), edges


# ---------------------------------------------------------------------------
# Rust
# ---------------------------------------------------------------------------

def _parse_rust_file(rel_path: str, source: str, repo_root: Path) -> tuple[ImportArtifact | None, list[ImportEdge]]:
    imports, edges = [], []
    crate_root = _find_rust_crate_root(rel_path, repo_root)
    for match in _RUST_USE_RE.finditer(source):
        path = match.group(1).replace("::", "/").rstrip(";").split("{")[0].rstrip("/")
        full = f"{crate_root}/{path}" if crate_root else f"src/{path}"
        for ext in (".rs", "/mod.rs", "/lib.rs"):
            candidate = repo_root / (full + ext)
            if candidate.is_file():
                target = candidate.relative_to(repo_root).as_posix()
                imports.append(target)
                edges.append(ImportEdge(source_path=rel_path, target_path=target))
                break
    mod = Path(rel_path).with_suffix("").as_posix().replace("/", ".")
    return ImportArtifact(path=rel_path, module_name=mod, language="rust", imports=tuple(imports)), edges


def _find_rust_crate_root(rel_path: str, repo_root: Path) -> str:
    parts = Path(rel_path).parts
    for i in range(len(parts) - 1, -1, -1):
        candidate = Path(*parts[:i + 1]) if i > 0 else Path(".")
        if (repo_root / candidate / "Cargo.toml").is_file():
            src = candidate / "src"
            if (repo_root / src).is_dir():
                return src.as_posix()
    return "src"
