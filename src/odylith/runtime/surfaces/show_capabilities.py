"""Backend for `odylith show` — analyze a repo and suggest concrete governance records.

Reads the repo itself — manifests, directory structure, file contents, TODOs —
and produces categorized governance suggestions with runnable CLI commands.
Advisory only unless --apply is passed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkstreamSuggestion:
    title: str
    description: str


@dataclass(frozen=True)
class ComponentSuggestion:
    component_id: str
    label: str
    path: str
    description: str


@dataclass(frozen=True)
class DiagramSuggestion:
    slug: str
    title: str
    description: str


@dataclass(frozen=True)
class IssueSuggestion:
    title: str
    detail: str


@dataclass
class RepoIdentity:
    name: str = ""
    description: str = ""
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_manager: str = ""
    monorepo: bool = False
    workspace_dirs: list[str] = field(default_factory=list)


@dataclass
class ShowResult:
    identity: RepoIdentity = field(default_factory=RepoIdentity)
    workstreams: list[WorkstreamSuggestion] = field(default_factory=list)
    components: list[ComponentSuggestion] = field(default_factory=list)
    diagrams: list[DiagramSuggestion] = field(default_factory=list)
    issues: list[IssueSuggestion] = field(default_factory=list)
    already_governed: dict[str, bool] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")
_NOISE_DIRS = frozenset({
    ".git", ".hg", ".svn", ".odylith", "node_modules",
    "__pycache__", ".venv", "venv", "env", ".env",
    "build", "dist", "target", "out", "output",
    "coverage", ".coverage", ".idea", ".vscode",
    ".next", ".nuxt", ".cache", ".turbo",
    "vendor", "deps", ".deps",
})
# Only skip odylith/ at the repo root (governance dir), not nested (source code)
_REPO_ROOT_SKIP = frozenset({"odylith"})
_TODO_RE = re.compile(r"#\s*\b(TODO|FIXME|HACK|XXX)\b[:\s]+(.*)|//\s*\b(TODO|FIXME|HACK|XXX)\b[:\s]+(.*)", re.IGNORECASE)


def _slugify(value: str) -> str:
    return _SLUGIFY_RE.sub("-", str(value or "").strip().lower()).strip("-") or "component"


def _humanize(value: str) -> str:
    token = str(value or "").strip().replace("-", " ").replace("_", " ")
    return " ".join(w.capitalize() for w in token.split()) if token else ""


def _progress(msg: str) -> None:
    print(f"  {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Phase 1: Project Identity
# ---------------------------------------------------------------------------

def _read_project_identity(repo_root: Path) -> RepoIdentity:
    """Read manifests, README, and structure to understand what this repo is."""
    identity = RepoIdentity()
    identity.name = repo_root.name

    # Python
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        identity.languages.append("Python")
        _parse_pyproject(pyproject, identity)

    setup_py = repo_root / "setup.py"
    if setup_py.is_file() and "Python" not in identity.languages:
        identity.languages.append("Python")

    # Node/TypeScript
    pkg_json = repo_root / "package.json"
    if pkg_json.is_file():
        _parse_package_json(pkg_json, identity)

    # Go
    go_mod = repo_root / "go.mod"
    if go_mod.is_file():
        identity.languages.append("Go")
        _parse_go_mod(go_mod, identity)

    # Rust
    cargo = repo_root / "Cargo.toml"
    if cargo.is_file():
        identity.languages.append("Rust")

    # Java/Kotlin
    if (repo_root / "pom.xml").is_file() or (repo_root / "build.gradle").is_file():
        identity.languages.append("Java/Kotlin")

    # Ruby
    if (repo_root / "Gemfile").is_file():
        identity.languages.append("Ruby")
        if (repo_root / "config" / "routes.rb").is_file():
            identity.frameworks.append("Rails")

    # README
    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme = repo_root / readme_name
        if readme.is_file():
            try:
                text = readme.read_text(encoding="utf-8", errors="replace")[:2000]
                # Extract first meaningful paragraph
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and not stripped.startswith("!") and len(stripped) > 20:
                        identity.description = stripped[:200]
                        break
            except OSError:
                pass
            break

    return identity


def _parse_pyproject(path: Path, identity: RepoIdentity) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    # Detect frameworks from dependencies
    lower = text.lower()
    if "django" in lower:
        identity.frameworks.append("Django")
    if "fastapi" in lower:
        identity.frameworks.append("FastAPI")
    if "flask" in lower:
        identity.frameworks.append("Flask")
    if "streamlit" in lower:
        identity.frameworks.append("Streamlit")
    # Extract project name
    for line in text.splitlines():
        if line.strip().startswith("name") and "=" in line:
            name = line.split("=", 1)[1].strip().strip('"').strip("'")
            if name:
                identity.name = name
            break


def _parse_package_json(path: Path, identity: RepoIdentity) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(data, dict):
        return

    if "TypeScript" not in identity.languages and "JavaScript" not in identity.languages:
        if (path.parent / "tsconfig.json").is_file():
            identity.languages.append("TypeScript")
        else:
            identity.languages.append("JavaScript")

    name = data.get("name", "")
    if name:
        identity.name = str(name)

    desc = data.get("description", "")
    if desc and not identity.description:
        identity.description = str(desc)[:200]

    # Detect frameworks
    all_deps = {**dict(data.get("dependencies", {})), **dict(data.get("devDependencies", {}))}
    if "next" in all_deps:
        identity.frameworks.append("Next.js")
    if "react" in all_deps and "Next.js" not in identity.frameworks:
        identity.frameworks.append("React")
    if "vue" in all_deps:
        identity.frameworks.append("Vue")
    if "svelte" in all_deps or "@sveltejs/kit" in all_deps:
        identity.frameworks.append("SvelteKit" if "@sveltejs/kit" in all_deps else "Svelte")
    if "express" in all_deps:
        identity.frameworks.append("Express")
    if "nestjs" in all_deps or "@nestjs/core" in all_deps:
        identity.frameworks.append("NestJS")
    if "hono" in all_deps:
        identity.frameworks.append("Hono")

    # Detect monorepo
    workspaces = data.get("workspaces", [])
    if workspaces:
        identity.monorepo = True
        if isinstance(workspaces, list):
            identity.workspace_dirs = [str(w) for w in workspaces[:10]]
        elif isinstance(workspaces, dict):
            identity.workspace_dirs = [str(w) for w in workspaces.get("packages", [])[:10]]

    if identity.package_manager == "":
        identity.package_manager = "npm"


def _parse_go_mod(path: Path, identity: RepoIdentity) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines():
        if line.startswith("module "):
            identity.name = line.split()[-1].split("/")[-1]
            break
    lower = text.lower()
    if "gin-gonic" in lower:
        identity.frameworks.append("Gin")
    if "gorilla/mux" in lower:
        identity.frameworks.append("Gorilla")
    if "fiber" in lower:
        identity.frameworks.append("Fiber")


# ---------------------------------------------------------------------------
# Phase 2: Component Discovery
# ---------------------------------------------------------------------------

def _discover_components(repo_root: Path, identity: RepoIdentity) -> list[ComponentSuggestion]:
    """Find real architectural boundaries using the best available analysis."""
    _progress("Reading source tree...")

    # For monorepos, use workspace directories
    if identity.monorepo and identity.workspace_dirs:
        return _discover_monorepo_components(repo_root, identity)

    # Try import-graph-based detection for Python repos
    if "Python" in identity.languages:
        try:
            components = _discover_components_from_import_graph(repo_root)
            if components:
                return components
        except Exception:
            pass  # fall back to directory walking

    # Fallback: directory structure analysis
    module_root = _find_module_level(repo_root)
    children = _source_children(module_root)

    if not children:
        return []

    components: list[ComponentSuggestion] = []
    for child in children[:8]:
        comp = _analyze_module(child, repo_root)
        if comp:
            components.append(comp)

    return components[:6]


def _discover_components_from_import_graph(repo_root: Path) -> list[ComponentSuggestion]:
    """Use the Odylith code graph builder to detect components from Python imports.

    This gives much richer results than directory walking because it understands
    which modules actually depend on each other, finds central vs leaf modules,
    and detects coupling between boundaries.
    """
    _progress("Building import graph from Python AST...")

    artifacts, edges = _build_import_graph(repo_root)

    if not artifacts:
        return []

    # Filter out test and script artifacts — components come from source code
    test_prefixes = ("tests/", "test/", "scripts/", "spec/", "benchmark/")
    source_artifacts = [a for a in artifacts if not any(a["path"].startswith(p) for p in test_prefixes)]
    if not source_artifacts:
        source_artifacts = artifacts  # fallback if everything is tests

    # Build artifact index and import graph
    artifact_by_path: dict[str, dict[str, Any]] = {a["path"]: a for a in artifacts}
    import_edges = [e for e in edges if e.get("relation") == "imports"]

    # Find the module level from source artifacts only
    module_prefix = _find_common_source_prefix(source_artifacts)

    # Group artifacts into component directories
    # For large modules (>40 files), go one level deeper to find real boundaries
    raw_dirs: dict[str, list[dict[str, Any]]] = {}
    for artifact in source_artifacts:
        path = artifact["path"]
        if not path.startswith(module_prefix + "/") and module_prefix:
            continue
        remainder = path[len(module_prefix):].lstrip("/") if module_prefix else path
        parts = remainder.split("/")
        if len(parts) >= 2:
            raw_dirs.setdefault(parts[0], []).append(artifact)
        else:
            raw_dirs.setdefault("__root__", []).append(artifact)

    # Split oversized directories into sub-components
    component_dirs: dict[str, list[dict[str, Any]]] = {}
    for name, arts in raw_dirs.items():
        if name.startswith("__"):
            component_dirs[name] = arts
            continue
        if len(arts) > 40:
            # Go one level deeper
            sub_dirs: dict[str, list[dict[str, Any]]] = {}
            for a in arts:
                remainder = a["path"][len(module_prefix):].lstrip("/") if module_prefix else a["path"]
                parts = remainder.split("/")
                if len(parts) >= 3:
                    sub_key = f"{parts[0]}/{parts[1]}"
                else:
                    sub_key = parts[0]
                sub_dirs.setdefault(sub_key, []).append(a)
            # Only split if we get multiple meaningful sub-dirs
            meaningful_subs = {k: v for k, v in sub_dirs.items() if "/" in k and len(v) >= 3}
            if len(meaningful_subs) >= 2:
                component_dirs.update(meaningful_subs)
                # Include any remaining top-level files as root module
                for k, v in sub_dirs.items():
                    if "/" not in k:
                        component_dirs.setdefault(name, []).extend(v)
            else:
                component_dirs[name] = arts
        else:
            component_dirs[name] = arts

    # Count cross-component import edges
    inbound: Counter[str] = Counter()
    outbound: Counter[str] = Counter()
    internal: Counter[str] = Counter()

    def _comp_for_path(path: str) -> str:
        if module_prefix and not path.startswith(module_prefix + "/"):
            return "__external__"
        remainder = path[len(module_prefix):].lstrip("/") if module_prefix else path
        parts = remainder.split("/")
        if len(parts) >= 3:
            two_level = f"{parts[0]}/{parts[1]}"
            if two_level in component_dirs:
                return two_level
        return parts[0] if len(parts) >= 2 else "__root__"

    for edge in import_edges:
        src_comp = _comp_for_path(edge["source_path"])
        tgt_comp = _comp_for_path(edge["target_path"])
        if src_comp == tgt_comp:
            internal[src_comp] += 1
        else:
            outbound[src_comp] += 1
            inbound[tgt_comp] += 1

    # Build component suggestions ranked by importance (inbound imports = centrality)
    components: list[ComponentSuggestion] = []
    skip = {"__root__", "__external__"}
    seen_labels: set[str] = set()

    ranked = sorted(
        ((name, arts) for name, arts in component_dirs.items() if name not in skip),
        key=lambda x: -(inbound[x[0]] + len(x[1])),
    )

    for comp_name, comp_artifacts in ranked[:8]:
        if not comp_name or comp_name.startswith("__"):
            continue

        comp_id = _slugify(comp_name)
        rel_path = f"{module_prefix}/{comp_name}" if module_prefix else comp_name
        full_path = repo_root / rel_path

        # Infer label: directory name is the primary signal, file contents secondary
        dir_parts = comp_name.split("/")
        deepest_dir = dir_parts[-1]
        file_names = [a.get("module_name", "").split(".")[-1] for a in comp_artifacts]

        # First try to infer from the directory name itself
        label = _infer_label(deepest_dir, [], [])
        # If directory name alone gives a generic result, enrich with file contents
        if label == _humanize(deepest_dir):
            label_from_files = _infer_label(deepest_dir, [], file_names)
            if label_from_files != _humanize(deepest_dir):
                label = label_from_files

        # Build description from import analysis
        n_modules = len(comp_artifacts)
        n_inbound = inbound[comp_name]
        n_outbound = outbound[comp_name]
        n_internal = internal[comp_name]

        role_parts: list[str] = []
        role_parts.append(f"{n_modules} modules")
        if n_inbound > 5:
            role_parts.append(f"imported by {n_inbound} other modules — this is a core dependency")
        elif n_inbound > 0:
            role_parts.append(f"imported by {n_inbound} other modules")
        if n_outbound > n_inbound and n_outbound > 3:
            role_parts.append("orchestrates across other components")
        if n_internal > 5:
            role_parts.append("tightly cohesive internally")

        why = _describe_why_from_imports(n_inbound, n_outbound, n_internal, n_modules)
        description = ", ".join(role_parts) + f". {why}"

        # Deduplicate by label — if same label already used, append the directory name
        if label in seen_labels:
            label = f"{label} ({_humanize(deepest_dir)})"
        seen_labels.add(label)

        components.append(ComponentSuggestion(
            component_id=comp_id,
            label=label,
            path=rel_path,
            description=description,
        ))

    return components[:6]


def _build_import_graph(repo_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build an import graph by scanning Python files with AST.

    Auto-discovers source roots (unlike the context engine which uses hardcoded roots).
    Returns (artifacts, edges) in the same format as the context engine code graph.
    """
    import ast

    # Find all Python source directories
    source_roots = _auto_detect_python_roots(repo_root)
    if not source_roots:
        return [], []

    # Collect all Python files and build module index
    module_index: dict[str, str] = {}  # module_name → rel_path
    for root_dir, module_root in source_roots:
        full_root = repo_root / root_dir
        if not full_root.is_dir():
            continue
        for py_file in sorted(full_root.rglob("*.py")):
            rel_path = py_file.relative_to(repo_root).as_posix()
            # Skip noise
            if any(noise in rel_path for noise in ("__pycache__", ".venv", "node_modules")):
                continue
            # Build module name
            module_path = py_file.relative_to(repo_root / root_dir).with_suffix("").as_posix()
            module_name = f"{module_root}.{module_path.replace('/', '.')}" if module_root else module_path.replace("/", ".")
            module_name = module_name.rstrip(".")
            if module_name.endswith(".__init__"):
                module_name = module_name[:-9]
            module_index[module_name] = rel_path

    # Parse each file for imports
    artifacts: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for module_name, rel_path in sorted(module_index.items()):
        full_path = repo_root / rel_path
        parts = rel_path.split("/")
        layer = parts[0] if parts else ""

        # Extract the meaningful subdirectory for component grouping
        artifact = {
            "path": rel_path,
            "module_name": module_name,
            "layer": layer,
            "imports": [],
        }

        try:
            source = full_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=rel_path)
        except (SyntaxError, OSError):
            artifacts.append(artifact)
            continue

        # Extract imports
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    imported_modules.add(node.module)
                elif node.module and node.level > 0:
                    # Relative import — resolve against current package
                    pkg_parts = module_name.split(".")
                    trim = max(0, node.level - 1)
                    base = ".".join(pkg_parts[:max(0, len(pkg_parts) - trim)])
                    resolved = f"{base}.{node.module}" if base else node.module
                    imported_modules.add(resolved)

        # Resolve imports to known modules and create edges
        for imp in sorted(imported_modules):
            # Try exact match and prefix matches
            target_path = module_index.get(imp)
            if not target_path:
                # Try parent module
                parent = imp.rsplit(".", 1)[0] if "." in imp else ""
                target_path = module_index.get(parent)
            if target_path:
                artifact["imports"].append(target_path)
                edges.append({
                    "source_path": rel_path,
                    "relation": "imports",
                    "target_path": target_path,
                })

        artifacts.append(artifact)

    return artifacts, edges


