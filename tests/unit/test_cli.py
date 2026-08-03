import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith import cli
from odylith.runtime.common import casebook_metadata
from odylith.runtime.governance import bug_authoring


class _TTYStream:
    def isatty(self) -> bool:
        return True


def _write_casebook_bug(
    path: Path,
    *,
    bug_id: str,
    status: str,
    created: str,
    severity: str,
    components: str,
    reproducibility: str = "High",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"- Bug ID: {bug_id}",
                "",
                f"- Status: {status}",
                "",
                f"- Created: {created}",
                "",
                f"- Severity: {severity}",
                "",
                f"- Reproducibility: {reproducibility}",
                "",
                "- Type: Product",
                "",
                f"- Components Affected: {components}",
                "",
                "- Description: Example bug.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _bug_capture_kwargs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "reproducibility": "High",
        "impact": "Maintainers can publish low-evidence bug truth into Casebook.",
        "environment": "Odylith product repo maintainer mode on branch 2026/freedom/v0.1.11.",
        "detected_by": "Maintainer review of the rendered Casebook detail after `odylith bug capture`.",
        "failure_signature": "A newly captured bug renders literal placeholder intake fields instead of grounded evidence.",
        "trigger_path": "`odylith bug capture --title ...` with only the legacy required flags.",
        "ownership": "casebook bug-authoring contract",
        "blast_radius": "Casebook bug truth, shared agent guidance, and automated casebook-create paths.",
        "slo_sla_impact": "Maintainer release-proof confidence drops because Casebook truth is visibly ungrounded.",
        "data_risk": "Low product-data risk, high governed-memory trust risk.",
        "security_compliance": (
            "Security/compliance posture: no credentials or regulated user data are exposed directly; "
            "policy risk is untrusted AI-agent evidence entering durable Casebook memory."
        ),
        "invariant_violated": "A newly captured bug must not publish placeholder evidence as authoritative Casebook truth.",
    }
    payload.update(overrides)
    return payload


