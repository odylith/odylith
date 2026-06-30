"""Atlas diagram-box extraction and reader-facing explanation rules."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_deferral_predicates import terminal_deferral_subject
from odylith.runtime.domain_intelligence.greenfield_text import normalize_action_target_language
from odylith.runtime.surfaces import atlas_diagram_intelligence
from odylith.runtime.surfaces import atlas_box_terms
from odylith.runtime.surfaces import display_text


_PLACEHOLDER_RE = re.compile(r"\b(tbd|todo|n/a|none|placeholder|fixme)\b", re.IGNORECASE)
_MECHANICAL_DESCRIPTION_RE = re.compile(
    r"\b("
    r"part of the path|incoming arrows|outgoing arrows|hands off|branch point|"
    r"read the boxes inside|diagram mechanics|through the arrows"
    r")\b",
    re.IGNORECASE,
)
_COMMON_COMPONENT_TOKENS = {
    "a",
    "an",
    "and",
    "app",
    "component",
    "control",
    "controls",
    "core",
    "for",
    "service",
    "services",
    "system",
    "the",
    "tracker",
    "view",
}
_SCOPE_OUT_RE = re.compile(
    r"^(?:not\s+in\s+scope|out\s+of\s+scope|no\s+external|no\s+third[- ]party)\b",
    re.IGNORECASE,
)
_OWNED_ACTION_RE = re.compile(
    r"^owns?\s+"
    r"(accepts?|assembles?|binds?|captures?|computes?|derives?|engraves?|estimates?|exports?|handles?|imports?|"
    r"issues?|links?|maintains?|normalizes?|optimizes?|performs?|predicts?|presents?|preserves?|pulls?|records?|renders?|"
    r"resolves?|shows?|stores?|tracks?|validates?|writes?)\b",
    re.IGNORECASE,
)
_ACTION_START_RE = re.compile(
    r"^(accepts?|assembles?|binds?|captures?|computes?|derives?|engraves?|estimates?|exports?|handles?|imports?|"
    r"issues?|links?|maintains?|normalizes?|optimizes?|performs?|predicts?|presents?|preserves?|pulls?|records?|renders?|"
    r"resolves?|shows?|stores?|tracks?|validates?|writes?)\b",
    re.IGNORECASE,
)
_LEGACY_COMPONENT_APPENDIX_RE = re.compile(
    r"\b("
    r"for release\s+\S+,\s+it receives or produces|"
    r"it matters for release\s+\S+\s+because the first|"
    r"reviewers trust it only when|"
    r"proof must stay inside|"
    r"the first workflow depends on|"
    r"the first path depends on"
    r")\b",
    re.IGNORECASE,
)
_GENERIC_DIAGRAM_TITLE_RE = re.compile(
    r"\b(context|sequence|ownership|proof|topology|diagram|view|state model|release map|workflow)\b",
    re.IGNORECASE,
)
_NODE_LABEL_RE = re.compile(
    r"""
    (?<![\w.-])
    (?P<id>[A-Za-z][\w.-]*)
    \s*
    (?:
      \[\[\s*(?P<bracket2>[^\]]+?)\s*\]\]
      |\[\s*"(?P<bracket_dq>[^"]+?)"\s*\]
      |\[\s*'(?P<bracket_sq>[^']+?)'\s*\]
      |\[\s*(?P<bracket>[^\]]+?)\s*\]
      |\{\{\s*(?P<brace2>[^}]+?)\s*\}\}
      |\{\s*(?P<brace>[^}]+?)\s*\}
      |\(\(\s*(?P<paren2>[^)]+?)\s*\)\)
      |\(\s*"(?P<paren_dq>[^"]+?)"\s*\)
      |\(\s*'(?P<paren_sq>[^']+?)'\s*\)
      |\(\s*(?P<paren>[^)]+?)\s*\)
    )
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class DiagramBoxExplanation:
    """Reader-facing explanation for one visible Mermaid box."""

    label: str
    role: str
    description: str
    generated: bool = False

    def as_dict(self) -> dict[str, str]:
        """Return the box explanation as a JSON-ready Atlas payload row."""
        return {
            "label": self.label,
            "role": self.role,
            "description": self.description,
        }


@dataclass(frozen=True)
class DiagramBoxContext:
    """Context used to make generated box copy about the project, not the arrows."""

    title: str = ""
    summary: str = ""
    source_text: str = ""
    components: tuple[Mapping[str, str], ...] = ()

    @property
    def project_name(self) -> str:
        return _project_name(title=self.title, summary=self.summary, source_text=self.source_text)

    @property
    def tracked_object(self) -> str:
        return atlas_box_terms.tracked_object_phrase(self.search_text)

    @property
    def tracked_objects(self) -> str:
        singular = self.tracked_object
        if singular.endswith("y"):
            return f"{singular[:-1]}ies"
        if singular.endswith("s"):
            return singular
        return f"{singular}s"

    @property
    def search_text(self) -> str:
        component_text = " ".join(
            f"{row.get('name', '')} {row.get('description', '')}" for row in self.components
        )
        return " ".join((self.title, self.summary, self.source_text, component_text))


