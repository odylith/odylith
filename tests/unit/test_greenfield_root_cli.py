from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from tests.unit.runtime.greenfield_baseline_fixtures import activate_greenfield_baseline_fixture
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    clarification_response,
)


def test_greenfield_help_describes_complete_preconfirm_package(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["greenfield", "--help"])

    output = capsys.readouterr().out.lower()
    assert excinfo.value.code == 0
    assert "provider-free" not in output
    assert "complete" in output
    assert "before confirmation" in output


def test_greenfield_create_help_exposes_precompiled_transaction_contract(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["greenfield", "create", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith greenfield create" in output
    assert "--transaction-file" in output
    assert "--transaction-hash" in output
    assert "--confirm" in output
    assert "--intent-file" not in output
    assert "--confirm-intent" not in output


def test_greenfield_propose_command_returns_one_model_authored_clarification(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    activate_greenfield_baseline_fixture(tmp_path)
    publication = (tmp_path / "odylith/index.html").read_bytes()
    baseline = greenfield_repository_write_set.greenfield_managed_fingerprints(tmp_path)
    provider = StructuredAuthoringProvider(
        clarification_response(
            question="unused test metadata",
            material_dimension="first_path",
            evidence_quotes=(),
        )
    )
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (provider, "test-model", "low"),
    )
    rc = cli.main(
        [
            "greenfield",
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Build an ecommerce site",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["mode"] == "clarification_required"
    clarification = payload["clarification"]
    assert clarification["question"] == (
        "Who uses this product first, what complete task do they finish, "
        "and what result do they see?"
    )
    assert clarification["required_fields"] == ["first_path"]
    assert clarification["consistency_assessment"]["status"] == "material_ambiguity"
    assert provider.calls == 1
    assert (tmp_path / "odylith/index.html").read_bytes() == publication
    assert greenfield_repository_write_set.greenfield_managed_fingerprints(tmp_path) == baseline
    assert not (tmp_path / ".odylith/runtime/greenfield/pending").exists()
    assert "provider_calls" not in payload
    assert "host_reasoning_task" not in payload
    assert "backlog" not in payload
    assert "components" not in payload
    assert "diagrams" not in payload
