import json
import re
from pathlib import Path

from odylith import cli
from odylith.runtime.governance import casebook_source_validation
from odylith.runtime.governance import sync_workstream_artifacts
from odylith.runtime.surfaces import render_casebook_dashboard


def _write_bug(path: Path, *, reproducibility: str = "High") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "- Bug ID: CB-001",
                "",
                "- Status: Open",
                "",
                "- Created: 2026-04-16",
                "",
                "- Severity: P1",
                "",
                f"- Reproducibility: {reproducibility}",
                "",
                "- Type: Product",
                "",
                "- Description: Example source validation bug.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_bug_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_casebook_source_validation_accepts_compact_reproducibility(tmp_path: Path) -> None:
    _write_bug(tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-compact.md")

    result = casebook_source_validation.validate_casebook_sources(repo_root=tmp_path)

    assert result.passed
    assert result.records_checked == 1
    assert result.issues == ()


def test_casebook_source_validation_rejects_prose_reproducibility(tmp_path: Path) -> None:
    _write_bug(
        tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-prose.md",
        reproducibility="High; render odylith/index.html and the diagnostic block appears above tabs.",
    )

    result = casebook_source_validation.validate_casebook_sources(repo_root=tmp_path)

    assert not result.passed
    assert result.records_checked == 1
    assert len(result.issues) == 1
    assert result.issues[0].field == "Reproducibility"
    assert result.issues[0].line == 9
    assert "one compact token" in result.issues[0].message


def test_casebook_source_validation_rejects_missing_reproducibility_field(tmp_path: Path) -> None:
    _write_bug_text(
        tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-missing.md",
        "\n".join(
            [
                "- Bug ID: CB-001",
                "",
                "- Status: Open",
                "",
                "- Created: 2026-04-16",
                "",
                "- Severity: P1",
                "",
                "- Type: Product",
                "",
                "- Description: Example source validation bug.",
                "",
            ]
        )
        + "\n",
    )

    result = casebook_source_validation.validate_casebook_sources(repo_root=tmp_path)

    assert not result.passed
    assert len(result.issues) == 1
    assert result.issues[0].message == "missing required Casebook bug field"


def test_casebook_source_validation_rejects_duplicate_reproducibility_fields(tmp_path: Path) -> None:
    _write_bug_text(
        tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-duplicate.md",
        "\n".join(
            [
                "- Bug ID: CB-001",
                "",
                "- Status: Open",
                "",
                "- Created: 2026-04-16",
                "",
                "- Severity: P1",
                "",
                "- Reproducibility: High",
                "",
                "- Reproducibility: Low",
                "",
                "- Type: Product",
                "",
                "- Description: Example source validation bug.",
                "",
            ]
        )
        + "\n",
    )

    result = casebook_source_validation.validate_casebook_sources(repo_root=tmp_path)

    assert not result.passed
    assert len(result.issues) == 1
    assert result.issues[0].message == "duplicate Casebook bug field"
    assert result.issues[0].value == "Low"


def test_casebook_source_validation_rejects_placeholder_reproducibility_token(tmp_path: Path) -> None:
    _write_bug(
        tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-placeholder.md",
        reproducibility="TBD",
    )

    result = casebook_source_validation.validate_casebook_sources(repo_root=tmp_path)

    assert not result.passed
    assert len(result.issues) == 1
    assert result.issues[0].value == "TBD"
    assert "one compact token" in result.issues[0].message


def test_casebook_source_validation_issue_payloads_use_repo_relative_paths(tmp_path: Path) -> None:
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-invalid.md"
    _write_bug(
        bug_path,
        reproducibility="High: reproduced from the dashboard screenshot.",
    )

    result = casebook_source_validation.validate_casebook_sources(repo_root=tmp_path)
    issue = result.issues[0]

    assert issue.as_dict(repo_root=tmp_path)["path"] == "odylith/casebook/bugs/2026-04-16-invalid.md"
    assert issue.render(repo_root=tmp_path).startswith("odylith/casebook/bugs/2026-04-16-invalid.md:9:")


def test_normalize_reproducibility_token_handles_sequences_and_bytes() -> None:
    assert casebook_source_validation.normalize_reproducibility_token(["always"]) == "Always"
    assert casebook_source_validation.normalize_reproducibility_token(b"medium") == "Medium"
    assert not casebook_source_validation.reproducibility_token_is_valid("pending")


def test_iter_casebook_bug_markdown_paths_skips_guidance_and_index_files(tmp_path: Path) -> None:
    bugs_root = tmp_path / "odylith" / "casebook" / "bugs"
    _write_bug(bugs_root / "2026-04-16-valid.md")
    _write_bug_text(bugs_root / "AGENTS.md", "# guidance\n")
    _write_bug_text(bugs_root / "CLAUDE.md", "# guidance\n")
    _write_bug_text(bugs_root / "INDEX.md", "# index\n")

    paths = casebook_source_validation.iter_casebook_bug_markdown_paths(repo_root=tmp_path)

    assert [path.name for path in paths] == ["2026-04-16-valid.md"]


def test_casebook_validate_cli_reports_invalid_source(tmp_path: Path, capsys) -> None:
    _write_bug(
        tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-invalid.md",
        reproducibility="High: reproduced from the dashboard screenshot.",
    )

    rc = cli.main(["casebook", "validate", "--repo-root", str(tmp_path)])

    output = capsys.readouterr().out
    assert rc == 2
    assert "casebook source validation failed" in output
    assert "odylith/casebook/bugs/2026-04-16-invalid.md:9" in output
    assert "must be one compact token" in output


def test_validate_casebook_source_alias_uses_same_validator(tmp_path: Path, capsys) -> None:
    _write_bug(tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-valid.md")

    rc = cli.main(["validate", "casebook-source", "--repo-root", str(tmp_path)])

    output = capsys.readouterr().out
    assert rc == 0
    assert "casebook source validation passed" in output
    assert "- records_checked: 1" in output


def test_casebook_refresh_fails_before_writing_index_for_invalid_source(tmp_path: Path) -> None:
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-invalid.md"
    _write_bug(
        bug_path,
        reproducibility="High; repro steps belong in Trigger Path.",
    )

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("casebook",),
        runtime_mode="standalone",
    )

    assert rc == 2
    assert not (bug_path.parent / "INDEX.md").exists()
    assert not (tmp_path / "odylith" / "casebook" / "casebook.html").exists()


def test_casebook_refresh_validates_before_cached_reuse(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _write_bug(
        tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-invalid.md",
        reproducibility="High; cached output must not hide this.",
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.surface_refresh_fingerprint_dag,
        "can_reuse_surface_refresh",
        lambda **kwargs: (True, {"reason": "forced"}),
    )

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("casebook",),
        runtime_mode="standalone",
    )

    assert rc == 2


def test_casebook_renderer_fails_before_output_for_invalid_source(tmp_path: Path) -> None:
    _write_bug(
        tmp_path / "odylith" / "casebook" / "bugs" / "2026-04-16-invalid.md",
        reproducibility="High; open odylith/index.html to reproduce.",
    )
    output_path = tmp_path / "odylith" / "casebook" / "casebook.html"

    rc = render_casebook_dashboard.main(
        [
            "--repo-root",
            str(tmp_path),
            "--output",
            str(output_path),
            "--runtime-mode",
            "standalone",
        ]
    )

    assert rc == 2
    assert not output_path.exists()


def test_checked_in_casebook_detail_shards_keep_reproducibility_compact() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    offenders: list[str] = []
    for path in sorted((repo_root / "odylith" / "casebook").glob("casebook-detail-shard-*.v1.js")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"Object\.assign\([^,]+, (?P<payload>.*)\);?$", text, re.S)
        assert match is not None, f"could not parse {path.relative_to(repo_root)}"
        payload = json.loads(match.group("payload"))
        for bug_id, row in payload.items():
            fields = row.get("fields", {}) if isinstance(row, dict) else {}
            value = str(fields.get("Reproducibility", "")).strip()
            if not casebook_source_validation.reproducibility_token_is_valid(value):
                offenders.append(f"{path.relative_to(repo_root)}:{bug_id}: {value}")
    assert offenders == []
