"""Access helpers for packaged bundle assets."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def bundle_root() -> Path:
    return Path(files("odylith.bundle").joinpath("assets", "odylith"))
