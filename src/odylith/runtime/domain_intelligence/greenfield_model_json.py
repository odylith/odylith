"""Canonical JSON bytes for Greenfield model requests and retained responses."""

from __future__ import annotations

import json
from typing import Any


def encode_greenfield_model_value(value: Any) -> bytes:
    """Encode one model-bound value without lossy normalization."""

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


__all__ = ["encode_greenfield_model_value"]
