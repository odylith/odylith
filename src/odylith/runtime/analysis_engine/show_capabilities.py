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
from odylith.runtime.analysis_engine import import_graph
from odylith.runtime.analysis_engine import repo_analysis


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_repo(repo_root: Path) -> ShowResult:
    """Orchestrate all analysis phases."""
    repo_root = repo_root.resolve()
    result = ShowResult()

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
    artifacts, edges, scan_ctx = import_graph.build_import_graph(
        repo_root, result.identity.languages,
    )
    result.scan_context = scan_ctx
    result.total_modules = len(artifacts)

    if artifacts:
        all_components = import_graph.discover_components_from_imports(repo_root, artifacts, edges)
    else:
        all_components = repo_analysis.discover_components_fallback(repo_root, result.identity)

    # Deduplicate against existing registry
    result.components = [c for c in all_components if c.component_id not in existing_comp_ids]

    # Phase 3: Delivery intelligence posture
    progress("Classifying governance posture...")
    result.component_postures = _classify_component_postures(repo_root, result.components)

    # Phase 4: Workstreams
    result.workstreams = repo_analysis.suggest_workstreams(
        repo_root, result.identity, result.components, result.already_governed, scan_ctx,
    )

    # Phase 5: Grounded diagrams from import edges
    all_diagrams = _suggest_grounded_diagrams(result.components, result.identity, repo_root, edges)
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

def _suggest_grounded_diagrams(
    components: list[ComponentSuggestion],
    identity: Any,
    repo_root: Path,
    edges: list[Any],
) -> list[DiagramSuggestion]:
    """Suggest diagrams grounded in actual import edges, not templates."""
    diagrams: list[DiagramSuggestion] = []
    repo_slug = slugify(repo_root.name) or "repo"

    if not components:
        return diagrams

    # Count cross-component edges for diagram evidence
    comp_paths = {c.path for c in components}
    cross_edges: Counter[tuple[str, str]] = Counter()
    for edge in edges:
        src_comp = _path_to_component(edge.source_path if hasattr(edge, "source_path") else edge.get("source_path", ""), components)
        tgt_comp = _path_to_component(edge.target_path if hasattr(edge, "target_path") else edge.get("target_path", ""), components)
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
    """Render as clean Odylith English with governance insight."""
    lines: list[str] = []
    identity = result.identity

    # Opening
    stack_parts = identity.frameworks[:2] + identity.languages[:2]
    stack = " + ".join(stack_parts) if stack_parts else ""
    governed_count = sum(1 for v in result.already_governed.values() if v)

    opening = f"I read your {'monorepo' if identity.monorepo else 'repo'}."
    if stack:
        opening += f" {stack} project"
        if result.total_modules:
            opening += f", {result.total_modules} source modules."
        else:
            opening += "."
    if governed_count == 4:
        lines.append(opening)
        lines.append("Already governed across all four surfaces. Here's what I'd add.")
    elif governed_count > 0:
        lines.append(opening)
        lines.append("Here's what I see.")
    else:
        if identity.description:
            opening += f" {identity.description}"
        lines.append(opening)
        lines.append("Here's what I can do for it.")
    lines.append("")

    has_any = False

    # Components — split into core (high centrality) and other
    if result.components:
        has_any = True
        core = [c for c in result.components if c.n_inbound > 5]
        other = [c for c in result.components if c.n_inbound <= 5]

        if core:
            lines.append(f"Core boundaries ({len(core)} — high centrality, changes cascade):")
            for comp in core:
                posture = result.component_postures.get(comp.component_id)
                posture_tag = f" [{posture.posture_mode.replace('_', ' ')}]" if posture else ""
                lines.append(f'  \u2192 odylith component register "{comp.label}"')
                blast = ""
                if posture and posture.blast_radius != "local":
                    blast = f" Blast radius: {posture.blast_radius}."
                lines.append(f"    {comp.description}.{blast}{posture_tag}")
            lines.append("")

        if other:
            label = "Other boundaries:" if core else f"Component boundaries ({len(other)}):"
            lines.append(label)
            for comp in other:
                lines.append(f'  \u2192 odylith component register "{comp.label}"')
                lines.append(f"    {comp.description}.")
            lines.append("")

    # Workstreams
    if result.workstreams:
        has_any = True
        lines.append(f"I'd create {len(result.workstreams)} workstream{'s' if len(result.workstreams) != 1 else ''}:")
        for ws in result.workstreams:
            lines.append(f'  \u2192 odylith backlog create --title "{ws.title}"')
            lines.append(f"    {ws.description}")
        lines.append("")

    # Diagrams
    if result.diagrams:
        has_any = True
        lines.append("I can diagram these relationships:")
        for d in result.diagrams:
            lines.append(f'  \u2192 odylith atlas scaffold "{d.title}"')
            lines.append(f"    {d.description}")
        lines.append("")

    # Issues
    if result.issues:
        has_any = True
        lines.append(f"Issues worth tracking ({len(result.issues)}):")
        for issue in result.issues:
            sev_tag = f" [{issue.severity}]" if issue.severity != "medium" else ""
            lines.append(f'  \u2192 odylith bug capture "{issue.title}"{sev_tag}')
            lines.append(f"    {issue.detail}")
        lines.append("")

    if has_any:
        lines.append("Run any command to create it.")
    else:
        lines.append("Nothing new to suggest.")

    return "\n".join(lines)


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
