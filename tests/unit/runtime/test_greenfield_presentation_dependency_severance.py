"""Pin presentation modules to typed inputs instead of legacy semantic authority."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys

from odylith.runtime.governance import component_spec_narrative
from odylith.runtime.surfaces import atlas_box_explanations


ROOT = Path(__file__).resolve().parents[3]
PRESENTATION_MODULES = (
    ROOT / "src/odylith/runtime/surfaces/atlas_box_explanations.py",
    ROOT / "src/odylith/runtime/governance/component_spec_narrative.py",
)


def test_presentation_modules_do_not_import_legacy_semantic_authority() -> None:
    forbidden_fragments = ("greenfield_confirmed_", "greenfield_first_path_")

    for path in PRESENTATION_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = (
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        imported_modules = tuple(imports)
        assert not any(
            fragment in module
            for module in imported_modules
            for fragment in forbidden_fragments
        ), path


def test_presentation_modules_do_not_load_legacy_semantic_authority() -> None:
    program = """
import importlib
import sys

importlib.import_module(sys.argv[1])
loaded = [
    name for name in sys.modules
    if "greenfield_confirmed_" in name or "greenfield_first_path_" in name
]
assert not loaded, loaded
"""
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    for module in (
        "odylith.runtime.surfaces.atlas_box_explanations",
        "odylith.runtime.governance.component_spec_narrative",
    ):
        subprocess.run(
            [sys.executable, "-c", program, module],
            cwd=ROOT,
            env=environment,
            check=True,
        )


def test_presentation_boundaries_do_not_reinterpret_free_form_prose() -> None:
    assert atlas_box_explanations._sentence_subject("eBPF gateway") == "eBPF gateway"
    responsibility = "turns raw evidence into an unsupported inferred verdict using hidden heuristics"
    rendered = component_spec_narrative.build_narrative_component_spec(
        component_id="decision-engine",
        label="Decision Engine",
        path="src/decision_engine",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-101",),
        responsibility=responsibility,
        component_contract={
            "owned_state": ["raw evidence", "decision record", "audit trail", "review status", "fifth fact"],
            "produced_outputs": ["source-cited decision result"],
        },
    )
    assert f"Responsibility: {responsibility}." in rendered
    for fact in ("raw evidence", "decision record", "audit trail", "review status", "fifth fact"):
        assert f"- {fact}." in rendered
    assert "calculated" not in rendered
    assert "rationale" not in rendered
