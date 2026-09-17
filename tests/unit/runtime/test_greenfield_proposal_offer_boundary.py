"""Public review output cannot imply an unproved native confirmation channel."""

from types import SimpleNamespace
import json

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_cli, greenfield_proposals_cli


@pytest.mark.parametrize("command", ["propose", "compile-transaction"])
@pytest.mark.parametrize("output_format", ["text", "json"])
def test_public_preview_is_read_only_without_interface_qualification(
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

    assert greenfield_proposals_cli.main([
        command, "--repo-root", str(tmp_path), "--prompt", "Example",
        "--format", output_format,
    ]) == 0
    output = capsys.readouterr().out

    assert transaction_hash in output
    assert "CONFIRM " not in output
    assert "EDIT " not in output
    assert "REJECT " not in output
    assert "odylith greenfield create" not in output
    assert "--confirm" not in output
    assert "Choose one command" not in output
    if output_format == "json":
        payload = json.loads(output)
        assert payload["product_create_transaction"] == summary
        assert payload["confirmation"]["status"] == "read_only"
        assert payload["confirmation"]["choices"] == []
        assert "qualified" in payload["confirmation"]["reason"]
    else:
        assert "Review only" in output
        assert "1 workstreams, 1 component previews, 1 Atlas previews" in output
        assert "quality gate: passed" in output
        assert "qualified" in output
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
