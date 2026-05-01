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


_APP_READY_TEACHING = (
    "Mental model: Registry names ownership, Radar tracks delivery, Atlas explains shape, "
    "and Casebook captures bugs; Odylith proposes them only from app-source evidence."
)
_CHEATSHEET_HINT = "For more examples, open `odylith/index.html` and use the Cheatsheet."
_SCENARIO_TEACHING = {
    "empty": "Odylith did not find app-source evidence yet, so it will not invent records. Open `odylith/index.html` and start with the Cheatsheet, or name the first path or feature you want governed.",
    "metadata-only": "Manifests identify the stack, but they are not an ownership boundary; name a path or feature when you are ready.",
    "docs-only": "Docs are useful context, but Odylith will not turn documentation alone into governance records.",
    "managed-only": "Odylith-managed files belong to Odylith, not your app, so they are ignored as boundary evidence.",
    "tests-only": "Tests prove behavior, but they are not the application boundary; Odylith needs app source before suggesting records.",
    "infra-only": "Infra and CI describe deployment mechanics, not app ownership; Odylith needs app source before suggesting records.",
    "thin-app": "Thin source exists, so Odylith will not invent a boundary; name the path or feature you want to govern first.",
    "already-governed": "Existing governance already covers the detected source; use a path-specific prompt to extend it instead of duplicating records.",
}


def analyze_repo(repo_root: Path) -> ShowResult:
    """Orchestrate all analysis phases."""
    repo_root = repo_root.resolve()
    result = ShowResult()

    if sys.stderr.isatty():
        if incremental_import_graph.has_incremental_cache(repo_root=repo_root):
            print("Refreshing your repo analysis from the incremental cache...", file=sys.stderr, flush=True)
        else:
            print("Scanning your repo for the first time. This takes a moment...", file=sys.stderr, flush=True)

    progress("Reading project manifests...")
    result.identity = repo_analysis.read_project_identity(repo_root)

    result.already_governed = repo_analysis.load_existing_governance(repo_root)
    existing_comp_ids = repo_analysis.load_existing_component_ids(repo_root)
    existing_diagram_slugs = repo_analysis.load_existing_diagram_slugs(repo_root)
    existing_bug_titles = repo_analysis.load_existing_bug_titles(repo_root)
    if existing_comp_ids:
        result.already_governed["components"] = True

    artifacts, edges, scan_ctx = incremental_import_graph.build_import_graph(
        repo_root, result.identity.languages,
    )
    result.scan_context = scan_ctx
    result.total_modules = len(artifacts)
    result.app_modules = len(scan_ctx.app_files)
    result.support_modules = len(scan_ctx.support_files)
    result.source_summary = repo_analysis.summarize_source_inventory(repo_root, scan_ctx)
    app_paths = set(scan_ctx.app_files)
    app_artifacts = [artifact for artifact in artifacts if artifact.path in app_paths]
    app_edges = [
        edge for edge in edges
        if edge.source_path in app_paths and edge.target_path in app_paths
    ]

    if result.app_modules >= 3:
        all_components = _discover_app_components(repo_root, result.identity, app_artifacts, app_edges)
    else:
        all_components = []

    result.components = [c for c in all_components if c.component_id not in existing_comp_ids]
    _annotate_registry_matches(repo_root, result.components, existing_comp_ids)

    progress("Classifying governance posture...")
    result.component_postures = _classify_component_postures(repo_root, result.components)

    result.workstreams = _suggest_grounded_workstreams(
        repo_root, result.identity, result.components,
        result.component_postures, result.already_governed, app_edges,
    )

    all_diagrams = _suggest_grounded_diagrams(result.components, result.identity, repo_root, app_edges, all_components)
    result.diagrams = [d for d in all_diagrams if d.slug not in existing_diagram_slugs]

    all_issues = repo_analysis.detect_issues(repo_root, result.components, scan_ctx)
    result.issues = [
        i for i in all_issues
        if not any(existing in i.title.lower() or i.title.lower() in existing for existing in existing_bug_titles)
    ]
    result.scenario = _select_show_scenario(result)

    progress("Done.")
    return result


