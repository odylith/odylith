from __future__ import annotations

from typing import Any


def bind(host: Any) -> None:
    getter = host.__getitem__ if isinstance(host, dict) else lambda name: getattr(host, name)
    for name in ('Any', 'Mapping', 'Path', 'Sequence', '_COMPANION_CONTEXT_RULES', '_TOPOLOGY_DOMAIN_RULES', '_architecture_rule_matches_path', '_broad_shared_only_input', '_cached_projection_rows', '_companion_context_paths_for_normalized_changed_paths', '_component_matches_changed_path', '_connect', '_dedupe_strings', '_delivery_profile_hot_path', '_entity_by_kind_id', '_normalize_repo_token', '_normalized_watch_path', '_path_match_type', '_path_touches_watch', '_runtime_enabled', '_warm_runtime', 'component_registry', 'governance', 'is_component_spec_path', 'odylith_context_cache', 'odylith_context_engine_grounding_runtime', 'projection_snapshot_path'):
        try:
            globals()[name] = getter(name)
        except (AttributeError, KeyError):
            continue


def _governance_surface_refs(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    workstream_ids: Sequence[str],
    component_ids: Sequence[str],
) -> dict[str, Any]:
    impact = governance.build_dashboard_impact(
        repo_root=repo_root,
        changed_paths=changed_paths,
        force=False,
        impact_mode="auto",
    ).as_dict()
    reasons = dict(impact.get("reasons", {})) if isinstance(impact.get("reasons"), Mapping) else {}
    if workstream_ids:
        impact["radar"] = True
        reasons.setdefault("radar", []).append("explicit_workstream_seed")
    if component_ids:
        impact["registry"] = True
        reasons.setdefault("registry", []).append("explicit_component_seed")
    impact["tooling_shell"] = bool(
        impact.get("tooling_shell")
        or impact.get("radar")
        or impact.get("atlas")
        or impact.get("compass")
        or impact.get("registry")
        or impact.get("casebook")
    )
    return {
        "impacted_surfaces": {
            key: bool(impact.get(key))
            for key in ("radar", "atlas", "compass", "registry", "casebook", "tooling_shell")
        },
        "reasons": {
            key: _dedupe_strings(str(token).strip() for token in value)
            for key, value in reasons.items()
            if isinstance(value, list)
        },
    }

def _governance_closeout_docs(
    *,
    docs: Sequence[str],
    workstream_details: Sequence[Mapping[str, Any]],
    component_details: Sequence[Mapping[str, Any]],
) -> list[str]:
    rows = [str(token).strip() for token in docs if str(token).strip()]
    for detail in workstream_details:
        rows.append(str(detail.get("idea_file", "")).strip())
        rows.append(str(detail.get("promoted_to_plan", "")).strip())
    for detail in component_details:
        traceability = dict(detail.get("traceability", {})) if isinstance(detail.get("traceability"), Mapping) else {}
        rows.extend(
            str(token).strip()
            for bucket in ("runbooks", "developer_docs", "code_references")
            for token in traceability.get(bucket, [])
            if isinstance(traceability.get(bucket), list) and str(token).strip()
        )
        component_entry = detail.get("component")
        if isinstance(component_entry, component_registry.ComponentEntry):
            rows.append(str(component_entry.spec_ref).strip())
    return _dedupe_strings(row for row in rows if row)

def _bounded_explicit_governance_closeout_docs(
    *,
    repo_root: Path,
    docs: Sequence[str],
    enabled: bool,
) -> list[str]:
    if not enabled:
        return [str(token).strip() for token in docs if str(token).strip()]
    return []

def _governance_state_actions(
    *,
    governed_surface_sync_required: bool,
    plan_binding_required: bool,
    diagram_watch_gaps: Sequence[Mapping[str, Any]],
    full_scan_recommended: bool,
) -> list[str]:
    actions: list[str] = []
    if plan_binding_required:
        actions.append("validate_plan_workstream_binding")
    if governed_surface_sync_required:
        actions.append("sync_workstream_artifacts")
    if diagram_watch_gaps:
        actions.append("read_required_diagrams")
    if full_scan_recommended:
        actions.append("widen_to_direct_reads")
    return actions

