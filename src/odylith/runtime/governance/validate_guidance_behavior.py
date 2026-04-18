from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.governance import guidance_behavior_benchmark_contracts
from odylith.runtime.governance import guidance_behavior_guidance_contracts
from odylith.runtime.governance import guidance_behavior_platform_contracts
from odylith.runtime.governance import guidance_behavior_runtime_contracts


CONTRACT = "odylith_guidance_behavior_validation.v1"
CORPUS_RELATIVE_PATH = Path("odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json")
BUNDLE_CORPUS_RELATIVE_PATH = Path(
    "src/odylith/bundle/assets/odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json"
)
BENCHMARK_CORPUS_RELATIVE_PATH = Path("odylith/runtime/source/optimization-evaluation-corpus.v1.json")
BUNDLE_BENCHMARK_CORPUS_RELATIVE_PATH = Path(
    "src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json"
)
EXPECTED_CORPUS_VERSION = "guidance_behavior_evaluation_corpus.v1"
EXPECTED_FAMILY = "guidance_behavior"
REQUIRED_CASE_FIELDS: tuple[str, ...] = (
    "id",
    "family",
    "prompt",
    "expected_behavior",
    "forbidden_behavior",
    "required_evidence",
    "related_guidance_refs",
    "severity",
)

_LIST_CASE_FIELDS = {
    "expected_behavior",
    "forbidden_behavior",
    "required_evidence",
    "related_guidance_refs",
}
_VALID_SEVERITIES = {"critical", "high", "medium", "low"}
_ALLOWED_RELATED_REF_PREFIXES = (
    "AGENTS.md",
    "odylith/",
    "src/odylith/",
    ".agents/",
    ".claude/",
    ".codex/",
)


@dataclass(frozen=True)
class GuidanceIssue:
    check_id: str
    message: str
    path: str = ""
    case_id: str = ""

    def as_dict(self) -> dict[str, str]:
        payload = {"check_id": self.check_id, "message": self.message}
        if self.path:
            payload["path"] = self.path
        if self.case_id:
            payload["case_id"] = self.case_id
        return payload


