"""Render one typed material question without interpreting source prose."""

from __future__ import annotations

from dataclasses import dataclass


_QUESTION_LABELS = {
    "human_actors": "who will use the product",
    "first_path": "first complete task",
    "visible_result": "result the user should see",
    "product_boundary": "product boundary",
    "external_systems": "required external dependency",
    "proof_boundary": "proof obligation",
    "operational_constraints": "operational or safety boundary",
    "non_goals": "accepted non-goal",
}


@dataclass(frozen=True)
class MaterialClarification:
    """One focused user question and the typed fields its answer must settle."""

    question: str
    required_fields: tuple[str, ...]


def material_clarification_for_fields(fields: tuple[str, ...]) -> MaterialClarification:
    """Render already-classified material fields as one focused question."""

    required_fields = tuple(dict.fromkeys(str(field).strip() for field in fields if str(field).strip()))
    if not required_fields:
        raise ValueError("material clarification requires at least one typed field")
    return MaterialClarification(
        question=_material_unknown_question(required_fields),
        required_fields=required_fields,
    )


def _material_unknown_question(labels: tuple[str, ...]) -> str:
    if labels == ("component_ownership",):
        return "Which product-owned system should own the stated responsibility?"
    if labels == ("first_path",):
        return "Who uses this product first, what complete task do they finish, and what result do they see?"
    readable = tuple(_QUESTION_LABELS.get(label, label.replace("_", " ")) for label in labels)
    if len(readable) == 1:
        field_text = readable[0]
    elif len(readable) == 2:
        field_text = f"{readable[0]} and {readable[1]}"
    else:
        field_text = f"{', '.join(readable[:-1])}, and {readable[-1]}"
    return f"Could you specify the {field_text} for this project?"


__all__ = ["MaterialClarification", "material_clarification_for_fields"]