def _clean_label(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = display_text.strip_inline_markdown_emphasis_tokens(text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        compact = " ".join(text.split())
        return terminal_deferral_subject(compact) or compact
    deferred_subject = terminal_deferral_subject(" ".join(lines))
    if deferred_subject:
        return deferred_subject
    if len(lines) == 1:
        return terminal_deferral_subject(lines[0]) or lines[0]
    first = lines[0]
    if first.endswith(":"):
        return f"{first} {', '.join(line.rstrip(',') for line in lines[1:])}"
    result = first
    for line in lines[1:]:
        if (
            result.endswith("/")
            or line.startswith("(")
            or re.search(r"\b(and|or|of|for|with)$", result, flags=re.IGNORECASE)
            or (len(lines) == 2 and len(result.split()) <= 2 and len(line.split()) <= 2)
        ):
            result = f"{result} {line}"
        else:
            break
    return " ".join(result.split())


def _label_key(value: str) -> str:
    text = str(value or "")
    if "·" in text:
        text = text.split("·", 1)[0]
    if re.match(r"^\s*proof\s+boundary\b", text, flags=re.IGNORECASE):
        text = "proof boundary"
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def clean_component_description(*, name: str, description: str) -> str:
    """Return concise reader-facing component copy for Atlas payloads."""

    text = _clean_label(description).replace("`", "").strip()
    if not text:
        return ""
    split_match = _LEGACY_COMPONENT_APPENDIX_RE.search(text)
    if split_match is not None:
        text = text[: split_match.start()].strip(" ;,.-")
    stripped_name = _strip_leading_component_name(name=name, text=text)
    if stripped_name and _component_name_key(stripped_name):
        text = stripped_name
    stripped_kind = re.sub(
        r"^(?:service|component|surface|adapter|engine|store|model|resolver)\b\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    if stripped_kind:
        text = stripped_kind
    text = re.sub(
        r"^(?:is\s+)?(?:a|an)\s+[a-z -]+?\s+component\s+responsible\s+for\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    text = re.sub(r"^(?:is\s+)?responsible\s+for\s+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(
        r"\s+with\s+\S+\s+as\s+its\s+initial(?:\s+evidence\s+anchor)?\.?$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" ;,")
    text = normalize_action_target_language(text)
    text = re.sub(r";\s*serve\s+as\b", "; serves as", text, flags=re.IGNORECASE)
    text = _OWNED_ACTION_RE.sub(lambda match: str(match.group(1)), text).strip()
    text = re.sub(r"^owns?\s+owns?\s+", "owns ", text, flags=re.IGNORECASE).strip()
    if not text:
        return ""
    if re.match(r"^owns?\b", text, flags=re.IGNORECASE):
        text = "Owns " + re.sub(r"^owns?\s+", "", text, flags=re.IGNORECASE).strip()
    else:
        text = text[:1].upper() + text[1:]
    return _first_sentence(text)


def _strip_leading_component_name(*, name: str, text: str) -> str:
    name_words = _component_name_key(name).split()
    if not name_words:
        return text
    for keep in range(len(name_words), 0, -1):
        pattern = r"^\s*" + r"[\s,/-]+".join(re.escape(word) for word in name_words[:keep]) + r"\b\s*"
        stripped = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip()
        if stripped != text.strip():
            return stripped or text
    return text


def _component_name_key(value: str) -> str:
    text = re.sub(
        r"\b(service|component|surface|adapter|engine|store|model|resolver)\b",
        " ",
        str(value or ""),
        flags=re.IGNORECASE,
    )
    text = re.sub(r"[^a-z0-9]+", " ", text.casefold())
    return " ".join(text.split())


def _subgraph_label(line: str) -> str:
    token = line.strip().split(None, 1)[1].strip() if len(line.strip().split(None, 1)) > 1 else ""
    bracket = re.search(r"\[\s*['\"]?(.+?)['\"]?\s*\]", token)
    if bracket:
        return _clean_label(bracket.group(1))
    quoted = re.match(r"['\"](.+?)['\"]", token)
    if quoted:
        return _clean_label(quoted.group(1))
    identifier = re.split(r"\s|\[", token, maxsplit=1)[0].strip()
    remainder = token[len(identifier) :].strip() if identifier else token
    return _clean_label(remainder or identifier)


def _first_label_match(match: re.Match[str]) -> str:
    for name, value in match.groupdict().items():
        if name != "id" and value:
            return _clean_label(value)
    return ""


def _generated_container_description(label: str, context: DiagramBoxContext) -> str:
    project = context.project_name or _sentence_subject(label)
    if _label_key(label) == _label_key(project):
        return (
            f"{label} is the product boundary. It contains the actors, interfaces, records, controls, "
            "and evidence paths that must work together before the release claim can be trusted."
        )
    return (
        f"{label} is the product boundary for {project}. It contains the actors, interfaces, records, "
        "controls, and evidence paths that must work together before the release claim can be trusted."
    )


def _generated_node_description(
    label: str,
    container_stack: Sequence[str],
    context: DiagramBoxContext,
) -> str:
    role_sentence = _node_action_sentence(label, context=context)
    if container_stack:
        container = container_stack[-1]
        return f"Within {container}, {role_sentence}"
    return role_sentence


def _node_action_sentence(label: str, *, context: DiagramBoxContext) -> str:
    clean = _clean_label(label).strip()
    lowered = clean.lower()
    subject = _sentence_subject(clean)
    project = context.project_name or "the product"
    tracked_object = context.tracked_object
    tracked_objects = context.tracked_objects
    matched_components = _matching_components(label=clean, context=context)
    if matched_components and _component_match_should_win(label=clean, matched_components=matched_components):
        return _component_grounded_sentence(
            subject=subject,
            label=clean,
            context=context,
            matched_components=matched_components,
        )
    if _SCOPE_OUT_RE.search(clean):
        project_phrase = project if project != "the product" else "this product"
        return (
            f"{subject} is intentionally outside the first-release proof boundary for {project_phrase}. "
            "It matters because reviewers need to see which integrations, claims, or responsibilities are deferred."
        )
    if _looks_like_person_role_label(clean):
        project_phrase = project if project != "the product" else "this product"
        return (
            f"{subject} is a person {project_phrase} must serve. "
            f"They supply, review, or depend on {_object_with_article(tracked_object)}, so the first release must make that outcome understandable and trustworthy."
        )
    if _has_any(lowered, ("steward", "owner", "operator")) and not _has_any(
        lowered,
        ("web", "surface", "service", "interface", "status"),
    ):
        return (
            f"{subject} owns or manages the {tracked_objects} being tracked in {project}. "
            f"They need trustworthy identity, state, evidence, and history for each {tracked_object} before decisions move forward."
        )
    if _has_any(lowered, ("observer", "community monitor", "field monitor", "monitor")) and not _has_any(lowered, ("service", "provider", "adapter")):
        return (
            f"{subject} captures real-world observations for {tracked_objects}. "
            "Their input only becomes trusted when it carries source, time, location, evidence, and review context."
        )
    if _has_any(lowered, ("verifier", "auditor", "reviewer")):
        return (
            f"{subject} checks whether a {tracked_object} claim is supported. "
            "They need to trace the claim back to the active record, source evidence, derivation step, and audit history."
        )
    if _has_any(lowered, ("coordinator", "program lead", "program manager")):
        return (
            f"{subject} manages the program across owners, submitters, reviewers, and scoped {tracked_objects}. "
            "They need to know what is in scope, which evidence is missing, and what is ready for the first release."
        )
    if _has_any(
        lowered,
        (
            "remote-sensing provider",
            "remote-sensing providers",
            "remote sensing provider",
            "remote sensing providers",
            "imagery provider",
            "imagery providers",
            "sensor provider",
            "sensor providers",
        ),
    ):
        return (
            f"{subject} is an external source of remote signals for {tracked_objects}. "
            "Those signals matter only when they retain provider, sensor, time, location, and provenance."
        )
    if _has_any(lowered, ("library", "libraries", "model", "dsp", "operating system", "subsystem")):
        return (
            f"{subject} is an external input, tool, or runtime dependency for {tracked_objects}. "
            "It matters only when the product records what came from it, when it was used, and which claim or output it supports."
        )
    if _has_any(lowered, ("remote sensing adapter", "remote-sensing adapter", "imagery adapter")):
        return (
            f"{subject} turns remote-observation signals into project evidence. "
            f"It connects provider output to the right {tracked_object}, active boundary or state version, and provenance record."
        )
    if _has_any(lowered, ("boundary source", "cadastral", "geometry source", "land record")):
        return (
            f"{subject} supplies the external boundary or ownership reference for {tracked_objects}. "
            f"The release needs this because a claim is meaningless unless the product knows which {tracked_object} and version it describes."
        )
    if _has_any(lowered, ("identity provider", "idp")):
        return (
            f"{subject} supplies trusted actor and organization identity. "
            "It lets the product distinguish who submitted, changed, reviewed, or approved each record."
        )
    if _has_any(lowered, ("auth", "authentication", "authorization", "session")):
        return (
            f"{subject} attributes product actions to a known actor. "
            f"It matters because {tracked_object} changes, observations, evidence submissions, and reviews must be accountable."
        )
    if _has_any(lowered, ("privacy", "sharing", "redaction", "access")):
        return (
            f"{subject} governs who can see records, evidence, derived state, and audit history. "
            "It matters when project data is sensitive, partner-scoped, legally constrained, or unsafe to expose broadly."
        )
    if _has_any(lowered, ("notification", "sms", "email", "alert")):
        return (
            f"{subject} is a later-wave communication path. "
            "It should notify the right people when state changes, evidence is missing, or review is needed, but it should not define the first release proof boundary."
        )
    if _has_any(lowered, ("field capture", "capture surface", "mobile capture")):
        return (
            f"{subject} lets field users submit evidence against a known {tracked_object}. "
            "It should capture observation type, time, location, notes, media references, and source identity without overwriting prior history."
        )
    if _has_any(lowered, ("web surface", "portal", "console", "workspace", "dashboard", "ui", "interface")):
        return (
            f"{subject} is the primary user surface for reviewing and changing {tracked_objects}. "
            "It should show identity, current state, recent observations, evidence status, and review state in one coherent view."
        )
    if _has_any(lowered, ("core services", "record core", "evidence core", "core:")):
        return (
            f"{subject} owns trusted record layer for {project}: records, state versions, evidence links, derivation, and audit history. "
            "It matters because the first release must turn scattered inputs into traceable claims."
        )
    if matched_components:
        return _component_grounded_sentence(
            subject=subject,
            label=clean,
            context=context,
            matched_components=matched_components,
        )
    if _has_any(lowered, ("product", "program", "release")):
        return f"{subject} defines the product scope, target outcome, and proof boundary that release work must satisfy."
    if _has_any(lowered, ("interface", "dashboard", "ui", "surface", "portal", "console", "app", "workspace")):
        return (
            f"{subject} presents the domain object, latest state, next decision, and supporting evidence "
            "for the user responsibility it serves."
        )
    if _has_any(lowered, ("radar", "backlog", "workstream", "queue")):
        return f"{subject} tracks the work choices, priorities, and next slices that need governed follow-through."
    if _has_any(lowered, ("atlas", "diagram", "topology", "map")):
        return f"{subject} shows the system shape, ownership boundaries, and flow relationships reviewers need to understand."
    if _has_any(lowered, ("compass", "timeline", "status")):
        return f"{subject} summarizes current runtime state, recent movement, and the evidence behind the status."
    if _has_any(lowered, ("plan", "plans", "implementation path", "implementation sequence")):
        return f"{subject} turns selected work into an implementation path, validation obligation, and release gate."
    if _has_any(lowered, ("router", "routing")):
        return f"{subject} chooses where work should go next and records why that route is admissible."
    if _has_any(lowered, ("orchestrator", "coordination")):
        return f"{subject} coordinates bounded work across owners and brings completion evidence back into the flow."
    if _has_any(lowered, ("broker", "proposal", "intervention", "observation", "assist")):
        return f"{subject} decides what should be shown to the operator and when it is safe to surface."
    if _has_any(lowered, ("chatter", "chat", "message", "narration")):
        return f"{subject} turns governed state into user-visible language without changing the underlying source truth."
    if _has_any(lowered, ("handshake", "contract")):
        return f"{subject} passes agreed state across a boundary and preserves the rules the next step must obey."
    if _has_any(lowered, ("owner", "operator", "reviewer", "approver", "advocate", "user", "engineer", "maintainer")):
        return f"{subject} makes or accepts the decisions this part of the flow depends on."
    if _has_any(lowered, ("sensor", "sensing", "monitor", "measurement", "telemetry", "signal", "probe", "scanner")):
        return f"{subject} measures the current state and feeds the decision or proof step that follows."
    if _has_any(lowered, ("decision", "policy", "rule", "eligibility", "approval", "review", "gate", "core", "engine", "tribunal")):
        return f"{subject} decides whether the next action is allowed, blocked, or ready for review."
    if _has_any(lowered, ("controller", "actuator", "executor", "execution", "worker", "runner", "adapter")):
        return f"{subject} performs the bounded action and should expose the result for verification."
    if _has_any(lowered, ("log", "record", "ledger", "evidence", "audit", "receipt", "proof", "history", "casebook")):
        return f"{subject} records the evidence needed to review what happened and why it was allowed."
    if _has_any(lowered, ("repo", "registry", "catalog", "store", "database", "source", "memory", "bundle", "snapshot")):
        return f"{subject} stores the source information that downstream boxes read or update."
    if _has_any(lowered, ("connector", "gateway", "api", "integration", "webhook", "bridge", "rail")):
        return f"{subject} moves data or requests across a system boundary and should preserve handoff evidence."
    if _looks_like_state_object(clean):
        return f"{subject} is the object whose state changes as the flow moves from trigger to outcome."
    return (
        f"{subject} is a named responsibility in {project}. It should name the domain object it owns, "
        "the evidence or decision it receives or produces, and the release condition it protects."
    )


def _project_name(*, title: str, summary: str, source_text: str) -> str:
    title_text = _clean_label(title).strip()
    if title_text and not _GENERIC_DIAGRAM_TITLE_RE.search(title_text):
        return title_text
    summary_text = _clean_label(summary)
    match = re.search(
        r"\b(?:of|for|inside)\s+the\s+([A-Z][A-Za-z0-9 -]+?)(?:\s+showing|[,.]|$)",
        summary_text,
    )
    if match:
        return match.group(1).strip()
    subgraph = re.search(r"subgraph\s+\w+\s+\[\s*['\"]([^'\"]+)['\"]\s*\]", source_text)
    if subgraph:
        return _clean_label(subgraph.group(1))
    label_match = re.search(
        r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){1,4})\s+(?:shows?|separates?|connects?|owns?|turns?)\b",
        summary_text,
    )
    if label_match and not _GENERIC_DIAGRAM_TITLE_RE.search(label_match.group(1)):
        return label_match.group(1).strip()
    return "the product"


def _matching_components(*, label: str, context: DiagramBoxContext) -> tuple[Mapping[str, str], ...]:
    label_tokens = _meaningful_tokens(label)
    if not label_tokens:
        return ()
    label_key = _component_name_key(label)
    exact_matches = [
        row
        for row in context.components
        if label_key and label_key == _component_name_key(str(row.get("name", "")).strip())
    ]
    if exact_matches:
        return tuple(exact_matches[:1])
    matches: list[tuple[int, Mapping[str, str]]] = []
    for row in context.components:
        name = str(row.get("name", "")).strip()
        description = str(row.get("description", "")).strip()
        component_tokens = _meaningful_tokens(f"{name} {description}")
        if not component_tokens:
            continue
        overlap = label_tokens & component_tokens
        name_overlap = label_tokens & _meaningful_tokens(name)
        if len(name_overlap) >= 1 and len(overlap) >= 2:
            matches.append((len(overlap) + len(name_overlap), row))
        elif len(overlap) >= 3:
            matches.append((len(overlap), row))
    return tuple(row for _score, row in sorted(matches, key=lambda item: -item[0])[:4])


def _component_match_should_win(*, label: str, matched_components: Sequence[Mapping[str, str]]) -> bool:
    """Return true when a generated box label is clearly a component label."""
    if len(matched_components) != 1:
        return False
    label_key = _component_name_key(label)
    component_key = _component_name_key(str(matched_components[0].get("name", "")).strip())
    return bool(component_key and (label_key == component_key or "…" in label or "..." in label))


def _component_grounded_sentence(
    *,
    subject: str,
    label: str,
    context: DiagramBoxContext,
    matched_components: Sequence[Mapping[str, str]],
) -> str:
    project = context.project_name or "the product"
    tracked_object = context.tracked_object
    tracked_objects = context.tracked_objects
    component_names = [str(row.get("name", "")).strip() for row in matched_components if str(row.get("name", "")).strip()]
    component_descriptions = [
        clean_component_description(
            name=str(row.get("name", "")).strip(),
            description=str(row.get("description", "")).strip(),
        )
        for row in matched_components
        if str(row.get("description", "")).strip()
    ]
    if len(matched_components) > 1 or _has_any(label.casefold(), ("core services", "record core", "evidence core", "core:")):
        owned = _join_list(component_names) or "the core records, evidence, state, and audit responsibilities"
        evidence_target = _review_outcome_phrase(tracked_object)
        detail = ""
        if component_descriptions:
            first_responsibility = _responsibility_phrase(component_descriptions[0], subject=subject)
            if first_responsibility:
                detail = f" It contributes {_ensure_gerund_phrase(first_responsibility)}."
        return (
            f"{subject} is the trusted record core for {project}. It ties {owned} into one release boundary "
            f"so {evidence_target} can be traced from input to review.{detail}"
        )
    description = component_descriptions[0] if component_descriptions else ""
    if description:
        responsibility = _responsibility_phrase(description, subject=subject)
        if _ACTION_START_RE.match(responsibility):
            return (
                f"{subject} {responsibility}. "
                f"It matters because release proof must make this boundary traceable from accepted input to {_review_outcome_phrase(tracked_object)}."
            )
        return (
            f"{subject} owns {responsibility}. "
            f"It matters because release proof must make this boundary traceable from accepted input to {_review_outcome_phrase(tracked_object)}."
        )
    return (
        f"{subject} owns a named responsibility for {tracked_objects}. "
        "It matters because release proof must show what it receives, preserves, or produces."
    )


def _responsibility_phrase(value: str, *, subject: str) -> str:
    text = _first_sentence(value).strip()
    if not text:
        return "the domain responsibility assigned to this boundary"
    text = re.sub(rf"^{re.escape(subject)}\s+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(
        r"^(?:is responsible for|is a [a-z ]+ responsible for|owns?|records?|stores?|tracks?|links?|maintains?|assembles?|evaluates?|derives?|serves?)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    text = text[:1].lower() + text[1:] if text else text
    return text.rstrip(".")


def _ensure_gerund_phrase(value: str) -> str:
    """Return a readable contribution phrase for optional component detail."""
    text = str(value or "").strip().rstrip(".")
    if not text:
        return ""
    replacements = (
        (r"^accepts?\b", "accepting"),
        (r"^assembles?\b", "assembling"),
        (r"^binds?\b", "binding"),
        (r"^captures?\b", "capturing"),
        (r"^computes?\b", "computing"),
        (r"^derives?\b", "deriving"),
        (r"^engraves?\b", "engraving"),
        (r"^estimates?\b", "estimating"),
        (r"^exports?\b", "exporting"),
        (r"^imports?\b", "importing"),
        (r"^links?\b", "linking"),
        (r"^maintains?\b", "maintaining"),
        (r"^performs?\b", "performing"),
        (r"^preserves?\b", "preserving"),
        (r"^records?\b", "recording"),
        (r"^renders?\b", "rendering"),
        (r"^resolves?\b", "resolving"),
        (r"^stores?\b", "storing"),
        (r"^tracks?\b", "tracking"),
        (r"^validates?\b", "validating"),
        (r"^writes?\b", "writing"),
    )
    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
        if updated != text:
            return updated
    return text


def _object_with_article(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "the tracked record"
    if re.match(r"^(?:a|an|the)\s+", text, flags=re.IGNORECASE):
        return text
    return f"the {text}"


def _review_outcome_phrase(value: str) -> str:
    text = str(value or "").strip()
    if not text or re.search(r"\b(proof|boundary|gate|release)\b", text, flags=re.IGNORECASE):
        return "a reviewed release outcome"
    return f"a reviewed outcome for {_object_with_article(text)}"


def _first_sentence(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    match = re.match(r"(.+?[.!?])(?:\s|$)", text)
    return match.group(1).strip() if match else text.rstrip(".") + "."


def _meaningful_tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9'-]*", str(value or "").casefold())
        if len(token) >= 3 and token not in _COMMON_COMPONENT_TOKENS
    }
    expansions: set[str] = set()
    for token in tokens:
        if token.endswith("ies") and len(token) > 4:
            expansions.add(f"{token[:-3]}y")
        elif token.endswith("s") and len(token) > 3:
            expansions.add(token[:-1])
    return tokens | expansions


def _join_list(values: Sequence[str]) -> str:
    rows = [str(value).strip() for value in values if str(value).strip()]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _sentence_subject(label: str) -> str:
    text = _clean_label(label).strip().rstrip(".")
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()
    return text[:1].upper() + text[1:] if text else "This step"


def _has_any(value: str, markers: Sequence[str]) -> bool:
    return any(re.search(rf"\b{re.escape(marker)}\b", value) for marker in markers)


def _looks_like_state_object(label: str) -> bool:
    lowered = label.lower().strip()
    if lowered.startswith(("one ", "a ", "an ", "the ")):
        return True
    return bool(re.search(r"\b(state|record|object|request|contract|endpoint|entity|item|artifact|package)\b", lowered))


def _looks_like_person_role_label(label: str) -> bool:
    lowered = _clean_label(label).casefold()
    if not lowered:
        return False
    tokens = re.findall(r"[a-z][a-z0-9'-]*", lowered)
    if not tokens or len(tokens) > 7:
        return False
    system_tokens = {
        "adapter",
        "app",
        "application",
        "console",
        "command",
        "dashboard",
        "desk",
        "engine",
        "form",
        "interface",
        "intake",
        "ledger",
        "model",
        "platform",
        "portal",
        "product",
        "queue",
        "register",
        "registry",
        "service",
        "store",
        "surface",
        "system",
        "tool",
        "tracker",
        "view",
        "workspace",
    }
    if any(token in system_tokens for token in tokens):
        return False
    if _ACTION_START_RE.match(lowered) or re.match(
        r"^(?:assign|check|choose|collect|compare|create|display|download|enter|export|fix|generate|import|log|open|prove|record|repair|review|route|save|select|send|show|submit|triage|update|upload|validate|view)\b",
        lowered,
    ):
        return False
    person_tokens = {
        "actor",
        "actors",
        "applicant",
        "applicants",
        "beneficiary",
        "beneficiaries",
        "client",
        "clients",
        "customer",
        "customers",
        "lead",
        "leads",
        "participant",
        "participants",
        "performer",
        "performers",
        "requester",
        "requesters",
        "reviewer",
        "reviewers",
        "stakeholder",
        "stakeholders",
        "user",
        "users",
    }
    return any(token in person_tokens for token in tokens)


def extract_diagram_boxes_from_mermaid(
    source_text: str,
    *,
    component_rows: Sequence[Mapping[str, str]] = (),
    diagram_title: str = "",
    diagram_summary: str = "",
) -> tuple[DiagramBoxExplanation, ...]:
    """Extract visible flowchart containers and node boxes from Mermaid source."""
    boxes: list[DiagramBoxExplanation] = []
    seen: set[str] = set()
    container_stack: list[str] = []
    graph = atlas_diagram_intelligence.parse_mermaid_graph(source_text)
    context = DiagramBoxContext(
        title=diagram_title,
        summary=diagram_summary,
        source_text=source_text,
        components=tuple(component_rows),
    )

    for raw_line in str(source_text or "").splitlines():
        line = raw_line.split("%%", 1)[0].strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered == "end":
            if container_stack:
                container_stack.pop()
            continue
        if lowered.startswith(("flowchart", "graph ", "sequencediagram")):
            continue
        if lowered.startswith(("autonumber", "note ", "activate ", "deactivate ")):
            continue
        if lowered.startswith("participant "):
            label = _sequence_participant_label(line)
            display_label = _resolved_box_label(label=label, context=context)
            key = _label_key(display_label)
            if display_label and key and key not in seen:
                boxes.append(
                    DiagramBoxExplanation(
                        label=display_label,
                        role="Participant",
                        description=_generated_node_description(display_label, container_stack, context),
                        generated=True,
                    )
                )
                seen.add(key)
            continue
        if lowered.startswith("subgraph "):
            label = _subgraph_label(line)
            if label:
                key = _label_key(label)
                if key and key not in seen:
                    boxes.append(
                        DiagramBoxExplanation(
                            label=label,
                            role="Container",
                            description=_generated_container_description(label, context),
                            generated=True,
                        )
                    )
                    seen.add(key)
                container_stack.append(label)
            continue
        for match in _NODE_LABEL_RE.finditer(line):
            node_id = str(match.group("id") or "").strip().lower()
            if node_id in {"subgraph", "flowchart", "graph", "style", "classdef", "linkstyle"}:
                continue
            label = _first_label_match(match)
            key = _label_key(label)
            if not label or not key or key in seen:
                continue
            display_label = _resolved_box_label(label=label, context=context)
            display_key = _label_key(display_label)
            if display_key and display_key in seen:
                continue
            graph_description = atlas_diagram_intelligence.node_explanation_from_graph(
                label=label,
                source_text=source_text,
            )
            semantic_description = _generated_node_description(display_label, container_stack, context)
            graph_role = atlas_diagram_intelligence.node_role_from_graph(
                label=label,
                source_text=source_text,
            )
            role = container_stack[-1] if container_stack else (graph_role or "Step")
            boxes.append(
                DiagramBoxExplanation(
                    label=display_label,
                    role=role,
                    description=_merge_node_description(
                        semantic_description=semantic_description,
                        graph_description=graph_description,
                    ),
                    generated=True,
                )
            )
            seen.add(display_key or key)
    for node_id in graph.node_ids():
        label = graph.label(node_id)
        key = _label_key(label)
        if not label or not key or key in seen:
            continue
        if _low_signal_generated_graph_label(label=label, node_id=node_id):
            continue
        display_label = _resolved_box_label(label=label, context=context)
        display_key = _label_key(display_label)
        if display_key and display_key in seen:
            continue
        boxes.append(
            DiagramBoxExplanation(
                label=display_label,
                role=atlas_diagram_intelligence.describe_graph_node_role(graph=graph, node_id=node_id),
                description=atlas_diagram_intelligence.describe_graph_node(graph=graph, node_id=node_id)
                or _generated_node_description(display_label, (), context),
                generated=True,
            )
        )
        seen.add(display_key or key)
    return tuple(boxes)


def _sequence_participant_label(line: str) -> str:
    """Return the visible label from a Mermaid sequence participant row."""
    match = re.match(
        r"^\s*(?:participant|actor)\s+\S+\s+as\s+(.+?)\s*$",
        line,
        flags=re.IGNORECASE,
    )
    if match:
        return _clean_label(match.group(1))
    match = re.match(r"^\s*(?:participant|actor)\s+(.+?)\s*$", line, flags=re.IGNORECASE)
    return _clean_label(match.group(1)) if match else ""


def _resolved_box_label(*, label: str, context: DiagramBoxContext) -> str:
    """Resolve generated/truncated labels to full component labels when catalog truth is available."""
    clean = _clean_label(label)
    if "…" not in clean and "..." not in clean:
        return clean
    matches = _matching_components(label=clean, context=context)
    if len(matches) != 1:
        return clean
    name = str(matches[0].get("name", "")).strip()
    return name or clean


def _merge_node_description(*, semantic_description: str, graph_description: str) -> str:
    semantic = _clean_label(semantic_description)
    graph = _clean_label(graph_description)
    if not graph:
        return semantic
    if _MECHANICAL_DESCRIPTION_RE.search(graph):
        return semantic
    if semantic and "is a named responsibility" not in semantic:
        return semantic
    if not semantic or "is a named responsibility" in semantic:
        return graph
    if graph.casefold() == semantic.casefold() or graph.casefold() in semantic.casefold():
        return semantic
    return f"{semantic} {graph}"


def _low_signal_generated_graph_label(*, label: str, node_id: str) -> bool:
    clean_label = _clean_label(label)
    clean_id = _clean_label(node_id)
    if not clean_label:
        return True
    if clean_label.casefold() in {"primary", "secondary", "later", "optional"}:
        return True
    if re.fullmatch(r"(?:component|actor|external|owner|proof|node)\d+", clean_label, flags=re.IGNORECASE):
        return True
    if clean_label.casefold() != clean_id.casefold():
        return False
    return bool(re.fullmatch(r"[A-Z]|\d+|node\d+", clean_label, flags=re.IGNORECASE))


def catalog_box_copy_errors(*, box: Mapping[str, Any], context: str) -> tuple[str, ...]:
    """Return authoring errors for hand-written Atlas diagram-box copy."""
    label = _clean_label(str(box.get("label", "")).strip())
    description = display_text.strip_inline_markdown_emphasis(box.get("description", ""))
    errors: list[str] = []
    if not label or not description:
        return (f"{context} requires non-empty `label` and `description`",)
    if _PLACEHOLDER_RE.search(description):
        errors.append(f"{context} description must not use placeholder copy")
    if _MECHANICAL_DESCRIPTION_RE.search(description):
        errors.append(f"{context} description must explain project meaning, not diagram mechanics")
    word_count = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", description))
    if word_count < 8:
        errors.append(f"{context} description must explain the box in a complete sentence")
    if description[-1:] not in {".", "!", "?"}:
        errors.append(f"{context} description must end with sentence punctuation")
    label_words = set(re.findall(r"[a-z0-9]+", label.lower()))
    description_words = set(re.findall(r"[a-z0-9]+", description.lower()))
    if label_words and description_words and description_words.issubset(label_words):
        errors.append(f"{context} description must add meaning beyond the label")
    return tuple(errors)


def normalize_catalog_diagram_boxes(
    *,
    raw_boxes: Any,
    context: str,
    errors: list[str],
) -> tuple[DiagramBoxExplanation, ...]:
    """Validate and normalize catalog-authored diagram box explanations."""
    if raw_boxes in (None, ""):
        return ()
    if not isinstance(raw_boxes, list):
        errors.append(f"{context}: `diagram_boxes` must be a list when present")
        return ()
    normalized: list[DiagramBoxExplanation] = []
    seen: set[str] = set()
    for box_idx, box in enumerate(raw_boxes):
        box_context = f"{context}: diagram_boxes[{box_idx}]"
        if not isinstance(box, Mapping):
            errors.append(f"{box_context} must be an object")
            continue
        errors.extend(catalog_box_copy_errors(box=box, context=box_context))
        label = _clean_label(str(box.get("label", "")).strip())
        description = display_text.strip_inline_markdown_emphasis(box.get("description", ""))
        role = str(box.get("role", "")).strip()
        key = _label_key(label)
        if not label or not description:
            continue
        if key in seen:
            errors.append(f"{box_context} duplicates diagram box label `{label}`")
            continue
        seen.add(key)
        normalized.append(
            DiagramBoxExplanation(
                label=label,
                role=role,
                description=description,
                generated=False,
            )
        )
    return tuple(normalized)


def merge_diagram_box_explanations(
    *,
    source_text: str,
    catalog_boxes: Iterable[DiagramBoxExplanation],
    component_rows: Sequence[Mapping[str, str]] = (),
    diagram_title: str = "",
    diagram_summary: str = "",
) -> tuple[dict[str, str], ...]:
    """Merge Mermaid-derived box inventory with catalog-authored explanations."""
    generated = extract_diagram_boxes_from_mermaid(
        source_text,
        component_rows=component_rows,
        diagram_title=diagram_title,
        diagram_summary=diagram_summary,
    )
    catalog_rows = tuple(catalog_boxes)
    catalog_by_label = {_label_key(box.label): box for box in catalog_rows if _label_key(box.label)}
    merged: list[DiagramBoxExplanation] = []
    used: set[str] = set()
    for generated_box in generated:
        key = _label_key(generated_box.label)
        override = catalog_by_label.get(key)
        if override is None:
            merged.append(generated_box)
        else:
            merged.append(
                DiagramBoxExplanation(
                    label=override.label,
                    role=override.role or generated_box.role,
                    description=override.description,
                    generated=False,
                )
            )
            used.add(key)
    for catalog_box in catalog_rows:
        key = _label_key(catalog_box.label)
        if key and key not in used and key not in {_label_key(box.label) for box in generated}:
            merged.append(catalog_box)
    return tuple(box.as_dict() for box in merged)


def diagram_box_labels(boxes: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return normalized labels for coverage checks."""
    return tuple(_label_key(str(box.get("label", ""))) for box in boxes if _label_key(str(box.get("label", ""))))
