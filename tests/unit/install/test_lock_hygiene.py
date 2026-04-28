from __future__ import annotations

import os
import time
from pathlib import Path

from odylith.install.lock_hygiene import compact_stale_zero_byte_locks, lock_hygiene_summary


def test_lock_hygiene_scans_recursively_and_preserves_install_lock(tmp_path: Path) -> None:
    locks_dir = tmp_path / ".odylith" / "locks"
    nested = locks_dir / "odylith-context-engine"
    nested.mkdir(parents=True)
    stale = nested / "stale.lock"
    recent = nested / "recent.lock"
    active_install = locks_dir / "install.lock"
    nonzero = nested / "held.lock"
    for path in (stale, recent, active_install):
        path.touch()
    nonzero.write_text("123\n", encoding="utf-8")
    old_time = time.time() - 7200
    os.utime(stale, (old_time, old_time))
    os.utime(active_install, (old_time, old_time))

    before = lock_hygiene_summary(repo_root=tmp_path)
    after = compact_stale_zero_byte_locks(repo_root=tmp_path)

    assert before.total_files == 4
    assert before.zero_byte_files == 3
    assert before.stale_zero_byte_files == 1
    assert after.removed_files == 1
    assert not stale.exists()
    assert recent.exists()
    assert active_install.exists()
    assert nonzero.exists()