def _auto_detect_python_roots(repo_root: Path) -> list[tuple[str, str]]:
    """Auto-detect Python source roots in the repo.

    Returns list of (rel_root, module_root) tuples.
    For src/odylith/ → ("src/odylith", "odylith")
    For app/ → ("app", "app")
    """
    roots: list[tuple[str, str]] = []

    # Check src/ layout (PEP 517 style)
    src_dir = repo_root / "src"
    if src_dir.is_dir():
        for child in sorted(src_dir.iterdir()):
            if child.is_dir() and not child.name.startswith(".") and not child.name.startswith("__"):
                if (child / "__init__.py").is_file() or any(child.rglob("*.py")):
                    roots.append((f"src/{child.name}", child.name))

    # Check common top-level source directories
    for name in ("app", "lib", "server", "backend", "api", "services"):
        candidate = repo_root / name
        if candidate.is_dir() and any(candidate.rglob("*.py")):
            roots.append((name, name))

    # Check for top-level package (pyproject.toml style)
    if not roots:
        for child in sorted(repo_root.iterdir()):
            if child.is_dir() and (child / "__init__.py").is_file():
                if child.name not in _NOISE_DIRS and not child.name.startswith("."):
                    roots.append((child.name, child.name))

    # Always include tests and scripts if they exist
    for name in ("tests", "test", "scripts"):
        candidate = repo_root / name
        if candidate.is_dir() and any(candidate.rglob("*.py")):
            roots.append((name, name))

    return roots


