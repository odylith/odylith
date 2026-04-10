from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.evaluation.odylith_benchmark_prompt_family_rules import (
    family_anchors_all_required_docs,
    family_uses_curated_doc_overrides,
    family_zero_support_doc_expansion,
    support_doc_family_rank,
)

_support_doc_family_rank = support_doc_family_rank


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _normalized_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(token).strip() for token in values if str(token).strip()]


_DOC_RELEVANCE_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "agent",
        "agents",
        "as",
        "at",
        "be",
        "case",
        "changed",
        "closeout",
        "component",
        "components",
        "contract",
        "contracts",
        "current",
        "criteria",
        "doc",
        "docs",
        "file",
        "files",
        "for",
        "from",
        "guide",
        "guidance",
        "impact",
        "intent",
        "json",
        "keep",
        "kind",
        "live",
        "local",
        "md",
        "mode",
        "needs",
        "odylith",
        "packet",
        "paths",
        "proof",
        "prompt",
        "publication",
        "py",
        "read",
        "reads",
        "repo",
        "required",
        "review",
        "runtime",
        "scenario",
        "slice",
        "spec",
        "src",
        "task",
        "tests",
        "the",
        "to",
        "truth",
        "txt",
        "unit",
        "validation",
        "validator",
        "with",
        "workstream",
    }
)


def _tokenize_relevance_text(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z0-9]+", str(value or "").lower())
        if len(token) >= 3 and token not in _DOC_RELEVANCE_STOPWORDS
    ]


def _scenario_relevance_hints(
    *,
    scenario: Mapping[str, Any] | None,
    changed_paths: Sequence[str],
) -> set[str]:
    rows: list[str] = []
    rows.extend(str(token).strip() for token in changed_paths if str(token).strip())
    if isinstance(scenario, Mapping):
        rows.extend(
            [
                str(scenario.get("family", "")).strip(),
                str(scenario.get("intent", "")).strip(),
                str(scenario.get("kind", "")).strip(),
                str(scenario.get("prompt", "")).strip(),
                str(scenario.get("workstream", "")).strip(),
                str(scenario.get("component", "")).strip(),
            ]
        )
        rows.extend(_normalized_string_list(scenario.get("required_paths")))
        rows.extend(_normalized_string_list(scenario.get("acceptance_criteria")))
        rows.extend(_normalized_string_list(scenario.get("validation_commands")))
    return set(_dedupe_strings(token for row in rows for token in _tokenize_relevance_text(row)))


def _strict_bounded_slice(scenario: Mapping[str, Any]) -> bool:
    changed_paths = _normalized_string_list(scenario.get("changed_paths"))
    required_paths = _normalized_string_list(scenario.get("required_paths"))
    family = str(scenario.get("family", "")).strip()
    if family == "exact_path_ambiguity":
        return True
    return bool(changed_paths) and required_paths == changed_paths and len(changed_paths) <= 2


def _strict_browser_slice(
    *,
    scenario_required_paths: Sequence[str],
    changed_paths: Sequence[str],
    family: str,
) -> bool:
    if str(family or "").strip() != "browser_surface_reliability":
        return False
    changed = {str(token).strip() for token in changed_paths if str(token).strip()}
    if changed:
        return True
    residual = [
        str(token).strip()
        for token in scenario_required_paths
        if str(token).strip() and str(token).strip() not in changed
    ]
    return bool(residual) and all(token.lower().endswith(".html") for token in residual)


