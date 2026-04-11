from __future__ import annotations

import threading
import time
from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_daemon_wait_runtime as wait_runtime


def test_wait_for_projection_change_returns_immediately_for_new_current_fingerprint(tmp_path: Path) -> None:
    payload = wait_runtime.wait_for_projection_change(
        repo_root=tmp_path,
        since_fingerprint="old",
        current_fingerprint="new",
        timeout_seconds=0.1,
    )

    assert payload == {
        "changed": True,
        "projection_fingerprint": "new",
    }


def test_wait_for_projection_change_wakes_when_fingerprint_changes(tmp_path: Path) -> None:
    result: dict[str, object] = {}

    def _wait() -> None:
        result.update(
            wait_runtime.wait_for_projection_change(
                repo_root=tmp_path,
                since_fingerprint="seed",
                current_fingerprint="seed",
                timeout_seconds=1.0,
            )
        )

    wait_runtime.record_projection_fingerprint(repo_root=tmp_path, projection_fingerprint="seed")
    thread = threading.Thread(target=_wait, daemon=True)
    thread.start()
    time.sleep(0.05)
    wait_runtime.record_projection_fingerprint(repo_root=tmp_path, projection_fingerprint="next")
    thread.join(timeout=2)

    assert result == {
        "changed": True,
        "projection_fingerprint": "next",
    }


def test_wait_for_projection_change_times_out_without_update(tmp_path: Path) -> None:
    wait_runtime.record_projection_fingerprint(repo_root=tmp_path, projection_fingerprint="same")

    payload = wait_runtime.wait_for_projection_change(
        repo_root=tmp_path,
        since_fingerprint="same",
        current_fingerprint="same",
        timeout_seconds=0.01,
    )

    assert payload == {
        "changed": False,
        "projection_fingerprint": "same",
    }
