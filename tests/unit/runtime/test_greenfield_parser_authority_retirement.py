"""Structural proof that Greenfield no longer ships the relation-free parser authority."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"

_RETIRED_MODULES = (
    "greenfield_canonical_meaning",
    "greenfield_atlas_semantic_coverage",
    "greenfield_component_kinds",
    "greenfield_component_term_constants",
    "greenfield_component_term_index",
    "greenfield_confirmed_completion",
    "greenfield_confirmed_intent",
    "greenfield_confirmed_intent_completion",
    "greenfield_confirmed_intent_context_completion",
    "greenfield_confirmed_intent_document",
    "greenfield_confirmed_intent_input",
    "greenfield_confirmed_intent_recovery",
    "greenfield_confirmed_intent_recovery_text",
    "greenfield_confirmed_intent_sections",
    "greenfield_confirmed_intent_validation",
    "greenfield_confirmed_prompt_source",
    "greenfield_confirmed_system_rows",
    "greenfield_confirmed_title_repair",
    "greenfield_gerund_actions",
    "greenfield_prompt_evidence_interpretation",
    "greenfield_preconfirm_patchset",
    "greenfield_preconfirm_repair",
    "greenfield_preconfirm_repair_context",
    "greenfield_preconfirm_rescue_planner",
    "greenfield_prewrite_projection_rerender",
    "greenfield_quality_lens_repair",
    "greenfield_recovered_intent_context",
    "greenfield_release_scope_limits",
    "greenfield_semantic_projection_surfaces",
    "greenfield_sequence_terminal_labels",
    "greenfield_source_casing",
    "greenfield_structured_first_path",
    "greenfield_transfer_phrases",
)
_RETIRED_ACTIVE_TOWER_PREFIXES = (
    "greenfield_first_path_",
    "greenfield_semantic_compiler",
    "greenfield_semantic_model",
)
_RETIRED_MECHANISM_MODULES = (
    "greenfield_component_contract",
    "greenfield_confirmed_backlog",
    "greenfield_confirmed_components",
    "greenfield_confirmed_diagrams",
    "greenfield_product_risks",
    "greenfield_project_brief",
    "greenfield_quality_gate",
    "greenfield_semantic_quality",
    "proposal_normalization",
    "proposal_rendering",
    "proposal_tribunal_substance",
)
_CANONICAL_SEMANTIC_BOUNDARY_PATHS = (
    DOMAIN_INTELLIGENCE / "greenfield_apply_components.py",
    DOMAIN_INTELLIGENCE / "greenfield_authored_semantics.py",
    DOMAIN_INTELLIGENCE / "greenfield_create_transaction.py",
    DOMAIN_INTELLIGENCE / "greenfield_model_atomic_projection.py",
    DOMAIN_INTELLIGENCE / "greenfield_model_intent_authoring.py",
    DOMAIN_INTELLIGENCE / "greenfield_model_intent_materialization.py",
    DOMAIN_INTELLIGENCE / "greenfield_preconfirm_engine.py",
    DOMAIN_INTELLIGENCE / "greenfield_preconfirm_findings.py",
    DOMAIN_INTELLIGENCE / "greenfield_product_intent_envelope.py",
    DOMAIN_INTELLIGENCE / "greenfield_project_intelligence.py",
    DOMAIN_INTELLIGENCE / "greenfield_proposals.py",
    DOMAIN_INTELLIGENCE / "greenfield_proposals_cli.py",
    DOMAIN_INTELLIGENCE / "greenfield_traceability.py",
    DOMAIN_INTELLIGENCE / "proposal_tribunal.py",
    ROOT / "src/odylith/runtime/project_intelligence/greenfield_authored_dashboard.py",
)
_DETACHED_AUTHORED_PRECONFIRM_PATHS = (
    DOMAIN_INTELLIGENCE / "greenfield_apply_prewrite.py",
    DOMAIN_INTELLIGENCE / "greenfield_preconfirm_completion.py",
    DOMAIN_INTELLIGENCE / "greenfield_preconfirm_findings.py",
    DOMAIN_INTELLIGENCE / "greenfield_preconfirm_handoff_quality.py",
    DOMAIN_INTELLIGENCE / "greenfield_preconfirm_package_findings.py",
    DOMAIN_INTELLIGENCE / "greenfield_preconfirm_package_hygiene.py",
    DOMAIN_INTELLIGENCE / "greenfield_preconfirm_semantic_alignment.py",
    DOMAIN_INTELLIGENCE / "greenfield_programs.py",
    DOMAIN_INTELLIGENCE / "project_intelligence_binding.py",
    DOMAIN_INTELLIGENCE / "proposal_validation.py",
)
_PARSER_ERA_IMPORTS = {
    "greenfield_domain_term_index",
    "greenfield_source_casing",
    "greenfield_text",
}


def test_relation_free_parser_authority_files_and_source_edges_are_absent() -> None:
    retired = (*_RETIRED_MODULES, *_RETIRED_MECHANISM_MODULES)
    assert [name for name in retired if (DOMAIN_INTELLIGENCE / f"{name}.py").exists()] == []
    assert [
        path.name
        for path in DOMAIN_INTELLIGENCE.glob("*.py")
        if any(path.stem.startswith(prefix) for prefix in _RETIRED_ACTIVE_TOWER_PREFIXES)
    ] == []
    regex_importers: list[str] = []
    for path in _CANONICAL_SEMANTIC_BOUNDARY_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            (isinstance(node, ast.Import) and any(alias.name == "re" for alias in node.names))
            or (isinstance(node, ast.ImportFrom) and node.module == "re")
            for node in ast.walk(tree)
        ):
            regex_importers.append(str(path.relative_to(ROOT)))
    assert regex_importers == []

    source_files = tuple((ROOT / "src/odylith").rglob("*.py"))
    stale_edges: dict[str, str] = {}
    for path in source_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: set[str] = set()
            if isinstance(node, ast.Import):
                imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith(
                    "odylith.runtime.domain_intelligence.greenfield_"
                ):
                    imported.add(node.module.rsplit(".", 1)[-1])
                elif node.module == "odylith.runtime.domain_intelligence":
                    imported.update(alias.name for alias in node.names)
            for name in imported.intersection(retired):
                stale_edges[str(path.relative_to(ROOT))] = name
    assert stale_edges == {}


def test_public_greenfield_imports_cannot_load_retired_parser_authority() -> None:
    probe = """