def _discover_app_components(
    repo_root: Path,
    identity: Any,
    app_artifacts: list[Any],
    app_edges: list[Any],
) -> list[ComponentSuggestion]:
    """Create candidates only from confident application-source evidence."""
    workspace_components = repo_analysis.discover_workspace_app_components(repo_root, identity, app_artifacts)
    if workspace_components:
        return workspace_components
    components = component_discovery.discover_components_from_imports(repo_root, app_artifacts, app_edges)
    if components and not _has_wrapper_component_label(components):
        return components
    fallback = repo_analysis.build_app_boundary_suggestion(repo_root, identity, app_artifacts)
    return [fallback] if fallback else []


def _has_wrapper_component_label(components: list[ComponentSuggestion]) -> bool:
    wrappers = {"src", "lib", "pkg", "packages", "apps", "app", "cmd", "main"}
    return any(component.label.strip().lower() in wrappers for component in components)


def _suggest_grounded_workstreams(
    repo_root: Path,
    identity: Any,
    components: list[ComponentSuggestion],
    postures: dict[str, ComponentPosture],
    governed: dict[str, bool],
    edges: list[Any],
) -> list[WorkstreamSuggestion]:
    """Suggest workstreams grounded in actual import-graph findings."""
    if not components:
        return []
    workstreams: list[WorkstreamSuggestion] = []
    repo_name = repo_analysis.display_repo_name(repo_root, identity)

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

    volatile = [c for c in components if c.n_outbound > c.n_inbound * 3 and c.n_outbound > 10]
    if volatile:
        v = volatile[0]
        workstreams.append(WorkstreamSuggestion(
            title=f"Reduce coupling in {v.label}",
            description=f"{v.label} depends on {v.n_outbound} modules but only {v.n_inbound} depend on it. High fan-out makes it fragile to upstream changes.",
        ))

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
            comp_dir = repo_root / comp.path
            file_paths: list[str] = []
            if comp_dir.is_dir():
                for f in comp_dir.rglob("*"):
                    if (
                        f.is_file()
                        and repo_analysis.source_file_role(f, repo_root=repo_root)
                        == repo_analysis.SOURCE_CATEGORY_APP
                    ):
                        file_paths.append(f.relative_to(repo_root).as_posix())
                        if len(file_paths) >= 50:
                            break

            change_vector = die._change_vector_from_paths(file_paths)

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
    existing_prefixes: dict[str, str] = {}
    for entry in data.get("components", []):
        if not isinstance(entry, dict):
            continue
        comp_id = str(entry.get("component_id", "")).strip()
        for prefix in entry.get("path_prefixes", []):
            existing_prefixes[str(prefix).strip()] = comp_id

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

    lookup_components = all_components if all_components else components
    cross_edges: Counter[tuple[str, str]] = Counter()
    for edge in edges:
        src_comp = _path_to_component(edge.source_path if hasattr(edge, "source_path") else "", lookup_components)
        tgt_comp = _path_to_component(edge.target_path if hasattr(edge, "target_path") else "", lookup_components)
        if src_comp and tgt_comp and src_comp != tgt_comp:
            pair = tuple(sorted([src_comp, tgt_comp]))
            cross_edges[pair] += 1

    primary = components[0]
    diagrams.append(DiagramSuggestion(
        slug=f"{primary.component_id}-boundary-map",
        title=f"{primary.label} Boundary and Ownership Map",
        description=f"Show what {primary.label} owns, what depends on it ({primary.n_inbound} inbound imports), and where its contract ends",
    ))

    if cross_edges:
        top_pair = cross_edges.most_common(1)[0]
        (comp_a, comp_b), edge_count = top_pair
        label_a = next((c.label for c in lookup_components if c.component_id == comp_a), comp_a)
        label_b = next((c.label for c in lookup_components if c.component_id == comp_b), comp_b)
        diagrams.append(DiagramSuggestion(
            slug=f"{repo_slug}-{comp_a}-{comp_b}-dependency",
            title=f"{label_a} \u2194 {label_b} Dependency Map",
            description=f"{edge_count} import edges connect these two boundaries — diagramming them makes the coupling visible",
        ))

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


def _backlog_detail_payload(ws: WorkstreamSuggestion) -> dict[str, str]:
    return {
        "problem": ws.description,
        "customer": "Maintainers and operators deciding whether this repo slice needs governed follow-up.",
        "opportunity": f"Turn {ws.title} into tracked Radar truth with explicit validation and ownership.",
        "product-view": "Odylith show should only create backlog records that are immediately usable, not title-only placeholders.",
        "success-metrics": (
            f"- Radar contains a grounded workstream for {ws.title}.\n"
            "- A maintainer can bind or decline the workstream without rewriting its core narrative."
        ),
    }


