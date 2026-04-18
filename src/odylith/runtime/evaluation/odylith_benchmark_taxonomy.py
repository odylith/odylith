"""Odylith Benchmark Taxonomy helpers for the Odylith evaluation layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class BenchmarkFamilyGroup:
    key: str
    label: str
    description: str
    families: tuple[str, ...]


FAMILY_GROUPS: tuple[BenchmarkFamilyGroup, ...] = (
    BenchmarkFamilyGroup(
        key="bug_fixes",
        label="Bug Fixes",
        description="Validator-backed repair work where the agent has to localize and fix a concrete defect.",
        families=(
            "validation_heavy_fix",
            "stateful_bug_recovery",
            "browser_surface_reliability",
            "cli_contract_regression",
        ),
    ),
    BenchmarkFamilyGroup(
        key="multi_file_features",
        label="Multi-File Features",
        description="Implementation-heavy feature work spanning multiple files or owners.",
        families=("cross_file_feature", "merge_heavy_change", "api_contract_evolution"),
    ),
    BenchmarkFamilyGroup(
        key="runtime_install_security",
        label="Runtime / Install / Security",
        description="Developer-facing runtime, activation, upgrade, and security-sensitive repair work.",
        families=(
            "install_upgrade_runtime",
            "agent_activation",
            "daemon_security",
            "consumer_profile_compatibility",
            "external_dependency_recovery",
            "runtime_state_integrity",
        ),
    ),
    BenchmarkFamilyGroup(
        key="surface_ui_reliability",
        label="Surface / UI Reliability",
        description="Shell and Compass surface work where the product behavior must stay reliable for operators.",
        families=("dashboard_surface", "compass_brief_freshness"),
    ),
    BenchmarkFamilyGroup(
        key="docs_code_closeout",
        label="Docs + Code Closeout",
        description="Real closeout work where code, docs, specs, and mirrors have to agree.",
        families=("docs_code_closeout", "governed_surface_sync", "cross_surface_governance_sync"),
    ),
    BenchmarkFamilyGroup(
        key="governance_release_integrity",
        label="Governance / Release Integrity",
        description="Benchmark, Registry, Atlas, release-proof, and live-proof integrity work.",
        families=(
            "component_governance",
            "destructive_scope_control",
            "live_proof_discipline",
            "release_publication",
        ),
    ),
    BenchmarkFamilyGroup(
        key="architecture_review",
        label="Architecture Review",
        description="Grounded design and topology review rather than direct implementation.",
        families=("architecture",),
    ),
    BenchmarkFamilyGroup(
        key="grounding_orchestration_control",
        label="Grounding / Orchestration Control",
        description="Control-plane and narrowing discipline families that explain how Odylith stays bounded.",
        families=(
            "broad_shared_scope",
            "context_engine_grounding",
            "execution_engine",
            "guidance_behavior",
            "agent_operating_character",
            "exact_path_ambiguity",
            "exact_anchor_recall",
            "explicit_workstream",
            "retrieval_miss_recovery",
            "orchestration_feedback",
            "orchestration_intelligence",
        ),
    ),
)


_FAMILY_GROUP_BY_FAMILY = {
    family: group
    for group in FAMILY_GROUPS
    for family in group.families
}

_FAMILY_ORDER = {
    family: (group_index, family_index)
    for group_index, group in enumerate(FAMILY_GROUPS)
    for family_index, family in enumerate(group.families)
}


def family_group_label(family: str) -> str:
    family_key = str(family or "").strip()
    group = _FAMILY_GROUP_BY_FAMILY.get(family_key)
    if group is None:
        return "Other"
    return group.label


def family_group_description(family: str) -> str:
    family_key = str(family or "").strip()
    group = _FAMILY_GROUP_BY_FAMILY.get(family_key)
    if group is None:
        return ""
    return group.description


def ordered_family_names(families: Iterable[str]) -> list[str]:
    normalized = sorted({str(token or "").strip() for token in families if str(token or "").strip()})
    return sorted(
        normalized,
        key=lambda family: (
            _FAMILY_ORDER.get(family, (len(FAMILY_GROUPS), 0))[0],
            _FAMILY_ORDER.get(family, (len(FAMILY_GROUPS), 0))[1],
            family,
        ),
    )