def _component_governance_doc_only_slice(changed_paths: Sequence[str]) -> bool:
    normalized_paths = [str(token).strip() for token in changed_paths if str(token).strip()]
    if not normalized_paths:
        return False
    allowed_prefixes = (
        "odylith/registry/source/",
        "odylith/atlas/source/",
        "odylith/maintainer/",
        "docs/benchmarks/",
        "tests/unit/runtime/",
    )
    allowed_exact = {"README.md"}
    return all(
        path in allowed_exact or path.startswith(allowed_prefixes)
        for path in normalized_paths
    )

def _governance_requires_architecture_audit(
    *,
    changed_paths: Sequence[str],
    family_hint: str,
) -> bool:
    family = str(family_hint or "").strip().lower()
    if family == "architecture":
        return True
    normalized_paths = [str(token).strip() for token in changed_paths if str(token).strip()]
    if not normalized_paths:
        return False
    if family == "component_governance" and _component_governance_doc_only_slice(normalized_paths):
        return False
    high_risk_prefixes = (
        "app/",
        "infra/",
        "services/",
        "odylith/atlas/",
    )
    high_risk_paths = {
        "agents-guidelines/ARCHITECTURE.MD",
        "agents-guidelines/INVARIANTS.MD",
    }
    return any(
        path.startswith(high_risk_prefixes) or path in high_risk_paths
        for path in normalized_paths
    )


def _governance_can_skip_runtime_warmup(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    workstream_hint: str,
    component_hint: str,
    runtime_mode: str,
    delivery_profile: str,
    family_hint: str,
    use_working_tree: bool,
    claimed_paths: Sequence[str],
) -> bool:
    if not _delivery_profile_hot_path(delivery_profile):
        return False
    if str(runtime_mode or "").strip().lower() not in {"", "auto", "local"}:
        return False
    if use_working_tree or any(str(token).strip() for token in claimed_paths):
        return False
    if not str(workstream_hint or "").strip() and not str(component_hint or "").strip():
        return False
    root = Path(repo_root).resolve()
    normalized_changed = [
        _normalize_repo_token(str(token).strip(), repo_root=root)
        for token in changed_paths
        if str(token).strip()
    ]
    if not normalized_changed or _broad_shared_only_input(normalized_changed):
        return False
    family = str(family_hint or "").strip().lower().replace("-", "_")
    if family not in {
        "agent_activation",
        "component_governance",
        "cross_surface_governance_sync",
        "daemon_security",
        "explicit_workstream",
        "install_upgrade_runtime",
        "release_publication",
    }:
        return False
    return projection_snapshot_path(repo_root=root).is_file()

def _governance_diagram_catalog_companions(
    *,
    changed_paths: Sequence[str],
    diagrams: Sequence[Mapping[str, Any]],
) -> list[str]:
    normalized_changed = [
        _normalize_repo_token(str(token), repo_root=Path("."))
        for token in changed_paths
        if str(token).strip()
    ]
    touches_atlas_source = any(path.startswith("odylith/atlas/source/") for path in normalized_changed)
    if not touches_atlas_source:
        touches_atlas_source = any(
            str(row.get("source_mmd", "")).strip().startswith("odylith/atlas/source/")
            for row in diagrams
            if isinstance(row, Mapping)
        )
    if not touches_atlas_source:
        return []
    return ["odylith/atlas/source/catalog/diagrams.v1.json"]

def _companion_context_paths_for_normalized_changed_paths(changed_paths: Sequence[str]) -> list[str]:
    normalized_changed = {
        _normalized_watch_path(str(token).strip())
        for token in changed_paths
        if str(token).strip()
    }
    companions: list[str] = []
    for rule in _COMPANION_CONTEXT_RULES:
        match_paths = {
            _normalized_watch_path(str(token).strip())
            for token in rule.get("match_paths", ())
            if str(token).strip()
        }
        match_prefixes = tuple(
            _normalized_watch_path(str(token).strip())
            for token in rule.get("match_prefixes", ())
            if str(token).strip()
        )
        if not any(
            path in match_paths or any(path.startswith(prefix) for prefix in match_prefixes)
            for path in normalized_changed
        ):
            continue
        companions.extend(
            _normalized_watch_path(str(token).strip())
            for token in rule.get("paths", ())
            if str(token).strip()
        )
    return _dedupe_strings(companions)

