"""Multi-language import graph analysis with single-pass file scanning.

Builds import graphs from Python AST, TypeScript/JS regex, Go regex, and Rust regex.
Collects TODOs and test-file flags during the same scan pass.
"""

from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from odylith.runtime.analysis_engine.types import (
    ComponentSuggestion,
    ImportArtifact,
    ImportEdge,
    ScanContext,
    humanize,
    progress,
    slugify,
)
from odylith.runtime.analysis_engine.repo_analysis import (
    NOISE_DIRS,
    infer_label,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"}
_TEST_PATTERNS = {"test_", "_test.", ".test.", ".spec.", "__tests__"}
_TODO_RE = re.compile(r"(?:#|//)\s*\b(TODO|FIXME|HACK|XXX)\b[:\s]+(.*)", re.IGNORECASE)
_SKIP_PATH_TOKENS = {"bundle", "dist", "generated", "vendor", ".min.", ".v1."}

# TypeScript/JS import patterns
_TS_IMPORT_RE = re.compile(
    r"""import\s+(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)"""
    r"""\s+from\s+['"](\.[^'"]+)['"]"""
    r"""|require\(\s*['"](\.[^'"]+)['"]\s*\)""",
)

# Go import patterns
_GO_IMPORT_RE = re.compile(r'"([^"]+)"')

# Rust import patterns
_RUST_USE_RE = re.compile(r"use\s+(?:crate|super|self)::([^\s;]+)")
_RUST_MOD_RE = re.compile(r"mod\s+(\w+)\s*;")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_import_graph(
    repo_root: Path,
    languages: list[str],
) -> tuple[list[ImportArtifact], list[ImportEdge], ScanContext]:
    """Single-pass scanner. Builds import graph + collects TODOs and test flags.

    Dispatches to per-language parsers based on file extension.
    Returns (artifacts, edges, scan_context).
    """
    progress("Building import graph...")

    ctx = ScanContext()
    artifacts: list[ImportArtifact] = []
    edges: list[ImportEdge] = []

    # Build module indexes per language
    py_index: dict[str, str] = {}  # module_name → rel_path
    py_roots = _auto_detect_python_roots(repo_root) if "Python" in languages else []
    go_module_prefix = _detect_go_module_prefix(repo_root) if "Go" in languages else ""

    # Single pass through all source files
    for entry in _iter_source_files(repo_root):
        rel_path = entry.relative_to(repo_root).as_posix()
        ctx.file_count += 1

        # Track language counts
        lang = _lang_for_ext(entry.suffix)
        ctx.language_counts[lang] = ctx.language_counts.get(lang, 0) + 1

        # Track test files
        name_lower = entry.name.lower()
        if any(p in name_lower for p in _TEST_PATTERNS):
            ctx.test_files.add(rel_path)

        # Read file once
        try:
            source = entry.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Extract TODOs (skip generated files)
        if not any(t in rel_path.lower() for t in _SKIP_PATH_TOKENS):
            for line in source.splitlines():
                match = _TODO_RE.search(line)
                if match:
                    text = (match.group(2) or "").strip()
                    if len(text) > 10:
                        ctx.todos.append((rel_path, text))

        # Parse imports by language
        if entry.suffix == ".py":
            artifact, file_edges = _parse_python_file(rel_path, source, py_index, py_roots)
            if artifact:
                artifacts.append(artifact)
                edges.extend(file_edges)
        elif entry.suffix in (".ts", ".tsx", ".js", ".jsx"):
            artifact, file_edges = _parse_typescript_file(rel_path, source, repo_root)
            if artifact:
                artifacts.append(artifact)
                edges.extend(file_edges)
        elif entry.suffix == ".go":
            artifact, file_edges = _parse_go_file(rel_path, source, go_module_prefix, repo_root)
            if artifact:
                artifacts.append(artifact)
                edges.extend(file_edges)
        elif entry.suffix == ".rs":
            artifact, file_edges = _parse_rust_file(rel_path, source, repo_root)
            if artifact:
                artifacts.append(artifact)
                edges.extend(file_edges)

    # Second pass for Python: resolve imports against the module index
    if py_index:
        resolved_edges = _resolve_python_imports(artifacts, py_index)
        edges = [e for e in edges if _lang_for_ext(Path(e.source_path).suffix) != "python"]
        edges.extend(resolved_edges)

    # Limit TODOs
    ctx.todos = ctx.todos[:10]

    return artifacts, edges, ctx


def discover_components_from_imports(
    repo_root: Path,
    artifacts: list[ImportArtifact],
    edges: list[ImportEdge],
) -> list[ComponentSuggestion]:
    """Group artifacts into components by directory clustering + import centrality."""
    if not artifacts:
        return []

    # Filter to source artifacts (exclude tests/scripts)
    test_prefixes = ("tests/", "test/", "scripts/", "spec/", "benchmark/")
    source_arts = [a for a in artifacts if not any(a.path.startswith(p) for p in test_prefixes)]
    if not source_arts:
        source_arts = artifacts

    # Find common source prefix
    module_prefix = _find_common_prefix(source_arts)

    # Group into component directories
    component_groups = _group_into_components(source_arts, module_prefix)

    # Merge small groups into their most-connected neighbor
    merged_groups = _merge_small_groups(component_groups, edges, min_size=5)

    # Count cross-component import edges on merged groups
    inbound, outbound, internal = _count_cross_component_edges(edges, merged_groups, module_prefix)

    # Build ranked suggestions
    return _build_component_suggestions(
        merged_groups, inbound, outbound, internal, module_prefix, repo_root,
    )


# ---------------------------------------------------------------------------
# File iteration
# ---------------------------------------------------------------------------

def _iter_source_files(repo_root: Path):
    """Yield source files, skipping noise directories."""
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
    return {
        ".py": "python", ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript",
        ".go": "go", ".rs": "rust",
    }.get(ext, "unknown")


# ---------------------------------------------------------------------------
# Python parsing
# ---------------------------------------------------------------------------

def _parse_python_file(
    rel_path: str,
    source: str,
    module_index: dict[str, str],
    py_roots: list[tuple[str, str]],
) -> tuple[ImportArtifact | None, list[ImportEdge]]:
    """Parse a Python file with AST. Populates module_index for later resolution."""
    # Build module name relative to the matching source root
    module_name = ""
    for root_dir, module_root in py_roots:
        if rel_path.startswith(root_dir + "/"):
            inner = rel_path[len(root_dir) + 1:]
            inner_mod = Path(inner).with_suffix("").as_posix().replace("/", ".")
            module_name = f"{module_root}.{inner_mod}" if module_root else inner_mod
            break
    if not module_name:
        # Fallback: full path as module name
        parts = Path(rel_path).with_suffix("").as_posix().replace("/", ".").split(".")
        module_name = ".".join(parts)
    if module_name.endswith(".__init__"):
        module_name = module_name[:-9]

    module_index[module_name] = rel_path

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError:
        return ImportArtifact(path=rel_path, module_name=module_name, language="python", imports=()), []

    # Extract raw import names (resolved in second pass)
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

    artifact = ImportArtifact(
        path=rel_path, module_name=module_name, language="python",
        imports=tuple(raw_imports),
    )
    return artifact, []  # edges resolved in second pass


def _resolve_python_imports(
    artifacts: list[ImportArtifact],
    module_index: dict[str, str],
) -> list[ImportEdge]:
    """Resolve raw Python import names to actual file paths."""
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
# TypeScript/JavaScript parsing
# ---------------------------------------------------------------------------

def _parse_typescript_file(
    rel_path: str,
    source: str,
    repo_root: Path,
) -> tuple[ImportArtifact | None, list[ImportEdge]]:
    """Regex-based TypeScript/JS import extraction."""
    imports: list[str] = []
    edges: list[ImportEdge] = []
    file_dir = (repo_root / rel_path).parent

    for match in _TS_IMPORT_RE.finditer(source):
        raw_path = match.group(1) or match.group(2)
        if not raw_path:
            continue
        # Resolve relative path
        resolved = _resolve_ts_path(file_dir, raw_path, repo_root)
        if resolved:
            imports.append(resolved)
            edges.append(ImportEdge(source_path=rel_path, target_path=resolved))

    module_name = Path(rel_path).with_suffix("").as_posix().replace("/", ".")
    return ImportArtifact(
        path=rel_path, module_name=module_name, language="typescript",
        imports=tuple(imports),
    ), edges


def _resolve_ts_path(file_dir: Path, raw_path: str, repo_root: Path) -> str:
    """Resolve a relative TS import path to a repo-relative path."""
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
# Go parsing
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


def _parse_go_file(
    rel_path: str,
    source: str,
    module_prefix: str,
    repo_root: Path,
) -> tuple[ImportArtifact | None, list[ImportEdge]]:
    """Regex-based Go import extraction."""
    imports: list[str] = []
    edges: list[ImportEdge] = []

    for match in _GO_IMPORT_RE.finditer(source):
        import_path = match.group(1)
        if not module_prefix or not import_path.startswith(module_prefix):
            continue
        # Resolve to repo-relative path
        local_path = import_path[len(module_prefix):].lstrip("/")
        if local_path and (repo_root / local_path).is_dir():
            imports.append(local_path)
            edges.append(ImportEdge(source_path=rel_path, target_path=local_path))

    module_name = Path(rel_path).with_suffix("").as_posix().replace("/", ".")
    return ImportArtifact(
        path=rel_path, module_name=module_name, language="go",
        imports=tuple(imports),
    ), edges


# ---------------------------------------------------------------------------
# Rust parsing
# ---------------------------------------------------------------------------

def _parse_rust_file(
    rel_path: str,
    source: str,
    repo_root: Path,
) -> tuple[ImportArtifact | None, list[ImportEdge]]:
    """Regex-based Rust import extraction."""
    imports: list[str] = []
    edges: list[ImportEdge] = []
    crate_root = _find_rust_crate_root(rel_path, repo_root)

    for match in _RUST_USE_RE.finditer(source):
        path = match.group(1).replace("::", "/").rstrip(";").split("{")[0].rstrip("/")
        if crate_root:
            full = f"{crate_root}/{path}"
        else:
            full = f"src/{path}"
        # Check if it maps to a real file
        for ext in (".rs", "/mod.rs", "/lib.rs"):
            candidate = repo_root / (full + ext)
            if candidate.is_file():
                target = candidate.relative_to(repo_root).as_posix()
                imports.append(target)
                edges.append(ImportEdge(source_path=rel_path, target_path=target))
                break

    module_name = Path(rel_path).with_suffix("").as_posix().replace("/", ".")
    return ImportArtifact(
        path=rel_path, module_name=module_name, language="rust",
        imports=tuple(imports),
    ), edges


def _find_rust_crate_root(rel_path: str, repo_root: Path) -> str:
    """Find the crate source root for a Rust file."""
    parts = Path(rel_path).parts
    for i in range(len(parts) - 1, -1, -1):
        candidate = Path(*parts[:i + 1]) if i > 0 else Path(".")
        if (repo_root / candidate / "Cargo.toml").is_file():
            src = candidate / "src"
            if (repo_root / src).is_dir():
                return src.as_posix()
    return "src"


# ---------------------------------------------------------------------------
# Component grouping from imports
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


def _find_common_prefix(artifacts: list[ImportArtifact]) -> str:
    """Find deepest directory prefix covering >50% of artifacts."""
    if not artifacts:
        return ""
    counts: Counter[str] = Counter()
    for a in artifacts:
        parts = a.path.split("/")
        for depth in range(1, min(len(parts), 5)):
            counts["/".join(parts[:depth])] += 1
    total = len(artifacts)
    best = ""
    for prefix, count in counts.most_common():
        if count >= total * 0.5 and len(prefix.split("/")) > len(best.split("/")):
            best = prefix
    return best


def _group_into_components(
    artifacts: list[ImportArtifact],
    module_prefix: str,
) -> dict[str, list[ImportArtifact]]:
    """Group artifacts into component directories, splitting large ones."""
    raw: dict[str, list[ImportArtifact]] = {}
    for art in artifacts:
        path = art.path
        if module_prefix and not path.startswith(module_prefix + "/"):
            continue
        remainder = path[len(module_prefix):].lstrip("/") if module_prefix else path
        parts = remainder.split("/")
        key = parts[0] if len(parts) >= 2 else "__root__"
        raw.setdefault(key, []).append(art)

    # Split oversized groups into sub-components
    result: dict[str, list[ImportArtifact]] = {}
    for name, arts in raw.items():
        if name.startswith("__"):
            result[name] = arts
            continue
        if len(arts) > 15:
            # Strategy 1: split by subdirectory (if the directory has real subdirs)
            subs: dict[str, list[ImportArtifact]] = {}
            for a in arts:
                remainder = a.path[len(module_prefix):].lstrip("/") if module_prefix else a.path
                parts = remainder.split("/")
                sub_key = f"{parts[0]}/{parts[1]}" if len(parts) >= 3 else parts[0]
                subs.setdefault(sub_key, []).append(a)
            dir_subs = {k: v for k, v in subs.items() if "/" in k and len(v) >= 3}

            if len(dir_subs) >= 2:
                result.update(dir_subs)
                for k, v in subs.items():
                    if "/" not in k:
                        result.setdefault(name, []).extend(v)
            else:
                # Strategy 2: split flat directories by file-name prefix
                prefix_groups = _group_by_filename_prefix(arts, module_prefix)
                if len(prefix_groups) >= 2:
                    for prefix, prefix_arts in prefix_groups.items():
                        result[f"{name}/{prefix}"] = prefix_arts
                else:
                    result[name] = arts
        else:
            result[name] = arts
    return result


def _group_by_filename_prefix(
    artifacts: list[ImportArtifact],
    module_prefix: str,
) -> dict[str, list[ImportArtifact]]:
    """Group files in a flat directory by their common name prefix.

    e.g., compass_dashboard_runtime.py, compass_standup_brief.py → "compass"
          claude_host_session_brief.py, claude_host_bash_guard.py → "claude_host"
    """
    filenames = [Path(art.path).stem for art in artifacts]
    prefix_map = _refine_prefixes_by_frequency(filenames)

    groups: dict[str, list[ImportArtifact]] = {}
    for art, fname in zip(artifacts, filenames):
        prefix = prefix_map.get(fname, fname.split("_")[0])
        groups.setdefault(prefix, []).append(art)

    # Merge tiny groups (< 2 files) into an "other" bucket
    merged: dict[str, list[ImportArtifact]] = {}
    other: list[ImportArtifact] = []
    for prefix, arts in groups.items():
        if len(arts) >= 2:
            merged[prefix] = arts
        else:
            other.extend(arts)
    if other:
        merged["core"] = other

    # Only split if we get meaningful groups
    if len(merged) >= 2 and all(len(v) >= 2 for v in merged.values() if v):
        return merged
    return {}


def _extract_meaningful_prefix(filename: str) -> str:
    """Extract a grouping prefix from a filename using frequency analysis.

    No domain-specific knowledge — works on any codebase by detecting the
    natural word boundary where filenames diverge.
    """
    parts = filename.split("_")
    if not parts:
        return filename
    # Use the first word as the default prefix
    return parts[0]


def _refine_prefixes_by_frequency(
    filenames: list[str],
) -> dict[str, str]:
    """Compute the best grouping prefix for each filename by analyzing
    which prefixes produce the most balanced groups.

    Strategy: try 1-word and 2-word prefixes. A 2-word prefix wins if
    it groups at least 3 files and the 1-word prefix would be too broad
    (groups > 60% of all files).
    """
    total = len(filenames)
    if total < 4:
        return {f: f.split("_")[0] if "_" in f else f for f in filenames}

    # Count 1-word and 2-word prefix frequencies
    one_word: Counter[str] = Counter()
    two_word: Counter[str] = Counter()
    for f in filenames:
        parts = f.split("_")
        if parts:
            one_word[parts[0]] += 1
        if len(parts) >= 2:
            two_word[f"{parts[0]}_{parts[1]}"] += 1

    # For each filename, pick the best prefix
    result: dict[str, str] = {}
    for f in filenames:
        parts = f.split("_")
        p1 = parts[0] if parts else f
        p2 = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else ""

        # Use 2-word prefix if it groups 3+ files AND the 1-word prefix is too broad
        if p2 and two_word.get(p2, 0) >= 3 and one_word.get(p1, 0) > total * 0.5:
            result[f] = p2
        else:
            result[f] = p1

    return result


def _count_cross_component_edges(
    edges: list[ImportEdge],
    groups: dict[str, list[ImportArtifact]],
    module_prefix: str,
) -> tuple[Counter[str], Counter[str], Counter[str]]:
    """Count inbound, outbound, and internal import edges per component."""
    # Build path-to-component lookup
    path_to_comp: dict[str, str] = {}
    for comp_name, arts in groups.items():
        for a in arts:
            path_to_comp[a.path] = comp_name

    inbound: Counter[str] = Counter()
    outbound: Counter[str] = Counter()
    internal: Counter[str] = Counter()

    for edge in edges:
        src_comp = path_to_comp.get(edge.source_path, "__external__")
        tgt_comp = path_to_comp.get(edge.target_path, "__external__")
        if src_comp == tgt_comp:
            internal[src_comp] += 1
        else:
            outbound[src_comp] += 1
            inbound[tgt_comp] += 1

    return inbound, outbound, internal


def _merge_small_groups(
    groups: dict[str, list[ImportArtifact]],
    edges: list[ImportEdge],
    min_size: int = 5,
) -> dict[str, list[ImportArtifact]]:
    """Merge groups under min_size into their most-connected neighbor by import edge count.

    This ensures we don't end up with 37 tiny fragments — small groups merge into
    the component they actually talk to most, not just their parent directory.
    """
    # Build edge count between groups
    path_to_group: dict[str, str] = {}
    for name, arts in groups.items():
        for a in arts:
            path_to_group[a.path] = name

    cross: Counter[tuple[str, str]] = Counter()
    for edge in edges:
        src_g = path_to_group.get(edge.source_path, "")
        tgt_g = path_to_group.get(edge.target_path, "")
        if src_g and tgt_g and src_g != tgt_g:
            cross[(src_g, tgt_g)] += 1
            cross[(tgt_g, src_g)] += 1

    merged = dict(groups)
    changed = True
    while changed:
        changed = False
        small = [name for name, arts in merged.items() if len(arts) < min_size and not name.startswith("__")]
        for name in small:
            # Find the neighbor with the most import edges
            neighbors: Counter[str] = Counter()
            for (a, b), count in cross.items():
                if a == name and b in merged and b != name:
                    neighbors[b] += count
            if not neighbors:
                # Merge into the first group that shares the parent directory
                parent = name.rsplit("/", 1)[0] if "/" in name else ""
                candidates = [k for k in merged if k != name and k.startswith(parent + "/")]
                if candidates:
                    target = candidates[0]
                else:
                    continue
            else:
                target = neighbors.most_common(1)[0][0]

            # Merge
            merged[target] = merged[target] + merged.pop(name)
            # Update path_to_group
            for a in merged[target]:
                path_to_group[a.path] = target
            changed = True
            break  # restart after each merge to recompute sizes

    return merged


def _build_component_suggestions(
    groups: dict[str, list[ImportArtifact]],
    inbound: Counter[str],
    outbound: Counter[str],
    internal: Counter[str],
    module_prefix: str,
    repo_root: Path,
) -> list[ComponentSuggestion]:
    """Build ranked component suggestions with software engineering metrics."""
    skip = {"__root__", "__external__"}
    seen_labels: set[str] = set()

    ranked = sorted(
        ((name, arts) for name, arts in groups.items() if name not in skip and not name.startswith("__")),
        key=lambda x: -(inbound[x[0]] + len(x[1])),
    )

    components: list[ComponentSuggestion] = []
    for comp_name, comp_arts in ranked[:12]:
        if not comp_name:
            continue

        # Build label from the full group path context
        parts = comp_name.split("/")
        deepest_dir = parts[-1] if parts else comp_name
        comp_id = slugify(deepest_dir)
        rel_path = f"{module_prefix}/{comp_name}" if module_prefix else comp_name
        file_names = [a.module_name.split(".")[-1] for a in comp_arts]

        # For compound paths like "surfaces/compass", combine parent context + child name
        if len(parts) >= 2:
            parent_label = infer_label(parts[0], [], [])
            child_label = infer_label(deepest_dir, [], file_names)
            if child_label == humanize(deepest_dir):
                # Child is generic — use parent + child humanized
                label = f"{humanize(deepest_dir)} {parent_label}" if humanize(deepest_dir) != "Core" else parent_label
            elif child_label != parent_label:
                label = child_label
            else:
                label = f"{humanize(deepest_dir)} {parent_label}"
        else:
            label = infer_label(deepest_dir, [], file_names)

        if label in seen_labels:
            label = f"{label} ({humanize(deepest_dir)})"
        seen_labels.add(label)

        n_modules = len(comp_arts)
        n_in = inbound[comp_name]
        n_out = outbound[comp_name]
        n_int = internal[comp_name]

        # Compute software engineering metrics
        fan_in = n_in
        fan_out = n_out
        instability = fan_out / max(fan_in + fan_out, 1)
        total_edges = n_in + n_out + n_int
        cohesion = n_int / max(total_edges, 1)

        desc = _build_import_description(n_modules, n_in, n_out, n_int, instability, cohesion)

        components.append(ComponentSuggestion(
            component_id=comp_id, label=label, path=rel_path,
            description=desc,
            n_modules=n_modules, n_inbound=n_in, n_outbound=n_out,
        ))

    return components


def _build_import_description(
    n_modules: int, n_in: int, n_out: int, n_int: int,
    instability: float, cohesion: float,
) -> str:
    """Build a description using real software engineering metrics."""
    parts: list[str] = [f"{n_modules} modules"]

    # Centrality insight
    if n_in > 20:
        parts.append(f"imported by {n_in} others — foundational dependency")
    elif n_in > 10:
        parts.append(f"imported by {n_in} others — core boundary")
    elif n_in > 0:
        parts.append(f"imported by {n_in} others")

    # Architecture role from instability metric
    if instability < 0.2 and n_in > 5:
        parts.append("stable core (low instability, high fan-in)")
    elif instability > 0.8 and n_out > 3:
        parts.append("volatile edge (high fan-out, depends on many others)")
    elif 0.3 < instability < 0.7 and n_in > 3 and n_out > 3:
        parts.append("integration layer (balanced fan-in/fan-out)")

    # Cohesion insight
    if cohesion > 0.7 and n_int > 5:
        parts.append("highly cohesive")
    elif cohesion < 0.3 and n_in + n_out > 5:
        parts.append("loosely coupled to everything")

    return ". ".join(parts)