def format_text(result: ShowResult) -> str:
    """Render the trust-first `odylith show` action report."""
    lines: list[str] = []
    scenario = result.scenario or _select_show_scenario(result)

    lines.append(_scenario_status_line(result, scenario))
    teaching = _scenario_teaching_line(scenario)
    if teaching:
        lines.append(teaching)
    cheatsheet_hint = _scenario_cheatsheet_hint(scenario)
    if cheatsheet_hint:
        lines.append(cheatsheet_hint)
    summary = _creation_summary(result)
    if summary:
        lines.append(f"It found {summary} it can create from this scan. Nothing changed yet.")
    best_first_move = _best_first_move(result)
    if best_first_move:
        lines.append("")
        lines.extend(best_first_move)
    elif not _has_candidates(result):
        lines.append(_prompt_line(_custom_slice_prompt(result)))
    if _has_candidates(result):
        lines.append("")

    if result.components:
        n = len(result.components)
        lines.append(f"### Registry candidates - {n} logical component{'s' if n != 1 else ''}")
        lines.append("")
        for comp in result.components:
            posture = result.component_postures.get(comp.component_id)
            metric = _short_metric(comp, posture)
            lines.append(f"- **{comp.label}**: {metric}.")
            if comp.path:
                lines.append(
                    f"  Defines: a logical Registry component; `{comp.path}` is evidence, not the boundary itself."
                )
            else:
                lines.append("  Defines: a logical Registry component from scan evidence.")
            evidence = _component_evidence(comp)
            if evidence:
                lines.append(f"  Evidence: {evidence}")
            lines.append(_prompt_line(f"Define the {comp.label} Registry component."))
        lines.append("")

    if result.workstreams:
        lines.append(
            f"### Radar candidates - {len(result.workstreams)} "
            f"workstream{'s' if len(result.workstreams) != 1 else ''}"
        )
        lines.append("")
        for ws in result.workstreams:
            lines.append(f"- **{ws.title}**")
            lines.append(f"  Why: {ws.description}")
            lines.append(_prompt_line(f"Open a Radar workstream for {ws.title}."))
        lines.append("")

    if result.diagrams:
        lines.append("### Atlas candidates")
        lines.append("")
        for d in result.diagrams:
            lines.append(f"- **{d.title}**")
            lines.append(f"  Why: {d.description}")
            lines.append(_prompt_line(_atlas_prompt(d)))
        lines.append("")

    if result.issues:
        lines.append(f"### Issues - {len(result.issues)} worth tracking")
        lines.append("")
        for issue in result.issues:
            sev = f" [{issue.severity}]" if issue.severity != "medium" else ""
            lines.append(f"- **{issue.title}**{sev}")
            lines.append(f"  {issue.detail}")
            lines.append(
                _prompt_line(
                    f"Capture a Casebook bug for {issue.title}. Evidence: <paste failing command and error>."
                )
            )
        lines.append("")

    lines.append("No files changed.")

    return "\n".join(lines)


def _has_candidates(result: ShowResult) -> bool:
    return bool(result.components or result.workstreams or result.diagrams or result.issues)


def _select_show_scenario(result: ShowResult) -> str:
    app_modules = _effective_app_modules(result)
    if app_modules >= 3 and _has_candidates(result):
        return "app-ready"
    if app_modules >= 3 and any(result.already_governed.values()):
        return "already-governed"
    if app_modules >= 3:
        return "app-ready"
    if app_modules:
        return "thin-app"
    summary = result.source_summary
    if summary.support_modules or summary.test_modules:
        return "tests-only"
    non_app = bool(summary.support_modules or summary.test_modules)
    if summary.infra_files and not (
        non_app or summary.managed_files or summary.docs_files or summary.metadata_files
    ):
        return "infra-only"
    if summary.managed_files and not (
        non_app or summary.infra_files or summary.docs_files or summary.metadata_files
    ):
        return "managed-only"
    if summary.docs_files and not (
        non_app or summary.infra_files or summary.managed_files or summary.metadata_files
    ):
        return "docs-only"
    if summary.metadata_files:
        return "metadata-only"
    return "empty"


