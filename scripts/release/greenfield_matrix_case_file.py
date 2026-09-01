"""External case-file support for greenfield release simulations."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from greenfield_matrix_leakage import term_present
from greenfield_matrix_corpus_provenance import case_provenance_from_mapping
from greenfield_matrix_input_axes import normalize_axis_token
from greenfield_matrix_input_axes import normalize_input_style
from greenfield_preconfirm_matrix_cases import DEFAULT_CASE_EXPECTATION
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import VALID_CASE_EXPECTATIONS
from odylith.runtime.domain_intelligence.greenfield_text import dedupe_adjacent_words


def load_case_file(
    path: Path,
    *,
    enforce_lexical_controls: bool = True,
) -> tuple[GreenfieldMatrixCase, ...]:
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
    expected_clarifications = _expected_clarifications_by_case(raw)
    compiled = tuple(
        _case_from_row(
            row,
            index=index,
            source=case_path,
            expected_clarification=expected_clarifications.get(
                _optional_text(row.get("case_id")) or _optional_text(row.get("id"))
            ),
            enforce_lexical_controls=enforce_lexical_controls,
        )
        for index, row in enumerate(cases, 1)
    )
    identity_counts = Counter(_case_identity(case) for case in compiled)
    duplicates = sorted(identity for identity, count in identity_counts.items() if count > 1)
    if duplicates:
        raise RuntimeError(
            f"greenfield case file {case_path} has duplicate case IDs: {', '.join(duplicates)}"
        )
    return compiled


def _case_identity(case: GreenfieldMatrixCase) -> str:
    return str(case.case_id or case.name or "").strip()


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


def _case_from_row(
    row: Mapping[str, Any],
    *,
    index: int,
    source: Path,
    expected_clarification: tuple[str, str] | None = None,
    enforce_lexical_controls: bool = True,
) -> GreenfieldMatrixCase:
    name = _required_text(row, "name", index=index, source=source)
    prompt = _canonical_block_text(_required_block_text(row, "prompt", index=index, source=source))
    required_terms = _string_tuple(row.get("required_terms"))
    leakage_terms = _string_tuple(row.get("leakage_terms"))
    confirmed_intent = _canonical_block_text(_optional_block_text(row.get("confirmed_intent_markdown")))
    try:
        provenance = case_provenance_from_mapping(row.get("provenance"))
    except ValueError as exc:
        raise RuntimeError(f"{source} case {index} ({name}) has invalid provenance: {exc}") from exc
    if enforce_lexical_controls:
        if not required_terms:
            raise RuntimeError(f"{source} case {index} ({name}) must define required_terms")
        if not leakage_terms:
            raise RuntimeError(f"{source} case {index} ({name}) must define leakage_terms")
        missing_terms = ungrounded_required_terms(
            prompt=prompt,
            confirmed_intent_markdown=confirmed_intent,
            required_terms=required_terms,
        )
        if missing_terms:
            raise RuntimeError(
                f"{source} case {index} ({name}) has ungrounded required_terms: {', '.join(missing_terms)}; "
                "required_terms must be source-grounded in the case prompt or confirmed intent"
            )
        missing_leakage_terms = ungrounded_leakage_terms(
            prompt=prompt,
            confirmed_intent_markdown=confirmed_intent,
            leakage_terms=leakage_terms,
        )
        if missing_leakage_terms:
            raise RuntimeError(
                f"{source} case {index} ({name}) has ungrounded leakage_terms: {', '.join(missing_leakage_terms)}; "
                "leakage_terms must be source-grounded in the case prompt or confirmed intent"
            )
    else:
        required_terms = ()
        leakage_terms = ()
    try:
        input_style_token = normalize_axis_token(row.get("input_style"))
        input_style = normalize_input_style(input_style_token)
        metamorphic_group = normalize_axis_token(row.get("metamorphic_group"))
        metamorphic_transform = normalize_axis_token(row.get("metamorphic_transform"))
    except ValueError as exc:
        raise RuntimeError(f"{source} case {index} ({name}) has invalid matrix axis metadata: {exc}") from exc
    if bool(metamorphic_group) != bool(metamorphic_transform):
        raise RuntimeError(
            f"{source} case {index} ({name}) must define both metamorphic_group and metamorphic_transform"
        )
    return GreenfieldMatrixCase(
        name=name,
        prompt=prompt,
        required_terms=required_terms,
        leakage_terms=leakage_terms,
        confirmed_intent_markdown=confirmed_intent,
        case_id=_optional_text(row.get("case_id")) or _optional_text(row.get("id")),
        tags=_string_tuple(row.get("tags")),
        stressors=_string_tuple(row.get("stressors")),
        source_file=str(source),
        provenance=provenance,
        expectation=_case_expectation(row.get("expectation"), index=index, name=name, source=source),
        input_style=input_style,
        input_style_declared=bool(input_style_token),
        metamorphic_group=metamorphic_group,
        metamorphic_transform=metamorphic_transform,
        expected_clarification_field=(expected_clarification or ("", ""))[0],
        expected_clarification_question=(expected_clarification or ("", ""))[1],
    )


def _expected_clarifications_by_case(raw: Any) -> dict[str, tuple[str, str]]:
    if not isinstance(raw, Mapping):
        return {}
    annotations = raw.get("annotations")
    if not isinstance(annotations, Sequence) or isinstance(annotations, (str, bytes, bytearray)):
        return {}
    clarifications: dict[str, tuple[str, str]] = {}
    for row in annotations:
        if not isinstance(row, Mapping):
            continue
        case_id = _optional_text(row.get("case_id"))
        expected = row.get("expected_clarification")
        if not case_id or expected is None:
            continue
        if not isinstance(expected, Mapping):
            raise RuntimeError(f"annotation `{case_id}` has invalid expected_clarification")
        field = _optional_text(expected.get("field"))
        question = _optional_block_text(expected.get("question"))
        if not field or not question:
            raise RuntimeError(f"annotation `{case_id}` has incomplete expected_clarification")
        clarifications[case_id] = (field, question)
    return clarifications


def ungrounded_required_terms(
    *,
    prompt: str,
    confirmed_intent_markdown: str,
    required_terms: Sequence[str],
) -> tuple[str, ...]:
    source_text = "\n".join(str(item or "") for item in (prompt, confirmed_intent_markdown))
    return tuple(
        term
        for term in required_terms
        if str(term).strip() and not term_present(source_text, str(term))
    )


def ungrounded_leakage_terms(
    *,
    prompt: str,
    confirmed_intent_markdown: str,
    leakage_terms: Sequence[str],
) -> tuple[str, ...]:
    source_text = "\n".join(str(item or "") for item in (prompt, confirmed_intent_markdown))
    return tuple(
        term
        for term in leakage_terms
        if str(term).strip() and not term_present(source_text, str(term))
    )


def _required_text(row: Mapping[str, Any], field: str, *, index: int, source: Path) -> str:
    value = _optional_text(row.get(field))
    if not value:
        raise RuntimeError(f"{source} case {index} must define {field}")
    return value


def _required_block_text(row: Mapping[str, Any], field: str, *, index: int, source: Path) -> str:
    value = _optional_block_text(row.get(field))
    if not value:
        raise RuntimeError(f"{source} case {index} must define {field}")
    return value


def _optional_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _optional_block_text(value: Any) -> str:
    return str(value or "").strip()


def _case_expectation(value: Any, *, index: int, name: str, source: Path) -> str:
    expectation = _optional_text(value).casefold() or DEFAULT_CASE_EXPECTATION
    if expectation not in VALID_CASE_EXPECTATIONS:
        supported = ", ".join(sorted(VALID_CASE_EXPECTATIONS))
        raise RuntimeError(
            f"{source} case {index} ({name}) has unsupported expectation `{expectation}`; expected one of: {supported}"
        )
    return expectation


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(dict.fromkeys(text for item in value if (text := _canonical_text(_optional_text(item)))))


def _canonical_text(value: Any) -> str:
    return dedupe_adjacent_words(_optional_text(value)).strip()


def canonical_case_text(value: Any) -> str:
    """Return the exact prompt normalization applied when a case file is loaded."""

    return _canonical_block_text(value)


def _canonical_block_text(value: Any) -> str:
    text = _optional_block_text(value)
    if not text:
        return ""
    return "\n".join(dedupe_adjacent_words(line).strip() for line in text.splitlines()).strip()


__all__ = [
    "canonical_case_text",
    "load_case_file",
    "normalize_input_style",
    "ungrounded_leakage_terms",
    "ungrounded_required_terms",
]
