"""Shared Codex CLI capability inspection and effective-config rendering."""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from odylith.install.fs import atomic_write_text


_CODEX_VERSION_RE = re.compile(r"\bcodex-cli\s+(?P<version>\S+)")
_COLUMN_SPLIT_RE = re.compile(r"\s{2,}")
_UNSUPPORTED_TOKENS = (
    "unexpected argument",
    "unrecognized subcommand",
    "unknown subcommand",
    "unknown command",
)
_PROJECT_ROOT_MARKERS: tuple[str, ...] = (".git", "AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md")
_PROJECT_DOC_FALLBACK_FILENAMES: tuple[str, ...] = ("CLAUDE.md",)
_PROJECT_DOC_MAX_BYTES = 65536
_AGENTS_MAX_THREADS = 6
_AGENTS_MAX_DEPTH = 1


@dataclass(frozen=True)
class CodexCliCapabilitySnapshot:
    repo_root: str
    codex_bin: str
    codex_available: bool
    codex_version_raw: str
    codex_version: str
    baseline_contract: str
    baseline_ready: bool
    launcher_present: bool
    repo_agents_present: bool
    codex_project_assets_present: bool
    codex_skill_shims_present: bool
    project_assets_mode: str
    trusted_project_required: bool
    hooks_feature_known: bool
    hooks_feature_enabled: bool | None
    prompt_input_probe_supported: bool
    prompt_input_probe_passed: bool
    repo_guidance_detected: bool
    future_version_policy: str
    overall_posture: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_repo_root(repo_root: Path | str) -> Path:
    return Path(repo_root).resolve()