def _scenario_status_line(result: ShowResult, scenario: str) -> str:
    stack = " + ".join((result.identity.frameworks[:2] + result.identity.languages[:2])[:3])
    app_phrase = _count_phrase(_effective_app_modules(result), "app source file", "app source files")
    if scenario == "already-governed":
        covered = _covered_governance_phrase(result.already_governed)
        return f"Odylith read this repo: {app_phrase} found; existing {covered} already covers this scan."
    if scenario == "app-ready":
        stack_prefix = f"{stack}, " if stack else ""
        return f"Odylith read this repo: {stack_prefix}{app_phrase} found."
    if scenario == "thin-app":
        return (
            f"Odylith read this repo: {app_phrase} found, but not enough stable structure "
            "to infer a governance boundary yet."
        )
    if scenario == "tests-only":
        return "Odylith read this repo: tests/support source was found, but no application source was found."
    if scenario == "infra-only":
        return "Odylith read this repo: only infra/CI project assets were found; no application source was found."
    if scenario == "managed-only":
        return "Odylith read this repo: only Odylith-managed install/governance files were found; no application source was found."
    if scenario == "docs-only":
        return "Odylith read this repo: documentation was found, but no application source was found."
    if scenario == "metadata-only":
        prefix = f"{stack} metadata" if stack else "project metadata"
        return f"Odylith read this repo: {prefix} is present, but no application source was found."
    return "Odylith read this repo: no application source was found."


def _scenario_teaching_line(scenario: str) -> str:
    if scenario == "app-ready":
        return _APP_READY_TEACHING
    return _SCENARIO_TEACHING.get(scenario, "")


def _scenario_cheatsheet_hint(scenario: str) -> str:
    if scenario == "empty":
        return ""
    return _CHEATSHEET_HINT


def _effective_app_modules(result: ShowResult) -> int:
    if result.app_modules:
        return result.app_modules
    if not _has_candidates(result):
        return 0
    component_modules = sum(max(component.n_modules, 0) for component in result.components)
    return component_modules or result.total_modules


def _covered_governance_phrase(governed: dict[str, bool]) -> str:
    names = [
        label
        for key, label in (
            ("components", "Registry"),
            ("workstreams", "Radar"),
            ("diagrams", "Atlas"),
            ("bugs", "Casebook"),
            ("registry", "Registry"),
            ("backlog", "Radar"),
            ("atlas", "Atlas"),
            ("casebook", "Casebook"),
        )
        if governed.get(key)
    ]
    unique = list(dict.fromkeys(names))
    return _natural_join(unique) if unique else "governance"


def _custom_slice_prompt(result: ShowResult) -> str:
    if (result.scenario or _select_show_scenario(result)) == "already-governed":
        return "Define an Odylith plan around <path or feature> and connect it to existing Registry, Radar, and Atlas truth."
    return "Define an Odylith plan around <path or feature> and connect it to Registry, Radar, and Atlas."


def _next_prompt(result: ShowResult) -> str:
    if result.components:
        return f"Define the {result.components[0].label} Registry component."
    if result.diagrams:
        return _atlas_prompt(result.diagrams[0])
    if result.workstreams:
        return f"Open a Radar workstream for {result.workstreams[0].title}."
    if result.issues:
        return f"Capture a Casebook bug for {result.issues[0].title}. Evidence: <paste failing command and error>."
    return _custom_slice_prompt(result)


def _creation_summary(result: ShowResult) -> str:
    items: list[str] = []
    if result.components:
        items.append(_count_phrase(len(result.components), "Registry component", "Registry components"))
    if result.workstreams:
        items.append(_count_phrase(len(result.workstreams), "Radar workstream", "Radar workstreams"))
    if result.diagrams:
        items.append(_count_phrase(len(result.diagrams), "Atlas diagram", "Atlas diagrams"))
    if result.issues:
        items.append(_count_phrase(len(result.issues), "Casebook issue", "Casebook issues"))
    return _natural_join(items)


