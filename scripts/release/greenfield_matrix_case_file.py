"""External case-file support for greenfield release simulations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from greenfield_post_confirm_matrix_cases import GreenfieldMatrixCase


def load_case_file(path: Path) -> tuple[GreenfieldMatrixCase, ...]:
    """Load matrix cases from a JSON file without baking domains into Odylith."""

    case_path = Path(path).expanduser().resolve()
    try:
        raw = json.loads(case_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"unable to read greenfield case file {case_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"greenfield case file {case_path} is not valid JSON: {exc}") from exc
    cases = _case_rows(raw)
    if not cases:
        raise RuntimeError(f"greenfield case file {case_path} must define at least one case")
    return tuple(_case_from_row(row, index=index, source=case_path) for index, row in enumerate(cases, 1))


def _case_rows(raw: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(raw, Mapping):
        raw_cases = raw.get("cases")
    else:
        raw_cases = raw
    if not isinstance(raw_cases, Sequence) or isinstance(raw_cases, (str, bytes, bytearray)):
        raise RuntimeError("greenfield case file must be a JSON array or an object with a cases array")
    rows: list[Mapping[str, Any]] = []
    for row in raw_cases:
        if not isinstance(row, Mapping):
            raise RuntimeError("greenfield case file cases must be JSON objects")
        rows.append(row)
    return tuple(rows)


def _case_from_row(row: Mapping[str, Any], *, index: int, source: Path) -> GreenfieldMatrixCase:
    name = _required_text(row, "name", index=index, source=source)
    prompt = _required_text(row, "prompt", index=index, source=source)
    required_terms = _string_tuple(row.get("required_terms"))
    leakage_terms = _string_tuple(row.get("leakage_terms"))
    if not required_terms:
        raise RuntimeError(f"{source} case {index} ({name}) must define required_terms")
    if not leakage_terms:
        raise RuntimeError(f"{source} case {index} ({name}) must define leakage_terms")
    return GreenfieldMatrixCase(
        name=name,
        prompt=prompt,
        required_terms=required_terms,
        leakage_terms=leakage_terms,
        confirmed_intent_markdown=_optional_block_text(row.get("confirmed_intent_markdown")),
    )


def _required_text(row: Mapping[str, Any], field: str, *, index: int, source: Path) -> str:
    value = _optional_text(row.get(field))
    if not value:
        raise RuntimeError(f"{source} case {index} must define {field}")
    return value


def _optional_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _optional_block_text(value: Any) -> str:
    return str(value or "").strip()


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(dict.fromkeys(text for item in value if (text := _optional_text(item))))


__all__ = ["load_case_file"]
