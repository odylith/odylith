#!/usr/bin/env python3
"""Fail release proof when project-domain fixture vocabulary leaks into platform code."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from greenfield_preconfirm_matrix_cases import default_cases  # noqa: E402
from greenfield_preconfirm_matrix_cases import historical_domain_leakage_sentinels  # noqa: E402


TEXT_SUFFIXES = frozenset(
    {
        ".css",
        ".html",
        ".js",
        ".json",
        ".md",
        ".mjs",
        ".py",
        ".sh",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
SOURCE_SCAN_PATHS = (
    "src/odylith",
    "bin",
    "scripts/release",
    "README.md",
    "AGENTS.md",
    "pyproject.toml",
    "docs",
    "odylith/agents-guidelines",
    "odylith/skills",
    "odylith/registry/source/components",
    ".codex",
    ".agents",
    ".claude",
)
MATRIX_FIXTURE_PATHS = frozenset(
    {
        "scripts/release/greenfield_preconfirm_matrix_cases.py",
    }
)
GOVERNANCE_EVIDENCE_PARTS = frozenset(
    {
        "casebook",
        "compass",
        "radar",
        "release-notes",
        "technical-plans",
    }
)
EVALUATION_EVIDENCE_FILES = frozenset(
    {
        "discipline-evaluation-corpus.v1.json",
        "guidance-behavior-evaluation-corpus.v1.json",
        "intervention-value-adjudication-corpus.v1.json",
        "optimization-evaluation-corpus.v1.json",
    }
)
DIST_EVIDENCE_PREFIXES = (
    "greenfield-matrix-",
    "greenfield-preconfirm-",
    "greenfield-rescue-proof-",
)
GENERIC_PRODUCT_TERMS = frozenset(
    {
        "archive",
        "artifact",
        "care",
        "certification",
        "consent",
        "court",
        "credit",
        "custody",
        "dependency",
        "deployment",
        "developer",
        "disclosure",
        "evidence",
        "flood",
        "credential",
        "guardian",
        "hearing",
        "incident",
        "interpreter",
        "lead",
        "menu",
        "open",
        "outage",
        "package",
        "placement",
        "port",
        "project",
        "product",
        "protocol",
        "provenance",
        "reliability",
        "resident",
        "review",
        "rights",
        "runbook",
        "screening",
        "security",
        "sample",
        "source",
        "union",
        "verifier",
        "waiver",
        "water",
    }
)
PLATFORM_NATIVE_TERMS = frozenset(
    {
        "agent",
        "artifact",
        "atlas",
        "casebook",
        "codex",
        "custody",
        "data",
        "flow",
        "compass",
        "governance",
        "matrix",
        "model",
        "odylith",
        "permission",
        "platform",
        "proof",
        "radar",
        "registry",
        "release",
        "tool",
        "tribunal",
        "workflow",
    }
)
DOMAIN_TEXT_STOPWORDS = frozenset(
    {
        "a",
        "across",
        "affected",
        "after",
        "all",
        "an",
        "and",
        "against",
        "action",
        "advisory",
        "ambiguities",
        "available",
        "approved",
        "assumptions",
        "automated",
        "boundary",
        "before",
        "blocks",
        "by",
        "can",
        "candidate",
        "capture",
        "claiming",
        "collect",
        "compare",
        "complete",
        "completed",
        "confirmation",
        "control",
        "coordinates",
        "coordinating",
        "counts",
        "create",
        "critical",
        "daily",
        "decision",
        "decisions",
        "delivery",
        "exception",
        "exceptions",
        "execution",
        "external",
        "event",
        "events",
        "failed",
        "final",
        "first",
        "flag",
        "for",
        "from",
        "governed",
        "greenfield",
        "helps",
        "history",
        "human",
        "in",
        "intake",
        "included",
        "intent",
        "internal",
        "is",
        "lets",
        "maintainer",
        "manage",
        "manages",
        "manager",
        "map",
        "match",
        "measurement",
        "measured",
        "multiple",
        "native",
        "no",
        "not",
        "new",
        "of",
        "only",
        "operations",
        "operator",
        "or",
        "outside",
        "owner",
        "owners",
        "plan",
        "planned",
        "planner",
        "prepare",
        "prepares",
        "preserve",
        "preserves",
        "produce",
        "proposal",
        "public",
        "publish",
        "publishes",
        "publishing",
        "question",
        "rationale",
        "readiness",
        "receives",
        "record",
        "records",
        "register",
        "report",
        "reports",
        "requests",
        "results",
        "review",
        "reviews",
        "routes",
        "run",
        "session",
        "show",
        "shows",
        "signoff",
        "simulation",
        "simulations",
        "staff",
        "state",
        "story",
        "system",
        "systems",
        "that",
        "the",
        "title",
        "to",
        "tool",
        "track",
        "tracks",
        "through",
        "until",
        "user",
        "users",
        "validation",
        "verification",
        "violation",
        "basis",
        "whether",
        "without",
        "workspace",
    }
).union(PLATFORM_NATIVE_TERMS)
LOW_ENTROPY_SENTINEL_HEADS = frozenset(
    {
        "evidence",
        "proof",
    }
)

@dataclass(frozen=True)
class LeakageFinding:
    location: str
    term: str
    line: int


@dataclass(frozen=True)
class _ScanToken:
    value: str
    line: int


@dataclass(frozen=True)
class _ScanDocument:
    location: str
    tokens: tuple[_ScanToken, ...]
    token_values: tuple[str, ...]
    token_lines: Mapping[str, tuple[int, ...]]
    token_positions: Mapping[str, tuple[int, ...]]


_PLATFORM_CUSTODY_DOCUMENT_CACHE: dict[tuple[str, str], tuple[_ScanDocument, ...]] = {}


def domain_leakage_terms(
    cases: Iterable[object] | None = None,
    *,
    include_historical: bool = True,
) -> tuple[str, ...]:
    """Return distinctive project-domain terms that must not enter platform custody."""

    selected_cases = tuple(cases) if cases is not None else default_cases()
    selected_terms = domain_leakage_terms_from_terms(
        term
        for case in selected_cases
        for term in case_leakage_terms(case)
    )
    if not include_historical:
        return selected_terms
    return tuple(sorted(set(selected_terms).union(historical_domain_leakage_terms())))


def domain_leakage_terms_from_terms(terms: Iterable[str]) -> tuple[str, ...]:
    """Return distinctive domain terms from an explicit simulation term stream."""

    leakage_terms: set[str] = set()
    for term in terms:
        normalized = _normalize_term(str(term))
        if normalized and _is_distinctive_declared_term(normalized):
            leakage_terms.add(normalized)
    return tuple(sorted(leakage_terms))


def domain_leakage_terms_from_text(text: str) -> tuple[str, ...]:
    """Derive distinctive project-domain leakage terms from simulation source text."""

    tokens = _tokens(text)
    candidates: set[str] = set()
    for width in (2, 3, 4):
        if len(tokens) < width:
            continue
        for index in range(len(tokens) - width + 1):
            window = tokens[index : index + width]
            if _is_distinctive_source_phrase(window):
                candidates.add(" ".join(window))
    return domain_leakage_terms_from_terms(candidates)


def historical_domain_leakage_terms() -> tuple[str, ...]:
    """Return historical consumer-domain sentinels used as release proof vocabulary."""

    return domain_leakage_terms_from_terms(historical_domain_leakage_sentinels())


def case_leakage_terms(case: object) -> tuple[str, ...]:
    """Return distinctive leakage terms for one simulation case."""

    declared = domain_leakage_terms_from_terms(_case_declared_leakage_terms(case))
    if declared:
        source_text = _case_source_text(case)
        if not source_text.strip():
            return declared
        grounded_declared = tuple(term for term in declared if _term_present(source_text, term))
        if len(grounded_declared) == len(declared):
            return grounded_declared
        source_terms = domain_leakage_terms_from_text(source_text)
        return tuple(dict.fromkeys((*grounded_declared, *source_terms)))
    return domain_leakage_terms_from_text(_case_source_text(case))


def case_leakage_term_candidates(case: object) -> tuple[str, ...]:
    """Return all source-grounded leakage sentinel candidates for one case.

    `case_leakage_terms` preserves the release-matrix contract that explicit,
    grounded sentinels are authoritative. High-volume external discovery needs a
    wider candidate set so the runner can discard sentinels that already appear
    in platform custody and still prove the case with richer source phrases.
    """

    declared = domain_leakage_terms_from_terms(_case_declared_leakage_terms(case))
    source_text = _case_source_text(case)
    if not source_text.strip():
        return declared
    grounded_declared = tuple(term for term in declared if _term_present(source_text, term))
    source_terms = domain_leakage_terms_from_text(_case_domain_source_text(case))
    return tuple(dict.fromkeys((*grounded_declared, *source_terms)))


def cases_missing_leakage_terms(cases: Iterable[object]) -> tuple[str, ...]:
    """Return case names whose contract cannot prove project-term leakage."""

    missing: list[str] = []
    for case in cases:
        if not case_leakage_terms(case):
            missing.append(str(getattr(case, "name", "unnamed case")).strip() or "unnamed case")
    return tuple(missing)


def scan_platform_custody(
    *,
    repo_root: Path,
    dist_dir: Path | None = None,
    terms: tuple[str, ...] | None = None,
) -> tuple[LeakageFinding, ...]:
    """Scan source and optional dist custody for forbidden project vocabulary."""

    scan_terms = terms or domain_leakage_terms()
    documents = _platform_custody_documents(
        repo_root=repo_root.resolve(),
        dist_dir=dist_dir.resolve() if dist_dir else None,
    )
    return _scan_documents(documents, terms=scan_terms)


def scan_repo(repo_root: Path, terms: tuple[str, ...] | None = None) -> tuple[LeakageFinding, ...]:
    scan_terms = terms or domain_leakage_terms()
    return _scan_documents(_repo_documents(repo_root.resolve()), terms=scan_terms)


def scan_dist(dist_dir: Path, terms: tuple[str, ...] | None = None) -> tuple[LeakageFinding, ...]:
    scan_terms = terms or domain_leakage_terms()
    return _scan_documents(_dist_documents(dist_dir.resolve()), terms=scan_terms)


def _platform_custody_documents(*, repo_root: Path, dist_dir: Path | None) -> tuple[_ScanDocument, ...]:
    key = (str(repo_root.resolve()), str(dist_dir.resolve()) if dist_dir else "")
    if key not in _PLATFORM_CUSTODY_DOCUMENT_CACHE:
        documents = list(_repo_documents(repo_root.resolve()))
        if dist_dir is not None:
            documents.extend(_dist_documents(dist_dir.resolve()))
        _PLATFORM_CUSTODY_DOCUMENT_CACHE[key] = tuple(documents)
    return _PLATFORM_CUSTODY_DOCUMENT_CACHE[key]


def _repo_documents(repo_root: Path) -> tuple[_ScanDocument, ...]:
    documents: list[_ScanDocument] = []
    for scan_path in SOURCE_SCAN_PATHS:
        path = repo_root / scan_path
        if path.is_file():
            documents.extend(_file_documents(path, repo_root=repo_root, location_prefix=""))
        elif path.is_dir():
            for file_path in sorted(path.rglob("*")):
                if _should_scan_source_file(file_path, repo_root):
                    documents.extend(_file_documents(file_path, repo_root=repo_root, location_prefix=""))
    return tuple(documents)


def _dist_documents(dist_dir: Path) -> tuple[_ScanDocument, ...]:
    documents: list[_ScanDocument] = []
    if not dist_dir.exists():
        return ()
    for file_path in sorted(dist_dir.iterdir()):
        if file_path.is_file() and file_path.name.endswith(".whl"):
            documents.extend(_wheel_documents(file_path))
        elif file_path.is_file() and file_path.name.endswith(".tar.gz"):
            documents.extend(_tar_documents(file_path))
        elif file_path.is_file() and _should_scan_dist_text_file(file_path):
            documents.extend(_file_documents(file_path, repo_root=dist_dir, location_prefix="dist:"))
    return tuple(documents)


def _wheel_documents(wheel: Path) -> tuple[_ScanDocument, ...]:
    documents: list[_ScanDocument] = []
    with zipfile.ZipFile(wheel) as zf:
        for name in sorted(zf.namelist()):
            if not _should_scan_wheel_member(name):
                continue
            try:
                text = zf.read(name).decode("utf-8")
            except UnicodeDecodeError:
                continue
            documents.append(_text_document(text, location=f"wheel:{wheel.name}:{name}"))
    return tuple(documents)


def _tar_documents(archive: Path) -> tuple[_ScanDocument, ...]:
    documents: list[_ScanDocument] = []
    with tarfile.open(archive) as tf:
        for member in sorted(tf.getmembers(), key=lambda item: item.name):
            if not member.isfile() or not _should_scan_tar_member(member.name):
                continue
            extracted = tf.extractfile(member)
            if extracted is None:
                continue
            try:
                text = extracted.read().decode("utf-8")
            except UnicodeDecodeError:
                continue
            documents.append(_text_document(text, location=f"tar:{archive.name}:{member.name}"))
    return tuple(documents)


def _file_documents(
    path: Path,
    *,
    repo_root: Path,
    location_prefix: str,
) -> tuple[_ScanDocument, ...]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ()
    location = f"{location_prefix}{path.relative_to(repo_root).as_posix()}"
    return (_text_document(text, location=location),)


def _text_document(text: str, *, location: str) -> _ScanDocument:
    tokens = _scan_tokens(text)
    line_sets: dict[str, set[int]] = {}
    position_lists: dict[str, list[int]] = {}
    for index, token in enumerate(tokens):
        line_sets.setdefault(token.value, set()).add(token.line)
        position_lists.setdefault(token.value, []).append(index)
    return _ScanDocument(
        location=location,
        tokens=tokens,
        token_values=tuple(token.value for token in tokens),
        token_lines={value: tuple(sorted(lines)) for value, lines in line_sets.items()},
        token_positions={value: tuple(positions) for value, positions in position_lists.items()},
    )


def _scan_documents(documents: tuple[_ScanDocument, ...], *, terms: tuple[str, ...]) -> tuple[LeakageFinding, ...]:
    findings: list[LeakageFinding] = []
    term_token_pairs = tuple((term, _tokens(term)) for term in terms)
    for document in documents:
        findings.extend(_scan_document(document, term_token_pairs=term_token_pairs))
    return tuple(findings)


def _scan_text(text: str, *, location: str, terms: tuple[str, ...]) -> tuple[LeakageFinding, ...]:
    return _scan_document(
        _text_document(text, location=location),
        term_token_pairs=tuple((term, _tokens(term)) for term in terms),
    )


def _scan_document(
    document: _ScanDocument,
    *,
    term_token_pairs: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[LeakageFinding, ...]:
    findings: list[LeakageFinding] = []
    seen: set[tuple[str, int]] = set()
    for term, term_tokens in term_token_pairs:
        for line_number in _term_match_lines(document, term_tokens):
            key = (term, line_number)
            if key in seen:
                continue
            seen.add(key)
            findings.append(LeakageFinding(location=document.location, term=term, line=line_number))
    return tuple(findings)


def _should_scan_source_file(path: Path, repo_root: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    relative = path.relative_to(repo_root).as_posix()
    if relative in MATRIX_FIXTURE_PATHS:
        return False
    if path.name in EVALUATION_EVIDENCE_FILES:
        return False
    parts = set(Path(relative).parts)
    if "worktrees" in parts or ".odylith" in parts:
        return False
    if "__pycache__" in parts or ".mypy_cache" in parts or ".pytest_cache" in parts:
        return False
    if "tests" in parts:
        return False
    if _is_governance_evidence_path(parts):
        return False
    return True


def _should_scan_wheel_member(name: str) -> bool:
    path = Path(name)
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    parts = set(path.parts)
    if "tests" in parts or "__pycache__" in parts:
        return False
    return name.startswith("odylith/") or name.endswith(".dist-info/METADATA")


def _should_scan_tar_member(name: str) -> bool:
    path = Path(name)
    if path.as_posix().endswith("/bin/odylith"):
        return True
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    parts = set(path.parts)
    if "tests" in parts or "__pycache__" in parts:
        return False
    if _is_governance_evidence_path(parts):
        return False
    if "odylith" in parts:
        return True
    return path.name == "METADATA" and any(
        part.startswith("odylith-") and part.endswith(".dist-info") for part in parts
    )


def _should_scan_dist_text_file(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    return not any(path.name.startswith(prefix) for prefix in DIST_EVIDENCE_PREFIXES)


def _normalize_term(term: str) -> str:
    return " ".join(_tokens(term))


def _is_distinctive_declared_term(term: str) -> bool:
    tokens = _tokens(term)
    if not tokens:
        return False
    if len(tokens) == 1:
        return not _is_generic_source_token(tokens[0])
    if len(tokens) <= 2 and all(_is_platform_generic_declared_token(token) for token in tokens):
        return False
    if len(tokens) == 2 and tokens[-1] in LOW_ENTROPY_SENTINEL_HEADS:
        return False
    return True


def _case_source_text_terms(case: object) -> tuple[str, ...]:
    return domain_leakage_terms_from_terms(
        term
        for value in _case_source_values(case)
        for term in domain_leakage_terms_from_text(str(value or ""))
    )


def _case_source_text(case: object) -> str:
    return "\n".join(str(value or "") for value in _case_source_values(case))


def _case_domain_source_text(case: object) -> str:
    values: list[str] = []
    name = str(getattr(case, "name", "") or "").strip()
    if name:
        values.append(name)
    prompt = str(getattr(case, "prompt", "") or "").strip()
    values.extend(_domain_source_prompt_segments(case=case, prompt=prompt))
    confirmed = str(getattr(case, "confirmed_intent_markdown", "") or "").strip()
    values.extend(_domain_source_confirmed_segments(case=case, confirmed=confirmed))
    return "\n".join(dict.fromkeys(value for value in values if value))


def _domain_source_prompt_segments(*, case: object, prompt: str) -> tuple[str, ...]:
    if not prompt:
        return ()
    declared_terms = _case_declared_leakage_terms(case)
    required_terms = _case_required_terms(case)
    segments: list[str] = []
    for index, segment in enumerate(_split_sentence_like_segments(prompt)):
        lowered = segment.casefold()
        if index == 0:
            segments.append(segment)
            continue
        if "distinctive" in lowered and "vocabulary" in lowered:
            segments.append(segment)
            continue
        if _contains_any_term(segment, declared_terms) or _contains_any_term(segment, required_terms):
            segments.append(segment)
    return tuple(dict.fromkeys(segments))


def _domain_source_confirmed_segments(*, case: object, confirmed: str) -> tuple[str, ...]:
    if not confirmed:
        return ()
    declared_terms = _case_declared_leakage_terms(case)
    required_terms = _case_required_terms(case)
    source_section_titles = {
        "product story",
        "state object",
        "first complete path",
        "actors",
        "systems",
    }
    segments: list[str] = []
    in_source_section = False
    for raw_line in confirmed.splitlines():
        line = _plain_markdown_line(raw_line)
        if not line:
            continue
        title = line.rstrip(":").casefold()
        if title in source_section_titles:
            in_source_section = True
            continue
        if _looks_like_markdown_heading(raw_line):
            in_source_section = False
        if in_source_section or _contains_any_term(line, declared_terms) or _contains_any_term(line, required_terms):
            segments.append(line)
    return tuple(dict.fromkeys(segments))


def _split_sentence_like_segments(text: str) -> tuple[str, ...]:
    normalized = str(text or "").replace("?", ".").replace("!", ".")
    return tuple(segment.strip() for segment in normalized.split(".") if segment.strip())


def _plain_markdown_line(line: str) -> str:
    value = str(line or "").strip()
    while value.startswith("#"):
        value = value[1:].strip()
    for prefix in ("- ", "* "):
        if value.startswith(prefix):
            value = value[len(prefix) :].strip()
    if value.startswith("**") and value.endswith("**") and len(value) > 4:
        value = value[2:-2].strip()
    return value


def _looks_like_markdown_heading(line: str) -> bool:
    value = str(line or "").lstrip()
    return value.startswith("#") or (value.startswith("**") and value.rstrip().endswith("**"))


def _case_source_values(case: object) -> tuple[object, ...]:
    return (
        getattr(case, "name", ""),
        getattr(case, "prompt", ""),
        getattr(case, "confirmed_intent_markdown", ""),
    )


def _term_present(text: str, term: str) -> bool:
    term_tokens = _tokens(term)
    if not term_tokens:
        return False
    return _contains_phrase(_tokens(text), term_tokens)


def _contains_any_term(text: str, terms: Iterable[str]) -> bool:
    return any(_term_present(text, str(term or "")) for term in terms)


def _is_distinctive_source_token(token: str) -> bool:
    value = str(token or "").casefold()
    if len(value) < 7:
        return False
    return not _is_generic_source_token(value)


def _is_distinctive_source_phrase(tokens: tuple[str, ...]) -> bool:
    if len(tokens) < 2:
        return False
    if _is_generic_source_token(tokens[0]) or _is_generic_source_token(tokens[-1]):
        return False
    signal_tokens = tuple(token for token in tokens if _is_distinctive_source_token(token))
    if len(signal_tokens) >= 2:
        return True
    supporting_tokens = tuple(token for token in tokens if _is_source_support_token(token))
    return any(_is_strong_source_token(token) for token in signal_tokens) and len(supporting_tokens) >= 2


def _is_strong_source_token(token: str) -> bool:
    value = str(token or "").casefold()
    return len(value) >= 9 and _is_distinctive_source_token(value)


def _is_source_support_token(token: str) -> bool:
    value = str(token or "").casefold()
    return len(value) >= 5 and not _is_generic_source_token(value)


def _is_generic_source_token(token: str) -> bool:
    return any(
        form in DOMAIN_TEXT_STOPWORDS or form in GENERIC_PRODUCT_TERMS or form in PLATFORM_NATIVE_TERMS
        for form in _source_token_forms(str(token or "").casefold())
    )


def _is_platform_generic_declared_token(token: str) -> bool:
    return any(
        form in DOMAIN_TEXT_STOPWORDS or form in PLATFORM_NATIVE_TERMS
        for form in _source_token_forms(str(token or "").casefold())
    )


def _source_token_forms(token: str) -> tuple[str, ...]:
    value = str(token or "").casefold()
    forms = [value]
    if len(value) > 2:
        forms.append(f"{value}s")
    if len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
        forms.append(value[:-1])
    if len(value) > 3 and value.endswith("y"):
        forms.append(f"{value[:-1]}ies")
    if len(value) > 4 and value.endswith("ies"):
        forms.append(f"{value[:-3]}y")
    return tuple(dict.fromkeys(form for form in forms if form))


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(token.value for token in _scan_tokens(text))


def _scan_tokens(text: str) -> tuple[_ScanToken, ...]:
    tokens: list[_ScanToken] = []
    current: list[str] = []
    line_number = 1
    token_line = 1
    for char in str(text or ""):
        if char.isalnum():
            if not current:
                token_line = line_number
            current.append(char)
            continue
        if current:
            tokens.extend(_scan_token_parts("".join(current), line=token_line))
            current = []
        if char == "\n":
            line_number += 1
    if current:
        tokens.extend(_scan_token_parts("".join(current), line=token_line))
    return tuple(tokens)


def _scan_token_parts(value: str, *, line: int) -> tuple[_ScanToken, ...]:
    parts = _identifier_parts(value)
    tokens = tuple(_ScanToken(part.casefold(), line) for part in parts if part)
    compact = "".join(part.casefold() for part in parts if part)
    if compact and compact not in {token.value for token in tokens}:
        return (*tokens, _ScanToken(compact, line))
    return tokens


def _identifier_parts(value: str) -> tuple[str, ...]:
    text = str(value or "")
    if not text:
        return ()
    starts = [0]
    for index in range(1, len(text)):
        previous = text[index - 1]
        current = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if (
            previous.islower()
            and current.isupper()
            or previous.isalpha()
            and current.isdigit()
            or previous.isdigit()
            and current.isalpha()
            or previous.isupper()
            and current.isupper()
            and bool(next_char)
            and next_char.islower()
        ):
            starts.append(index)
    starts.append(len(text))
    return tuple(text[starts[index] : starts[index + 1]] for index in range(len(starts) - 1))


def _term_match_lines(document: _ScanDocument, term_tokens: tuple[str, ...]) -> tuple[int, ...]:
    if not document.tokens or not term_tokens:
        return ()
    lines: list[int] = []
    if len(term_tokens) == 1:
        return document.token_lines.get(term_tokens[0], ())
    width = len(term_tokens)
    if width <= len(document.token_values):
        lines.extend(
            document.tokens[index].line
            for index in document.token_positions.get(term_tokens[0], ())
            if index + width <= len(document.token_values)
            and document.token_values[index : index + width] == term_tokens
        )
    compact = "".join(term_tokens)
    if compact:
        lines.extend(
            line
            for token_value, token_lines in document.token_lines.items()
            if compact in token_value
            for line in token_lines
        )
    return tuple(lines)


def _contains_phrase(line_tokens: tuple[str, ...], term_tokens: tuple[str, ...]) -> bool:
    if len(term_tokens) > len(line_tokens):
        return False
    width = len(term_tokens)
    return any(line_tokens[index : index + width] == term_tokens for index in range(len(line_tokens) - width + 1))


def _is_governance_evidence_path(parts: set[str]) -> bool:
    return bool(parts & GOVERNANCE_EVIDENCE_PARTS and "agents-guidelines" not in parts and "skills" not in parts)


def _case_required_terms(case: object) -> tuple[str, ...]:
    value = getattr(case, "required_terms", ())
    if isinstance(value, (str, bytes)):
        return (str(value),)
    if not isinstance(value, Iterable):
        return ()
    return tuple(str(term) for term in value)


def _case_declared_leakage_terms(case: object) -> tuple[str, ...]:
    value = getattr(case, "leakage_terms", ())
    if isinstance(value, (str, bytes)):
        return (str(value),)
    if not isinstance(value, Iterable):
        return ()
    return tuple(str(term) for term in value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--dist-dir", type=Path)
    args = parser.parse_args(argv)

    terms = domain_leakage_terms()
    findings = list(scan_platform_custody(repo_root=args.repo_root, dist_dir=args.dist_dir, terms=terms))

    if findings:
        print("platform domain leakage check failed", file=sys.stderr)
        for finding in findings[:40]:
            print(f"- {finding.location}:{finding.line}: leaked `{finding.term}`", file=sys.stderr)
        remaining = len(findings) - 40
        if remaining > 0:
            print(f"- ... {remaining} additional finding(s)", file=sys.stderr)
        return 1

    print(f"platform domain leakage check passed: {len(terms)} distinctive fixture term(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