def _find_common_source_prefix(artifacts: list[dict[str, Any]]) -> str:
    """Find the deepest directory prefix shared by most artifacts."""
    if not artifacts:
        return ""

    # Count how many artifacts share each prefix
    prefix_counts: Counter[str] = Counter()
    for artifact in artifacts:
        path = artifact["path"]
        parts = path.split("/")
        for depth in range(1, min(len(parts), 5)):
            prefix = "/".join(parts[:depth])
            prefix_counts[prefix] += 1

    total = len(artifacts)
    # Find the deepest prefix that covers >60% of artifacts
    best = ""
    for prefix, count in prefix_counts.most_common():
        if count >= total * 0.6 and len(prefix.split("/")) > len(best.split("/")):
            best = prefix

    # Don't return single generic names
    if best and best.split("/")[-1].lower() in _WRAPPER_NAMES:
        # Keep it — the wrapper IS part of the prefix path
        pass

    return best


def _describe_why_from_imports(n_inbound: int, n_outbound: int, n_internal: int, n_modules: int) -> str:
    """Explain governance value based on import analysis."""
    if n_inbound > 10:
        return "Heavy dependency — changes here cascade across the codebase. Tracking it prevents silent breakage"
    if n_inbound > 5:
        return "Central boundary — many modules depend on it. Registering it makes ownership visible before changes land"
    if n_outbound > n_inbound and n_outbound > 5:
        return "Orchestration layer — coordinates across other components. Tracking it keeps the coordination contract explicit"
    if n_internal > 5 and n_inbound <= 2:
        return "Self-contained module — low coupling, high cohesion. Naming it now makes it a clean delegation target for agent sessions"
    if n_modules >= 5:
        return "Meaningful boundary — large enough to need explicit ownership and delivery accountability"
    return "Tracking it gives agent sessions a named boundary to reason about"


