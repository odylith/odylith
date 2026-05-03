from __future__ import annotations

import json
import subprocess
from pathlib import Path

from odylith.install import upgrade_reporting
from odylith.install.casebook_metadata_migration import STATUS_FSM_MIGRATION_ID
from odylith.install.casebook_metadata_migration import MIGRATION_ID as CASEBOOK_COMPACT_MIGRATION_ID
from odylith.runtime.governance import sync_workstream_artifacts

from tests.integration.install.simulator import InstallLifecycleSimulator
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _new_page,
    _static_server,
    browser_context,
)

_REAL_SUBPROCESS_RUN = subprocess.run


def _git(repo_root: Path, *args: str) -> None:
    _REAL_SUBPROCESS_RUN(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _route_git_subprocess(monkeypatch, sim: InstallLifecycleSimulator) -> None:  # noqa: ANN001
    def _run(command, *, check=False, capture_output=False, text=False, **kwargs):  # noqa: ANN001
        argv = [str(token) for token in command]
        if argv and Path(argv[0]).name == "git":
            return _REAL_SUBPROCESS_RUN(
                command,
                check=check,
                capture_output=capture_output,
                text=text,
                **kwargs,
            )
        return sim._fake_smoke_run(  # noqa: SLF001
            command,
            check=check,
            capture_output=capture_output,
            text=text,
            **kwargs,
        )

    monkeypatch.setattr(subprocess, "run", _run)


def _commit_installed_baseline(repo_root: Path) -> None:
    _git(repo_root, "init")
    _git(repo_root, "config", "user.name", "freedom-research")
    _git(repo_root, "config", "user.email", "freedom-research@example.com")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "consumer baseline")


def _write_bad_legacy_casebook_records(repo_root: Path) -> tuple[Path, Path]:
    bugs_root = repo_root / "odylith" / "casebook" / "bugs"
    bugs_root.mkdir(parents=True, exist_ok=True)
    deploy_bug = bugs_root / "2026-05-03-bad-status-and-deployment-type.md"
    deploy_bug.write_text(
        "\n".join(
            [
                "- Bug ID: CB-998",
                "",
                "- Status: ForwardFixUpdatedLocallyPendingPlatformReleaseDeploy",
                "",
                "- Created: 2026-05-03",
                "",
                "- Fixed: Pending release/deploy",
                "",
                "- Severity: P1",
                "",
                "- Reproducibility: Always",
                "",
                "- Type: PrivateJobsRunnerManifes",
                "",
                "- Description: Consumer dirty-repo migration fixture.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    infra_bug = bugs_root / "2026-05-03-truncated-infra-type.md"
    infra_bug.write_text(
        "\n".join(
            [
                "- Bug ID: CB-999",
                "",
                "- Status: Open",
                "",
                "- Created: 2026-05-03",
                "",
                "- Severity: P2",
                "",
                "- Reproducibility: Always",
                "",
                "- Type: TestHarnessInfraRegressi",
                "",
                "- Description: Consumer dirty-repo migration fixture for truncated Type.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return deploy_bug, infra_bug


def test_dirty_consumer_upgrade_normalizes_casebook_and_browser_stale_url_state(
    tmp_path: Path,
    monkeypatch,
    browser_context,
) -> None:  # noqa: ANN001
    _base_url, context = browser_context
    sim = InstallLifecycleSimulator(tmp_path=tmp_path, monkeypatch=monkeypatch)
    _route_git_subprocess(monkeypatch, sim)
    sim.register_release("0.1.14")

    assert sim.install("0.1.13") == 0
    _commit_installed_baseline(sim.repo_root)
    deploy_bug, infra_bug = _write_bad_legacy_casebook_records(sim.repo_root)
    (sim.repo_root / "consumer-notes.md").write_text("local work must survive upgrade\n", encoding="utf-8")
    sim.write_pin("0.1.14")

    assert sim.upgrade() == 0
    assert sim.status().active_version == "0.1.14"
    assert (sim.repo_root / "consumer-notes.md").read_text(encoding="utf-8") == "local work must survive upgrade\n"
    assert "- Status: FixedPendingRelease" in deploy_bug.read_text(encoding="utf-8")
    assert "- Type: Deployment" in deploy_bug.read_text(encoding="utf-8")
    assert "- Type: Infra" in infra_bug.read_text(encoding="utf-8")

    latest_report = upgrade_reporting.latest_upgrade_report(repo_root=sim.repo_root)
    assert latest_report is not None
    _report_path, report = latest_report
    change_review = report["change_review"]
    assert change_review["pre_existing_dirty_touched_by_migrations"] == [
        "odylith/casebook/bugs/2026-05-03-bad-status-and-deployment-type.md",
        "odylith/casebook/bugs/2026-05-03-truncated-infra-type.md",
    ]
    assert change_review["required_migrations"][CASEBOOK_COMPACT_MIGRATION_ID]["written_paths"][:2] == [
        "odylith/casebook/bugs/2026-05-03-bad-status-and-deployment-type.md",
        "odylith/casebook/bugs/2026-05-03-truncated-infra-type.md",
    ]
    assert any(
        row.get("migration_id") == STATUS_FSM_MIGRATION_ID
        and row.get("verification_result", {}).get("status") == "passed"
        for row in report["migration_results"]
    )
    assert change_review["manual_review_required"]["paths"] == ["consumer-notes.md"]

    assert sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=sim.repo_root,
        surfaces=("casebook", "tooling_shell"),
        runtime_mode="standalone",
    ) == 0
    payload_text = (sim.repo_root / "odylith" / "casebook" / "casebook-payload.v1.js").read_text(encoding="utf-8")
    assert "ForwardFixUpdatedLocallyPendingPlatformReleaseDeploy" not in payload_text
    assert "PrivateJobsRunnerManifes" not in payload_text
    assert "TestHarnessInfraRegressi" not in payload_text

    with _static_server(root=sim.repo_root) as base_url:
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(
            base_url
            + "/odylith/index.html?tab=casebook&bug=CB-998&status=ForwardFixUpdatedLocallyPendingPlatformReleaseDeploy",
            wait_until="domcontentloaded",
        )
        assert response is not None and response.ok
        casebook = page.frame_locator("#frame-casebook")
        casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
        casebook.locator('button.bug-row.active[data-bug="CB-998"]').wait_for(timeout=15000)
        assert casebook.locator("#statusFilter").input_value() == ""
        assert casebook.locator("#listMeta").inner_text().strip() != "Visible: 0"
        facts = casebook.locator("#detailPane .summary-fact").evaluate_all(
            """nodes => Object.fromEntries(nodes.map((node) => [
              (node.querySelector(".summary-fact-label")?.textContent || "").trim(),
              (node.querySelector(".summary-fact-value")?.textContent || "").trim(),
            ]))"""
        )
        assert facts["Status"] == "Fixed pending release"
        assert facts["Type"] == "Deployment"
        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)

    report_payload = json.loads(_report_path.read_text(encoding="utf-8"))
    assert report_payload["change_review"]["manual_review_required"]["paths"] == ["consumer-notes.md"]
