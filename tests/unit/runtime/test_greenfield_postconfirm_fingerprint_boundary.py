from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import (
    _POSTCONFIRM_RUNTIME_SOURCE_FILES,
    build_product_create_transaction_compiler_identity,
)
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)


def test_compiler_identity_covers_only_the_commit_runtime_boundary() -> None:
    paths = set(_POSTCONFIRM_RUNTIME_SOURCE_FILES)

    assert PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION == (
        "odylith.greenfield.compiler_identity.v12"
    )
    assert build_product_create_transaction_compiler_identity()["version"] == (
        PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION
    )
    assert "cli.py" in paths
    assert "runtime/domain_intelligence/greenfield_create_cli.py" in paths
    assert "runtime/domain_intelligence/greenfield_commit_transaction.py" in paths
    assert "runtime/domain_intelligence/greenfield_proposals_cli.py" not in paths
    assert "runtime/surfaces/greenfield_host_confirmation.py" not in paths
    assert "runtime/domain_intelligence/greenfield_transaction_compiler.py" not in paths
    assert "runtime/domain_intelligence/greenfield_semantic_proposal.py" not in paths


def test_public_compiler_has_no_repair_contract() -> None:
    parameters = inspect.signature(
        greenfield_proposals_cli._compile_prompt_evidence_transaction  # noqa: SLF001
    ).parameters
    assert "repair_tier" not in parameters
    assert "proposal_ready" not in parameters

    with pytest.raises(SystemExit):
        greenfield_proposals_cli._parse_args(  # noqa: SLF001
            [
                "compile-transaction",
                "--prompt",
                "Build a product",
                "--semantic-intent-file",
                "intent.json",
                "--repair-tier",
                "auto",
            ]
        )


def test_public_graph_compile_then_commit_loads_no_semantic_authority(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).resolve().parents[3]
    shutil.copytree(root / "src/odylith/bundle/assets/odylith", tmp_path / "odylith")
    packet_path = tmp_path / "semantic-intent.json"
    packet_path.write_text(json.dumps(semantic_intent_packet()), encoding="utf-8")
    assert greenfield_proposals_cli.main(
        [
            "compile-transaction",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            SEMANTIC_PROMPT,
            "--semantic-intent-file",
            str(packet_path),
            "--format",
            "json",
        ]
    ) == 0
    compiled = json.loads(capsys.readouterr().out)
    transaction_path = Path(str(compiled["transaction_file"]))
    transaction_hash = str(compiled["product_create_transaction"]["transaction_hash"])

    script = """
import json
import sys
from odylith.runtime.domain_intelligence import greenfield_create_cli
banned = {
    'greenfield_actor_action_relation_ledger',
    'greenfield_atomic_fact_ledger',
    'greenfield_product_intent_envelope',
    'greenfield_semantic_compiler',
    'greenfield_semantic_model',
}
before = set(sys.modules)
rc = greenfield_create_cli.main([
    'create', '--repo-root', sys.argv[1], '--transaction-file', sys.argv[2],
    '--transaction-hash', sys.argv[3], '--confirm', '--json',
])
loaded = sorted(
    name for name in set(sys.modules) - before
    if name.rsplit('.', 1)[-1] in banned
)
print(json.dumps({'rc': rc, 'loaded': loaded}, sort_keys=True))
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = "src:."
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path),
            str(transaction_path),
            transaction_hash,
        ],
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert json.loads(result.stdout.strip().splitlines()[-1]) == {
        "loaded": [],
        "rc": 0,
    }