def _companion_context_paths(*, changed_paths: Sequence[str], repo_root: Path) -> list[str]:
    normalized_changed = [
        _normalize_repo_token(str(token).strip(), repo_root=repo_root)
        for token in changed_paths
        if str(token).strip()
    ]
    return _companion_context_paths_for_normalized_changed_paths(normalized_changed)

def _governance_hot_path_docs(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    family_hint: str,
    workstream_detail: Mapping[str, Any] | None,
) -> list[str] | None:
    root = Path(repo_root).resolve()
    normalized_changed = {
        _normalize_repo_token(str(token).strip(), repo_root=root)
        for token in changed_paths
        if str(token).strip()
    }
    family = str(family_hint or "").strip().lower()
    docs: list[str] = []
    strategy_applies = False

    touches_context_engine = any(
        path.startswith("src/odylith/runtime/context_engine/")
        or path.startswith("tests/unit/runtime/test_odylith_context_engine_")
        for path in normalized_changed
    )
    touches_install_agents = "src/odylith/install/agents.py" in normalized_changed
    touches_install_repair = "src/odylith/install/repair.py" in normalized_changed
    touches_install_runtime = bool(
        {"src/odylith/install/manager.py", "src/odylith/install/runtime.py"} & normalized_changed
    )
    touches_governance_sync = (
        "src/odylith/runtime/governance/sync_workstream_artifacts.py" in normalized_changed
        or {
            "odylith/radar/source/INDEX.md",
            "odylith/technical-plans/INDEX.md",
        }.issubset(normalized_changed)
    )
    touches_benchmark_corpus_sync = {
        "odylith/runtime/source/optimization-evaluation-corpus.v1.json",
        "src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json",
        "tests/unit/runtime/test_odylith_benchmark_corpus.py",
    }.issubset(normalized_changed)
    touches_benchmark_proof_lane = (
        "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd" in normalized_changed
    )
    touches_benchmark_component_honesty = {
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
    }.issubset(normalized_changed)
    touches_benchmark_docs_closeout = {
        "README.md",
        "docs/benchmarks/README.md",
        "docs/benchmarks/REVIEWER_GUIDE.md",
    }.issubset(normalized_changed)
    touches_benchmark_publication = touches_benchmark_proof_lane or any(
        path.startswith("src/odylith/runtime/evaluation/odylith_benchmark_")
        or path
        in {
            "README.md",
            "odylith/MAINTAINER_RELEASE_RUNBOOK.md",
            "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        }
        for path in normalized_changed
    )

    if family == "daemon_security" or touches_context_engine or touches_install_repair:
        strategy_applies = True
        docs.extend(
            [
                "odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md",
                "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
            ]
        )

    if family == "agent_activation" or touches_install_agents:
        strategy_applies = True
        docs.extend(
            [
                "odylith/AGENTS.md",
                "odylith/CLAUDE.md",
                "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
                "odylith/skills/subagent-orchestrator/SKILL.md",
            ]
        )

    if family == "install_upgrade_runtime" or (
        touches_install_runtime and not touches_install_agents and not touches_install_repair
    ):
        strategy_applies = True
        docs.extend(
            [
                "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
                "odylith/registry/source/components/release/CURRENT_SPEC.md",
                "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
            ]
        )

    if family == "cross_surface_governance_sync" and touches_benchmark_corpus_sync:
        strategy_applies = True
        docs.extend(
            [
                "tests/unit/runtime/test_hygiene.py",
                "odylith/radar/source/ideas/2026-03/2026-03-29-odylith-benchmark-anti-gaming-adversarial-corpus-integrity-and-independent-proof.md",
                "odylith/technical-plans/in-progress/2026-03/2026-03-31-odylith-raw-codex-baseline-and-four-lane-benchmark-table.md",
            ]
        )
    elif family == "cross_surface_governance_sync" or touches_governance_sync:
        strategy_applies = True
        docs.extend(
            [
                "odylith/atlas/source/catalog/diagrams.v1.json",
                "odylith/registry/source/component_registry.v1.json",
            ]
        )
        if isinstance(workstream_detail, Mapping):
            idea_file = str(workstream_detail.get("idea_file", "")).strip()
            if idea_file:
                docs.append(idea_file)

    if family == "release_publication":
        strategy_applies = True
        docs.extend(
            [
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
            ]
        )
    if family == "docs_code_closeout" and touches_benchmark_docs_closeout:
        strategy_applies = True
        docs.extend(
            [
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
            ]
        )
    elif touches_benchmark_publication:
        strategy_applies = True
        docs.append("odylith/registry/source/components/benchmark/CURRENT_SPEC.md")

    if family == "component_governance" and touches_benchmark_component_honesty:
        strategy_applies = True
        docs.extend(
            [
                "odylith/registry/source/component_registry.v1.json",
                "docs/benchmarks/README.md",
                "odylith/maintainer/skills/release-benchmark-publishing/SKILL.md",
            ]
        )
    elif family == "component_governance" or touches_benchmark_proof_lane:
        strategy_applies = True
        docs.extend(
            [
                "odylith/atlas/source/catalog/diagrams.v1.json",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            ]
        )

    if not strategy_applies:
        return None
    return _dedupe_strings(doc for doc in docs if doc and doc not in normalized_changed)

def _governance_explicit_slice_grounded(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    explicit_workstream: str,
    explicit_component: str,
    workstream_detail: Mapping[str, Any] | None,
    component_detail: Mapping[str, Any] | None,
    diagrams: Sequence[Mapping[str, Any]],
) -> bool:
    if explicit_workstream and not isinstance(workstream_detail, Mapping):
        return False
    if explicit_component and not isinstance(component_detail, Mapping):
        return False
    component_entry = component_detail.get("component") if isinstance(component_detail, Mapping) else None
    if (
        explicit_workstream
        and isinstance(component_entry, component_registry.ComponentEntry)
        and explicit_workstream
        not in {str(token).strip().upper() for token in component_entry.workstreams if str(token).strip()}
    ):
        return False

    root = Path(repo_root).resolve()
    normalized_changed = {
        _normalize_repo_token(str(token), repo_root=root)
        for token in changed_paths
        if str(token).strip()
    }
    direct_targets: set[str] = set()
    if explicit_component:
        direct_targets.add("odylith/registry/source/component_registry.v1.json")
    if isinstance(component_entry, component_registry.ComponentEntry):
        direct_targets.add(_normalize_repo_token(str(component_entry.spec_ref), repo_root=root))
    for row in diagrams:
        if not isinstance(row, Mapping):
            continue
        for key in ("source_mmd", "source_svg", "source_png", "path"):
            token = _normalize_repo_token(str(row.get(key, "")).strip(), repo_root=root)
            if token:
                direct_targets.add(token)
    return bool(normalized_changed.intersection(token for token in direct_targets if token))

def build_governance_slice(
    *,
    repo_root: Path,
    changed_paths: Sequence[str] = (),
    workstream: str = "",
    component: str = "",
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    delivery_profile: str = "full",
    family_hint: str = "",
    intent: str = "",
    validation_command_hints: Sequence[str] = (),
) -> dict[str, Any]:
    return odylith_context_engine_grounding_runtime.build_governance_slice(
        repo_root=repo_root,
        changed_paths=changed_paths,
        workstream=workstream,
        component=component,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=session_id,
        claimed_paths=claimed_paths,
        runtime_mode=runtime_mode,
        delivery_profile=delivery_profile,
        family_hint=family_hint,
        intent=intent,
        validation_command_hints=validation_command_hints,
    )

def select_impacted_diagrams(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    runtime_mode: str = "auto",
    skip_runtime_warmup: bool = False,
) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    if _runtime_enabled(runtime_mode) and not bool(skip_runtime_warmup):
        _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="diagram_select")
    connection = _connect(root)
    changed = [
        _normalize_repo_token(str(token).strip(), repo_root=root)
        for token in changed_paths
        if str(token).strip()
    ]
    results: dict[str, dict[str, Any]] = {}
    try:
        diagram_rows = _cached_projection_rows(
            repo_root=root,
            cache_name="diagram_rows",
            loader=lambda: [
                dict(row)
                for row in connection.execute(
                    "SELECT diagram_id, slug, title, source_mmd, source_svg, source_png, source_mmd_hash FROM diagrams"
                ).fetchall()
            ],
        )
        watch_rows = _cached_projection_rows(
            repo_root=root,
            cache_name="diagram_watch_rows",
            loader=lambda: [
                dict(row)
                for row in connection.execute(
                    "SELECT diagram_id, watch_path FROM diagram_watch_paths"
                ).fetchall()
            ],
        )
        watch_map: dict[str, list[str]] = {}
        for row in watch_rows:
            watch_map.setdefault(str(row.get("diagram_id", "")), []).append(str(row.get("watch_path", "")))
        for row in diagram_rows:
            diagram_id = str(row.get("diagram_id", ""))
            diagram_paths = watch_map.get(diagram_id, [])
            if not any(_path_touches_watch(changed_path=path, watch_path=watch) for path in changed for watch in diagram_paths):
                continue
            source_mmd = str(row.get("source_mmd", ""))
            source_svg = str(row.get("source_svg", ""))
            source_png = str(row.get("source_png", ""))
            direct_source_match = any(
                _path_match_type(changed_path=path, target_path=target_path) == "exact"
                for path in changed
                for target_path in (source_mmd, source_svg, source_png)
                if str(target_path).strip()
            )
            source_mmd_path = root / source_mmd if source_mmd and not Path(source_mmd).is_absolute() else Path(source_mmd)
            current_hash = odylith_context_cache.fingerprint_paths([source_mmd_path.resolve()]) if source_mmd_path.is_file() else ""
            needs_render = bool(current_hash and current_hash != str(row.get("source_mmd_hash", "")))
            results[diagram_id] = {
                "diagram_id": diagram_id,
                "slug": str(row.get("slug", "")),
                "title": str(row.get("title", "")),
                "source_mmd": source_mmd,
                "source_svg": source_svg,
                "source_png": source_png,
                "needs_render": needs_render,
                "direct_source_match": direct_source_match,
            }
    finally:
        connection.close()
    direct_source_matches = [row for row in results.values() if bool(row.get("direct_source_match"))]
    ordered = direct_source_matches if direct_source_matches else list(results.values())
    return [
        {
            key: value
            for key, value in row.items()
            if key != "direct_source_match"
        }
        for row in sorted(
            ordered,
            key=lambda row: (
                0 if bool(row.get("direct_source_match")) else 1,
                str(row.get("diagram_id", "")),
            ),
        )
    ]

