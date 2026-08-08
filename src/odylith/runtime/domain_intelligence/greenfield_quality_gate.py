"""Fail-closed quality gates for greenfield proposal product content."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence.greenfield_component_contract import public_prose_quality_issues
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_requirement_control_clause
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import progression_marker_count
from odylith.runtime.domain_intelligence.greenfield_text import text_values

_CONTROL_PLANE_LEAKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Radar", re.compile(r"\bRadar\b")),
    ("Registry", re.compile(r"\b(?:Odylith\s+Registry|(?:in|from|through|to|via)\s+Registry|Registry\s+(?:anchors|assigns|carries|component|components|dossiers|names|records|shows|turns))\b")),
    ("Atlas", re.compile(r"\bAtlas\b")),
    ("Compass", re.compile(r"\bCompass\b")),
    ("Tribunal", re.compile(r"\bTribunal\b")),
    ("Odylith surfaces", re.compile(r"\bOdylith\s+surfaces\b", re.IGNORECASE)),
    ("Odylith owns", re.compile(r"\bOdylith\s+owns\b", re.IGNORECASE)),
    ("Odylith assumptions", re.compile(r"\bOdylith\s+assumptions\b", re.IGNORECASE)),
    ("governance surfaces", re.compile(r"\bgovernance\s+surfaces\b", re.IGNORECASE)),
    ("governance records", re.compile(r"\bgovernance\s+records\b", re.IGNORECASE)),
    ("surface refresh", re.compile(r"\bsurface\s+refresh\b", re.IGNORECASE)),
    ("refreshed surfaces", re.compile(r"\brefreshed\s+surfaces\b", re.IGNORECASE)),
    ("app-surface", re.compile(r"\bapp[-\s]+surface\b", re.IGNORECASE)),
    ("proof surface", re.compile(r"\bproof\s+surface\b", re.IGNORECASE)),
    ("governed control surface", re.compile(r"\bgoverned\s+control\s+surface\b", re.IGNORECASE)),
)

_STALE_GENERIC_TERMS: tuple[str, ...] = (
    "Experience Boundary",
    "Domain Core",
    "Verification Harness",
    "Project intelligence renderer",
    "Create or accept project truth",
    "Primary user",
    "Project operator",
    "Domain reviewer",
    "Implementation owner",
    "Evidence owner",
    "Operator Workspace",
    "Product Model",
    "Evidence Harness",
    "Central Thing the Product",
)

_GENERIC_ACTOR_LABELS: tuple[str, ...] = (
    "Operator",
    "Maintainer",
    "Reviewer",
    "Primary user",
    "Project operator",
    "Domain reviewer",
    "Implementation owner",
    "Evidence owner",
    "End-user advocate",
    "Workflow operator",
    "Risk reviewer",
    "Proof reviewer",
    "Build owner",
)

_DIRECTIVE_LEAKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("show the interpretation", re.compile(r"\bshow\s+(?:the\s+)?interpretation\b", re.IGNORECASE)),
    ("show direction choices", re.compile(r"\bshow\s+(?:the\s+)?direction\s+choices\b", re.IGNORECASE)),
    ("do not write records", re.compile(r"\bdo\s+not\s+write\s+(?:any\s+)?records?\b", re.IGNORECASE)),
    ("until I confirm", re.compile(r"\buntil\s+i\s+confirm\b", re.IGNORECASE)),
    ("before I confirm", re.compile(r"\bbefore\s+i\s+confirm\b", re.IGNORECASE)),
    ("apply as-is", re.compile(r"\bapply\s+as[-\s]is\b", re.IGNORECASE)),
    ("greenfield propose", re.compile(r"\bgreenfield\s+propose\b", re.IGNORECASE)),
    ("repo-root", re.compile(r"--repo-root\b", re.IGNORECASE)),
)

_INTENT_DOMAIN_TERM_KEYS = (
    "prompt",
    "title",
    "summary",
    "product_story",
    "product_view",
    "state_object",
    "first_path",
    "proof_boundary",
    "human_actors",
    "external_systems",
    "internal_systems",
    "assumptions",
    "ambiguities",
    "non_goals",
)

_GOVERNANCE_PREP_PHRASES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("execution spine before source exists", re.compile(r"\bexecution\s+spine\s+before\s+source\s+exists\b", re.IGNORECASE)),
    ("trace to product intent", re.compile(r"\btrace\s+to\s+product\s+intent\b", re.IGNORECASE)),
    ("component, diagram, release gate framing", re.compile(r"\bcomponents?,\s*diagrams?,\s*release\s+gates?\b", re.IGNORECASE)),
    ("proposal-first product program", re.compile(r"\bproposal[-\s]first\s+product\s+program\b", re.IGNORECASE)),
    ("accepted product truth before artifacts", re.compile(r"\baccepted\s+product\s+truth\s+before\b", re.IGNORECASE)),
    ("accepted project story before artifacts", re.compile(r"\baccepted\s+project\s+story\s+before\b", re.IGNORECASE)),
)

_MECHANICAL_ARTIFACT_PHRASES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("diagram mechanics", re.compile(r"\b(?:part of the path|incoming arrows|outgoing arrows|starts the path|branch point)\b", re.IGNORECASE)),
    ("generic current-state UI copy", re.compile(r"\bcurrent state,\s*available action,\s*and evidence\b", re.IGNORECASE)),
    ("generated greenfield copy", re.compile(r"\bgenerated\s+from\s+the\s+(?:accepted\s+)?greenfield\s+(?:project|proposal)\b", re.IGNORECASE)),
    ("proposal record provenance", re.compile(r"\b(?:actors and owners|jobs)\s+come\s+from\s+(?:the\s+)?proposal\b", re.IGNORECASE)),
    ("generic first workflow", re.compile(r"(?<![-\w])(?:accepted\s+)?first\s+workflow\b", re.IGNORECASE)),
    ("workflow lead scaffold", re.compile(r"\bworkflow\s+lead(?:\s+and\s+beneficiary)?\b", re.IGNORECASE)),
    ("one accountable workflow", re.compile(r"\bone\s+accountable\s+workflow\b", re.IGNORECASE)),
    ("generated records", re.compile(r"\bgenerated\s+(?:records|workstreams)\b", re.IGNORECASE)),
    ("visible completion scaffold", re.compile(r"\bintake\s+to\s+visible\s+completion\b|\bvisible\s+completion\b", re.IGNORECASE)),
)

_SCAFFOLD_MARKERS: tuple[str, ...] = (
    "odylith_apply_ready_scaffold",
    "apply_ready_scaffold",
    "proposal_template",
    "canonical_proposal",
    "GreenfieldDomainProfile",
)

_EXCLUDED_PUBLIC_KEYS = {
    "accepted_aliases",
    "apply_commands",
    "artifact_plan_patch_ledger",
    "classification",
    "component_id",
    "evidence_tier",
    "host_instruction",
    "host_independent_paths",
    "id",
    "intended_path",
    "kind",
    "link_state",
    "mode",
    "observed_source",
    "priority",
    "product_intent_authority",
    "provider_calls",
    "artifact_derivation",
    "atlas_scaffold_logs",
    "project_intelligence_binding",
    "qualification",
    "reasoning_contract",
    "reasoning_mode",
    "schema_version",
    "semantic_model",
    "sizing",
    "slug",
    "source_html",
    "source_mmd",
    "source_png",
    "source_svg",
    "source_title",
    "status",
    "next_steps",
    "commit_manifest",
    "validation_gate",
    "validation_plan",
    "watch_paths",
    "write_policy",
}

_EXCLUDED_KEY_SUFFIXES = (
    "_id",
    "_ids",
    "_path",
    "_paths",
    "_ref",
    "_refs",
    "_slug",
    "_slugs",
)

_TERM_STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "application",
    "build",
    "create",
    "design",
    "draft",
    "for",
    "from",
    "govern",
    "governed",
    "greenfield",
    "help",
    "in",
    "into",
    "make",
    "me",
    "new",
    "of",
    "on",
    "platform",
    "product",
    "project",
    "proposal",
    "repo",
    "should",
    "system",
    "the",
    "to",
    "tool",
    "using",
    "with",
}

_SHORT_DOMAIN_TERMS = {"ai", "ml", "ui", "ux", "ar", "vr", "kyb", "aml", "smb", "crm", "erp"}
_CONTROL_CONTEXT_STOPWORDS = frozenset(
    {
        *_TERM_STOPWORDS,
        "atlas",
        "casebook",
        "compass",
        "component",
        "diagram",
        "governance",
        "mermaid",
        "radar",
        "registry",
        "surface",
        "tribunal",
        "workstream",
        "workspace",
    }
)
_SOURCE_GROUNDED_CONTROL_LABELS = frozenset({"radar", "registry", "atlas", "compass", "tribunal"})


def greenfield_quality_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Return greenfield product-quality failures that should block writes."""

    issues: list[str] = []
    public_leaves = list(_public_text_leaves(proposal))
    prompt_terms = _prompt_terms(proposal)
    issues.extend(_control_plane_leak_issues(public_leaves, grounded_contexts=_source_grounded_control_contexts(proposal)))
    issues.extend(_stale_generic_issues(public_leaves))
    issues.extend(_generic_actor_label_issues(public_leaves))
    issues.extend(_directive_leak_issues(public_leaves))
    issues.extend(_scaffold_marker_issues(public_leaves))
    issues.extend(_mechanical_artifact_issues(public_leaves))
    issues.extend(_qualitative_structure_issues(proposal))
    issues.extend(_semantic_model_issues(proposal))
    issues.extend(_release_workstream_reference_issues(proposal))
    issues.extend(_governance_prep_language_issues(proposal))
    issues.extend(f"semantic slop: {issue}" for issue in generated_semantic_slop_issues(proposal, root="proposal"))
    issues.extend(public_prose_quality_issues(proposal))
    if prompt_terms:
        issues.extend(_prompt_echo_issues(proposal, public_leaves=public_leaves))
    return _dedupe(issues)


