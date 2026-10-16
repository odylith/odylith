"""Lightweight prompt classifiers for host-hook fast paths.

This module intentionally avoids importing the intervention renderer stack.
Prompt-submit hooks use it before deciding whether a turn earns the heavier
conversation bundle, so it must stay cheap and deterministic.
"""

from __future__ import annotations

import re
from typing import Any
from typing import Sequence

WORKSTREAM_RE = re.compile(r"\bB-\d{3,}\b")
BUG_RE = re.compile(r"\bCB-\d{3,}\b")
DIAGRAM_RE = re.compile(r"\bD-\d{3,}\b")
ANCHOR_RE = re.compile(r"\b(?:B|CB|D)-\d{3,}\b")
GOVERNANCE_HINTS: tuple[str, ...] = (
    "governance",
    "workstream",
    "radar",
    "registry",
    "atlas",
    "casebook",
    "proposal",
    "capture",
    "record",
)
TOPOLOGY_HINTS: tuple[str, ...] = (
    "topology",
    "diagram",
    "atlas",
    "architecture",
    "ownership",
    "boundary",
    "authority",
    "relationship",
)
INVARIANT_HINTS: tuple[str, ...] = ("invariant", "must", "never", "always", "guardrail", "non-negotiable")
BUG_HINTS: tuple[str, ...] = ("bug", "failure", "regression", "incident", "broken", "crash")
EXECUTION_HINTS: tuple[str, ...] = ("implement", "wire", "build", "fix", "ship", "harden", "design")
GREENFIELD_ACTION_HINTS: tuple[str, ...] = (
    "build",
    "create",
    "design",
    "draft",
    "govern",
    "make",
    "plan",
    "propose",
)
GREENFIELD_SCOPE_HINTS: tuple[str, ...] = (
    "app",
    "application",
    "architecture",
    "audit",
    "compliance",
    "cli",
    "data",
    "device",
    "diagram",
    "ecommerce",
    "education",
    "game",
    "library",
    "math",
    "mobile",
    "platform",
    "project",
    "registry",
    "research",
    "science",
    "security",
    "service",
    "site",
    "system",
    "topology",
    "website",
    "workflow",
)
PLACEHOLDER_FAILURE_EVIDENCE_MARKERS: tuple[str, ...] = (
    "<paste failing command and error>",
    "<paste failing command",
    "paste failing command and error",
    "paste failing command",
)
STRONG_INVARIANT_RE = re.compile(
    r"\b("
    r"hard rule|"
    r"non-negotiable|"
    r"must never|"
    r"must not|"
    r"never allow|"
    r"never remove|"
    r"do not remove|"
    r"don't remove|"
    r"do not ever|"
    r"always require"
    r")\b",
    re.IGNORECASE,
)
GOVERNED_CAPTURE_VERB_RE = re.compile(
    r"\b("
    r"capture|"
    r"create|"
    r"define|"
    r"map|"
    r"open|"
    r"register|"
    r"scaffold|"
    r"track|"
    r"write"
    r")\b",
    re.IGNORECASE,
)
HELP_PROMPT_TOKENS: frozenset[str] = frozenset(
    {
        "help odylith",
        "odylith help",
        "odylith please help",
        "please odylith help",
    }
)
ODYLITH_SHOW_PROMPT_PHRASES: tuple[str, ...] = (
    "show me what you got",
    "show me what you can do",
    "what can you do",
    "what can odylith do",
    "show odylith",
)
REPO_SHOW_PROMPT_PHRASES: tuple[str, ...] = (
    "what can you do for this repo",
    "what can you do in this repo",
    "show me what you can do for this repo",
    "show me what you can do in this repo",
)
SHOW_PROMPT_TOKENS: frozenset[str] = frozenset(
    {
        "odylith show me what you got",
        "odylith show me what you can do",
        "odylith what can you do",
    }
)
CAPABILITY_INVENTORY_MARKERS: tuple[str, ...] = (
    "capabilities and engines",
    "capability and engine",
    "capability map",
    "product architecture",
    "show capabilities",
    "odylith show capabilities",
    "odylith capabilities",
)
VISIBILITY_PRODUCT_TOKENS = {
    "ambient",
    "assist",
    "intervention",
    "interventions",
    "observation",
    "observations",
    "odylith",
    "proposal",
    "proposals",
}
VISIBILITY_DELIVERY_TOKENS = {
    "chat",
    "hook",
    "hooks",
    "output",
    "outputs",
    "see",
    "seen",
    "show",
    "showing",
    "shown",
    "surface",
    "surfaced",
    "surfacing",
    "visible",
    "visibility",
    "ux",
}
VISIBILITY_COMPLAINT_PHRASES = (
    "do not see",
    "don't see",
    "cannot see",
    "can't see",
    "not seeing",
    "not visible",
    "still do not see",
    "still don't see",
    "no ambient",
    "no intervention",
    "no interventions",
    "no assist",
    "no signal",
    "no signals",
    "zero ambient",
    "zero intervention",
    "zero interventions",
    "zero assist",
    "zero signals",
    "want to see odylith assist",
    "need to see odylith assist",
    "show odylith assist",
    "assist in every prompt",
    "assist every prompt",
    "not showing",
    "hidden hook",
    "hidden hooks",
    "unproven this session",
    "not sure",
    "unsure",
)
ASSIST_VISIBILITY_COMPLAINT_PHRASES = (
    "want to see odylith assist",
    "need to see odylith assist",
    "show odylith assist",
    "assist in every prompt",
    "assist every prompt",
)
INTERVENTION_EXPERIENCE_REQUEST_PHRASES = (
    "more frequent",
    "more often",
)
ASSIST_CADENCE_REQUEST_PHRASES = (
    *INTERVENTION_EXPERIENCE_REQUEST_PHRASES,
    "assist in every prompt",
    "assist every prompt",
)
PROOF_BOUNDARY_RE = re.compile(
    r"\b(?:proof|evidence|validat(?:e|ion)|verif(?:y|ication)|review|audit)\b",
    re.IGNORECASE,
)
STATUS_OR_QUALITY_RE = re.compile(
    r"\b(?:"
    r"status|"
    r"progress|"
    r"quality(?:\s+score)?|"
    r"scorecard|"
    r"gap(?:s)?|"
    r"risk(?:s)?|"
    r"what(?:'s| is) left|"
    r"where do we stand|"
    r"how are we doing|"
    r"how is (?:this|the) .* doing"
    r")\b",
    re.IGNORECASE,
)
ASSIST_CADENCE_SIGNAL_RE = re.compile(
    r"\b(?:"
    r"decision|tradeoff|assumption|next\s+(?:step|move|task|slice)|priority|blocker|constraint|"
    r"continue|continuing|proceed|carry\s+on|go\s+ahead|keep\s+(?:going|working)|move\s+forward|"
    r"status|progress|quality|score|gap(?:s)?|risk(?:s)?|proof|validat(?:e|ion)|review"
    r")\b",
    re.IGNORECASE,
)
ASSIST_CONTINUATION_RE = re.compile(
    r"\b(?:continue|continuing|proceed|carry\s+on|go\s+ahead|keep\s+(?:going|working)|move\s+forward)\b",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[a-z0-9']+")


def normalize_string(value: Any) -> str:
    """Collapse internal whitespace and trim a scalar value without renderer imports."""

    return " ".join(str(value or "").split()).strip()


def normalize_token(value: Any) -> str:
    """Normalize free-form text into a lowercase underscore token."""

    return re.sub(r"[^a-z0-9]+", "_", normalize_string(value).casefold()).strip("_")


def explicit_ids(text: str, pattern: re.Pattern[str]) -> list[str]:
    """Return deduplicated explicit ids that appear in the raw prompt text."""

    seen: set[str] = set()
    rows: list[str] = []
    for token in pattern.findall(normalize_string(text)):
        value = normalize_string(token).upper()
        if not value or value in seen:
            continue
        seen.add(value)
        rows.append(value)
    return rows


def prompt_refs(value: Any) -> list[str]:
    """Return deduplicated workstream, bug, and diagram anchors in prompt order."""

    return list(dict.fromkeys(ANCHOR_RE.findall(str(value or ""))))


def prompt_anchor(value: Any) -> str:
    """Return the first explicit governance anchor in the prompt."""

    refs = prompt_refs(value)
    return refs[0] if refs else ""


def contains_any(text: str, hints: Sequence[str]) -> bool:
    """Return whether any hint token appears in the normalized text."""

    haystack = normalize_token(text)
    return any(normalize_token(hint) in haystack for hint in hints)


def normalized_passthrough_prompt(value: Any) -> str:
    """Return a compact prompt token for exact first-match passthrough routes."""

    text = normalize_string(value).casefold()
    if not text:
        return ""
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def passthrough_prompt_kind(value: Any) -> str:
    """Return the first-match passthrough route kind for prompt-only CLI lanes."""

    token = normalized_passthrough_prompt(value)
    if token in HELP_PROMPT_TOKENS:
        return "help"
    if "odylith" in token and any(marker in token for marker in CAPABILITY_INVENTORY_MARKERS):
        return "capabilities"
    if token in SHOW_PROMPT_TOKENS:
        return "show"
    if "odylith" in token and any(phrase in token for phrase in ODYLITH_SHOW_PROMPT_PHRASES):
        return "show"
    if any(phrase in token for phrase in REPO_SHOW_PROMPT_PHRASES):
        return "show"
    return ""


def is_passthrough_prompt(value: Any) -> bool:
    """Return whether a prompt should print CLI/demo stdout without narration."""

    return bool(passthrough_prompt_kind(value))


def is_cli_help_output(value: Any) -> bool:
    """Return whether text is raw Odylith CLI help output, not conversation signal."""

    text = normalize_string(value).casefold()
    if not text:
        return False
    return (
        "usage: odylith" in text
        and "-h, --help" in text
        and ("options:" in text or "optional arguments:" in text)
        and "show this help message" in text
    )


def is_greenfield_governance_prompt(value: Any) -> bool:
    """Return whether a prompt should route to proposal-first greenfield planning."""

    text = normalize_string(value)
    if not text or is_passthrough_prompt(text):
        return False
    token = normalized_passthrough_prompt(text)
    if not token:
        return False
    has_action = any(f" {hint} " in f" {token} " for hint in GREENFIELD_ACTION_HINTS)
    has_scope = any(f" {hint} " in f" {token} " for hint in GREENFIELD_SCOPE_HINTS)
    explicit_governance_set = {"backlog", "registry", "atlas", "component", "components", "diagram", "diagrams"}
    governance_hits = {word for word in token.split() if word in explicit_governance_set}
    return bool((has_action and has_scope) or ("odylith" in token and len(governance_hits) >= 2))


def has_prompt_intervention_signal(value: Any) -> bool:
    """Return whether a prompt is worth the prompt-submit intervention hot path."""

    text = normalize_string(value)
    if not text or is_passthrough_prompt(text):
        return False
    if is_greenfield_governance_prompt(text):
        return False
    if intervention_experience_feedback_requested(prompt=text):
        return True
    if explicit_ids(text, WORKSTREAM_RE) or explicit_ids(text, BUG_RE) or explicit_ids(text, DIAGRAM_RE):
        return True
    lowered = text.casefold()
    if any(marker in lowered for marker in PLACEHOLDER_FAILURE_EVIDENCE_MARKERS):
        return True
    if STRONG_INVARIANT_RE.search(text):
        return True
    if STATUS_OR_QUALITY_RE.search(text):
        return True
    if not (
        contains_any(text, GOVERNANCE_HINTS)
        or contains_any(text, TOPOLOGY_HINTS)
        or contains_any(text, BUG_HINTS)
    ):
        return False
    return bool(
        contains_any(text, EXECUTION_HINTS)
        or GOVERNED_CAPTURE_VERB_RE.search(text)
        or contains_any(text, INVARIANT_HINTS)
    )


def has_assist_cadence_signal(value: Any) -> bool:
    """Return whether a cadence preference can usefully surface an extra Assist."""

    text = normalize_string(value)
    if not text or is_passthrough_prompt(text) or is_greenfield_governance_prompt(text):
        return False
    return bool(ASSIST_CADENCE_SIGNAL_RE.search(text))


def prompt_assist_summary(value: Any) -> str:
    """Return one concrete user-facing Assist sentence for an earned prompt signal."""

    text = normalize_string(value)
    if _assist_cadence_feedback_requested(text):
        return "I will surface meaningful decisions, risks, proof points, and verified results; routine chatter stays out of the way."
    if _visibility_feedback_requested_text(text):
        return "I will make the next decision, risk, or verified result visible in the conversation."
    anchor = prompt_anchor(text)
    if anchor.startswith("CB-"):
        return "I will separate the symptom, accountable owner, and proof of recovery before it is called resolved."
    if anchor:
        return f"{anchor} stays tied to a visible proof checkpoint; I will surface the evidence that changes its status."
    if STRONG_INVARIANT_RE.search(text):
        return "I will treat the stated constraint as a release gate, not a detail to repair later."
    if PROOF_BOUNDARY_RE.search(text):
        return "I will keep the next decision tied to a visible proof checkpoint before it becomes a completion claim."
    if STATUS_OR_QUALITY_RE.search(text):
        return "I will separate verified progress, open risk, and the next gate so this status guides the next move."
    if ASSIST_CONTINUATION_RE.search(text):
        return "I will continue from the last verified checkpoint and call out the next completed change, remaining risk, and gate."
    return "I will surface the next assumption, risk, or verified result that changes the outcome."


def meaningful_tokens(value: Any) -> set[str]:
    """Return lowercase word tokens for the visibility-complaint detector."""

    return {token.strip("'") for token in _WORD_RE.findall(normalize_string(value).casefold()) if token.strip("'")}


def _visibility_feedback_requested_text(value: Any) -> bool:
    text = normalize_string(value)
    if not text:
        return False
    tokens = meaningful_tokens(text)
    product_hits = tokens & VISIBILITY_PRODUCT_TOKENS
    delivery_hits = tokens & VISIBILITY_DELIVERY_TOKENS
    if not product_hits or not delivery_hits:
        return False
    if "odylith" not in tokens and len(product_hits | delivery_hits) < 3:
        return False
    return any(phrase in text.casefold() for phrase in VISIBILITY_COMPLAINT_PHRASES)


def _assist_cadence_feedback_requested(value: Any) -> bool:
    text = normalize_string(value).casefold()
    if not text:
        return False
    tokens = set(_WORD_RE.findall(text))
    direct_targets = {"assist", "observation", "observations", "intervention", "interventions"}
    return bool(
        "odylith" in tokens
        and direct_targets & tokens
        and any(phrase in text for phrase in ASSIST_CADENCE_REQUEST_PHRASES)
    )


def visibility_feedback_phrase(*, prompt: Any = "", assistant_summary: Any = "") -> tuple[str, str]:
    """Detect prompt feedback about missing Odylith visibility."""

    text = normalize_string(f"{prompt or ''} {assistant_summary or ''}")
    if not text:
        return "", ""
    if not _visibility_feedback_requested_text(text):
        return "", ""
    summary = prompt_assist_summary(text)
    return summary, summary


def visibility_feedback_requested(*, prompt: Any = "", assistant_summary: Any = "") -> bool:
    """Return whether explicit visibility feedback should pay for recovery."""

    markdown_phrase, _ = visibility_feedback_phrase(
        prompt=prompt,
        assistant_summary=assistant_summary,
    )
    return bool(markdown_phrase)


def intervention_experience_feedback_requested(*, prompt: Any = "", assistant_summary: Any = "") -> bool:
    """Return whether an operator explicitly asks Odylith to improve its visible help."""

    text = normalize_string(f"{prompt or ''} {assistant_summary or ''}")
    if not text:
        return False
    if _assist_cadence_feedback_requested(text):
        return True
    if not any(phrase in text.casefold() for phrase in VISIBILITY_COMPLAINT_PHRASES):
        return False
    return visibility_feedback_requested(prompt=text)


def assist_cadence_feedback_requested(*, prompt: Any = "", assistant_summary: Any = "") -> bool:
    """Return whether the operator explicitly asks for more frequent Assist moments."""

    return _assist_cadence_feedback_requested(f"{prompt or ''} {assistant_summary or ''}")


def assist_visibility_feedback_requested(*, prompt: Any = "", assistant_summary: Any = "") -> bool:
    """Return whether feedback specifically asks for the Assist recovery line."""

    if not visibility_feedback_requested(prompt=prompt, assistant_summary=assistant_summary):
        return False
    text = normalize_string(f"{prompt or ''} {assistant_summary or ''}").casefold()
    return any(phrase in text for phrase in ASSIST_VISIBILITY_COMPLAINT_PHRASES)
