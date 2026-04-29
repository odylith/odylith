from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from odylith import cli
from odylith.runtime.governance import bug_authoring
from odylith.runtime.governance import github_issue_cli
from odylith.runtime.governance import github_issue_pipeline
from odylith.runtime.governance.github_issue_transport import GitHubPipelineError


ISSUE_21 = {
    "number": 21,
    "title": "[Bug] Critical: Partial installation breaks Claude Code (if SSL error)",
    "html_url": "https://github.com/odylith/odylith/issues/21",
    "state": "open",
    "user": {"login": "pathri"},
    "created_at": "2026-04-29T19:14:50Z",
    "updated_at": "2026-04-29T19:14:50Z",
    "labels": [{"name": "bug"}],
    "body": "\n".join(
        [
            "Corporate VPN SSL certificate interception caused the GitHub asset download to fail.",
            "Installation had already modified `~/.claude/settings.json` before the failure occurred.",
            "Claude Code operations now fail with hook errors.",
            "Data Loss: Original hooks, permissions, and AWS credentials overwritten.",
        ]
    ),
}

GENERIC_ISSUE = {
    "number": 22,
    "title": "[Bug] Upgrade reinstall output is confusing",
    "html_url": "https://github.com/odylith/odylith/issues/22",
    "state": "open",
    "user": {"login": "operator"},
    "labels": [],
    "body": "Upgrade and reinstall are noisy, but no linked Casebook evidence exists yet.",
}


class FakeGitHubTransport:
    def __init__(
        self,
        *,
        issues: Sequence[Mapping[str, Any]] = (ISSUE_21,),
        labels: Sequence[Mapping[str, str]] = ({"name": "bug"},),
        release_tags: Sequence[str] = (),
    ) -> None:
        self.issues = {int(issue["number"]): dict(issue) for issue in issues}
        self.labels = [dict(label) for label in labels]
        self.release_tags = set(release_tags)
        self.created_labels: list[str] = []
        self.added_labels: list[tuple[int, tuple[str, ...]]] = []
        self.comments: list[tuple[int, str]] = []
        self.closed: list[int] = []

    def get_issue(self, *, repo: str, number: int) -> Mapping[str, Any]:
        return self.issues[number]

    def list_issues(self, *, repo: str, state: str) -> Sequence[Mapping[str, Any]]:
        return [issue for issue in self.issues.values() if state == "all" or issue.get("state") == state]

    def list_labels(self, *, repo: str) -> Sequence[Mapping[str, Any]]:
        return self.labels

    def create_label(self, *, repo: str, name: str, description: str, color: str) -> None:
        self.created_labels.append(name)
        self.labels.append({"name": name, "description": description, "color": color})

    def add_labels(self, *, repo: str, number: int, labels: Sequence[str]) -> None:
        self.added_labels.append((number, tuple(labels)))

    def comment_issue(self, *, repo: str, number: int, body: str) -> None:
        self.comments.append((number, body))

    def close_issue(self, *, repo: str, number: int) -> None:
        self.closed.append(number)

    def get_release_by_tag(self, *, repo: str, tag: str) -> Mapping[str, Any] | None:
        return {"tag_name": tag} if tag in self.release_tags else None


