"""Modal and infinitive grammar repair for confirmed greenfield artifacts."""

from __future__ import annotations

from typing import Any

from odylith.runtime.common.prose_grammar import repair_infinitive_base_form_drift
from odylith.runtime.common.prose_grammar import repair_modal_base_form_drift


_MODAL_GRAMMAR_SKIP_KEYS = frozenset(
    {
        "actor_id",
        "component_id",
        "diagram_id",
        "id",
        "kind",
        "link_state",
        "owner",
        "path",
        "prompt",
        "prompt_source",
        "raw_prompt",
        "release_id",
        "slug",
        "source",
        "source_path",
        "source_text",
        "target_workstream_titles",
        "title",
        "watch_paths",
        "workstream_id",
        "workstream_ids",
        "workstream_titles",
    }
)


def repair_generated_modal_grammar(value: Any, *, parent_key: str = "") -> bool:
    """Repair modal and infinitive verb-form drift in generated prose leaves."""

    if isinstance(value, dict):
        changed = False
        for key, child in list(value.items()):
            key_text = str(key)
            if _skip_modal_grammar_repair_key(key_text):
                continue
            if isinstance(child, str):
                repaired = _repair_modal_grammar_text(child)
                if repaired != child:
                    value[key] = repaired
                    changed = True
                continue
            if repair_generated_modal_grammar(child, parent_key=key_text):
                changed = True
        return changed
    if isinstance(value, list):
        changed = False
        for index, child in enumerate(list(value)):
            if isinstance(child, str):
                repaired = _repair_modal_grammar_text(child)
                if repaired != child:
                    value[index] = repaired
                    changed = True
                continue
            if repair_generated_modal_grammar(child, parent_key=parent_key):
                changed = True
        return changed
    if isinstance(value, str):
        return False
    return False


def _skip_modal_grammar_repair_key(key: str) -> bool:
    text = key.casefold().strip()
    if text in _MODAL_GRAMMAR_SKIP_KEYS:
        return True
    return text.endswith(("_id", "_ids", "_slug", "_path", "_paths"))


def _repair_modal_grammar_text(value: str) -> str:
    repaired = repair_modal_base_form_drift(value)
    repaired = repair_infinitive_base_form_drift(repaired)
    return repaired


__all__ = ["repair_generated_modal_grammar"]
