from __future__ import annotations

import pytest

from odylith import cli


def test_greenfield_compile_transaction_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["greenfield", "compile-transaction", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith greenfield compile-transaction" in output
    assert "--prompt" in output
    assert "--intent-file" in output
    assert "--transaction-file" not in output
    assert "--output" in output
    assert "--format" in output