def _semantic_model_issues(proposal: Mapping[str, Any]) -> list[str]:
    if not _is_confirmed_generated_proposal(proposal):
        return []
    issues: list[str] = []
    model = proposal.get("semantic_model")
    if not isinstance(model, Mapping):
        return ["confirmed greenfield proposal is missing semantic_model"]
    contract = model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        issues.append("semantic_model is missing first_path_contract")
    else:
        capability = clean_text(contract.get("capability"))
        raw_path = clean_text(contract.get("raw_path"))
        events = [row for row in contract.get("events", []) if isinstance(row, Mapping)] if isinstance(contract.get("events"), list) else []
        if not capability or re.search(r"\b(?:first\s+path\s+entry|first\s+accepted\s+action)\b", capability, re.IGNORECASE):
            issues.append("semantic_model first_path_contract has a mechanical or missing capability phrase")
        if raw_path and _path_needs_events(raw_path) and len(events) < 2:
            issues.append("semantic_model first_path_contract collapses a multi-step first path")
        if events and not any(row.get("visible_result") for row in events):
            issues.append("semantic_model first_path_contract has no visible-result event")
        if any(contains_requirement_control_clause(clean_text(row.get("text") or row.get("mutation"))) for row in events):
            issues.append("semantic_model first_path_contract includes release/proof constraints as path events")
    component_refs = model.get("components")
    if not isinstance(component_refs, list) or not component_refs:
        issues.append("semantic_model is missing component contract references")
    else:
        by_id = {
            clean_text(row.get("component_id"))
            for row in component_refs
            if isinstance(row, Mapping) and clean_text(row.get("component_id"))
        }
        active_ids = {
            clean_text(row.get("component_id"))
            for row in proposal.get("components", [])
            if isinstance(row, Mapping)
            and clean_text(row.get("component_id"))
            and clean_text(row.get("release_scope")) not in {"deferred", "out_of_scope", "external"}
        }
        missing = sorted(active_ids - by_id)
        if missing:
            issues.append("semantic_model omits active component references: " + ", ".join(missing[:4]))
        for row in component_refs:
            if not isinstance(row, Mapping):
                continue
            label = clean_text(row.get("label")) or clean_text(row.get("component_id")) or "component"
            if clean_text(row.get("release_scope")) != "out_of_scope" and not clean_text(row.get("semantic_axis")):
                contract_terms = set(
                    _meaningful_terms(
                        " ".join(
                            [
                                clean_text(row.get("owned_state")),
                                clean_text(row.get("accepted_inputs")),
                                clean_text(row.get("produced_outputs")),
                            ]
                        )
                    )
                )
                if len(contract_terms) < 8:
                    issues.append(f"semantic_model component `{label}` has no semantic axis or specific contract nouns")
    graph = model.get("diagram_event_graph")
    if not isinstance(graph, Mapping):
        issues.append("semantic_model is missing diagram_event_graph")
    else:
        checkpoint = clean_text(graph.get("proof_checkpoint"))
        if re.search(r"\b(?:done,\s*path,\s*mean)\b", checkpoint, re.IGNORECASE):
            issues.append("semantic_model proof checkpoint contains token soup")
    obligations = model.get("proof_obligations")
    if not isinstance(obligations, list) or len(obligations) < 2:
        issues.append("semantic_model must include first-path and release-boundary proof obligations")
    return issues


