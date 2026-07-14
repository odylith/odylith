from __future__ import annotations

import pytest

from odylith import cli


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
