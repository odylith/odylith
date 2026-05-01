from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from odylith.install import upgrade_reporting


def test_lifecycle_plan_payload_serializes_paths_and_metadata(tmp_path: Path) -> None:
    plan = SimpleNamespace(
        command="upgrade",
        headline="preview",
        metadata={"target": tmp_path / "runtime", "digests": {"asset": "abc"}},
        steps=(
            SimpleNamespace(
                label="Stage runtime.",
                mutation_classes=("runtime_state",),
                paths=(".odylith/runtime/current",),
                detail="Target release: v1.2.4.",
            ),
        ),
        dirty_overlap=(" M .odylith/install.json",),
        notes=("Dry-run is idempotent.",),
    )

    payload = upgrade_reporting.lifecycle_plan_payload(plan)

    assert payload["metadata"]["target"] == str(tmp_path / "runtime")
    assert payload["steps"][0]["paths"] == [".odylith/runtime/current"]
    assert payload["dirty_overlap"] == ["M .odylith/install.json"]


def test_write_upgrade_report_persists_json_and_updates_report_path(tmp_path: Path) -> None:
    report = {"schema": "odylith.upgrade.report.v1", "status": "succeeded"}
    started_at = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)

    report_path = upgrade_reporting.write_upgrade_report(
        repo_root=tmp_path,
        report=report,
        started_at=started_at,
    )

    assert report_path == tmp_path / ".odylith" / "runtime" / "logs" / "upgrade-20260427T120000Z.json"
    assert report["report_path"] == str(report_path)
    assert json.loads(report_path.read_text(encoding="utf-8"))["report_path"] == str(report_path)


def test_doctor_observability_lines_report_upgrade_and_lock_compaction_prompt(tmp_path: Path) -> None:
    report_dir = tmp_path / ".odylith" / "runtime" / "logs"
    report_dir.mkdir(parents=True)
    (report_dir / "upgrade-20260427T120000Z.json").write_text(
        json.dumps(
            {
                "status": "succeeded_with_warnings",
                "finished_at": "2026-04-27T12:01:00+00:00",
                "dashboard_refresh": {"mode": "launcher", "fresh": True, "timeout_detected": True},
                "generated_change_manifest": {
                    "path": "odylith/upgrade-generated-changes.v1.json",
                    "generated_changed_count": 3,
                    "content_fingerprint": "abcdef1234567890",
                },
            }
        ),
        encoding="utf-8",
    )
    locks_dir = tmp_path / ".odylith" / "locks" / "odylith-context-engine"
    locks_dir.mkdir(parents=True)
    for index in range(200):
        (locks_dir / f"lock-{index}.lock").touch()

    lines = upgrade_reporting.doctor_operational_observability_lines(
        repo_root=tmp_path,
        status=SimpleNamespace(last_known_good_version="1.2.3"),
    )

    assert any(
        "Last upgrade: succeeded_with_warnings at 2026-04-27T12:01:00+00:00" in line
        for line in lines
    )
    assert any(
        "Last upgrade dashboard refresh: mode=launcher; fresh=yes; timeout_detected=yes" in line
        for line in lines
    )
    assert any(
        "Last upgrade generated changes: 3 generated path(s); "
        "manifest: odylith/upgrade-generated-changes.v1.json; fingerprint=abcdef123456"
        in line
        for line in lines
    )
    assert "Rollback target: 1.2.3" in lines
    assert any("200 zero-byte lock placeholders exist under .odylith/locks" in line for line in lines)
    assert any("doctor --repo-root . --repair" in line for line in lines)


def test_git_status_paths_reports_unique_changed_paths(monkeypatch, tmp_path: Path) -> None:
    class _Result:
        returncode = 0
        stdout = " M file-a.py\n?? docs/new.md\nR  old.py -> new.py\n"

    monkeypatch.setattr(upgrade_reporting.subprocess, "run", lambda *args, **kwargs: _Result())
    (tmp_path / ".git").mkdir()

    assert upgrade_reporting.git_status_paths(repo_root=tmp_path) == ["docs/new.md", "file-a.py", "new.py"]


