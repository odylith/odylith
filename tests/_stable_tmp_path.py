from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest


def stable_tmp_path(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a tmp path keyed by full node id instead of pytest's truncated prefix."""

    nodeid = request.node.nodeid
    safe_prefix = re.sub(r"[^A-Za-z0-9_.-]+", "_", nodeid).strip("_") or "test"
    digest = hashlib.sha256(nodeid.encode("utf-8")).hexdigest()[:12]
    return tmp_path_factory.mktemp(f"{safe_prefix[:40]}-{digest}", numbered=False)
