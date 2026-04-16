"""CLI backend for `odylith bug capture` — create a Casebook bug record.

Creates a new bug file in `odylith/casebook/bugs/` with a properly assigned
CB-### ID, rebuilds `INDEX.md` from markdown source, and rerenders the
Casebook surface so the new bug is immediately visible.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence as SequenceABC
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.governance import casebook_source_validation
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance import sync_casebook_bug_index

_CASEBOOK_BUGS_RELATIVE = Path("odylith/casebook/bugs")
_BUG_ID_RE = re.compile(r"^CB-(\d{3,})$")
_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")
_SEVERITY_RE = re.compile(r"^P[0-5]$", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(
    r"^(?:tbd|todo|unknown|n/?a|pending|to be determined|not yet known|not yet determined)(?:\b|[^A-Za-z0-9].*)?$",
    re.IGNORECASE,
)
_CAPTURE_CONTRACT = "fail_closed_minimum_evidence_v1"
_REPRODUCIBILITY_HELP = casebook_source_validation.REPRODUCIBILITY_HELP
_REQUIRED_FIELD_SPECS: tuple[tuple[str, str], ...] = (
    ("reproducibility", "Reproducibility"),
    ("impact", "Impact"),
    ("environment", "Environment(s)"),
    ("detected_by", "Detected By"),
    ("failure_signature", "Failure Signature"),
    ("trigger_path", "Trigger Path"),
    ("ownership", "Ownership"),
    ("blast_radius", "Blast Radius"),
    ("slo_sla_impact", "SLO/SLA Impact"),
    ("data_risk", "Data Risk"),
    ("security_compliance", "Security/Compliance"),
    ("invariant_violated", "Invariant Violated"),
)
_OPTIONAL_FIELD_SPECS: tuple[tuple[str, str], ...] = (
    ("workaround", "Workaround"),
    ("root_cause", "Root Cause"),
    ("solution", "Solution"),
    ("rollback_forward_fix", "Rollback/Forward Fix"),
    ("verification", "Verification"),
    ("prevention", "Prevention"),
    ("agent_guardrails", "Agent Guardrails"),
    ("preflight_checks", "Preflight Checks"),
    ("regression_tests_added", "Regression Tests Added"),
    ("monitoring_updates", "Monitoring Updates"),
    ("version_build", "Version/Build"),
    ("config_flags", "Config/Flags"),
    ("customer_comms", "Customer Comms"),
    ("related_incidents_bugs", "Related Incidents/Bugs"),
    ("code_references", "Code References"),
    ("runbook_references", "Runbook References"),
    ("fix_commit_pr", "Fix Commit/PR"),
)


def _slugify(value: str) -> str:
    token = _SLUGIFY_RE.sub("-", str(value or "").strip().lower()).strip("-")
    return token[:80] if token else "bug"


@dataclass(frozen=True)
class CreatedBug:
    bug_id: str
    title: str
    bug_path: Path
    severity: str
    component: str
    capture_contract: str = _CAPTURE_CONTRACT

    def as_dict(self) -> dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "title": self.title,
            "bug_path": str(self.bug_path),
            "severity": self.severity,
            "component": self.component,
            "capture_contract": self.capture_contract,
        }


def _refresh_casebook_surface(*, repo_root: Path) -> int:
    return owned_surface_refresh.refresh_owned_surface(repo_root=repo_root, surface="casebook")


def _next_bug_id(bugs_dir: Path) -> str:
    """Scan existing bug files and return the next CB-### ID."""
    max_id = 0
    if not bugs_dir.is_dir():
        return "CB-001"
    try:
        for entry in bugs_dir.iterdir():
            if not entry.is_file() or entry.suffix != ".md":
                continue
            try:
                text = entry.read_text(encoding="utf-8")
            except OSError:
                continue
            for line in text.splitlines()[:5]:
                stripped = line.strip().lstrip("- ").strip()
                if stripped.startswith("Bug ID:"):
                    token = stripped.split(":", 1)[1].strip()
                    match = _BUG_ID_RE.fullmatch(token)
                    if match:
                        max_id = max(max_id, int(match.group(1)))
    except OSError:
        pass
    return f"CB-{max_id + 1:03d}"


