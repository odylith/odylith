#!/usr/bin/env python3
"""Validate maintainer identity and contribution history against repo policy."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import NamedTuple, Sequence


EXPECTED_NAME = "freedom-research"
EXPECTED_EMAIL = "freedom@freedompreetham.org"
EXPECTED_GITHUB_LOGIN = EXPECTED_NAME
EXPECTED_GITHUB_REPOSITORY = "odylith/odylith"
EXPECTED_GITHUB_PERMISSIONS = frozenset({"ADMIN", "MAINTAIN", "WRITE"})
EXPECTED_LOCAL_CONFIG = {
    "user.name": EXPECTED_NAME,
    "user.email": EXPECTED_EMAIL,
    "user.useConfigOnly": "true",
}
ALLOWED_LEGACY_MAINTAINER_IDENTITIES = frozenset(
    {
        ("Freedom Preetham", EXPECTED_EMAIL),
    }
)
LEGACY_MAINTAINER_HISTORY_CUTOFF = "fae446995e13e12409e50f944a336dbc846db90a"
IDENT_PATTERN = re.compile(r"^(?P<name>.+) <(?P<email>[^>]+)> \d+ [+-]\d{4}$")
STRONG_ASSISTANT_IDENTITY_PHRASES = (
    "ai agent",
    "ai assistant",
    "amazon q developer",
    "anthropic claude",
    "chatgpt",
    "claude code",
    "code assistant",
    "coding assistant",
    "cursor agent",
    "gemini code assist",
    "gpt 4",
    "gpt 4o",
    "gpt 5",
    "github copilot",
    "google gemini",
    "llm assistant",
    "openai codex",
    "replit agent",
    "sourcegraph cody",
    "windsurf agent",
)
ASSISTANT_BRAND_WORDS = frozenset(
    {
        "ai",
        "aider",
        "amazon",
        "amazonq",
        "chatgpt",
        "claude",
        "codeium",
        "codex",
        "copilot",
        "coderabbit",
        "continue",
        "cody",
        "cursor",
        "devin",
        "gemini",
        "gpt",
        "gpt5",
        "greptile",
        "llm",
        "openai",
        "qodo",
        "replit",
        "sweep",
        "tabnine",
        "windsurf",
    }
)
ASSISTANT_ROLE_WORDS = frozenset(
    {"agent", "assistant", "automation", "bot", "cli", "code", "noreply", "swe", "worker"}
)
ASSISTANT_VENDOR_DOMAINS = frozenset(
    {
        "anthropic.com",
        "amazon.com",
        "aider.chat",
        "coderabbit.ai",
        "codeium.com",
        "continue.dev",
        "cursor.com",
        "deepmind.com",
        "google.com",
        "greptile.com",
        "openai.com",
        "qodo.ai",
        "replit.com",
        "sourcegraph.com",
        "tabnine.com",
        "windsurf.com",
    }
)
CONFUSABLE_IDENTITY_CHARACTERS = str.maketrans(
    {
        "а": "a",
        "в": "b",
        "с": "c",
        "е": "e",
        "і": "i",
        "ј": "j",
        "к": "k",
        "м": "m",
        "н": "h",
        "о": "o",
        "р": "p",
        "т": "t",
        "у": "y",
        "х": "x",
        "α": "a",
        "ε": "e",
        "ι": "i",
        "κ": "k",
        "ο": "o",
        "ρ": "p",
        "τ": "t",
        "υ": "y",
        "χ": "x",
        "ϲ": "c",
    }
)
TRAILER_DASH_CHARACTERS = str.maketrans(
    {
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        "−": "-",
    }
)
ATTRIBUTION_PHRASE_PATTERN = re.compile(
    r"\b(?:(?<!co )authored|assisted|built|committed|created|generated|implemented|"
    r"pair programmed|powered|prepared|produced|reported|reviewed|tested|written)"
    r"\s+(?:by|with)\s+(?P<subject>.+)",
)
ATTRIBUTION_TRAILER_PATTERN = re.compile(
    r"^(?P<key>[A-Za-z][A-Za-z0-9-]*-By)\s*:\s*(?P<value>.*)$",
    re.IGNORECASE,
)


class HistoryRecord(NamedTuple):
    sha: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    message: str


def _run_git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown git failure"
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return completed.stdout.strip()


def _run_command(repo_root: Path, args: Sequence[str]) -> str:
    completed = subprocess.run(
        list(args),
        cwd=repo_root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown command failure"
        raise RuntimeError(f"{' '.join(args)} failed: {stderr}")
    return completed.stdout.strip()


def _get_local_config(repo_root: Path, key: str) -> str | None:
    completed = subprocess.run(
        ["git", "config", "--local", "--get", key],
        cwd=repo_root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    if completed.returncode == 1:
        return None
    stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown git failure"
    raise RuntimeError(f"git config --local --get {key} failed: {stderr}")


def _parse_ident(raw: str, *, label: str) -> tuple[str, str]:
    match = IDENT_PATTERN.match(raw.strip())
    if match is None:
        raise RuntimeError(f"could not parse {label}: {raw!r}")
    return match.group("name"), match.group("email")


def _valid_direct_identity(name: str, email: str) -> bool:
    return name == EXPECTED_NAME and email == EXPECTED_EMAIL


def _normalized_identity_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = normalized.translate(CONFUSABLE_IDENTITY_CHARACTERS)
    normalized = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Cf"
        and not unicodedata.category(character).startswith("M")
    )
    normalized = normalized.replace("[bot]", " bot ")
    return " ".join(re.sub(r"[\W_]+", " ", normalized).split())


def _normalized_email_local_part(email: str) -> str:
    local_part = email.casefold().partition("@")[0]
    local_part = re.sub(r"^\d+\+", "", local_part)
    return _normalized_identity_text(local_part)


def _contains_identity_phrase(normalized: str, phrase: str) -> bool:
    return f" {phrase} " in f" {normalized} "


def _has_strong_assistant_phrase(normalized: str) -> bool:
    return any(
        _contains_identity_phrase(normalized, phrase)
        for phrase in STRONG_ASSISTANT_IDENTITY_PHRASES
    )


def _brand_and_role_signal(normalized: str) -> bool:
    words = frozenset(normalized.split())
    return bool(words & ASSISTANT_BRAND_WORDS) and bool(words & ASSISTANT_ROLE_WORDS)


def _uses_prohibited_assistant_identity(name: str, email: str) -> bool:
    normalized_name = _normalized_identity_text(name)
    normalized_email = _normalized_email_local_part(email)
    combined_words = frozenset((*normalized_name.split(), *normalized_email.split()))
    email_domain = email.casefold().partition("@")[2].rstrip(".")
    vendor_domain = any(
        email_domain == vendor or email_domain.endswith(f".{vendor}")
        for vendor in ASSISTANT_VENDOR_DOMAINS
    )
    return (
        _has_strong_assistant_phrase(normalized_name)
        or _has_strong_assistant_phrase(normalized_email)
        or (
            bool(combined_words & ASSISTANT_BRAND_WORDS)
            and bool(combined_words & ASSISTANT_ROLE_WORDS)
        )
        or (
            vendor_domain and bool(combined_words & ASSISTANT_BRAND_WORDS)
        )
    )


def _uses_unapproved_maintainer_identity(
    name: str,
    email: str,
    *,
    allow_legacy: bool,
) -> bool:
    if _valid_direct_identity(name, email):
        return False
    if allow_legacy and (name, email) in ALLOWED_LEGACY_MAINTAINER_IDENTITIES:
        return False
    normalized_name = _normalized_identity_text(name)
    expected_name = _normalized_identity_text(EXPECTED_NAME)
    reserved_names = {expected_name}
    reserved_names.update(
        _normalized_identity_text(legacy_name)
        for legacy_name, _legacy_email in ALLOWED_LEGACY_MAINTAINER_IDENTITIES
    )
    compact_name = normalized_name.replace(" ", "")
    return (
        any(
            _contains_identity_phrase(normalized_name, reserved)
            or reserved.replace(" ", "") in compact_name
            for reserved in reserved_names
        )
        or email.casefold() == EXPECTED_EMAIL.casefold()
    )


def _split_trailer_identity(value: str) -> tuple[str, str] | None:
    stripped = value.strip()
    if not stripped.endswith(">"):
        return None
    name, separator, email = stripped[:-1].rpartition("<")
    if not separator or not name.strip() or not email.strip():
        return None
    if any(character in name or character in email for character in "<>"):
        return None
    return name.strip(), email.strip()


def _identity_value_attributes_assistant(value: str) -> bool:
    identity = _split_trailer_identity(value)
    if identity is not None:
        return _uses_prohibited_assistant_identity(*identity)
    normalized = _normalized_identity_text(value)
    words = frozenset(normalized.split())
    return (
        _has_strong_assistant_phrase(normalized)
        or _brand_and_role_signal(normalized)
        or (len(words) == 1 and bool(words & ASSISTANT_BRAND_WORDS))
    )


def _normalized_trailer_line(line: str) -> str:
    normalized = unicodedata.normalize("NFKC", line).translate(TRAILER_DASH_CHARACTERS)
    return "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Cf"
        and not unicodedata.category(character).startswith("M")
    )


def _attribution_is_negated(normalized_line: str, *, match_start: int) -> bool:
    prefix = normalized_line[:match_start].strip()
    if re.search(r"\b(?:never|not|without)\s*$", prefix):
        return True
    if re.match(r"^(?:deny|forbid|remove|removed|removing)\b", normalized_line):
        return True
    return bool(
        prefix.startswith("no ")
        and re.search(r"\b(?:are|is|was|were)\s*$", prefix)
    )


def _prohibited_message_attribution(message: str) -> str | None:
    lines = message.splitlines()
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        trailer_match = ATTRIBUTION_TRAILER_PATTERN.match(_normalized_trailer_line(line))
        if trailer_match is not None:
            value = trailer_match.group("value")
            continuation_index = index + 1
            while continuation_index < len(lines) and lines[continuation_index].startswith((" ", "\t")):
                value = f"{value} {lines[continuation_index].strip()}".strip()
                continuation_index += 1
            if _identity_value_attributes_assistant(value):
                return f"{trailer_match.group('key')}: {value}".strip()
            continue

        normalized_line = _normalized_identity_text(line)
        phrase_match = ATTRIBUTION_PHRASE_PATTERN.search(normalized_line)
        if phrase_match is not None and _identity_value_attributes_assistant(
            phrase_match.group("subject")
        ):
            if _attribution_is_negated(normalized_line, match_start=phrase_match.start()):
                continue
            return line
    return None


def _history_records(
    repo_root: Path,
    *,
    revisions: Sequence[str],
    include_all: bool,
) -> list[HistoryRecord]:
    log_args = [
        "log",
        "--no-show-signature",
        "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%B%x00",
    ]
    if include_all:
        log_args.append("--all")
    elif revisions:
        unsafe_revisions = [revision for revision in revisions if revision.startswith("-")]
        if unsafe_revisions:
            raise RuntimeError(
                f"revision selectors must not start with '-': {unsafe_revisions!r}"
            )
        log_args.extend(revisions)
    else:
        log_args.append("HEAD")
    output = _run_git(repo_root, *log_args)
    if not output:
        return []

    fields = output.split("\x00")
    if fields and not fields[-1].strip("\n"):
        fields.pop()
    if len(fields) % len(HistoryRecord._fields) != 0:
        raise RuntimeError("could not parse git history record")

    records: list[HistoryRecord] = []
    field_count = len(HistoryRecord._fields)
    for offset in range(0, len(fields), field_count):
        record_fields = fields[offset : offset + field_count]
        record_fields[0] = record_fields[0].lstrip("\n")
        records.append(HistoryRecord(*record_fields))
    return records


def validate_local_identity(repo_root: Path) -> list[str]:
    failures: list[str] = []
    for key, expected in EXPECTED_LOCAL_CONFIG.items():
        value = _get_local_config(repo_root, key)
        if value is None:
            failures.append(f"missing local {key}; expected {expected!r}")
            continue
        if value != expected:
            failures.append(f"local {key} must be {expected!r} (found {value!r})")
    for role in ("AUTHOR", "COMMITTER"):
        ident = _run_git(repo_root, "var", f"GIT_{role}_IDENT")
        name, email = _parse_ident(ident, label=f"GIT_{role}_IDENT")
        if name != EXPECTED_NAME:
            failures.append(f"{role.lower()} name must be {EXPECTED_NAME!r} (found {name!r})")
        if email != EXPECTED_EMAIL:
            failures.append(f"{role.lower()} email must be {EXPECTED_EMAIL!r} (found {email!r})")
    return failures


def validate_commit_history(repo_root: Path, *, revisions: Sequence[str], include_all: bool) -> list[str]:
    failures: list[str] = []
    legacy_commit_shas: frozenset[str] | None = None

    def legacy_identity_is_allowed(sha: str, name: str, email: str) -> bool:
        nonlocal legacy_commit_shas
        if (name, email) not in ALLOWED_LEGACY_MAINTAINER_IDENTITIES:
            return False
        if legacy_commit_shas is None:
            legacy_commit_shas = frozenset(
                _run_git(repo_root, "rev-list", LEGACY_MAINTAINER_HISTORY_CUTOFF).splitlines()
            )
        return sha in legacy_commit_shas

    for sha, author_name, author_email, committer_name, committer_email, message in _history_records(
        repo_root,
        revisions=revisions,
        include_all=include_all,
    ):
        if _uses_unapproved_maintainer_identity(
            author_name,
            author_email,
            allow_legacy=legacy_identity_is_allowed(sha, author_name, author_email),
        ):
            failures.append(
                f"{sha}: maintainer authorship must use the exact "
                f"{EXPECTED_NAME!r} / {EXPECTED_EMAIL!r} pair "
                f"(found {author_name!r} / {author_email!r})"
            )
        elif _uses_prohibited_assistant_identity(author_name, author_email):
            failures.append(
                f"{sha}: author identity must not use an assistant, model, or coding tool "
                f"(found {author_name!r} / {author_email!r})"
            )

        if _uses_prohibited_assistant_identity(committer_name, committer_email):
            failures.append(
                f"{sha}: committer identity must not use an assistant, model, or coding tool "
                f"(found {committer_name!r} / {committer_email!r})"
            )
        elif _uses_unapproved_maintainer_identity(
            committer_name,
            committer_email,
            allow_legacy=legacy_identity_is_allowed(sha, committer_name, committer_email),
        ):
            failures.append(
                f"{sha}: maintainer committer identity must use the exact "
                f"{EXPECTED_NAME!r} / {EXPECTED_EMAIL!r} pair "
                f"(found {committer_name!r} / {committer_email!r})"
            )

        prohibited_attribution = _prohibited_message_attribution(message)
        if prohibited_attribution is not None:
            failures.append(
                f"{sha}: commit message must not attribute work to an assistant, model, or coding tool "
                f"(found {prohibited_attribution!r})"
            )
    return failures


def validate_github_identity(repo_root: Path) -> list[str]:
    if shutil.which("gh") is None:
        return ["GitHub CLI `gh` is required before pushing from this repository"]

    user_raw = _run_command(repo_root, ["gh", "api", "user"])
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh api user returned invalid JSON: {exc}") from exc

    failures: list[str] = []
    login = str(user.get("login") or "")
    email = str(user.get("email") or "")
    if login != EXPECTED_GITHUB_LOGIN:
        failures.append(f"GitHub login must be {EXPECTED_GITHUB_LOGIN!r} (found {login!r})")
    if email != EXPECTED_EMAIL:
        failures.append(f"GitHub email must be {EXPECTED_EMAIL!r} (found {email!r})")

    permission_raw = _run_command(
        repo_root,
        ["gh", "repo", "view", EXPECTED_GITHUB_REPOSITORY, "--json", "viewerPermission"],
    )
    try:
        permission_payload = json.loads(permission_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh repo view returned invalid JSON: {exc}") from exc
    permission = str(permission_payload.get("viewerPermission") or "")
    if permission not in EXPECTED_GITHUB_PERMISSIONS:
        expected = ", ".join(sorted(EXPECTED_GITHUB_PERMISSIONS))
        failures.append(
            f"GitHub permission for {EXPECTED_GITHUB_REPOSITORY} must be one of {{{expected}}} "
            f"(found {permission!r})"
        )
    return failures


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Odylith maintainer credentials while preserving external human Git authorship."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser(
        "config",
        help="Validate the local repo config and effective author/committer identity.",
    )
    config_parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root.")

    history_parser = subparsers.add_parser(
        "history",
        help=(
            "Validate maintainer aliases and reject explicit assistant/tool identity signatures or attribution "
            "without rewriting external human contributors."
        ),
    )
    history_parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root.")
    history_parser.add_argument(
        "--all",
        action="store_true",
        help="Inspect every reachable commit instead of only the listed revisions.",
    )
    history_parser.add_argument(
        "revisions",
        nargs="*",
        help="Revision selectors for git log. Defaults to HEAD when omitted.",
    )

    github_parser = subparsers.add_parser(
        "github",
        help="Validate the authenticated GitHub CLI account before push operations.",
    )
    github_parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "config":
            failures = validate_local_identity(repo_root)
        elif args.command == "github":
            failures = validate_github_identity(repo_root)
        else:
            failures = validate_commit_history(
                repo_root,
                revisions=args.revisions,
                include_all=args.all,
            )
    except RuntimeError as exc:
        print(f"identity guard: {exc}", file=sys.stderr)
        return 2

    if not failures:
        return 0

    for failure in failures:
        print(f"identity guard: {failure}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