def _discover_monorepo_components(repo_root: Path, identity: RepoIdentity) -> list[ComponentSuggestion]:
    """Discover components from monorepo workspace patterns."""
    import glob as glob_module
    components: list[ComponentSuggestion] = []

    for pattern in identity.workspace_dirs:
        # Expand glob patterns like "packages/*"
        matches = sorted(glob_module.glob(str(repo_root / pattern)))
        for match_path in matches[:6]:
            match = Path(match_path)
            if not match.is_dir():
                continue
            comp = _analyze_module(match, repo_root)
            if comp:
                components.append(comp)

    return components[:8]


_SOURCE_ROOTS = ("src", "lib", "packages", "apps", "services", "backend", "frontend", "server", "api", "cmd")
_WRAPPER_NAMES = frozenset({
    "src", "lib", "libs", "pkg", "packages", "apps", "app", "cmd",
    "internal", "modules", "main",
})


def _find_module_level(repo_root: Path) -> Path:
    """Walk from a source root through wrapper dirs to the real module level."""
    # Find source root
    for name in _SOURCE_ROOTS:
        candidate = repo_root / name
        if candidate.is_dir() and _has_source_files(candidate):
            source_root = candidate
            break
    else:
        return repo_root

    # Walk down through single-child wrappers
    current = source_root
    for _depth in range(5):
        children = _source_children(current)
        if len(children) >= 2:
            return current
        if len(children) == 1:
            current = children[0]
            continue
        break
    return current


def _source_children(directory: Path, *, is_repo_root: bool = False) -> list[Path]:
    """List child directories that contain source code."""
    children: list[Path] = []
    try:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            name = entry.name
            if not entry.is_dir() or name.startswith(".") or name.startswith("__") or name in _NOISE_DIRS:
                continue
            # Only skip governance dirs (odylith/) at the repo root, not inside source trees
            if is_repo_root and name in _REPO_ROOT_SKIP:
                continue
            if _has_source_files(entry):
                children.append(entry)
    except OSError:
        pass
    return children


def _has_source_files(directory: Path) -> bool:
    """Quick check: does this directory have at least one source file?"""
    count = 0
    try:
        for entry in directory.rglob("*"):
            if entry.is_file() and entry.suffix in {
                ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs",
                ".java", ".rb", ".swift", ".kt", ".cs", ".c", ".cpp",
            }:
                count += 1
                if count >= 2:
                    return True
    except OSError:
        pass
    return count > 0


def _analyze_module(directory: Path, repo_root: Path) -> ComponentSuggestion | None:
    """Analyze a single module directory and produce a component suggestion."""
    rel_path = directory.relative_to(repo_root).as_posix()
    dir_name = directory.name

    # Read the module's contents to understand what it does
    subdirs: list[str] = []
    source_files: list[str] = []
    has_init = False
    has_index = False
    has_readme = False
    readme_text = ""

    try:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            name = entry.name
            if name.startswith(".") or name.startswith("__pycache__"):
                continue
            if entry.is_dir() and name not in _NOISE_DIRS:
                subdirs.append(name)
            elif entry.is_file():
                if name == "__init__.py":
                    has_init = True
                elif name in ("index.ts", "index.js", "index.tsx", "mod.rs", "mod.go"):
                    has_index = True
                elif name.lower().startswith("readme"):
                    has_readme = True
                    try:
                        readme_text = entry.read_text(encoding="utf-8", errors="replace")[:500]
                    except OSError:
                        pass
                elif entry.suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}:
                    source_files.append(entry.stem)
    except OSError:
        return None

    if not subdirs and not source_files:
        return None

    # Infer component label from contents
    label = _infer_label(dir_name, subdirs, source_files)
    comp_id = _slugify(dir_name)

    # Build description: what it is + why track it
    what = _describe_what(dir_name, subdirs, source_files, readme_text)
    why = _describe_why(subdirs, source_files)
    description = f"{what}. {why}"

    return ComponentSuggestion(
        component_id=comp_id,
        label=label,
        path=rel_path,
        description=description,
    )


