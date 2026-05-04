"""Canonical compact metadata helpers for Casebook source and projections."""

from __future__ import annotations

import re
from collections.abc import Sequence

_COMPACT_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_NON_TOKEN_RE = re.compile(r"[^A-Za-z0-9]+")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_ACRONYMS = {
    "ai": "AI",
    "api": "API",
    "cli": "CLI",
    "db": "DB",
    "html": "HTML",
    "osw": "OSW",
    "ui": "UI",
    "ux": "UX",
}

CASEBOOK_STATUS_STATES: tuple[str, ...] = (
    "Open",
    "InProgress",
    "Mitigated",
    "Monitoring",
    "Resolved",
    "FixedPendingRelease",
    "Closed",
)
CASEBOOK_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "Open": ("Open", "InProgress", "Mitigated", "Monitoring", "Resolved", "FixedPendingRelease", "Closed"),
    "InProgress": ("Open", "InProgress", "Mitigated", "Monitoring", "Resolved", "FixedPendingRelease", "Closed"),
    "Mitigated": ("Open", "InProgress", "Mitigated", "Monitoring", "Resolved", "FixedPendingRelease", "Closed"),
    "Monitoring": ("Open", "InProgress", "Mitigated", "Monitoring", "Resolved", "FixedPendingRelease", "Closed"),
    "Resolved": ("Open", "InProgress", "Monitoring", "Resolved", "FixedPendingRelease", "Closed"),
    "FixedPendingRelease": ("Open", "InProgress", "Monitoring", "Resolved", "FixedPendingRelease", "Closed"),
    "Closed": ("Open", "InProgress", "Closed"),
}
_CASEBOOK_STATUS_LOOKUP = {token.casefold(): token for token in CASEBOOK_STATUS_STATES}
_STATUS_ALIASES = {
    "active": "Open",
    "approved": "Closed",
    "archive": "Closed",
    "archived": "Closed",
    "as designed": "Closed",
    "assigned": "InProgress",
    "awaiting cab approval": "Open",
    "awaiting implementation": "Open",
    "backlog": "Open",
    "blocked": "Open",
    "build broken": "InProgress",
    "building": "InProgress",
    "cancelled": "Closed",
    "canceled": "Closed",
    "closed": "Closed",
    "committed": "InProgress",
    "completed": "Closed",
    "could not reproduce": "Closed",
    "cannot reproduce": "Closed",
    "declined": "Closed",
    "deferred": "Closed",
    "done": "Closed",
    "duplicate": "Closed",
    "escalated": "Open",
    "escalating": "Open",
    "fixed": "Resolved",
    "fixed pending deploy": "FixedPendingRelease",
    "fixed pending deployment": "FixedPendingRelease",
    "fixed pending platform deploy": "FixedPendingRelease",
    "fixed pending platform release": "FixedPendingRelease",
    "fixed pending release": "FixedPendingRelease",
    "fixed released": "Closed",
    "fixed in next release": "FixedPendingRelease",
    "fixedpendingdeploy": "FixedPendingRelease",
    "fixedpendingdeployment": "FixedPendingRelease",
    "fixedpendingplatformdeploy": "FixedPendingRelease",
    "fixedpendingplatformrelease": "FixedPendingRelease",
    "fixedpendingrelease": "FixedPendingRelease",
    "ignored": "Closed",
    "implementing": "InProgress",
    "in progress": "InProgress",
    "in review": "InProgress",
    "inprogress": "InProgress",
    "investigating": "InProgress",
    "mitigated": "Mitigated",
    "new": "Open",
    "not a bug": "Closed",
    "not planned": "Closed",
    "obsolete": "Closed",
    "ongoing": "Open",
    "open": "Open",
    "pending": "Open",
    "pending deploy": "FixedPendingRelease",
    "pending deployment": "FixedPendingRelease",
    "pending platform deploy": "FixedPendingRelease",
    "pending platform release": "FixedPendingRelease",
    "pending release": "FixedPendingRelease",
    "published": "Closed",
    "regressed": "Open",
    "rejected": "Closed",
    "released": "Closed",
    "reopened": "Open",
    "resolved": "Resolved",
    "resolved in next release": "FixedPendingRelease",
    "resolvedinnextrelease": "FixedPendingRelease",
    "selected for development": "Open",
    "shipped": "Closed",
    "started": "InProgress",
    "to do": "Open",
    "todo": "Open",
    "triage": "Open",
    "triaged": "Open",
    "unconfirmed": "Open",
    "under investigation": "InProgress",
    "under review": "InProgress",
    "unresolved": "Open",
    "verified": "Closed",
    "waiting for approval": "Open",
    "waiting for customer": "Open",
    "waiting for support": "Open",
    "watch": "Monitoring",
    "watching": "Monitoring",
    "work in progress": "InProgress",
    "work finished": "Closed",
    "wontfix": "Closed",
    "won t fix": "Closed",
    "won't fix": "Closed",
}
_TERMINAL_STATUSES = frozenset({"closed"})
CANONICAL_CASEBOOK_TYPES: tuple[str, ...] = (
    "Product",
    "App",
    "API",
    "Tooling",
    "Workflow",
    "UX",
    "OperatorUX",
    "Data",
    "DataLoss",
    "Database",
    "Security",
    "Compliance",
    "Config",
    "Infra",
    "IaC",
    "Deployment",
    "Dependency",
    "Observability",
    "Migration",
    "Install",
    "Operational",
    "Performance",
    "Release",
    "Runtime",
    "Build",
    "CI",
    "Test",
    "Documentation",
    "Integration",
    "Platform",
    "Model",
    "Evaluation",
    "Research",
)
_CANONICAL_TYPE_LOOKUP = {token.casefold(): token for token in CANONICAL_CASEBOOK_TYPES}
_TYPE_ALIASES = {
    "account lifecycle onboardi": "Install",
    "agent governance policy": "Tooling",
    "api": "API",
    "app": "App",
    "auth workflow contract": "Security",
    "build": "Build",
    "ci": "CI",
    "compliance": "Compliance",
    "config": "Config",
    "control plane deploy": "Deployment",
    "control plane deploy iam sco": "Security",
    "credential bootstrap": "Security",
    "data": "Data",
    "database": "Database",
    "dashboard rendering regression": "UX",
    "data loss": "DataLoss",
    "dataloss": "DataLoss",
    "day 2 manifest metadata path": "Deployment",
    "day 2 wave task definition co": "Deployment",
    "day2 manifest metadata path": "Deployment",
    "day2 wave task definition co": "Deployment",
    "dependency": "Dependency",
    "deployment": "Deployment",
    "diagnostics ownership": "Observability",
    "documentation": "Documentation",
    "docs": "Documentation",
    "evaluation": "Evaluation",
    "hidden cli surface drift": "Tooling",
    "hosted long wait auth and res": "Security",
    "hosted preview false negati": "Workflow",
    "hosted proof sandbox state c": "Workflow",
    "hosted proof source anchor i": "Workflow",
    "hosted proof zero credentia": "Security",
    "ia c": "IaC",
    "iac": "IaC",
    "infra": "Infra",
    "infra lifecycle protected r": "Infra",
    "install release": "Install",
    "kafka topic contract osw upg": "Runtime",
    "managed workflow source of t": "Workflow",
    "observability": "Observability",
    "observability correlation": "Observability",
    "observability diagnostics": "Observability",
    "operational": "Operational",
    "operator ux": "OperatorUX",
    "operatorux": "OperatorUX",
    "osw upgrade contract regres": "Install",
    "platform": "Platform",
    "platform runner dependency": "Dependency",
    "platform runner kafka topic": "Runtime",
    "private jobs runner manifes": "Deployment",
    "product trust": "Product",
    "product ux regression": "UX",
    "public read plane permissio": "Security",
    "research": "Research",
    "regression": "UX",
    "test": "Test",
    "test harness infra regressi": "Infra",
    "ui": "UX",
    "workflow": "Workflow",
    "ux lifecycle": "UX",
    "ux regression": "UX",
    "zero credential onboarding": "Security",
    "zero credential osw contrac": "Security",
}
_TYPE_KEYWORD_FALLBACKS = (
    ("operator ux", "OperatorUX"),
    ("data loss", "DataLoss"),
    ("dataloss", "DataLoss"),
    ("data", "Data"),
    ("database", "Database"),
    ("postgres", "Database"),
    ("sql", "Database"),
    ("zero credential", "Security"),
    ("credential", "Security"),
    ("permission", "Security"),
    ("auth", "Security"),
    ("iam", "Security"),
    ("security", "Security"),
    ("compliance", "Compliance"),
    ("observability", "Observability"),
    ("diagnostic", "Observability"),
    ("docs", "Documentation"),
    ("documentation", "Documentation"),
    ("dashboard", "UX"),
    ("rendering", "UX"),
    ("ux", "UX"),
    ("ui", "UX"),
    ("release", "Release"),
    ("deploy", "Deployment"),
    ("deployment", "Deployment"),
    ("manifest", "Deployment"),
    ("wave", "Deployment"),
    ("task definition", "Deployment"),
    ("infra", "Infra"),
    ("iac", "IaC"),
    ("config", "Config"),
    ("dependency", "Dependency"),
    ("ci", "CI"),
    ("build", "Build"),
    ("test harness", "Test"),
    ("test", "Test"),
    ("evaluation", "Evaluation"),
    ("eval", "Evaluation"),
    ("benchmark", "Evaluation"),
    ("research", "Research"),
    ("model", "Model"),
    ("llm", "Model"),
    ("api", "API"),
    ("integration", "Integration"),
    ("platform", "Platform"),
    ("workflow", "Workflow"),
    ("hosted proof", "Workflow"),
    ("hosted preview", "Workflow"),
    ("source anchor", "Workflow"),
    ("onboarding", "Install"),
    ("upgrade", "Install"),
    ("migration", "Migration"),
    ("install", "Install"),
    ("performance", "Performance"),
    ("tooling", "Tooling"),
    ("runtime", "Runtime"),
    ("product", "Product"),
    ("regression", "UX"),
)


