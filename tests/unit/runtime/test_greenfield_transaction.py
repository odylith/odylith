from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction


def test_greenfield_apply_transaction_rolls_back_tooling_shell_outputs(tmp_path) -> None:
    shell_root = tmp_path / "odylith"
    shell_root.mkdir()
    index_path = shell_root / "index.html"
    payload_path = shell_root / "tooling-payload.v1.js"
    app_path = shell_root / "tooling-app.v1.js"
    index_path.write_text("old index\n", encoding="utf-8")
    payload_path.write_text("old payload\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="late refresh failure"):
        with GreenfieldApplyTransaction(tmp_path):
            index_path.write_text("new index\n", encoding="utf-8")
            payload_path.unlink()
            app_path.write_text("new app\n", encoding="utf-8")
            raise RuntimeError("late refresh failure")

    assert index_path.read_text(encoding="utf-8") == "old index\n"
    assert payload_path.read_text(encoding="utf-8") == "old payload\n"
    assert not app_path.exists()