def test_generated_change_manifest_summarizes_generated_surfaces(tmp_path: Path) -> None:
    radar_html = tmp_path / "odylith" / "radar" / "radar.html"
    radar_html.parent.mkdir(parents=True)
    radar_html.write_text("<!doctype html>\n", encoding="utf-8")
    source_index = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    source_index.parent.mkdir(parents=True)
    source_index.write_text("# source truth\n", encoding="utf-8")
    bundle_mirror = tmp_path / "src" / "odylith" / "bundle" / "assets" / "odylith" / "radar" / "radar.html"
    bundle_mirror.parent.mkdir(parents=True)
    bundle_mirror.write_text("<!doctype html>\n", encoding="utf-8")

    payload = upgrade_reporting.generated_change_manifest_payload(
        repo_root=tmp_path,
        changed_paths=[
            "odylith/radar/radar.html",
            "odylith/radar/source/INDEX.md",
            "src/odylith/bundle/assets/odylith/radar/radar.html",
        ],
        active_version="1.2.4",
        previous_version="1.2.3",
        pinned_version="1.2.4",
        dashboard_details={"mode": "launcher", "fresh": True, "stdout": "large generated renderer log"},
    )

    assert payload["generated_changed_count"] == 2
    assert payload["by_category"]["radar"]["count"] == 1
    assert payload["by_category"]["bundle_surface_mirror"]["count"] == 1
    assert payload["entries"][0]["path"] == "odylith/radar/radar.html"
    assert payload["other_changed_paths"] == ["odylith/radar/source/INDEX.md"]
    assert payload["dashboard_refresh"] == {"mode": "launcher", "fresh": True}
    assert len(str(payload["content_fingerprint"])) == 64


def test_write_generated_change_manifest_is_stable_and_skips_non_generated_paths(tmp_path: Path) -> None:
    source_index = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    source_index.parent.mkdir(parents=True)
    source_index.write_text("# source truth\n", encoding="utf-8")

    skipped = upgrade_reporting.write_generated_change_manifest(
        repo_root=tmp_path,
        changed_paths=["odylith/radar/source/INDEX.md"],
        active_version="1.2.4",
        previous_version="1.2.3",
        pinned_version="1.2.4",
        dashboard_details={},
    )

    assert skipped["written"] is False
    assert not (tmp_path / "odylith" / "upgrade-generated-changes.v1.json").exists()

    compass_payload = tmp_path / "odylith" / "compass" / "compass-payload.v1.js"
    compass_payload.parent.mkdir(parents=True)
    compass_payload.write_text("window.payload = {};\n", encoding="utf-8")

    first = upgrade_reporting.write_generated_change_manifest(
        repo_root=tmp_path,
        changed_paths=["odylith/compass/compass-payload.v1.js"],
        active_version="1.2.4",
        previous_version="1.2.3",
        pinned_version="1.2.4",
        dashboard_details={"mode": "standalone", "fresh": True},
    )
    second = upgrade_reporting.write_generated_change_manifest(
        repo_root=tmp_path,
        changed_paths=["odylith/compass/compass-payload.v1.js"],
        active_version="1.2.4",
        previous_version="1.2.3",
        pinned_version="1.2.4",
        dashboard_details={"mode": "standalone", "fresh": True},
    )

    manifest_payload = json.loads(
        (tmp_path / "odylith" / "upgrade-generated-changes.v1.json").read_text(encoding="utf-8")
    )
    assert first["written"] is True
    assert first["changed"] is True
    assert second["written"] is True
    assert second["changed"] is False
    assert manifest_payload["generated_changed_count"] == 1
    assert manifest_payload["entries"][0]["category"] == "compass"