class CorpusStateError(ValueError):
    def __init__(self, message: str, *, status: str = "malformed", path: Path | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.path = path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith validate guidance-behavior",
        description="Validate Odylith guidance behavior pressure cases and high-risk guidance contracts.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Restrict validation to one corpus case id. May be supplied multiple times.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Render the validation result as JSON.")
    return parser.parse_args(argv)


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CorpusStateError(f"guidance behavior corpus is missing: {path}", status="unavailable", path=path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusStateError(f"guidance behavior corpus is not valid JSON: {path}: {exc}", path=path) from exc
    if not isinstance(payload, dict):
        raise CorpusStateError(f"guidance behavior corpus must be a JSON object: {path}", path=path)
    return payload


def _nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def _validate_case_shape(case: Mapping[str, Any], *, index: int) -> list[GuidanceIssue]:
    issues: list[GuidanceIssue] = []
    case_id = str(case.get("id", "")).strip()
    for field in REQUIRED_CASE_FIELDS:
        if field not in case:
            issues.append(GuidanceIssue("case_missing_field", f"case {index} is missing `{field}`", case_id=case_id))
            continue
        value = case.get(field)
        if field in _LIST_CASE_FIELDS:
            if not _nonempty_string_list(value):
                issues.append(
                    GuidanceIssue(
                        "case_field_type",
                        f"case {case_id or index} field `{field}` must be a non-empty string list",
                        case_id=case_id,
                    )
                )
        elif not isinstance(value, str) or not value.strip():
            issues.append(
                GuidanceIssue(
                    "case_field_type",
                    f"case {case_id or index} field `{field}` must be a non-empty string",
                    case_id=case_id,
                )
            )
    if case_id and case.get("family") != EXPECTED_FAMILY:
        issues.append(
            GuidanceIssue(
                "case_family",
                f"case {case_id} family must be `{EXPECTED_FAMILY}`",
                case_id=case_id,
            )
        )
    severity = str(case.get("severity", "")).strip().lower()
    if severity and severity not in _VALID_SEVERITIES:
        issues.append(
            GuidanceIssue(
                "case_severity",
                f"case {case_id or index} severity must be one of {', '.join(sorted(_VALID_SEVERITIES))}",
                case_id=case_id,
            )
        )
    related_refs = case.get("related_guidance_refs", [])
    if isinstance(related_refs, list):
        for raw_ref in related_refs:
            ref = str(raw_ref).strip()
            if ref.startswith("/") or ".." in Path(ref).parts:
                issues.append(GuidanceIssue("case_external_ref", f"case {case_id} uses an unsafe guidance ref `{ref}`", case_id=case_id))
                continue
            if not ref.startswith(_ALLOWED_RELATED_REF_PREFIXES):
                issues.append(
                    GuidanceIssue(
                        "case_external_ref",
                        f"case {case_id} guidance ref `{ref}` is outside Odylith-owned guidance surfaces",
                        case_id=case_id,
                    )
                )
    return issues


def load_guidance_behavior_cases(*, repo_root: Path) -> list[dict[str, Any]]:
    corpus_path = Path(repo_root).resolve() / CORPUS_RELATIVE_PATH
    payload = _read_json_object(corpus_path)
    version = str(payload.get("version", "")).strip()
    if version != EXPECTED_CORPUS_VERSION:
        raise CorpusStateError(
            f"guidance behavior corpus version must be `{EXPECTED_CORPUS_VERSION}`; got `{version or '<empty>'}`",
            path=corpus_path,
        )
    contract = str(payload.get("contract", "")).strip()
    if contract != CONTRACT:
        raise CorpusStateError(
            f"guidance behavior corpus contract must be `{CONTRACT}`; got `{contract or '<empty>'}`",
            path=corpus_path,
        )
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CorpusStateError("guidance behavior corpus must contain a non-empty `cases` list", path=corpus_path)
    normalized: list[dict[str, Any]] = []
    issues: list[GuidanceIssue] = []
    seen: set[str] = set()
    for index, raw_case in enumerate(cases, start=1):
        if not isinstance(raw_case, Mapping):
            issues.append(GuidanceIssue("case_type", f"case {index} must be a JSON object"))
            continue
        case = dict(raw_case)
        issues.extend(_validate_case_shape(case, index=index))
        case_id = str(case.get("id", "")).strip()
        if case_id:
            if case_id in seen:
                issues.append(GuidanceIssue("case_duplicate_id", f"duplicate case id `{case_id}`", case_id=case_id))
            seen.add(case_id)
        normalized.append(case)
    if issues:
        raise CorpusStateError("; ".join(issue.message for issue in issues), path=corpus_path)
    return normalized


def _select_cases(cases: Sequence[Mapping[str, Any]], *, case_ids: Sequence[str]) -> tuple[list[dict[str, Any]], list[GuidanceIssue]]:
    selected_ids = [str(case_id).strip() for case_id in case_ids if str(case_id).strip()]
    if not selected_ids:
        return [dict(case) for case in cases], []
    by_id = {str(case.get("id", "")).strip(): dict(case) for case in cases if str(case.get("id", "")).strip()}
    missing = [case_id for case_id in selected_ids if case_id not in by_id]
    if missing:
        return [], [
            GuidanceIssue(
                "case_selection",
                f"unknown guidance behavior case id(s): {', '.join(sorted(missing))}",
            )
        ]
    return [by_id[case_id] for case_id in selected_ids], []


def _read_text(repo_root: Path, relative_path: str) -> str:
    path = repo_root / relative_path
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _contains_all(text: str, tokens: Sequence[str]) -> bool:
    lowered = text.lower()
    return all(token.lower() in lowered for token in tokens)


def _frontmatter_description(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:20]:
        stripped = line.strip()
        if stripped == "---":
            return ""
        if stripped.startswith("description:"):
            return stripped.split(":", 1)[1].strip().strip('"')
    return ""


def _iter_agent_skill_shims(repo_root: Path) -> list[Path]:
    roots = [
        repo_root / ".agents" / "skills",
        repo_root / "src" / "odylith" / "bundle" / "assets" / "project-root" / ".agents" / "skills",
    ]
    paths: list[Path] = []
    for root in roots:
        if root.is_dir():
            paths.extend(sorted(path for path in root.glob("*/SKILL.md") if path.is_file()))
    return paths


def _relative_path(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _check_skill_descriptions(repo_root: Path) -> dict[str, Any]:
    failures: list[GuidanceIssue] = []
    checked = 0
    for path in _iter_agent_skill_shims(repo_root):
        checked += 1
        description = _frontmatter_description(path.read_text(encoding="utf-8"))
        lowered = description.lower()
        if not description:
            failures.append(
                GuidanceIssue(
                    "skill_description_trigger_only",
                    "skill shim is missing a frontmatter description",
                    path=_relative_path(repo_root, path),
                )
            )
            continue
        trigger_framed = any(token in lowered for token in ("use when", "when ", "asks", "needs", "requires", "after "))
        if not trigger_framed:
            failures.append(
                GuidanceIssue(
                    "skill_description_trigger_only",
                    "skill description must describe trigger conditions rather than only summarizing the workflow",
                    path=_relative_path(repo_root, path),
                )
            )
    return {
        "id": "skill_description_trigger_only",
        "status": "passed" if not failures else "failed",
        "checked": checked,
        "failures": [failure.as_dict() for failure in failures],
    }


def _check_text_contract(
    repo_root: Path,
    *,
    check_id: str,
    paths: Sequence[str],
    tokens: Sequence[str],
    message: str,
) -> dict[str, Any]:
    failures: list[GuidanceIssue] = []
    evidence: list[str] = []
    for relative_path in paths:
        text = _read_text(repo_root, relative_path)
        if not text:
            failures.append(
                GuidanceIssue(
                    check_id,
                    f"required guidance file is missing: {relative_path}",
                    path=relative_path,
                )
            )
            continue
        if not _contains_all(text, tokens):
            failures.append(GuidanceIssue(check_id, message, path=relative_path))
        else:
            evidence.append(relative_path)
    return {
        "id": check_id,
        "status": "passed" if not failures else "failed",
        "evidence": evidence,
        "failures": [failure.as_dict() for failure in failures],
    }


def _check_bundle_corpus_mirror(repo_root: Path) -> dict[str, Any]:
    source = repo_root / CORPUS_RELATIVE_PATH
    mirror = repo_root / BUNDLE_CORPUS_RELATIVE_PATH
    failures: list[GuidanceIssue] = []
    if not mirror.is_file():
        failures.append(
            GuidanceIssue(
                "guidance_behavior_bundle_mirror",
                "guidance behavior corpus bundle mirror is missing",
                path=str(BUNDLE_CORPUS_RELATIVE_PATH),
            )
        )
    elif source.read_text(encoding="utf-8") != mirror.read_text(encoding="utf-8"):
        failures.append(
            GuidanceIssue(
                "guidance_behavior_bundle_mirror",
                "guidance behavior corpus bundle mirror is stale",
                path=str(BUNDLE_CORPUS_RELATIVE_PATH),
            )
        )
    return {
        "id": "guidance_behavior_bundle_mirror",
        "status": "passed" if not failures else "failed",
        "evidence": [str(CORPUS_RELATIVE_PATH), str(BUNDLE_CORPUS_RELATIVE_PATH)] if not failures else [],
        "failures": [failure.as_dict() for failure in failures],
    }


def _guidance_checks(repo_root: Path, *, cases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        _check_skill_descriptions(repo_root),
        _check_bundle_corpus_mirror(repo_root),
        guidance_behavior_benchmark_contracts.validate_benchmark_family_integration(
            repo_root=repo_root,
            cases=cases,
            expected_family=EXPECTED_FAMILY,
            corpus_relative_path=CORPUS_RELATIVE_PATH,
            benchmark_corpus_relative_path=BENCHMARK_CORPUS_RELATIVE_PATH,
            bundle_benchmark_corpus_relative_path=BUNDLE_BENCHMARK_CORPUS_RELATIVE_PATH,
        ),
        guidance_behavior_runtime_contracts.validate_runtime_layer_contracts(repo_root=repo_root),
        guidance_behavior_guidance_contracts.validate_guidance_surface_contracts(repo_root=repo_root),
        guidance_behavior_platform_contracts.validate_platform_contracts(repo_root=repo_root),
        _check_text_contract(
            repo_root,
            check_id="cli_first_governed_truth",
            paths=("AGENTS.md", "odylith/AGENTS.md", "src/odylith/bundle/assets/odylith/AGENTS.md"),
            tokens=("CLI-first", "hand-edit governed files", "odylith backlog create"),
            message="governed truth guidance must point to CLI-first paths where a CLI exists",
        ),
        _check_text_contract(
            repo_root,
            check_id="fresh_proof_completion_claims",
            paths=("odylith/AGENTS.md", "src/odylith/bundle/assets/odylith/AGENTS.md"),
            tokens=("fixed", "cleared", "resolved", "hosted proof moved past the prior failing phase"),
            message="completion guidance must require fresh proof before fixed/cleared/resolved claims",
        ),
        _check_text_contract(
            repo_root,
            check_id="bounded_subagent_prompt_contract",
            paths=("odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md",),
            tokens=("explicit owner", "goal", "expected output", "termination condition", "validation commands"),
            message="subagent prompt contract must carry owner, goal, output, termination, and validation expectations",
        ),
        _check_text_contract(
            repo_root,
            check_id="queue_non_adoption",
            paths=("AGENTS.md", "odylith/AGENTS.md", "src/odylith/bundle/assets/odylith/AGENTS.md"),
            tokens=("Queued backlog items", "not implicit implementation instructions", "explicitly asks"),
            message="queue guidance must prevent queued records from becoming implicit implementation work",
        ),
        _check_text_contract(
            repo_root,
            check_id="visible_intervention_proof",
            paths=("AGENTS.md", "odylith/AGENTS.md", "src/odylith/bundle/assets/odylith/AGENTS.md"),
            tokens=("intervention-status", "visible-intervention", "show that Markdown directly"),
            message="visible intervention claims must require status proof or a directly rendered fallback",
        ),
    ]


def _case_result(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(case.get("id", "")).strip(),
        "family": str(case.get("family", "")).strip(),
        "severity": str(case.get("severity", "")).strip(),
        "status": "passed",
        "required_evidence": list(case.get("required_evidence", [])),
    }


def validate_guidance_behavior(*, repo_root: Path, case_ids: Sequence[str] = ()) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve()
    payload: dict[str, Any] = {
        "contract": CONTRACT,
        "status": "passed",
        "repo_root": str(root),
        "corpus_path": str(root / CORPUS_RELATIVE_PATH),
        "selected_case_ids": [],
        "case_count": 0,
        "critical_or_high_case_count": 0,
        "severity_counts": {},
        "case_results": [],
        "check_count": 0,
        "failed_check_ids": [],
        "guidance_checks": [],
        "errors": [],
    }
    try:
        cases = load_guidance_behavior_cases(repo_root=root)
    except CorpusStateError as exc:
        payload["status"] = exc.status
        payload["errors"] = [
            {
                "check_id": "corpus_state",
                "message": str(exc),
                "path": str(exc.path or root / CORPUS_RELATIVE_PATH),
            }
        ]
        return payload
    selected_cases, selection_errors = _select_cases(cases, case_ids=case_ids)
    if selection_errors:
        payload["status"] = "malformed"
        payload["errors"] = [issue.as_dict() for issue in selection_errors]
        return payload
    checks = _guidance_checks(root, cases=selected_cases)
    check_failures = [
        failure
        for check in checks
        for failure in check.get("failures", [])
        if isinstance(failure, Mapping)
    ]
    payload["selected_case_ids"] = [str(case.get("id", "")).strip() for case in selected_cases]
    payload["case_count"] = len(selected_cases)
    severity_counts: dict[str, int] = {}
    for case in selected_cases:
        severity = str(case.get("severity", "")).strip().lower()
        if severity:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
    payload["severity_counts"] = dict(sorted(severity_counts.items()))
    payload["critical_or_high_case_count"] = int(severity_counts.get("critical", 0) or 0) + int(
        severity_counts.get("high", 0) or 0
    )
    payload["case_results"] = [_case_result(case) for case in selected_cases]
    payload["check_count"] = len(checks)
    payload["guidance_checks"] = checks
    if check_failures:
        payload["status"] = "failed"
        payload["errors"] = [dict(failure) for failure in check_failures]
        payload["failed_check_ids"] = sorted(
            {
                str(failure.get("check_id", "")).strip()
                for failure in check_failures
                if str(failure.get("check_id", "")).strip()
            }
        )
    return payload


def _exit_code_for_status(status: str) -> int:
    if status == "passed":
        return 0
    if status in {"unavailable", "malformed"}:
        return 1
    return 2


def _print_text(payload: Mapping[str, Any]) -> None:
    status = str(payload.get("status", "")).strip()
    if status == "passed":
        print("guidance behavior validation OK")
        print(f"- cases checked: {int(payload.get('case_count', 0) or 0)}")
        print(f"- guidance checks: {len(payload.get('guidance_checks', []) or [])}")
        return
    if status in {"unavailable", "malformed"}:
        print("guidance behavior validation UNAVAILABLE")
    else:
        print("guidance behavior validation FAILED")
    for raw_error in payload.get("errors", []) or []:
        if not isinstance(raw_error, Mapping):
            continue
        path = str(raw_error.get("path", "")).strip()
        suffix = f" ({path})" if path else ""
        print(f"- {raw_error.get('check_id', 'error')}: {raw_error.get('message', '')}{suffix}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = validate_guidance_behavior(
        repo_root=Path(str(args.repo_root)).expanduser().resolve(),
        case_ids=list(args.case_id or []),
    )
    if bool(args.as_json):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_text(payload)
    return _exit_code_for_status(str(payload.get("status", "")).strip())


if __name__ == "__main__":
    raise SystemExit(main())
