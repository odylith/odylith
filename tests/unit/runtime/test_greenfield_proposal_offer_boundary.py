"""Public review output offers only the qualified terminal decision channel."""

from types import SimpleNamespace
import json

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_cli, greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from tests.unit.runtime.greenfield_authored_proposal_fixtures import (
    canonical_model_authored_intent_fixture,
)


def test_authored_proposal_retains_original_untrusted_source_for_edit(tmp_path) -> None:
    confirmed_intent = canonical_model_authored_intent_fixture(tmp_path)
    source = confirmed_intent["prompt"]

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=source,
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
        require_completion_ready=False,
    )

    assert proposal["intent"]["prompt"] == source


@pytest.mark.parametrize("command", ["propose", "compile-transaction"])
@pytest.mark.parametrize("output_format", ["text", "json"])
def test_public_preview_offers_three_hash_bound_terminal_decisions(
    tmp_path, monkeypatch, capsys, command, output_format,
) -> None:
    """Exercise public rendering; semantic compilation is a separate proof lane."""
    transaction_hash = "a" * 64
    staged_path = tmp_path / ".odylith/runtime/greenfield/pending" / transaction_hash / "product-create-transaction.v1.json"
    summary = {
        "transaction_hash": transaction_hash,
        "quality_status": "passed",
        "validation_status": "passed",
        "repository_write_count": 3,
        "repository_delete_count": 0,
    }
    transaction = SimpleNamespace(
        transaction_hash=transaction_hash,
        summary=lambda: dict(summary),
        quality_manifest={},
        intent_authority={"product_facts_sha256": "b" * 64},
        prewrite_package=SimpleNamespace(
            backlog_result={"created": [{}]},
            component_registry_preview=({},),
            rendered_atlas_sources={"context": "sealed diagram"},
        ),
    )
    monkeypatch.setattr(
        greenfield_proposals_cli, "_compile_prompt_evidence_transaction",
        lambda **_kwargs: ({"title": "Example"}, transaction, staged_path),
    )
    monkeypatch.setattr(greenfield_proposals_cli, "_public_intent_hypothesis", lambda value: value)
    monkeypatch.setattr(greenfield_proposals_cli, "render_product_intent_preview", lambda _value: "Product story: Example")
    monkeypatch.setattr(
        greenfield_proposals_cli.greenfield_proposals,
        "product_create_transaction_to_dict", lambda value: value.summary(),
    )
    candidate_path = tmp_path.parent / f"{tmp_path.name}-host-candidate.json"
    candidate_path.write_text("{}\n", encoding="utf-8")

    assert greenfield_proposals_cli.main([
        command, "--repo-root", str(tmp_path), "--prompt", "Example",
        "--candidate-file", str(candidate_path),
        "--format", output_format,
    ]) == 0
    output = capsys.readouterr().out

    assert transaction_hash in output
    assert "ordinary chat approval" in output.lower()
    assert "odylith greenfield create" not in output
    assert "--confirm" not in output
    if output_format == "json":
        payload = json.loads(output)
        assert payload["product_create_transaction"] == summary
        confirmation = payload["confirmation"]
        assert confirmation["status"] == "terminal_only"
        assert confirmation["interface"] == "terminal"
        assert len(confirmation["choices"]) == 3
        for decision, choice in zip(("CONFIRM", "EDIT", "REJECT"), confirmation["choices"], strict=True):
            assert set(choice) == {"command", "label"}
            assert choice["label"].strip()
            assert choice["command"].startswith("odylith greenfield decide ")
            assert decision in choice["command"]
            assert transaction_hash in choice["command"]
    else:
        assert "Choose one command" in output
        assert output.count("odylith greenfield decide ") == 3
        for decision in ("CONFIRM", "EDIT", "REJECT"):
            assert decision in output
        assert output.count(transaction_hash) >= 3
        assert "1 workstreams, 1 component previews, 1 Atlas previews" in output
        assert "quality gate: passed" in output
    assert not list(tmp_path.iterdir())


def test_explicit_create_keeps_its_separate_deterministic_dispatch(monkeypatch) -> None:
    arguments = ["create", "--transaction-file", "reviewed.json", "--transaction-hash", "a" * 64, "--confirm"]
    received = []
    monkeypatch.setattr(greenfield_create_cli, "main", lambda value: received.append(value) or 7)
    monkeypatch.setattr(
        greenfield_proposals_cli, "_parse_args",
        lambda *_args: pytest.fail("Explicit create must not enter proposal rendering or compilation"),
    )
    assert greenfield_proposals_cli.main(arguments) == 7
    assert received == [arguments]


def test_retired_apply_does_not_offer_an_unqualified_publication(tmp_path, capsys) -> None:
    assert greenfield_proposals_cli.main(["apply", "--repo-root", str(tmp_path)]) != 0
    output = capsys.readouterr().out
    assert "disabled" in output
    assert "read-only" in output
    assert "No governed records were written" in output
    assert "greenfield create" not in output
    assert "--confirm" not in output
    assert not list(tmp_path.iterdir())
