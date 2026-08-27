"""Project concise governance narratives from accepted Semantic Intent facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_MAX_NARRATIVE_FACTS = 8
_MAX_NARRATIVE_CANDIDATES = 8
_MAX_SUMMARY_ROWS = 3


def project_semantic_narratives(
    facts: Mapping[str, Sequence[Mapping[str, Any]]],
    relations: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Return source-custodied narrative views without prose interpretation."""

    audiences = _rows(facts, "audiences")
    actors = _rows(facts, "actors")
    steps = _rows(facts, "workflow_steps")
    states = _rows(facts, "state_objects")
    outputs = _rows(facts, "visible_outputs")
    dependencies = _rows(facts, "external_systems")
    product_boundaries = _rows(facts, "product_boundaries")
    policy_boundaries = _rows(facts, "policy_boundaries")
    index = {
        str(row["fact_id"]): row
        for rows in facts.values()
        for row in rows
    }
    producer_steps = _relation_subjects(relations, "produces", index=index)
    change_steps = _relation_subjects(relations, "changes", index=index)
    workflow_actors = _workflow_actors(
        relations,
        actor_index={str(row["fact_id"]): row for row in actors},
        step_ids={str(row["fact_id"]) for row in steps},
    )

    result = [
        _product_story(workflow_actors, steps, outputs),
        _problem(workflow_actors, steps, policy_boundaries),
        _customer(audiences, actors, steps),
        _opportunity(steps, outputs),
        _product_view(
            outputs,
            states,
            dependencies,
            product_boundaries,
            policy_boundaries,
        ),
        _proof_boundary(outputs, states),
    ]
    metrics = _success_metrics(
        steps,
        states,
        outputs,
        producer_steps=producer_steps,
        change_steps=change_steps,
    )
    evidence = _evidence_requirements(
        states,
        outputs,
        producer_steps=producer_steps,
        change_steps=change_steps,
    )
    return [*result, *metrics, *evidence]