def _path_touches_watch(*, changed_path: str, watch_path: str) -> bool:
    changed = _normalized_watch_path(str(changed_path))
    watch = _normalized_watch_path(str(watch_path))
    return changed == watch or changed.startswith(f"{watch}/") or watch.startswith(f"{changed}/")

def _normalized_watch_path(value: str) -> str:
    token = str(value or "").strip().replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    while "//" in token:
        token = token.replace("//", "/")
    return token.rstrip("/")

def _architecture_rule_matches_path(*, changed_path: str, watch_path: str) -> bool:
    return _path_touches_watch(changed_path=changed_path, watch_path=watch_path)

def _collect_topology_domains(
    *,
    changed_paths: Sequence[str],
    component_ids: Sequence[str],
) -> list[dict[str, Any]]:
    normalized_components = {str(token).strip() for token in component_ids if str(token).strip()}
    results: list[dict[str, Any]] = []
    for rule in _TOPOLOGY_DOMAIN_RULES:
        matched_paths = [
            str(path).strip()
            for path in changed_paths
            if str(path).strip()
            and any(
                _architecture_rule_matches_path(changed_path=str(path).strip(), watch_path=str(watch_path))
                for watch_path in rule.get("path_prefixes", ())
            )
        ]
        matched_components = [
            str(component_id).strip()
            for component_id in rule.get("components", ())
            if str(component_id).strip() in normalized_components
        ]
        if not matched_paths and not matched_components:
            continue
        results.append(
            {
                "domain_id": str(rule.get("domain_id", "")).strip(),
                "label": str(rule.get("label", "")).strip(),
                "summary": str(rule.get("summary", "")).strip(),
                "matched_paths": _dedupe_strings(matched_paths),
                "matched_components": _dedupe_strings(matched_components),
                "required_reads": _dedupe_strings(
                    [str(path).strip() for path in rule.get("required_reads", ()) if str(path).strip()]
                ),
                "checks": [str(check).strip() for check in rule.get("checks", ()) if str(check).strip()],
            }
        )
    return results

