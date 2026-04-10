from __future__ import annotations


_ZERO_SUPPORT_DOC_EXPANSION_FAMILIES = frozenset(
    {
        "component_governance",
        "context_engine_grounding",
        "compass_brief_freshness",
        "consumer_profile_compatibility",
        "cross_file_feature",
        "daemon_security",
        "exact_anchor_recall",
        "explicit_workstream",
        "governed_surface_sync",
        "live_proof_discipline",
        "orchestration_feedback",
        "orchestration_intelligence",
    }
)

_CURATED_DOC_OVERRIDE_FAMILIES = frozenset(
    {
        *_ZERO_SUPPORT_DOC_EXPANSION_FAMILIES,
        "cross_surface_governance_sync",
        "live_proof_discipline",
        "release_publication",
    }
)

_REQUIRED_DOC_ANCHOR_FAMILIES = frozenset(
    {
        *_CURATED_DOC_OVERRIDE_FAMILIES,
        "architecture",
    }
)


def _normalized_family(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def family_zero_support_doc_expansion(family: str) -> bool:
    return _normalized_family(family) in _ZERO_SUPPORT_DOC_EXPANSION_FAMILIES


def family_uses_curated_doc_overrides(family: str) -> bool:
    return _normalized_family(family) in _CURATED_DOC_OVERRIDE_FAMILIES


def family_anchors_all_required_docs(family: str) -> bool:
    return _normalized_family(family) in _REQUIRED_DOC_ANCHOR_FAMILIES


def support_doc_family_rank(*, path: str, family: str) -> int:
    lowered = str(path or "").strip().lower()
    normalized_family = _normalized_family(family)
    if not lowered or not normalized_family:
        return 9
    if normalized_family == "architecture":
        if lowered.endswith("/current_spec.md"):
            return 0
        if lowered.endswith("/maintainer_release_runbook.md") or lowered.endswith("/install_and_upgrade_runbook.md"):
            return 1
        if lowered == "readme.md" or lowered.endswith("/readme.md"):
            return 2
        return 4
    if normalized_family == "component_governance":
        if lowered.endswith("/current_spec.md") or lowered.endswith("/component_registry.v1.json"):
            return 0
        if lowered.endswith("/atlas/source/catalog/diagrams.v1.json") or (
            lowered.endswith(".mmd") and "/atlas/source/" in lowered
        ):
            return 1
        return 4
    if normalized_family == "context_engine_grounding":
        if lowered.endswith("/runtime/context_engine_operations.md"):
            return 0
        if lowered.endswith("/components/odylith-context-engine/current_spec.md"):
            return 1
        if lowered.endswith("/atlas/source/odylith-context-and-agent-execution-stack.mmd"):
            return 2
        return 4
    if normalized_family == "compass_brief_freshness":
        if lowered.endswith("/components/compass/current_spec.md"):
            return 0
        if lowered.endswith("/product_surfaces_and_runtime.md"):
            return 1
        return 4
    if normalized_family == "consumer_profile_compatibility":
        if lowered == "odylith/agents.md" or lowered.endswith("/odylith/agents.md"):
            return 0
        if lowered.endswith("/components/odylith/current_spec.md"):
            return 1
        if lowered.endswith("/components/registry/current_spec.md"):
            return 2
        if lowered.endswith("/component_registry.v1.json"):
            return 6
        return 4
    if normalized_family == "governed_surface_sync":
        if lowered.endswith("/surfaces/governance_surfaces.md") or lowered.endswith("/runtime/context_engine_operations.md"):
            return 0
        if lowered.endswith("/radar/source/index.md"):
            return 1
        return 4
    if normalized_family == "live_proof_discipline":
        if lowered.endswith("/components/proof-state/current_spec.md"):
            return 0
        if "/casebook/bugs/" in lowered or "/technical-plans/" in lowered:
            return 1
        if lowered.endswith("/delivery_intelligence.v4.json"):
            return 2
        return 4
    if normalized_family == "cross_surface_governance_sync":
        if lowered.endswith("/component_registry.v1.json") or lowered.endswith("/atlas/source/catalog/diagrams.v1.json"):
            return 0
        if lowered.endswith("/index.md"):
            return 1
        if "/radar/source/ideas/" in lowered:
            return 3
        return 4
    if normalized_family == "daemon_security":
        if lowered.endswith("/odylith_context_engine.md"):
            return 0
        if lowered.endswith("/components/odylith-context-engine/current_spec.md"):
            return 1
        return 4
    if normalized_family in {
        "cross_file_feature",
        "exact_anchor_recall",
        "explicit_workstream",
        "orchestration_feedback",
        "orchestration_intelligence",
    }:
        if lowered.endswith("/skill.md"):
            return 0
        if lowered.endswith("/tribunal_and_remediation.md"):
            return 1
        return 4
    if normalized_family == "release_publication":
        if lowered.endswith("/release-baselines.v1.json"):
            return 0
        if lowered.endswith("/current_spec.md"):
            return 1
        if lowered.endswith("/reviewer_guide.md") or lowered.endswith("/metrics_and_priorities.md"):
            return 1
        if lowered == "readme.md" or lowered.endswith("/readme.md"):
            return 2
        if lowered.endswith("/release_benchmarks.md"):
            return 3
        if lowered.endswith("/maintainer_release_runbook.md"):
            return 4
        if lowered.endswith("/skill.md"):
            return 5
        return 3
    if normalized_family == "browser_surface_reliability":
        if lowered.endswith("/index.html") or lowered.endswith("/compass.html"):
            return 0
        if lowered.endswith("/current_spec.md"):
            return 1
        return 3
    return 9


__all__ = [
    "family_anchors_all_required_docs",
    "family_uses_curated_doc_overrides",
    "family_zero_support_doc_expansion",
    "support_doc_family_rank",
]