def _infer_label(dir_name: str, subdirs: list[str], files: list[str]) -> str:
    """Infer a product-level component name."""
    all_names = {n.lower().replace("_", " ") for n in [dir_name] + subdirs + files}

    # Pattern matching on module purpose
    patterns: list[tuple[set[str], str]] = [
        ({"route", "router", "dispatch", "middleware"}, "Request Routing and Middleware"),
        ({"orchestrat", "subagent", "worker", "queue", "celery"}, "Task Orchestration"),
        ({"surface", "dashboard", "render", "template", "shell", "view"}, "Surface and Dashboard Rendering"),
        ({"context", "retrieval", "search", "index", "projection"}, "Context and Retrieval Engine"),
        ({"governance", "sync", "validate", "backlog", "workstream"}, "Governance and Validation"),
        ({"compass", "timeline", "brief", "standup", "history"}, "Execution Timeline"),
        ({"install", "manager", "upgrade", "rollback", "bootstrap", "setup"}, "Install and Lifecycle"),
        ({"bundle", "asset", "mirror", "package", "dist"}, "Asset Bundle and Distribution"),
        ({"benchmark", "evaluation", "score", "metric", "perf"}, "Benchmark and Evaluation"),
        ({"contract", "schema", "adapter", "protocol", "interface"}, "Contracts and Interfaces"),
        ({"auth", "login", "session", "token", "jwt", "oauth", "identity"}, "Authentication and Identity"),
        ({"api", "endpoint", "handler", "controller"}, "API Layer"),
        ({"model", "schema", "migration", "database", "orm", "prisma", "entity"}, "Data Model and Persistence"),
        ({"ui", "component", "page", "layout", "widget", "button"}, "UI Components"),
        ({"config", "setting", "env"}, "Configuration"),
        ({"release", "publish", "deploy", "version", "ci"}, "Release Pipeline"),
        ({"security", "audit", "permission", "access", "rbac"}, "Security and Access Control"),
        ({"cli", "command", "arg", "parse", "console"}, "CLI Interface"),
        ({"common", "shared", "util", "helper", "lib"}, "Shared Utilities"),
        ({"delivery", "intelligence", "proof", "state", "signal"}, "Delivery Intelligence"),
        ({"notification", "email", "webhook", "alert", "sms"}, "Notification Pipeline"),
        ({"payment", "billing", "stripe", "invoice", "checkout"}, "Payment and Billing"),
        ({"storage", "upload", "file", "s3", "blob"}, "File Storage"),
        ({"cache", "redis", "memcache"}, "Caching Layer"),
        ({"log", "trace", "monitor", "observ", "telemetry"}, "Observability"),
        ({"test", "spec", "fixture", "mock", "stub"}, "Test Infrastructure"),
    ]

    for keywords, label in patterns:
        if any(kw in name for name in all_names for kw in keywords):
            return label

    # Fallback: humanize with context
    return _humanize(dir_name)


def _describe_what(dir_name: str, subdirs: list[str], files: list[str], readme: str) -> str:
    """Describe what this module contains."""
    if readme:
        # Use first sentence of README
        for line in readme.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and len(stripped) > 15:
                # Truncate at first period or 120 chars
                dot = stripped.find(".")
                if 0 < dot < 120:
                    return stripped[:dot + 1]
                return stripped[:120]

    parts: list[str] = []
    if subdirs:
        parts.append("contains " + ", ".join(subdirs[:4]) + ("..." if len(subdirs) > 4 else ""))
    if files:
        notable = [f for f in files if f not in ("index", "main", "app", "mod", "__init__")][:4]
        if notable:
            parts.append("key modules: " + ", ".join(notable))

    return " — ".join(parts) if parts else f"code under {dir_name}/"


def _describe_why(subdirs: list[str], files: list[str]) -> str:
    """Explain the governance value of tracking this component."""
    total = len(subdirs) + len(files)
    if total >= 10:
        return "Large boundary — registering it keeps ownership explicit and prevents agents from making changes without understanding the full scope"
    if total >= 5:
        return "Meaningful boundary — naming it gives agent sessions a clear target and keeps delivery accountability visible"
    return "Tracking it now prevents it from becoming an unnamed blind spot as the repo grows"


# ---------------------------------------------------------------------------
# Phase 3: Workstream Suggestions
# ---------------------------------------------------------------------------

def _suggest_workstreams(
    repo_root: Path,
    identity: RepoIdentity,
    components: list[ComponentSuggestion],
    governed: dict[str, bool],
) -> list[WorkstreamSuggestion]:
    """Suggest governance-oriented workstreams based on what the repo needs."""
    _progress("Analyzing governance gaps...")
    workstreams: list[WorkstreamSuggestion] = []

    n_components = len(components)
    repo_name = identity.name or repo_root.name
    stack = ", ".join(identity.frameworks[:2]) if identity.frameworks else ", ".join(identity.languages[:2]) or "this codebase"

    # First workstream: establish component boundaries
    if n_components >= 2 and not governed.get("components"):
        labels = [c.label for c in components[:3]]
        label_text = ", ".join(labels)
        workstreams.append(WorkstreamSuggestion(
            title=f"Establish Component Boundaries for {repo_name}",
            description=(
                f"Your repo has {n_components} natural boundaries ({label_text}). "
                f"Registering them gives every agent session named targets instead of guessing what belongs where."
            ),
        ))

    # Workstream based on test coverage gaps
    untested = [c for c in components if not _dir_has_tests(repo_root, c.path)]
    if untested:
        names = ", ".join(c.label for c in untested[:3])
        workstreams.append(WorkstreamSuggestion(
            title=f"Add Test Coverage for {untested[0].label}" if len(untested) == 1 else f"Close Test Coverage Gaps Across {len(untested)} Components",
            description=(
                f"{names} {'has' if len(untested) == 1 else 'have'} no test files alongside source. "
                f"Tracking this as a workstream ensures coverage lands as governed delivery, not afterthought."
            ),
        ))

    # Workstream for documentation if README is thin
    if not identity.description or len(identity.description) < 30:
        workstreams.append(WorkstreamSuggestion(
            title=f"Document the {repo_name} Architecture and Component Contracts",
            description=(
                f"The repo has no substantive README or architecture docs yet. "
                f"Documenting the {stack} component contracts now prevents knowledge loss as the team grows."
            ),
        ))

    # Workstream for CI/CD if missing
    if not _has_ci(repo_root):
        workstreams.append(WorkstreamSuggestion(
            title=f"Establish CI/CD and Release Governance for {repo_name}",
            description=(
                f"No CI configuration found. Setting up release governance ensures changes are validated before merging."
            ),
        ))

    return workstreams[:4]


