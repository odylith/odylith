from __future__ import annotations

import ast
import copy
import inspect
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from odylith.runtime.domain_intelligence import greenfield_product_intent_binding
from odylith.runtime.domain_intelligence import greenfield_sealed_product_intent_authority
from odylith.runtime.domain_intelligence.greenfield_apply_diagrams import (
    materialize_apply_diagrams,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_binding import (
    rebind_authoritative_product_facts,
    require_authoritative_intent_binding,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    require_product_intent_authority_structure,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
    compile_verified_semantic_transaction,
)
from odylith.runtime.domain_intelligence.greenfield_prewrite_surface_stage import (
    materialize_staged_greenfield_surfaces,
)
from odylith.runtime.domain_intelligence.greenfield_prewrite_transaction_seal import (
    GreenfieldPrewriteSealRequest,
)
from odylith.runtime.domain_intelligence.greenfield_surface_refresh_proof import (
    build_prewrite_surface_refresh_preview,
)
from odylith.runtime.domain_intelligence.greenfield_transaction_compiler import (
    compile_sealed_greenfield_transaction,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)


_SEAM_PATHS = (
    "src/odylith/runtime/domain_intelligence/greenfield_sealed_product_intent_authority.py",
    "src/odylith/runtime/domain_intelligence/greenfield_product_intent_binding.py",
    "src/odylith/runtime/domain_intelligence/greenfield_transaction_compiler.py",
    "src/odylith/runtime/domain_intelligence/greenfield_semantic_workflow.py",
    "src/odylith/runtime/domain_intelligence/greenfield_compiled_package_contract.py",
    "src/odylith/runtime/domain_intelligence/greenfield_prewrite_surface_stage.py",
)
_FORBIDDEN_IMPORTS = {
    "odylith.runtime.domain_intelligence.greenfield_actor_action_relation_ledger",
    "odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger",
    "odylith.runtime.domain_intelligence.greenfield_product_intent_envelope",
    "odylith.runtime.domain_intelligence.greenfield_preconfirm_completion",
    "odylith.runtime.domain_intelligence.greenfield_preconfirm_engine",
    "odylith.runtime.domain_intelligence.greenfield_preconfirm_repair",
    "odylith.runtime.domain_intelligence.proposal_tribunal",
}
_REMOVED_AUTHORITY_PREFIXES = (
    "greenfield_confirmed_",
    "greenfield_first_path_",
    "greenfield_prompt_evidence_",
)
_REMOVED_AUTHORITY_FILES = ("greenfield_prompt_intent_materiality.py",)
_GRAPH_COMPILE_GREENFIELD_MODULES = {
    "greenfield_acceptance_contract",
    "greenfield_acceptance_identity",
    "greenfield_apply_diagrams",
    "greenfield_apply_prewrite",
    "greenfield_backlog_commit",
    "greenfield_candidate_intent_stage",
    "greenfield_commit_transaction",
    "greenfield_compiled_memory_write",
    "greenfield_compiled_package_contract",
    "greenfield_completion_types",
    "greenfield_confirmation_rail",
    "greenfield_create_baseline",
    "greenfield_create_contract",
    "greenfield_create_manifest",
    "greenfield_create_transaction",
    "greenfield_generation_state",
    "greenfield_operating_envelope",
    "greenfield_pending_transaction_store",
    "greenfield_prewrite_commit_result",
    "greenfield_prewrite_stage_root",
    "greenfield_prewrite_stale_cleanup",
    "greenfield_prewrite_surface_stage",
    "greenfield_prewrite_transaction_seal",
    "greenfield_product_intent_binding",
    "greenfield_proposals_cli",
    "greenfield_release_commit",
    "greenfield_release_contract",
    "greenfield_repository_write_set",
    "greenfield_rows",
    "greenfield_sealed_product_intent_authority",
    "greenfield_semantic_atlas_materialization",
    "greenfield_semantic_atomic_source_custody",
    "greenfield_semantic_authoring_contract",
    "greenfield_semantic_backlog_projection",
    "greenfield_semantic_component_package",
    "greenfield_semantic_component_projection",
    "greenfield_semantic_delivery",
    "greenfield_semantic_diagrams",
    "greenfield_semantic_graph_contract",
    "greenfield_semantic_execution_contract",
    "greenfield_semantic_graph_author_output",
    "greenfield_semantic_graph_extension",
    "greenfield_semantic_graph_extension_contract",
    "greenfield_semantic_host_profiles",
    "greenfield_semantic_identifiers",
    "greenfield_semantic_intent_contract",
    "greenfield_semantic_intent_schema",
    "greenfield_semantic_materiality_contract",
    "greenfield_semantic_intent_packet",
    "greenfield_semantic_memory",
    "greenfield_semantic_package_validation",
    "greenfield_semantic_preconfirm",
    "greenfield_semantic_projection_plan",
    "greenfield_semantic_projection_validation",
    "greenfield_semantic_proposal",
    "greenfield_semantic_radar_write",
    "greenfield_semantic_traceability",
    "greenfield_semantic_workflow",
    "greenfield_semantic_source_citations",
    "greenfield_semantic_source_claims",
    "greenfield_surface_refresh_proof",
    "greenfield_traceability_commit",
    "greenfield_traceability_contract",
    "greenfield_transaction_compiler",
}


def test_legacy_semantic_authority_families_are_physically_absent() -> None:
    root = Path(__file__).resolve().parents[3]
    domain_root = root / "src/odylith/runtime/domain_intelligence"
    remaining = sorted(
        path.name
        for path in domain_root.glob("*.py")
        if path.name in _REMOVED_AUTHORITY_FILES
        or path.name.startswith(_REMOVED_AUTHORITY_PREFIXES)
    )
    assert remaining == []

    stale_imports: list[str] = []
    for path in (root / "src/odylith").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if any(prefix in source for prefix in _REMOVED_AUTHORITY_PREFIXES):
            stale_imports.append(str(path.relative_to(root)))
        if "greenfield_prompt_intent_materiality" in source:
            stale_imports.append(str(path.relative_to(root)))
    assert stale_imports == []


def _authority() -> tuple[dict[str, object], dict[str, object]]:
    verified = require_semantic_intent_packet(
        semantic_intent_packet(),
        prompt=SEMANTIC_PROMPT,
    )
    authority = semantic_intent_authority(verified, prompt=SEMANTIC_PROMPT)
    return authority, dict(verified.product_facts)


def test_graph_authority_rejects_legacy_authority_and_graph_shapes_without_fallback() -> None:
    authority, _facts = _authority()

    old_authority = copy.deepcopy(authority)
    old_authority["version"] = "odylith.product-intent-authority.v7"
    with pytest.raises(ValueError, match="unsupported version"):
        require_product_intent_authority_structure(old_authority)

    old_graph = copy.deepcopy(authority)
    old_graph["semantic_intent_ir_version"] = "odylith.greenfield.semantic-intent-ir.v1"
    with pytest.raises(ValueError, match="Semantic Intent authority is invalid"):
        require_product_intent_authority_structure(old_graph)

    old_packet = copy.deepcopy(authority)
    old_packet["semantic_intent_packet_version"] = (
        "odylith.greenfield.semantic-intent-packet.v2"
    )
    with pytest.raises(ValueError, match="Semantic Intent authority is invalid"):
        require_product_intent_authority_structure(old_packet)

    old_authoring_contract = copy.deepcopy(authority)
    old_authoring_contract["semantic_intent_authoring_contract_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Semantic Intent authority is invalid"):
        require_product_intent_authority_structure(old_authoring_contract)

    missing_graph = copy.deepcopy(authority)
    missing_graph.pop("semantic_intent")
    with pytest.raises(ValueError, match="Semantic Intent authority is malformed"):
        require_product_intent_authority_structure(missing_graph)


def test_graph_binding_uses_only_exact_semantic_product_facts() -> None:
    authority, facts = _authority()
    require_authoritative_intent_binding(facts, authority)

    drifted = dict(facts)
    drifted["product_story"] = "A projection silently changed the product story."
    with pytest.raises(ValueError, match="do not match"):
        require_authoritative_intent_binding(drifted, authority)

    rebound = rebind_authoritative_product_facts(
        {**drifted, "projection_note": "non-authoritative metadata"},
        authoritative_intent=facts,
        authority=authority,
    )
    assert rebound["product_story"] == facts["product_story"]
    assert rebound["projection_note"] == "non-authoritative metadata"


def test_graph_compiler_surface_has_no_legacy_or_repair_callback() -> None:
    assert tuple(inspect.signature(compile_sealed_greenfield_transaction).parameters) == (
        "repo_root",
        "proposal",
        "release_selector",
        "verified_semantic_prewrite",
    )
    assert tuple(inspect.signature(compile_verified_semantic_transaction).parameters) == (
        "repo_root",
        "proposal",
        "release_selector",
    )
    assert tuple(inspect.signature(materialize_apply_diagrams).parameters) == (
        "root",
        "diagram_ids",
        "rendered_atlas_sources",
        "compiled_catalog_rows",
    )
    assert tuple(inspect.signature(build_prewrite_surface_refresh_preview).parameters) == (
        "repo_root",
    )
    assert tuple(inspect.signature(materialize_staged_greenfield_surfaces).parameters) == (
        "prewrite_root",
        "proposal",
        "staged_component_registry_preview",
        "rendered_component_specs",
        "diagram_ids",
        "rendered_atlas_sources",
        "compiled_atlas_catalog_rows",
        "accepted_project_preview",
        "project_brief_record_text",
        "compass_memory_preview",
    )
    assert not {
        "diagram_rows",
        "staged_traceability_plan",
        "atlas_review_date",
    } & set(GreenfieldPrewriteSealRequest.__dataclass_fields__)


def test_graph_authority_seams_have_no_legacy_semantic_reachability() -> None:
    root = Path(__file__).resolve().parents[3]
    imported_modules: set[str] = set()
    sources: dict[str, str] = {}
    for relative in _SEAM_PATHS:
        source = (root / relative).read_text(encoding="utf-8")
        sources[relative] = source
        tree = ast.parse(source)
        imported_modules.update(
            str(node.module or "")
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        imported_modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )

    assert not (_FORBIDDEN_IMPORTS & imported_modules)
    combined = "\n".join(sources.values())
    for obsolete_name in (
        "legacy_prewrite",
        "_reject_legacy_prewrite",
        "atomic_facts",
        "actor_action_relations",
        "material_custody_sha256",
        "verified_semantic_graph",
    ):
        assert obsolete_name not in combined
    compiler_source = sources[
        "src/odylith/runtime/domain_intelligence/greenfield_transaction_compiler.py"
    ]
    assert '.get("origin")' not in compiler_source


def test_public_graph_compile_closure_has_no_prose_matching_stack() -> None:
    root = Path(__file__).resolve().parents[3]
    domain_root = root / "src/odylith/runtime/domain_intelligence"
    prohibited = {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
    violations: dict[str, list[str]] = {}
    for module_name in sorted(_GRAPH_COMPILE_GREENFIELD_MODULES):
        path = domain_root / f"{module_name}.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            str(node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        if found := sorted(prohibited & imports):
            violations[module_name] = found

    assert violations == {}


def test_graph_authority_module_exports_no_stale_envelope_or_ledger_contract() -> None:
    for obsolete_name in (
        "LEGACY_PRODUCT_INTENT_AUTHORITY_VERSION",
        "MATERIAL_FACT_KEYS",
        "PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION",
        "PRODUCT_INTENT_LEDGER_VERSION",
        "STRUCTURED_SOURCE_FORMATS",
        "TYPED_SOURCE_FORMATS",
        "product_intent_material_custody_hash",
    ):
        assert not hasattr(greenfield_sealed_product_intent_authority, obsolete_name)
    assert not hasattr(greenfield_product_intent_binding, "product_facts_hash")


def test_public_graph_proposal_loads_only_the_explicit_graph_transaction_closure() -> None:
    root = Path(__file__).resolve().parents[3]
    script = textwrap.dedent(
        """
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        import json
        import shutil
        import sys
        from tempfile import TemporaryDirectory
        from tests.unit.runtime.greenfield_semantic_intent_fixtures import SEMANTIC_PROMPT, semantic_intent_packet
        from odylith.runtime.domain_intelligence.greenfield_proposals_cli import main

        with TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(
                Path.cwd() / "src/odylith/bundle/assets/odylith",
                root / "odylith",
            )
            packet_path = root / "semantic-intent.json"
            packet_path.write_text(
                json.dumps(semantic_intent_packet()),
                encoding="utf-8",
            )
            with redirect_stdout(StringIO()):
                result = main(
                    [
                        "propose",
                        "--repo-root",
                        str(root),
                        "--prompt",
                        SEMANTIC_PROMPT,
                        "--semantic-intent-file",
                        str(packet_path),
                    ]
                )
            if result != 0:
                raise SystemExit("public graph proposal did not compile")
            transaction_paths = list(
                (root / ".odylith/runtime/greenfield/pending").glob(
                    "*/product-create-transaction.v1.json"
                )
            )
            if len(transaction_paths) != 1:
                raise SystemExit("public graph proposal did not stage exactly one transaction")
            transaction = json.loads(transaction_paths[0].read_text(encoding="utf-8"))
            if transaction["intent_authority"].get("version") != "odylith.product-intent-authority.v19":
                raise SystemExit("graph transaction changed its v15 authority")
            if transaction["compiler_provenance"].get("phase") != "pre_confirm_compile":
                raise SystemExit("graph transaction lost its pre-confirm compiler attestation")

        banned = {
            "greenfield_actor_action_relation_ledger",
            "greenfield_atomic_fact_ledger",
            "greenfield_product_intent_envelope",
            "greenfield_preconfirm_completion",
            "greenfield_preconfirm_engine",
            "greenfield_preconfirm_repair",
            "proposal_tribunal",
        }
        loaded = sorted(name for name in sys.modules if name.rsplit(".", 1)[-1] in banned)
        prefixes = (
            "greenfield_confirmed_",
            "greenfield_first_path_",
            "greenfield_prompt_evidence_",
        )
        loaded.extend(
            name
            for name in sys.modules
            if name.rsplit(".", 1)[-1].startswith(prefixes)
        )
        loaded = sorted(set(loaded))
        if loaded:
            raise SystemExit("legacy semantic authority modules loaded: " + ", ".join(loaded))

        allowed = %r
        loaded_greenfield = {
            name.rsplit(".", 1)[-1]
            for name in sys.modules
            if name.rsplit(".", 1)[-1].startswith("greenfield_")
        }
        loaded_greenfield.discard("greenfield_semantic_intent_fixtures")
        unexpected = sorted(loaded_greenfield - allowed)
        if unexpected:
            raise SystemExit(
                "graph compile loaded modules outside its explicit closure: "
                + ", ".join(unexpected)
            )
        """
        % _GRAPH_COMPILE_GREENFIELD_MODULES
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = "src:."
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