import sys
import tempfile
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_product_intent_envelope
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import combined_prompt_evidence_source
from tests.unit.runtime.greenfield_model_authoring_fixtures import StructuredAuthoringProvider
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source

source = _source()
evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
provider = StructuredAuthoringProvider(_response(evidence))
greenfield_proposals_cli._greenfield_authoring_provider = (
    lambda **_kwargs: (provider, "test-model", "low")
)
with tempfile.TemporaryDirectory(prefix="greenfield-parser-retirement-") as repo_root:
    result = greenfield_proposals_cli.main(
        ["propose", "--repo-root", repo_root, "--prompt", source, "--format", "json"]
    )
if result != 0:
    raise SystemExit(f"public Greenfield proposal failed with exit code {{result}}")

retired = {retired!r}
retired_prefixes = {retired_prefixes!r}
loaded = sorted(
    module
    for module in sys.modules
    if any(module.endswith(name) for name in retired)
    or any(module.rsplit(".", 1)[-1].startswith(prefix) for prefix in retired_prefixes)
)
if loaded:
    raise SystemExit(f"retired Greenfield parser modules loaded: {{loaded}}")
""".format(
        retired=_RETIRED_MODULES,
        retired_prefixes=_RETIRED_ACTIVE_TOWER_PREFIXES,
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_authored_preconfirm_owners_do_not_import_parser_era_helpers() -> None:
    stale_edges: dict[str, list[str]] = {}
    for path in _DETACHED_AUTHORED_PRECONFIRM_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module == "odylith.runtime.domain_intelligence":
                    imported.update(alias.name for alias in node.names)
                elif node.module:
                    imported.add(node.module.rsplit(".", 1)[-1])
        stale = sorted(imported.intersection(_PARSER_ERA_IMPORTS))
        if stale:
            stale_edges[str(path.relative_to(ROOT))] = stale
    assert stale_edges == {}

    scalar_owner = DOMAIN_INTELLIGENCE / "greenfield_scalar_values.py"
    scalar_tree = ast.parse(
        scalar_owner.read_text(encoding="utf-8"),
        filename=str(scalar_owner),
    )
    assert not any(
        (isinstance(node, ast.Import) and any(alias.name == "re" for alias in node.names))
        or (isinstance(node, ast.ImportFrom) and node.module == "re")
        for node in ast.walk(scalar_tree)
    )


def test_importing_authored_preconfirm_engine_cannot_load_parser_era_helpers() -> None:
    probe = """
import sys
import odylith.runtime.domain_intelligence.greenfield_preconfirm_engine

forbidden = {forbidden!r}
loaded = sorted(
    module
    for module in sys.modules
    if module.rsplit(".", 1)[-1] in forbidden
)
if loaded:
    raise SystemExit(f"parser-era Greenfield helper modules loaded: {{loaded}}")
""".format(forbidden=_PARSER_ERA_IMPORTS)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