def _product_story(
    workflow_actors: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(
        steps=steps[:_MAX_SUMMARY_ROWS],
        outputs=outputs[:2],
        actors=workflow_actors[:_MAX_NARRATIVE_FACTS],
    )
    text = f"The product workflow steps: {_quoted_actions(scope['steps'])}."
    if scope["actors"]:
        owner = "Owner" if len(scope["actors"]) == 1 else "Owners"
        text += f" {owner}: {_labels(scope['actors'])}."
    if scope["outputs"]:
        text += f" Visible output: {_quoted_labels(scope['outputs'])}."
    return _narrative("product_story", 0, text, scope)


def _problem(
    workflow_actors: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    policy_boundaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(
        steps=steps[:2],
        policy_boundaries=policy_boundaries[:2],
        actors=workflow_actors[:_MAX_NARRATIVE_FACTS],
    )
    text = "The release must preserve the accepted workflow and its ownership."
    if scope["policy_boundaries"]:
        text += f" It must also uphold {_labels(scope['policy_boundaries'])}."
    return _narrative("problem", 0, text, scope)


def _customer(
    audiences: Sequence[Mapping[str, Any]],
    actors: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if actors:
        scope = _scope(actors=actors[:_MAX_NARRATIVE_FACTS])
        participants = _quoted_labels(scope["actors"])
        text = (
            f"The declared participant is {participants}."
            if len(scope["actors"]) == 1
            else f"The declared participants are {participants}."
        )
    elif audiences:
        scope = _scope(audiences=audiences[:_MAX_NARRATIVE_FACTS])
        label = "audience" if len(scope["audiences"]) == 1 else "audiences"
        text = f"The declared {label} is {_quoted_labels(scope['audiences'])}."
    else:
        scope = _scope(steps=steps[:1])
        text = (
            "No human participant is declared; the first path is owned by the "
            "product or its systems."
        )
    return _narrative("customer", 0, text, scope)


def _opportunity(
    steps: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(outputs=outputs[:2], steps=steps[:1])
    if scope["steps"]:
        text = (
            f"The product can make {_quoted_labels(scope['outputs'])} available "
            "through the accepted path."
        )
    else:
        text = (
            "The opportunity is to make "
            f"{_result_subject(scope['outputs'])} visible."
        )
    return _narrative("opportunity", 0, text, scope)


def _product_view(
    outputs: Sequence[Mapping[str, Any]],
    states: Sequence[Mapping[str, Any]],
    dependencies: Sequence[Mapping[str, Any]],
    product_boundaries: Sequence[Mapping[str, Any]],
    policy_boundaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(
        outputs=outputs[:2],
        states=states[:1],
        dependencies=dependencies[:1],
        product_boundaries=product_boundaries[:1],
        policy_boundaries=policy_boundaries[:1],
    )
    text = f"The product includes the accepted workflow and exposes {_quoted_labels(scope['outputs'])}."
    if scope["states"]:
        text += f" Governed state: {_labels(scope['states'])}."
    if scope["dependencies"]:
        text += f" Dependency: {_labels(scope['dependencies'])}."
    if scope["product_boundaries"]:
        text += f" Product boundary: {_labels(scope['product_boundaries'])}."
    if scope["policy_boundaries"]:
        text += f" Policy boundary: {_labels(scope['policy_boundaries'])}."
    return _narrative("product_view", 0, text, scope)


def _proof_boundary(
    outputs: Sequence[Mapping[str, Any]],
    states: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(
        outputs=outputs[:2],
        states=states[:2],
    )
    clauses = [f"{_quoted_labels(scope['outputs'])} visible"]
    transitions = _transitions(scope["states"])
    if transitions:
        clauses.append(transitions)
    text = f"Release proof: {_join(clauses)}."
    return _narrative("proof_boundary", 0, text, scope)


def _success_metrics(
    steps: Sequence[Mapping[str, Any]],
    states: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
    *,
    producer_steps: Mapping[str, Mapping[str, Any]],
    change_steps: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for output in outputs[:4]:
        step = producer_steps.get(str(output["fact_id"]))
        scope = _scope(output=(output,), step=(step,) if step else ())
        if scope["step"]:
            text = (
                f"When {_step_completion(scope['step'])}, the path makes "
                f"{_result_subject(scope['output'])} visible."
            )
        else:
            text = f"The path makes {_result_subject(scope['output'])} visible."
        result.append(_narrative("success_metric", len(result), text, scope))
    for state in states[:4]:
        transition = state.get("transition")
        if not isinstance(transition, Mapping):
            continue
        step = change_steps.get(str(state["fact_id"]))
        scope = _scope(state=(state,), step=(step,) if step else ())
        if scope["step"]:
            text = f"When {_step_completion(scope['step'])}, {_state_transition(state, finite=True)}."
        else:
            transition = _state_transition(state, finite=True)
            text = f"{transition[:1].upper()}{transition[1:]}."
        result.append(_narrative("success_metric", len(result), text, scope))
    for step in steps:
        if len(result) >= 2:
            break
        scope = _scope(step=(step,))
        result.append(
            _narrative(
                "success_metric",
                len(result),
                f"The first path completes {_quoted_labels(scope['step'])}.",
                scope,
            )
        )
    if len(result) < 2:
        raise ValueError("Semantic narrative projection lacks two observable checks")
    return result


def _evidence_requirements(
    states: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
    *,
    producer_steps: Mapping[str, Mapping[str, Any]],
    change_steps: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for output in outputs[:4]:
        step = producer_steps.get(str(output["fact_id"]))
        scope = _scope(output=(output,), step=(step,) if step else ())
        if scope["step"]:
            text = (
                f"Evidence must show that {_step_subject(scope['step'])} produced "
                f"{_result_subject(scope['output'])}."
            )
        else:
            text = f"Evidence must show {_result_subject(scope['output'])}."
        result.append(
            _narrative("evidence_requirement", len(result), text, scope)
        )
    for state in states[:4]:
        transition = state.get("transition")
        if not isinstance(transition, Mapping):
            continue
        step = change_steps.get(str(state["fact_id"]))
        scope = _scope(state=(state,), step=(step,) if step else ())
        text = f"Evidence must show {_state_transition(state, finite=False)}"
        result.append(
            _narrative("evidence_requirement", len(result), text + ".", scope)
        )
    return result


def _scope(**groups: Sequence[Mapping[str, Any] | None]) -> dict[str, list[Mapping[str, Any]]]:
    accepted: dict[str, list[Mapping[str, Any]]] = {name: [] for name in groups}
    candidate_ids: set[str] = set()
    fact_ids: set[str] = set()
    for name, rows in groups.items():
        for raw in rows:
            if raw is None:
                continue
            row = raw
            row_candidates = {str(value) for value in row.get("candidate_ids", ())}
            fact_id = str(row.get("fact_id") or "")
            if (
                not fact_id
                or fact_id in fact_ids
                or len(fact_ids) >= _MAX_NARRATIVE_FACTS
                or len(candidate_ids | row_candidates) > _MAX_NARRATIVE_CANDIDATES
            ):
                continue
            accepted[name].append(row)
            fact_ids.add(fact_id)
            candidate_ids.update(row_candidates)
    return accepted


def _narrative(
    field: str,
    order: int,
    text: str,
    scope: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    rows = [row for values in scope.values() for row in values]
    fact_ids = list(dict.fromkeys(str(row["fact_id"]) for row in rows))
    candidate_ids = list(
        dict.fromkeys(
            str(candidate_id)
            for row in rows
            for candidate_id in row.get("candidate_ids", ())
        )
    )
    if not fact_ids or not candidate_ids:
        raise ValueError("Semantic narrative projection lacks source custody")
    return {
        "field": field,
        "order": order,
        "text": text,
        "fact_ids": fact_ids,
        "candidate_ids": candidate_ids,
    }


def _relation_subjects(
    relations: Mapping[str, Sequence[Mapping[str, Any]]],
    kind: str,
    *,
    index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for relation in relations.get(kind, ()):
        subject = index.get(str(relation.get("subject_id") or ""))
        object_id = str(relation.get("object_id") or "")
        if subject is not None and object_id and object_id not in result:
            result[object_id] = subject
    return result


def _workflow_actors(
    relations: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    actor_index: Mapping[str, Mapping[str, Any]],
    step_ids: set[str],
) -> list[Mapping[str, Any]]:
    """Return unique human owners in the accepted workflow relation order."""

    result: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for relation in relations.get("owned_by", ()):
        actor_id = str(relation.get("object_id") or "")
        step_id = str(relation.get("subject_id") or "")
        actor = actor_index.get(actor_id)
        if (
            actor_id
            and actor_id not in seen
            and step_id in step_ids
            and actor is not None
        ):
            result.append(actor)
            seen.add(actor_id)
    return result


def _rows(
    facts: Mapping[str, Sequence[Mapping[str, Any]]], name: str
) -> list[Mapping[str, Any]]:
    return list(facts.get(name, ()))


def _labels(rows: Sequence[Mapping[str, Any]], *, fallback: str = "") -> str:
    labels = [_fragment(str(row.get("label") or "")) for row in rows]
    return _join([label for label in labels if label]) or fallback


def _quoted_actions(rows: Sequence[Mapping[str, Any]]) -> str:
    actions = []
    for row in rows:
        attributes = row.get("attributes", ())
        action_phrase = next(
            (
                str(attribute.get("value") or "")
                for attribute in attributes
                if isinstance(attribute, Mapping)
                and attribute.get("name") == "action_phrase"
            ),
            str(row.get("label") or ""),
        )
        action = _fragment(action_phrase)
        if action:
            actions.append(f"“{action}”")
    return _join(actions)


def _attribute(row: Mapping[str, Any], name: str) -> str:
    for attribute in row.get("attributes", ()):
        if isinstance(attribute, Mapping) and attribute.get("name") == name:
            return str(attribute.get("value") or "")
    return ""


def _quoted_labels(rows: Sequence[Mapping[str, Any]]) -> str:
    return _join(
        [f"“{label}”" for label in (_fragment(str(row.get("label") or "")) for row in rows) if label]
    )


def _step_subject(rows: Sequence[Mapping[str, Any]]) -> str:
    labels = _quoted_labels(rows)
    return f"the {labels} step" if len(rows) == 1 else f"the {labels} steps"


def _step_completion(rows: Sequence[Mapping[str, Any]]) -> str:
    subject = _step_subject(rows)
    return f"{subject} completes" if len(rows) == 1 else f"{subject} complete"


def _result_subject(rows: Sequence[Mapping[str, Any]]) -> str:
    noun = "result" if len(rows) == 1 else "results"
    return f"the {_quoted_labels(rows)} {noun}"


def _state_subject(rows: Sequence[Mapping[str, Any]]) -> str:
    noun = "state" if len(rows) == 1 else "states"
    return f"the {_quoted_labels(rows)} {noun}"


def _transitions(rows: Sequence[Mapping[str, Any]]) -> str:
    values = []
    for row in rows:
        transition = row.get("transition")
        if isinstance(transition, Mapping):
            values.append(_state_transition(row, finite=False))
    return _join(values)


def _state_transition(row: Mapping[str, Any], *, finite: bool) -> str:
    """Render one typed transition without reparsing its label or endpoints."""

    subject = _fragment(str(row.get("label") or "state"))
    transition = row.get("transition")
    if not isinstance(transition, Mapping):
        return subject
    before = transition.get("from_state")
    after = transition.get("to_state")
    if before is None:
        verb = "becomes" if finite else "becoming"
        return f"{subject} {verb} {_fragment(str(after))}"
    if after is None:
        verb = "leaves" if finite else "leaving"
        return f"{subject} {verb} {_fragment(str(before))}"
    verb = "changes" if finite else "changing"
    return (
        f"{subject} {verb} from {_fragment(str(before))} "
        f"to {_fragment(str(after))}"
    )


def _join(values: Sequence[str]) -> str:
    items = [value for value in values if value]
    if len(items) < 2:
        return items[0] if items else ""
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _fragment(value: str) -> str:
    result = " ".join(value.strip().split())
    while result.endswith((".", "!", "?")):
        result = result[:-1].rstrip()
    return result


__all__ = ["project_semantic_narratives"]