def _write_cb136(repo_root: Path, *, verification: str = "Focused install tests passed.") -> Path:
    bug_path = repo_root / "odylith/casebook/bugs/2026-04-29-install-overwrites-claude-settings-before-verified-runtime-activation.md"
    bug_path.parent.mkdir(parents=True, exist_ok=True)
    bug_path.write_text(
        "\n".join(
            [
                "- Bug ID: CB-136",
                "",
                "- Status: Closed",
                "",
                "- Created: 2026-04-29",
                "",
                "- Severity: P0",
                "",
                "- Reproducibility: High",
                "",
                "- Type: data-loss",
                "",
                "- Description: Install overwrites Claude settings before verified runtime activation.",
                "",
                "- Components Affected: migration-runtime",
                "",
                "- Failure Signature: ~/.claude/settings.json is replaced before SSL release download fails.",
                "",
                f"- Verification: {verification}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return bug_path


def _write_releases(repo_root: Path, *, status: str = "active") -> None:
    release_path = repo_root / "odylith/radar/source/releases/releases.v1.json"
    release_path.parent.mkdir(parents=True, exist_ok=True)
    release_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "aliases": {"current": "release-0-1-12"},
                "releases": [
                    {
                        "release_id": "release-0-1-12",
                        "status": status,
                        "version": "0.1.12",
                        "tag": "v0.1.12",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_parse_issue_reference_accepts_url_shorthand_and_number() -> None:
    assert github_issue_pipeline.parse_issue_reference("https://github.com/odylith/odylith/issues/21").as_dict() == {
        "repo": "odylith/odylith",
        "number": 21,
    }
    assert github_issue_pipeline.parse_issue_reference("odylith/odylith#21").number == 21
    assert github_issue_pipeline.parse_issue_reference("21", default_repo="odylith/odylith").repo == "odylith/odylith"


def test_issue_21_triage_matches_cb136_and_drafts_requested_labels(tmp_path: Path) -> None:
    _write_cb136(tmp_path)
    plan = github_issue_pipeline.build_triage_plan(
        issue=ISSUE_21,
        repo_root=tmp_path,
        repo="odylith/odylith",
        existing_labels=({"name": "bug"},),
    )

    assert plan.severity == "P0"
    assert plan.issue_types == ("data-loss", "install")
    assert plan.suspected_component == "migration-runtime"
    assert [candidate.bug_id for candidate in plan.duplicate_casebook_candidates] == ["CB-136"]
    assert plan.recommended_governance_mutation.fields == {
        "GitHub Issue(s)": "odylith/odylith#21",
        "GitHub Status": "fixed_pending_release",
        "Fixed In": "0.1.12",
        "Public Response": "pending",
    }
    assert plan.recommended_github_mutation.labels_to_add == (
        "severity:P0",
        "type:data-loss",
        "type:install",
        "component:migration-runtime",
        "release:0.1.12",
        "status:fixed-pending-release",
    )
    assert "type:trust" not in plan.recommended_github_mutation.labels_to_add


def test_triage_without_casebook_match_blocks_public_github_apply(tmp_path: Path) -> None:
    plan = github_issue_pipeline.build_triage_plan(
        issue=GENERIC_ISSUE,
        repo_root=tmp_path,
        repo="odylith/odylith",
        existing_labels=(),
    )

    assert plan.recommended_governance_mutation.action == "blocked"
    assert plan.recommended_github_mutation.close_decision == "blocked"
    assert "Casebook" in plan.recommended_github_mutation.blocked_reason
    assert "status:needs-repro" in plan.recommended_github_mutation.labels_to_add
    assert "release:0.1.12" not in plan.recommended_github_mutation.labels_to_add

    with pytest.raises(GitHubPipelineError):
        github_issue_pipeline.apply_github_plan(
            repo="odylith/odylith",
            issue_number=22,
            plan=plan.recommended_github_mutation,
            transport=FakeGitHubTransport(),
        )


def test_triage_reports_creation_for_missing_standard_bug_label(tmp_path: Path) -> None:
    _write_cb136(tmp_path)
    issue = {**ISSUE_21, "labels": []}
    plan = github_issue_pipeline.build_triage_plan(
        issue=issue,
        repo_root=tmp_path,
        repo="odylith/odylith",
        existing_labels=(),
    )

    assert "bug" in [label.name for label in plan.recommended_github_mutation.labels_to_create]
    assert "bug" in plan.recommended_github_mutation.labels_to_add


def test_triage_does_not_recreate_existing_labels(tmp_path: Path) -> None:
    _write_cb136(tmp_path)
    existing = (
        {"name": "bug"},
        {"name": "severity:P0"},
        {"name": "type:data-loss"},
        {"name": "type:install"},
        {"name": "component:migration-runtime"},
        {"name": "release:0.1.12"},
        {"name": "status:fixed-pending-release"},
    )
    plan = github_issue_pipeline.build_triage_plan(
        issue=ISSUE_21,
        repo_root=tmp_path,
        repo="odylith/odylith",
        existing_labels=existing,
    )

    assert plan.recommended_github_mutation.labels_to_create == ()


def test_apply_governance_updates_casebook_without_public_github_writes(tmp_path: Path) -> None:
    bug_path = _write_cb136(tmp_path)
    fake = FakeGitHubTransport()
    plan = github_issue_pipeline.build_triage_plan(
        issue=fake.get_issue(repo="odylith/odylith", number=21),
        repo_root=tmp_path,
        repo="odylith/odylith",
        existing_labels=fake.list_labels(repo="odylith/odylith"),
    )

    changed = github_issue_pipeline.apply_governance_plan(repo_root=tmp_path, plan=plan)

    assert changed == (bug_path,)
    text = bug_path.read_text(encoding="utf-8")
    assert "- GitHub Issue(s): odylith/odylith#21" in text
    assert "- GitHub Status: fixed_pending_release" in text
    assert "- Fixed In: 0.1.12" in text
    assert "- Public Response: pending" in text
    assert fake.created_labels == []
    assert fake.comments == []


def test_cli_json_does_not_write_to_github_without_apply_flag(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_cb136(tmp_path)
    fake = FakeGitHubTransport()
    monkeypatch.setattr(github_issue_cli, "build_transport", lambda: fake)

    rc = cli.main(["github", "--repo-root", str(tmp_path), "issue", "triage", "21", "--repo", "odylith/odylith", "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"]["severity"] == "P0"
    assert payload["applied"] == {"governance": False, "github": False}
    assert fake.created_labels == []
    assert fake.added_labels == []
    assert fake.comments == []
    assert fake.closed == []


def test_cli_apply_github_records_labels_and_comment_only_when_explicit(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_cb136(tmp_path)
    fake = FakeGitHubTransport()
    monkeypatch.setattr(github_issue_cli, "build_transport", lambda: fake)

    rc = cli.main(
        [
            "github",
            "--repo-root",
            str(tmp_path),
            "issue",
            "triage",
            "21",
            "--repo",
            "odylith/odylith",
            "--apply-github",
            "--json",
        ]
    )

    assert rc == 0
    json.loads(capsys.readouterr().out)
    assert "severity:P0" in fake.created_labels
    assert fake.added_labels == [
        (
            21,
            (
                "severity:P0",
                "type:data-loss",
                "type:install",
                "component:migration-runtime",
                "release:0.1.12",
                "status:fixed-pending-release",
            ),
        )
    ]
    assert fake.comments and "CB-136" in fake.comments[0][1]
    assert fake.closed == []


def test_cli_apply_github_without_casebook_match_fails_closed(tmp_path: Path, monkeypatch, capsys) -> None:
    fake = FakeGitHubTransport(issues=(GENERIC_ISSUE,), labels=())
    monkeypatch.setattr(github_issue_cli, "build_transport", lambda: fake)

    rc = cli.main(
        [
            "github",
            "--repo-root",
            str(tmp_path),
            "issue",
            "triage",
            "22",
            "--repo",
            "odylith/odylith",
            "--apply-github",
            "--json",
        ]
    )

    output = capsys.readouterr()
    assert rc == 2
    assert "No matching Casebook record" in output.err
    assert fake.created_labels == []
    assert fake.added_labels == []
    assert fake.comments == []


def test_sweep_processes_open_issues_deterministically(tmp_path: Path) -> None:
    _write_cb136(tmp_path)
    fake = FakeGitHubTransport(
        issues=(
            {**ISSUE_21, "number": 22, "title": "[Bug] later", "state": "open"},
            ISSUE_21,
        )
    )

    issues = sorted(fake.list_issues(repo="odylith/odylith", state="open"), key=lambda issue: int(issue["number"]))
    plans = [
        github_issue_pipeline.build_triage_plan(
            issue=issue,
            repo_root=tmp_path,
            repo="odylith/odylith",
            existing_labels=fake.list_labels(repo="odylith/odylith"),
        )
        for issue in issues
    ]

    assert [plan.issue["number"] for plan in plans] == [21, 22]


def test_release_closeout_keeps_fixed_issue_pending_before_public_release(tmp_path: Path) -> None:
    bug_path = _write_cb136(tmp_path)
    bug_path.write_text(
        bug_path.read_text(encoding="utf-8")
        + "- GitHub Issue(s): odylith/odylith#21\n\n"
        + "- GitHub Status: fixed_pending_release\n\n"
        + "- Fixed In: 0.1.12\n\n"
        + "- Public Response: pending\n",
        encoding="utf-8",
    )
    _write_releases(tmp_path, status="active")

    plan = github_issue_pipeline.build_release_closeout_plan(
        repo_root=tmp_path,
        release="current",
        repo="odylith/odylith",
        transport=FakeGitHubTransport(release_tags=("v0.1.12",)),
    )

    assert plan.public_release_available is False
    assert [item.issue for item in plan.pending] == ["odylith/odylith#21"]
    assert plan.closable == ()


def test_release_closeout_closes_only_after_shipped_release_is_public(tmp_path: Path) -> None:
    bug_path = _write_cb136(tmp_path)
    bug_path.write_text(
        bug_path.read_text(encoding="utf-8")
        + "- GitHub Issue(s): odylith/odylith#21\n\n"
        + "- GitHub Status: fixed_pending_release\n\n"
        + "- Fixed In: 0.1.12\n\n"
        + "- Public Response: pending\n",
        encoding="utf-8",
    )
    _write_releases(tmp_path, status="shipped")

    plan = github_issue_pipeline.build_release_closeout_plan(
        repo_root=tmp_path,
        release="current",
        repo="odylith/odylith",
        transport=FakeGitHubTransport(release_tags=("v0.1.12",)),
    )

    assert plan.public_release_available is True
    assert plan.pending == ()
    assert [item.issue for item in plan.closable] == ["odylith/odylith#21"]
    assert plan.closable[0].github_mutation.close_decision == "close"


def test_release_closeout_blocks_public_release_when_issue_state_is_unknown(tmp_path: Path) -> None:
    class ReleaseOnlyTransport(FakeGitHubTransport):
        def get_issue(self, *, repo: str, number: int) -> Mapping[str, Any]:
            raise GitHubPipelineError("issue state unavailable")

    bug_path = _write_cb136(tmp_path)
    bug_path.write_text(
        bug_path.read_text(encoding="utf-8")
        + "- GitHub Issue(s): odylith/odylith#21\n\n"
        + "- GitHub Status: fixed_pending_release\n\n"
        + "- Fixed In: 0.1.12\n\n"
        + "- Public Response: pending\n",
        encoding="utf-8",
    )
    _write_releases(tmp_path, status="shipped")

    plan = github_issue_pipeline.build_release_closeout_plan(
        repo_root=tmp_path,
        release="current",
        repo="odylith/odylith",
        transport=ReleaseOnlyTransport(release_tags=("v0.1.12",)),
    )

    assert [item.casebook_id for item in plan.blocked] == ["CB-136"]
    assert "issue state" in plan.blocked[0].github_mutation.blocked_reason


def test_release_closeout_ignores_linked_issues_from_other_repositories(tmp_path: Path) -> None:
    bug_path = _write_cb136(tmp_path)
    bug_path.write_text(
        bug_path.read_text(encoding="utf-8")
        + "- GitHub Issue(s): other/repo#21\n\n"
        + "- GitHub Status: fixed_pending_release\n\n"
        + "- Fixed In: 0.1.12\n\n"
        + "- Public Response: pending\n",
        encoding="utf-8",
    )
    _write_releases(tmp_path, status="shipped")

    plan = github_issue_pipeline.build_release_closeout_plan(
        repo_root=tmp_path,
        release="current",
        repo="odylith/odylith",
        transport=FakeGitHubTransport(release_tags=("v0.1.12",)),
    )

    assert plan.pending == ()
    assert plan.closable == ()
    assert plan.blocked == ()


def test_release_closeout_blocks_p0_without_validation_evidence(tmp_path: Path) -> None:
    bug_path = _write_cb136(tmp_path, verification="")
    bug_path.write_text(
        bug_path.read_text(encoding="utf-8")
        + "- GitHub Issue(s): odylith/odylith#21\n\n"
        + "- GitHub Status: fixed_pending_release\n\n"
        + "- Fixed In: 0.1.12\n\n"
        + "- Public Response: pending\n",
        encoding="utf-8",
    )
    _write_releases(tmp_path, status="shipped")

    plan = github_issue_pipeline.build_release_closeout_plan(
        repo_root=tmp_path,
        release="current",
        repo="odylith/odylith",
        transport=FakeGitHubTransport(release_tags=("v0.1.12",)),
    )

    assert [item.casebook_id for item in plan.blocked] == ["CB-136"]
    assert "validation evidence" in plan.blocked[0].github_mutation.blocked_reason


def test_release_closeout_blocks_linked_issue_missing_public_response_plan(tmp_path: Path) -> None:
    bug_path = _write_cb136(tmp_path)
    bug_path.write_text(
        bug_path.read_text(encoding="utf-8")
        + "- GitHub Issue(s): odylith/odylith#21\n\n"
        + "- Fixed In: 0.1.12\n",
        encoding="utf-8",
    )
    _write_releases(tmp_path, status="shipped")

    plan = github_issue_pipeline.build_release_closeout_plan(
        repo_root=tmp_path,
        release="current",
        repo="odylith/odylith",
        transport=FakeGitHubTransport(release_tags=("v0.1.12",)),
    )

    assert [item.casebook_id for item in plan.blocked] == ["CB-136"]
    assert "Public Response" in plan.blocked[0].github_mutation.blocked_reason


def test_release_closeout_keeps_already_closed_issue_noop(tmp_path: Path) -> None:
    closed_issue = {**ISSUE_21, "state": "closed"}
    bug_path = _write_cb136(tmp_path)
    bug_path.write_text(
        bug_path.read_text(encoding="utf-8")
        + "- GitHub Issue(s): odylith/odylith#21\n\n"
        + "- GitHub Status: fixed_released\n\n"
        + "- Fixed In: 0.1.12\n\n"
        + "- Public Response: closed\n",
        encoding="utf-8",
    )
    _write_releases(tmp_path, status="shipped")

    plan = github_issue_pipeline.build_release_closeout_plan(
        repo_root=tmp_path,
        release="current",
        repo="odylith/odylith",
        transport=FakeGitHubTransport(issues=(closed_issue,), release_tags=("v0.1.12",)),
    )

    assert [item.issue for item in plan.already_closed] == ["odylith/odylith#21"]
    assert plan.already_closed[0].github_mutation.close_decision == "already_closed"
    assert plan.closable == ()


def test_bug_capture_accepts_github_linkage_optional_fields_in_payload(tmp_path: Path) -> None:
    result = bug_authoring.capture_bug_from_payload(
        repo_root=tmp_path,
        title="GitHub linked bug",
        component="github-issue-pipeline",
        severity="P1",
        dry_run=True,
        payload={
            "reproducibility": "High",
            "impact": "Maintainer issue handling cannot be release gated.",
            "environment": "Product repo",
            "detected_by": "Unit test",
            "failure_signature": "Missing public issue lifecycle state.",
            "trigger_path": "odylith bug capture payload",
            "ownership": "github-issue-pipeline",
            "blast_radius": "Maintainer workflow",
            "slo_sla_impact": "Release gate confidence",
            "data_risk": "None",
            "security_compliance": "None",
            "invariant_violated": "Linked public bugs must have lifecycle state.",
            "github_issues": "odylith/odylith#21",
            "github_status": "confirmed",
            "fixed_in": "0.1.12",
            "public_response": "pending",
        },
    )

    assert result.bug_id == "CB-001"


def test_pipeline_boundary_keeps_policy_and_casebook_owners_separate() -> None:
    pipeline_source = Path("src/odylith/runtime/governance/github_issue_pipeline.py").read_text(encoding="utf-8")

    assert "MANAGED_LABELS" not in pipeline_source
    assert "casebook_source_validation" not in pipeline_source
    assert "re.compile" not in pipeline_source
    assert len(pipeline_source.splitlines()) < 250
