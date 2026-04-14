"""Orchestrator for `odylith show` — wires analysis phases, delivery intelligence, and output formatting."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from odylith.runtime.analysis_engine.types import (
    ComponentPosture,
    ComponentSuggestion,
    DiagramSuggestion,
    IssueSuggestion,
    ShowResult,
    WorkstreamSuggestion,
    humanize,
    progress,
    slugify,
)
from odylith.runtime.analysis_engine import component_discovery
from odylith.runtime.analysis_engine import incremental_import_graph
from odylith.runtime.analysis_engine import repo_analysis


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_repo(repo_root: Path) -> ShowResult:
    """Orchestrate all analysis phases."""
    repo_root = repo_root.resolve()
    result = ShowResult()

    if incremental_import_graph.has_incremental_cache(repo_root=repo_root):
        print("Refreshing your repo analysis from the incremental cache...", file=sys.stderr, flush=True)
    else:
        print("Scanning your repo for the first time. This takes a moment...", file=sys.stderr, flush=True)

    # Phase 1: Identity
    progress("Reading project manifests...")
    result.identity = repo_analysis.read_project_identity(repo_root)

    # Phase 1b: Existing governance
    result.already_governed = repo_analysis.load_existing_governance(repo_root)
    existing_comp_ids = repo_analysis.load_existing_component_ids(repo_root)
    existing_diagram_slugs = repo_analysis.load_existing_diagram_slugs(repo_root)
    existing_bug_titles = repo_analysis.load_existing_bug_titles(repo_root)

    # Phase 2: Import graph + component discovery
    artifacts, edges, scan_ctx = incremental_import_graph.build_import_graph(
        repo_root, result.identity.languages,
    )
    result.scan_context = scan_ctx
    result.total_modules = len(artifacts)

    if artifacts:
        all_components = component_discovery.discover_components_from_imports(repo_root, artifacts, edges)
    else:
        all_components = repo_analysis.discover_components_fallback(repo_root, result.identity)

    # Deduplicate against existing registry
    result.components = [c for c in all_components if c.component_id not in existing_comp_ids]

    # Match discovered components against existing registered boundaries by path
    _annotate_registry_matches(repo_root, result.components, existing_comp_ids)

    # Phase 3: Delivery intelligence posture
    progress("Classifying governance posture...")
    result.component_postures = _classify_component_postures(repo_root, result.components)

    # Phase 4: Workstreams — grounded in import graph insights
    result.workstreams = _suggest_grounded_workstreams(
        repo_root, result.identity, result.components,
        result.component_postures, result.already_governed, edges,
    )

    # Phase 5: Grounded diagrams — use the surviving components but ALL edges for evidence
    all_diagrams = _suggest_grounded_diagrams(result.components, result.identity, repo_root, edges, all_components)
    result.diagrams = [d for d in all_diagrams if d.slug not in existing_diagram_slugs]

    # Phase 6: Issues
    all_issues = repo_analysis.detect_issues(repo_root, result.components, scan_ctx)
    result.issues = [
        i for i in all_issues
        if not any(existing in i.title.lower() or i.title.lower() in existing for existing in existing_bug_titles)
    ]

    progress("Done.")
    return result


# ---------------------------------------------------------------------------
# Delivery intelligence integration
# ---------------------------------------------------------------------------

def _suggest_grounded_workstreams(
    repo_root: Path,
    identity: Any,
    components: list[ComponentSuggestion],
    postures: dict[str, ComponentPosture],
    governed: dict[str, bool],
    edges: list[Any],
) -> list[WorkstreamSuggestion]:
    """Suggest workstreams grounded in actual import-graph findings."""
    workstreams: list[WorkstreamSuggestion] = []
    repo_name = identity.name or repo_root.name

    # 1. High-blast-radius components with no governance
    risky = [c for c in components if c.component_id in postures
             and postures[c.component_id].blast_radius in ("cross-surface", "contract-level")]
    if risky and not governed.get("components"):
        top = risky[0]
        workstreams.append(WorkstreamSuggestion(
            title=f"Register governance boundaries for {repo_name}",
            description=(
                f"{len(risky)} components have high blast radius but no governance. "
                f"{top.label} alone has {top.n_inbound} dependents — changes there cascade silently without tracked ownership."
            ),
        ))

    # 2. Tightly coupled component pairs (from cross-edges)
    cross: Counter[tuple[str, str]] = Counter()
    comp_paths = {c.path for c in components}
    for edge in edges:
        src = _path_to_component(edge.source_path if hasattr(edge, "source_path") else "", components)
        tgt = _path_to_component(edge.target_path if hasattr(edge, "target_path") else "", components)
        if src and tgt and src != tgt:
            cross[tuple(sorted([src, tgt]))] += 1

    if cross:
        (a, b), count = cross.most_common(1)[0]
        label_a = next((c.label for c in components if c.component_id == a), a)
        label_b = next((c.label for c in components if c.component_id == b), b)
        if count > 10:
            workstreams.append(WorkstreamSuggestion(
                title=f"Clarify the contract between {label_a} and {label_b}",
                description=f"{count} import edges cross this boundary. Documenting the contract prevents breaking changes.",
            ))

    # 3. Volatile edge components (high fan-out, low fan-in)
    volatile = [c for c in components if c.n_outbound > c.n_inbound * 3 and c.n_outbound > 10]
    if volatile:
        v = volatile[0]
        workstreams.append(WorkstreamSuggestion(
            title=f"Reduce coupling in {v.label}",
            description=f"{v.label} depends on {v.n_outbound} modules but only {v.n_inbound} depend on it. High fan-out makes it fragile to upstream changes.",
        ))

    # Fallback if nothing graph-specific found
    if not workstreams:
        workstreams = repo_analysis.suggest_workstreams(
            repo_root, identity, components, governed,
        )

    return workstreams[:3]


def _classify_component_postures(
    repo_root: Path,
    components: list[ComponentSuggestion],
) -> dict[str, ComponentPosture]:
    """Classify each component's governance posture using the delivery intelligence engine."""
    try:
        from odylith.runtime.governance import delivery_intelligence_engine as die
    except ImportError:
        return {}

    postures: dict[str, ComponentPosture] = {}
    for comp in components:
        try:
            # Collect file paths for change vector
            comp_dir = repo_root / comp.path
            file_paths: list[str] = []
            if comp_dir.is_dir():
                for f in comp_dir.rglob("*"):
                    if f.is_file() and f.suffix in {".py", ".ts", ".js", ".go", ".rs"}:
                        file_paths.append(f.relative_to(repo_root).as_posix())
                        if len(file_paths) >= 50:
                            break

            change_vector = die._change_vector_from_paths(file_paths)

            # Map import centrality to blast radius
            if comp.n_inbound > 10:
                blast_class, blast_severity = "cross-surface", 58
            elif comp.n_inbound > 5:
                blast_class, blast_severity = "contract-level", 45
            else:
                blast_class, blast_severity = "local", 24

            lag = die._governance_lag_score(
                explicit_count=0, synthetic_count=0,
                latest_event=None, latest_explicit=None, status="proposed",
            )
            evidence = die._evidence_quality(explicit_count=0, synthetic_count=0)

            mode = die._classify_mode(
                scope_type="component", scope_id=comp.component_id,
                status="proposed",
                explicit_count=0, decision_count=0, implementation_count=0, synthetic_count=0,
                closure_readiness=0, governance_lag=lag,
                convergence=8, concentration=90,
                blast_radius_class=blast_class,
                control_posture="none",
                change_vector=change_vector,
            )

            postures[comp.component_id] = ComponentPosture(
                component_id=comp.component_id,
                posture_mode=mode,
                governance_lag=lag,
                blast_radius=blast_class,
                blast_severity=blast_severity,
                evidence_quality=evidence,
            )
        except Exception:
            continue

    return postures