def _path_needs_events(value: str) -> bool:
    return progression_marker_count(value, connectors=("and", "then", "later"), punctuation=".;") >= 2


def _is_confirmed_generated_proposal(proposal: Mapping[str, Any]) -> bool:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return str(intent.get("reasoning_mode", "")).strip() == "odylith_confirmed_governed_proposal"


def _control_plane_leak_issues(
    public_leaves: list[tuple[str, str]],
    *,
    grounded_contexts: Mapping[str, tuple[frozenset[str], ...]],
) -> list[str]:
    issues: list[str] = []
    for label, pattern in _CONTROL_PLANE_LEAKS:
        label_key = label.casefold()
        contexts = grounded_contexts.get(label_key, ())
        paths = [
            path
            for path, text in public_leaves
            if pattern.search(text) and not _control_label_is_source_grounded(text, label=label_key, contexts=contexts)
        ]
        if paths:
            issues.append(
                f"greenfield public product content leaks Odylith control-plane term `{label}` at {_path_preview(paths)}"
            )
    return issues


def _source_grounded_control_contexts(proposal: Mapping[str, Any]) -> dict[str, tuple[frozenset[str], ...]]:
    source_keys = (
        ("source_title", *_INTENT_DOMAIN_TERM_KEYS)
        if _is_confirmed_generated_proposal(proposal)
        else ("prompt", "source_title", "title", "first_path")
    )
    contexts: dict[str, list[frozenset[str]]] = {}
    intent = proposal.get("intent")
    if not isinstance(intent, Mapping):
        return {}
    for key in source_keys:
        for text in text_values(intent.get(key)):
            if not text:
                continue
            for label in _SOURCE_GROUNDED_CONTROL_LABELS:
                for context in _control_label_contexts(text, label=label):
                    if context:
                        contexts.setdefault(label, []).append(context)
    return {label: tuple(dict.fromkeys(rows)) for label, rows in contexts.items()}


