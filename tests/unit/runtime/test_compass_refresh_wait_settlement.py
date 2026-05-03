from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.surfaces import compass_refresh_wait_settlement


def test_unsettled_global_windows_treats_intentional_skip_as_settled(tmp_path: Path) -> None:
    runtime_path = tmp_path / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(
        json.dumps(
            {
                "standup_brief": {
                    "24h": {
                        "status": "unavailable",
                        "source": "unavailable",
                        "diagnostics": {"reason": "skipped_not_worth_calling"},
                    },
                    "48h": {
                        "status": "ready",
                        "source": "provider",
                        "generated_utc": "2026-05-01T00:00:00Z",
                        "diagnostics": {},
                    },
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert compass_refresh_wait_settlement.unsettled_global_windows(repo_root=tmp_path) == ()