def _component_matches_changed_path(entity: Mapping[str, Any], changed_path: str) -> bool:
    metadata = entity.get("metadata", {})
    if not isinstance(metadata, Mapping):
        return False
    path_prefixes = metadata.get("path_prefixes", [])
    if not isinstance(path_prefixes, list):
        return False
    return any(
        _path_touches_watch(changed_path=changed_path, watch_path=str(prefix).strip())
        for prefix in path_prefixes
        if str(prefix).strip()
    )

def _load_architecture_diagrams(
    connection: Any,
    *,
    diagram_ids: Sequence[str],
    changed_paths: Sequence[str],
    component_diagram_map: Mapping[str, Sequence[str]],
    direct_diagram_ids: Sequence[str],
) -> list[dict[str, Any]]:
    ordered_diagram_ids = _dedupe_strings(diagram_ids)
    if not ordered_diagram_ids:
        return []
    watch_rows = connection.execute(
        "SELECT diagram_id, watch_path FROM diagram_watch_paths ORDER BY diagram_id, watch_path"
    ).fetchall()
    watch_map: dict[str, list[str]] = {}
    for row in watch_rows:
        watch_map.setdefault(str(row["diagram_id"]), []).append(str(row["watch_path"]))
    results: list[dict[str, Any]] = []
    direct_ids = set(str(token).strip() for token in direct_diagram_ids if str(token).strip())
    for diagram_id in ordered_diagram_ids:
        entity = _entity_by_kind_id(connection, kind="diagram", entity_id=diagram_id)
        if entity is None:
            continue
        watch_paths = watch_map.get(diagram_id, [])
        matched_paths = [
            str(path).strip()
            for path in changed_paths
            if any(_path_touches_watch(changed_path=str(path).strip(), watch_path=watch) for watch in watch_paths)
        ]
        related_components = [
            component_id
            for component_id, related_diagrams in component_diagram_map.items()
            if diagram_id in {str(token).strip() for token in related_diagrams if str(token).strip()}
        ]
        relation = "component_link"
        if diagram_id in direct_ids and related_components:
            relation = "direct_and_component_link"
        elif diagram_id in direct_ids:
            relation = "direct"
        results.append(
            {
                "diagram_id": str(entity.get("entity_id", "")).strip(),
                "title": str(entity.get("title", "")).strip(),
                "path": str(entity.get("path", "")).strip(),
                "relation": relation,
                "related_components": _dedupe_strings(related_components),
                "matched_paths": _dedupe_strings(matched_paths),
                "watch_paths": _dedupe_strings(watch_paths),
            }
        )
    return results

