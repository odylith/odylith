"""Project identity, component fallback discovery, workstream/diagram suggestions, issue detection, and governance checks."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

from odylith.runtime.analysis_engine.types import (
    ComponentSuggestion,
    DiagramSuggestion,
    IssueSuggestion,
    RepoIdentity,
    ScanContext,
    WorkstreamSuggestion,
    slugify,
    humanize,
    progress,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NOISE_DIRS = frozenset({
    ".git", ".hg", ".svn", ".odylith", "node_modules",
    "__pycache__", ".venv", "venv", "env", ".env",
    "build", "dist", "target", "out", "output",
    "coverage", ".coverage", ".idea", ".vscode",
    ".next", ".nuxt", ".cache", ".turbo",
    "vendor", "deps", ".deps",
})
REPO_ROOT_SKIP = frozenset({"odylith"})
_SOURCE_ROOTS = ("src", "lib", "packages", "apps", "services", "backend", "frontend", "server", "api", "cmd")
_WRAPPER_NAMES = frozenset({
    "src", "lib", "libs", "pkg", "packages", "apps", "app", "cmd",
    "internal", "modules", "main",
})
_INFRA_DIR_NAMES = frozenset({
    "ci", "docker", "k8s", "kubernetes", "terraform", "infra",
    "deployment", "deploy", ".github", "migrations",
})

_LABEL_PATTERNS: list[tuple[set[str], str]] = [
    # General software architecture patterns — no product-specific knowledge.
    # These are universal concepts found across any codebase.
    ({"route", "router", "dispatch", "middleware"}, "Routing and Middleware"),
    ({"orchestrat", "worker", "queue", "celery", "scheduler"}, "Orchestration"),
    ({"render", "template", "view", "presenter"}, "Rendering"),
    ({"search", "index", "retrieval", "query"}, "Search and Retrieval"),
    ({"validate", "validator", "check", "lint"}, "Validation"),
    ({"install", "setup", "upgrade", "rollback", "bootstrap"}, "Install and Lifecycle"),
    ({"bundle", "asset", "package", "dist", "build"}, "Build and Distribution"),
    ({"benchmark", "evaluation", "perf", "metric", "score"}, "Benchmark and Evaluation"),
    ({"contract", "schema", "protocol", "interface", "adapter"}, "Contracts and Interfaces"),
    ({"auth", "login", "session", "token", "jwt", "oauth", "identity"}, "Authentication"),
    ({"api", "endpoint", "handler", "controller"}, "API"),
    ({"model", "migration", "database", "orm", "entity", "repository"}, "Data Model"),
    ({"ui", "component", "page", "layout", "widget"}, "UI"),
    ({"config", "setting", "env"}, "Configuration"),
    ({"release", "publish", "deploy", "version"}, "Release and Deployment"),
    ({"security", "audit", "permission", "access", "rbac"}, "Security"),
    ({"cli", "command", "console"}, "CLI"),
    ({"common", "shared", "util", "helper", "lib"}, "Shared Utilities"),
    ({"notification", "email", "webhook", "alert", "sms", "push"}, "Notifications"),
    ({"payment", "billing", "invoice", "checkout", "stripe"}, "Payments"),
    ({"storage", "upload", "file", "blob", "s3"}, "Storage"),
    ({"cache", "redis", "memcache"}, "Cache"),
    ({"log", "trace", "monitor", "observ", "telemetry"}, "Observability"),
    ({"test", "spec", "fixture", "mock"}, "Tests"),
    ({"memory", "embed", "vector", "similarity"}, "Memory"),
    ({"dashboard", "surface", "shell", "panel"}, "Dashboard"),
    ({"sync", "replicate", "mirror"}, "Sync"),
    ({"context", "engine", "runtime", "core"}, "Core Engine"),
    ({"delivery", "intelligence", "signal"}, "Intelligence"),
    ({"reasoning", "inference", "logic", "rule"}, "Reasoning"),
    ({"execution", "pipeline", "workflow", "step"}, "Execution"),
]


# ---------------------------------------------------------------------------
# Project Identity
# ---------------------------------------------------------------------------

def read_project_identity(repo_root: Path) -> RepoIdentity:
    """Read manifests, README, and structure to understand what this repo is."""
    identity = RepoIdentity()
    identity.name = repo_root.name

    if (repo_root / "pyproject.toml").is_file():
        identity.languages.append("Python")
        _parse_pyproject(repo_root / "pyproject.toml", identity)
    if (repo_root / "setup.py").is_file() and "Python" not in identity.languages:
        identity.languages.append("Python")
    if (repo_root / "package.json").is_file():
        _parse_package_json(repo_root / "package.json", identity)
    if (repo_root / "go.mod").is_file():
        identity.languages.append("Go")
        _parse_go_mod(repo_root / "go.mod", identity)
    if (repo_root / "Cargo.toml").is_file():
        identity.languages.append("Rust")
    if (repo_root / "pom.xml").is_file() or (repo_root / "build.gradle").is_file():
        identity.languages.append("Java/Kotlin")
    if (repo_root / "Gemfile").is_file():
        identity.languages.append("Ruby")
        if (repo_root / "config" / "routes.rb").is_file():
            identity.frameworks.append("Rails")

    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme = repo_root / readme_name
        if readme.is_file():
            try:
                text = readme.read_text(encoding="utf-8", errors="replace")[:2000]
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
    lower = text.lower()
    for name, framework in [("django", "Django"), ("fastapi", "FastAPI"), ("flask", "Flask"), ("streamlit", "Streamlit")]:
        if name in lower:
            identity.frameworks.append(framework)
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
        identity.languages.append("TypeScript" if (path.parent / "tsconfig.json").is_file() else "JavaScript")
    if data.get("name"):
        identity.name = str(data["name"])
    if data.get("description") and not identity.description:
        identity.description = str(data["description"])[:200]
    all_deps = {**dict(data.get("dependencies", {})), **dict(data.get("devDependencies", {}))}
    for pkg, fw in [("next", "Next.js"), ("@sveltejs/kit", "SvelteKit"), ("svelte", "Svelte"),
                     ("vue", "Vue"), ("express", "Express"), ("@nestjs/core", "NestJS"), ("hono", "Hono")]:
        if pkg in all_deps:
            identity.frameworks.append(fw)
            break
    if "react" in all_deps and not identity.frameworks:
        identity.frameworks.append("React")
    workspaces = data.get("workspaces", [])
    if workspaces:
        identity.monorepo = True
        if isinstance(workspaces, list):
            identity.workspace_dirs = [str(w) for w in workspaces[:10]]
        elif isinstance(workspaces, dict):
            identity.workspace_dirs = [str(w) for w in workspaces.get("packages", [])[:10]]


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
    for name, fw in [("gin-gonic", "Gin"), ("gorilla/mux", "Gorilla"), ("fiber", "Fiber")]:
        if name in lower:
            identity.frameworks.append(fw)


# ---------------------------------------------------------------------------
# Component fallback discovery (directory walking)
# ---------------------------------------------------------------------------

def discover_components_fallback(repo_root: Path, identity: RepoIdentity) -> list[ComponentSuggestion]:
    """Directory-structure-based component discovery. Used when import graph is unavailable."""
    if identity.monorepo and identity.workspace_dirs:
        return _discover_monorepo_components(repo_root, identity)
    module_root = _find_module_level(repo_root)
    children = _source_children(module_root)
    components: list[ComponentSuggestion] = []
    for child in children[:8]:
        comp = _analyze_module(child, repo_root)
        if comp:
            components.append(comp)
    return components[:6]


def _discover_monorepo_components(repo_root: Path, identity: RepoIdentity) -> list[ComponentSuggestion]:
    import glob as glob_mod
    components: list[ComponentSuggestion] = []
    for pattern in identity.workspace_dirs:
        for match_path in sorted(glob_mod.glob(str(repo_root / pattern)))[:6]:
            match = Path(match_path)
            if match.is_dir():
                comp = _analyze_module(match, repo_root)
                if comp:
                    components.append(comp)
    return components[:8]


def _find_module_level(repo_root: Path) -> Path:
    source_root = None
    for name in _SOURCE_ROOTS:
        candidate = repo_root / name
        if candidate.is_dir() and _has_source_files(candidate):
            source_root = candidate
            break
    if source_root is None:
        return repo_root
    current = source_root
    for _ in range(5):
        children = _source_children(current)
        if len(children) >= 2:
            return current
        if len(children) == 1:
            current = children[0]
            continue
        break
    return current


def _source_children(directory: Path) -> list[Path]:
    skip = NOISE_DIRS | {n for n in directory.parts if n.startswith(".")}
    children: list[Path] = []
    try:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            name = entry.name
            if not entry.is_dir() or name.startswith(".") or name.startswith("__") or name in skip:
                continue
            if _has_source_files(entry):
                children.append(entry)
    except OSError:
        pass
    return children


def _has_source_files(directory: Path) -> bool:
    count = 0
    try:
        for entry in directory.rglob("*"):
            if entry.is_file() and entry.suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".rb"}:
                count += 1
                if count >= 2:
                    return True
    except OSError:
        pass
    return count > 0


def _analyze_module(directory: Path, repo_root: Path) -> ComponentSuggestion | None:
    rel_path = directory.relative_to(repo_root).as_posix()
    subdirs, source_files = [], []
    try:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            name = entry.name
            if name.startswith(".") or name.startswith("__"):
                continue
            if entry.is_dir() and name not in NOISE_DIRS:
                subdirs.append(name)
            elif entry.is_file() and entry.suffix in {".py", ".ts", ".js", ".go", ".rs", ".java"}:
                source_files.append(entry.stem)
    except OSError:
        return None
    if not subdirs and not source_files:
        return None
    label = infer_label(directory.name, subdirs, source_files)
    what = _describe_what(directory.name, subdirs, source_files)
    why = _describe_why(subdirs, source_files)
    return ComponentSuggestion(
        component_id=slugify(directory.name), label=label, path=rel_path,
        description=f"{what}. {why}",
    )


def infer_label(dir_name: str, subdirs: list[str], files: list[str]) -> str:
    all_names = {n.lower().replace("_", " ") for n in [dir_name] + subdirs + files}
    for keywords, label in _LABEL_PATTERNS:
        if any(kw in name for name in all_names for kw in keywords):
            return label
    return humanize(dir_name)


def _describe_what(dir_name: str, subdirs: list[str], files: list[str]) -> str:
    parts = []
    if subdirs:
        parts.append("contains " + ", ".join(subdirs[:4]) + ("..." if len(subdirs) > 4 else ""))
    notable = [f for f in files if f not in ("index", "main", "app", "mod", "__init__")][:4]
    if notable:
        parts.append("key modules: " + ", ".join(notable))
    return " — ".join(parts) if parts else f"code under {dir_name}/"


def _describe_why(subdirs: list[str], files: list[str]) -> str:
    total = len(subdirs) + len(files)
    if total >= 10:
        return "Large boundary — registering it keeps ownership explicit"
    if total >= 5:
        return "Meaningful boundary — naming it gives agent sessions a clear target"
    return "Tracking it prevents it from becoming an unnamed blind spot"


# ---------------------------------------------------------------------------
# Workstream, diagram, and issue suggestions
# ---------------------------------------------------------------------------

def suggest_workstreams(
    repo_root: Path,
    identity: RepoIdentity,
    components: list[ComponentSuggestion],
    governed: dict[str, bool],
    scan_ctx: ScanContext | None = None,
) -> list[WorkstreamSuggestion]:
    progress("Analyzing governance gaps...")
    workstreams: list[WorkstreamSuggestion] = []
    repo_name = identity.name or repo_root.name
    n = len(components)

    if n >= 2 and not governed.get("components"):
        labels = [c.label for c in components[:3]]
        workstreams.append(WorkstreamSuggestion(
            title=f"Establish Component Boundaries for {repo_name}",
            description=f"{n} boundaries found ({', '.join(labels)}). Registering them gives agent sessions named targets.",
        ))

    if scan_ctx:
        untested_dirs = {c.path for c in components if c.path not in scan_ctx.test_files}
        if untested_dirs and len(untested_dirs) >= 2:
            workstreams.append(WorkstreamSuggestion(
                title=f"Close Test Coverage Gaps Across {len(untested_dirs)} Components",
                description="Tracking coverage as a workstream ensures it lands as governed delivery.",
            ))
    if not identity.description or len(identity.description) < 30:
        stack = ", ".join(identity.frameworks[:2]) or ", ".join(identity.languages[:2]) or "this codebase"
        workstreams.append(WorkstreamSuggestion(
            title=f"Document the {repo_name} Architecture and Component Contracts",
            description=f"No substantive README yet. Documenting the {stack} contracts prevents knowledge loss.",
        ))
    if not _has_ci(repo_root):
        workstreams.append(WorkstreamSuggestion(
            title=f"Establish CI/CD and Release Governance for {repo_name}",
            description="No CI configuration found. Release governance ensures changes are validated before merging.",
        ))
    return workstreams[:4]


def _has_ci(repo_root: Path) -> bool:
    return any((repo_root / p).exists() for p in [
        ".github/workflows", ".gitlab-ci.yml", ".circleci", "Jenkinsfile",
        ".travis.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml",
    ])


def suggest_diagrams(
    components: list[ComponentSuggestion],
    identity: RepoIdentity,
    repo_root: Path,
) -> list[DiagramSuggestion]:
    diagrams: list[DiagramSuggestion] = []
    repo_slug = slugify(repo_root.name) or "repo"
    if not components:
        return diagrams
    primary = components[0]
    diagrams.append(DiagramSuggestion(
        slug=f"{primary.component_id}-boundary-map",
        title=f"{primary.label} Boundary and Ownership Map",
        description=f"Show what {primary.label} owns and where its contract ends",
    ))
    if len(components) >= 2:
        labels = [c.label for c in components[:4]]
        label_text = ", ".join(labels[:-1]) + " and " + labels[-1]
        diagrams.append(DiagramSuggestion(
            slug=f"{repo_slug}-component-interaction",
            title=f"{humanize(repo_root.name)} Component Interaction Map",
            description=f"Connect {label_text} — show dependency edges and data flow",
        ))
    if identity.frameworks:
        diagrams.append(DiagramSuggestion(
            slug=f"{repo_slug}-request-flow",
            title=f"{identity.frameworks[0]} Request and Execution Flow",
            description=f"Trace a request from entry through middleware to response",
        ))
    return diagrams[:4]


def detect_issues(
    repo_root: Path,
    components: list[ComponentSuggestion],
    scan_ctx: ScanContext | None = None,
) -> list[IssueSuggestion]:
    progress("Scanning for issues...")
    issues: list[IssueSuggestion] = []
    if scan_ctx and scan_ctx.todos:
        for rel_path, text in scan_ctx.todos[:3]:
            issues.append(IssueSuggestion(
                title=f"TODO in {rel_path}: {text[:60]}",
                detail=f"Found in {rel_path} — capturing it in Casebook makes it tracked",
                severity="medium",
            ))
    return issues[:5]


# ---------------------------------------------------------------------------
# Governance existence checks
# ---------------------------------------------------------------------------

def load_existing_governance(repo_root: Path) -> dict[str, bool]:
    radar = repo_root / "odylith" / "radar" / "source" / "ideas"
    registry = repo_root / "odylith" / "registry" / "source" / "components"
    atlas = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    casebook = repo_root / "odylith" / "casebook" / "bugs"

    def _has_md(d: Path) -> bool:
        if not d.is_dir():
            return False
        try:
            return any(e.is_file() and e.suffix == ".md" and e.name not in ("INDEX.md", "AGENTS.md", "CLAUDE.md") for e in d.rglob("*.md"))
        except OSError:
            return False

    def _has_dirs(d: Path) -> bool:
        if not d.is_dir():
            return False
        try:
            return any(e.is_dir() and not e.name.startswith(".") for e in d.iterdir())
        except OSError:
            return False

    def _has_diagrams(p: Path) -> bool:
        if not p.is_file():
            return False
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return isinstance(data.get("diagrams"), list) and len(data["diagrams"]) > 0
        except (json.JSONDecodeError, OSError):
            return False

    return {
        "workstreams": _has_md(radar),
        "components": _has_dirs(registry),
        "diagrams": _has_diagrams(atlas),
        "bugs": _has_md(casebook),
    }


def load_existing_component_ids(repo_root: Path) -> set[str]:
    path = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(c.get("component_id", "")).strip() for c in data.get("components", []) if isinstance(c, dict)}
    except (json.JSONDecodeError, OSError):
        return set()


def load_existing_diagram_slugs(repo_root: Path) -> set[str]:
    path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(d.get("slug", "")).strip() for d in data.get("diagrams", []) if isinstance(d, dict)}
    except (json.JSONDecodeError, OSError):
        return set()


def load_existing_bug_titles(repo_root: Path) -> set[str]:
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