def _best_first_move(result: ShowResult) -> list[str]:
    if result.components:
        comp = result.components[0]
        metric = _short_metric(comp, result.component_postures.get(comp.component_id))
        lines = [f"Best first move: **{comp.label} Registry component**."]
        lines.append(
            f"Why: {metric}; defining this logical boundary gives future changes a safer ownership anchor."
        )
        lines.append(_prompt_line(f"Define the {comp.label} Registry component."))
        return lines
    if result.diagrams:
        diagram = result.diagrams[0]
        lines = [f"Best first move: **{diagram.title}**."]
        lines.append(f"Why: {diagram.description}")
        lines.append(_prompt_line(_atlas_prompt(diagram)))
        return lines
    if result.workstreams:
        workstream = result.workstreams[0]
        lines = [f"Best first move: **{workstream.title}**."]
        lines.append(f"Why: {workstream.description}")
        lines.append(_prompt_line(f"Open a Radar workstream for {workstream.title}."))
        return lines
    if result.issues:
        issue = result.issues[0]
        lines = [f"Best first move: **{issue.title}**."]
        lines.append(f"Why: {issue.detail}")
        lines.append(
            _prompt_line(
                f"Capture a Casebook bug for {issue.title}. Evidence: <paste failing command and error>."
            )
        )
        return lines
    return []


def _atlas_prompt(diagram: DiagramSuggestion) -> str:
    return f"Create the {diagram.title} Atlas diagram."


def _count_phrase(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _natural_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _prompt_line(prompt: str) -> str:
    return f"  Prompt: `{_inline_code(prompt)}`"


def _inline_code(value: str) -> str:
    return str(value).replace("`", "'")


def _component_evidence(comp: ComponentSuggestion) -> str:
    evidence = [str(item).strip() for item in comp.evidence if str(item).strip()]
    if not evidence:
        if comp.path and comp.n_modules:
            evidence.append(f"{comp.n_modules} source files anchored at `{comp.path}`")
        elif comp.path:
            evidence.append(f"anchor path `{comp.path}`")
        if comp.n_inbound:
            evidence.append(_import_count(comp.n_inbound, "inbound"))
        if comp.n_outbound:
            evidence.append(_import_count(comp.n_outbound, "outbound"))
    return "; ".join(evidence[:4]) + ("." if evidence else "")


def _import_count(count: int, direction: str) -> str:
    noun = "import" if count == 1 else "imports"
    return f"{count} {direction} {noun}"


def _short_metric(comp: ComponentSuggestion, posture: ComponentPosture | None) -> str:
    """One short right-aligned metric string for a component."""
    parts: list[str] = []
    if comp.n_inbound > 20:
        parts.append(f"{comp.n_inbound} dependents")
    elif comp.n_inbound > 0:
        parts.append(f"{comp.n_inbound} dependents")

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
    scenario = result.scenario or _select_show_scenario(result)
    payload: dict[str, Any] = {
        "identity": {
            "name": result.identity.name,
            "description": result.identity.description,
            "languages": result.identity.languages,
            "frameworks": result.identity.frameworks,
            "monorepo": result.identity.monorepo,
        },
        "scenario": scenario,
        "teaching": _scenario_teaching_line(scenario),
        "cheatsheet_hint": _scenario_cheatsheet_hint(scenario),
        "next_prompt": _next_prompt(result),
        "total_modules": result.total_modules,
        "app_modules": result.app_modules,
        "support_modules": result.support_modules,
        "source_summary": dict(vars(result.source_summary)),
        "already_governed": result.already_governed,
        "components": [
            {
                "component_id": c.component_id,
                "label": c.label,
                "path": c.path,
                "description": c.description,
                "member_paths": list(c.member_paths),
                "evidence": list(c.evidence),
                "confidence": c.confidence,
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
        "workstreams": [
            {"title": w.title, "description": w.description, "confidence": w.confidence}
            for w in result.workstreams
        ],
        "diagrams": [
            {"slug": d.slug, "title": d.title, "description": d.description, "confidence": d.confidence}
            for d in result.diagrams
        ],
        "issues": [
            {"title": i.title, "detail": i.detail, "severity": i.severity, "confidence": i.confidence}
            for i in result.issues
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=False)


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
            command = ["odylith", "backlog", "create", "--repo-root", str(repo_root), "--title", ws.title]
            for key, value in _backlog_detail_payload(ws).items():
                command.extend([f"--{key}", value])
            r = subprocess.run(command, capture_output=True, text=True, cwd=str(repo_root), timeout=30)
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