# ---------------------------------------------------------------------------
# Grounded diagram suggestions
# ---------------------------------------------------------------------------

def _annotate_registry_matches(
    repo_root: Path,
    components: list[ComponentSuggestion],
    existing_ids: set[str],
) -> None:
    """Check if discovered components overlap with existing registered boundaries by path prefix."""
    registry_path = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    if not registry_path.is_file():
        return
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    # Build path prefix lookup from existing components
    existing_prefixes: dict[str, str] = {}
    for entry in data.get("components", []):
        if not isinstance(entry, dict):
            continue
        comp_id = str(entry.get("component_id", "")).strip()
        for prefix in entry.get("path_prefixes", []):
            existing_prefixes[str(prefix).strip()] = comp_id

    # Note: we can't modify frozen dataclasses, so we filter out components
    # whose path already falls under an existing registered boundary
    # (This prevents suggesting a sub-component when the parent is already tracked)
    to_remove: set[int] = set()
    for idx, comp in enumerate(components):
        for prefix, existing_id in existing_prefixes.items():
            if comp.path.startswith(prefix) or prefix.startswith(comp.path):
                to_remove.add(idx)
                break
    for idx in sorted(to_remove, reverse=True):
        components.pop(idx)


def _suggest_grounded_diagrams(
    components: list[ComponentSuggestion],
    identity: Any,
    repo_root: Path,
    edges: list[Any],
    all_components: list[ComponentSuggestion] | None = None,
) -> list[DiagramSuggestion]:
    """Suggest diagrams grounded in actual import edges, not templates."""
    diagrams: list[DiagramSuggestion] = []
    repo_slug = slugify(repo_root.name) or "repo"

    if not components:
        return diagrams

    # Use all_components for edge counting (includes pre-filter components)
    lookup_components = all_components if all_components else components
    cross_edges: Counter[tuple[str, str]] = Counter()
    for edge in edges:
        src_comp = _path_to_component(edge.source_path if hasattr(edge, "source_path") else "", lookup_components)
        tgt_comp = _path_to_component(edge.target_path if hasattr(edge, "target_path") else "", lookup_components)
        if src_comp and tgt_comp and src_comp != tgt_comp:
            pair = tuple(sorted([src_comp, tgt_comp]))
            cross_edges[pair] += 1

    # Highest-centrality component boundary map
    primary = components[0]
    diagrams.append(DiagramSuggestion(
        slug=f"{primary.component_id}-boundary-map",
        title=f"{primary.label} Boundary and Ownership Map",
        description=f"Show what {primary.label} owns, what depends on it ({primary.n_inbound} inbound imports), and where its contract ends",
    ))

    # Cross-component dependency diagram from real edges
    if cross_edges:
        top_pair = cross_edges.most_common(1)[0]
        (comp_a, comp_b), edge_count = top_pair
        label_a = next((c.label for c in components if c.component_id == comp_a), comp_a)
        label_b = next((c.label for c in components if c.component_id == comp_b), comp_b)
        diagrams.append(DiagramSuggestion(
            slug=f"{repo_slug}-{comp_a}-{comp_b}-dependency",
            title=f"{label_a} \u2194 {label_b} Dependency Map",
            description=f"{edge_count} import edges connect these two boundaries — diagramming them makes the coupling visible",
        ))

    # Full interaction map if 3+ components
    if len(components) >= 3:
        labels = [c.label for c in components[:4]]
        label_text = ", ".join(labels[:-1]) + " and " + labels[-1]
        total_cross = sum(cross_edges.values())
        diagrams.append(DiagramSuggestion(
            slug=f"{repo_slug}-component-interaction",
            title=f"{humanize(repo_root.name)} Component Interaction Map",
            description=f"Connect {label_text} — {total_cross} cross-component import edges to visualize",
        ))

    return diagrams[:4]


