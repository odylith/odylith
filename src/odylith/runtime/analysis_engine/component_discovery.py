"""Component boundary discovery from import graph topology.

Groups source artifacts into components using directory structure, filename
prefix frequency analysis, and graph-based merging. Ranks components by
import centrality and computes software engineering metrics.

No domain-specific knowledge — works on any codebase.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from odylith.runtime.analysis_engine.types import (
    ComponentSuggestion,
    ImportArtifact,
    ImportEdge,
    humanize,
    slugify,
)
from odylith.runtime.analysis_engine.repo_analysis import infer_label


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

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

    module_prefix = _find_common_prefix(source_arts)
    component_groups = _group_into_components(source_arts, module_prefix)
    merged_groups = _merge_small_groups(component_groups, edges, min_size=5)
    inbound, outbound, internal = _count_cross_component_edges(edges, merged_groups)

    return _build_component_suggestions(
        merged_groups, inbound, outbound, internal, module_prefix, repo_root,
    )


# ---------------------------------------------------------------------------
# Prefix detection
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------

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

    result: dict[str, list[ImportArtifact]] = {}
    for name, arts in raw.items():
        if name.startswith("__"):
            result[name] = arts
            continue
        if len(arts) > 15:
            # Strategy 1: split by subdirectory
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
                # Strategy 2: split by filename prefix frequency
                prefix_groups = _group_by_filename_prefix(arts)
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
) -> dict[str, list[ImportArtifact]]:
    """Group flat-directory files by common filename prefix using frequency analysis."""
    filenames = [Path(art.path).stem for art in artifacts]
    prefix_map = _refine_prefixes_by_frequency(filenames)

    groups: dict[str, list[ImportArtifact]] = {}
    for art, fname in zip(artifacts, filenames):
        prefix = prefix_map.get(fname, fname.split("_")[0])
        groups.setdefault(prefix, []).append(art)

    # Merge tiny groups into "core"
    merged: dict[str, list[ImportArtifact]] = {}
    other: list[ImportArtifact] = []
    for prefix, arts in groups.items():
        if len(arts) >= 2:
            merged[prefix] = arts
        else:
            other.extend(arts)
    if other:
        merged["core"] = merged.get("core", []) + other

    if len(merged) >= 2:
        return merged
    return {}


def _refine_prefixes_by_frequency(filenames: list[str]) -> dict[str, str]:
    """Pick the best grouping prefix per filename via frequency analysis.

    A 2-word prefix wins over 1-word if it groups 3+ files and the 1-word
    prefix is overly broad (> 60% of all files).
    """
    total = len(filenames)
    if total < 4:
        return {f: f.split("_")[0] if "_" in f else f for f in filenames}

    one_word: Counter[str] = Counter()
    two_word: Counter[str] = Counter()
    for f in filenames:
        parts = f.split("_")
        if parts:
            one_word[parts[0]] += 1
        if len(parts) >= 2:
            two_word[f"{parts[0]}_{parts[1]}"] += 1

    result: dict[str, str] = {}
    for f in filenames:
        parts = f.split("_")
        p1 = parts[0] if parts else f
        p2 = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else ""
        if p2 and two_word.get(p2, 0) >= 3 and one_word.get(p1, 0) > total * 0.5:
            result[f] = p2
        else:
            result[f] = p1
    return result


# ---------------------------------------------------------------------------
# Graph-based merging
# ---------------------------------------------------------------------------

def _merge_small_groups(
    groups: dict[str, list[ImportArtifact]],
    edges: list[ImportEdge],
    min_size: int = 5,
) -> dict[str, list[ImportArtifact]]:
    """Merge groups under min_size into their most-connected neighbor by edge count."""
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
        small = [n for n, a in merged.items() if len(a) < min_size and not n.startswith("__")]
        for name in small:
            neighbors: Counter[str] = Counter()
            for (a, b), count in cross.items():
                if a == name and b in merged and b != name:
                    neighbors[b] += count
            if not neighbors:
                parent = name.rsplit("/", 1)[0] if "/" in name else ""
                candidates = [k for k in merged if k != name and k.startswith(parent + "/")]
                if candidates:
                    target = candidates[0]
                else:
                    continue
            else:
                target = neighbors.most_common(1)[0][0]
            merged[target] = merged[target] + merged.pop(name)
            for a in merged[target]:
                path_to_group[a.path] = target
            changed = True
            break
    return merged


# ---------------------------------------------------------------------------
# Edge counting
# ---------------------------------------------------------------------------

def _count_cross_component_edges(
    edges: list[ImportEdge],
    groups: dict[str, list[ImportArtifact]],
) -> tuple[Counter[str], Counter[str], Counter[str]]:
    """Count inbound, outbound, and internal import edges per component."""
    path_to_comp: dict[str, str] = {}
    for comp_name, arts in groups.items():
        for a in arts:
            path_to_comp[a.path] = comp_name

    inbound: Counter[str] = Counter()
    outbound: Counter[str] = Counter()
    internal: Counter[str] = Counter()
    for edge in edges:
        src = path_to_comp.get(edge.source_path, "__external__")
        tgt = path_to_comp.get(edge.target_path, "__external__")
        if src == tgt:
            internal[src] += 1
        else:
            outbound[src] += 1
            inbound[tgt] += 1
    return inbound, outbound, internal


# ---------------------------------------------------------------------------
# Component suggestion building
# ---------------------------------------------------------------------------

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
        ((n, a) for n, a in groups.items() if n not in skip and not n.startswith("__")),
        key=lambda x: -(inbound[x[0]] + len(x[1])),
    )

    components: list[ComponentSuggestion] = []
    for comp_name, comp_arts in ranked[:12]:
        if not comp_name:
            continue

        path_parts = comp_name.split("/")
        rel_path = f"{module_prefix}/{comp_name}" if module_prefix else comp_name
        meaningful_parts = [p for p in path_parts if p and p.lower() not in ("core", "")]
        comp_id = slugify(meaningful_parts[-1] if meaningful_parts else comp_name)

        label = _label_from_path_parts(path_parts)
        if label in seen_labels:
            disambig = ""
            for part in reversed(meaningful_parts):
                candidate = humanize(part)
                if candidate.lower() != label.lower() and candidate.lower() not in label.lower():
                    disambig = candidate
                    break
            label = f"{disambig} {label}" if disambig else humanize(" ".join(meaningful_parts)) if meaningful_parts else f"{label} ({comp_id})"
        seen_labels.add(label)

        n_mod = len(comp_arts)
        n_in, n_out, n_int = inbound[comp_name], outbound[comp_name], internal[comp_name]
        instability = n_out / max(n_in + n_out, 1)
        cohesion = n_int / max(n_in + n_out + n_int, 1)

        desc = _build_description(n_mod, n_in, n_out, n_int, instability, cohesion)
        components.append(ComponentSuggestion(
            component_id=comp_id, label=label, path=rel_path,
            description=desc, n_modules=n_mod, n_inbound=n_in, n_outbound=n_out,
        ))

    return components


def _label_from_path_parts(parts: list[str]) -> str:
    """Infer label from path parts, most specific first. No domain knowledge."""
    generic = {"core", "main", "base", "default", "internal", "src", "lib", ""}
    for part in reversed(parts):
        if part.lower() in generic:
            continue
        label = infer_label(part, [], [])
        if label != humanize(part):
            return label
    meaningful = [p for p in parts if p.lower() not in generic]
    if len(meaningful) >= 2:
        return f"{humanize(meaningful[-1])} {humanize(meaningful[0])}"
    if meaningful:
        return humanize(meaningful[0])
    return humanize(parts[0]) if parts else "Unknown"


def _build_description(
    n_mod: int, n_in: int, n_out: int, n_int: int,
    instability: float, cohesion: float,
) -> str:
    """One key architectural insight per component."""
    if instability < 0.2 and n_in > 20:
        role = f"stable foundation — {n_in} modules depend on it, changes here ripple everywhere"
    elif instability < 0.2 and n_in > 5:
        role = f"stable core — {n_in} dependents, low churn risk"
    elif instability > 0.8 and n_out > 5:
        role = f"edge consumer — depends on {n_out} others, absorbs upstream changes"
    elif 0.3 < instability < 0.7 and n_in > 3 and n_out > 3:
        role = f"integration layer — {n_in} dependents, {n_out} dependencies"
    elif n_in > 10:
        role = f"{n_in} modules depend on it"
    elif n_in > 0:
        role = f"{n_in} dependents"
    elif n_out > 5:
        role = f"depends on {n_out} other modules"
    else:
        role = "self-contained"
    if cohesion > 0.7 and n_int > 5:
        role += ", highly cohesive"
    return f"{n_mod} modules. {role}"