def normalize_casebook_scalar(value: str | Sequence[str] | None) -> str:
    """Normalize scalar or list-like Casebook metadata into plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="ignore").strip()
    return "\n".join(str(item).strip() for item in value if str(item).strip()).strip()


def casebook_token_is_valid(value: str | Sequence[str] | None) -> bool:
    """Return whether the value is one compact Casebook metadata token."""
    token = normalize_casebook_scalar(value)
    return bool(token) and _COMPACT_TOKEN_RE.fullmatch(token) is not None


def compact_casebook_token(value: str | Sequence[str] | None) -> str:
    """Convert prose or separator-delimited metadata into one compact token."""
    raw = normalize_casebook_scalar(value)
    if not raw:
        return ""
    if casebook_token_is_valid(raw):
        return _preserve_known_acronym_token(raw)
    parts = [part for part in _NON_TOKEN_RE.split(raw) if part]
    return "".join(_compact_part(part) for part in parts)


def canonical_casebook_status(value: str | Sequence[str] | None) -> str:
    """Canonicalize Casebook Status to the closed Casebook lifecycle FSM."""
    raw = normalize_casebook_scalar(value)
    if not raw:
        return ""
    folded = _fold_metadata_value(raw)
    exact = _CASEBOOK_STATUS_LOOKUP.get(raw.casefold()) or _CASEBOOK_STATUS_LOOKUP.get(folded)
    if exact:
        return exact
    alias = _STATUS_ALIASES.get(folded) or _STATUS_ALIASES.get(folded.replace(" ", ""))
    if alias:
        return alias
    words = set(folded.split())
    if words & {
        "closed",
        "archived",
        "cancelled",
        "canceled",
        "completed",
        "duplicate",
        "rejected",
        "obsolete",
        "verified",
    } or words & {"released", "shipped"}:
        return "Closed"
    if (
        "pending" in words
        and words & {"deploy", "deployment", "release", "rollout", "ship"}
        and words & {"fix", "fixed", "resolved"}
    ):
        return "FixedPendingRelease"
    if words & {"investigating", "assigned", "implementing", "started", "building"}:
        return "InProgress"
    if ("progress" in words and "in" in words) or ("review" in words and words & {"in", "under", "peer"}):
        return "InProgress"
    if words & {"monitoring", "watching", "observing"}:
        return "Monitoring"
    if words & {"mitigated", "workaround"}:
        return "Mitigated"
    if words & {"fixed", "resolved"} or "fix" in words:
        return "Resolved"
    if "pending" in words and words & {"deploy", "deployment", "release", "rollout", "ship"}:
        return "FixedPendingRelease"
    if words & {"open", "active", "blocked", "triage", "triaged", "reopened", "regressed", "unresolved", "new"}:
        return "Open"
    return "Open"


def casebook_status_is_valid(value: str | Sequence[str] | None) -> bool:
    """Return whether Casebook Status is one canonical FSM state."""
    raw = normalize_casebook_scalar(value)
    return bool(raw) and canonical_casebook_status(raw) == raw and raw in CASEBOOK_STATUS_STATES


def casebook_status_transition_is_valid(
    from_value: str | Sequence[str] | None,
    to_value: str | Sequence[str] | None,
) -> bool:
    """Return whether a Casebook status transition stays inside the FSM."""
    from_status = normalize_casebook_scalar(from_value)
    to_status = normalize_casebook_scalar(to_value)
    if not casebook_status_is_valid(from_status) or not casebook_status_is_valid(to_status):
        return False
    return to_status in CASEBOOK_STATUS_TRANSITIONS.get(from_status, ())


def canonical_casebook_type(value: str | Sequence[str] | None) -> str:
    """Canonicalize Casebook Type to one controlled category token."""
    raw = normalize_casebook_scalar(value)
    if not raw:
        return ""
    folded = _fold_metadata_value(raw)
    exact = _CANONICAL_TYPE_LOOKUP.get(raw.casefold()) or _CANONICAL_TYPE_LOOKUP.get(folded)
    if exact:
        return exact
    alias = _TYPE_ALIASES.get(folded) or _TYPE_ALIASES.get(folded.replace(" ", ""))
    if alias:
        return alias
    folded_words = folded.split()
    for needle, label in _TYPE_KEYWORD_FALLBACKS:
        if _metadata_phrase_present(folded_words, needle.split()):
            return label
    return "Product"


def canonical_casebook_display_type(value: str | Sequence[str] | None) -> str:
    """Canonicalize verbose legacy Type prose into a compact display token."""
    return canonical_casebook_type(value)


def casebook_type_is_valid(value: str | Sequence[str] | None) -> bool:
    """Return whether Casebook Type is one canonical allowed category token."""
    raw = normalize_casebook_scalar(value)
    return bool(raw) and canonical_casebook_type(raw) == raw and raw in CANONICAL_CASEBOOK_TYPES


def canonical_casebook_fixed(value: str | Sequence[str] | None) -> str:
    """Canonicalize legacy Fixed prose into a short display token or date."""
    raw = normalize_casebook_scalar(value)
    if not raw:
        return ""
    if _DATE_RE.fullmatch(raw):
        return raw
    if casebook_token_is_valid(raw):
        return _preserve_known_acronym_token(raw)
    folded = _fold_metadata_value(raw)
    words = set(folded.split())
    if "pending" in words:
        return "Pending"
    if words & {"release", "released", "ship", "shipped"}:
        return "Released"
    if words & {"deploy", "deployed"}:
        return "Deployed"
    if "fixed" in words:
        return "Fixed"
    if "closed" in words:
        return "Closed"
    if "none" in words or folded in {"na", "n a"}:
        return "None"
    token = compact_casebook_token(raw)
    return token[:24] if token else ""


def casebook_status_is_terminal(value: str | Sequence[str] | None) -> bool:
    """Return whether the Casebook status is no longer an active open bug."""
    status = canonical_casebook_status(value)
    return status.casefold() in _TERMINAL_STATUSES


def _compact_part(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    acronym = _ACRONYMS.get(token.casefold())
    if acronym:
        return acronym
    if token.isupper() and len(token) <= 6:
        return token
    return token[:1].upper() + token[1:].lower()


def _fold_metadata_value(value: str) -> str:
    return " ".join(part.casefold() for part in _metadata_words(value))


def _metadata_words(value: str) -> list[str]:
    words: list[str] = []
    for token in _NON_TOKEN_RE.split(str(value or "")):
        if not token:
            continue
        words.extend(part for part in _CAMEL_BOUNDARY_RE.split(token) if part)
    return words


def _metadata_phrase_present(words: list[str], phrase: list[str]) -> bool:
    if not words or not phrase:
        return False
    phrase_len = len(phrase)
    return any(words[index : index + phrase_len] == phrase for index in range(len(words) - phrase_len + 1))


def _preserve_known_acronym_token(value: str) -> str:
    token = str(value or "").strip()
    return _ACRONYMS.get(token.casefold(), token)