def _path_to_component(file_path: str, components: list[ComponentSuggestion]) -> str:
    """Map a file path to the component that owns it."""
    for comp in components:
        if file_path.startswith(comp.path + "/") or file_path.startswith(comp.path):
            return comp.component_id
    return ""


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_text(result: ShowResult) -> str:
    """Render as clean, scannable Odylith output. Every line earns its place."""
    lines: list[str] = []
    identity = result.identity
    governed_count = sum(1 for v in result.already_governed.values() if v)

    # --- Opening: one line, identity + scale ---
    parts = []
    stack = " + ".join((identity.frameworks[:2] + identity.languages[:2])[:3])
    if stack:
        parts.append(stack)
    if result.total_modules:
        parts.append(f"{result.total_modules} modules")
    if identity.monorepo:
        parts.append("monorepo")
    opening = ", ".join(parts) + "." if parts else ""
    if governed_count == 4:
        lines.append(f"I read your repo. {opening} Already governed across all four surfaces.")
    elif governed_count > 0:
        lines.append(f"I read your repo. {opening}")
    else:
        desc = f" {identity.description}" if identity.description else ""
        lines.append(f"I read your repo. {opening}{desc}")
    lines.append("")

    has_any = False

    # --- Components ---
    if result.components:
        has_any = True
        n = len(result.components)
        lines.append(f"### Components — {n} boundar{'ies' if n != 1 else 'y'} discovered")
        lines.append("")
        for comp in result.components:
            posture = result.component_postures.get(comp.component_id)
            metric = _short_metric(comp, posture)
            lines.append(f"- **{comp.label}** — {metric}")
            lines.append(f'  `odylith component register "{comp.label}"`')
        lines.append("")

    # --- Workstreams ---
    if result.workstreams:
        has_any = True
        lines.append(f"### Workstreams — {len(result.workstreams)} to get started")
        lines.append("")
        for ws in result.workstreams:
            lines.append(f"- **{ws.title}**")
            lines.append(f"  {ws.description}")
            lines.append(f'  `odylith backlog create --title "{ws.title}"`')
        lines.append("")

    # --- Diagrams ---
    if result.diagrams:
        has_any = True
        lines.append("### Diagrams")
        lines.append("")
        for d in result.diagrams:
            lines.append(f"- **{d.title}**")
            lines.append(f"  {d.description}")
            lines.append(f'  `odylith atlas scaffold "{d.title}"`')
        lines.append("")

    # --- Issues ---
    if result.issues:
        has_any = True
        lines.append(f"### Issues — {len(result.issues)} worth tracking")
        lines.append("")
        for issue in result.issues:
            sev = f" [{issue.severity}]" if issue.severity != "medium" else ""
            lines.append(f"- **{issue.title}**{sev}")
            lines.append(f"  {issue.detail}")
            lines.append(f'  `odylith bug capture "{issue.title}"`')
        lines.append("")

    # --- Footer ---
    if has_any:
        lines.append("---")
        lines.append("Run any command to create it.")
    else:
        if governed_count == 4:
            lines.append("Your repo is well-governed. Nothing new to suggest.")
        else:
            lines.append("Nothing to suggest yet. Run `odylith show` again after adding source files.")

    return "\n".join(lines)