def _dir_has_tests(repo_root: Path, rel_path: str) -> bool:
    """Check if a component directory or a sibling tests/ dir has test files."""
    # Check repo-level test directories
    for test_dir in ("tests", "test", "__tests__", "spec"):
        if (repo_root / test_dir).is_dir():
            return True

    target = repo_root / rel_path
    if not target.is_dir():
        return True

    test_patterns = {"test_", "_test.", ".test.", ".spec.", "__tests__"}
    count = 0
    try:
        for entry in target.rglob("*"):
            count += 1
            if count > 300:
                return True
            if entry.is_file():
                name = entry.name.lower()
                if any(p in name for p in test_patterns):
                    return True
    except OSError:
        return True
    return False


def _has_ci(repo_root: Path) -> bool:
    """Check for CI configuration."""
    ci_paths = [
        ".github/workflows",
        ".gitlab-ci.yml",
        ".circleci",
        "Jenkinsfile",
        ".travis.yml",
        "azure-pipelines.yml",
        "bitbucket-pipelines.yml",
    ]
    return any((repo_root / p).exists() for p in ci_paths)


# ---------------------------------------------------------------------------
# Phase 4: Diagram Suggestions
# ---------------------------------------------------------------------------

def _suggest_diagrams(
    components: list[ComponentSuggestion],
    identity: RepoIdentity,
    repo_root: Path,
) -> list[DiagramSuggestion]:
    """Suggest diagrams based on discovered components."""
    diagrams: list[DiagramSuggestion] = []
    repo_slug = _slugify(repo_root.name) or "repo"

    if not components:
        return diagrams

    primary = components[0]

    # Primary component boundary map
    diagrams.append(DiagramSuggestion(
        slug=f"{primary.component_id}-boundary-map",
        title=f"{primary.label} Boundary and Ownership Map",
        description=f"Show what {primary.label} owns, what it depends on, and where its public contract ends",
    ))

    # Cross-component interaction
    if len(components) >= 2:
        labels = [c.label for c in components[:4]]
        label_text = ", ".join(labels[:-1]) + " and " + labels[-1]
        diagrams.append(DiagramSuggestion(
            slug=f"{repo_slug}-component-interaction",
            title=f"{_humanize(repo_root.name)} Component Interaction Map",
            description=f"Connect {label_text} — show dependency edges, shared boundaries, and data flow between them",
        ))

    # Request/execution flow if it's a web app
    if identity.frameworks:
        framework = identity.frameworks[0]
        diagrams.append(DiagramSuggestion(
            slug=f"{repo_slug}-request-flow",
            title=f"{framework} Request and Execution Flow",
            description=f"Trace how a request enters the {framework} app, moves through middleware, hits the data layer, and returns a response",
        ))
    elif len(components) >= 3:
        diagrams.append(DiagramSuggestion(
            slug=f"{repo_slug}-execution-flow",
            title=f"{_humanize(repo_root.name)} Execution Flow",
            description=f"Show how execution moves from the entry point through the core modules to output",
        ))

    return diagrams[:4]


# ---------------------------------------------------------------------------
# Phase 5: Issue Detection
# ---------------------------------------------------------------------------

def _detect_issues(
    repo_root: Path,
    components: list[ComponentSuggestion],
) -> list[IssueSuggestion]:
    """Scan for real issues: TODOs, test gaps, missing docs."""
    _progress("Scanning for issues...")
    issues: list[IssueSuggestion] = []

    # Scan for TODO/FIXME/HACK comments
    todos = _scan_todos(repo_root)
    if todos:
        top = todos[:3]
        for path, line_text in top:
            rel = path.relative_to(repo_root).as_posix() if path.is_relative_to(repo_root) else str(path)
            issues.append(IssueSuggestion(
                title=f"TODO in {rel}: {line_text[:80]}",
                detail=f"Found in {rel} — capturing it in Casebook makes it tracked instead of forgotten",
            ))

    # Check for components with no tests
    for comp in components:
        if not _dir_has_tests(repo_root, comp.path):
            issues.append(IssueSuggestion(
                title=f"No test coverage for {comp.label}",
                detail=f"{comp.path}/ has source files but no test files — the {comp.label} boundary is untested",
            ))

    return issues[:5]


def _scan_todos(repo_root: Path) -> list[tuple[Path, str]]:
    """Fast scan for TODO/FIXME/HACK/XXX comments in source files."""
    results: list[tuple[Path, str]] = []
    source_exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".rb"}
    file_count = 0

    # Skip patterns for generated/bundled files
    skip_patterns = {"bundle", "dist", "generated", "vendor", ".min.", ".v1."}

    try:
        for entry in repo_root.rglob("*"):
            # Skip noise directories
            parts = entry.parts
            if any(p in _NOISE_DIRS or p.startswith(".") for p in parts):
                continue

            if not entry.is_file() or entry.suffix not in source_exts:
                continue

            # Skip generated/bundled files
            rel_str = str(entry.relative_to(repo_root)).lower()
            if any(p in rel_str for p in skip_patterns):
                continue

            file_count += 1
            if file_count > 500:  # Bound the scan
                break

            try:
                text = entry.read_text(encoding="utf-8", errors="replace")
                for line in text.splitlines():
                    match = _TODO_RE.search(line)
                    if match:
                        # Extract text from whichever group matched (# or //)
                        comment_text = (match.group(2) or match.group(4) or "").strip()
                        if len(comment_text) > 10:  # Skip empty/trivial TODOs
                            results.append((entry, comment_text))
                            if len(results) >= 10:
                                return results
            except OSError:
                continue
    except OSError:
        pass

    return results


