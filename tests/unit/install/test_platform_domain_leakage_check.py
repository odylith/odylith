from __future__ import annotations

import io
import json
from pathlib import Path
import tarfile
import zipfile

from scripts.release import platform_domain_leakage_check as leakage


def _fixture(path: Path, *, sentinels: list[str] | None = None) -> Path:
    payload = {
        "version": "fixture.v1",
        "prompt": "Build a Lunar Relay Console for Orbital Clerks.",
        "packet": {"facts": [{"label": "Lunar Relay Console"}, {"label": "Orbital Clerks"}]},
        "platform_custody_sentinels": sentinels or ["Lunar Relay Console", "Orbital Clerks"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_loads_only_explicit_source_grounded_sentinels(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "fixture.json")
    assert leakage.load_custody_sentinels(repo_root=tmp_path, fixture_paths=[fixture]) == (
        "Lunar Relay Console",
        "Orbital Clerks",
    )


def test_rejects_ungrounded_or_duplicate_sentinels(tmp_path: Path) -> None:
    ungrounded = _fixture(tmp_path / "ungrounded.json", sentinels=["Invented Vocabulary"])
    try:
        leakage.load_custody_sentinels(repo_root=tmp_path, fixture_paths=[ungrounded])
    except RuntimeError as exc:
        assert "not grounded" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("ungrounded custody sentinel should fail")

    duplicate = _fixture(tmp_path / "duplicate.json", sentinels=["Lunar Relay Console", "lunar-relay_console"])
    try:
        leakage.load_custody_sentinels(repo_root=tmp_path, fixture_paths=[duplicate])
    except RuntimeError as exc:
        assert "duplicate" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("normalized duplicate custody sentinel should fail")


def test_repo_scan_matches_exact_semantic_sentinel_across_code_separators(tmp_path: Path) -> None:
    source = tmp_path / "src" / "odylith" / "runtime" / "bad.py"
    source.parent.mkdir(parents=True)
    source.write_text("LUNAR_RELAY_CONSOLE = True\n", encoding="utf-8")
    assert leakage.scan_repo(tmp_path, sentinels=("Lunar Relay Console",)) == (
        leakage.LeakageFinding(location="src/odylith/runtime/bad.py", sentinel="Lunar Relay Console", line=1),
    )


def test_repo_scan_excludes_fixture_tests_and_governance_evidence(tmp_path: Path) -> None:
    for relative in (
        "scripts/release/fixtures/semantic.json",
        "tests/unit/test_fixture.py",
        "odylith/radar/source/history.md",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Lunar Relay Console\n", encoding="utf-8")
    assert leakage.scan_repo(tmp_path, sentinels=("Lunar Relay Console",)) == ()


def test_distribution_scan_reads_wheel_and_source_archive(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    with zipfile.ZipFile(dist / "odylith.whl", "w") as archive:
        archive.writestr("odylith/runtime/bad.py", "ORBITAL_CLERKS = True\n")
    tar_bytes = b"Lunar Relay Console\n"
    with tarfile.open(dist / "odylith.tar.gz", "w:gz") as archive:
        info = tarfile.TarInfo("odylith/runtime/bad.txt")
        info.size = len(tar_bytes)
        archive.addfile(info, io.BytesIO(tar_bytes))
    findings = leakage.scan_dist(dist, sentinels=("Orbital Clerks", "Lunar Relay Console"))
    assert {(finding.sentinel, finding.location.split(":", 1)[0]) for finding in findings} == {
        ("Orbital Clerks", "wheel"),
        ("Lunar Relay Console", "tar"),
    }


def test_default_release_fixture_is_explicit_and_current_repo_is_clean() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    sentinels = leakage.load_custody_sentinels(repo_root=repo_root)
    assert "Claim Desk" in sentinels
    assert leakage.scan_platform_custody(repo_root=repo_root, sentinels=sentinels) == ()