def _collect_diagram_watch_gaps(
    *,
    changed_paths: Sequence[str],
    component_entities: Sequence[Mapping[str, Any]],
    linked_diagrams: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    watched_by_path: dict[str, list[str]] = {}
    for row in linked_diagrams:
        diagram_id = str(row.get("diagram_id", "")).strip()
        for matched_path in row.get("matched_paths", []):
            token = str(matched_path).strip()
            if not token:
                continue
            watched_by_path.setdefault(token, []).append(diagram_id)
    gaps: list[dict[str, Any]] = []
    for changed_path in changed_paths:
        token = str(changed_path).strip()
        if not token or watched_by_path.get(token):
            continue
        matched_components = [
            str(entity.get("entity_id", "")).strip()
            for entity in component_entities
            if _component_matches_changed_path(entity, token)
        ]
        linked_diagram_ids = _dedupe_strings(
            [
                str(diagram.get("diagram_id", "")).strip()
                for diagram in linked_diagrams
                if not matched_components
                or set(str(component_id).strip() for component_id in diagram.get("related_components", []))
                .intersection(set(matched_components))
            ]
        )
        gaps.append(
            {
                "path": token,
                "component_ids": _dedupe_strings(matched_components),
                "linked_diagram_ids": linked_diagram_ids,
            }
        )
    return gaps
