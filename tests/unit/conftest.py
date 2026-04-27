from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests._stable_tmp_path import stable_tmp_path


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = stable_tmp_path(request, tmp_path_factory)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