# ---------------------------------------------------------------------------
# Governance existence checks
# ---------------------------------------------------------------------------

def _load_existing_component_ids(repo_root: Path) -> set[str]:
    """Load component IDs already registered in the registry."""
    registry_path = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    if not registry_path.is_file():
        return set()
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        components = data.get("components", [])
        return {str(c.get("component_id", "")).strip() for c in components if isinstance(c, dict)}
    except (json.JSONDecodeError, OSError):
        return set()


def _load_existing_diagram_slugs(repo_root: Path) -> set[str]:
    """Load diagram slugs already in the Atlas catalog."""
    catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog_path.is_file():
        return set()
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        diagrams = data.get("diagrams", [])
        return {str(d.get("slug", "")).strip() for d in diagrams if isinstance(d, dict)}
    except (json.JSONDecodeError, OSError):
        return set()


def _load_existing_bug_titles(repo_root: Path) -> set[str]:
    """Load bug titles already in Casebook (lowercased for fuzzy match)."""
    bugs_dir = repo_root / "odylith" / "casebook" / "bugs"
    if not bugs_dir.is_dir():
        return set()
    titles: set[str] = set()
    try:
        for entry in bugs_dir.rglob("*.md"):
            if entry.name in ("INDEX.md", "AGENTS.md", "CLAUDE.md"):
                continue
            try:
                for line in entry.read_text(encoding="utf-8").splitlines()[:10]:
                    if "Description:" in line:
                        titles.add(line.split(":", 1)[1].strip().lower()[:80])
                        break
            except OSError:
                continue
    except OSError:
        pass
    return titles


def _has_existing_governance(repo_root: Path) -> dict[str, bool]:
    """Check which governance surfaces already have records."""
    radar_ideas = repo_root / "odylith" / "radar" / "source" / "ideas"
    registry_components = repo_root / "odylith" / "registry" / "source" / "components"
    atlas_catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    casebook_bugs = repo_root / "odylith" / "casebook" / "bugs"

    def _has_records(directory: Path, extension: str = ".md") -> bool:
        if not directory.is_dir():
            return False
        try:
            return any(
                entry.is_file() and entry.suffix == extension and entry.name != "INDEX.md"
                and not entry.name.startswith("AGENTS") and not entry.name.startswith("CLAUDE")
                for entry in directory.rglob(f"*{extension}")
            )
        except OSError:
            return False

    def _has_component_dirs(directory: Path) -> bool:
        if not directory.is_dir():
            return False
        try:
            return any(
                entry.is_dir() and not entry.name.startswith(".")
                and not entry.name.startswith("AGENTS") and not entry.name.startswith("CLAUDE")
                for entry in directory.iterdir()
            )
        except OSError:
            return False

    def _has_atlas_diagrams(catalog_path: Path) -> bool:
        if not catalog_path.is_file():
            return False
        try:
            data = json.loads(catalog_path.read_text(encoding="utf-8"))
            diagrams = data.get("diagrams", [])
            return isinstance(diagrams, list) and len(diagrams) > 0
        except (json.JSONDecodeError, OSError):
            return False

    return {
        "workstreams": _has_records(radar_ideas),
        "components": _has_component_dirs(registry_components),
        "diagrams": _has_atlas_diagrams(atlas_catalog),
        "bugs": _has_records(casebook_bugs),
    }


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_repo(repo_root: Path) -> ShowResult:
    """Analyze the repo and produce governance suggestions."""
    repo_root = repo_root.resolve()
    result = ShowResult()

    print("Scanning your repo for the first time...", file=sys.stderr, flush=True)

    # Phase 1: Identity
    _progress("Reading project manifests...")
    result.identity = _read_project_identity(repo_root)

    # Existing governance check
    result.already_governed = _has_existing_governance(repo_root)

    # Load existing records for dedup
    existing_component_ids = _load_existing_component_ids(repo_root)
    existing_diagram_slugs = _load_existing_diagram_slugs(repo_root)
    existing_bug_titles = _load_existing_bug_titles(repo_root)

    # Phase 2: Components — filter out already-registered
    all_components = _discover_components(repo_root, result.identity)
    result.components = [c for c in all_components if c.component_id not in existing_component_ids]

    # Phase 3: Workstreams
    result.workstreams = _suggest_workstreams(
        repo_root, result.identity, result.components, result.already_governed,
    )

    # Phase 4: Diagrams — filter out already-scaffolded
    all_diagrams = _suggest_diagrams(result.components, result.identity, repo_root)
    result.diagrams = [d for d in all_diagrams if d.slug not in existing_diagram_slugs]

    # Phase 5: Issues — filter out already-captured (fuzzy title match)
    all_issues = _detect_issues(repo_root, result.components)
    result.issues = [
        i for i in all_issues
        if not any(existing in i.title.lower() or i.title.lower() in existing for existing in existing_bug_titles)
    ]

    _progress("Done.")
    return result


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_text(result: ShowResult) -> str:
    """Render the ShowResult as clean Odylith English."""
    lines: list[str] = []
    has_any = False
    identity = result.identity

    # --- Opening ---
    governed_count = sum(1 for v in result.already_governed.values() if v)
    stack_parts: list[str] = []
    if identity.frameworks:
        stack_parts.extend(identity.frameworks[:2])
    if identity.languages:
        stack_parts.extend(identity.languages[:2])
    stack_label = " + ".join(stack_parts) if stack_parts else ""

    if governed_count == 4:
        opening = f"I read your {'monorepo' if identity.monorepo else 'repo'}."
        if stack_label:
            opening += f" It's a {stack_label} project."
        opening += " It already has governance across all four surfaces."
        lines.append(opening)
        lines.append("Here's what I'd add on top of what exists.")
    elif governed_count > 0:
        opening = f"I read your {'monorepo' if identity.monorepo else 'repo'}."
        if stack_label:
            opening += f" It's a {stack_label} project."
        lines.append(opening)
        lines.append("Here's what I see.")
    else:
        opening = f"I read your {'monorepo' if identity.monorepo else 'repo'}."
        if stack_label:
            opening += f" It's a {stack_label} project."
        if identity.description:
            opening += f" {identity.description}"
        lines.append(opening)
        lines.append("Here's what I can do for it.")
    lines.append("")

    # --- Components ---
    if result.components:
        has_any = True
        n = len(result.components)
        lines.append(f"I identified {n} component boundar{'ies' if n != 1 else 'y'}:")
        for comp in result.components:
            lines.append(f'  \u2192 odylith component register "{comp.label}"')
            lines.append(f"    {comp.description}")
        lines.append("")

    # --- Workstreams ---
    if result.workstreams:
        has_any = True
        n = len(result.workstreams)
        lines.append(f"I'd create {n} workstream{'s' if n != 1 else ''} to get started:")
        for ws in result.workstreams:
            lines.append(f'  \u2192 odylith backlog create --title "{ws.title}"')
            lines.append(f"    {ws.description}")
        lines.append("")

    # --- Diagrams ---
    if result.diagrams:
        has_any = True
        lines.append("I can diagram these relationships:")
        for diagram in result.diagrams:
            lines.append(f'  \u2192 odylith atlas scaffold "{diagram.title}"')
            lines.append(f"    {diagram.description}")
        lines.append("")

    # --- Issues ---
    if result.issues:
        has_any = True
        n = len(result.issues)
        lines.append(f"I noticed {n} issue{'s' if n != 1 else ''} worth tracking:")
        for issue in result.issues:
            lines.append(f'  \u2192 odylith bug capture "{issue.title}"')
            lines.append(f"    {issue.detail}")
        lines.append("")

    # --- Footer ---
    if has_any:
        lines.append("Run any command to create it.")
    else:
        lines.append("This repo is already well-governed. Nothing new to suggest.")

    return "\n".join(lines)