def test_bug_capture_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["bug", "capture", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith bug capture" in output
    assert "--title" in output
    assert "--component" in output
    assert "--severity" in output
    assert "--reproducibility" in output
    assert "--impact" in output
    assert "--failure-signature" in output
    assert "--trigger-path" in output
    assert "--detected-by" in output
    assert "--github-issues" in output
    assert "--github-status" in output
    assert "--fixed-in" in output
    assert "--public-response" in output
    assert "--dry-run" in output
    assert "--json" in output


def test_turn_gate_decide_cli_emits_product_receipt(tmp_path: Path, capsys) -> None:
    command = "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_turn_gate.py"
    payload = {
        "prompt": "Verify the bounded contract without editing when evidence already passes.",
        "policy_hints": {
            "non_mutating_closure_allowed": True,
            "focused_checks_cover_contract": True,
        },
        "focused_local_checks": [command],
        "validation_commands": [command],
        "focused_check_result": {
            "status": "passed",
            "results": [{"status": "passed", "command": command}],
        },
    }

    rc = cli.main(
        [
            "turn-gate",
            "decide",
            "--repo-root",
            str(tmp_path),
            "--host",
            "codex",
            "--mode",
            "observe",
            "--prompt-json",
            json.dumps(payload),
            "--json",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert output["decision_type"] == "early_exit_proof"
    assert output["receipt"]["source"] == "product_turn_gate"


def test_github_issue_triage_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["github", "issue", "triage", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith github issue triage" in output
    assert "--apply-governance" in output
    assert "--apply-github" in output
    assert "--repo" in output
    assert "--json" in output


def test_github_issue_pipeline_blocks_consumer_repo_json(tmp_path: Path, capsys) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"consumer\"\n", encoding="utf-8")

    rc = cli.main([
        "github",
        f"--repo-root={tmp_path}",
        "issue",
        "triage",
        "21",
        "--repo",
        "odylith/odylith",
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["repo_role"] == "consumer_repo"
    assert "maintainer-only" in payload["blocked_reason"]
    assert "consumer repos do not run public issue mutation workflows" in payload["blocked_reason"]


def test_plan_help_is_read_only_command_guide(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["plan", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith plan" in output
    assert "Technical-plan writes and checks use the" in output
    assert "odylith governance reconcile-plan-workstream-binding" in output
    assert "odylith validate plan-traceability" in output
    assert "There is no odylith/technical-plans/source/ directory." in output


def test_plan_command_prints_read_only_command_guide(capsys) -> None:
    rc = cli.main(["plan"])

    output = capsys.readouterr().out
    assert rc == 0
    assert "Odylith technical-plan command guide" in output
    assert "`odylith plan` is read-only guidance" in output
    assert "odylith validate plan-risk-mitigation" in output


def test_capabilities_command_prints_host_agnostic_engine_inventory(capsys) -> None:
    rc = cli.main(["capabilities"])

    output = capsys.readouterr().out
    assert rc == 0
    assert "Odylith capabilities and engines" in output
    assert "Host model: agnostic" in output
    assert "Analysis Engine" in output
    assert "Context Engine" in output
    assert "Domain Intelligence" in output
    assert "Governance Engine" in output
    assert "Governed Harness / Turn Gate" in output
    assert "Delivery Intelligence" in output
    assert "Tribunal" in output
    assert "Memory Substrate" in output
    assert "Reasoning Engine" in output
    assert "Surface DAGs" in output
    assert "Topology Integrity" in output
    assert "Taxonomies and FSMs" in output
    assert "Operator Experience" in output
    assert "odylith greenfield compile-transaction" not in output
    assert "odylith greenfield create" in output
    assert "odylith greenfield apply" not in output
    assert "Activation:" in output
    assert "attach the normalized execution handshake" in output
    assert "deterministic proposal gating" in output
    assert "Codex and Claude Code are adapters" in output
    assert "Use `odylith --help` for command syntax." in output


def test_capabilities_command_json_exposes_product_inventory(capsys) -> None:
    rc = cli.main(["capabilities", "--json"])

    payload = json.loads(capsys.readouterr().out)
    names = {
        item["name"]
        for group_key in ("engine_groups", "surface_groups")
        for group in payload[group_key]
        for item in group["items"]
    }
    assert rc == 0
    assert payload["schema"] == "odylith.capability_inventory.v1"
    assert payload["posture"] == "host-model-agnostic"
    assert {
        "Analysis Engine",
        "Context Engine",
        "Domain Intelligence",
        "Governance Engine",
        "Governed Harness / Turn Gate",
        "Delivery Intelligence",
        "Tribunal",
        "Memory Substrate",
        "Reasoning Engine",
        "Surface DAGs",
        "Topology Integrity",
        "Taxonomies and FSMs",
        "Operator Experience",
        "Codex Adapter",
        "Claude Code Adapter",
    } <= names
    context_engine = next(
        item
        for group in payload["engine_groups"]
        for item in group["items"]
        if item["name"] == "Context Engine"
    )
    assert "activation" in context_engine
    assert "execution handshakes" in context_engine["activation"]


def test_validate_engine_integrity_command_is_exposed(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["validate", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "engine-integrity" in output
    assert "Validate Odylith engine inventory" in output


def test_compass_log_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["compass", "log", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith compass log" in output
    assert "--kind" in output
    assert "--summary" in output
    assert "--workstream" in output
    assert "--artifact" in output


def test_backlog_create_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["backlog", "create", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith backlog create" in output
    assert "--title" in output
    assert "--problem" in output
    assert "--customer" in output
    assert "--opportunity" in output
    assert "--product-view" in output
    assert "--success-metrics" in output
    assert "--domain-risk" in output
    assert "--security-posture" in output
    assert "--priority" in output
    assert "--sizing {XS,S,M,L,XL}" in output
    assert "--complexity {Low,Medium,High,VeryHigh}" in output
    assert "--release" in output
    assert "--parent" in output
    assert "--dry-run" in output
    assert "--json" in output


def test_program_create_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["program", "create", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith program create" in output
    assert "umbrella_id" in output
    assert "--dry-run" in output
    assert "--json" in output


def test_wave_create_and_assign_help_forward_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["wave", "create", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith wave create" in output
    assert "umbrella_id" in output
    assert "wave_id" in output
    assert "--label" in output
    assert "--depends-on" in output

    with pytest.raises(SystemExit) as assign_excinfo:
        cli.main(["wave", "assign", "--help"])

    assign_output = capsys.readouterr().out
    assert assign_excinfo.value.code == 0
    assert "usage: odylith wave assign" in assign_output
    assert "workstream_id" in assign_output
    assert "--role" in assign_output
    assert "--adopt" in assign_output


def test_greenfield_propose_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["greenfield", "propose", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith greenfield propose" in output
    assert "--prompt" in output
    assert "--format" in output
    assert "--edit" in output
    assert "--edit-evidence" in output
    assert "--confirm-intent" not in output
    assert "--intent-file" not in output


def test_greenfield_apply_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["greenfield", "apply", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith greenfield apply" in output
    assert "Legacy proposal apply is disabled" in output
    assert "use propose, then hash-bound create" in output
    assert "--proposal-file" in output
    assert "--confirm" in output
    assert "--release" in output


def test_greenfield_create_help_forwards_commit_only_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["greenfield", "create", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith greenfield create" in output
    assert "--confirm" in output
    assert "--transaction-file" in output
    assert "--transaction-hash" in output
    assert "--transaction-json" not in output
    assert "--prompt" not in output
    assert "--intent-file" not in output
    assert "--release" not in output
    assert "--repair-tier" not in output


def test_greenfield_propose_command_is_provider_free(tmp_path: Path, capsys) -> None:
    rc = cli.main(
        [
            "greenfield",
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Build an ecommerce site",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload == {
        "mode": "clarification_required",
        "clarification": {
            "question": "What is the first complete task the product should help a person finish, and what result should they see?",
            "required_fields": ["first_path"],
        },
    }
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()
    assert "provider_calls" not in payload
    assert "host_reasoning_task" not in payload
    assert "backlog" not in payload
    assert "components" not in payload
    assert "diagrams" not in payload


def test_greenfield_propose_confirm_intent_json_is_provider_free(tmp_path: Path, capsys) -> None:
    intent_file = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_file.parent.mkdir(parents=True, exist_ok=True)
    intent_file.write_text(
        """Permit Review Workspace — Product Intent Confirmation

Product story
A city permitting team uses the Permit Review Workspace to review building applications without losing the connection between submitted documents, zoning checks, applicant revisions, reviewer comments, and final decisions. The product gives coordinators and supervisors one place to see what changed, what still blocks approval, and why a permit decision is defensible.

State object that changes through the first journey
A Permit Review File tracks the active application, submitted documents, zoning check status, applicant revisions, reviewer comments, unresolved blockers, decision state, and evidence supporting each approval or rejection.

First complete path the product should prove before broader scope
A coordinator imports one application, a reviewer records a zoning check, the applicant submits one revision, and a supervisor reviews the decision package.

Human actors
- Coordinator — intakes applications, keeps review work moving, and routes blockers to the right reviewer.
- Zoning reviewer — records zoning checks, code references, comments, and pass or block outcomes.
- Applicant — submits revised documents that respond to reviewer comments and unresolved blockers.
- Supervisor — reviews the decision package and approves, blocks, or rejects the permit.

External systems
- Document portal — supplies application documents.
- Parcel data source — supplies zoning context.

Internal product systems
- Permit file registry — owns permit identity, applicant metadata, active submitted documents, unresolved blockers, and decision state.
- Zoning check ledger — records zoning checks, reviewer comments, rule references, and pass or block outcomes.
- Revision tracker — links applicant revisions to the documents, comments, and checks they are meant to address.
- Decision package review — assembles source documents, reviewer evidence, unresolved blockers, supervisor decision, and final approval state.

Proof boundary
Release 0.0.1 succeeds when a supervisor can inspect one permit review file, see the active documents, zoning result, applicant revision, reviewer comments, unresolved blockers, and final decision state, and trace every decision back to source documents and reviewer evidence.
""",
        encoding="utf-8",
    )
    rc = cli.main(
        [
            "greenfield",
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Build a permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm-intent",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["mode"] == "error"
    assert "separate Product Intent confirmation flow is retired" in payload["error"]


def test_component_register_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["component", "register", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith component register" in output
    assert "--id" in output
    assert "--path" in output
    assert "--label" in output
    assert "--kind" in output
    assert "--responsibility" in output
    assert "--risk" in output


def test_atlas_scaffold_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["atlas", "scaffold", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith atlas scaffold" in output
    assert "--diagram-id" in output
    assert "--slug" in output
    assert "--title" in output
    assert "--component" in output


def test_atlas_render_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["atlas", "render", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith atlas render" in output
    assert "Render odylith/atlas/atlas.html from catalog metadata" in output
    assert "Skip current Atlas rerenders" not in output
    assert "--catalog" in output
    assert "--output" in output
    assert "--diagram-id" in output


def test_atlas_auto_update_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["atlas", "auto-update", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith atlas auto-update" in output
    assert "--changed-path" in output
    assert "--from-git-head" in output
    assert "--dry-run" in output


def test_atlas_install_autosync_hook_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["atlas", "install-autosync-hook", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith atlas install-autosync-hook" in output
    assert "--force" in output


def test_governance_intervention_preview_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["governance", "intervention-preview", "--repo-root", ".", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith governance intervention-preview" in output
    assert "--payload-json" in output


def test_governance_capture_apply_help_forwards_backend_flags(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["governance", "capture-apply", "--repo-root", ".", "--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "usage: odylith governance capture-apply" in output
    assert "--payload-json" in output
    assert "--decline" in output


def test_bug_capture_rebuilds_multiline_casebook_index_from_source(tmp_path: Path, monkeypatch) -> None:
    bug_root = tmp_path / "odylith" / "casebook" / "bugs"
    existing_bug = bug_root / "2026-04-12-existing-open-bug.md"
    refresh_calls: list[Path] = []

    monkeypatch.setattr(
        bug_authoring,
        "_refresh_casebook_surface",
        lambda *, repo_root: refresh_calls.append(repo_root) or 0,
    )
    _write_casebook_bug(
        existing_bug,
        bug_id="CB-101",
        status="Open",
        created="2026-04-12",
        severity="P1",
        components=(
            "`src/odylith/runtime/governance/sync_workstream_artifacts.py`,\n"
            "  `src/odylith/runtime/governance/sync_casebook_bug_index.py`"
        ),
    )
    (bug_root / "INDEX.md").write_text(
        "\n".join(
            [
                "# Bug Index",
                "",
                "Last updated (UTC): 2026-04-12",
                "",
                "## Open Bugs",
                "",
                "| Bug ID | Date | Title | Severity | Components | Status | Link |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| CB-101 | 2026-04-12 | Existing open bug | P1 | `src/odylith/runtime/governance/sync_workstream_artifacts.py`,",
                "  `src/odylith/runtime/governance/sync_casebook_bug_index.py` | Open | [2026-04-12-existing-open-bug.md](2026-04-12-existing-open-bug.md) |",
                "",
                "## Closed Bugs",
                "",
                "| Bug ID | Date | Title | Severity | Components | Status | Link |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    created = bug_authoring.capture_bug(
        repo_root=tmp_path,
        title="Fresh Casebook bug capture stays out of multiline rows",
        component="compass",
        severity="P1",
        **_bug_capture_kwargs(),
    )
    index_text = (bug_root / "INDEX.md").read_text(encoding="utf-8")
    created_text = created.bug_path.read_text(encoding="utf-8")

    existing_row = (
        "| CB-101 | 2026-04-12 | Existing open bug | P1 | "
        "`src/odylith/runtime/governance/sync_workstream_artifacts.py`,\n"
        "  `src/odylith/runtime/governance/sync_casebook_bug_index.py` | Open | "
        "[2026-04-12-existing-open-bug.md](2026-04-12-existing-open-bug.md) |"
    )
    assert created.bug_id == "CB-102"
    assert existing_row in index_text
    assert "`src/odylith/runtime/governance/sync_workstream_artifacts.py`,\n| CB-102 |" not in index_text
    assert "## Closed Bugs" in index_text
    assert "TBD" not in created_text
    assert refresh_calls == [tmp_path]


def test_bug_capture_prints_casebook_dashboard_handoff(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        bug_authoring,
        "_refresh_casebook_surface",
        lambda *, repo_root: 0,
    )
    payload = _bug_capture_kwargs()

    rc = bug_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--title",
            "Casebook route should be obvious",
            "--component",
            "casebook",
            "--severity",
            "P2",
            "--reproducibility",
            str(payload["reproducibility"]),
            "--impact",
            str(payload["impact"]),
            "--environment",
            str(payload["environment"]),
            "--detected-by",
            str(payload["detected_by"]),
            "--failure-signature",
            str(payload["failure_signature"]),
            "--trigger-path",
            str(payload["trigger_path"]),
            "--ownership",
            str(payload["ownership"]),
            "--blast-radius",
            str(payload["blast_radius"]),
            "--slo-impact",
            str(payload["slo_sla_impact"]),
            "--data-risk",
            str(payload["data_risk"]),
            "--security-compliance",
            str(payload["security_compliance"]),
            "--invariant-violated",
            str(payload["invariant_violated"]),
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0
    assert "view: odylith/index.html?tab=casebook&bug=CB-001 (reload browser tab if already open)" in output


def test_bug_capture_raises_when_casebook_refresh_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(bug_authoring, "_refresh_casebook_surface", lambda *, repo_root: 1)

    with pytest.raises(RuntimeError, match="Casebook-only refresh failed"):
        bug_authoring.capture_bug(
            repo_root=tmp_path,
            title="Refresh failure should not hide stale Casebook state",
            component="casebook",
            severity="P1",
            **_bug_capture_kwargs(),
        )


def test_bug_capture_rejects_missing_grounded_evidence(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing grounded capture fields: --impact"):
        bug_authoring.capture_bug(
            repo_root=tmp_path,
            title="Low-evidence bug capture should fail closed",
            component="casebook",
            severity="P1",
            **_bug_capture_kwargs(impact=""),
        )


def test_bug_capture_rejects_placeholder_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="placeholder-like values are not allowed"):
        bug_authoring.capture_bug(
            repo_root=tmp_path,
            title="Placeholder values must not pass bug capture",
            component="casebook",
            severity="P1",
            **_bug_capture_kwargs(failure_signature="TBD"),
        )


def test_bug_capture_rejects_sentence_reproducibility(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="`--reproducibility` must be one compact token"):
        bug_authoring.capture_bug(
            repo_root=tmp_path,
            title="Reproducibility must stay compact",
            component="casebook",
            severity="P1",
            **_bug_capture_kwargs(
                reproducibility=(
                    "High; render odylith/index.html and the diagnostic shell block "
                    "appears above dashboard tabs."
                ),
            ),
        )


def test_bug_capture_rejects_prose_type(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="`--type` must be one allowed category token"):
        bug_authoring.capture_bug(
            repo_root=tmp_path,
            title="Casebook type must stay compact",
            component="casebook",
            severity="P1",
            bug_type="UX / lifecycle",
            **_bug_capture_kwargs(),
        )


def test_bug_capture_rejects_status_like_compact_type(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="use `Release` for this value"):
        bug_authoring.capture_bug(
            repo_root=tmp_path,
            title="Casebook type must stay in the controlled enum",
            component="casebook",
            severity="P1",
            bug_type="ForwardFixUpdatedLocallyPendingPlatformReleaseDeploy",
            **_bug_capture_kwargs(),
        )


def test_checked_in_casebook_metadata_fields_are_compact() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    offenders: list[str] = []
    for path in sorted((repo_root / "odylith" / "casebook" / "bugs").rglob("*.md")):
        if path.name in {"AGENTS.md", "CLAUDE.md", "INDEX.md"}:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- Reproducibility:"):
                value = line.split(":", 1)[1].strip()
                if not bug_authoring._reproducibility_token_is_valid(value):  # noqa: SLF001
                    offenders.append(f"{path.relative_to(repo_root)}: Reproducibility={value}")
            if line.startswith("- Status:"):
                value = line.split(":", 1)[1].strip()
                if not casebook_metadata.casebook_token_is_valid(value):
                    offenders.append(f"{path.relative_to(repo_root)}: Status={value}")
            if line.startswith("- Type:"):
                value = line.split(":", 1)[1].strip()
                if not casebook_metadata.casebook_type_is_valid(value):
                    offenders.append(f"{path.relative_to(repo_root)}: Type={value}")
    assert offenders == []


def test_bug_capture_from_payload_accepts_single_string_references(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bug_authoring,
        "_refresh_casebook_surface",
        lambda *, repo_root: 0,
    )

    created = bug_authoring.capture_bug_from_payload(
        repo_root=tmp_path,
        title="Single-string reference payloads stay intact",
        component="casebook",
        severity="P1",
        payload={
            **_bug_capture_kwargs(),
            "code_references": "src/odylith/runtime/governance/bug_authoring.py",
            "runbook_references": "docs/runbooks/casebook-bug-capture.md",
        },
    )

    created_text = created.bug_path.read_text(encoding="utf-8")
    assert "- Code References: - src/odylith/runtime/governance/bug_authoring.py" in created_text
    assert "- Runbook References: - docs/runbooks/casebook-bug-capture.md" in created_text
    assert "- Code References: - s\n- r\n- c" not in created_text


def test_bug_capture_from_payload_rejects_non_scalar_grounded_fields(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="`failure_signature` must be a single grounded string value"):
        bug_authoring.capture_bug_from_payload(
            repo_root=tmp_path,
            title="List-valued scalar evidence must fail closed",
            component="casebook",
            severity="P1",
            payload={
                **_bug_capture_kwargs(),
                "failure_signature": ["wrong", "shape"],
            },
            dry_run=True,
        )


def _seed_product_repo_shape(repo_root: Path) -> None:
    (repo_root / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.0'\n", encoding="utf-8")
    (repo_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Backlog Index\n", encoding="utf-8")
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        json.dumps({"version": "v1", "components": []}) + "\n",
        encoding="utf-8",
    )


def _seed_first_run_surfaces(repo_root: Path) -> None:
    for relative_path in (
        Path("odylith/index.html"),
        Path("odylith/radar/radar.html"),
        Path("odylith/atlas/atlas.html"),
        Path("odylith/compass/compass.html"),
        Path("odylith/registry/registry.html"),
        Path("odylith/casebook/casebook.html"),
    ):
        output_path = repo_root / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("<!doctype html>\n", encoding="utf-8")


def _seed_first_run_surfaces_without_shell(repo_root: Path) -> None:
    for relative_path in (
        Path("odylith/radar/radar.html"),
        Path("odylith/atlas/atlas.html"),
        Path("odylith/compass/compass.html"),
        Path("odylith/registry/registry.html"),
        Path("odylith/casebook/casebook.html"),
    ):
        output_path = repo_root / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("<!doctype html>\n", encoding="utf-8")


def _seed_complete_consumer_install_shape(repo_root: Path, *, version: str = "1.2.3") -> None:
    install_state_path = repo_root / ".odylith" / "install.json"
    install_state_path.parent.mkdir(parents=True, exist_ok=True)
    install_state_path.write_text(json.dumps({"active_version": version}) + "\n", encoding="utf-8")
    pin_path = repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json"
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    pin_path.write_text(json.dumps({"odylith_version": version}) + "\n", encoding="utf-8")
    (repo_root / "odylith" / "AGENTS.md").write_text("# Odylith\n", encoding="utf-8")
    _seed_first_run_surfaces(repo_root)


def test_install_bootstraps_first_run_surfaces_and_reports_agent_workflow(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    sync_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=True,
        ),
    )

    def fail_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        raise AssertionError(f"shell-only refresh should not run while sibling surfaces are missing: {kwargs}")

    def fake_full_sync(argv: list[str]) -> int:
        sync_capture["argv"] = argv
        print("workstream sync impact plan")
        print("- dirty_overlap: bootstrap internals that should stay hidden")
        _seed_first_run_surfaces(tmp_path)
        return 0

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", fail_refresh_dashboard_surfaces)
    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fake_full_sync)

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr()

    assert rc == 0
    assert sync_capture["argv"] == [
        "--repo-root",
        str(tmp_path.resolve()),
        "--force",
        "--impact-mode",
        "full",
        "--proceed-with-overlap",
    ]
    assert "Odylith 1.2.3 is ready" in output.out
    assert "Rendering first-run Odylith surfaces" in output.out
    assert "First-run Odylith surfaces rendered." in output.out
    assert "workstream sync impact plan" not in output.out
    assert "bootstrap internals" not in output.out
    assert "Dashboard:" in output.out
    assert "Added Odylith local-state ignore rules to the root `.gitignore`" in output.out
    assert "Repo-root AGENTS now activates Odylith guidance, skills, and route-ready native delegation candidates" in output.out
    assert "host transport support kept separate from current-session spawn policy" in output.out
    assert "Full Odylith is installed by default." in output.out
    assert "later repairs and upgrades" in output.out
    assert "Odylith is used through an AI coding agent" in output.out
    assert "paste this starter prompt" in output.out
    assert "Starter prompt:" in output.out
    assert cli.shell_onboarding.STARTER_PROMPT in output.out
    assert "use `odylith/index.html` as the first-run Odylith launchpad" in output.out
    assert "doctor --repo-root . --repair" in output.out


def test_hosted_first_install_uses_compact_progress_labels(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"

    monkeypatch.setenv("ODYLITH_INSTALL_COMPACT", "1")
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=True,
            created_guidance_files=("AGENTS.md", "CLAUDE.md"),
            git_repo_present=True,
            gitignore_updated=True,
        ),
    )

    def fake_full_sync(argv: list[str]) -> int:  # noqa: ARG001
        print("workstream sync impact plan")
        print("- dirty_overlap: bootstrap internals that should stay hidden")
        _seed_first_run_surfaces(tmp_path)
        return 0

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fake_full_sync)

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert "write  Adding Odylith files." in output
    assert "draw   Building the dashboard." in output
    assert "done   Dashboard ready." in output
    assert "ready  Odylith 1.2.3 is installed." in output
    assert f"file   {tmp_path / 'odylith' / 'index.html'}" in output
    assert "start  In Codex or Claude Code, ask: Odylith, show me what you can do." in output
    assert "install plan" not in output
    assert "dirty_overlap" not in output
    assert "workstream sync impact plan" not in output
    assert "Created root guidance files" not in output
    assert "Repo-root AGENTS now activates" not in output
    assert "Full Odylith is installed by default" not in output


def test_install_progress_bar_does_not_glue_child_output_to_elapsed_seconds(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_install_progress_bar_enabled", lambda: True)

    with cli._install_progress_bar("write", "Adding Odylith files."):  # noqa: SLF001
        time.sleep(0.02)
        print("mermaid catalog render passed")

    output = capsys.readouterr().out
    assert "smermaid catalog render passed" not in output
    assert "mermaid catalog render passed" in output


def test_compact_install_reports_failure_without_traceback(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("ODYLITH_INSTALL_COMPACT", "1")
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("migration ledger exists, but value-engine verification no longer passes")),
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--no-open"])
    captured = capsys.readouterr()

    assert rc == 2
    assert "write  Adding Odylith files." in captured.out
    assert "stop   Install needs attention." in captured.out
    assert "migration ledger exists, but value-engine verification no longer passes" in captured.err
    assert "Traceback" not in captured.err


def test_first_run_surface_bootstrap_replays_sync_output_on_failure(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    def fake_full_sync(argv: list[str]) -> int:  # noqa: ARG001
        print("workstream sync blocked")
        print("contract failure details", file=sys.stderr)
        return 2

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fake_full_sync)

    rc = cli._bootstrap_first_run_surfaces(  # noqa: SLF001
        repo_root=tmp_path,
        proceed_with_bootstrap_overlap=True,
    )
    output = capsys.readouterr()

    assert rc == 2
    assert "workstream sync blocked" in output.out
    assert "contract failure details" in output.err


def test_compact_existing_install_surface_failure_hides_sync_internals(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True)
    install_state.write_text('{"active_version":"1.2.3"}\n', encoding="utf-8")
    sync_capture: dict[str, object] = {}

    monkeypatch.setenv("ODYLITH_INSTALL_COMPACT", "1")
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=False,
        ),
    )

    def fail_full_sync(argv: list[str]) -> int:
        sync_capture["argv"] = argv
        print("workstream sync plan")
        print("- dirty_overlap: details that compact install must hide")
        print("contract failure details", file=sys.stderr)
        return 17

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fail_full_sync)

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--no-open"])
    captured = capsys.readouterr()

    assert rc == 17
    assert sync_capture["argv"] == [
        "--repo-root",
        str(tmp_path.resolve()),
        "--force",
        "--impact-mode",
        "full",
        "--proceed-with-overlap",
    ]
    assert "write  Adding Odylith files." in captured.out
    assert "draw   Building the dashboard." in captured.out
    assert "workstream sync plan" not in captured.out
    assert "dirty_overlap" not in captured.out
    assert "contract failure details" not in captured.err
    assert "Odylith runtime install succeeded, but the first-run Odylith shell is incomplete." in captured.err
    assert "odylith sync --repo-root . --proceed-with-overlap" in captured.err
    assert "Traceback" not in captured.err


def test_install_opens_dashboard_browser_on_successful_first_install(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.delenv("ODYLITH_NO_BROWSER", raising=False)
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    opened: dict[str, object] = {}
    refresh_capture: dict[str, object] = {}
    _seed_first_run_surfaces_without_shell(tmp_path)

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        refresh_capture.update(kwargs)
        (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", fake_refresh_dashboard_surfaces)
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "main",
        lambda argv: (_ for _ in ()).throw(AssertionError(f"full sync should not run when only shell is missing: {argv}")),
    )
    monkeypatch.setattr(cli, "_interactive_browser_launch_possible", lambda: True)
    monkeypatch.setattr(
        cli.webbrowser,
        "open",
        lambda url, new=0: opened.update({"url": url, "new": new}) or True,
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr()

    assert rc == 0
    assert refresh_capture["repo_root"] == tmp_path.resolve()
    assert refresh_capture["surfaces"] == ("tooling_shell",)
    assert refresh_capture["runtime_mode"] == "auto"
    assert refresh_capture["atlas_sync"] is False
    assert opened["url"] == (tmp_path / "odylith" / "index.html").resolve().as_uri()
    assert opened["new"] == 2
    assert "Opened `odylith/index.html` in your browser." in output.out


def test_install_rematerialize_does_not_auto_acknowledge_surface_overlap(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")
    sync_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )

    def fake_full_sync(argv: list[str]) -> int:
        sync_capture["argv"] = argv
        _seed_first_run_surfaces(tmp_path)
        return 0

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fake_full_sync)

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr()

    assert rc == 0
    assert sync_capture["argv"] == [
        "--repo-root",
        str(tmp_path.resolve()),
        "--force",
        "--impact-mode",
        "full",
    ]
    assert "--proceed-with-overlap" not in sync_capture["argv"]
    assert "Refreshing missing Odylith surfaces" in output.out
    assert "Opened `odylith/index.html` in your browser." not in output.out


def test_install_no_open_flag_suppresses_browser_launch(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces_without_shell(tmp_path)

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        lambda **kwargs: (_seed_first_run_surfaces_without_shell(tmp_path), (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8"), 0)[2],
    )
    monkeypatch.setattr(cli, "_interactive_browser_launch_possible", lambda: True)

    def fail_open(url: str, new: int = 0) -> bool:
        raise AssertionError(f"browser should not open when --no-open is set: {url=} {new=}")

    monkeypatch.setattr(cli.webbrowser, "open", fail_open)

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--no-open"])
    output = capsys.readouterr()

    assert rc == 0
    assert "Opened `odylith/index.html` in your browser." not in output.out


def test_compact_install_env_browser_opt_out_prints_dashboard_path_and_hint(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces_without_shell(tmp_path)
    monkeypatch.setenv("ODYLITH_INSTALL_COMPACT", "1")
    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        lambda **kwargs: (
            _seed_first_run_surfaces_without_shell(tmp_path),
            (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8"),
            0,
        )[2],
    )

    def fail_open(url: str, new: int = 0) -> bool:
        raise AssertionError(f"browser should not open when ODYLITH_NO_BROWSER is set: {url=} {new=}")

    monkeypatch.setattr(cli.webbrowser, "open", fail_open)

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr()

    assert rc == 0
    assert "open   Browser auto-open disabled by ODYLITH_NO_BROWSER." in output.out
    assert f"file   {tmp_path / 'odylith' / 'index.html'}" in output.out
    assert "hint   Run `unset ODYLITH_NO_BROWSER` to auto-open on the next install." in output.out
    assert "Opened `odylith/index.html` in your browser." not in output.out


def test_install_opens_dashboard_browser_on_successful_rematerialize(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.delenv("ODYLITH_NO_BROWSER", raising=False)
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")
    _seed_first_run_surfaces_without_shell(tmp_path)
    opened: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        lambda **kwargs: (_seed_first_run_surfaces_without_shell(tmp_path), (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8"), 0)[2],
    )
    monkeypatch.setattr(cli, "_interactive_browser_launch_possible", lambda: True)
    monkeypatch.setattr(
        cli.webbrowser,
        "open",
        lambda url, new=0: opened.update({"url": url, "new": new}) or True,
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr()

    assert rc == 0
    assert "Odylith is already installed here on 1.2.3." in output.out
    assert opened["url"] == (tmp_path / "odylith" / "index.html").resolve().as_uri()
    assert opened["new"] == 2
    assert "Opened `odylith/index.html` in your browser." in output.out


def test_install_adopt_latest_reinstalls_and_updates_repo_pin(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")
    _seed_first_run_surfaces(tmp_path)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=True,
        ),
    )

    def fake_upgrade_install(
        *,
        repo_root: str,
        release_repo: str,
        version: str,
        source_repo: str | None = None,
        write_pin: bool,
    ) -> SimpleNamespace:
        captured["repo_root"] = repo_root
        captured["release_repo"] = release_repo
        captured["version"] = version
        captured["source_repo"] = source_repo
        captured["write_pin"] = write_pin
        return SimpleNamespace(
            active_version="1.2.4",
            previous_version="1.2.3",
            pinned_version="1.2.4",
            pin_changed=True,
            launcher_path=launcher_path,
            repo_role="consumer_repo",
            followed_latest=True,
            release_tag="v1.2.4",
            release_body="Sharper install messaging.\n\nCleaner shell onboarding.",
            release_highlights=("Sharper install messaging.", "Cleaner shell onboarding."),
            release_published_at="2026-03-30T14:00:00Z",
            release_url="https://example.com/releases/v1.2.4",
        )

    monkeypatch.setattr(cli, "upgrade_install", fake_upgrade_install)
    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", lambda **kwargs: (True, "Dashboard refreshed."))

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--adopt-latest"])
    output = capsys.readouterr()
    spotlight_payload = json.loads(
        (tmp_path / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").read_text(encoding="utf-8")
    )

    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["release_repo"] == "odylith/odylith"
    assert captured["version"] == ""
    assert captured["source_repo"] is None
    assert captured["write_pin"] is True
    assert spotlight_payload["from_version"] == "1.2.3"
    assert spotlight_payload["to_version"] == "1.2.4"
    assert spotlight_payload["release_tag"] == "v1.2.4"
    assert spotlight_payload["highlights"] == ["Sharper install messaging.", "Cleaner shell onboarding."]
    assert "Odylith was reinstalled on the latest verified release: 1.2.4. Repo pin updated to match." in output.out
    assert "This reinstall flow keeps the managed runtime and the tracked repo pin aligned in one step." in output.out
    assert "Dashboard refreshed." in output.out
    assert "odylith-bootstrap doctor --repo-root . --repair" in output.out


def test_install_adopt_latest_keeps_first_install_free_of_upgrade_spotlight(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces(tmp_path)
    cli.write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_body="Stale spotlight payload.",
        highlights=("Should be cleared.",),
    )

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.2",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=False,
        ),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.3",
            previous_version="1.2.2",
            pinned_version="1.2.3",
            pin_changed=True,
            launcher_path=launcher_path,
            repo_role="consumer_repo",
            followed_latest=True,
            release_tag="v1.2.3",
            release_body="Upgrade body.",
            release_highlights=("Upgrade highlight.",),
            release_published_at="2026-03-30T14:00:00Z",
            release_url="https://example.com/releases/v1.2.3",
        ),
    )
    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", lambda **kwargs: (True, "Dashboard refreshed."))

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--adopt-latest", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert not (tmp_path / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").exists()
    assert f"Odylith 1.2.3 is ready in {tmp_path / 'odylith'}." in output
    assert "Dashboard refreshed." in output


def test_install_adopt_latest_clears_stale_upgrade_spotlight_when_no_version_change(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")
    _seed_first_run_surfaces(tmp_path)
    cli.write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_body="Old spotlight payload.",
        highlights=("Old highlight.",),
    )

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=False,
        ),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.3",
            previous_version="1.2.3",
            pinned_version="1.2.3",
            pin_changed=False,
            launcher_path=launcher_path,
            repo_role="consumer_repo",
            followed_latest=True,
            release_tag="",
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", lambda **kwargs: (True, "Dashboard refreshed."))

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--adopt-latest", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert not (tmp_path / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").exists()
    assert "Odylith was reinstalled on the latest verified release: 1.2.3. Repo pin updated to match." in output
    assert "Dashboard refreshed." in output


def test_refresh_dashboard_after_upgrade_reenters_through_fresh_launcher(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    launcher_path = repo_root / ".odylith" / "bin" / "odylith"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text("#!/bin/sh\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):  # noqa: ANN001, ANN003
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="dashboard refresh completed\n", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    refreshed, message = cli._refresh_dashboard_after_upgrade(repo_root=repo_root)  # noqa: SLF001
    output = capsys.readouterr()

    assert refreshed is True
    assert message == "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release."
    assert captured["command"] == [
        str(launcher_path.resolve()),
        "dashboard",
        "refresh",
        "--repo-root",
        str(repo_root),
        "--surfaces",
        "tooling_shell,radar,compass",
        "--force",
    ]
    assert captured["kwargs"] == {
        "cwd": str(repo_root),
        "check": False,
        "capture_output": True,
        "text": True,
    }
    assert "Refreshing Odylith dashboard surfaces so the local shell reflects the new release." in output.out
    assert "dashboard refresh completed" in output.out


def test_refresh_dashboard_after_upgrade_compact_hides_launcher_refresh_plan(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    repo_root = tmp_path / "repo"
    launcher_path = repo_root / ".odylith" / "bin" / "odylith"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(  # noqa: ANN002, ANN003
            returncode=0,
            stdout="dashboard refresh plan\n- stage_timing.complete: 0.1s\ndashboard refresh completed\n",
            stderr="",
        ),
    )

    refreshed, message = cli._refresh_dashboard_after_upgrade(  # noqa: SLF001
        repo_root=repo_root,
        compact_output=True,
    )
    output = capsys.readouterr()

    assert refreshed is True
    assert message == "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release."
    assert "draw   Refreshing dashboard." in output.out
    assert "dashboard refresh plan" not in output.out
    assert "stage_timing" not in output.out


def test_refresh_dashboard_after_upgrade_returns_failure_when_launcher_refresh_fails(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    repo_root = tmp_path / "repo"
    launcher_path = repo_root / ".odylith" / "bin" / "odylith"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(  # noqa: ANN002, ANN003
            returncode=2,
            stdout="dashboard refresh completed\n- outcome: failed\n",
            stderr="compass failed\n",
        ),
    )

    refreshed, message = cli._refresh_dashboard_after_upgrade(repo_root=repo_root)  # noqa: SLF001
    output = capsys.readouterr()

    assert refreshed is False
    assert (
        message
        == "Odylith upgrade succeeded, but dashboard refresh failed. Retry with `./.odylith/bin/odylith dashboard refresh --repo-root . --force`."
    )
    assert "dashboard refresh completed" in output.out
    assert "compass failed" in output.err


def test_refresh_dashboard_after_upgrade_falls_back_to_in_process_refresh_when_launcher_is_missing(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        lambda **kwargs: captured.update(kwargs) or 0,
    )
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should use in-process fallback")),
    )

    refreshed, message = cli._refresh_dashboard_after_upgrade(repo_root=repo_root)  # noqa: SLF001
    output = capsys.readouterr()

    assert refreshed is True
    assert message == "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release."
    assert captured == {
        "repo_root": repo_root,
        "surfaces": ("tooling_shell", "radar", "compass"),
        "runtime_mode": "auto",
        "atlas_sync": False,
        "force": True,
    }
    assert "Refreshing Odylith dashboard surfaces so the local shell reflects the new release." in output.out


def test_install_align_pin_reports_repo_pin_update(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")
    _seed_first_run_surfaces(tmp_path)
    captured: dict[str, object] = {}

    def fake_plan_install_lifecycle(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        captured["plan_kwargs"] = kwargs
        return SimpleNamespace(command="install", headline="preview", steps=(), dirty_overlap=(), notes=())

    def fake_install_bundle(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        captured["install_kwargs"] = kwargs
        return SimpleNamespace(
            version="1.2.4",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            pinned_version="1.2.4",
            pin_changed=True,
        )

    monkeypatch.setattr(cli, "plan_install_lifecycle", fake_plan_install_lifecycle)
    monkeypatch.setattr(cli, "install_bundle", fake_install_bundle)

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--version", "1.2.4", "--align-pin", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["plan_kwargs"] == {
        "repo_root": tmp_path.resolve(),
        "adopt_latest": False,
        "align_pin": True,
        "target_version": "1.2.4",
        "bootstrap_runtime_prestaged": False,
    }
    assert captured["install_kwargs"] == {
        "repo_root": str(tmp_path),
        "bundle_root": cli.bundle_root(),
        "version": "1.2.4",
        "align_pin": True,
    }
    assert "Repo pin updated to 1.2.4." in output


def test_install_refreshes_dashboard_after_repo_state_migration(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces(tmp_path)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "plan_install_lifecycle",
        lambda **kwargs: SimpleNamespace(command="install", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=False,
            migration=SimpleNamespace(
                already_migrated=False,
                moved_paths=("odyssey/ -> odylith/",),
                removed_paths=(),
                stale_reference_audit=None,
            ),
        ),
    )

    def fake_refresh_dashboard_after_upgrade(**kwargs) -> tuple[bool, str]:  # noqa: ANN003
        captured.update(kwargs)
        return True, "Dashboard refreshed."

    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", fake_refresh_dashboard_after_upgrade)

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--version", "1.2.4", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured == {
        "repo_root": tmp_path,
        "compact_output": False,
    }
    assert "Migrated legacy repo roots into the Odylith layout before continuing." in output
    assert "Dashboard refreshed." in output


def test_compact_install_refreshes_dashboard_after_repo_state_migration(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces(tmp_path)
    captured: dict[str, object] = {}

    monkeypatch.setenv("ODYLITH_INSTALL_COMPACT", "1")
    monkeypatch.setenv("ODYLITH_INSTALL_PROGRESS", "0")
    monkeypatch.setattr(
        cli,
        "plan_install_lifecycle",
        lambda **kwargs: SimpleNamespace(command="install", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.4",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=False,
            migration=SimpleNamespace(
                already_migrated=False,
                moved_paths=("odyssey/ -> odylith/",),
                removed_paths=(),
                stale_reference_audit=None,
            ),
        ),
    )

    def fake_refresh_dashboard_after_upgrade(**kwargs) -> tuple[bool, str]:  # noqa: ANN003
        captured.update(kwargs)
        return True, "Dashboard refreshed."

    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", fake_refresh_dashboard_after_upgrade)

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--version", "1.2.4", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured == {
        "repo_root": tmp_path,
        "compact_output": True,
    }
    assert "done   Dashboard ready." in output


def test_install_fallback_preserves_upgrade_spotlight_after_hosted_state_cleanup(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces(tmp_path)
    captured: dict[str, object] = {}

    monkeypatch.setenv("ODYLITH_INSTALL_PREVIOUS_ACTIVE_VERSION", "1.2.3")
    monkeypatch.setattr(
        cli,
        "plan_install_lifecycle",
        lambda **kwargs: SimpleNamespace(command="install", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )

    def fake_install_bundle(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        cli._install_state().write_install_state(
            repo_root=tmp_path,
            payload={
                "active_version": "1.2.4",
                "activation_history": ["1.2.4"],
                "installed_versions": {
                    "1.2.4": {
                        "runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "1.2.4"),
                    }
                },
            },
        )
        return SimpleNamespace(
            version="1.2.4",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
            gitignore_updated=False,
            migration=None,
        )

    def fake_refresh_dashboard_after_upgrade(**kwargs) -> tuple[bool, str]:  # noqa: ANN003
        captured.update(kwargs)
        return True, "Dashboard refreshed."

    monkeypatch.setattr(cli, "install_bundle", fake_install_bundle)
    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", fake_refresh_dashboard_after_upgrade)

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--version", "1.2.4", "--no-open"])
    output = capsys.readouterr().out
    install_state = cli._install_state().load_install_state(repo_root=tmp_path)
    spotlight_payload = json.loads(
        (tmp_path / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").read_text(encoding="utf-8")
    )

    assert rc == 0
    assert install_state["activation_history"] == ["1.2.3", "1.2.4"]
    assert spotlight_payload["from_version"] == "1.2.3"
    assert spotlight_payload["to_version"] == "1.2.4"
    assert spotlight_payload["release_tag"] == "v1.2.4"
    assert spotlight_payload["release_url"] == "https://github.com/odylith/odylith/releases/tag/v1.2.4"
    assert captured == {"repo_root": tmp_path, "compact_output": False}
    assert "Dashboard refreshed." in output


def test_install_existing_complete_repo_routes_through_upgrade_lifecycle(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_complete_consumer_install_shape(tmp_path, version="1.2.3")
    captured: dict[str, object] = {}

    def fake_plan_upgrade_lifecycle(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        captured["plan_kwargs"] = kwargs
        return SimpleNamespace(command="upgrade", headline="preview", steps=(), dirty_overlap=(), notes=(), metadata={})

    def fake_upgrade_install(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        captured["upgrade_kwargs"] = kwargs
        return SimpleNamespace(
            active_version="1.2.4",
            launcher_path=launcher_path,
            pin_changed=True,
            pinned_version="1.2.4",
            previous_version="1.2.3",
            repo_root=tmp_path,
            repo_role="consumer_repo",
            followed_latest=False,
            release_body="",
            release_highlights=("release migrations ran",),
            release_published_at="",
            release_tag="v1.2.4",
            release_url="",
            verification={},
            repaired=False,
            retention_warnings=(),
            migration=None,
            migration_plan={"migration_ids": ["v0.1.14-casebook-status-fsm"]},
            migration_results=({"migration_id": "v0.1.14-casebook-status-fsm", "status": "applied"},),
        )

    monkeypatch.setattr(cli, "plan_upgrade_lifecycle", fake_plan_upgrade_lifecycle)
    monkeypatch.setattr(
        cli,
        "plan_install_lifecycle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("install plan should not run")),
    )
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("install_bundle should not run")),
    )
    monkeypatch.setattr(cli, "upgrade_install", fake_upgrade_install)
    monkeypatch.setattr(cli, "_prepare_consumer_upgrade_spotlight", lambda **kwargs: None)
    monkeypatch.setattr(
        cli,
        "_refresh_dashboard_after_upgrade",
        lambda **kwargs: (True, "Dashboard refreshed."),
    )
    monkeypatch.setattr(cli.upgrade_reporting, "git_status_paths", lambda **kwargs: ())
    monkeypatch.setattr(
        cli.upgrade_reporting,
        "write_generated_change_manifest",
        lambda **kwargs: {"changed": False, "written": False},
    )
    monkeypatch.setattr(
        cli.upgrade_reporting,
        "upgrade_change_review_payload",
        lambda **kwargs: {"categories": {}},
    )
    monkeypatch.setattr(
        cli.upgrade_reporting,
        "write_upgrade_report",
        lambda **kwargs: tmp_path / ".odylith" / "reports" / "upgrade.json",
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--version", "1.2.4", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["plan_kwargs"] == {
        "repo_root": tmp_path.resolve(),
        "version": "1.2.4",
        "release_repo": "odylith/odylith",
        "source_repo": None,
        "write_pin": True,
    }
    assert captured["upgrade_kwargs"] == {
        "repo_root": str(tmp_path),
        "release_repo": "odylith/odylith",
        "version": "1.2.4",
        "source_repo": None,
        "write_pin": True,
    }
    assert "Existing Odylith install detected; routing install through the upgrade lifecycle" in output
    assert "Upgraded Odylith from 1.2.3 to 1.2.4" in output
    assert "Dashboard ready." in output


def test_install_dry_run_existing_complete_repo_previews_upgrade_lifecycle(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    _seed_complete_consumer_install_shape(tmp_path, version="1.2.3")
    captured: dict[str, object] = {}

    def fake_plan_upgrade_lifecycle(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        captured.update(kwargs)
        return SimpleNamespace(command="upgrade", headline="preview", steps=(), dirty_overlap=(), notes=(), metadata={})

    monkeypatch.setattr(cli, "plan_upgrade_lifecycle", fake_plan_upgrade_lifecycle)
    monkeypatch.setattr(
        cli,
        "plan_install_lifecycle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("install plan should not run")),
    )
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("install_bundle should not run")),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("upgrade_install should not run during --dry-run")),
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--version", "1.2.4", "--dry-run"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured == {
        "repo_root": tmp_path.resolve(),
        "version": "1.2.4",
        "release_repo": "odylith/odylith",
        "source_repo": None,
        "write_pin": True,
    }
    assert "upgrade dry-run" in output
    assert "install dry-run" not in output


def test_install_product_repo_shape_does_not_route_through_consumer_upgrade(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    _seed_complete_consumer_install_shape(tmp_path, version="1.2.3")
    _seed_product_repo_shape(tmp_path)
    captured: dict[str, object] = {}

    def fake_plan_install_lifecycle(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        captured.update(kwargs)
        return SimpleNamespace(command="install", headline="preview", steps=(), dirty_overlap=(), notes=())

    monkeypatch.setattr(cli, "plan_install_lifecycle", fake_plan_install_lifecycle)
    monkeypatch.setattr(
        cli,
        "plan_upgrade_lifecycle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("consumer upgrade route should not run")),
    )
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("install_bundle should not run during --dry-run")),
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--version", "1.2.4", "--dry-run"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["repo_root"] == tmp_path.resolve()
    assert captured["target_version"] == "1.2.4"
    assert "install dry-run" in output
    assert "upgrade dry-run" not in output


def test_install_dry_run_passes_bootstrap_runtime_prestaged_env(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_plan_install_lifecycle(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        captured.update(kwargs)
        return SimpleNamespace(command="install", headline="preview", steps=(), dirty_overlap=(), notes=())

    monkeypatch.setenv("ODYLITH_BOOTSTRAP_RUNTIME_PRESTAGED", "1")
    monkeypatch.setattr(cli, "plan_install_lifecycle", fake_plan_install_lifecycle)

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--dry-run"])

    assert rc == 0
    assert captured["bootstrap_runtime_prestaged"] is True


def test_reinstall_defaults_to_latest_verified_release(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    install_state = tmp_path / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True, exist_ok=True)
    install_state.write_text("{}\n", encoding="utf-8")
    _seed_first_run_surfaces(tmp_path)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        cli,
        "reinstall_install",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(
            active_version="1.2.4",
            previous_version="1.2.3",
            pinned_version="1.2.4",
            pin_changed=True,
            launcher_path=launcher_path,
            repaired=False,
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", lambda **kwargs: (True, "Dashboard refreshed."))

    rc = cli.main(["reinstall", "--repo-root", str(tmp_path), "--latest", "--no-open"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["version"] == ""
    assert captured["release_repo"] == "odylith/odylith"
    assert "Reinstalled Odylith from 1.2.3 to 1.2.4 and adopted the verified repo pin." in output
    assert "Repo pin updated to 1.2.4." in output
    assert "Dashboard refreshed." in output
    assert "odylith-bootstrap doctor --repo-root . --repair" in output


def test_install_dry_run_skips_install_bundle(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "plan_install_lifecycle",
        lambda **kwargs: SimpleNamespace(command="install", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("install_bundle should not run during --dry-run")),
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--dry-run"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "install dry-run" in captured


def test_reinstall_dry_run_skips_reinstall_install(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "plan_reinstall_lifecycle",
        lambda **kwargs: SimpleNamespace(command="reinstall", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "reinstall_install",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("reinstall_install should not run during --dry-run")),
    )

    rc = cli.main(["reinstall", "--repo-root", str(tmp_path), "--dry-run"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "reinstall dry-run" in captured


def test_upgrade_dry_run_skips_upgrade_install(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "plan_upgrade_lifecycle",
        lambda **kwargs: SimpleNamespace(command="upgrade", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("upgrade_install should not run during --dry-run")),
    )

    rc = cli.main(["upgrade", "--repo-root", str(tmp_path), "--dry-run"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "upgrade dry-run" in captured


def test_upgrade_dry_run_prints_binding_target_metadata_and_verbose_paths(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    captured: dict[str, object] = {}

    def fake_plan_upgrade_lifecycle(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        captured.update(kwargs)
        return SimpleNamespace(
            command="upgrade",
            headline="Preview the Odylith upgrade lifecycle.",
            metadata={
                "target_version": "1.2.4",
                "target_tag": "v1.2.4",
                "target_relation": "newer_than_active",
                "operation": "mutating",
                "release_repo": "example/odylith",
                "release_url": "https://example.com/releases/v1.2.4",
                "published_at": "2026-04-27T12:00:00Z",
                "verification_policy": "sigstore identity, OIDC issuer, provenance, SBOM, archive safety, and sha256 digest checks",
                "asset_digests": {
                    "odylith-runtime-v1.2.4.tar.gz": "abc123",
                    "release-manifest.json": "def456",
                },
                "rollback_target": "1.2.3",
                "rollback_command": "./.odylith/bin/odylith rollback --repo-root . --previous",
                "rollback_scope": "runtime activation and repo-local launchers",
                "migration_ids": (),
                "migration_ledger": ".odylith/state/migrations/example.json",
            },
            steps=(
                SimpleNamespace(
                    label="Stage the verified managed runtime.",
                    mutation_classes=("runtime_state",),
                    paths=("one", "two", "three", "four", "five"),
                    detail="Target release: v1.2.4.",
                ),
            ),
            dirty_overlap=(),
            notes=(),
        )

    monkeypatch.setattr(cli, "plan_upgrade_lifecycle", fake_plan_upgrade_lifecycle)
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("upgrade_install should not run during --dry-run")),
    )

    rc = cli.main(
        [
            "upgrade",
            "--repo-root",
            str(tmp_path),
            "--release-repo",
            "example/odylith",
            "--dry-run",
            "--verbose",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["release_repo"] == "example/odylith"
    assert "target_version: 1.2.4" in output
    assert "release_url: https://example.com/releases/v1.2.4" in output
    assert "odylith-runtime-v1.2.4.tar.gz: abc123" in output
    assert "rollback_command: ./.odylith/bin/odylith rollback --repo-root . --previous" in output
    assert "paths: one, two, three, four, five" in output
    assert "+1 more" not in output


def test_release_migration_gate_json_reports_registered_runtime(capsys) -> None:
    repo_root = Path(__file__).resolve().parents[2]

    rc = cli.main([
        "release",
        "migration-gate",
            "--repo-root",
            str(repo_root),
            "--target-version",
            "0.1.15",
            "--json",
        ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["schema_version"] == "odylith.release-migration-gate.v1"
    assert payload["fixture_matrix"]["v0.1.11-visible-intervention-value-engine"]["dry_run"] is True
    assert payload["destructive_write_matrix"]["host.claude.preverified-settings"][
        "test_install_bundle_preserves_host_settings_when_runtime_download_fails"
    ] is True
    assert payload["destructive_write_scenarios"]
    assert payload["ungated_lifecycle_paths"] == []
    assert payload["surface_migration_observer"]["schema_version"] == "odylith.surface-migration-observer.v1"
    assert payload["surface_migration_observer"]["ok"] is True


def test_release_group_help_includes_maintainer_commands(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["release", "--help"])

    output = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert "migration-gate" in output
    assert "casebook-closeout" in output


def test_release_migration_gate_blocks_consumer_repo_json(tmp_path: Path, capsys) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"consumer\"\n", encoding="utf-8")

    rc = cli.main([
        "release",
        "migration-gate",
        "--repo-root",
        str(tmp_path),
        "--target-version",
        "0.1.12",
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["repo_role"] == "consumer_repo"
    assert "maintainer-only" in payload["blocked_reason"]
    assert "consumer repos do not run migration-observer guidance or skills" in payload["blocked_reason"]


def test_upgrade_dry_run_json_outputs_binding_plan(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "plan_upgrade_lifecycle",
        lambda **kwargs: SimpleNamespace(
            command="upgrade",
            headline="Already at the resolved verified release; no upgrade mutation is planned.",
            metadata={
                "target_version": "1.2.4",
                "target_tag": "v1.2.4",
                "operation": "no-op",
                "asset_digests": {"release-manifest.json": "abc123"},
                "scenario": "already_current_consumer",
                "migration_plan": {
                    "schema_version": "odylith.migration-plan.v1",
                    "plan_fingerprint": "abc123",
                },
                "ledger_state": {"v0.1.11-visible-intervention-value-engine": "skipped"},
                "blocked_reason": "",
                "plan_fingerprint": "abc123",
            },
            steps=(
                SimpleNamespace(
                    label="No upgrade mutation is planned.",
                    mutation_classes=(),
                    paths=(),
                    detail="Resolved target: v1.2.4.",
                ),
            ),
            dirty_overlap=(),
            notes=("Dry-run is idempotent after a completed upgrade.",),
        ),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("upgrade_install should not run during --dry-run")),
    )

    rc = cli.main(["upgrade", "--repo-root", str(tmp_path), "--dry-run", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["schema"] == "odylith.upgrade.dry_run.v1"
    assert payload["dry_run"] is True
    assert payload["plan"]["metadata"]["target_tag"] == "v1.2.4"
    assert payload["plan"]["metadata"]["operation"] == "no-op"
    assert payload["plan"]["metadata"]["asset_digests"]["release-manifest.json"] == "abc123"
    assert payload["scenario"] == "already_current_consumer"
    assert payload["migration_plan"]["plan_fingerprint"] == "abc123"
    assert payload["ledger_state"]["v0.1.11-visible-intervention-value-engine"] == "skipped"


def test_dashboard_refresh_dispatches_selected_surfaces(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "normalize_dashboard_surfaces",
        lambda values: ["tooling_shell", "radar", "atlas"],
    )

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        fake_refresh_dashboard_surfaces,
    )

    rc = cli.main(
        [
            "dashboard",
            "refresh",
            "--repo-root",
            str(tmp_path),
            "--surfaces",
            "shell,radar,atlas",
            "--atlas-sync",
            "--dry-run",
            "--verbose",
            "--runtime-mode",
            "standalone",
        ]
    )

    assert rc == 0
    assert captured["repo_root"] == tmp_path.resolve()
    assert captured["surfaces"] == ["tooling_shell", "radar", "atlas"]
    assert captured["runtime_mode"] == "standalone"
    assert captured["atlas_sync"] is True
    assert captured["dry_run"] is True
    assert captured["verbose"] is True


def test_dashboard_refresh_defaults_to_tooling_shell_radar_and_compass(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        fake_refresh_dashboard_surfaces,
    )

    rc = cli.main(
        [
            "dashboard",
            "refresh",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
        ]
    )

    assert rc == 0
    assert captured["repo_root"] == tmp_path.resolve()
    assert captured["surfaces"] == ["tooling_shell", "radar", "compass"]
    assert captured["verbose"] is False


def test_dashboard_and_owned_surface_refresh_help_expose_verbose() -> None:
    parser = cli.build_parser()
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)  # noqa: SLF001
    )
    dashboard = subparsers.choices["dashboard"]
    dashboard_subparsers = next(
        action for action in dashboard._actions if isinstance(action, argparse._SubParsersAction)  # noqa: SLF001
    )
    radar = subparsers.choices["radar"]
    radar_subparsers = next(
        action for action in radar._actions if isinstance(action, argparse._SubParsersAction)  # noqa: SLF001
    )

    assert "--verbose" in dashboard_subparsers.choices["refresh"].format_help()
    assert "--verbose" in radar_subparsers.choices["refresh"].format_help()


def test_radar_refresh_dispatches_owned_surface_lane(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        fake_refresh_dashboard_surfaces,
    )

    rc = cli.main(["radar", "refresh", "--repo-root", str(tmp_path), "--dry-run"])

    assert rc == 0
    assert captured == {
        "repo_root": tmp_path.resolve(),
        "surfaces": ("radar",),
        "runtime_mode": "auto",
        "atlas_sync": False,
        "dry_run": True,
        "verbose": False,
        "force": False,
    }


def test_registry_refresh_dispatches_owned_surface_lane(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        fake_refresh_dashboard_surfaces,
    )

    rc = cli.main(["registry", "refresh", "--repo-root", str(tmp_path), "--runtime-mode", "standalone"])

    assert rc == 0
    assert captured == {
        "repo_root": tmp_path.resolve(),
        "surfaces": ("registry",),
        "runtime_mode": "standalone",
        "atlas_sync": False,
        "dry_run": False,
        "verbose": False,
        "force": False,
    }


def test_casebook_refresh_dispatches_owned_surface_lane(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        fake_refresh_dashboard_surfaces,
    )

    rc = cli.main(["casebook", "refresh", "--repo-root", str(tmp_path)])

    assert rc == 0
    assert captured == {
        "repo_root": tmp_path.resolve(),
        "surfaces": ("casebook",),
        "runtime_mode": "auto",
        "atlas_sync": False,
        "dry_run": False,
        "verbose": False,
        "force": False,
    }


def test_atlas_refresh_dispatches_owned_surface_lane(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        fake_refresh_dashboard_surfaces,
    )

    rc = cli.main(["atlas", "refresh", "--repo-root", str(tmp_path), "--atlas-sync"])

    assert rc == 0
    assert captured == {
        "repo_root": tmp_path.resolve(),
        "surfaces": ("atlas",),
        "runtime_mode": "auto",
        "atlas_sync": True,
        "dry_run": False,
        "verbose": False,
        "force": False,
    }


def test_product_repo_main_branch_guard_uses_local_shape_without_install_manager(monkeypatch, tmp_path: Path) -> None:
    _seed_product_repo_shape(tmp_path)
    monkeypatch.setattr(
        cli,
        "product_repo_role",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("install manager role lookup should stay off the hot path")),
    )
    monkeypatch.setattr(cli, "_current_git_branch", lambda **kwargs: "main")

    message = cli._product_repo_main_branch_write_block(repo_root=tmp_path)

    assert "Maintainer authoring on `main` is forbidden in this repo." in message
    assert f"{cli.datetime.now(cli.UTC).year}/freedom/<tag>" in message


def test_backlog_create_dispatches_to_backlog_authoring(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_backlog_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(cli.backlog_authoring, "main", fake_backlog_main)

    rc = cli.main(
        [
            "backlog",
            "create",
            "--repo-root",
            str(tmp_path),
            "--title",
            "Fix backlog authoring",
            "--dry-run",
        ]
    )

    assert rc == 0
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "--title",
        "Fix backlog authoring",
        "--dry-run",
    ]


def test_validate_guidance_portability_dispatches_fast_path(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_validate_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(cli.validate_guidance_portability, "main", fake_validate_main)

    rc = cli.main(["validate", "guidance-portability", "--repo-root", str(tmp_path)])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path)]


def test_validate_guidance_behavior_dispatches_fast_path(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_validate_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(cli.validate_guidance_behavior, "main", fake_validate_main)

    rc = cli.main(
        [
            "validate",
            "guidance-behavior",
            "--repo-root",
            str(tmp_path),
            "--case-id",
            "guidance-a",
            "--json",
        ]
    )

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--case-id", "guidance-a", "--json"]


def test_validate_discipline_dispatches_fast_path(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_validate_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(cli.validate_discipline, "main", fake_validate_main)

    rc = cli.main(
        [
            "validate",
            "discipline",
            "--repo-root",
            str(tmp_path),
            "--case-id",
            "discipline-credit-safe-hot-path",
            "--json",
        ]
    )

    assert rc == 0
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "--case-id",
        "discipline-credit-safe-hot-path",
        "--json",
    ]


def test_discipline_check_dispatches_to_shared_cli(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class _DisciplineModule:
        @staticmethod
        def run_discipline(argv: list[str]) -> int:
            captured["argv"] = list(argv)
            return 7

    real_module_handle = cli._module_handle  # noqa: SLF001
    monkeypatch.setattr(
        cli,
        "_module_handle",
        lambda module_name: _DisciplineModule if module_name == "odylith.runtime.discipline.cli" else real_module_handle(module_name),
    )
    intent = tmp_path / "intent.txt"
    intent.write_text("Say it is fixed now.", encoding="utf-8")

    rc = cli.main(
        [
            "discipline",
            "check",
            "--repo-root",
            str(tmp_path),
            "--intent-file",
            str(intent),
            "--host",
            "codex",
            "--json",
        ]
    )

    assert rc == 7
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "check",
        "--intent-file",
        str(intent),
        "--host",
        "codex",
        "--lane",
        "dev",
        "--json",
    ]


def test_discipline_dispatches_to_shared_discipline_cli(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class _DisciplineModule:
        @staticmethod
        def run_discipline(argv: list[str]) -> int:
            captured["argv"] = list(argv)
            return 9

    real_module_handle = cli._module_handle  # noqa: SLF001
    monkeypatch.setattr(
        cli,
        "_module_handle",
        lambda module_name: _DisciplineModule if module_name == "odylith.runtime.discipline.cli" else real_module_handle(module_name),
    )
    intent = tmp_path / "intent.txt"
    intent.write_text("Say it is fixed now.", encoding="utf-8")

    rc = cli.main(
        [
            "discipline",
            "check",
            "--repo-root",
            str(tmp_path),
            "--intent-file",
            str(intent),
            "--host",
            "claude",
            "--lane",
            "dev-maintainer",
        ]
    )

    assert rc == 9
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "check",
        "--intent-file",
        str(intent),
        "--host",
        "claude",
        "--lane",
        "dev-maintainer",
    ]


def test_discipline_status_and_explain_dispatch_to_shared_cli(monkeypatch, tmp_path: Path) -> None:
    captured: list[list[str]] = []

    class _DisciplineModule:
        @staticmethod
        def run_discipline(argv: list[str]) -> int:
            captured.append(list(argv))
            return 0

    real_module_handle = cli._module_handle  # noqa: SLF001
    monkeypatch.setattr(
        cli,
        "_module_handle",
        lambda module_name: _DisciplineModule if module_name == "odylith.runtime.discipline.cli" else real_module_handle(module_name),
    )

    assert cli.main(["discipline", "status", "--repo-root", str(tmp_path), "--json"]) == 0
    assert cli.main(
        [
            "discipline",
            "explain",
            "--repo-root",
            str(tmp_path),
            "--decision-id",
            "discipline:codex:dev:abc",
            "--json",
        ]
    ) == 0

    assert captured == [
        ["--repo-root", str(tmp_path), "status", "--json"],
        [
            "--repo-root",
            str(tmp_path),
            "explain",
            "--decision-id",
            "discipline:codex:dev:abc",
            "--json",
        ],
    ]


def test_validate_version_truth_dispatches_check_mode(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_validate_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(cli.version_truth, "main", fake_validate_main)

    rc = cli.main(["validate", "version-truth", "--repo-root", str(tmp_path)])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "check"]


def test_interactive_browser_launch_possible_respects_env_opt_out(monkeypatch) -> None:
    monkeypatch.setattr(cli.sys, "stdout", _TTYStream())
    monkeypatch.setattr(cli.sys, "stderr", _TTYStream())
    monkeypatch.setattr(cli.sys, "platform", "darwin")
    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("BUILD_BUILDID", raising=False)
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)

    assert cli._interactive_browser_launch_possible() is False
    assert cli._browser_launch_disabled_message() == "Browser auto-open disabled by ODYLITH_NO_BROWSER."


def test_interactive_browser_launch_possible_blocks_headless_linux(monkeypatch) -> None:
    monkeypatch.setattr(cli.sys, "stdout", _TTYStream())
    monkeypatch.setattr(cli.sys, "stderr", _TTYStream())
    monkeypatch.setattr(cli.sys, "platform", "linux")
    monkeypatch.delenv("ODYLITH_NO_BROWSER", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("BUILD_BUILDID", raising=False)
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.delenv("SSH_CLIENT", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    assert cli._interactive_browser_launch_possible() is False


def test_format_bold_uses_ansi_in_tty(monkeypatch) -> None:
    monkeypatch.setattr(cli.sys, "stdout", _TTYStream())

    assert cli._format_bold("Starter prompt") == "\033[1mStarter prompt\033[0m"


def test_install_reports_created_guidance_and_non_git_caveat(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces_without_shell(tmp_path)

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=True,
            created_guidance_files=("AGENTS.md", "CLAUDE.md"),
            git_repo_present=False,
            gitignore_updated=True,
        ),
    )
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        lambda **kwargs: (_seed_first_run_surfaces_without_shell(tmp_path), (tmp_path / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8"), 0)[2],
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Created root guidance files:" in captured.out
    assert "AGENTS.md" in captured.out
    assert "CLAUDE.md" in captured.out
    assert "Added Odylith local-state ignore rules to the root `.gitignore`" in captured.out
    assert "This folder is not backed by Git yet." in captured.out
    assert "working-tree intelligence, background autospawn, and git-fsmonitor watcher help" in captured.out


def test_install_skips_surface_bootstrap_when_shell_already_exists(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    _seed_first_run_surfaces(tmp_path)

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )

    def fail_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        raise AssertionError(f"dashboard refresh should not run when first-run surfaces already exist: {kwargs}")

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", fail_refresh_dashboard_surfaces)

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Rendering first-run Odylith surfaces" not in captured.out


def test_install_fails_when_first_run_full_sync_fails(monkeypatch, tmp_path: Path, capsys) -> None:
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    sync_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "install_bundle",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3",
            repo_root=tmp_path,
            launcher_path=launcher_path,
            repo_guidance_created=False,
            git_repo_present=True,
        ),
    )

    def fail_refresh_dashboard_surfaces(**kwargs) -> int:  # noqa: ANN003
        raise AssertionError(f"shell-only refresh should not run while sibling surfaces are missing: {kwargs}")

    monkeypatch.setattr(cli.sync_workstream_artifacts, "refresh_dashboard_surfaces", fail_refresh_dashboard_surfaces)

    def fail_full_sync(argv: list[str]) -> int:
        sync_capture["argv"] = argv
        return 17

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fail_full_sync)

    rc = cli.main(["install", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 17
    assert sync_capture["argv"] == [
        "--repo-root",
        str(tmp_path.resolve()),
        "--force",
        "--impact-mode",
        "full",
        "--proceed-with-overlap",
    ]
    assert "Odylith runtime install succeeded, but the first-run Odylith shell is incomplete." in captured.err
    assert "odylith sync --repo-root . --proceed-with-overlap" in captured.err


def test_sync_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 17

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fake_main)
    rc = cli.main(["sync", "--repo-root", str(tmp_path), "--force", "--check-only"])
    assert rc == 17
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--force", "--check-only"]


def test_sync_help_exposes_runtime_controls() -> None:
    parser = cli.build_parser()
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)  # noqa: SLF001
    )
    sync_parser = subparsers.choices["sync"]

    output = sync_parser.format_help()

    assert "--dry-run" in output
    assert "--verbose" in output
    assert "--proceed-with-overlap" in output
    assert "does not yet expose a pure terminal `--json` mode" in output


def test_validate_backlog_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 19

    monkeypatch.setattr(cli.validate_backlog_contract, "main", fake_main)
    rc = cli.main(["validate", "backlog-contract", "--repo-root", str(tmp_path), "--check-only"])
    assert rc == 19
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--check-only"]


def test_validate_component_registry_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 21

    monkeypatch.setattr(cli.validate_component_registry_contract, "main", fake_main)
    rc = cli.main(["validate", "component-registry", "--repo-root", str(tmp_path), "--policy-mode", "advisory"])
    assert rc == 21
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--policy-mode", "advisory"]


def test_validate_component_registry_contract_alias_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 210

    monkeypatch.setattr(cli.validate_component_registry_contract, "main", fake_main)
    rc = cli.main(["validate", "component-registry-contract", "--repo-root", str(tmp_path), "--policy-mode", "advisory"])
    assert rc == 210
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--policy-mode", "advisory"]


def test_validate_plan_risk_mitigation_contract_alias_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 211

    monkeypatch.setattr(cli.validate_plan_risk_mitigation_contract, "main", fake_main)
    rc = cli.main(["validate", "plan-risk-mitigation-contract", "--repo-root", str(tmp_path), "--check-only"])
    assert rc == 211
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--check-only"]


def test_validate_self_host_posture_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 27

    monkeypatch.setattr(cli.validate_self_host_posture, "main", fake_main)
    rc = cli.main(
        [
            "validate",
            "self-host-posture",
            "--repo-root",
            str(tmp_path),
            "--mode",
            "release",
            "--expected-tag",
            "v0.1.0",
        ]
    )
    assert rc == 27
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--mode", "release", "--expected-tag", "v0.1.0"]


def test_governance_backfill_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 22

    monkeypatch.setattr(cli.backfill_workstream_traceability, "main", fake_main)
    rc = cli.main(
        [
            "governance",
            "backfill-workstream-traceability",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
        ]
    )
    assert rc == 22
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--dry-run"]


def test_governance_reconcile_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 24

    monkeypatch.setattr(cli.reconcile_plan_workstream_binding, "main", fake_main)
    rc = cli.main(
        [
            "governance",
            "reconcile-plan-workstream-binding",
            "--repo-root",
            str(tmp_path),
            "odylith/technical-plans/in-progress/example.md",
        ]
    )
    assert rc == 24
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "odylith/technical-plans/in-progress/example.md",
    ]


def test_release_show_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 31

    monkeypatch.setattr(cli.release_planning_authoring, "main", fake_main)
    rc = cli.main(["release", "show", "--repo-root", str(tmp_path), "current", "--json"])

    assert rc == 31
    assert captured["argv"] == ["--repo-root", str(tmp_path), "show", "current", "--json"]


def test_context_engine_help_dispatches_to_context_engine_parser(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 313

    monkeypatch.setattr(cli.odylith_context_engine, "main", fake_main)
    rc = cli.main(["context-engine", "--repo-root", str(tmp_path), "--help"])

    assert rc == 313
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--help"]


def test_benchmark_help_dispatches_to_context_engine_benchmark_parser(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 314

    monkeypatch.setattr(cli.odylith_context_engine, "main", fake_main)
    rc = cli.main(["benchmark", "--repo-root", str(tmp_path), "--help"])

    assert rc == 314
    assert captured["argv"] == ["--repo-root", str(tmp_path), "benchmark", "--help"]


def test_release_list_dispatch_accepts_option_only_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 311

    monkeypatch.setattr(cli.release_planning_authoring, "main", fake_main)
    rc = cli.main(["release", "list", "--repo-root", str(tmp_path), "--json"])

    assert rc == 311
    assert captured["argv"] == ["--repo-root", str(tmp_path), "list", "--json"]


def test_release_show_dispatch_accepts_option_before_positional(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 312

    monkeypatch.setattr(cli.release_planning_authoring, "main", fake_main)
    rc = cli.main(["release", "show", "--repo-root", str(tmp_path), "--json", "current"])

    assert rc == 312
    assert captured["argv"] == ["--repo-root", str(tmp_path), "show", "--json", "current"]


def test_release_mutation_dry_run_skips_main_branch_guard(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "_guard_product_repo_main_branch",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("dry-run release mutation should not hit main-branch guard")),
    )

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 32

    monkeypatch.setattr(cli.release_planning_authoring, "main", fake_main)
    rc = cli.main(["release", "create", "--repo-root", str(tmp_path), "release-1", "--dry-run"])

    assert rc == 32
    assert captured["argv"] == ["--repo-root", str(tmp_path), "create", "release-1", "--dry-run"]


def test_release_mutation_blocks_on_main_branch_before_authoring(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_guard_product_repo_main_branch", lambda **_kwargs: 17)
    monkeypatch.setattr(
        cli.release_planning_authoring,
        "main",
        lambda argv: (_ for _ in ()).throw(AssertionError(f"release authoring should not run when guard blocks: {argv}")),
    )

    rc = cli.main(["release", "create", "--repo-root", str(tmp_path), "release-1"])

    assert rc == 17


def test_program_status_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv: list[str]) -> int:
        captured["argv"] = argv
        return 41

    monkeypatch.setattr(cli.program_wave_authoring, "run_program", fake_run)
    rc = cli.main(["program", "status", "--repo-root", str(tmp_path), "B-201", "--json"])

    assert rc == 41
    assert captured["argv"] == ["--repo-root", str(tmp_path), "status", "B-201", "--json"]


def test_wave_status_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv: list[str]) -> int:
        captured["argv"] = argv
        return 42

    monkeypatch.setattr(cli.program_wave_authoring, "run_wave", fake_run)
    rc = cli.main(["wave", "status", "--repo-root", str(tmp_path), "B-201", "W1", "--json"])

    assert rc == 42
    assert captured["argv"] == ["--repo-root", str(tmp_path), "status", "B-201", "W1", "--json"]


def test_program_mutation_dry_run_skips_main_branch_guard(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "_guard_product_repo_main_branch",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("dry-run program mutation should not hit main-branch guard")),
    )

    def fake_run(argv: list[str]) -> int:
        captured["argv"] = argv
        return 43

    monkeypatch.setattr(cli.program_wave_authoring, "run_program", fake_run)
    rc = cli.main(["program", "create", "--repo-root", str(tmp_path), "B-201", "--dry-run"])

    assert rc == 43
    assert captured["argv"] == ["--repo-root", str(tmp_path), "create", "B-201", "--dry-run"]


def test_wave_mutation_blocks_on_main_branch_before_authoring(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_guard_product_repo_main_branch", lambda **_kwargs: 18)
    monkeypatch.setattr(
        cli.program_wave_authoring,
        "run_wave",
        lambda argv: (_ for _ in ()).throw(AssertionError(f"wave authoring should not run when guard blocks: {argv}")),
    )

    rc = cli.main(["wave", "assign", "--repo-root", str(tmp_path), "B-201", "W1", "B-202"])

    assert rc == 18


def test_governance_sync_component_spec_requirements_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 25

    monkeypatch.setattr(cli.sync_component_spec_requirements, "main", fake_main)
    rc = cli.main(
        [
            "governance",
            "sync-component-spec-requirements",
            "--repo-root",
            str(tmp_path),
            "--component",
            "registry",
        ]
    )
    assert rc == 25
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--component", "registry"]


def test_governance_version_truth_dispatch_accepts_plain_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 251

    monkeypatch.setattr(cli.version_truth, "main", fake_main)
    rc = cli.main(["governance", "version-truth", "--repo-root", str(tmp_path)])
    assert rc == 251
    assert captured["argv"] == ["--repo-root", str(tmp_path), "check"]


def test_governance_validate_guidance_portability_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 252

    monkeypatch.setattr(cli.validate_guidance_portability, "main", fake_main)
    rc = cli.main(["governance", "validate-guidance-portability", "--repo-root", str(tmp_path), "--check-only"])
    assert rc == 252
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--check-only"]


def test_governance_validate_guidance_behavior_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 251

    monkeypatch.setattr(cli.validate_guidance_behavior, "main", fake_main)
    rc = cli.main(["governance", "validate-guidance-behavior", "--repo-root", str(tmp_path), "--case-id", "guidance-a"])
    assert rc == 251
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--case-id", "guidance-a"]


def test_governance_validate_plan_traceability_dispatch_accepts_plain_forwarded_flags(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 253

    monkeypatch.setattr(cli.validate_plan_traceability_contract, "main", fake_main)
    rc = cli.main(["governance", "validate-plan-traceability", "--repo-root", str(tmp_path), "--check-only"])
    assert rc == 253
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--check-only"]


def test_benchmark_dispatch_preserves_argument_order(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 23

    monkeypatch.setattr(cli.odylith_context_engine, "main", fake_main)
    rc = cli.main(["benchmark", "--repo-root", str(tmp_path), "--output", "report.json"])
    assert rc == 23
    assert captured["argv"] == ["--repo-root", str(tmp_path), "benchmark", "--output", "report.json"]


def test_compass_update_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 29

    monkeypatch.setattr(cli.update_compass, "main", fake_main)
    rc = cli.main(["compass", "update", "--repo-root", str(tmp_path), "--statement", "hello"])
    assert rc == 29
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--statement", "hello"]


def test_compass_refresh_dispatch_accepts_structured_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 28

    monkeypatch.setattr(cli.compass_refresh_runtime, "main", fake_main)
    rc = cli.main(
        [
            "compass",
            "refresh",
            "--repo-root",
            str(tmp_path),
            "--runtime-mode",
            "standalone",
            "--wait",
        ]
    )
    assert rc == 28
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "--wait",
        "--runtime-mode",
        "standalone",
    ]


def test_compass_deep_refresh_dispatch_implies_wait(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 28

    monkeypatch.setattr(cli.compass_refresh_runtime, "main", fake_main)
    rc = cli.main(
        [
            "compass",
            "deep-refresh",
            "--repo-root",
            str(tmp_path),
            "--runtime-mode",
            "standalone",
        ]
    )
    assert rc == 28
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "--wait",
        "--runtime-mode",
        "standalone",
    ]


def test_compass_refresh_dispatch_rejects_removed_refresh_profile_flag(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        cli.main(
            [
                "compass",
                "refresh",
                "--repo-root",
                str(tmp_path),
                "--refresh-profile",
                "full",
            ]
        )


def test_compass_restore_history_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 31

    monkeypatch.setattr(cli.restore_compass_history, "main", fake_main)
    rc = cli.main(["compass", "restore-history", "--repo-root", str(tmp_path), "--date", "2026-03-01"])
    assert rc == 31
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--date", "2026-03-01"]


def test_compass_watch_transactions_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 30

    monkeypatch.setattr(cli.watch_prompt_transactions, "main", fake_main)
    rc = cli.main(["compass", "watch-transactions", "--repo-root", str(tmp_path), "--once"])
    assert rc == 30
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--once"]


def test_doctor_uses_bundle_root(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_doctor_bundle(
        *,
        repo_root: str,
        bundle_root: Path,
        repair: bool,
        reset_local_state: bool,
    ) -> tuple[bool, str]:
        captured["repo_root"] = repo_root
        captured["bundle_root"] = bundle_root
        captured["repair"] = repair
        captured["reset_local_state"] = reset_local_state
        return True, "healthy"

    monkeypatch.setattr(cli, "doctor_bundle", fake_doctor_bundle)
    rc = cli.main(["doctor", "--repo-root", str(tmp_path)])
    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["repair"] is False
    assert captured["reset_local_state"] is False
    assert isinstance(captured["bundle_root"], Path)


def test_doctor_passes_reset_local_state(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_doctor_bundle(
        *,
        repo_root: str,
        bundle_root: Path,
        repair: bool,
        reset_local_state: bool,
    ) -> tuple[bool, str]:
        captured["repo_root"] = repo_root
        captured["repair"] = repair
        captured["reset_local_state"] = reset_local_state
        return True, "healthy"

    monkeypatch.setattr(cli, "doctor_bundle", fake_doctor_bundle)
    rc = cli.main(["doctor", "--repo-root", str(tmp_path), "--repair", "--reset-local-state"])
    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["repair"] is True
    assert captured["reset_local_state"] is True


def test_doctor_repair_renders_missing_first_run_surfaces(monkeypatch, tmp_path: Path, capsys) -> None:
    missing_surface = tmp_path / "odylith" / "index.html"
    surface_calls: list[dict[str, object]] = []
    missing_checks = {"count": 0}
    (tmp_path / ".odylith").mkdir()
    (tmp_path / ".odylith" / "install.json").write_text("{}", encoding="utf-8")
    (tmp_path / "odylith").mkdir()

    monkeypatch.setattr(cli, "doctor_bundle", lambda **kwargs: (True, "Odylith repair completed."))
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            runtime_source_detail="",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            runtime_trust_warnings=(),
        ),
    )
    monkeypatch.setattr(cli.upgrade_reporting, "doctor_operational_observability_lines", lambda **kwargs: ())
    monkeypatch.setattr(cli.migration_runtime, "doctor_migration_observability_lines", lambda **kwargs: ())

    def fake_missing_first_run_surfaces(*, repo_root: Path) -> list[Path]:  # noqa: ARG001
        missing_checks["count"] += 1
        return [missing_surface] if missing_checks["count"] == 1 else []

    def fake_bootstrap_first_run_surfaces(*, repo_root: Path, proceed_with_bootstrap_overlap: bool = False) -> int:
        surface_calls.append(
            {
                "repo_root": repo_root,
                "proceed_with_bootstrap_overlap": proceed_with_bootstrap_overlap,
            }
        )
        return 0

    monkeypatch.setattr(cli, "_missing_first_run_surfaces", fake_missing_first_run_surfaces)
    monkeypatch.setattr(cli, "_bootstrap_first_run_surfaces", fake_bootstrap_first_run_surfaces)

    rc = cli.main(["doctor", "--repo-root", str(tmp_path), "--repair"])
    output = capsys.readouterr().out

    assert rc == 0
    assert surface_calls == [
        {
            "repo_root": tmp_path.resolve(),
            "proceed_with_bootstrap_overlap": True,
        }
    ]
    assert "Doctor repair: rendering missing Odylith shell surfaces." in output
    assert "Odylith repair completed." in output


def test_doctor_rejects_reset_without_repair(capsys, tmp_path: Path) -> None:
    rc = cli.main(["doctor", "--repo-root", str(tmp_path), "--reset-local-state"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "--reset-local-state requires --repair." in captured.err


def test_on_uses_set_agents_integration(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_set_agents_integration(*, repo_root: str, enabled: bool) -> tuple[bool, str]:
        captured["repo_root"] = repo_root
        captured["enabled"] = enabled
        return True, "on"

    monkeypatch.setattr(cli, "set_agents_integration", fake_set_agents_integration)
    rc = cli.main(["on", "--repo-root", str(tmp_path)])
    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["enabled"] is True


def test_off_uses_set_agents_integration(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_set_agents_integration(*, repo_root: str, enabled: bool) -> tuple[bool, str]:
        captured["repo_root"] = repo_root
        captured["enabled"] = enabled
        return True, "off"

    monkeypatch.setattr(cli, "set_agents_integration", fake_set_agents_integration)
    rc = cli.main(["off", "--repo-root", str(tmp_path)])
    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert captured["enabled"] is False


def test_uninstall_uses_uninstall_bundle(monkeypatch, tmp_path: Path, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_uninstall_bundle(*, repo_root: str) -> SimpleNamespace:
        captured["repo_root"] = repo_root
        (Path(repo_root) / "odylith").mkdir()
        return SimpleNamespace(removed_paths=(".odylith/",))

    monkeypatch.setattr(cli, "uninstall_bundle", fake_uninstall_bundle)
    rc = cli.main(["uninstall", "--repo-root", str(tmp_path)])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert "Odylith runtime was uninstalled from this repository." in output
    assert "Preserved `odylith/` governed source truth." in output
    assert "Removed `.odylith/` local runtime state." in output
    assert "Detached repo-root Odylith guidance." in output
    assert "Detached Odylith hook entries from Claude/Codex project settings." in output
    assert "Preserved `.claude/`, `.codex/`, and `.agents/` directories" in output


def test_uninstall_help_states_exact_scope(capsys) -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["uninstall", "--help"])
    output = capsys.readouterr().out

    assert raised.value.code == 0
    assert "Remove Odylith's repo-local runtime state" in output
    assert "--dry-run" in output
    assert "removes:   .odylith/ runtime state and launcher files" in output
    assert "detaches:  Odylith hook entries in Claude/Codex project settings" in output
    assert "preserves: odylith/ governed source truth, dashboards, records, and history" in output
    assert "preserves: .claude/, .codex/, and .agents/ host directories" in output
    assert "Do not replace it with rm -rf or Python shutil.rmtree" in output
    assert "Use --dry-run when you only need the scope preview" in output


def test_uninstall_dry_run_prints_scope_without_mutating(monkeypatch, tmp_path: Path, capsys) -> None:
    def fail_uninstall_bundle(*, repo_root: str) -> SimpleNamespace:
        raise AssertionError(f"dry-run must not call uninstall_bundle: {repo_root}")

    monkeypatch.setattr(cli, "uninstall_bundle", fail_uninstall_bundle)
    (tmp_path / ".odylith").mkdir()
    (tmp_path / "odylith").mkdir()
    (tmp_path / ".claude").mkdir()

    rc = cli.main(["uninstall", "--repo-root", str(tmp_path), "--dry-run"])
    output = capsys.readouterr().out

    assert rc == 0
    assert "uninstall plan" in output
    assert f"- repo: {tmp_path.resolve()}" in output
    assert "- removes: .odylith/ runtime state and launcher files" in output
    assert "- detaches: Odylith hook entries in Claude/Codex project settings" in output
    assert "- preserves: odylith/ governed source truth, dashboards, records, and history" in output
    assert "- preserves: .claude/, .codex/, and .agents/ host directories" in output
    assert "- changed: no" in output
    assert "- run: ./.odylith/bin/odylith uninstall --repo-root ." in output
    assert (tmp_path / ".odylith").is_dir()
    assert (tmp_path / "odylith").is_dir()
    assert (tmp_path / ".claude").is_dir()


def test_uninstall_dry_run_reports_product_repo_block(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(cli, "repo_role_from_local_shape", lambda *, repo_root: cli.PRODUCT_REPO_ROLE)
    monkeypatch.setattr(
        cli,
        "uninstall_bundle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("dry-run must not mutate")),
    )

    rc = cli.main(["uninstall", "--repo-root", str(tmp_path), "--dry-run"])
    output = capsys.readouterr().out

    assert rc == 1
    assert "uninstall plan" in output
    assert "- status: blocked" in output
    assert "refusing to uninstall the Odylith product repo's own `odylith/` source tree" in output
    assert "- changed: no" in output


def test_uninstall_reports_refusal_without_traceback(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_uninstall_bundle(*, repo_root: str) -> SimpleNamespace:
        del repo_root
        raise ValueError("refusing to uninstall product repo")

    monkeypatch.setattr(cli, "uninstall_bundle", fake_uninstall_bundle)
    rc = cli.main(["uninstall", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 1
    assert "refusing to uninstall product repo" in captured.err


def test_uninstall_reports_filesystem_failure_without_traceback(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_uninstall_bundle(*, repo_root: str) -> SimpleNamespace:
        del repo_root
        raise OSError("Directory not empty")

    monkeypatch.setattr(cli, "uninstall_bundle", fake_uninstall_bundle)
    rc = cli.main(["uninstall", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 1
    assert "Odylith uninstall could not finish cleanly: Directory not empty" in captured.err
    assert "No traceback was emitted" in captured.err
    assert "Traceback" not in captured.err


def test_on_prints_bootstrap_guidance(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(cli, "set_agents_integration", lambda **kwargs: (True, "on"))

    rc = cli.main(["on", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Repo guidance is active again. Start from the repo-local Odylith entrypoint before default repo-scan behavior." in captured.out
    assert "./.odylith/bin/odylith start --repo-root ." in captured.out
    assert "./.odylith/bin/odylith context --repo-root . <ref>" in captured.out


def test_start_bootstrap_lane_emits_payload(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="bootstrap",
            reason="healthy",
            next_command="./.odylith/bin/odylith start --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "_start_bootstrap_payload",
        lambda args: {
            "packet_kind": "bootstrap_session",
            "narrowing_guidance": {"required": False, "reason": "grounded"},
        },
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "- lane: bootstrap" in captured
    assert "- packet: bootstrap_session" in captured
    assert "- json: rerun with --json for the full bootstrap packet" in captured
    assert '"packet_kind": "bootstrap_session"' not in captured


def test_start_bootstrap_lane_prints_recognized_target(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="bootstrap",
            reason="healthy",
            next_command="./.odylith/bin/odylith start --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "_start_bootstrap_payload",
        lambda args: {
            "packet_kind": "bootstrap_session",
            "narrowing_guidance": {"required": False, "reason": "grounded"},
            "target_resolution": {
                "candidate_targets": [
                    {
                        "path": "src/odylith/runtime/context_engine/new_startup_probe.py",
                        "source": "path_scope",
                        "writable": True,
                    }
                ],
                "has_writable_targets": True,
                "requires_more_consumer_context": False,
            },
        },
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "- target: src/odylith/runtime/context_engine/new_startup_probe.py" in captured
    assert "- packet: bootstrap_session" in captured


def test_start_bootstrap_lane_emits_full_payload_with_json(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="bootstrap",
            reason="healthy",
            next_command="./.odylith/bin/odylith start --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "_start_bootstrap_payload",
        lambda args: {
            "packet_kind": "bootstrap_session",
            "narrowing_guidance": {"required": False, "reason": "grounded"},
        },
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path), "--json"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "- lane: bootstrap" in captured
    assert '"packet_kind": "bootstrap_session"' in captured


def test_start_bootstrap_payload_forwards_turn_context(monkeypatch, tmp_path: Path) -> None:
    from odylith.runtime.common import agent_runtime_contract
    from odylith.runtime.context_engine import odylith_context_engine_packet_session_runtime as packet_session_runtime
    from odylith.runtime.context_engine import runtime_read_session

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        packet_session_runtime,
        "build_session_bootstrap",
        lambda **kwargs: captured.update(
            kwargs,
            read_session_active=runtime_read_session.active_runtime_read_session() is not None,
        )
        or {"packet_kind": "bootstrap_session"},
    )

    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "start",
            "--repo-root",
            str(tmp_path),
            "--intent",
            "Why doesn't this admin panel take full width?",
            "--surface",
            "compass",
            "--visible-text",
            "Current release",
            "--active-tab",
            "releases",
            "--user-turn-id",
            "turn-3",
            "--supersedes-turn-id",
            "turn-2",
        ]
    )

    payload = cli._start_bootstrap_payload(args)

    assert payload == {"packet_kind": "bootstrap_session"}
    assert captured["intent"] == "Why doesn't this admin panel take full width?"
    assert captured["generated_surfaces"] == ["compass"]
    assert captured["visible_text"] == ["Current release"]
    assert captured["active_tab"] == "releases"
    assert captured["user_turn_id"] == "turn-3"
    assert captured["supersedes_turn_id"] == "turn-2"
    assert captured["delivery_profile"] == agent_runtime_contract.AGENT_HOT_PATH_PROFILE
    assert captured["skip_impact_runtime_warmup"] is True
    assert captured["read_session_active"] is True


def test_start_fallback_lane_prints_exact_next_command(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="bootstrap",
            reason="healthy",
            next_command="./.odylith/bin/odylith start --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "_start_bootstrap_payload",
        lambda args: {
            "packet_kind": "bootstrap_session",
            "narrowing_guidance": {
                "required": True,
                "reason": "Need one code path.",
                "next_fallback_command": "rg --files | rg 'src/odylith/cli.py'",
                "next_fallback_followup": "sed -n '1,200p' src/odylith/cli.py",
            },
        },
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 1
    assert "- lane: narrowing" in captured
    assert "- status: needs target" in captured
    assert "Name one code path, workstream, component, bug, or file before implementation." in captured
    assert "- next: rg --files | rg 'src/odylith/cli.py'" in captured
    assert "- followup: sed -n '1,200p' src/odylith/cli.py" in captured
    assert "- lane: bootstrap" not in captured
    assert '"packet_kind": "bootstrap_session"' not in captured
    assert "lane: fallback" not in captured


def test_start_status_only_routes_to_version(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="status",
            reason="status only",
            next_command="./.odylith/bin/odylith version --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            available_versions=["1.2.3"],
        ),
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path), "--status-only"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "- lane: status" in captured
    assert "Runtime interpreter: Odylith is using the managed Odylith Python runtime." in captured


def test_start_install_lane_prints_hosted_installer(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="install",
            reason="not installed",
            next_command="curl -fsSL https://odylith.ai/install.sh | bash",
            healthy=False,
            launcher_exists=False,
            bootstrap_launcher_exists=False,
            install_shape_present=False,
            status=None,
        ),
    )

    rc = cli.main(["start", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 1
    assert "- lane: install" in captured
    assert "curl -fsSL https://odylith.ai/install.sh | bash" in captured


def test_start_bootstrap_exception_prints_repair_guidance(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "evaluate_start_preflight",
        lambda **kwargs: SimpleNamespace(
            lane="bootstrap",
            reason="healthy",
            next_command="./.odylith/bin/odylith start --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=None,
        ),
    )
    monkeypatch.setattr(cli, "_start_bootstrap_payload", lambda args: (_ for _ in ()).throw(RuntimeError("projection cache corrupted")))
    monkeypatch.setattr(cli, "preferred_repair_entrypoint", lambda **kwargs: "./.odylith/bin/odylith doctor --repo-root . --repair")

    rc = cli.main(["start", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 1
    assert "- lane: repair" in captured
    assert "projection cache corrupted" in captured
    assert "- next: ./.odylith/bin/odylith doctor --repo-root . --repair" in captured
    assert "- followup: ./.odylith/bin/odylith bootstrap --repo-root . --no-working-tree" in captured


def test_bootstrap_shortcut_exception_prints_repair_guidance(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "_dispatch_context_engine_shortcut",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("context engine daemon unavailable")),
    )
    monkeypatch.setattr(cli, "preferred_repair_entrypoint", lambda **kwargs: "./.odylith/bin/odylith doctor --repo-root . --repair")

    rc = cli.main(["bootstrap", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 1
    assert "odylith bootstrap" in captured
    assert "context engine daemon unavailable" in captured
    assert "- next: ./.odylith/bin/odylith doctor --repo-root . --repair" in captured
    assert "- followup: ./.odylith/bin/odylith bootstrap --repo-root . --no-working-tree" in captured


def test_version_reports_runtime_toolchain_boundary(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            available_versions=["1.2.3"],
        ),
    )

    rc = cli.main(["version", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "Runtime interpreter: Odylith is using the managed Odylith Python runtime." in captured
    assert "Repo-code validation: use the repo's own project toolchain for application tests, builds, and linting." in captured


def test_version_prints_runtime_detail_when_present(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="product_repo",
            posture="pinned_release",
            runtime_source="wrapped_runtime",
            runtime_source_detail="Managed runtime trust is degraded: managed runtime tree entry unexpected: /tmp/.DS_Store",
            release_eligible=False,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            available_versions=["1.2.3"],
        ),
    )

    rc = cli.main(["version", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "Runtime detail: Managed runtime trust is degraded:" in captured


def test_version_check_upgrade_reports_available_release(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            runtime_source_detail="",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            runtime_trust_warnings=(),
            available_versions=["1.2.3"],
        ),
    )
    monkeypatch.setattr(
        cli,
        "check_for_available_upgrade",
        lambda **kwargs: SimpleNamespace(
            latest_version="1.2.4",
            current_version=kwargs["current_version"],
            release_url="https://github.com/odylith/odylith/releases/tag/v1.2.4",
            from_cache=False,
            next_check_after="",
            disabled=False,
            status="upgrade_available",
            update_available=True,
        ),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_check_lines",
        lambda result, *, explicit=False: (
            f"Upgrade available: Odylith {result.latest_version} (active {result.current_version}). Run `./.odylith/bin/odylith upgrade --repo-root .`.",
            f"Release: {result.release_url}",
        ),
    )

    rc = cli.main(["version", "--repo-root", str(tmp_path), "--check-upgrade"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "Upgrade available: Odylith 1.2.4 (active 1.2.3)." in captured
    assert "Release: https://github.com/odylith/odylith/releases/tag/v1.2.4" in captured


def test_version_without_check_uses_cache_only(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            runtime_source_detail="",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            runtime_trust_warnings=(),
            available_versions=["1.2.3"],
        ),
    )
    monkeypatch.setattr(
        cli,
        "check_for_available_upgrade",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("plain version should not ping remote")),
    )
    monkeypatch.setattr(
        cli,
        "load_cached_upgrade_check",
        lambda **kwargs: SimpleNamespace(
            latest_version="1.2.4",
            current_version=kwargs["current_version"],
            release_url="",
            from_cache=True,
            next_check_after="2026-05-07T00:00:00+00:00",
            disabled=False,
            status="upgrade_available",
            update_available=True,
        ),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_check_lines",
        lambda result, *, explicit=False: (
            f"Upgrade available: Odylith {result.latest_version} (active {result.current_version}). Run `./.odylith/bin/odylith upgrade --repo-root .`.",
        ),
    )

    rc = cli.main(["version", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "Upgrade available: Odylith 1.2.4 (active 1.2.3)." in captured


def test_doctor_prints_trust_degraded_wrapped_runtime_detail(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "doctor_bundle",
        lambda **kwargs: (
            True,
            "Odylith runtime is healthy but trust-degraded and not release-eligible: "
            "Managed runtime trust is degraded: managed runtime tree entry unexpected: /tmp/rogue.txt",
        ),
    )
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="product_repo",
            posture="pinned_release",
            runtime_source="wrapped_runtime",
            runtime_source_detail="Managed runtime trust is degraded: managed runtime tree entry unexpected: /tmp/rogue.txt",
            release_eligible=False,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            available_versions=["1.2.3"],
        ),
    )

    rc = cli.main(["doctor", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "Runtime source: wrapped_runtime" in captured
    assert "Runtime detail: Managed runtime trust is degraded:" in captured
    assert "healthy but trust-degraded" in captured.lower()
    assert "not release-eligible" in captured.lower()


def test_doctor_prints_nonfatal_runtime_trust_warning(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(cli, "doctor_bundle", lambda **kwargs: (True, "Odylith install is healthy."))
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            runtime_source_detail="",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            available_versions=["1.2.3"],
            runtime_trust_warnings=(
                "Sigstore emitted expected non-fatal trust-root warning stream(s), but verification completed successfully.",
            ),
        ),
    )

    rc = cli.main(["doctor", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "Doctor status: healthy with warnings" in captured
    assert "Trust warning: Sigstore emitted expected non-fatal trust-root warning stream(s)" in captured


def test_doctor_prints_last_upgrade_report_and_lock_note(monkeypatch, tmp_path: Path, capsys) -> None:
    report_dir = tmp_path / ".odylith" / "runtime" / "logs"
    report_dir.mkdir(parents=True)
    (report_dir / "upgrade-20260427T120000Z.json").write_text(
        json.dumps(
            {
                "status": "succeeded_with_warnings",
                "finished_at": "2026-04-27T12:01:00+00:00",
                "dashboard_refresh": {
                    "mode": "launcher",
                    "fresh": True,
                    "timeout_detected": True,
                },
                "generated_change_manifest": {
                    "path": "odylith/upgrade-generated-changes.v1.json",
                    "generated_changed_count": 2,
                    "content_fingerprint": "123456abcdef",
                },
            }
        ),
        encoding="utf-8",
    )
    locks_dir = tmp_path / ".odylith" / "locks"
    locks_dir.mkdir(parents=True)
    for index in range(200):
        (locks_dir / f"lock-{index}.lock").touch()
    monkeypatch.setattr(cli, "doctor_bundle", lambda **kwargs: (True, "Odylith install is healthy."))
    monkeypatch.setattr(
        cli,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_root=tmp_path,
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            runtime_source_detail="",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.4",
            active_version="1.2.4",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            available_versions=["1.2.3", "1.2.4"],
        ),
    )

    rc = cli.main(["doctor", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "Last upgrade: succeeded_with_warnings at 2026-04-27T12:01:00+00:00" in captured
    assert "Last upgrade dashboard refresh: mode=launcher; fresh=yes; timeout_detected=yes" in captured
    assert "Last upgrade generated changes: 2 generated path(s); manifest: odylith/upgrade-generated-changes.v1.json; fingerprint=123456abcdef" in captured
    assert "Rollback target: 1.2.3" in captured
    assert "Lock note: 200 zero-byte lock placeholders exist under .odylith/locks" in captured


def test_install_dry_run_condenses_dirty_overlap_without_verbose(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "plan_install_lifecycle",
        lambda **kwargs: SimpleNamespace(
            command="install",
            headline="preview",
            steps=(),
            dirty_overlap=("M one", "M two", "M three", "M four", "M five"),
            notes=(),
        ),
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--dry-run"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "5 local worktree entries overlap this mutation plan." in captured
    assert "By area: other=5." in captured
    assert "... 1 more overlap entries hidden; rerun with --verbose to show the full set." in captured


def test_install_dry_run_verbose_prints_full_dirty_overlap(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "plan_install_lifecycle",
        lambda **kwargs: SimpleNamespace(
            command="install",
            headline="preview",
            steps=(),
            dirty_overlap=("M one", "M two", "M three", "M four", "M five"),
            notes=(),
        ),
    )

    rc = cli.main(["install", "--repo-root", str(tmp_path), "--dry-run", "--verbose"])
    captured = capsys.readouterr().out

    assert rc == 0
    assert "M five" in captured
    assert "hidden; rerun with --verbose" not in captured


def test_off_prints_default_behavior_guidance(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(cli, "set_agents_integration", lambda **kwargs: (True, "off"))

    rc = cli.main(["off", "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "The current coding host falls back to the surrounding repo's default behavior" in captured.out
    assert "./.odylith/bin/odylith on --repo-root ." in captured.out
    assert "runtime and `odylith/` context stay installed" in captured.out


def test_bootstrap_shortcut_defaults_to_clean_first_turn_command(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.odylith_context_engine,
        "main",
        lambda argv: captured.update({"argv": argv}) or 0,
    )

    rc = cli.main(["bootstrap", "--repo-root", str(tmp_path)])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "bootstrap-session", "--working-tree"]


def test_bootstrap_shortcut_forwards_turn_context(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.odylith_context_engine,
        "main",
        lambda argv: captured.update({"argv": argv}) or 0,
    )

    rc = cli.main(
        [
            "bootstrap",
            "--repo-root",
            str(tmp_path),
            "--intent",
            'Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"',
            "--surface",
            "compass",
            "--visible-text",
            "Task Contract, Event Ledger, and Hard-Constraint Promotion",
            "--active-tab",
            "releases",
            "--user-turn-id",
            "turn-2",
            "--supersedes-turn-id",
            "turn-1",
        ]
    )

    assert rc == 0
    assert captured["argv"] == [
        "--repo-root",
        str(tmp_path),
        "bootstrap-session",
        "--working-tree",
        "--intent",
        'Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"',
        "--surface",
        "compass",
        "--visible-text",
        "Task Contract, Event Ledger, and Hard-Constraint Promotion",
        "--active-tab",
        "releases",
        "--user-turn-id",
        "turn-2",
        "--supersedes-turn-id",
        "turn-1",
    ]


def test_context_shortcut_dispatches_to_context_engine(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.odylith_context_engine,
        "main",
        lambda argv: captured.update({"argv": argv}) or 0,
    )

    rc = cli.main(["context", "--repo-root", str(tmp_path), "odylith"])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "context", "odylith"]


def test_query_shortcut_dispatches_to_context_engine(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.odylith_context_engine,
        "main",
        lambda argv: captured.update({"argv": argv}) or 0,
    )

    rc = cli.main(["query", "--repo-root", str(tmp_path), "launchpad"])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "query", "launchpad"]


def test_upgrade_dispatches_to_upgrade_install(monkeypatch, tmp_path: Path, capsys) -> None:
    captured: dict[str, object] = {}
    refresh_capture: dict[str, object] = {}

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True, text=True)
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")

    def fake_upgrade_install(
        *,
        repo_root: str,
        release_repo: str,
        version: str,
        source_repo: str | None,
        write_pin: bool,
    ) -> SimpleNamespace:
        captured["repo_root"] = repo_root
        captured["release_repo"] = release_repo
        captured["version"] = version
        captured["source_repo"] = source_repo
        captured["write_pin"] = write_pin
        return SimpleNamespace(
            active_version="1.2.3",
            launcher_path=Path(repo_root) / ".odylith" / "bin" / "odylith",
            pin_changed=False,
            pinned_version="1.2.3",
            previous_version="1.2.2",
            repo_role="consumer_repo",
            followed_latest=False,
            release_tag="v1.2.3",
            release_body="## Highlights\n\nSharper install messaging.\n\nCleaner shell onboarding.",
            release_highlights=("Sharper install messaging.", "Cleaner shell onboarding."),
            release_published_at="2026-03-28T12:30:00Z",
            release_url="https://example.com/releases/v1.2.3",
        )

    monkeypatch.setattr(
        cli,
        "plan_upgrade_lifecycle",
        lambda **kwargs: SimpleNamespace(command="upgrade", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(cli, "upgrade_install", fake_upgrade_install)

    def fake_refresh_dashboard_after_upgrade(
        *,
        repo_root: Path,
        emit_output: bool = True,
        compact_output: bool = False,
        details: dict[str, object] | None = None,
    ) -> tuple[bool, str]:
        refresh_capture["repo_root"] = repo_root
        refresh_capture["emit_output"] = emit_output
        refresh_capture["compact_output"] = compact_output
        if details is not None:
            details.update({"mode": "launcher", "success": True})
        if emit_output and compact_output:
            print("draw   Refreshing dashboard.")
        elif emit_output:
            print("Refreshing Odylith dashboard surfaces so the local shell reflects the new release.")
        return True, "Dashboard refreshed. Open `odylith/index.html` to see what landed in this release."

    monkeypatch.setattr(
        cli,
        "_refresh_dashboard_after_upgrade",
        fake_refresh_dashboard_after_upgrade,
    )

    rc = cli.main(["upgrade", "--repo-root", str(repo_root), "--to", "1.2.3", "--write-pin"])
    output = capsys.readouterr().out
    spotlight_payload = json.loads((repo_root / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json").read_text(encoding="utf-8"))

    assert rc == 0
    assert captured["repo_root"] == str(repo_root)
    assert captured["release_repo"] == "odylith/odylith"
    assert captured["version"] == "1.2.3"
    assert captured["source_repo"] is None
    assert captured["write_pin"] is True
    assert refresh_capture["repo_root"] == repo_root
    assert refresh_capture["compact_output"] is True
    assert spotlight_payload["from_version"] == "1.2.2"
    assert spotlight_payload["to_version"] == "1.2.3"
    assert spotlight_payload["release_tag"] == "v1.2.3"
    assert spotlight_payload["release_body"] == "## Highlights\n\nSharper install messaging.\n\nCleaner shell onboarding."
    assert spotlight_payload["highlights"] == ["Sharper install messaging.", "Cleaner shell onboarding."]
    assert "move   Preparing the verified Odylith release." in output
    assert "write  Upgraded Odylith from 1.2.2 to 1.2.3." in output
    assert "notes  2 release highlight(s) in the dashboard." in output
    assert "draw   Refreshing dashboard." in output
    assert "done   Dashboard ready." in output
    assert "open   Open odylith/index.html to see what changed." in output
    assert "undo   Rollback: ./.odylith/bin/odylith rollback --repo-root . --previous" in output
    assert "Release: https://example.com/releases/v1.2.3" not in output
    assert "What changed:" not in output
    assert "Refreshing Odylith dashboard surfaces so the local shell reflects the new release." not in output


def test_upgrade_json_writes_auditable_report_and_suppresses_refresh_stdout(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True, text=True)
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "plan_upgrade_lifecycle",
        lambda **kwargs: SimpleNamespace(
            command="upgrade",
            headline="Preview the Odylith upgrade lifecycle.",
            metadata={
                "target_version": "1.2.4",
                "target_tag": "v1.2.4",
                "operation": "mutating",
                "asset_digests": {"release-manifest.json": "abc123"},
                "rollback_target": "1.2.3",
            },
            steps=(
                SimpleNamespace(
                    label="Stage the verified managed runtime.",
                    mutation_classes=("runtime_state",),
                    paths=(".odylith/install.json",),
                    detail="Target release: v1.2.4.",
                ),
            ),
            dirty_overlap=(),
            notes=(),
        ),
    )

    def fake_upgrade_install(**kwargs) -> SimpleNamespace:  # noqa: ANN003
        (repo_root / "odylith").mkdir(exist_ok=True)
        (repo_root / "odylith" / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
        return SimpleNamespace(
            active_version="1.2.4",
            launcher_path=repo_root / ".odylith" / "bin" / "odylith",
            pin_changed=True,
            pinned_version="1.2.4",
            previous_version="1.2.3",
            repo_role="consumer_repo",
            followed_latest=True,
            release_tag="v1.2.4",
            release_body="",
            release_highlights=(),
            release_published_at="2026-04-27T12:00:00Z",
            release_url="https://example.com/releases/v1.2.4",
            verification={"sigstore_warning_count": 1},
            retention_warnings=(),
        )

    monkeypatch.setattr(cli, "upgrade_install", fake_upgrade_install)

    def fake_refresh_dashboard_after_upgrade(
        *,
        repo_root: Path,
        emit_output: bool = True,
        compact_output: bool = False,
        details: dict[str, object] | None = None,
    ) -> tuple[bool, str]:
        assert emit_output is False
        assert compact_output is False
        assert repo_root == tmp_path / "repo"
        if details is not None:
            details.update(
                {
                    "mode": "launcher",
                    "returncode": 0,
                    "timeout_detected": True,
                    "stdout": "shell-safe runtime timed out at 45s; standalone fallback succeeded",
                    "success": True,
                }
            )
        return True, "Dashboard refreshed."

    monkeypatch.setattr(cli, "_refresh_dashboard_after_upgrade", fake_refresh_dashboard_after_upgrade)

    rc = cli.main(["upgrade", "--repo-root", str(repo_root), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["schema"] == "odylith.upgrade.report.v1"
    assert payload["status"] == "succeeded"
    assert payload["final_state"]["active_version"] == "1.2.4"
    assert payload["dashboard_refresh"]["timeout_detected"] is True
    assert payload["generated_change_manifest"]["path"] == "odylith/upgrade-generated-changes.v1.json"
    assert payload["generated_change_manifest"]["generated_changed_count"] == 1
    assert payload["generated_change_manifest"]["entries"][0]["path"] == "odylith/index.html"
    assert payload["plan"]["metadata"]["asset_digests"]["release-manifest.json"] == "abc123"
    assert "odylith/index.html" in payload["changed_paths"]
    assert "odylith/upgrade-generated-changes.v1.json" in payload["changed_paths"]
    assert Path(payload["report_path"]).is_file()
    assert (repo_root / "odylith" / "upgrade-generated-changes.v1.json").is_file()


def test_migrate_legacy_install_dispatches_to_install_migration(monkeypatch, tmp_path: Path, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_migrate_legacy_install(*, repo_root: str) -> SimpleNamespace:
        captured["repo_root"] = repo_root
        return SimpleNamespace(
            already_migrated=False,
            state_root=tmp_path / ".odylith",
            launcher_path=tmp_path / ".odylith" / "bin" / "odylith",
            moved_paths=("odyssey/ -> odylith/", ".odyssey/ -> .odylith/"),
            removed_paths=(".odylith/runtime/odylith-memory",),
            stale_reference_audit=SimpleNamespace(
                hit_count=2,
                file_count=2,
                sample_paths=("AGENTS.md", "docs/platform-maintainer-guide.md"),
                report_path=tmp_path / ".odylith" / "state" / "migration" / "stale-odyssey-reference-audit.md",
            ),
        )

    monkeypatch.setattr(cli, "migrate_legacy_install", fake_migrate_legacy_install)

    rc = cli.main(["migrate-legacy-install", "--repo-root", str(tmp_path)])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert "Migrated legacy install state into" in output
    assert "odyssey/ -> odylith/" in output
    assert ".odyssey/ -> .odylith/" in output
    assert ".odylith/runtime/odylith-memory" in output
    assert "Stale legacy references audit: 2 match(es) across 2 tracked file(s)." in output
    assert "docs/platform-maintainer-guide.md" in output
    assert "./.odylith/bin/odylith start --repo-root ." in output


def test_upgrade_reports_already_latest_verified_release(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    refresh_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "plan_upgrade_lifecycle",
        lambda **kwargs: SimpleNamespace(command="upgrade", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.3",
            launcher_path=repo_root / ".odylith" / "bin" / "odylith",
            pin_changed=False,
            pinned_version="1.2.3",
            previous_version="1.2.3",
            repo_role="consumer_repo",
            followed_latest=True,
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(
        cli,
        "_refresh_dashboard_after_upgrade",
        lambda **kwargs: refresh_capture.update(kwargs) or (True, "Dashboard refreshed."),
    )

    rc = cli.main(["upgrade", "--repo-root", str(repo_root)])
    output = capsys.readouterr().out

    assert rc == 0
    assert refresh_capture["repo_root"] == repo_root
    assert "write  Already on latest verified release 1.2.3." in output
    assert "done   Dashboard ready." in output
    assert "Repo pin remains 1.2.3." not in output


def test_upgrade_reports_already_on_tracked_self_host_pin(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    refresh_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "plan_upgrade_lifecycle",
        lambda **kwargs: SimpleNamespace(command="upgrade", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.3",
            launcher_path=repo_root / ".odylith" / "bin" / "odylith",
            pin_changed=False,
            pinned_version="1.2.3",
            previous_version="1.2.3",
            repo_role="product_repo",
            followed_latest=False,
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(
        cli,
        "_refresh_dashboard_after_upgrade",
        lambda **kwargs: refresh_capture.update(kwargs) or (True, "Dashboard refreshed."),
    )

    rc = cli.main(["upgrade", "--repo-root", str(repo_root)])
    output = capsys.readouterr().out

    assert rc == 0
    assert refresh_capture["repo_root"] == repo_root
    assert "write  Already on tracked self-host pin 1.2.3." in output
    assert "done   Dashboard ready." in output
    assert "Repo pin remains 1.2.3." not in output


def test_upgrade_refreshes_dashboard_for_product_repo_version_change_without_consumer_popup(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    refresh_capture: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "plan_upgrade_lifecycle",
        lambda **kwargs: SimpleNamespace(command="upgrade", headline="preview", steps=(), dirty_overlap=(), notes=()),
    )
    monkeypatch.setattr(
        cli,
        "upgrade_install",
        lambda **kwargs: SimpleNamespace(
            active_version="1.2.4",
            launcher_path=repo_root / ".odylith" / "bin" / "odylith",
            pin_changed=False,
            pinned_version="1.2.4",
            previous_version="1.2.3",
            repo_role="product_repo",
            followed_latest=False,
            release_tag="v1.2.4",
            release_body="",
            release_highlights=(),
            release_published_at="",
            release_url="",
        ),
    )
    monkeypatch.setattr(
        cli,
        "_refresh_dashboard_after_upgrade",
        lambda **kwargs: refresh_capture.update(kwargs) or (True, "Dashboard refreshed."),
    )

    rc = cli.main(["upgrade", "--repo-root", str(repo_root), "--to", "1.2.4"])
    output = capsys.readouterr().out

    assert rc == 0
    assert refresh_capture["repo_root"] == repo_root
    assert "write  Upgraded Odylith from 1.2.3 to 1.2.4." in output
    assert "done   Dashboard ready." in output


def test_rollback_dispatches_to_previous(monkeypatch, tmp_path: Path, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_rollback_install(*, repo_root: str) -> SimpleNamespace:
        captured["repo_root"] = repo_root
        return SimpleNamespace(
            active_version="1.2.2",
            diverged_from_pin=True,
            launcher_path=Path(repo_root) / ".odylith" / "bin" / "odylith",
            pinned_version="1.2.3",
            previous_version="1.2.3",
        )

    monkeypatch.setattr(cli, "rollback_install", fake_rollback_install)

    rc = cli.main(["rollback", "--repo-root", str(tmp_path), "--previous"])
    output = capsys.readouterr().out

    assert rc == 0
    assert captured["repo_root"] == str(tmp_path)
    assert "Odylith rolled back from 1.2.3 to 1.2.2." in output
    assert "diverges from repo pin 1.2.3" in output


def test_version_reports_pinned_and_available(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_version_status(*, repo_root: str) -> SimpleNamespace:
        return SimpleNamespace(
            repo_root=Path(repo_root),
            repo_role="product_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            release_eligible=True,
            context_engine_mode="full_local_memory",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.2",
            last_known_good_version="1.2.2",
            detached=False,
            diverged_from_pin=True,
            available_versions=["1.2.2", "1.2.3"],
        )

    monkeypatch.setattr(cli, "version_status", fake_version_status)

    rc = cli.main(["version", "--repo-root", str(tmp_path)])
    output = capsys.readouterr().out

    assert rc == 0
    assert f"Repo root: {tmp_path}" in output
    assert "Repo role: product_repo" in output
    assert "Posture: pinned_release" in output
    assert "Runtime source: pinned_runtime" in output
    assert "Release eligible: yes" in output
    assert "Context engine mode: full_local_memory" in output
    assert "Context engine pack: installed" in output
    assert "Pinned: 1.2.3" in output
    assert "Active: 1.2.2" in output
    assert "Diverged from pin: yes" in output
    assert "Installed locally: 1.2.2, 1.2.3" in output


def test_version_reports_nonfatal_runtime_trust_warning(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_version_status(*, repo_root: str) -> SimpleNamespace:
        return SimpleNamespace(
            repo_root=Path(repo_root),
            repo_role="consumer_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            runtime_source_detail="",
            release_eligible=True,
            context_engine_mode="local",
            context_engine_pack_installed=True,
            pinned_version="1.2.3",
            active_version="1.2.3",
            last_known_good_version="1.2.3",
            detached=False,
            diverged_from_pin=False,
            available_versions=["1.2.3"],
            runtime_trust_warnings=(
                "Sigstore emitted expected non-fatal trust-root warning stream(s) "
                "(severity=notice; verification_degraded=no), but artifact identity, issuer, provenance, "
                "SBOM, and sha256 verification completed successfully.",
            ),
        )

    monkeypatch.setattr(cli, "version_status", fake_version_status)

    rc = cli.main(["version", "--repo-root", str(tmp_path)])
    output = capsys.readouterr().out

    assert rc == 0
    assert "Trust warning: Sigstore emitted expected non-fatal trust-root warning stream(s)" in output
    assert "verification_degraded=no" in output
    assert "artifact identity, issuer, provenance, SBOM, and sha256 verification completed successfully" in output



def test_subagent_router_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 31

    monkeypatch.setattr(cli.subagent_router, "main", fake_main)
    rc = cli.main(["subagent-router", "--repo-root", str(tmp_path), "show-tuning", "--json"])
    assert rc == 31
    assert captured["argv"] == ["show-tuning", "--repo-root", str(tmp_path), "--json"]


def test_subagent_orchestrator_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 37

    monkeypatch.setattr(cli.subagent_orchestrator, "main", fake_main)
    rc = cli.main(["subagent-orchestrator", "--repo-root", str(tmp_path), "show-tuning", "--json"])
    assert rc == 37
    assert captured["argv"] == ["show-tuning", "--repo-root", str(tmp_path), "--json"]


def test_subagent_router_help_does_not_receive_injected_repo_root(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(cli.subagent_router, "main", fake_main)
    rc = cli.main(["subagent-router", "--repo-root", str(tmp_path), "--help"])

    assert rc == 0
    assert captured["argv"] == ["--help"]


def test_subagent_orchestrator_help_does_not_receive_injected_repo_root(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(cli.subagent_orchestrator, "main", fake_main)
    rc = cli.main(["subagent-orchestrator", "--repo-root", str(tmp_path), "--help"])

    assert rc == 0
    assert captured["argv"] == ["--help"]


def test_atlas_render_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 41

    monkeypatch.setattr(cli.render_mermaid_catalog, "main", fake_main)
    rc = cli.main(["atlas", "render", "--repo-root", str(tmp_path), "--fail-on-stale"])
    assert rc == 41
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--fail-on-stale"]


def test_atlas_auto_update_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 43

    monkeypatch.setattr(cli.auto_update_mermaid_diagrams, "main", fake_main)
    rc = cli.main(["atlas", "auto-update", "--repo-root", str(tmp_path), "--all-stale"])
    assert rc == 43
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--all-stale"]


def test_sync_help_uses_parser_without_running_sync(monkeypatch, tmp_path: Path, capsys) -> None:
    def fail(*args, **kwargs) -> int:  # noqa: ANN002, ANN003
        raise AssertionError("sync main should not run for --help")

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fail)

    try:
        cli.main(["sync", "--repo-root", str(tmp_path), "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected argparse help exit")

    assert "usage: odylith sync" in capsys.readouterr().out


def test_governance_help_uses_parser_without_running_subcommand(monkeypatch, tmp_path: Path, capsys) -> None:
    def fail(argv: list[str]) -> int:
        raise AssertionError(f"governance subcommand should not run for --help: {argv}")

    monkeypatch.setattr(cli.version_truth, "main", fail)

    try:
        cli.main(["governance", "version-truth", "--repo-root", str(tmp_path), "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected argparse help exit")

    assert "usage: odylith governance version-truth" in capsys.readouterr().out


def test_validate_help_uses_parser_without_running_subcommand(monkeypatch, tmp_path: Path, capsys) -> None:
    def fail(argv: list[str]) -> int:
        raise AssertionError(f"validate subcommand should not run for --help: {argv}")

    monkeypatch.setattr(cli.validate_component_registry_contract, "main", fail)

    try:
        cli.main(["validate", "component-registry-contract", "--repo-root", str(tmp_path), "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected argparse help exit")

    assert "usage: odylith validate component-registry-contract" in capsys.readouterr().out


def test_validate_topology_integrity_dispatch_accepts_forwarded_flags(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 44

    monkeypatch.setattr(cli.topology_integrity, "main", fake_main)
    rc = cli.main(["validate", "topology-integrity", "--repo-root", str(tmp_path), "--min-score", "95"])

    assert rc == 44
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--min-score", "95"]


def test_lane_status_help_uses_parser_without_running_status(monkeypatch, tmp_path: Path, capsys) -> None:
    def fail(argv: list[str]) -> int:
        raise AssertionError(f"lane status should not run for --help: {argv}")

    monkeypatch.setattr(cli.maintainer_lane_status, "main", fail)

    try:
        cli.main(["lane", "status", "--repo-root", str(tmp_path), "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected argparse help exit")

    assert "usage: odylith lane status" in capsys.readouterr().out
