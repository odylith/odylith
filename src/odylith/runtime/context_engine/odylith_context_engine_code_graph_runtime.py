"""Code-graph compilation helpers extracted from the context engine store."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Mapping, Sequence


def _python_module_name(*, rel_path: str, source_root: str, module_root: str) -> str:
    relative = Path(rel_path).relative_to(source_root)
    parts = list(relative.parts)
    if not parts:
        return module_root
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = Path(parts[-1]).stem
    if not parts:
        return module_root
    return ".".join([module_root, *parts])


def _collect_python_module_index(repo_root: Path) -> dict[str, str]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    rows: dict[str, str] = {}
    for rel_root, module_root in odylith_context_engine_store._PYTHON_GRAPH_ROOTS:  # noqa: SLF001
        root = repo_root / rel_root
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            rel_path = path.relative_to(repo_root).as_posix()
            rows[_python_module_name(rel_path=rel_path, source_root=rel_root, module_root=module_root)] = rel_path
    return rows


def _resolve_from_import(
    *,
    current_module: str,
    is_package: bool,
    module: str | None,
    level: int,
    alias_name: str,
    module_index: Mapping[str, str],
) -> str:
    package_parts = current_module.split(".")
    if not is_package:
        package_parts = package_parts[:-1]
    if level > 0:
        trim = max(0, level - 1)
        package_parts = package_parts[: max(0, len(package_parts) - trim)]
    else:
        package_parts = []
    base_parts = [*package_parts]
    if module:
        base_parts.extend([part for part in str(module).split(".") if part])
    base = ".".join(part for part in base_parts if part)
    if alias_name == "*":
        return base
    candidate = f"{base}.{alias_name}" if base else alias_name
    if candidate in module_index:
        return candidate
    return base


def _extract_marker_names(decorators: Sequence[ast.expr]) -> list[str]:
    markers: set[str] = set()
    for decorator in decorators:
        node = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute):
            if isinstance(node.value.value, ast.Name) and node.value.value.id == "pytest" and node.value.attr == "mark":
                markers.add(str(node.attr))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "pytest" and node.attr == "mark":
                markers.add("mark")
    return sorted(markers)


def _parse_python_artifact(
    *,
    repo_root: Path,
    rel_path: str,
    module_name: str,
    module_index: Mapping[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    path = repo_root / rel_path
    source = odylith_context_engine_store._raw_text(path)  # noqa: SLF001
    imports: set[str] = set()
    contract_refs = set(
        odylith_context_engine_store._extract_path_refs(text=source, repo_root=repo_root)  # noqa: SLF001
    )
    try:
        tree = ast.parse(source or "", filename=rel_path)
    except SyntaxError:
        return (
            {
                "path": rel_path,
                "module_name": module_name,
                "layer": module_name.split(".", 1)[0] if module_name else "",
                "imports": [],
                "contract_refs": sorted(contract_refs),
                "metadata": {"parse_error": True},
            },
            [],
        )
    is_package = Path(rel_path).name == "__init__.py"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target_module = str(alias.name).strip()
                if target_module in module_index:
                    imports.add(module_index[target_module])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                target_module = _resolve_from_import(
                    current_module=module_name,
                    is_package=is_package,
                    module=node.module,
                    level=int(node.level or 0),
                    alias_name=str(alias.name),
                    module_index=module_index,
                )
                if target_module and target_module in module_index:
                    imports.add(module_index[target_module])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            contract_refs.update(
                odylith_context_engine_store._extract_path_refs(text=str(node.value), repo_root=repo_root)  # noqa: SLF001
            )
    edges: list[dict[str, Any]] = []
    for target_path in sorted(imports):
        edges.append(
            {
                "source_path": rel_path,
                "relation": "imports",
                "target_path": target_path,
                "metadata": {"module_name": module_name},
            }
        )
    for target_path in sorted(contract_refs):
        if target_path.startswith(odylith_context_engine_store._CONTRACT_PATH_PREFIXES):  # noqa: SLF001
            edges.append(
                {
                    "source_path": rel_path,
                    "relation": "references_contract",
                    "target_path": target_path,
                    "metadata": {"module_name": module_name},
                }
            )
    return (
        {
            "path": rel_path,
            "module_name": module_name,
            "layer": module_name.split(".", 1)[0] if module_name else "",
            "imports": sorted(imports),
            "contract_refs": sorted(
                path_ref
                for path_ref in contract_refs
                if path_ref.startswith(odylith_context_engine_store._CONTRACT_PATH_PREFIXES)  # noqa: SLF001
            ),
            "metadata": {},
        },
        edges,
    )


def _module_command_to_path(
    *,
    repo_root: Path,
    module_token: str,
    module_index: Mapping[str, str],
) -> str:
    token = str(module_token or "").strip()
    if not token:
        return ""
    normalized = token.replace("/", ".").strip(".")
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    if normalized in module_index:
        return str(module_index[normalized]).strip()
    candidate = Path(normalized.replace(".", "/") + ".py").as_posix()
    return candidate if (repo_root / candidate).is_file() else ""


def _relation_for_target_path(target_path: str) -> str:
    from odylith.runtime.context_engine import odylith_context_engine_store

    normalized = str(target_path or "").strip()
    if normalized.startswith(odylith_context_engine_store._CONTRACT_PATH_PREFIXES):  # noqa: SLF001
        return "references_contract"
    if normalized.startswith("tests/"):
        return "runs_test"
    return "invokes_code"


def _load_make_artifacts(
    *,
    repo_root: Path,
    module_index: Mapping[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    artifacts: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    candidates = [repo_root / "Makefile"]
    mk_root = repo_root / "mk"
    if mk_root.is_dir():
        candidates.extend(sorted(mk_root.rglob("*.mk")))
    for path in candidates:
        if not path.is_file():
            continue
        rel_path = path.relative_to(repo_root).as_posix()
        invoked_paths: set[str] = set()
        contract_refs: set[str] = set()
        targets: set[str] = set()
        current_target = ""
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = str(raw).rstrip()
            stripped = line.strip()
            match = odylith_context_engine_store._MAKE_TARGET_RE.match(line)  # noqa: SLF001
            if match is not None:
                current_target = str(match.group(1) or "").strip()
                if current_target and not current_target.startswith(".") and "%" not in current_target and "/" not in current_target:
                    targets.add(current_target)
                continue
            if not current_target or not stripped or stripped.startswith("#"):
                continue
            path_refs = set(
                odylith_context_engine_store._extract_path_refs(text=stripped, repo_root=repo_root)  # noqa: SLF001
            )
            for module_token in odylith_context_engine_store._PYTHON_MODULE_COMMAND_RE.findall(stripped):  # noqa: SLF001
                resolved = _module_command_to_path(
                    repo_root=repo_root,
                    module_token=str(module_token),
                    module_index=module_index,
                )
                if resolved:
                    path_refs.add(resolved)
            for target_path in sorted(path_refs):
                relation = _relation_for_target_path(target_path)
                if relation == "references_contract":
                    contract_refs.add(target_path)
                else:
                    invoked_paths.add(target_path)
                edges.append(
                    {
                        "source_path": rel_path,
                        "relation": relation,
                        "target_path": target_path,
                        "metadata": {
                            "target": current_target,
                            "source_kind": "make",
                        },
                    }
                )
        artifacts.append(
            {
                "path": rel_path,
                "module_name": "",
                "layer": "make",
                "imports": sorted(invoked_paths),
                "contract_refs": sorted(contract_refs),
                "metadata": {"targets": sorted(targets)},
            }
        )
    return artifacts, edges


def _doc_source_paths(*, repo_root: Path) -> list[Path]:
    rows: dict[str, Path] = {}
    docs_root = repo_root / "docs"
    if docs_root.is_dir():
        for path in docs_root.rglob("*.md"):
            if path.is_file():
                rows[str(path.resolve())] = path.resolve()
    guidelines_root = repo_root / "agents-guidelines"
    if guidelines_root.is_dir():
        for glob in ("*.md", "*.MD"):
            for path in guidelines_root.rglob(glob):
                if path.is_file():
                    rows[str(path.resolve())] = path.resolve()
    return [rows[key] for key in sorted(rows)]


def _load_doc_relationship_edges(*, repo_root: Path) -> list[dict[str, Any]]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    edges: list[dict[str, Any]] = []
    for path in _doc_source_paths(repo_root=repo_root):
        rel_path = path.relative_to(repo_root).as_posix()
        relation = "runbook_covers_code" if rel_path.startswith("docs/runbooks/") else "documents_code"
        for target_path in odylith_context_engine_store._extract_path_refs(  # noqa: SLF001
            text=odylith_context_engine_store._raw_text(path),  # noqa: SLF001
            repo_root=repo_root,
        ):
            target_relation = _relation_for_target_path(target_path)
            edges.append(
                {
                    "source_path": rel_path,
                    "relation": relation if target_relation != "references_contract" else "references_contract",
                    "target_path": target_path,
                    "metadata": {
                        "source_kind": "runbook" if rel_path.startswith("docs/runbooks/") else "doc",
                    },
                }
            )
    return edges


def _load_traceability_doc_code_edges_from_rows(trace_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_workstream: dict[str, dict[str, set[str]]] = {}
    for row in trace_rows:
        if not isinstance(row, Mapping):
            continue
        target_kind = str(row.get("target_kind", "")).strip()
        if target_kind not in {"runbook", "doc", "code"}:
            continue
        source_kind = str(row.get("source_kind", "")).strip()
        if source_kind != "workstream":
            continue
        source_id = str(row.get("source_id", "")).strip().upper()
        if not source_id:
            continue
        workstream_bucket = by_workstream.setdefault(source_id, {"runbook": set(), "doc": set(), "code": set()})
        target_id = str(row.get("target_id", "")).strip()
        if target_id:
            workstream_bucket[target_kind].add(target_id)
    edges: list[dict[str, Any]] = []
    for source_id, bucket in by_workstream.items():
        code_paths = sorted(bucket["code"])
        for runbook_path in sorted(bucket["runbook"]):
            for code_path in code_paths:
                edges.append(
                    {
                        "source_path": runbook_path,
                        "relation": "runbook_covers_code",
                        "target_path": code_path,
                        "metadata": {"workstream_id": source_id, "source_kind": "traceability"},
                    }
                )
        for doc_path in sorted(bucket["doc"]):
            for code_path in code_paths:
                edges.append(
                    {
                        "source_path": doc_path,
                        "relation": "documents_code",
                        "target_path": code_path,
                        "metadata": {"workstream_id": source_id, "source_kind": "traceability"},
                    }
                )
    return edges


def _load_traceability_doc_code_edges(connection: Any) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT source_kind, source_id, target_kind, target_id FROM traceability_edges WHERE target_kind IN ('runbook', 'doc', 'code')"
    ).fetchall()
    return _load_traceability_doc_code_edges_from_rows(rows)


def _load_code_graph(
    *,
    repo_root: Path,
    connection: Any | None = None,
    trace_rows: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from odylith.runtime.context_engine import odylith_context_engine_store

    module_index = _collect_python_module_index(repo_root)
    artifacts: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for module_name, rel_path in sorted(module_index.items()):
        artifact, artifact_edges = _parse_python_artifact(
            repo_root=repo_root,
            rel_path=rel_path,
            module_name=module_name,
            module_index=module_index,
        )
        artifacts.append(artifact)
        edges.extend(artifact_edges)
    make_artifacts, make_edges = _load_make_artifacts(repo_root=repo_root, module_index=module_index)
    artifacts.extend(make_artifacts)
    edges.extend(make_edges)
    edges.extend(_load_doc_relationship_edges(repo_root=repo_root))
    if trace_rows is not None:
        edges.extend(_load_traceability_doc_code_edges_from_rows(trace_rows))
    elif connection is not None:
        edges.extend(_load_traceability_doc_code_edges(connection))
    else:
        raise RuntimeError("traceability rows or connection required for code graph compilation")
    return artifacts, odylith_context_engine_store._dedupe_code_edges(edges)  # noqa: SLF001