def format_json(result: ShowResult) -> str:
    """Render the ShowResult as structured JSON for agent consumption."""
    payload: dict[str, Any] = {
        "identity": {
            "name": result.identity.name,
            "description": result.identity.description,
            "languages": result.identity.languages,
            "frameworks": result.identity.frameworks,
            "monorepo": result.identity.monorepo,
        },
        "already_governed": result.already_governed,
        "components": [
            {
                "component_id": c.component_id,
                "label": c.label,
                "path": c.path,
                "description": c.description,
            }
            for c in result.components
        ],
        "workstreams": [
            {
                "title": w.title,
                "description": w.description,
            }
            for w in result.workstreams
        ],
        "diagrams": [
            {
                "slug": d.slug,
                "title": d.title,
                "description": d.description,
            }
            for d in result.diagrams
        ],
        "issues": [
            {
                "title": i.title,
                "detail": i.detail,
            }
            for i in result.issues
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=False)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="odylith show",
        description="Analyze this repo and show what Odylith governance records it could create.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="Output format: text (default) or json.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create all suggested governance records instead of just showing them.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).expanduser().resolve()
    result = analyze_repo(repo_root)

    if args.apply:
        return _apply_all(repo_root=repo_root, result=result)

    if args.output_format == "json":
        print(format_json(result))
    else:
        print(format_text(result))
    return 0


def _apply_all(*, repo_root: Path, result: ShowResult) -> int:
    """Execute all suggested governance creation commands."""
    created: list[str] = []
    errors: list[str] = []

    for ws in result.workstreams:
        try:
            r = subprocess.run(
                ["odylith", "backlog", "create", "--repo-root", str(repo_root), "--title", ws.title],
                capture_output=True, text=True, cwd=str(repo_root), timeout=30,
            )
            if r.returncode == 0:
                created.append(f"Workstream: {ws.title}")
            else:
                errors.append(f"Workstream '{ws.title}': {r.stdout.strip() or r.stderr.strip()}")
        except Exception as exc:
            errors.append(f"Workstream '{ws.title}': {exc}")

    for comp in result.components:
        try:
            r = subprocess.run(
                ["odylith", "component", "register", "--repo-root", str(repo_root),
                 "--id", comp.component_id, "--path", comp.path, "--label", comp.label],
                capture_output=True, text=True, cwd=str(repo_root), timeout=30,
            )
            if r.returncode == 0:
                created.append(f"Component: {comp.label}")
            else:
                errors.append(f"Component '{comp.label}': {r.stdout.strip() or r.stderr.strip()}")
        except Exception as exc:
            errors.append(f"Component '{comp.label}': {exc}")

    for diagram in result.diagrams:
        try:
            r = subprocess.run(
                ["odylith", "atlas", "scaffold", "--repo-root", str(repo_root),
                 "--slug", diagram.slug, "--title", diagram.title, "--kind", "flowchart"],
                capture_output=True, text=True, cwd=str(repo_root), timeout=30,
            )
            if r.returncode == 0:
                created.append(f"Diagram: {diagram.title}")
            else:
                errors.append(f"Diagram '{diagram.title}': {r.stdout.strip() or r.stderr.strip()}")
        except Exception as exc:
            errors.append(f"Diagram '{diagram.title}': {exc}")

    for issue in result.issues:
        try:
            r = subprocess.run(
                ["odylith", "bug", "capture", "--repo-root", str(repo_root), "--title", issue.title],
                capture_output=True, text=True, cwd=str(repo_root), timeout=30,
            )
            if r.returncode == 0:
                created.append(f"Bug: {issue.title}")
            else:
                errors.append(f"Bug '{issue.title}': {r.stdout.strip() or r.stderr.strip()}")
        except Exception as exc:
            errors.append(f"Bug '{issue.title}': {exc}")

    if created:
        print("Created:")
        for item in created:
            print(f"  \u2713 {item}")
    if errors:
        print("Errors:")
        for item in errors:
            print(f"  \u2717 {item}")
    if not created and not errors:
        print("Nothing to create.")

    return 1 if errors else 0