def _run_codex_command(
    *,
    repo_root: Path,
    codex_bin: str,
    args: list[str],
    timeout: int = 10,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            [codex_bin, *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None


def parse_codex_version(text: str) -> str:
    match = _CODEX_VERSION_RE.search(str(text or ""))
    if match:
        return str(match.group("version")).strip()
    tokens = str(text or "").strip().split()
    return tokens[-1] if tokens else ""


def parse_feature_flags(text: str) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        columns = [column.strip() for column in _COLUMN_SPLIT_RE.split(line) if column.strip()]
        if len(columns) < 3:
            continue
        enabled_token = columns[-1].lower()
        if enabled_token not in {"true", "false"}:
            continue
        parsed[columns[0]] = {
            "stability": " ".join(columns[1:-1]).strip(),
            "enabled": enabled_token == "true",
        }
    return parsed


def _first_project_doc_probe_token(repo_root: Path) -> str:
    path = repo_root / "AGENTS.md"
    if not path.is_file():
        return ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line:
            return line
    return ""


def _unsupported_probe(completed: subprocess.CompletedProcess[str] | None) -> bool:
    if completed is None:
        return False
    combined = f"{completed.stdout}\n{completed.stderr}".lower()
    return any(token in combined for token in _UNSUPPORTED_TOKENS)


@lru_cache(maxsize=32)
def _inspect_cached(repo_root: str, codex_bin: str, probe_prompt_input: bool) -> CodexCliCapabilitySnapshot:
    resolved_root = _resolve_repo_root(repo_root)
    launcher_present = (resolved_root / ".odylith" / "bin" / "odylith").is_file()
    repo_agents_present = (resolved_root / "AGENTS.md").is_file()
    codex_project_assets_present = (
        (resolved_root / ".codex" / "config.toml").is_file()
        and (resolved_root / ".codex" / "hooks.json").is_file()
        and any((resolved_root / ".codex" / "agents").glob("*.toml"))
    )
    codex_skill_shims_present = any((resolved_root / ".agents" / "skills").rglob("SKILL.md"))
    baseline_ready = launcher_present and repo_agents_present

    version_run = _run_codex_command(repo_root=resolved_root, codex_bin=codex_bin, args=["--version"])
    codex_available = version_run is not None and version_run.returncode == 0
    version_raw = str(version_run.stdout or "").strip() if version_run is not None else ""
    version = parse_codex_version(version_raw)

    hooks_feature_known = False
    hooks_feature_enabled: bool | None = None
    if codex_available:
        features_run = _run_codex_command(repo_root=resolved_root, codex_bin=codex_bin, args=["features", "list"])
        features = parse_feature_flags(features_run.stdout if features_run is not None and features_run.returncode == 0 else "")
        if "codex_hooks" in features:
            hooks_feature_known = True
            hooks_feature_enabled = bool(features["codex_hooks"]["enabled"])

    prompt_input_probe_supported = False
    prompt_input_probe_passed = False
    repo_guidance_detected = False
    if codex_available and probe_prompt_input:
        prompt_run = _run_codex_command(repo_root=resolved_root, codex_bin=codex_bin, args=["debug", "prompt-input"])
        if prompt_run is not None:
            prompt_input_probe_supported = prompt_run.returncode == 0 or not _unsupported_probe(prompt_run)
            prompt_input_probe_passed = prompt_run.returncode == 0
            probe_token = _first_project_doc_probe_token(resolved_root)
            if prompt_input_probe_passed and probe_token:
                repo_guidance_detected = probe_token in str(prompt_run.stdout or "")

    overall_posture = "baseline_incomplete"
    if baseline_ready:
        overall_posture = "baseline_safe"
        if codex_available:
            overall_posture = "baseline_safe_with_best_effort_project_assets"
        if prompt_input_probe_passed and repo_guidance_detected:
            overall_posture = "baseline_safe_live_proven"

    return CodexCliCapabilitySnapshot(
        repo_root=str(resolved_root),
        codex_bin=codex_bin,
        codex_available=codex_available,
        codex_version_raw=version_raw,
        codex_version=version,
        baseline_contract="AGENTS.md + ./.odylith/bin/odylith",
        baseline_ready=baseline_ready,
        launcher_present=launcher_present,
        repo_agents_present=repo_agents_present,
        codex_project_assets_present=codex_project_assets_present,
        codex_skill_shims_present=codex_skill_shims_present,
        project_assets_mode="best_effort_enhancements",
        trusted_project_required=True,
        hooks_feature_known=hooks_feature_known,
        hooks_feature_enabled=hooks_feature_enabled,
        prompt_input_probe_supported=prompt_input_probe_supported,
        prompt_input_probe_passed=prompt_input_probe_passed,
        repo_guidance_detected=repo_guidance_detected,
        future_version_policy="capability_based_no_max_pin",
        overall_posture=overall_posture,
    )


def clear_codex_cli_capability_cache() -> None:
    _inspect_cached.cache_clear()


def inspect_codex_cli_capabilities(
    repo_root: Path | str = ".",
    *,
    codex_bin: str = "codex",
    probe_prompt_input: bool = True,
) -> CodexCliCapabilitySnapshot:
    return _inspect_cached(str(_resolve_repo_root(repo_root)), str(codex_bin or "codex").strip() or "codex", bool(probe_prompt_input))


def render_effective_codex_project_config(
    *,
    repo_root: Path | str = ".",
    capabilities: CodexCliCapabilitySnapshot | None = None,
) -> str:
    resolved_root = _resolve_repo_root(repo_root)
    snapshot = capabilities or inspect_codex_cli_capabilities(
        repo_root=resolved_root,
        probe_prompt_input=False,
    )
    lines = [
        'project_root_markers = ["' + '", "'.join(_PROJECT_ROOT_MARKERS) + '"]',
        f"project_doc_max_bytes = {max(_PROJECT_DOC_MAX_BYTES, (resolved_root / 'AGENTS.md').stat().st_size if (resolved_root / 'AGENTS.md').is_file() else 0)}",
        'project_doc_fallback_filenames = ["' + '", "'.join(_PROJECT_DOC_FALLBACK_FILENAMES) + '"]',
    ]
    if snapshot.hooks_feature_enabled is True:
        lines.extend(
            [
                "",
                "[features]",
                "codex_hooks = true",
            ]
        )
    lines.extend(
        [
            "",
            "[agents]",
            f"max_threads = {_AGENTS_MAX_THREADS}",
            f"max_depth = {_AGENTS_MAX_DEPTH}",
            "",
        ]
    )
    return "\n".join(lines)


def write_effective_codex_project_config(
    *,
    repo_root: Path | str,
    capabilities: CodexCliCapabilitySnapshot | None = None,
) -> Path:
    resolved_root = _resolve_repo_root(repo_root)
    target_path = resolved_root / ".codex" / "config.toml"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        target_path,
        render_effective_codex_project_config(repo_root=resolved_root, capabilities=capabilities),
        encoding="utf-8",
    )
    return target_path
