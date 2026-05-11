"""Greenfield Product Story projection for the Project tab."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.project_intelligence.utils import dict_value, list_value, sentence, short, strings


def build_product_story(
    *,
    title: str,
    intro: str,
    project: Mapping[str, Any],
    first_path: str,
    release: str,
    release_plan: Mapping[str, Any],
    accepted: Mapping[str, Any],
    backlog: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    actors: Sequence[tuple[str, str, str]],
) -> dict[str, Any]:
    """Build a source-derived story where topology is the organizing spine."""

    outcome = project_intent_line(project, "user or stakeholder outcome")
    success = project_intent_line(project, "success condition")
    first_release = sentence(release_plan.get("strategy"))
    release_text = sentence(first_release or success, f"Release {release} proves the first path before broader buildout.")
    created = dict_value(accepted.get("created"))
    workstream_items = _workstream_story_items(created=created, backlog=backlog)
    component_items = _component_story_items(created=created, components=components)
    diagram_items = _diagram_story_items(created=created, diagrams=diagrams)
    headline = _story_headline(intro=intro, title=title)
    standfirst = _story_sentence(
        " ".join(row for row in (outcome, success or first_release) if row)
        or "This proposal is the first coherent project story; implementation waits until the first path and proof boundary are accepted."
    )
    narrative = [
        {"label": "Product promise", "title": "What the project is trying to make true", "body": _story_sentence(intro)},
        {"label": "Human outcome", "title": "Who must feel the difference", "body": _story_sentence(outcome or _actor_story(actors))},
        {"label": "First proof", "title": "The smallest journey worth proving", "body": _story_sentence(first_path)},
        {"label": "Scale restraint", "title": f"Why {release} should not sprawl", "body": _story_sentence(release_text)},
    ]
    return {
        "headline": headline,
        "standfirst": standfirst,
        "narrative": [row for row in narrative if sentence(row.get("body"))],
        "actors": _story_actor_items(actors),
        "topology_title": "Topology spine",
        "topology_note": (
            "The story is the root. Radar, Registry, Atlas, and release proof each derive one obligation from it "
            "so the first build starts from one shared product truth."
        ),
        "topology_spine": _topology_spine(
            headline=headline,
            first_path=first_path,
            release=release,
            release_text=release_text,
            workstreams=workstream_items,
            components=component_items,
            diagrams=diagram_items,
        ),
        "artifact_intro": _artifact_story_sentence(
            workstreams=[item["title"] for item in workstream_items],
            components=[item["title"] for item in component_items],
            diagrams=[item["title"] for item in diagram_items],
            release=release,
        ),
        "artifacts": [
            {
                "label": "Workstreams",
                "title": "How the work moves",
                "body": "Radar turns the story into an ordered build program: direction first, then the smallest proof path, then the supporting contracts and harnesses.",
                "items": workstream_items,
            },
            {
                "label": "Registry components",
                "title": "What owns the system",
                "body": "Registry splits the story into owned product boundaries so future implementation can change one responsibility without blurring the rest.",
                "items": component_items,
            },
            {
                "label": "Atlas views",
                "title": "What reviewers can see",
                "body": "Atlas turns the story into reviewable topology: overview, first path, ownership, state model, and release proof.",
                "items": diagram_items,
            },
        ],
        "groups": [
            {"label": "Workstreams", "items": [item["title"] for item in workstream_items]},
            {"label": "Registry components", "items": [item["title"] for item in component_items]},
            {"label": "Atlas views", "items": [item["title"] for item in diagram_items]},
        ],
    }


def project_intent_line(project: Mapping[str, Any], prefix: str) -> str:
    """Read one named intent line from a canonical greenfield proposal."""

    needle = prefix.strip().lower()
    for raw in strings(project.get("intent")):
        head, sep, body = raw.partition(":")
        if sep and head.strip().lower() == needle:
            return sentence(body)
    return ""


def _story_headline(*, intro: str, title: str) -> str:
    text = sentence(intro)
    if not text:
        return title
    for marker in (" that ", " around ", " to ", " by "):
        head, sep, _ = text.partition(marker)
        if sep and 8 <= len(head) <= 92:
            return f"{head}, reduced to one provable journey"
    return short(text, limit=118, fallback=title)


def _story_sentence(value: str) -> str:
    text = sentence(value).replace("`", "")
    if text:
        text = text[0].upper() + text[1:]
    return text if text.endswith((".", "?", "!")) else f"{text}." if text else ""


def _story_actor_items(actors: Sequence[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [
        {"role": sentence(role), "title": sentence(title), "body": sentence(body)}
        for role, title, body in actors[:4]
        if sentence(title)
    ]


def _actor_story(actors: Sequence[tuple[str, str, str]]) -> str:
    names = [sentence(title) for _, title, _ in actors[:4] if sentence(title)]
    if not names:
        return ""
    if len(names) == 1:
        return f"{names[0]} is the first accountable actor."
    return f"{', '.join(names[:-1])}, and {names[-1]} keep the first path accountable."


def _workstream_story_items(*, created: Mapping[str, Any], backlog: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    created_rows = [dict(row) for row in list_value(created.get("workstreams")) if isinstance(row, Mapping)]
    rows = backlog[:5] or created_rows[:5]
    items: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        created_row = created_rows[index] if index < len(created_rows) else {}
        ref = sentence(created_row.get("idea_id"))
        title = _workstream_story_title(row.get("title") or created_row.get("title"))
        body = sentence(row.get("recommended_first_slice") or row.get("product_view") or row.get("problem"))
        items.append({"ref": ref, "title": " ".join(part for part in (ref, title) if part), "body": short(body, limit=170)})
    return items


def _workstream_story_title(value: object) -> str:
    title = sentence(value, "Proposed workstream")
    if title.lower().startswith("govern "):
        return "Govern project direction"
    return title


def _component_story_items(*, created: Mapping[str, Any], components: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    created_rows = [dict(row) for row in list_value(created.get("components")) if isinstance(row, Mapping)]
    rows = components[:5] or created_rows[:5]
    items: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        created_row = created_rows[index] if index < len(created_rows) else {}
        title = sentence(row.get("label") or created_row.get("label") or row.get("component_id"), "Planned component")
        body = sentence(row.get("responsibility") or row.get("boundary") or created_row.get("path"))
        items.append({"ref": sentence(created_row.get("component_id")), "title": title, "body": short(body, limit=170)})
    return items


def _diagram_story_items(*, created: Mapping[str, Any], diagrams: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    ids = [sentence(row) for row in list_value(created.get("diagrams"))]
    rows = diagrams[:5]
    items: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        ref = ids[index] if index < len(ids) else ""
        label = sentence(row.get("title") or row.get("slug"), "Architecture view")
        body = sentence(row.get("operator_question") or row.get("proof_gate") or row.get("link_state"))
        items.append({"ref": ref, "title": " ".join(part for part in (ref, label) if part), "body": short(body, limit=170)})
    if items:
        return items
    return [{"ref": ref, "title": ref, "body": ""} for ref in ids[:5] if ref]


def _topology_spine(
    *,
    headline: str,
    first_path: str,
    release: str,
    release_text: str,
    workstreams: Sequence[Mapping[str, str]],
    components: Sequence[Mapping[str, str]],
    diagrams: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    return [
        {
            "label": "Story root",
            "title": headline,
            "body": "Defines the product promise, beneficiary, first path, and proof boundary.",
        },
        {
            "label": "First path",
            "title": "One journey to prove",
            "body": short(first_path, limit=170),
        },
        {
            "label": "Radar",
            "title": _counted_names(workstreams, "workstream"),
            "body": _first_titles(workstreams, fallback="Orders the work that makes the story buildable."),
        },
        {
            "label": "Registry",
            "title": _counted_names(components, "component"),
            "body": _first_titles(components, fallback="Assigns ownership, boundaries, interfaces, and proof obligations."),
        },
        {
            "label": "Atlas",
            "title": _counted_names(diagrams, "view"),
            "body": _first_titles(diagrams, fallback="Makes the topology reviewable before implementation widens."),
        },
        {
            "label": "Release proof",
            "title": release,
            "body": short(release_text, limit=170),
        },
    ]


def _first_titles(values: Sequence[Mapping[str, str]], *, fallback: str) -> str:
    titles = [sentence(row.get("title")) for row in values[:3] if sentence(row.get("title"))]
    if not titles:
        return fallback
    if len(titles) == 1:
        return titles[0]
    return f"{', '.join(titles[:-1])}, and {titles[-1]}"


def _artifact_story_sentence(
    *,
    workstreams: Sequence[str],
    components: Sequence[str],
    diagrams: Sequence[str],
    release: str,
) -> str:
    workstream_text = _counted_names_from_strings(workstreams, "workstream")
    component_text = _counted_names_from_strings(components, "Registry component")
    diagram_text = _counted_names_from_strings(diagrams, "Atlas view")
    release_text = sentence(release, "first release")
    return (
        f"The topology spine ties {workstream_text}, {component_text}, and {diagram_text} "
        f"to release {release_text}. Workstreams sequence the build, Registry components own the responsibilities, "
        "and Atlas views make the first path reviewable before implementation widens."
    )


def _counted_names(values: Sequence[Mapping[str, str]], singular: str) -> str:
    return _counted_names_from_strings([sentence(row.get("title")) for row in values], singular)


def _counted_names_from_strings(values: Sequence[str], singular: str) -> str:
    rows = [sentence(value) for value in values if sentence(value)]
    if not rows:
        return f"no {singular}s yet"
    noun = singular if len(rows) == 1 else f"{singular}s"
    return f"{len(rows)} {noun}"