def _normalize_capture_value(value: str | Sequence[str] | None) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        rows = [str(item).strip() for item in value if str(item).strip()]
        return "\n".join(rows).strip()
    return str(value).strip()


def _normalize_payload_scalar(field_name: str, value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="ignore").strip()
    if isinstance(value, MappingABC):
        raise ValueError(
            f"`{field_name}` must be a single grounded string value, not an object payload"
        )
    if isinstance(value, SequenceABC):
        raise ValueError(
            f"`{field_name}` must be a single grounded string value, not a list payload"
        )
    return str(value).strip()


def _normalize_reference_values(field_name: str, value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        token = value.strip()
        return (token,) if token else ()
    if isinstance(value, (bytes, bytearray)):
        token = value.decode("utf-8", errors="ignore").strip()
        return (token,) if token else ()
    if isinstance(value, MappingABC):
        raise ValueError(
            f"`{field_name}` must be a grounded string or sequence of strings, not an object payload"
        )
    if isinstance(value, SequenceABC):
        rows = [str(item).strip() for item in value if str(item).strip()]
        return tuple(rows)
    token = str(value).strip()
    return (token,) if token else ()


def _field_looks_placeholder(value: str) -> bool:
    token = str(value or "").strip()
    if not token:
        return False
    return _PLACEHOLDER_RE.fullmatch(token) is not None


def _normalize_reproducibility_token(value: str | Sequence[str] | None) -> str:
    return casebook_source_validation.normalize_reproducibility_token(value)


def _reproducibility_token_is_valid(value: str | Sequence[str] | None) -> bool:
    return casebook_source_validation.reproducibility_token_is_valid(value)


def missing_capture_requirements(
    *,
    title: str,
    component: str,
    payload: Mapping[str, Any] | None,
) -> list[str]:
    rows: list[str] = []
    if not _normalize_capture_value(title) or _field_looks_placeholder(title):
        rows.append("title")
    if not _normalize_capture_value(component) or _field_looks_placeholder(component):
        rows.append("component")
    mapping = dict(payload or {})
    for arg_name, _field_label in _REQUIRED_FIELD_SPECS:
        try:
            value = _normalize_payload_scalar(arg_name, mapping.get(arg_name, ""))
        except ValueError:
            value = ""
        if not value or _field_looks_placeholder(value):
            rows.append(arg_name)
        elif arg_name == "reproducibility" and not _reproducibility_token_is_valid(value):
            rows.append(arg_name)
    return rows


def _normalize_multiline_reference(*, field_name: str, values: Any) -> str:
    rows = list(_normalize_reference_values(field_name, values))
    if not rows:
        return ""
    return "\n".join(f"- {row}" for row in rows)


def _validate_capture_inputs(
    *,
    title: str,
    component: str,
    severity: str,
    description: str,
    bug_type: str,
    required_fields: dict[str, str],
    optional_fields: dict[str, str],
) -> tuple[str, str, str, str, dict[str, str], dict[str, str]]:
    normalized_title = _normalize_capture_value(title)
    normalized_component = _normalize_capture_value(component)
    normalized_severity = _normalize_capture_value(severity).upper()
    normalized_description = _normalize_capture_value(description) or normalized_title
    normalized_type = _normalize_capture_value(bug_type) or "Product"

    errors: list[str] = []
    if not normalized_title or _field_looks_placeholder(normalized_title):
        errors.append("`--title` must be a grounded non-placeholder bug title")
    if not normalized_component or _field_looks_placeholder(normalized_component):
        errors.append("`--component` must identify the affected component or boundary")
    if not _SEVERITY_RE.fullmatch(normalized_severity):
        errors.append("`--severity` must be one of P0 through P5")
    if _field_looks_placeholder(normalized_description):
        errors.append("`--description` cannot be a placeholder value")
    if _field_looks_placeholder(normalized_type):
        errors.append("`--type` cannot be a placeholder value")

    missing_flags: list[str] = []
    placeholder_flags: list[str] = []
    cleaned_required: dict[str, str] = {}
    for arg_name, _field_label in _REQUIRED_FIELD_SPECS:
        value = _normalize_capture_value(required_fields.get(arg_name, ""))
        if not value:
            missing_flags.append(f"--{arg_name.replace('_', '-')}")
            continue
        if _field_looks_placeholder(value):
            placeholder_flags.append(f"--{arg_name.replace('_', '-')}")
            continue
        if arg_name == "reproducibility":
            if not _reproducibility_token_is_valid(value):
                errors.append(
                    "`--reproducibility` must be "
                    + _REPRODUCIBILITY_HELP
                    + "; put repro steps in `--trigger-path`, `--failure-signature`, "
                    "or `--environment`"
                )
                continue
            cleaned_required[arg_name] = _normalize_reproducibility_token(value)
            continue
        cleaned_required[arg_name] = value

    cleaned_optional: dict[str, str] = {}
    timeline_value = _normalize_capture_value(optional_fields.get("timeline", ""))
    if timeline_value:
        if _field_looks_placeholder(timeline_value):
            placeholder_flags.append("--timeline")
        else:
            cleaned_optional["timeline"] = timeline_value
    for arg_name, _field_label in _OPTIONAL_FIELD_SPECS:
        value = _normalize_capture_value(optional_fields.get(arg_name, ""))
        if not value:
            continue
        if _field_looks_placeholder(value):
            placeholder_flags.append(f"--{arg_name.replace('_', '-')}")
            continue
        cleaned_optional[arg_name] = value

    if missing_flags:
        errors.append(
            "missing grounded capture fields: " + ", ".join(sorted(missing_flags))
        )
    if placeholder_flags:
        errors.append(
            "placeholder-like values are not allowed for: " + ", ".join(sorted(set(placeholder_flags)))
        )
    if errors:
        raise ValueError(
            "odylith bug capture requires grounded evidence before writing Casebook truth; "
            + "; ".join(errors)
        )

    return (
        normalized_title,
        normalized_component,
        normalized_severity,
        normalized_description,
        normalized_type,
        cleaned_required,
        cleaned_optional,
    )


def _render_bug_field_lines(name: str, value: str) -> list[str]:
    token = _normalize_capture_value(value)
    if not token:
        return []
    lines = token.splitlines()
    rendered = [f"- {name}: {lines[0]}"]
    rendered.extend(line.rstrip() for line in lines[1:])
    rendered.append("")
    return rendered


def _build_bug_text(
    *,
    bug_id: str,
    title: str,
    description: str,
    severity: str,
    component: str,
    bug_type: str,
    today: dt.date,
    required_fields: dict[str, str],
    optional_fields: dict[str, str],
) -> str:
    timeline = optional_fields.get("timeline", "") or f"Captured {today.isoformat()} through `odylith bug capture`."
    lines: list[str] = []
    lines.extend(_render_bug_field_lines("Bug ID", bug_id))
    lines.extend(_render_bug_field_lines("Status", "Open"))
    lines.extend(_render_bug_field_lines("Created", today.isoformat()))
    lines.extend(_render_bug_field_lines("Severity", severity))
    lines.extend(_render_bug_field_lines("Reproducibility", required_fields["reproducibility"]))
    lines.extend(_render_bug_field_lines("Type", bug_type))
    lines.extend(_render_bug_field_lines("Description", description or title))
    lines.extend(_render_bug_field_lines("Impact", required_fields["impact"]))
    lines.extend(_render_bug_field_lines("Components Affected", component))
    lines.extend(_render_bug_field_lines("Environment(s)", required_fields["environment"]))
    lines.extend(_render_bug_field_lines("Detected By", required_fields["detected_by"]))
    lines.extend(_render_bug_field_lines("Failure Signature", required_fields["failure_signature"]))
    lines.extend(_render_bug_field_lines("Trigger Path", required_fields["trigger_path"]))
    lines.extend(_render_bug_field_lines("Ownership", required_fields["ownership"]))
    lines.extend(_render_bug_field_lines("Timeline", timeline))
    lines.extend(_render_bug_field_lines("Blast Radius", required_fields["blast_radius"]))
    lines.extend(_render_bug_field_lines("SLO/SLA Impact", required_fields["slo_sla_impact"]))
    lines.extend(_render_bug_field_lines("Data Risk", required_fields["data_risk"]))
    lines.extend(_render_bug_field_lines("Security/Compliance", required_fields["security_compliance"]))
    lines.extend(_render_bug_field_lines("Invariant Violated", required_fields["invariant_violated"]))
    for arg_name, field_label in _OPTIONAL_FIELD_SPECS:
        if arg_name == "timeline":
            continue
        value = optional_fields.get(arg_name, "")
        if value:
            lines.extend(_render_bug_field_lines(field_label, value))
    return "\n".join(lines).rstrip() + "\n"


def capture_bug(
    *,
    repo_root: Path,
    title: str,
    component: str,
    severity: str,
    reproducibility: str,
    impact: str,
    environment: str,
    detected_by: str,
    failure_signature: str,
    trigger_path: str,
    ownership: str,
    blast_radius: str,
    slo_sla_impact: str,
    data_risk: str,
    security_compliance: str,
    invariant_violated: str,
    description: str = "",
    bug_type: str = "Product",
    timeline: str = "",
    workaround: str = "",
    root_cause: str = "",
    solution: str = "",
    rollback_forward_fix: str = "",
    verification: str = "",
    prevention: str = "",
    agent_guardrails: str = "",
    preflight_checks: str = "",
    regression_tests_added: str = "",
    monitoring_updates: str = "",
    version_build: str = "",
    config_flags: str = "",
    customer_comms: str = "",
    related_incidents_bugs: str = "",
    code_references: Sequence[str] = (),
    runbook_references: Sequence[str] = (),
    fix_commit_pr: str = "",
    dry_run: bool = False,
) -> CreatedBug:
    """Create a new bug record in Casebook and refresh the Casebook surface."""
    bugs_dir = (repo_root / _CASEBOOK_BUGS_RELATIVE).resolve()
    today = dt.datetime.now(tz=dt.UTC).date()

    bug_id = _next_bug_id(bugs_dir)
    slug = _slugify(title)
    filename = f"{today.isoformat()}-{slug}.md"
    bug_path = bugs_dir / filename

    # Avoid collision
    suffix = 2
    while bug_path.exists():
        filename = f"{today.isoformat()}-{slug}-{suffix}.md"
        bug_path = bugs_dir / filename
        suffix += 1

    (
        normalized_title,
        normalized_component,
        normalized_severity,
        normalized_description,
        normalized_type,
        cleaned_required,
        cleaned_optional,
    ) = _validate_capture_inputs(
        title=title,
        component=component,
        severity=severity,
        description=description,
        bug_type=bug_type,
        required_fields={
            "reproducibility": reproducibility,
            "impact": impact,
            "environment": environment,
            "detected_by": detected_by,
            "failure_signature": failure_signature,
            "trigger_path": trigger_path,
            "ownership": ownership,
            "blast_radius": blast_radius,
            "slo_sla_impact": slo_sla_impact,
            "data_risk": data_risk,
            "security_compliance": security_compliance,
            "invariant_violated": invariant_violated,
        },
        optional_fields={
            "timeline": timeline,
            "workaround": workaround,
            "root_cause": root_cause,
            "solution": solution,
            "rollback_forward_fix": rollback_forward_fix,
            "verification": verification,
            "prevention": prevention,
            "agent_guardrails": agent_guardrails,
            "preflight_checks": preflight_checks,
            "regression_tests_added": regression_tests_added,
            "monitoring_updates": monitoring_updates,
            "version_build": version_build,
            "config_flags": config_flags,
            "customer_comms": customer_comms,
            "related_incidents_bugs": related_incidents_bugs,
            "code_references": _normalize_multiline_reference(
                field_name="code_references",
                values=code_references,
            ),
            "runbook_references": _normalize_multiline_reference(
                field_name="runbook_references",
                values=runbook_references,
            ),
            "fix_commit_pr": fix_commit_pr,
        },
    )

    bug_text = _build_bug_text(
        bug_id=bug_id,
        title=normalized_title,
        description=normalized_description,
        severity=normalized_severity,
        component=normalized_component,
        bug_type=normalized_type,
        today=today,
        required_fields=cleaned_required,
        optional_fields=cleaned_optional,
    )

    created_bug = CreatedBug(
        bug_id=bug_id,
        title=normalized_title,
        bug_path=bug_path,
        severity=normalized_severity,
        component=normalized_component,
    )

    if not dry_run:
        validation = casebook_source_validation.validate_casebook_sources(repo_root=repo_root)
        if not validation.passed:
            first_issue = validation.issues[0]
            raise RuntimeError(
                "Casebook source validation failed before bug capture; "
                f"{first_issue.render(repo_root=validation.repo_root)}. "
                "Run `odylith casebook validate --repo-root .` before writing new Casebook truth."
            )
        bugs_dir.mkdir(parents=True, exist_ok=True)
        bug_path.write_text(bug_text, encoding="utf-8")
        sync_casebook_bug_index.sync_casebook_bug_index(
            repo_root=repo_root,
            migrate_bug_ids=False,
        )
        refresh_rc = _refresh_casebook_surface(repo_root=repo_root)
        if refresh_rc != 0:
            raise RuntimeError(
                "Bug record captured but Casebook-only refresh failed; "
                f"bug_id={created_bug.bug_id} path={created_bug.bug_path}. "
                "Retry with `./.odylith/bin/odylith casebook refresh --repo-root .`."
            )

    return created_bug


def capture_bug_from_payload(
    *,
    repo_root: Path,
    title: str,
    component: str,
    severity: str,
    payload: Mapping[str, Any] | None,
    dry_run: bool = False,
) -> CreatedBug:
    mapping = dict(payload or {})
    return capture_bug(
        repo_root=repo_root,
        title=title,
        component=component,
        severity=severity,
        reproducibility=_normalize_payload_scalar("reproducibility", mapping.get("reproducibility", "")),
        impact=_normalize_payload_scalar("impact", mapping.get("impact", "")),
        environment=_normalize_payload_scalar("environment", mapping.get("environment", "")),
        detected_by=_normalize_payload_scalar("detected_by", mapping.get("detected_by", "")),
        failure_signature=_normalize_payload_scalar("failure_signature", mapping.get("failure_signature", "")),
        trigger_path=_normalize_payload_scalar("trigger_path", mapping.get("trigger_path", "")),
        ownership=_normalize_payload_scalar("ownership", mapping.get("ownership", "")),
        blast_radius=_normalize_payload_scalar("blast_radius", mapping.get("blast_radius", "")),
        slo_sla_impact=_normalize_payload_scalar("slo_sla_impact", mapping.get("slo_sla_impact", "")),
        data_risk=_normalize_payload_scalar("data_risk", mapping.get("data_risk", "")),
        security_compliance=_normalize_payload_scalar("security_compliance", mapping.get("security_compliance", "")),
        invariant_violated=_normalize_payload_scalar("invariant_violated", mapping.get("invariant_violated", "")),
        description=_normalize_payload_scalar("description", mapping.get("description", "")),
        bug_type=_normalize_payload_scalar("bug_type", mapping.get("bug_type", ""))
        or _normalize_payload_scalar("type", mapping.get("type", ""))
        or "Product",
        timeline=_normalize_payload_scalar("timeline", mapping.get("timeline", "")),
        workaround=_normalize_payload_scalar("workaround", mapping.get("workaround", "")),
        root_cause=_normalize_payload_scalar("root_cause", mapping.get("root_cause", "")),
        solution=_normalize_payload_scalar("solution", mapping.get("solution", "")),
        rollback_forward_fix=_normalize_payload_scalar(
            "rollback_forward_fix",
            mapping.get("rollback_forward_fix", ""),
        ),
        verification=_normalize_payload_scalar("verification", mapping.get("verification", "")),
        prevention=_normalize_payload_scalar("prevention", mapping.get("prevention", "")),
        agent_guardrails=_normalize_payload_scalar("agent_guardrails", mapping.get("agent_guardrails", "")),
        preflight_checks=_normalize_payload_scalar("preflight_checks", mapping.get("preflight_checks", "")),
        regression_tests_added=_normalize_payload_scalar(
            "regression_tests_added",
            mapping.get("regression_tests_added", ""),
        ),
        monitoring_updates=_normalize_payload_scalar(
            "monitoring_updates",
            mapping.get("monitoring_updates", ""),
        ),
        version_build=_normalize_payload_scalar("version_build", mapping.get("version_build", "")),
        config_flags=_normalize_payload_scalar("config_flags", mapping.get("config_flags", "")),
        customer_comms=_normalize_payload_scalar("customer_comms", mapping.get("customer_comms", "")),
        related_incidents_bugs=_normalize_payload_scalar(
            "related_incidents_bugs",
            mapping.get("related_incidents_bugs", ""),
        ),
        code_references=_normalize_reference_values("code_references", mapping.get("code_references")),
        runbook_references=_normalize_reference_values("runbook_references", mapping.get("runbook_references")),
        fix_commit_pr=_normalize_payload_scalar("fix_commit_pr", mapping.get("fix_commit_pr", "")),
        dry_run=dry_run,
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith bug capture",
        description="Capture a new bug record in the Odylith Casebook.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--title", required=True, help="Bug title.")
    parser.add_argument("--description", default="", help="Detailed bug description. Defaults to the title.")
    parser.add_argument("--component", required=True, help="Affected component ID or boundary.")
    parser.add_argument("--severity", default="P2", help="Severity (P0-P5, default P2).")
    parser.add_argument("--type", dest="bug_type", default="Product", help="Bug type label.")
    parser.add_argument(
        "--reproducibility",
        required=True,
        help=f"How consistently the bug reproduces; use {_REPRODUCIBILITY_HELP}.",
    )
    parser.add_argument("--impact", required=True, help="User or operator impact of the failure.")
    parser.add_argument("--environment", required=True, help="Environment or posture where the bug was observed.")
    parser.add_argument("--detected-by", required=True, help="How the bug was detected.")
    parser.add_argument("--failure-signature", required=True, help="Concrete failure signature.")
    parser.add_argument("--trigger-path", required=True, help="Command or workflow path that triggers the bug.")
    parser.add_argument("--ownership", required=True, help="Owning product surface or team boundary.")
    parser.add_argument("--blast-radius", required=True, help="Scope of affected operators or surfaces.")
    parser.add_argument("--slo-impact", dest="slo_sla_impact", required=True, help="SLO/SLA or delivery impact.")
    parser.add_argument("--data-risk", required=True, help="Data-risk posture for the bug.")
    parser.add_argument("--security-compliance", required=True, help="Security or compliance posture for the bug.")
    parser.add_argument("--invariant-violated", required=True, help="Invariant the bug breaks.")
    parser.add_argument("--timeline", default="", help="Optional detailed capture timeline.")
    parser.add_argument("--workaround", default="", help="Known workaround, if any.")
    parser.add_argument("--root-cause", default="", help="Known root cause, if already understood.")
    parser.add_argument("--solution", default="", help="Known or intended solution.")
    parser.add_argument("--rollback-forward-fix", default="", help="Rollback or forward-fix posture.")
    parser.add_argument("--verification", default="", help="How to verify the fix or current diagnosis.")
    parser.add_argument("--prevention", default="", help="How recurrence should be prevented.")
    parser.add_argument("--agent-guardrails", default="", help="Agent guardrails learned from the failure.")
    parser.add_argument("--preflight-checks", default="", help="Required preflight checks before re-entry.")
    parser.add_argument("--regression-tests-added", default="", help="Regression tests that prove the fix.")
    parser.add_argument("--monitoring-updates", default="", help="Monitoring or alerting updates tied to the bug.")
    parser.add_argument("--version-build", default="", help="Version or build context.")
    parser.add_argument("--config-flags", default="", help="Relevant config or flag posture.")
    parser.add_argument("--customer-comms", default="", help="Customer communication posture, if any.")
    parser.add_argument("--related-incidents-bugs", default="", help="Related incident or bug references.")
    parser.add_argument("--code-reference", action="append", default=[], help="Code reference to include. Repeatable.")
    parser.add_argument("--runbook-reference", action="append", default=[], help="Runbook reference to include. Repeatable.")
    parser.add_argument("--fix-commit-pr", default="", help="Fix commit or PR reference, if known.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()

    try:
        result = capture_bug(
            repo_root=repo_root,
            title=str(args.title).strip(),
            component=str(args.component).strip(),
            severity=str(args.severity).strip(),
            description=str(args.description).strip(),
            bug_type=str(args.bug_type).strip(),
            reproducibility=str(args.reproducibility).strip(),
            impact=str(args.impact).strip(),
            environment=str(args.environment).strip(),
            detected_by=str(args.detected_by).strip(),
            failure_signature=str(args.failure_signature).strip(),
            trigger_path=str(args.trigger_path).strip(),
            ownership=str(args.ownership).strip(),
            blast_radius=str(args.blast_radius).strip(),
            slo_sla_impact=str(args.slo_sla_impact).strip(),
            data_risk=str(args.data_risk).strip(),
            security_compliance=str(args.security_compliance).strip(),
            invariant_violated=str(args.invariant_violated).strip(),
            timeline=str(args.timeline).strip(),
            workaround=str(args.workaround).strip(),
            root_cause=str(args.root_cause).strip(),
            solution=str(args.solution).strip(),
            rollback_forward_fix=str(args.rollback_forward_fix).strip(),
            verification=str(args.verification).strip(),
            prevention=str(args.prevention).strip(),
            agent_guardrails=str(args.agent_guardrails).strip(),
            preflight_checks=str(args.preflight_checks).strip(),
            regression_tests_added=str(args.regression_tests_added).strip(),
            monitoring_updates=str(args.monitoring_updates).strip(),
            version_build=str(args.version_build).strip(),
            config_flags=str(args.config_flags).strip(),
            customer_comms=str(args.customer_comms).strip(),
            related_incidents_bugs=str(args.related_incidents_bugs).strip(),
            code_references=tuple(args.code_reference),
            runbook_references=tuple(args.runbook_reference),
            fix_commit_pr=str(args.fix_commit_pr).strip(),
            dry_run=bool(args.dry_run),
        )
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 2 if isinstance(exc, ValueError) else 1

    mode = "dry-run" if args.dry_run else "captured"
    if args.as_json:
        print(json.dumps({"mode": mode, **result.as_dict()}, indent=2))
    else:
        print(f"odylith bug capture {mode}")
        print(f"  bug_id: {result.bug_id}")
        print(f"  title: {result.title}")
        print(f"  severity: {result.severity}")
        print(f"  component: {result.component}")
        print(f"  path: {result.bug_path}")
    return 0
