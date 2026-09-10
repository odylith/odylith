from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

from odylith.runtime.governance import component_compiled_commit


def test_compiled_component_commit_preserves_exact_bytes(tmp_path: Path) -> None:
    result = component_compiled_commit.materialize_compiled_component(
        repo_root=tmp_path,
        registry_entry={
            "component_id": "sample-service",
            "name": "Sample Service",
            "kind": "service",
            "category": "application",
            "qualification": "candidate",
            "aliases": ("sample",),
            "path_prefixes": (Path("src/sample"),),
            "workstreams": ("B-001",),
            "diagrams": ("D-001",),
            "owner": "repo",
            "status": "planned",
            "what_it_is": "Sample.",
            "why_tracked": "Evidence.",
            "spec_ref": "odylith/registry/source/components/sample-service/CURRENT_SPEC.md",
            "sources": ("user_intent",),
            "subcomponents": (),
            "product_layer": "application",
            "ignored": "discarded",
        },
        spec_text="# Sample\n\nExact bytes.\n",
        validation_gate={"status": "passed"},
        refresh=False,
    )

    assert hashlib.sha256(result.registry_path.read_bytes()).hexdigest() == (
        "1aaae6db52bf89eef7e1da6cb55cf36bdc0478b8fdd4fbd38b056a1b5f54f095"
    )
    assert hashlib.sha256(result.spec_path.read_bytes()).hexdigest() == (
        "7e552805069e2fbcb35365d868546723f40a539847ab4c783667e614751ebc59"
    )


def test_greenfield_prewrite_import_does_not_load_phrase_interpreters() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import odylith.runtime.domain_intelligence.greenfield_apply_prewrite; "
                "assert 'odylith.runtime.domain_intelligence.greenfield_phrase_quality' not in sys.modules; "
                "assert 'odylith.runtime.domain_intelligence.greenfield_text' not in sys.modules"
            ),
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[3],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