def _strip_supporting_surface_hints(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = dict(payload or {})
    rows.pop("docs", None)
    rows.pop("relevant_docs", None)
    rows.pop("implementation_anchors", None)
    context_packet = dict(rows.get("context_packet", {})) if isinstance(rows.get("context_packet"), Mapping) else {}
    if context_packet:
        context_packet.pop("retrieval_plan", None)
        if context_packet:
            rows["context_packet"] = context_packet
        else:
            rows.pop("context_packet", None)
    return rows


def _set_context_anchor_explicit_paths(
    payload: Mapping[str, Any],
    *,
    explicit_paths: Sequence[str],
) -> dict[str, Any]:
    rows = dict(payload or {})
    explicit = _dedupe_strings(str(token).strip() for token in explicit_paths if str(token).strip())
    if not explicit:
        return rows
    context_packet = dict(rows.get("context_packet", {})) if isinstance(rows.get("context_packet"), Mapping) else {}
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    anchors["explicit_paths"] = _dedupe_strings(
        [
            *_normalized_string_list(anchors.get("explicit_paths")),
            *explicit,
        ]
    )
    context_packet["anchors"] = anchors
    rows["context_packet"] = context_packet
    return rows


def _drop_selected_docs_when_curated_docs_exist(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = dict(payload or {})
    if not _normalized_string_list(rows.get("docs")):
        return rows
    context_packet = dict(rows.get("context_packet", {})) if isinstance(rows.get("context_packet"), Mapping) else {}
    if not context_packet:
        return rows
    retrieval_plan = dict(context_packet.get("retrieval_plan", {})) if isinstance(context_packet.get("retrieval_plan"), Mapping) else {}
    if not retrieval_plan:
        return rows
    retrieval_plan.pop("selected_docs", None)
    if retrieval_plan:
        context_packet["retrieval_plan"] = retrieval_plan
    else:
        context_packet.pop("retrieval_plan", None)
    if context_packet:
        rows["context_packet"] = context_packet
    else:
        rows.pop("context_packet", None)
    return rows


def _support_doc_priority(path: str) -> tuple[int, int, str]:
    token = str(path or "").strip()
    lowered = token.lower()
    if lowered.endswith("/install_and_upgrade_runbook.md") or lowered.endswith("/maintainer_release_runbook.md"):
        return (0, len(token), token)
    if lowered.endswith("/release-baselines.v1.json"):
        return (1, len(token), token)
    if "/atlas/source/catalog/" in lowered and lowered.endswith(".json"):
        return (1, len(token), token)
    if (
        lowered.endswith("/reviewer_guide.md")
        or lowered.endswith("/metrics_and_priorities.md")
        or lowered.endswith("/release_benchmarks.md")
    ):
        return (1, len(token), token)
    if lowered.endswith("/current_spec.md"):
        return (2, len(token), token)
    if lowered.endswith("/index.html") or lowered.endswith("/compass.html"):
        return (3, len(token), token)
    if lowered == "agents.md" or lowered.endswith("/agents.md"):
        return (4, len(token), token)
    if "/agents-guidelines/" in lowered and lowered.endswith(".md"):
        return (4, len(token), token)
    if lowered.endswith("/readme.md"):
        return (4, len(token), token)
    if "/runtime/" in lowered and lowered.endswith(".md"):
        return (5, len(token), token)
    if lowered.endswith("/skill.md"):
        return (6, len(token), token)
    if "/atlas/source/" in lowered:
        return (7, len(token), token)
    if "/casebook/bugs/" in lowered:
        return (8, len(token), token)
    return (7, len(token), token)


def _skip_support_doc_candidate(path: str) -> bool:
    lowered = str(path or "").strip().lower()
    if not lowered:
        return True
    if lowered.endswith((".js", ".css", ".png", ".svg")):
        return True
    if lowered.endswith(".json"):
        return (
            "/registry/source/" not in lowered
            and "/runtime/source/" not in lowered
            and "/atlas/source/catalog/" not in lowered
            and not lowered.endswith("/release-baselines.v1.json")
        )
    return False


def _support_doc_relevance_score(
    *,
    path: str,
    hint_tokens: set[str],
) -> int:
    if not hint_tokens:
        return 0
    doc_tokens = set(_tokenize_relevance_text(path))
    if not doc_tokens:
        return 0
    overlap = len(doc_tokens.intersection(hint_tokens))
    if overlap <= 0:
        return 0
    if str(path or "").strip().lower().endswith("/current_spec.md"):
        return overlap + 1
    if "/atlas/source/catalog/" in str(path or "").strip().lower() and str(path or "").strip().lower().endswith(".json"):
        return overlap + 1
    return overlap


def _component_scope_size(entry: Any) -> int:
    path_prefixes = getattr(entry, "path_prefixes", ())
    if not isinstance(path_prefixes, Sequence):
        return 0
    return len([str(token).strip() for token in path_prefixes if str(token).strip()])


def _filter_component_scoped_support_docs(
    *,
    docs: Sequence[str],
    scenario_component: str,
    required_paths: Sequence[str],
    family: str = "",
) -> list[str]:
    component_id = str(scenario_component or "").strip().lower()
    if not component_id:
        return _dedupe_strings([str(token).strip() for token in docs if str(token).strip()])
    required = {str(token).strip() for token in required_paths if str(token).strip()}
    component_fragment = f"/registry/source/components/{component_id}/"
    normalized_family = str(family or "").strip()
    rows: list[str] = []
    for raw in docs:
        token = str(raw or "").strip()
        if not token:
            continue
        lowered = token.lower()
        if token in required:
            rows.append(token)
            continue
        if normalized_family == "install_upgrade_runtime":
            if lowered.endswith("/install_and_upgrade_runbook.md"):
                rows.append(token)
                continue
            if lowered.endswith(".md") and "/registry/source/components/" not in lowered:
                continue
        if "/registry/source/components/" in lowered and component_fragment not in lowered:
            continue
        rows.append(token)
    return _dedupe_strings(rows)


def _component_spec_path(*, repo_root: Path, component_id: str) -> str:
    token = str(component_id or "").strip().lower()
    if not token:
        return ""
    candidate = (
        Path(repo_root).resolve()
        / "odylith"
        / "registry"
        / "source"
        / "components"
        / token
        / "CURRENT_SPEC.md"
    )
    if not candidate.exists():
        return ""
    return candidate.relative_to(Path(repo_root).resolve()).as_posix()


def _is_component_spec_path(path: str) -> bool:
    normalized = str(path or "").strip()
    return normalized.endswith("/CURRENT_SPEC.md") and "/components/" in normalized


def _expand_component_anchor_paths(
    *,
    repo_root: Path,
    component_id: str,
    path_ref: str,
) -> list[str]:
    root = Path(repo_root).resolve()
    candidate = root / str(path_ref or "").strip()
    if not candidate.exists():
        return []
    if candidate.is_file():
        return [candidate.relative_to(root).as_posix()]
    if not candidate.is_dir():
        return []
    explicit_file = candidate / f"{str(component_id or '').strip().replace('-', '_')}.py"
    if explicit_file.is_file():
        return [explicit_file.relative_to(root).as_posix()]
    py_files = sorted(path for path in candidate.glob("*.py") if path.is_file())
    if py_files:
        return [py_files[0].relative_to(root).as_posix()]
    return []


def _selected_component_entries(
    *,
    repo_root: Path,
    component_ids: Sequence[str],
) -> list[Any]:
    component_index = store.load_component_index(repo_root=Path(repo_root).resolve(), runtime_mode="local")
    selected_entries: list[Any] = []
    seen_components: set[str] = set()
    for raw_component_id in component_ids:
        component_id = str(raw_component_id or "").strip().lower()
        if not component_id or component_id in seen_components:
            continue
        entry = component_index.get(component_id)
        if entry is None:
            continue
        seen_components.add(component_id)
        selected_entries.append(entry)
    ordered_entries = sorted(
        selected_entries,
        key=lambda item: (
            _component_scope_size(item),
            str(getattr(item, "component_id", "")).strip().lower(),
        ),
    )
    smallest_scope = min(
        (_component_scope_size(entry) for entry in ordered_entries if _component_scope_size(entry) > 0),
        default=0,
    )
    scope_ceiling = max(4, smallest_scope * 2) if smallest_scope else 0
    filtered_entries: list[Any] = []
    for entry in ordered_entries:
        if scope_ceiling and len(ordered_entries) > 1 and _component_scope_size(entry) > scope_ceiling:
            continue
        filtered_entries.append(entry)
    return filtered_entries


def _implementation_anchor_priority(path: str) -> tuple[int, int, str]:
    token = str(path or "").strip()
    lowered = token.lower()
    if lowered.startswith("src/") and lowered.endswith(".py"):
        return (0, len(token), token)
    if lowered.startswith("src/") and lowered.endswith((".ts", ".tsx", ".js", ".jsx")):
        return (1, len(token), token)
    if lowered.startswith("src/"):
        return (2, len(token), token)
    if lowered.startswith("odylith/runtime/") and lowered.endswith(".md"):
        return (4, len(token), token)
    return (3, len(token), token)


def _looks_like_code_anchor(path: str) -> bool:
    token = str(path or "").strip()
    lowered = token.lower()
    return lowered.startswith(("src/", "tests/")) and lowered.endswith((".py", ".ts", ".tsx", ".js", ".jsx"))


def _select_code_anchors_from_paths(
    *,
    paths: Sequence[str],
    changed_paths: Sequence[str],
    limit: int,
    preserve_input_order: bool = False,
) -> list[str]:
    normalized_changed = {str(token).strip() for token in changed_paths if str(token).strip()}
    bounded_limit = max(0, int(limit or 0))
    if bounded_limit == 0:
        return []
    candidates = [
        token
        for token in _dedupe_strings([str(token).strip() for token in paths if str(token).strip()])
        if token not in normalized_changed and _looks_like_code_anchor(token)
    ]
    if preserve_input_order:
        return candidates[:bounded_limit]
    return sorted(candidates, key=_implementation_anchor_priority)[:bounded_limit]


def _filter_first_pass_implementation_anchors(
    *,
    scenario: Mapping[str, Any] | None,
    changed_paths: Sequence[str],
    anchors: Sequence[str],
) -> list[str]:
    family = str((scenario or {}).get("family", "")).strip()
    required_paths = {str(token).strip() for token in _normalized_string_list((scenario or {}).get("required_paths"))}
    if not bool((scenario or {}).get("allow_noop_completion")) or family not in {"install_upgrade_runtime", "agent_activation"}:
        if family == "cross_surface_governance_sync":
            return _dedupe_strings(
                [
                    str(token).strip()
                    for token in anchors
                    if str(token).strip()
                    and (
                        not str(token).strip().startswith("tests/")
                        or str(token).strip() in set(str(path).strip() for path in changed_paths if str(path).strip())
                        or (
                            str(token).strip() in required_paths
                            and not str(token).strip().endswith("test_hygiene.py")
                        )
                    )
                ]
            )
        return _dedupe_strings([str(token).strip() for token in anchors if str(token).strip()])
    normalized_changed = {str(token).strip() for token in changed_paths if str(token).strip()}
    install_test_prefixes = ("tests/unit/install/", "tests/integration/install/")
    return _dedupe_strings(
        [
            str(token).strip()
            for token in anchors
            if str(token).strip()
            and (
                not str(token).strip().startswith("tests/")
                or str(token).strip() in normalized_changed
                or str(token).strip().startswith(install_test_prefixes)
            )
        ]
    )


def select_live_prompt_support_docs(
    *,
    docs: Sequence[str],
    changed_paths: Sequence[str],
    scenario: Mapping[str, Any] | None = None,
    limit: int = 3,
) -> list[str]:
    changed = {str(token).strip() for token in changed_paths if str(token).strip()}
    hint_tokens = _scenario_relevance_hints(scenario=scenario, changed_paths=changed_paths)
    candidates = [
        token
        for token in _dedupe_strings([str(token).strip() for token in docs if str(token).strip()])
        if token not in changed and not _looks_like_code_anchor(token) and not _skip_support_doc_candidate(token)
    ]
    family = str((scenario or {}).get("family", "")).strip()
    relevant_scores = {
        token: _support_doc_relevance_score(path=token, hint_tokens=hint_tokens)
        for token in candidates
    }
    if any(score > 0 for score in relevant_scores.values()):
        candidates = [
            token
            for token in candidates
            if relevant_scores.get(token, 0) > 0
        ]
    ordered = sorted(
        candidates,
        key=lambda token: (
            -int(relevant_scores.get(token, 0) or 0),
            _support_doc_family_rank(path=token, family=family),
            *_support_doc_priority(token),
        ),
    )
    bounded_limit = max(0, int(limit or 0))
    strong_docs = [token for token in ordered if _support_doc_priority(token)[0] <= 4]
    if strong_docs:
        return strong_docs[:bounded_limit]
    return ordered[:bounded_limit]


def select_live_prompt_implementation_anchors(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    component_ids: Sequence[str],
    limit: int = 2,
) -> list[str]:
    normalized_changed = {str(token).strip() for token in changed_paths if str(token).strip()}
    bounded_limit = max(0, int(limit or 0))
    if bounded_limit == 0:
        return []
    ordered_entries = _selected_component_entries(repo_root=repo_root, component_ids=component_ids)
    anchors: list[str] = []
    seen_paths: set[str] = set()
    for entry in ordered_entries:
        path_prefixes = getattr(entry, "path_prefixes", ())
        if not isinstance(path_prefixes, Sequence):
            continue
        candidates: list[str] = []
        for raw_path_ref in path_prefixes:
            path_ref = str(raw_path_ref).strip()
            if not path_ref:
                continue
            candidates.extend(
                _expand_component_anchor_paths(
                    repo_root=Path(repo_root).resolve(),
                    component_id=str(getattr(entry, "component_id", "")).strip(),
                    path_ref=path_ref,
                )
            )
        for path_ref in sorted(candidates, key=_implementation_anchor_priority):
            if path_ref in normalized_changed:
                continue
            if path_ref in seen_paths:
                continue
            seen_paths.add(path_ref)
            anchors.append(path_ref)
            break
        if len(anchors) >= bounded_limit:
            break
    return anchors[:bounded_limit]


def select_live_prompt_component_specs(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    component_ids: Sequence[str],
    limit: int = 3,
) -> list[str]:
    normalized_changed = {str(token).strip() for token in changed_paths if str(token).strip()}
    bounded_limit = max(0, int(limit or 0))
    if bounded_limit == 0:
        return []
    specs: list[str] = []
    seen_specs: set[str] = set()
    for entry in _selected_component_entries(repo_root=repo_root, component_ids=component_ids):
        spec_path = _component_spec_path(
            repo_root=Path(repo_root).resolve(),
            component_id=str(getattr(entry, "component_id", "")).strip(),
        )
        if not spec_path or spec_path in normalized_changed or spec_path in seen_specs:
            continue
        seen_specs.add(spec_path)
        specs.append(spec_path)
        if len(specs) >= bounded_limit:
            break
    return specs[:bounded_limit]


def _scenario_required_paths_for_live_prompt(
    *,
    scenario: Mapping[str, Any] | None,
    changed_paths: Sequence[str],
) -> list[str]:
    if not isinstance(scenario, Mapping):
        return []
    changed = {str(token).strip() for token in changed_paths if str(token).strip()}
    return [
        token
        for token in _dedupe_strings(_normalized_string_list(scenario.get("required_paths")))
        if token not in changed
    ]


def _required_support_docs_for_live_prompt(
    *,
    scenario: Mapping[str, Any] | None,
    changed_paths: Sequence[str],
    limit: int,
) -> list[str]:
    changed = {str(token).strip() for token in changed_paths if str(token).strip()}
    bounded_limit = max(0, int(limit or 0))
    if bounded_limit == 0:
        return []
    required_paths = _scenario_required_paths_for_live_prompt(
        scenario=scenario,
        changed_paths=changed_paths,
    )
    candidates = [
        token
        for token in _dedupe_strings(required_paths)
        if token not in changed and not _looks_like_code_anchor(token) and not _skip_support_doc_candidate(token)
    ]
    family = str((scenario or {}).get("family", "")).strip()
    return sorted(
        candidates,
        key=lambda token: (
            _support_doc_family_rank(path=token, family=family),
            *_support_doc_priority(token),
        ),
    )[:bounded_limit]


def _architecture_component_ids(payload: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    linked_components = payload.get("linked_components")
    if isinstance(linked_components, list):
        rows.extend(
            str(row.get("component_id", "")).strip()
            for row in linked_components
            if isinstance(row, Mapping) and str(row.get("component_id", "")).strip()
        )
    topology_domains = payload.get("topology_domains")
    if isinstance(topology_domains, list):
        rows.extend(
            str(row.get("domain_id", "")).strip()
            for row in topology_domains
            if isinstance(row, Mapping) and str(row.get("domain_id", "")).strip()
        )
    return _dedupe_strings(rows)


def _supplement_architecture_live_prompt_payload(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    prompt_payload: Mapping[str, Any],
    changed_paths: Sequence[str],
    full_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(prompt_payload or {})
    architecture_audit = (
        dict(payload.get("architecture_audit", {}))
        if isinstance(payload.get("architecture_audit"), Mapping)
        else {}
    )
    if not architecture_audit:
        return payload
    if _strict_bounded_slice(scenario):
        architecture_audit["strict_boundary"] = True
        architecture_audit["boundary_hints"] = [
            "Treat this as a bounded dossier review. Audit only the listed file and fail closed on claims the dossier itself cannot support."
        ]
        payload["architecture_audit"] = architecture_audit
        return payload

    scenario_required_paths = _scenario_required_paths_for_live_prompt(
        scenario=scenario,
        changed_paths=changed_paths,
    )
    raw_audit = dict(full_payload or {})
    if not raw_audit or (
        not isinstance(raw_audit.get("linked_components"), list)
        and not isinstance(raw_audit.get("topology_domains"), list)
    ):
        raw_audit = store.build_architecture_audit(
            repo_root=Path(repo_root).resolve(),
            changed_paths=[str(token).strip() for token in changed_paths if str(token).strip()],
            runtime_mode="local",
            detail_level="full",
        )
    component_ids = _architecture_component_ids(raw_audit)
    explicit_implementation_anchors = _select_code_anchors_from_paths(
        paths=_normalized_string_list(architecture_audit.get("implementation_anchors")),
        changed_paths=changed_paths,
        limit=2,
        preserve_input_order=True,
    )
    implementation_anchors = list(explicit_implementation_anchors)
    if not implementation_anchors and (
        not scenario_required_paths or any(_looks_like_code_anchor(token) for token in scenario_required_paths)
    ):
        implementation_anchors = select_live_prompt_implementation_anchors(
            repo_root=Path(repo_root).resolve(),
            changed_paths=changed_paths,
            component_ids=component_ids,
        )
    if implementation_anchors:
        architecture_audit["implementation_anchors"] = implementation_anchors
    else:
        architecture_audit.pop("implementation_anchors", None)
    component_specs = select_live_prompt_component_specs(
        repo_root=Path(repo_root).resolve(),
        changed_paths=changed_paths,
        component_ids=component_ids,
    )
    support_doc_limit = 5
    required_support_docs = _required_support_docs_for_live_prompt(
        scenario=scenario,
        changed_paths=changed_paths,
        limit=support_doc_limit,
    )
    if required_support_docs:
        # When the scenario already names the supporting docs, fail closed to that
        # contract instead of widening the live prompt with extra audit reads.
        support_docs = list(required_support_docs)
    else:
        support_docs = select_live_prompt_support_docs(
            docs=[
                token
                for token in [
                    *scenario_required_paths,
                    *component_specs,
                    *_normalized_string_list(raw_audit.get("required_reads")),
                    *_normalized_string_list(architecture_audit.get("required_reads")),
                ]
                if token not in set(required_support_docs)
            ],
            changed_paths=changed_paths,
            scenario=scenario,
            limit=max(0, support_doc_limit - len(required_support_docs)),
        )
        support_docs = _dedupe_strings([*required_support_docs, *support_docs])
    if component_specs:
        component_spec_set = set(component_specs)
        support_docs = [
            *[token for token in support_docs if token in component_spec_set],
            *[token for token in support_docs if token not in component_spec_set],
        ]
    support_docs = support_docs[:support_doc_limit]
    if support_docs:
        architecture_audit["required_reads"] = support_docs
    else:
        architecture_audit.pop("required_reads", None)
    payload["architecture_audit"] = architecture_audit
    return payload


def supplement_live_prompt_payload(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    prompt_payload: Mapping[str, Any],
    packet_source: str,
    changed_paths: Sequence[str],
    full_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(prompt_payload or {})
    raw_payload = dict(full_payload or {})
    strict_bounded_slice = _strict_bounded_slice(scenario)
    existing_docs = select_live_prompt_support_docs(
        docs=_normalized_string_list(payload.get("docs")),
        changed_paths=changed_paths,
        scenario=scenario,
    )
    normalized_packet_source = str(packet_source or "").strip()
    if normalized_packet_source == "architecture_dossier":
        return _supplement_architecture_live_prompt_payload(
            repo_root=repo_root,
            scenario=scenario,
            prompt_payload=payload,
            changed_paths=changed_paths,
            full_payload=raw_payload,
        )
    if normalized_packet_source not in {"impact", "governance_slice"}:
        if strict_bounded_slice:
            payload = _strip_supporting_surface_hints(payload)
            payload["strict_boundary"] = True
            return payload
        if existing_docs:
            payload["docs"] = existing_docs
        return payload
    if strict_bounded_slice:
        payload = _strip_supporting_surface_hints(payload)
        strict_doc_explicit_paths = [
            token
            for token in _dedupe_strings([str(token).strip() for token in changed_paths if str(token).strip()])
            if not _looks_like_code_anchor(token) and not _skip_support_doc_candidate(token)
        ]
        if strict_doc_explicit_paths:
            payload = _set_context_anchor_explicit_paths(payload, explicit_paths=strict_doc_explicit_paths)
        payload["strict_boundary"] = True
        return payload

    if not raw_payload or (
        not isinstance(raw_payload.get("components"), list)
        and not isinstance(raw_payload.get("docs"), list)
    ):
        raw_payload = store.build_impact_report(
            repo_root=Path(repo_root).resolve(),
            changed_paths=[str(token).strip() for token in changed_paths if str(token).strip()],
            runtime_mode="local",
            intent=str(scenario.get("intent", "")).strip(),
            delivery_profile=agent_runtime_contract.AGENT_HOT_PATH_PROFILE,
            family_hint=str(scenario.get("family", "")).strip(),
            workstream_hint=str(scenario.get("workstream", "")).strip(),
            validation_command_hints=[
                str(token).strip()
                for token in scenario.get("validation_commands", [])
                if str(token).strip()
            ]
            if isinstance(scenario.get("validation_commands"), list)
            else (),
            retain_hot_path_internal_context=False,
            finalize_packet=False,
        )
    component_ids = [
        str(row.get("entity_id", "")).strip()
        for row in raw_payload.get("components", [])
        if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    ] if isinstance(raw_payload.get("components"), list) else []
    family = str(scenario.get("family", "")).strip()
    scenario_component = str(scenario.get("component", "")).strip()
    scenario_required_paths = _scenario_required_paths_for_live_prompt(
        scenario=scenario,
        changed_paths=changed_paths,
    )
    strict_browser_slice = _strict_browser_slice(
        scenario_required_paths=scenario_required_paths,
        changed_paths=changed_paths,
        family=family,
    )
    raw_doc_paths = _filter_component_scoped_support_docs(
        docs=_normalized_string_list(raw_payload.get("docs")),
        scenario_component=scenario_component,
        required_paths=scenario_required_paths,
        family=family,
    )
    existing_docs = _filter_component_scoped_support_docs(
        docs=existing_docs,
        scenario_component=scenario_component,
        required_paths=scenario_required_paths,
        family=family,
    )
    anchor_limit = 3 if normalized_packet_source == "governance_slice" else 2
    if normalized_packet_source == "governance_slice" and family in {"agent_activation", "install_upgrade_runtime"}:
        anchor_limit = 4
    if family == "browser_surface_reliability":
        anchor_limit = max(anchor_limit, 4)
    changed_code_anchors = _select_code_anchors_from_paths(
        paths=changed_paths,
        changed_paths=[],
        limit=anchor_limit,
        preserve_input_order=True,
    )
    implementation_anchors = select_live_prompt_implementation_anchors(
        repo_root=Path(repo_root).resolve(),
        changed_paths=changed_paths,
        component_ids=component_ids,
        limit=anchor_limit,
    )
    required_code_anchors = _select_code_anchors_from_paths(
        paths=scenario_required_paths,
        changed_paths=changed_paths,
        limit=anchor_limit,
        preserve_input_order=True,
    )
    raw_code_anchors = _select_code_anchors_from_paths(
        paths=raw_doc_paths,
        changed_paths=changed_paths,
        limit=anchor_limit,
    )
    merged_anchors = _filter_first_pass_implementation_anchors(
        scenario=scenario,
        changed_paths=changed_paths,
        anchors=_dedupe_strings([*changed_code_anchors, *implementation_anchors, *required_code_anchors, *raw_code_anchors]),
    )[:anchor_limit]
    if merged_anchors:
        payload["implementation_anchors"] = merged_anchors

    spec_component_ids = [scenario_component] if scenario_component else component_ids
    component_specs = select_live_prompt_component_specs(
        repo_root=Path(repo_root).resolve(),
        changed_paths=changed_paths,
        component_ids=spec_component_ids,
        limit=5 if normalized_packet_source == "governance_slice" else 3,
    )
    if family == "browser_surface_reliability":
        component_specs = []

    support_doc_limit = 5 if normalized_packet_source == "governance_slice" else 3
    required_support_docs = _required_support_docs_for_live_prompt(
        scenario=scenario,
        changed_paths=changed_paths,
        limit=support_doc_limit,
    )
    support_docs = (
        []
        if family_zero_support_doc_expansion(family)
        else select_live_prompt_support_docs(
            docs=[
                *[
                    token
                    for token in [*scenario_required_paths, *component_specs, *existing_docs, *raw_doc_paths]
                    if token not in set(required_support_docs)
                ]
            ],
            changed_paths=changed_paths,
            scenario=scenario,
            limit=max(0, support_doc_limit - len(required_support_docs)),
        )
    )
    changed_support_docs = [
        token
        for token in _dedupe_strings([str(token).strip() for token in changed_paths if str(token).strip()])
        if not _looks_like_code_anchor(token) and not _skip_support_doc_candidate(token)
    ]
    if family == "merge_heavy_change" and changed_support_docs:
        support_doc_limit = max(
            support_doc_limit,
            len(_dedupe_strings([*changed_support_docs, *required_support_docs, *component_specs])),
        )
        support_docs = _dedupe_strings([*changed_support_docs, *support_docs])
    boundary_hints = _normalized_string_list(payload.get("boundary_hints"))
    if family == "browser_surface_reliability":
        support_docs = [token for token in support_docs if not _is_component_spec_path(token)]
        explicitly_required_support_docs = {
            token
            for token in scenario_required_paths
            if not _looks_like_code_anchor(token)
        }
        if explicitly_required_support_docs:
            support_docs = _dedupe_strings(
                [
                    token
                    for token in support_docs
                    if token in explicitly_required_support_docs
                ]
            )
            context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
            retrieval_plan = (
                dict(context_packet.get("retrieval_plan", {}))
                if isinstance(context_packet.get("retrieval_plan"), Mapping)
                else {}
            )
            selected_docs = [
                token
                for token in _normalized_string_list(retrieval_plan.get("selected_docs"))
                if token in explicitly_required_support_docs
            ]
            if selected_docs:
                retrieval_plan["selected_docs"] = selected_docs
            else:
                retrieval_plan.pop("selected_docs", None)
            if retrieval_plan:
                context_packet["retrieval_plan"] = retrieval_plan
            else:
                context_packet.pop("retrieval_plan", None)
            if context_packet:
                payload["context_packet"] = context_packet
            else:
                payload.pop("context_packet", None)
        required_html_docs = {
            token
            for token in scenario_required_paths
            if str(token).strip().lower().endswith(".html")
        }
        if required_html_docs:
            support_docs = _dedupe_strings(
                [
                    token
                    for token in support_docs
                    if not str(token).strip().lower().endswith(".html") or token in required_html_docs
                ]
            )
        if required_html_docs or any(token in {"odylith/index.html", "odylith/compass/compass.html"} for token in support_docs):
            boundary_hints.append(
                "For shell/browser regressions, keep writable changes on the listed source renderers, onboarding or CLI sources, and browser tests. Treat odylith/*.html shell pages as rendered read surfaces or validator outputs, not primary edit targets, unless a listed changed path or validator failure points there directly."
            )
        boundary_hints.append(
            "Do not widen browser slices into bundle assets, generated tooling-app payloads, or adjacent shell templates unless the focused browser validator or a listed anchor points there directly."
        )
        boundary_hints.append(
            "Do not inspect benchmark runner, prompt, or evaluation sources on browser slices unless they are explicit listed anchors or a focused validator failure points there directly."
        )
        boundary_hints.append(
            "Prefer the smallest source-of-truth repair on the listed renderers, onboarding helpers, CLI surfaces, and browser tests. Restore the real rendered shell path or remove test-only stubs before adding broader onboarding-state assertions."
        )
        boundary_hints.append(
            "If the browser integration slice already has a shared helper for the real renderer path, preserve that helper and reroute callers through it instead of deleting it, shadowing it, or replacing it with one-off nested helpers."
        )
        boundary_hints.append(
            "In temporary consumer-repo browser tests, keep the rendered-shell setup on the existing fake sync or dashboard-refresh hooks; do not unmock or introduce live `sync_workstream_artifacts.main` calls just to prove the browser contract."
        )
        boundary_hints.append(
            "Treat install-state persistence and upgrade spotlight storage under `src/odylith/install/` as out of scope on browser slices unless the focused validator or an explicit required path points there directly."
        )
        boundary_hints.append(
            "Use the listed browser validators and shared real-render helpers for local proof. Do not add one-off Python or shell probes that import `odylith.install.state` or other install persistence helpers just to inspect onboarding or spotlight state."
        )
        boundary_hints.append(
            "Do not add new spotlight, reopen-pill, or upgrade-state assertions unless the existing focused browser validator points to that exact missing contract."
        )
        boundary_hints.append(
            "Ignore unrelated dirty worktree changes outside the listed browser anchors and validators. They are not evidence for this slice and must not pull you into benchmark evaluation helpers or other repo-adjacent cleanup."
        )
        if strict_browser_slice:
            context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
            anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
            changed_anchor_paths = {
                token
                for token in _normalized_string_list(anchors.get("changed_paths"))
            }
            residual_required_paths = [
                token
                for token in scenario_required_paths
                if token not in changed_anchor_paths
            ]
            explicit_paths = _dedupe_strings(
                [
                    *_normalized_string_list(anchors.get("explicit_paths")),
                    *residual_required_paths,
                ]
            )
            if explicit_paths:
                anchors["explicit_paths"] = explicit_paths
            if anchors:
                context_packet["anchors"] = anchors
            if context_packet:
                payload["context_packet"] = context_packet
            payload = _strip_supporting_surface_hints(payload)
            payload["strict_boundary"] = True
            if boundary_hints:
                payload["boundary_hints"] = _dedupe_strings(boundary_hints)
            return payload
    if family == "docs_code_closeout":
        boundary_hints.append(
            "For docs closeout slices, keep writes on the listed README/docs surfaces and any explicit graph or source anchor. Do not widen into unrelated Registry specs, plans, Atlas, Casebook, or other documentation families unless a listed anchor or validator failure points there directly."
        )
    if family == "merge_heavy_change":
        boundary_hints.append(
            "For merge-heavy router or governed-doc slices, treat the listed router skill and governed operations docs as the whole writable boundary. If those anchors already agree and the focused validator passes, close successfully with no file changes."
        )
        boundary_hints.append(
            "Unrelated Registry, Atlas, or other governance drift elsewhere in the repo is a follow-up note, not a blocker for this bounded closeout."
        )
    if family == "component_governance":
        boundary_hints.append(
            "For component-governance slices, keep the listed Registry entry, component spec, Mermaid source, and paired Atlas catalog or index artifacts synchronized as one bounded truth set."
        )
        boundary_hints.append(
            "If the listed component-governance validators already pass on that bounded truth set, stop with no file changes instead of restating the contract through speculative Registry, Atlas, or benchmark-doc edits."
        )
        boundary_hints.append(
            "Do not stop after updating only the component spec or Mermaid source when a listed catalog or index artifact still needs the matching change."
        )
        boundary_hints.append(
            "If the required paths also list benchmark docs or maintainer guidance, treat those docs as part of the same bounded truth set when the focused validator still reports contract drift there; do not leave them as read-only support context."
        )
        boundary_hints.append(
            "Benchmark runner helpers, graph generators, benchmark docs, and maintainer publication skills are out of scope on this family unless they are explicit required paths or a focused validator failure points there directly."
        )
        boundary_hints.append(
            "Do not widen into `src/odylith/cli.py`, validator harness helpers, install or release runbooks, or broader benchmark publication infrastructure unless one of those exact files is an explicit required path or the focused validator failure cites it directly."
        )
    if family == "governed_surface_sync":
        support_docs = _dedupe_strings([*changed_support_docs, *required_support_docs, *support_docs])[:support_doc_limit]
        boundary_hints.append(
            "For governed-surface sync slices, keep writes on the listed governance surface docs and the named Radar index only. If the focused sync validators already pass on that bounded slice, stop with no file changes instead of widening into store code, runtime helpers, or broader backlog cleanup."
        )
        boundary_hints.append(
            "Treat unrelated Radar ideas, plan docs, Registry inventory, Atlas catalog artifacts, and broader governance maintenance drift as out of scope unless they are explicit required paths or a focused validator failure points there directly."
        )
    if family == "cross_surface_governance_sync":
        boundary_hints.append(
            "For cross-surface governance sync slices, keep writes on the listed sync engine and paired backlog, plan, Registry, and Atlas surfaces. If the focused sync validator passes on that bounded slice, do not escalate unrelated pre-existing repo drift into a blocked closeout."
        )
        boundary_hints.append(
            "Treat rendered Radar or Compass HTML, backlog JS payloads, traceability JSON, and unrelated Radar idea notes as out of scope unless those exact files are explicit required paths or the focused sync validator points there directly."
        )
    if family == "validation_heavy_fix":
        boundary_hints.append(
            "For validation-heavy benchmark fixes, keep writable changes on the listed runtime and test anchors. Treat reviewer docs, Registry specs, and maintainer benchmark guidance as read-only references; do not edit README or benchmark docs unless they are explicit changed or required paths."
        )
        boundary_hints.append(
            "Do not rewrite benchmark expectation literals or published delta assertions unless the focused runner check fails locally and the grounded runner logic still contradicts the raw-baseline contract."
        )
    required_support_doc_boundary = {
        token
        for token in _normalized_string_list((scenario or {}).get("required_paths"))
        if not _looks_like_code_anchor(token) and not _skip_support_doc_candidate(token)
    }
    prioritized_changed_support_docs = [
        token
        for token in changed_support_docs
        if token in required_support_doc_boundary
    ]
    if family == "release_publication" and prioritized_changed_support_docs:
        support_doc_limit = max(
            support_doc_limit,
            len(_dedupe_strings([*prioritized_changed_support_docs, *required_support_docs, *component_specs])),
        )
        support_docs = _dedupe_strings([*prioritized_changed_support_docs, *support_docs])
    release_publication_has_baseline_doc = any(
        str(token).strip().lower().endswith("/release-baselines.v1.json")
        for token in required_support_doc_boundary
    )
    if family == "release_publication" and prioritized_changed_support_docs and not release_publication_has_baseline_doc:
        support_docs = _dedupe_strings(
            [*prioritized_changed_support_docs, *required_support_docs, *support_docs]
        )[:support_doc_limit]
    else:
        support_docs = _dedupe_strings([*required_support_docs, *support_docs])[:support_doc_limit]
    if support_docs:
        payload["docs"] = support_docs
    else:
        payload.pop("docs", None)
    if family_uses_curated_doc_overrides(family) and support_docs:
        payload = _drop_selected_docs_when_curated_docs_exist(payload)
    explicit_required_docs: list[str] = []
    if family_anchors_all_required_docs(family):
        explicit_required_docs = [
            token
            for token in scenario_required_paths
            if not _looks_like_code_anchor(str(token).strip())
        ]
    if family == "merge_heavy_change" and changed_support_docs:
        explicit_required_docs = _dedupe_strings([*changed_support_docs, *explicit_required_docs])
    elif family == "release_publication" and prioritized_changed_support_docs:
        explicit_required_docs = _dedupe_strings([*prioritized_changed_support_docs, *explicit_required_docs])
    payload = _set_context_anchor_explicit_paths(payload, explicit_paths=explicit_required_docs)
    if family == "release_publication":
        boundary_hints.append(
            "For benchmark publication slices, keep reads and edits on the listed benchmark contracts plus the runner/graphs anchors. Do not inspect adjacent benchmark helpers or secondary benchmark docs unless a listed anchor or validator failure points there directly, and do not rerun `odylith benchmark --repo-root .` during first-pass diagnosis."
        )
        boundary_hints.append(
            "If the current copied artifacts and anchored publication docs already reflect the validated report, stop with no file changes instead of editing benchmark wording."
        )
        boundary_hints.append(
            "Treat graph command output paths and generated SVGs as validator-produced outputs, not manual patch targets. Use repo-relative benchmark doc paths only, and map any absolute graph output back to the corresponding tracked docs/benchmarks target before editing."
        )
        boundary_hints.append(
            "Unrelated dirty evaluation helpers under `src/odylith/runtime/evaluation/`, rendered shell pages, and generated proof SVGs are out of scope unless they are explicit required paths or a focused validator failure points there directly."
        )
    if family == "install_upgrade_runtime":
        boundary_hints.append(
            "For install/upgrade runtime slices, stay on the listed install manager, runtime, repair, release-contract anchors, and focused validators. If the grounded tree already passes those validators, stop with no file changes instead of widening into activation or policy wording."
        )
        boundary_hints.append(
            "Do not inspect README, pyproject.toml, odylith/*.html shell surfaces, src/odylith/cli.py, or broader context-engine/orchestration helpers on install slices unless a focused install validator fails and points there directly."
        )
    if family == "daemon_security":
        boundary_hints.append(
            "For daemon/security slices, stay on the listed context-engine and repair anchors plus their focused tests. Do not widen into `src/odylith/cli.py` or adjacent runtime helpers unless a listed anchor or validator failure points there directly."
        )
        boundary_hints.append(
            "Keep the named context-engine guidance and context-engine spec surfaces as the only supporting docs. Do not pull Registry inventory, benchmark publication docs, or unrelated governance records into daemon/security proof slices unless they are explicit required paths."
        )
        if bool((scenario or {}).get("allow_noop_completion")):
            boundary_hints.append(
                "If the grounded daemon lifecycle anchors and focused daemon validator already pass, stop with no file changes instead of rewriting auth-token persistence, socket transport, or shutdown flow."
            )
    if family == "compass_brief_freshness":
        boundary_hints.append(
            "For Compass freshness slices, keep the writable boundary on the listed Compass runtime, brief narrator, focused tests, and the named Compass/product runtime surfaces. Do not widen into install, repair, or context-engine docs unless a listed anchor or focused validator failure points there directly."
        )
        if bool((scenario or {}).get("allow_noop_completion")):
            boundary_hints.append(
                "If the listed Compass freshness validators already pass on that bounded runtime slice, stop with no file changes instead of speculative freshness or narration rewrites."
            )
    if family == "consumer_profile_compatibility":
        boundary_hints.append(
            "For consumer-profile compatibility slices, keep writes on the listed consumer profile code/tests plus the named AGENTS and component-spec surfaces. Do not widen into component inventory or broader Registry governance unless a listed anchor or focused validator failure points there directly."
        )
        if bool((scenario or {}).get("allow_noop_completion")):
            boundary_hints.append(
                "If the listed consumer-profile validator already passes on that bounded compatibility slice, stop with no file changes instead of rebinding truth roots or widening into broader Registry governance."
            )
    if family in {"cross_file_feature", "exact_anchor_recall", "explicit_workstream", "orchestration_feedback", "orchestration_intelligence"}:
        boundary_hints.append(
            "For narrow anchored orchestration slices, keep the boundary on the listed skills and named runtime anchor only. Do not widen into Registry specs, runbooks, Radar ideas, or unrelated orchestration helpers unless they are explicit required paths or a focused validator failure points there directly."
        )
        boundary_hints.append(
            "If the listed anchors already satisfy the focused validator or expectation, stop with no file changes instead of adding adjacent support docs or governance cleanup."
        )
    if family == "agent_activation":
        boundary_hints.append(
            "For agent-activation slices, keep the boundary on the listed install activation anchors, consumer AGENTS surface, and focused install validators. If the grounded tree already passes those validators, stop with no file changes instead of rewriting install activation or AGENTS guidance wording."
        )
        boundary_hints.append(
            "Do not inspect README, pyproject.toml, odylith/*.html shell surfaces, src/odylith/cli.py, or broader runtime routing helpers on agent-activation slices unless the focused install validator fails and points there directly."
        )
    if boundary_hints:
        payload["boundary_hints"] = _dedupe_strings(boundary_hints)
    return payload
