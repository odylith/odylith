"""Traceability planning for confirmed greenfield governance proposals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence.artifact_enrichment import build_artifact_enrichment
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_text import collect_delimited_text_values
from odylith.runtime.domain_intelligence.greenfield_text import delimited_text_values
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.governance import backlog_authoring

_REF_FIELDS = (
    "workstreams",
    "workstream_ids",
    "workstream_titles",
    "related_workstreams",
    "related_workstream_ids",
    "related_workstream_titles",
    "workstream_focus",
    "backlog",
    "backlog_titles",
)
_COMPONENT_FIELDS = (
    "component_focus",
    "component_ids",
    "components",
    "related_components",
    "related_component_ids",
)
_DIAGRAM_FIELDS = (
    "diagram_slugs",
    "related_diagram_slugs",
    "related_diagrams",
    "diagrams",
)
_STOPWORDS = {
    "adapter",
    "and",
    "application",
    "boundary",
    "candidate",
    "component",
    "core",
    "engine",
    "framework",
    "from",
    "govern",
    "greenfield",
    "harness",
    "into",
    "library",
    "memory",
    "module",
    "project",
    "research",
    "runner",
    "service",
    "surface",
    "store",
    "system",
    "the",
    "that",
    "this",
    "view",
    "with",
    "without",
}


@dataclass(frozen=True)
class CreatedWorkstream:
    idea_id: str
    title: str
    path: Path
    row: Mapping[str, Any]


@dataclass(frozen=True)
class DiagramLink:
    row: Mapping[str, Any]
    diagram_id: str
    related_workstream_ids: tuple[str, ...]
    related_backlog_paths: tuple[str, ...]


@dataclass(frozen=True)
class GreenfieldTraceabilityPlan:
    workstreams: tuple[CreatedWorkstream, ...]
    component_workstreams: dict[str, tuple[str, ...]]
    component_diagrams: dict[str, tuple[str, ...]]
    diagram_links: tuple[DiagramLink, ...]
    backlog_diagrams: dict[str, tuple[str, ...]]


def component_key(row: Mapping[str, Any]) -> str:
    """Return the stable proposal-local key for a component row."""

    return slugify(str(row.get("component_id", "")).strip() or str(row.get("label", "")).strip())


def build_traceability_plan(
    *,
    proposal: Mapping[str, Any],
    created_backlog: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
) -> GreenfieldTraceabilityPlan:
    """Map confirmed proposal topology onto newly created governance IDs."""

    workstreams = _created_workstreams(proposal=proposal, created_backlog=created_backlog)
    components = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    diagrams = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    component_workstreams = {
        component_key(row): _component_workstream_ids(row=row, workstreams=workstreams)
        for row in components
    }
    diagram_links = tuple(
        _diagram_link(
            row=row,
            diagram_id=str(diagram_id).strip(),
            workstreams=workstreams,
            components=components,
            component_workstreams=component_workstreams,
        )
        for row, diagram_id in zip(diagrams, diagram_ids, strict=False)
        if str(diagram_id).strip()
    )
    component_diagrams = {
        component_key(row): _component_diagram_ids(row=row, diagram_links=diagram_links)
        for row in components
    }
    backlog_diagrams: dict[str, list[str]] = {}
    for link in diagram_links:
        for idea_id in link.related_workstream_ids:
            backlog_diagrams.setdefault(idea_id, []).append(link.diagram_id)
    return GreenfieldTraceabilityPlan(
        workstreams=workstreams,
        component_workstreams={key: tuple(values) for key, values in component_workstreams.items()},
        component_diagrams={key: tuple(values) for key, values in component_diagrams.items()},
        diagram_links=diagram_links,
        backlog_diagrams={key: tuple(_unique(values)) for key, values in backlog_diagrams.items()},
    )


def apply_backlog_traceability(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    plan: GreenfieldTraceabilityPlan,
) -> list[str]:
    """Write proposal-derived topology and richer detail sections into new backlog specs."""

    touched: list[str] = []
    risks = _risk_lines(proposal.get("risks", []))
    validation_strategy = _section_items(proposal.get("validation_strategy", []))
    open_questions = _question_lines(proposal.get("open_questions", []))
    for workstream in plan.workstreams:
        metadata, sections = backlog_authoring._parse_metadata_and_sections(workstream.path)
        diagrams = plan.backlog_diagrams.get(workstream.idea_id, ())
        if diagrams:
            metadata["related_diagram_ids"] = _join_ids(_merge_ids(metadata.get("related_diagram_ids", ""), diagrams))
        _patch_sections(
            metadata=metadata,
            sections=sections,
            row=workstream.row,
            proposal=proposal,
            component_lines=_component_lines_for_workstream(workstream.idea_id, proposal=proposal, plan=plan),
            risks=risks,
            validation_strategy=validation_strategy,
            open_questions=open_questions,
        )
        workstream.path.write_text(backlog_authoring._render_idea_text(metadata=metadata, sections=sections), encoding="utf-8")
        touched.append(_repo_relative(repo_root=repo_root, path=workstream.path))
    return touched


def _created_workstreams(
    *,
    proposal: Mapping[str, Any],
    created_backlog: Sequence[Mapping[str, Any]],
) -> tuple[CreatedWorkstream, ...]:
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    workstreams: list[CreatedWorkstream] = []
    for index, created in enumerate(created_backlog):
        row = rows[index] if index < len(rows) else {}
        idea_id = str(created.get("idea_id", "")).strip().upper()
        title = str(created.get("title", "")).strip() or str(row.get("title", "")).strip()
        raw_path = str(created.get("idea_path", "")).strip()
        if not idea_id or not raw_path:
            continue
        workstreams.append(
            CreatedWorkstream(
                idea_id=idea_id,
                title=title,
                path=Path(raw_path).expanduser().resolve(),
                row=row,
            )
        )
    return tuple(workstreams)


def _component_workstream_ids(
    *,
    row: Mapping[str, Any],
    workstreams: Sequence[CreatedWorkstream],
) -> tuple[str, ...]:
    explicit = _workstream_refs_to_ids(collect_delimited_text_values(row, _REF_FIELDS), workstreams)
    parent = workstreams[:1]
    if explicit:
        return tuple(_unique([*(item.idea_id for item in parent), *explicit]))
    primary = _semantic_tokens(" ".join([str(row.get("component_id", "")), str(row.get("label", ""))]))
    detail = _semantic_tokens(
        " ".join(
            [
                str(row.get("responsibility", "")),
                str(row.get("boundary", "")),
                str(row.get("intended_path", "")),
            ]
        )
    )
    scored: list[tuple[int, str]] = []
    for workstream in workstreams[1:]:
        tokens = _semantic_tokens(_workstream_haystack(workstream.row, fallback_title=workstream.title))
        primary_overlap = len(primary & tokens)
        detail_overlap = len(detail & tokens)
        score = (3 * primary_overlap) + detail_overlap
        if primary_overlap >= 1 or detail_overlap >= 3:
            scored.append((score, workstream.idea_id))
    return tuple(_unique([*(item.idea_id for item in parent), *(idea_id for _score, idea_id in sorted(scored, reverse=True))]))


def _diagram_link(
    *,
    row: Mapping[str, Any],
    diagram_id: str,
    workstreams: Sequence[CreatedWorkstream],
    components: Sequence[Mapping[str, Any]],
    component_workstreams: Mapping[str, Sequence[str]],
) -> DiagramLink:
    related_ids: list[str] = [workstreams[0].idea_id] if workstreams else []
    explicit = _workstream_refs_to_ids(collect_delimited_text_values(row, _REF_FIELDS), workstreams)
    related_ids.extend(explicit)
    diagram_component_aliases = _diagram_component_aliases(row)
    for component in components:
        key = component_key(component)
        aliases = _component_aliases(component)
        if diagram_component_aliases & aliases:
            related_ids.extend(component_workstreams.get(key, ()))
    diagram_tokens = _semantic_tokens(
        " ".join(
            [
                str(row.get("title", "")),
                str(row.get("summary", "")),
                str(row.get("kind", "")),
                str(row.get("mermaid_source", "") or row.get("source", "")),
            ]
        )
    )
    for workstream in workstreams[1:]:
        tokens = _semantic_tokens(_workstream_haystack(workstream.row, fallback_title=workstream.title))
        if len(diagram_tokens & tokens) >= 2:
            related_ids.append(workstream.idea_id)
    deduped_ids = tuple(_unique(related_ids))
    paths_by_id = {workstream.idea_id: str(workstream.path) for workstream in workstreams}
    return DiagramLink(
        row=row,
        diagram_id=diagram_id,
        related_workstream_ids=deduped_ids,
        related_backlog_paths=tuple(paths_by_id[idea_id] for idea_id in deduped_ids if idea_id in paths_by_id),
    )


def _component_diagram_ids(
    *,
    row: Mapping[str, Any],
    diagram_links: Sequence[DiagramLink],
) -> tuple[str, ...]:
    explicit_slugs = {slugify(item) for item in collect_delimited_text_values(row, _DIAGRAM_FIELDS)}
    aliases = _component_aliases(row)
    primary = _semantic_tokens(" ".join([str(row.get("component_id", "")), str(row.get("label", ""))]))
    matches: list[str] = []
    for link in diagram_links:
        slug = slugify(str(link.row.get("slug", "")))
        if slug and slug in explicit_slugs:
            matches.append(link.diagram_id)
            continue
        if aliases & _diagram_component_aliases(link.row):
            matches.append(link.diagram_id)
            continue
        diagram_tokens = _semantic_tokens(str(link.row.get("mermaid_source", "") or link.row.get("source", "")))
        if primary and primary & diagram_tokens:
            matches.append(link.diagram_id)
    return tuple(_unique(matches))


def _patch_sections(
    *,
    metadata: Mapping[str, str],
    sections: dict[str, str],
    row: Mapping[str, Any],
    proposal: Mapping[str, Any],
    component_lines: Sequence[str],
    risks: Sequence[str],
    validation_strategy: Sequence[str],
    open_questions: Sequence[str],
) -> None:
    first_slice = str(row.get("recommended_first_slice", "")).strip()
    product_view = str(row.get("product_view", "")).strip()
    focus = _workstream_focus(row)
    scope_ref = _section_scope_reference(component_lines, metadata=metadata)
    if product_view or first_slice:
        sections["Proposed Solution"] = _paragraph(
            [
                f"Implementation slice: {first_slice}" if first_slice else "",
                (
                    f"Keep success, blocked-input, replay, and handoff proof tied to {scope_ref} "
                    "before expanding adjacent source ownership."
                )
                if focus
                else "",
            ]
        )
    sections["Scope"] = _bullets(
        [
            first_slice or str(row.get("scope", "")).strip(),
            *_section_items(row.get("scope_items", [])),
        ]
    )
    sections["Non-Goals"] = _bullets(
        _section_items(row.get("non_goals", []))
        or [
            f"Do not claim source-backed implementation ownership for {scope_ref} before code exists.",
            (
                f"Do not treat the {scope_ref} as release-ready until success, blocked-input, replay, "
                "and handoff evidence are written and reviewed."
            ),
        ]
    )
    sections["Risks"] = _bullets(_risk_lines(row.get("risks", [])) or risks[:3])
    sections["Dependencies"] = _bullets(
        _section_items(row.get("dependencies", []))
        or _section_items(row.get("depends_on", []))
        or _topology_dependency_lines(metadata)
    )
    validation_items = (
        _section_items(row.get("validation", []))
        or _section_items(row.get("validation_gate", []))
        or _section_items(row.get("success_metrics", []))
        or validation_strategy[:3]
    )
    sections["Validation"] = _bullets(validation_items)
    sections["Test Strategy"] = _bullets(
        _section_items(row.get("test_strategy", []))
        or [
            f"Turn {scope_ref} success metrics into focused reproducibility, contract, or smoke proof before source implementation starts.",
        ]
    )
    sections["Impacted Components"] = _bullets(
        component_lines
        or [
            "No candidate component was inferred for this workstream; the first technical plan must resolve ownership before implementation.",
        ]
    )
    sections["Interface Changes"] = _bullets(
        _section_items(row.get("interfaces", []))
        or _section_items(row.get("interface_changes", []))
        or [
            "Candidate interfaces are proposal-level only until the first source-backed plan defines runtime contracts.",
        ]
    )
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    sections["Rollout"] = _bullets(
        _section_items(row.get("rollout", []))
        or _milestone_lines(release_plan.get("release_stages") or release_plan.get("milestones"))[:3]
        or [
            "Keep the workstream queued until the first implementation plan binds scope, proof, and release gates.",
        ]
    )
    sections["Why Now"] = _why_now_text(row=row, focus=scope_ref, first_slice=first_slice) or sections.get("Why Now", "")
    row_questions = _question_lines(row.get("open_questions", []))
    if not row_questions and _is_parent_workstream(row):
        row_questions = _scoped_question_lines(open_questions[:3], focus=focus)
    sections["Open Questions"] = (
        _bullets(row_questions) if row_questions else "- No unresolved questions are recorded for this slice."
    )
    sections.update(build_artifact_enrichment(row=row, proposal=proposal).radar_sections)


def _is_parent_workstream(row: Mapping[str, Any]) -> bool:
    text = _clean(row.get("workstream_type") or row.get("type") or row.get("shape")).casefold()
    return text in {"program_parent", "umbrella", "parent", "program"}


def _section_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return _mapping_line(value)
    if isinstance(value, (list, tuple, set)):
        rows: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                rows.extend(_mapping_line(item))
            else:
                rows.extend(text_values(item, split_scalar=True, split_commas=False, strip_bullets=True))
        return _unique(rows)
    return list(text_values(value, split_scalar=True, split_commas=False, strip_bullets=True))


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _section_scope_reference(component_lines: Sequence[str], *, metadata: Mapping[str, str]) -> str:
    impacted = _clean(metadata.get("impacted_parts"))
    if impacted:
        return _clean(impacted.split(",", 1)[0]).strip(" .") or "this workstream"
    for line in component_lines:
        text = _clean(line).strip(" .")
        if not text:
            continue
        match = re.search(r"\(([^()]{3,120})\)", text)
        if match:
            return _clean(match.group(1)).strip(" .") or "this workstream"
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"^\s*[-*]\s*", "", text).strip(" .")
        if text:
            return text
    return "this workstream"


def _workstream_focus(row: Mapping[str, Any]) -> str:
    return _clean(row.get("title")) or _clean(row.get("recommended_first_slice")) or "this workstream"


def _why_now_text(*, row: Mapping[str, Any], focus: str, first_slice: str) -> str:
    focus_text = _clean(focus) or "this workstream"
    if first_slice:
        return (
            f"Do this before implementation expands so this workstream has a tested first slice for {focus_text}, clear ownership, "
            "and a release boundary the team can review."
        )
    opportunity = _clean(row.get("opportunity"))
    if not opportunity:
        return ""
    return f"Do this now because the opportunity is ready to turn into reviewable scope: {opportunity}"


def _scoped_question_lines(values: Sequence[str], *, focus: str) -> list[str]:
    _ = focus
    rows: list[str] = []
    for value in values:
        text = _clean(value)
        if not text:
            continue
        question, impact = _split_question_impact(text)
        if impact:
            rows.append(_question_impact_line(question, impact, prefix=False))
        else:
            rows.append(text)
    return rows


def _split_question_impact(value: str) -> tuple[str, str]:
    marker = " Impact:"
    text = _clean(value)
    if marker not in text:
        return text, ""
    question, impact = text.split(marker, 1)
    return _clean(question), _clean(impact)


def _mapping_line(row: Mapping[str, Any]) -> list[str]:
    for fields in (
        ("statement", "mitigation"),
        ("question", "impact"),
        ("label", "exit_criteria"),
        ("release", "exit_criteria"),
        ("name", "description"),
        ("title", "summary"),
    ):
        primary = _clean(row.get(fields[0]))
        secondary = _clean(row.get(fields[1])) if len(fields) > 1 else ""
        if primary and secondary:
            if fields[0] in {"label", "release", "name", "title"}:
                return [f"{primary}: {secondary}"]
            suffix = fields[1].replace("_", " ").title()
            return [f"{primary} {suffix}: {secondary}"]
        if primary:
            return [primary]
    rendered = "; ".join(text_values(row))
    return [rendered] if rendered else []


def _risk_lines(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        return _risk_lines([value])
    if isinstance(value, (list, tuple, set)):
        lines: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                statement = _clean(item.get("statement")) or _clean(item.get("risk"))
                details = _risk_detail_segments(item)
                if statement and details:
                    lines.append(f"{statement} {' '.join(details)}")
                elif statement:
                    lines.append(statement)
                else:
                    lines.extend(_section_items(item))
            else:
                lines.extend(_section_items(item))
        return _unique(lines)
    return _section_items(value)


def _risk_detail_segments(row: Mapping[str, Any]) -> list[str]:
    segments: list[str] = []
    for key, label in (
        ("risk_class", "Class"),
        ("severity", "Severity"),
        ("probability", "Probability"),
        ("blast_radius", "Blast radius"),
        ("trigger", "Trigger"),
        ("early_warning", "Early warning"),
        ("owner", "Owner"),
        ("evidence", "Evidence"),
        ("mitigation", "Mitigation"),
    ):
        value = _clean(row.get(key))
        if value:
            segments.append(f"{label}: {value}")
    return segments


def _question_lines(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        return _question_lines([value])
    if isinstance(value, (list, tuple, set)):
        lines: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                question = _clean(item.get("question")) or _clean(item.get("prompt"))
                impact = _clean(item.get("impact"))
                lines.append(_question_impact_line(question, impact, prefix=False) if question and impact else question)
            else:
                lines.extend(_section_items(item))
        return _unique([line for line in lines if line])
    return _section_items(value)


def _question_impact_line(question: str, impact: str, *, prefix: bool) -> str:
    question_text = _clean(question).strip()
    impact_text = _clean(impact).strip()
    if question_text and question_text[-1:] not in {".", "?", "!"}:
        question_text = f"{question_text}."
    if impact_text:
        impact_text = impact_text.rstrip(" .")
    head = f"Question: {question_text}" if prefix else question_text
    return f"{head} {impact_text}." if impact_text else head


def _milestone_lines(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        return _milestone_lines([value])
    if not isinstance(value, (list, tuple, set)):
        return _section_items(value)
    lines: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            label = _clean(item.get("label")) or _clean(item.get("release"))
            exit_criteria = _clean(item.get("exit_criteria")) or _clean(item.get("criteria"))
            lines.append(f"{label}: {exit_criteria}" if label and exit_criteria else label or exit_criteria)
        else:
            lines.extend(_section_items(item))
    return _unique([line for line in lines if line])


def _component_lines_for_workstream(
    idea_id: str,
    *,
    proposal: Mapping[str, Any],
    plan: GreenfieldTraceabilityPlan,
) -> list[str]:
    lines: list[str] = []
    for row in proposal.get("components", []):
        if not isinstance(row, Mapping):
            continue
        key = component_key(row)
        workstreams = set(plan.component_workstreams.get(key, ()))
        if idea_id not in workstreams:
            continue
        label = str(row.get("label", "")).strip() or key
        component_id = str(row.get("component_id", "")).strip() or key
        lines.append(f"`{component_id}` ({label})")
    return lines


def _workstream_refs_to_ids(values: Sequence[str], workstreams: Sequence[CreatedWorkstream]) -> list[str]:
    by_id = {workstream.idea_id: workstream.idea_id for workstream in workstreams}
    by_slug = {slugify(workstream.title): workstream.idea_id for workstream in workstreams}
    by_ref: dict[str, str] = {}
    for workstream in workstreams:
        refs = [
            workstream.idea_id,
            workstream.title,
            workstream.row.get("id"),
            workstream.row.get("idea_id"),
            workstream.row.get("workstream_id"),
            workstream.row.get("slug"),
            workstream.row.get("title"),
        ]
        for ref in refs:
            token = str(ref or "").strip()
            if not token:
                continue
            by_ref[token.upper()] = workstream.idea_id
            by_ref[token.casefold()] = workstream.idea_id
            slug = slugify(token)
            if slug:
                by_ref[slug] = workstream.idea_id
    result: list[str] = []
    for value in values:
        token = str(value).strip()
        normalized_id = token.upper()
        if normalized_id in by_id:
            result.append(by_id[normalized_id])
            continue
        if normalized_id in by_ref:
            result.append(by_ref[normalized_id])
            continue
        slug = slugify(token)
        if token.casefold() in by_ref:
            result.append(by_ref[token.casefold()])
            continue
        if slug in by_ref:
            result.append(by_ref[slug])
            continue
        if slug in by_slug:
            result.append(by_slug[slug])
    return _unique(result)


def _diagram_component_aliases(row: Mapping[str, Any]) -> set[str]:
    aliases: set[str] = set()
    for component in row.get("components", []):
        if isinstance(component, Mapping):
            aliases.update(_slug_aliases(str(component.get("component_id", ""))))
            aliases.update(_slug_aliases(str(component.get("name", ""))))
            aliases.update(_slug_aliases(str(component.get("label", ""))))
        else:
            aliases.update(_slug_aliases(str(component)))
    aliases.update(_slug_aliases(" ".join(collect_delimited_text_values(row, _COMPONENT_FIELDS))))
    return aliases


def _component_aliases(row: Mapping[str, Any]) -> set[str]:
    aliases: set[str] = set()
    aliases.update(_slug_aliases(str(row.get("component_id", ""))))
    aliases.update(_slug_aliases(str(row.get("label", ""))))
    aliases.update(_slug_aliases(str(row.get("name", ""))))
    return aliases


def _slug_aliases(value: str) -> set[str]:
    token = slugify(str(value).strip())
    aliases = {token} if token else set()
    if token:
        aliases.add(token.replace("-", ""))
    return {item for item in aliases if item}


def _workstream_haystack(row: Mapping[str, Any], *, fallback_title: str) -> str:
    values = [
        str(row.get("title", "") or fallback_title),
        str(row.get("problem", "")),
        str(row.get("opportunity", "")),
        str(row.get("product_view", "")),
        str(row.get("recommended_first_slice", "")),
        " ".join(delimited_text_values(row.get("success_metrics", []))),
        " ".join(collect_delimited_text_values(row, _COMPONENT_FIELDS)),
    ]
    return " ".join(values)


def _semantic_tokens(value: str) -> set[str]:
    tokens = set(ordered_terms(value, minimum=3, stopwords=_STOPWORDS))
    expanded: set[str] = set(tokens)
    for token in tokens:
        expanded.update(part for part in token.replace("_", "-").split("-") if len(part) > 2 and part not in _STOPWORDS)
    return expanded


def _merge_ids(existing: str, additions: Sequence[str]) -> list[str]:
    return _unique([*re.split(r"[,;\s]+", str(existing or "")), *additions])


def _join_ids(values: Sequence[str]) -> str:
    return ",".join(_unique(str(value).strip().upper() for value in values if str(value).strip()))


def _unique(values: Sequence[str]) -> list[str]:
    return dedupe_strings(values)


def _paragraph(values: Sequence[str]) -> str:
    return "\n\n".join(str(value).strip() for value in values if str(value).strip())


def _bullets(values: Sequence[str]) -> str:
    items = [_sentence_bullet(str(value).strip()) for value in values if str(value).strip()]
    return "\n".join(f"- {item}" for item in items) if items else "TBD."


def _sentence_bullet(value: str) -> str:
    item = value.strip()
    if not item:
        return item
    return item if item[-1:] in {".", "?", "!"} else f"{item}."


def _topology_dependency_lines(metadata: Mapping[str, str]) -> list[str]:
    lines: list[str] = []
    parent = str(metadata.get("workstream_parent", "")).strip()
    children = str(metadata.get("workstream_children", "")).strip()
    if parent:
        lines.append(f"Parent topology anchor: `{parent}`")
    if children:
        lines.append(f"Child topology anchors: `{children}`")
    if not lines:
        lines.append("No source-level dependency is claimed yet; implementation planning must confirm runtime ordering.")
    return lines


def _repo_relative(*, repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