def _short_metric(comp: ComponentSuggestion, posture: ComponentPosture | None) -> str:
    """One short right-aligned metric string for a component."""
    parts: list[str] = []
    if comp.n_inbound > 20:
        parts.append(f"{comp.n_inbound} dependents")
    elif comp.n_inbound > 0:
        parts.append(f"{comp.n_inbound} dependents")

    # Architecture role
    total = comp.n_inbound + comp.n_outbound
    if total > 0:
        instability = comp.n_outbound / total
        if instability < 0.2 and comp.n_inbound > 5:
            parts.append("stable foundation")
        elif instability > 0.8 and comp.n_outbound > 5:
            parts.append("edge consumer")
        elif 0.3 < instability < 0.7 and comp.n_inbound > 3:
            parts.append("integration layer")
    elif comp.n_modules > 0:
        parts.append(f"{comp.n_modules} modules")

    if not parts:
        parts.append("self-contained")

    return " \u00b7 ".join(parts)


def format_json(result: ShowResult) -> str:
    """Structured JSON for agent consumption."""
    payload: dict[str, Any] = {
        "identity": {
            "name": result.identity.name,
            "description": result.identity.description,
            "languages": result.identity.languages,
            "frameworks": result.identity.frameworks,
            "monorepo": result.identity.monorepo,
        },
        "total_modules": result.total_modules,
        "already_governed": result.already_governed,
        "components": [
            {
                "component_id": c.component_id,
                "label": c.label,
                "path": c.path,
                "description": c.description,
                "n_modules": c.n_modules,
                "n_inbound": c.n_inbound,
                "n_outbound": c.n_outbound,
                "posture": {
                    "mode": result.component_postures[c.component_id].posture_mode,
                    "governance_lag": result.component_postures[c.component_id].governance_lag,
                    "blast_radius": result.component_postures[c.component_id].blast_radius,
                    "evidence_quality": result.component_postures[c.component_id].evidence_quality,
                } if c.component_id in result.component_postures else None,
            }
            for c in result.components
        ],
        "workstreams": [{"title": w.title, "description": w.description} for w in result.workstreams],
        "diagrams": [{"slug": d.slug, "title": d.title, "description": d.description} for d in result.diagrams],
        "issues": [{"title": i.title, "detail": i.detail, "severity": i.severity} for i in result.issues],
    }
    return json.dumps(payload, indent=2, sort_keys=False)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="odylith show", description="Analyze this repo and show what Odylith can do.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    parser.add_argument("--apply", action="store_true")
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
    created, errors = [], []
    for ws in result.workstreams:
        try:
            r = subprocess.run(["odylith", "backlog", "create", "--repo-root", str(repo_root), "--title", ws.title],
                               capture_output=True, text=True, cwd=str(repo_root), timeout=30)
            (created if r.returncode == 0 else errors).append(f"Workstream: {ws.title}")
        except Exception as exc:
            errors.append(f"Workstream '{ws.title}': {exc}")
    for comp in result.components:
        try:
            r = subprocess.run(["odylith", "component", "register", "--repo-root", str(repo_root),
                                "--id", comp.component_id, "--path", comp.path, "--label", comp.label],
                               capture_output=True, text=True, cwd=str(repo_root), timeout=30)
            (created if r.returncode == 0 else errors).append(f"Component: {comp.label}")
        except Exception as exc:
            errors.append(f"Component '{comp.label}': {exc}")
    for d in result.diagrams:
        try:
            r = subprocess.run(["odylith", "atlas", "scaffold", "--repo-root", str(repo_root),
                                "--slug", d.slug, "--title", d.title, "--kind", "flowchart"],
                               capture_output=True, text=True, cwd=str(repo_root), timeout=30)
            (created if r.returncode == 0 else errors).append(f"Diagram: {d.title}")
        except Exception as exc:
            errors.append(f"Diagram '{d.title}': {exc}")
    for issue in result.issues:
        try:
            r = subprocess.run(["odylith", "bug", "capture", "--repo-root", str(repo_root), "--title", issue.title],
                               capture_output=True, text=True, cwd=str(repo_root), timeout=30)
            (created if r.returncode == 0 else errors).append(f"Bug: {issue.title}")
        except Exception as exc:
            errors.append(f"Bug '{issue.title}': {exc}")

    for item in created:
        print(f"  \u2713 {item}")
    for item in errors:
        print(f"  \u2717 {item}")
    if not created and not errors:
        print("Nothing to create.")
    return 1 if errors else 0
