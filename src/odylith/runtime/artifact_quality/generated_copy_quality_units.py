"""Typed text-unit collection for generated-copy quality checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import shlex
from typing import Any

from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import ArtifactQualityUnit
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import artifact_quality_units
from odylith.runtime.common.mermaid_text import visible_mermaid_label_quality_texts
from odylith.runtime.domain_intelligence.greenfield_structural_copy import structural_copy_value
from odylith.runtime.domain_intelligence.greenfield_text import SENTENCE_TRAILING_CLOSERS
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


_SENTENCE_TERMINATORS = frozenset(".!?\n\r")


def text_quality_units(value: Any) -> tuple[ArtifactQualityUnit, ...]:
    """Return typed text chunks that should be inspected for prose quality."""

    units: list[ArtifactQualityUnit] = []
    _append_text_quality_units(units, value)
    return _unique_units(units)


def raw_text_units(value: Any) -> tuple[ArtifactQualityUnit, ...]:
    """Return typed scalar leaves for raw punctuation checks."""

    units: list[ArtifactQualityUnit] = []
    _append_raw_text_values(units, value)
    return _unique_units(units)


def _append_raw_text_values(units: list[ArtifactQualityUnit], value: Any) -> None:
    _append_raw_text_values_for_key(units, value, key="")


def _append_raw_text_values_for_key(units: list[ArtifactQualityUnit], value: Any, *, key: str) -> None:
    if value is None:
        return
    if isinstance(value, ArtifactQualityUnit):
        if text := clean_text(value.text):
            units.append(_copy_unit(value, text=text))
        return
    if isinstance(value, RenderedArtifact):
        units.extend(artifact_quality_units(value))
        return
    if isinstance(value, Mapping):
        for nested_key, nested in value.items():
            _append_raw_text_values_for_key(units, nested, key=str(nested_key))
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _append_raw_text_values_for_key(units, nested, key=key)
        return
    if not isinstance(value, (str, int, float, bool)):
        return
    text = clean_text(value)
    if text and not structural_copy_value(key=key, value=text):
        units.append(_scalar_unit(text=text, key=key))


def _append_text_quality_units(units: list[ArtifactQualityUnit], value: Any) -> None:
    _append_text_quality_units_for_key(units, value, key="")


def _append_text_quality_units_for_key(units: list[ArtifactQualityUnit], value: Any, *, key: str) -> None:
    if value is None:
        return
    if isinstance(value, ArtifactQualityUnit):
        _append_unit_text_quality_units(units, value)
        return
    if isinstance(value, RenderedArtifact):
        for unit in artifact_quality_units(value):
            _append_unit_text_quality_units(units, unit)
        return
    if isinstance(value, Mapping):
        for nested_key, nested in value.items():
            _append_text_quality_units_for_key(units, nested, key=str(nested_key))
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _append_text_quality_units_for_key(units, nested, key=key)
        return
    if not isinstance(value, (str, int, float, bool)):
        return
    if structural_copy_value(key=key, value=clean_text(value)):
        return
    mermaid_units = visible_mermaid_label_quality_texts(value)
    if mermaid_units:
        for index, unit in enumerate(mermaid_units):
            _append_unit_text_quality_units(
                units,
                _scalar_unit(text=unit, key=key, text_kind="mermaid_label", surface_role=f"label[{index}]"),
            )
        return
    if _looks_like_shell_command(str(value or "")):
        units.append(_scalar_unit(text=clean_text(value), key=key, text_kind="command"))
        return
    _append_sentence_quality_units(units, str(value or ""), key=key)


def _append_unit_text_quality_units(units: list[ArtifactQualityUnit], unit: ArtifactQualityUnit) -> None:
    text = clean_text(unit.text)
    if not text:
        return
    if unit.text_kind == "mermaid_source":
        for index, label in enumerate(visible_mermaid_label_quality_texts(unit.text)):
            if not label:
                continue
            units.append(
                ArtifactQualityUnit(
                    projection_id=unit.projection_id,
                    surface=unit.surface,
                    source_path=f"{unit.source_path}.label[{index}]",
                    surface_role=f"{unit.surface_role}.label[{index}]",
                    text_kind="mermaid_label",
                    text=label,
                    semantic_node_id=unit.semantic_node_id,
                )
            )
        return
    if unit.text_kind in {"command", "metadata", "mermaid_label"}:
        units.append(_copy_unit(unit, text=text))
        return
    _append_sentence_quality_units(units, text, key=unit.surface_role, template=unit)


def _append_sentence_quality_units(
    units: list[ArtifactQualityUnit],
    value: str,
    *,
    key: str,
    template: ArtifactQualityUnit | None = None,
) -> None:
    current: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char not in _SENTENCE_TERMINATORS:
            current.append(char)
            index += 1
            continue
        index += 1
        if char not in "\n\r":
            while index < len(value) and value[index] in SENTENCE_TRAILING_CLOSERS:
                current.append(value[index])
                index += 1
        _append_quality_chunk(units, current, key=key, template=template)
        current = []
    _append_quality_chunk(units, current, key=key, template=template)


def _append_quality_chunk(
    units: list[ArtifactQualityUnit],
    chars: list[str],
    *,
    key: str,
    template: ArtifactQualityUnit | None = None,
) -> None:
    text = clean_text("".join(chars)).strip(" -#*_`|")
    if text:
        units.append(_copy_unit(template, text=text) if template else _scalar_unit(text=text, key=key))


def _scalar_unit(
    *,
    text: str,
    key: str,
    text_kind: str = "free_prose",
    surface_role: str = "body",
) -> ArtifactQualityUnit:
    return ArtifactQualityUnit(
        projection_id="ad_hoc_generated_copy",
        surface="generated public copy",
        source_path=key or "value",
        surface_role=surface_role if surface_role != "body" else (key or "body"),
        text_kind=text_kind,
        text=text,
    )


def _copy_unit(unit: ArtifactQualityUnit | None, *, text: str) -> ArtifactQualityUnit:
    if unit is None:
        return _scalar_unit(text=text, key="")
    return ArtifactQualityUnit(
        projection_id=unit.projection_id,
        surface=unit.surface,
        source_path=unit.source_path,
        surface_role=unit.surface_role,
        text_kind=unit.text_kind,
        text=text,
        semantic_node_id=unit.semantic_node_id,
    )


def _unique_units(units: Sequence[ArtifactQualityUnit]) -> tuple[ArtifactQualityUnit, ...]:
    seen: set[tuple[str, str, str, str, str]] = set()
    result: list[ArtifactQualityUnit] = []
    for unit in units:
        key = (
            unit.projection_id,
            unit.source_path,
            unit.surface_role,
            unit.text_kind,
            unit.text.casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(unit)
    return tuple(result)


def _looks_like_shell_command(value: str) -> bool:
    text = clean_text(value)
    if not text:
        return False
    try:
        tokens = shlex.split(text)
    except ValueError:
        return False
    if len(tokens) < 2:
        return False
    executable = tokens[0]
    if executable in {"odylith", "bash", "curl", "git", "node", "npm", "pnpm", "python", "python3", "pytest", "yarn"}:
        return True
    return executable.startswith(("./", "../", "/", ".venv/")) or any(token.startswith("--") for token in tokens[1:])


__all__ = [
    "raw_text_units",
    "text_quality_units",
]