def _control_label_is_source_grounded(text: str, *, label: str, contexts: tuple[frozenset[str], ...]) -> bool:
    if _control_label_has_hard_platform_context(text, label=label):
        return False
    if not contexts:
        return False
    observed = tuple(context for context in _control_label_contexts(text, label=label) if context)
    if not observed:
        return False
    for context in observed:
        if not any(_context_overlap_sufficient(context, accepted) for accepted in contexts):
            return False
    return True


def _context_overlap_sufficient(observed: frozenset[str], accepted: frozenset[str]) -> bool:
    return bool(observed & accepted)


def _control_label_contexts(text: str, *, label: str) -> tuple[frozenset[str], ...]:
    tokens = [str(term).casefold() for term in label_terms(text)]
    contexts: list[frozenset[str]] = []
    for index, token in enumerate(tokens):
        if token != label:
            continue
        window = tokens[max(0, index - 3) : index] + tokens[index + 1 : index + 4]
        context = frozenset(
            item
            for item in window
            if item and item not in _CONTROL_CONTEXT_STOPWORDS and len(item) >= 3
        )
        contexts.append(context)
    return tuple(contexts)


def _control_label_has_hard_platform_context(text: str, *, label: str) -> bool:
    literal = re.escape(label)
    hard_patterns = (
        rf"\bOdylith\s+{literal}\b",
        rf"\b{literal}\s+(?:Mermaid|surface|surfaces|catalog|dashboard|viewer|render(?:ed|er)?|assets?|source)\b",
        rf"\b{literal}\s+diagram\b(?=[^.\n]*(?:generated|governance|control[-\s]+plane|Odylith|surface|Mermaid))",
        rf"\b(?:generated|governance|control[-\s]+plane|Odylith|surface|Mermaid)[^.\n]{{0,80}}\b{literal}\s+diagram\b",
        rf"\b{literal}\b[^.\n]{{0,80}}\b(?:governance\s+(?:flow|record|records|surface|surfaces)|control[-\s]+plane)\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in hard_patterns)


def _stale_generic_issues(public_leaves: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for term in _STALE_GENERIC_TERMS:
        paths = [path for path, text in public_leaves if _contains_stale_generic_label(text, term)]
        if paths:
            issues.append(f"greenfield public product content reuses stale generic label `{term}` at {_path_preview(paths)}")
    return issues


def _contains_stale_generic_label(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9-]){re.escape(term)}(?![A-Za-z0-9-])", text))


def _generic_actor_label_issues(public_leaves: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for label in _GENERIC_ACTOR_LABELS:
        paths = [
            path
            for path, text in public_leaves
            if not _is_option_metadata_path(path) and _starts_with_generic_actor_label(text, label)
        ]
        if paths:
            issues.append(
                f"greenfield public product content uses generic actor label `{label}` instead of a project-specific actor at {_path_preview(paths)}"
            )
    return issues


def _starts_with_generic_actor_label(text: str, label: str) -> bool:
    """Reject placeholder actor rows without rejecting domain-specific owners."""

    cleaned = clean_text(text)
    label_text = str(label or "").strip()
    if not label_text or not cleaned.casefold().startswith(label_text.casefold()):
        return False
    after_label = cleaned[len(label_text) :]
    if not after_label:
        return True
    separator = after_label[0]
    if separator not in {" ", ":", "-", "–", "—"}:
        return False
    if separator != " ":
        return True
    tail = after_label[1:].strip()
    if not tail:
        return True
    words = [part.strip(".,;:()[]{}").casefold() for part in tail.split() if part.strip(".,;:()[]{}")]
    if not words:
        return True
    first = words[0]
    second = words[1] if len(words) > 1 else ""
    if first in {"can", "cannot", "could", "is", "must", "needs", "need", "should", "will", "would"}:
        return True
    if first.endswith("ing"):
        return True
    if first.endswith("s") and second not in {"is", "are", "was", "were"}:
        return True
    return False


def _directive_leak_issues(public_leaves: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for label, pattern in _DIRECTIVE_LEAKS:
        paths = [path for path, text in public_leaves if path != "intent.prompt" and pattern.search(text)]
        if paths:
            issues.append(
                f"greenfield public product content leaks operator instruction `{label}` into product records at {_path_preview(paths)}"
            )
    return issues


def _scaffold_marker_issues(public_leaves: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for marker in _SCAFFOLD_MARKERS:
        paths = [path for path, text in public_leaves if marker in text]
        if paths:
            issues.append(f"greenfield public product content exposes scaffold marker `{marker}` at {_path_preview(paths)}")
    return issues


def _mechanical_artifact_issues(public_leaves: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for label, pattern in _MECHANICAL_ARTIFACT_PHRASES:
        paths = [path for path, text in public_leaves if pattern.search(text)]
        if paths:
            issues.append(
                f"greenfield public product content uses mechanical scaffold language `{label}` instead of domain explanation at {_path_preview(paths)}"
            )
    return issues


def _qualitative_structure_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Reject product records that have labels but no operational meaning."""

    issues: list[str] = []
    project_brief = proposal.get("project_brief")
    if isinstance(project_brief, Mapping):
        purpose = _field_text(project_brief, "purpose", "summary", "operator_value", "project_outcome")
        if purpose and not _has_user_capability(purpose):
            issues.append("proposal `project_brief` does not explain a user capability in product terms")
        if purpose and not _has_problem_tension(purpose):
            issues.append("proposal `project_brief` does not explain the problem, risk, or operational tension")
        principle = _field_text(project_brief, "operating_principle", "project_outcome")
        if principle and not _has_evidence_relationship(principle):
            issues.append("proposal `project_brief` does not explain what evidence makes the release trustable")

    backlog = proposal.get("backlog")
    if isinstance(backlog, list):
        for index, row in enumerate(backlog, start=1):
            if not isinstance(row, Mapping):
                continue
            title = clean_text(row.get("title")) or f"row {index}"
            problem = _field_text(row, "problem")
            if problem and not _has_problem_tension(problem):
                issues.append(f"backlog row {index} `{title}` does not state the user problem, risk, or failure mode")
            value_text = _field_text(
                row,
                "customer",
                "opportunity",
                "product_view",
                "recommended_first_slice",
                "success_metrics",
                "validation",
            )
            if value_text and not _has_user_capability(value_text):
                issues.append(f"backlog row {index} `{title}` does not describe a user capability or decision")
            if value_text and not _has_ownership_boundary(value_text):
                issues.append(f"backlog row {index} `{title}` does not explain ownership or state responsibility")
            if value_text and not _has_evidence_relationship(value_text):
                issues.append(f"backlog row {index} `{title}` does not explain evidence, review, or validation")

    components = proposal.get("components")
    if isinstance(components, list):
        for index, row in enumerate(components, start=1):
            if not isinstance(row, Mapping):
                continue
            label = clean_text(row.get("label") or row.get("component_id")) or f"component {index}"
            component_text = _field_text(row, "responsibility", "boundary", "dependencies", "interfaces", "validation")
            if component_text and not _has_ownership_boundary(component_text):
                issues.append(f"component row {index} `{label}` does not explain what it owns, receives, or produces")
            if component_text and not _has_evidence_relationship(component_text):
                issues.append(f"component row {index} `{label}` does not explain proof, review, validation, or source evidence")

    diagrams = proposal.get("diagrams")
    if isinstance(diagrams, list):
        for index, row in enumerate(diagrams, start=1):
            if not isinstance(row, Mapping):
                continue
            title = clean_text(row.get("title") or row.get("slug")) or f"diagram {index}"
            diagram_text = _field_text(row, "summary", "purpose", "operator_question", "proof_gate")
            if diagram_text and not (_has_user_capability(diagram_text) or _has_evidence_relationship(diagram_text)):
                issues.append(f"diagram row {index} `{title}` does not explain the product meaning of the view")
            for component_index, component in enumerate(row.get("components") if isinstance(row.get("components"), list) else [], start=1):
                if not isinstance(component, Mapping):
                    continue
                description = clean_text(component.get("description") or component.get("role"))
                if description and not _has_ownership_boundary(description):
                    issues.append(
                        f"diagram row {index} `{title}` component {component_index} does not explain domain responsibility"
                    )
    return issues


def _field_text(row: Mapping[str, Any], *keys: str) -> str:
    return " ".join(str(nested or "") for key in keys for nested in text_values(row.get(key))).strip()


def _has_user_capability(text: str) -> bool:
    lowered = clean_text(text).casefold()
    return bool(
        re.search(
            r"\b(?:can|uses?|needs?|sees?|views?|reviews?|inspects?|understands?|decides?|submits?|records?|tracks?|approves?|blocks?|rejects?|verifies?|produces?|captures?|imports?|links?|derives?|assembles?|makes?|keeps?|completes?)\b",
            lowered,
        )
    )


def _has_problem_tension(text: str) -> bool:
    lowered = clean_text(text).casefold()
    return bool(
        re.search(
            r"\b(?:without|risk|harm|danger|fails?|failure|cannot|missing|unclear|unowned|blocked|drift|stale|unsupported|untrusted|needs?|must|if|when|unless|because|otherwise|prevents?|reduces?|no)\b",
            lowered,
        )
    )


def _has_ownership_boundary(text: str) -> bool:
    lowered = clean_text(text).casefold()
    return bool(
        re.search(
            r"\b(?:owns?|owned|responsible|authority|boundary|state|record|version|source of truth|receives?|produces?|records?|stores?|tracks?|links?|assembles?|derives?|controls?|protects?|coordinates?)\b",
            lowered,
        )
    )


def _has_evidence_relationship(text: str) -> bool:
    lowered = clean_text(text).casefold()
    return bool(
        re.search(
            r"\b(?:evidence|proof|trace|traces|source|audit|validate|validation|review|reviewer|inspect|replay|verified?|citation|history|decision|outcome|checks?|gate|readiness|failure|recovery)\b",
            lowered,
        )
    )


def _governance_prep_language_issues(proposal: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    backlog = proposal.get("backlog")
    if not isinstance(backlog, list):
        return issues
    checked_fields = ("title", "problem", "customer", "opportunity", "product_view", "recommended_first_slice")
    for index, row in enumerate(backlog, start=1):
        if not isinstance(row, Mapping):
            continue
        text = " ".join(clean_text(row.get(field)) for field in checked_fields)
        for label, pattern in _GOVERNANCE_PREP_PHRASES:
            if pattern.search(text):
                issues.append(
                    f"backlog row {index} uses governance-prep phrase `{label}` where product/business language is required"
                )
    return issues


def _release_workstream_reference_issues(proposal: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    backlog = proposal.get("backlog")
    release_plan = proposal.get("release_plan")
    if not isinstance(backlog, list) or not isinstance(release_plan, Mapping):
        return issues
    titles = [
        clean_text(row.get("title"))
        for row in backlog
        if isinstance(row, Mapping) and clean_text(row.get("title"))
    ]
    title_lookup = {title.casefold() for title in titles}
    for label, ref in _release_title_refs(release_plan):
        if ref.casefold() not in title_lookup:
            issues.append(
                f"release plan {label} references workstream title `{ref}` that is not a generated backlog row"
            )
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    if str(intent.get("reasoning_mode", "")).strip() == "odylith_confirmed_governed_proposal":
        child_titles = titles[1:]
        target_titles = [
            ref
            for label, ref in _release_title_refs(release_plan)
            if label == "target_workstream_titles"
        ]
        missing = [title for title in child_titles if title.casefold() not in {ref.casefold() for ref in target_titles}]
        if target_titles and missing:
            issues.append(
                "release plan target_workstream_titles omits generated first-release workstreams: "
                + ", ".join(missing[:3])
            )
    return issues


def _release_title_refs(release_plan: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = [
        ("target_workstream_titles", ref)
        for ref in text_values(release_plan.get("target_workstream_titles"))
        if clean_text(ref)
    ]
    stages = release_plan.get("release_stages")
    if isinstance(stages, list):
        for index, stage in enumerate(stages, start=1):
            if not isinstance(stage, Mapping):
                continue
            rows.extend(
                (f"release_stages[{index}].workstream_titles", ref)
                for ref in text_values(stage.get("workstream_titles"))
                if clean_text(ref)
            )
    return rows


def _prompt_echo_issues(
    proposal: Mapping[str, Any],
    *,
    public_leaves: list[tuple[str, str]],
) -> list[str]:
    intent = proposal.get("intent")
    if not isinstance(intent, Mapping):
        return []
    raw_prompt = clean_text(intent.get("prompt"))
    raw_title = clean_text(intent.get("title"))
    issues: list[str] = []
    for label, value, max_hits, minimum_length in (
        ("prompt", raw_prompt, 0, 32),
        ("title", raw_title, 0, 24),
    ):
        needle = value.casefold()
        if len(needle) < minimum_length or (label == "title" and len(value.split()) < 4):
            continue
        paths = [
            path
            for path, text in public_leaves
            if needle
            and _raw_echo_matches(label=label, needle=needle, text=text)
            and not path.startswith("intent.")
            and _is_artifact_content_path(path)
            and (label != "title" or _is_project_brief_prose_path(path))
        ]
        if len(paths) > max_hits:
            issues.append(
                f"greenfield public product content repeats the raw {label} instead of authoring natural project language at {_path_preview(paths)}"
            )
    return issues


def _raw_echo_matches(*, label: str, needle: str, text: str) -> bool:
    lowered = text.casefold()
    if label != "title":
        return needle in lowered
    if lowered.strip() == needle:
        return True
    return lowered.startswith(needle) and len(text.split()) <= 14


def _is_artifact_content_path(path: str) -> bool:
    return path.startswith(("backlog.", "components.", "diagrams.", "release_plan.", "project_brief."))


def _is_project_brief_prose_path(path: str) -> bool:
    return path in {
        "project_brief.purpose",
        "project_brief.project_outcome",
        "project_brief.operating_principle",
    }


def _is_option_metadata_path(path: str) -> bool:
    return ".customization_options." in f".{path}."


def _public_text_leaves(value: Any, *, path: tuple[str, ...] = ()) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        rows: list[tuple[str, str]] = []
        for key, nested in value.items():
            key_text = str(key)
            if _is_excluded_public_key(key_text):
                continue
            rows.extend(_public_text_leaves(nested, path=(*path, key_text)))
        return tuple(rows)
    if isinstance(value, (list, tuple, set)):
        rows = []
        for index, nested in enumerate(value):
            rows.extend(_public_text_leaves(nested, path=(*path, str(index))))
        return tuple(rows)
    text = clean_text(value)
    return ((".".join(path) or "<root>", text),) if text else ()


def _is_excluded_public_key(key: str) -> bool:
    lowered = key.casefold()
    if lowered == "mermaid_source":
        return False
    return lowered in _EXCLUDED_PUBLIC_KEYS or lowered.endswith(_EXCLUDED_KEY_SUFFIXES)


def _prompt_terms(proposal: Mapping[str, Any]) -> tuple[str, ...]:
    intent = proposal.get("intent")
    values: list[str] = []
    if isinstance(intent, Mapping):
        for key in _INTENT_DOMAIN_TERM_KEYS:
            values.extend(text_values(intent.get(key)))
    return _meaningful_terms(" ".join(values))


def _meaningful_terms(text: str) -> tuple[str, ...]:
    return tuple(
        ordered_terms(
            text,
            stopwords=_TERM_STOPWORDS,
            minimum=3,
            preserve_terms=_SHORT_DOMAIN_TERMS,
        )
    )


def _path_preview(paths: list[str]) -> str:
    preview = ", ".join(paths[:3])
    if len(paths) > 3:
        preview = f"{preview}, +{len(paths) - 3} more"
    return preview


def _dedupe(issues: list[str]) -> list[str]:
    return dedupe_strings(clean_text(issue) for issue in issues)


__all__ = ["greenfield_quality_issues"]
