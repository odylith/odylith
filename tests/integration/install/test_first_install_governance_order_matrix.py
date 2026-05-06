from __future__ import annotations

import itertools
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith import cli
from odylith.install import manager as install_manager_module
from odylith.install.manager import install_bundle
from tests.integration.install import test_manager as install_test_support


_COMPONENT_ID = "fixture-core"
_UMBRELLA_TITLE = "First install governance order fixture"
_CHILD_TITLE_ONE = "First install governance order child one"
_CHILD_TITLE_TWO = "First install governance order child two"
_BUG_TITLE = "First install governance order bug fixture"
_DIAGRAM_ID = "D-901"
_DIAGRAM_SLUG = "first-install-order-fixture"
_COMPASS_SUMMARY = "First install governance order matrix appended a Compass event."
_RELEASE_ID = "release-first-install-order-fixture"
_WAVE_ID = "W3"
_SURFACE_COMMANDS = ("component", "backlog", "atlas", "bug", "compass")
_FIRST_COMMAND_ORDERS = tuple(itertools.permutations(_SURFACE_COMMANDS))
_FAKE_FIRST_INSTALL_UX_LEAKS = (
    "Tribunal already has CB-122",
    "Casebook already remembers CB-122",
    "This turn resolves to B-096",
    "Show the next Odylith Observation",
    "transcript confirmation",
    "proven visible",
    "brand promise",
    "ready to speak",
    "systemMessage",
    "additionalContext",
    "Stop hook error",
    "Stop says",
)


def _assert_no_fake_first_install_ux_leaks(captured: pytest.CaptureResult[str]) -> None:
    text = f"{captured.out}\n{captured.err}".casefold()
    leaks = [token for token in _FAKE_FIRST_INSTALL_UX_LEAKS if token.casefold() in text]
    assert leaks == []


def _install_fresh_consumer_repo(monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> None:
    install_test_support._write_repo_root(repo_root)  # noqa: SLF001
    monkeypatch.setattr(
        install_manager_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    def _fake_install_release_runtime(*, repo_root, repo, version="latest", activate=True):  # noqa: ANN001
        assert repo == "odylith/odylith"
        resolved_version = "1.2.3" if version == "latest" else str(version)
        runtime_root, python = install_test_support._seed_verified_release_runtime(  # noqa: SLF001
            Path(repo_root),
            version=resolved_version,
        )
        if activate:
            current = Path(repo_root) / ".odylith" / "runtime" / "current"
            current.parent.mkdir(parents=True, exist_ok=True)
            if current.exists() or current.is_symlink():
                current.unlink()
            current.symlink_to(runtime_root)
        return SimpleNamespace(
            version=resolved_version,
            manifest={"repo_schema_version": 1, "migration_required": False},
            python=python,
            root=runtime_root,
            verification=install_test_support._release_verification(resolved_version),  # noqa: SLF001
        )

    def _fake_install_release_feature_pack(
        *,
        repo_root,
        repo,
        version,
        runtime_root=None,
        pack_id="odylith-context-engine-memory",
    ):  # noqa: ANN001
        assert repo == "odylith/odylith"
        assert pack_id == "odylith-context-engine-memory"
        target_root = (
            Path(runtime_root)
            if runtime_root is not None
            else Path(repo_root) / ".odylith" / "runtime" / "versions" / str(version)
        )
        install_test_support._write_fake_context_engine_pack(  # noqa: SLF001
            Path(repo_root),
            target_root=target_root,
            version=str(version),
            pack_id=pack_id,
            feature_pack_sha256=f"feature-pack-{version}",
        )
        return SimpleNamespace(
            asset_name=f"{pack_id}-darwin-arm64.tar.gz",
            manifest={"repo_schema_version": 1, "migration_required": False},
            pack_id=pack_id,
            root=target_root,
            verification={
                "feature_pack_id": pack_id,
                "feature_pack_sha256": f"feature-pack-{version}",
            },
            version=str(version),
        )

    monkeypatch.setattr(install_manager_module, "install_release_runtime", _fake_install_release_runtime)
    monkeypatch.setattr(install_manager_module, "install_release_feature_pack", _fake_install_release_feature_pack)
    monkeypatch.setattr(
        install_manager_module,
        "fetch_release",
        lambda **kwargs: SimpleNamespace(
            version="1.2.3"
            if str(kwargs.get("version") or "").strip() in {"", "latest"}
            else str(kwargs["version"])
        ),
    )
    install_bundle(repo_root=repo_root, bundle_root=repo_root.parent / "unused-bundle", version="1.2.3")
    _seed_atlas_render_outputs(repo_root)


def _seed_atlas_render_outputs(repo_root: Path) -> None:
    atlas_source = repo_root / "odylith" / "atlas" / "source"
    (atlas_source / f"{_DIAGRAM_SLUG}.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"></svg>\n',
        encoding="utf-8",
    )
    (atlas_source / f"{_DIAGRAM_SLUG}.png").write_bytes(b"PNG")


def _commands(repo_root: Path) -> dict[str, list[str]]:
    root = str(repo_root)
    return {
        "component": [
            "component",
            "register",
            "--repo-root",
            root,
            "--id",
            _COMPONENT_ID,
            "--path",
            "src/fixture",
            "--label",
            "Fixture Core",
            "--kind",
            "library",
            "--responsibility",
            "Owns the fresh-install fixture component boundary for governed authoring order proof.",
            "--boundary",
            "Local fixture code path only; no runtime secrets or customer data boundary is crossed.",
            "--dependency",
            "Depends on installed Odylith governance CLI writers being available in a fresh consumer repo.",
            "--interface",
            "Exposes a Registry component record used by Atlas, Radar, and Casebook fixture links.",
            "--validation",
            "Validated by the first install governance order matrix and follow-on sync proof.",
            "--risk",
            "Operational risk is first-run authoring failure; security and compliance risk is limited to local fixture metadata with no credentials, private data, or regulated data.",
        ],
        "backlog": [
            "backlog",
            "create",
            "--repo-root",
            root,
            "--title",
            _UMBRELLA_TITLE,
            "--title",
            _CHILD_TITLE_ONE,
            "--title",
            _CHILD_TITLE_TWO,
            "--workstream-type",
            "umbrella",
            "--problem",
            "Operators need first install authoring to work even when no governance records exist yet.",
            "--customer",
            "Maintainers validating a fresh Odylith install.",
            "--opportunity",
            "Prove each governed surface can be created without depending on a hidden order.",
            "--product-view",
            "The CLI should create grounded records with clear refresh behavior.",
            "--success-metrics",
            "Each command exits zero and its source truth exists after the order matrix.",
            "--domain-risk",
            "Operational risk is hidden first-install ordering dependence; policy risk is low because fixture records stay local and contain no regulated data.",
            "--security-posture",
            "Security posture is local-only fixture metadata with no credentials, secrets, permissions, private user data, or external network access.",
        ],
        "atlas": [
            "atlas",
            "scaffold",
            "--repo-root",
            root,
            "--diagram-id",
            _DIAGRAM_ID,
            "--slug",
            _DIAGRAM_SLUG,
            "--title",
            "First Install Order Fixture",
            "--kind",
            "flowchart",
            "--owner",
            "governance",
            "--summary",
            "Draft diagram created before or after other governance truth without orphan failures.",
            "--component",
            "Fixture Core::Registered component boundary",
            "--watch",
            f"odylith/atlas/source/{_DIAGRAM_SLUG}.mmd",
        ],
        "bug": [
            "bug",
            "capture",
            "--repo-root",
            root,
            "--title",
            _BUG_TITLE,
            "--component",
            _COMPONENT_ID,
            "--severity",
            "P2",
            "--reproducibility",
            "Always",
            "--impact",
            "Fresh installs cannot trust authoring order when commands fail on empty truth.",
            "--environment",
            "fresh installed consumer repo",
            "--detected-by",
            "integration order matrix",
            "--failure-signature",
            "any governance command exits non-zero on empty first install truth",
            "--trigger-path",
            "first install governance authoring matrix",
            "--ownership",
            "governance authoring CLI",
            "--blast-radius",
            "new Odylith adopters creating first records",
            "--slo-impact",
            "operational risk blocks first-run setup confidence",
            "--data-risk",
            "Low data risk; local fixture only.",
            "--security-compliance",
            "Security/compliance posture is local-only fixture metadata with no credentials, secrets, private user data, or regulated data.",
            "--invariant-violated",
            "first-class governance commands must tolerate empty first install truth",
            "--regression-tests-added",
            "first install governance order matrix",
        ],
        "compass": [
            "compass",
            "log",
            "--repo-root",
            root,
            "--kind",
            "implementation",
            "--summary",
            _COMPASS_SUMMARY,
        ],
    }


def _dependent_record_commands(repo_root: Path, *, umbrella_id: str, child_id: str) -> tuple[list[str], ...]:
    root = str(repo_root)
    return (
        [
            "release",
            "create",
            "--repo-root",
            root,
            _RELEASE_ID,
            "--version",
            "0.0.0-fixture",
            "--name",
            "First install order fixture release",
            "--json",
        ],
        [
            "release",
            "add",
            "--repo-root",
            root,
            umbrella_id,
            _RELEASE_ID,
            "--note",
            "First install order matrix release assignment.",
            "--json",
        ],
        [
            "program",
            "create",
            "--repo-root",
            root,
            umbrella_id,
            "--json",
        ],
        [
            "wave",
            "create",
            "--repo-root",
            root,
            umbrella_id,
            _WAVE_ID,
            "--label",
            "First Install Order Fixture Wave",
            "--summary",
            "Execution wave created from a fresh install after surface records exist.",
            "--json",
        ],
        [
            "wave",
            "assign",
            "--repo-root",
            root,
            umbrella_id,
            _WAVE_ID,
            child_id,
            "--role",
            "primary",
            "--json",
        ],
    )


@pytest.mark.parametrize("order", _FIRST_COMMAND_ORDERS, ids=lambda order: " order=" + ">".join(order))
def test_first_install_governance_records_can_be_created_in_every_surface_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    order: tuple[str, ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir()
    _install_fresh_consumer_repo(monkeypatch, repo_root)

    commands = _commands(repo_root)
    for command_name in order:
        assert cli.main(commands[command_name]) == 0, command_name
        _assert_no_fake_first_install_ux_leaks(capsys.readouterr())

    workstream_ids = _created_workstream_ids(repo_root)
    for command in _dependent_record_commands(
        repo_root,
        umbrella_id=workstream_ids["umbrella"],
        child_id=workstream_ids["child_two"],
    ):
        assert cli.main(command) == 0, " ".join(command[:2])
        _assert_no_fake_first_install_ux_leaks(capsys.readouterr())

    assert cli.main(["sync", "--repo-root", str(repo_root), "--proceed-with-overlap", "--force", "--impact-mode", "full"]) == 0
    _assert_no_fake_first_install_ux_leaks(capsys.readouterr())

    _assert_created_truth_and_surfaces(repo_root, workstream_ids=workstream_ids)


def _created_workstream_ids(repo_root: Path) -> dict[str, str]:
    titles_to_keys = {
        _UMBRELLA_TITLE: "umbrella",
        _CHILD_TITLE_ONE: "child_one",
        _CHILD_TITLE_TWO: "child_two",
    }
    ids: dict[str, str] = {}
    idea_paths = list((repo_root / "odylith" / "radar" / "source" / "ideas").rglob("*.md"))
    for path in idea_paths:
        text = path.read_text(encoding="utf-8")
        key = next((value for title, value in titles_to_keys.items() if title in text), "")
        if not key:
            continue
        for raw_line in text.splitlines():
            if raw_line.startswith("idea_id:"):
                ids[key] = raw_line.split(":", 1)[1].strip()
    if set(ids) != set(titles_to_keys.values()):
        raise AssertionError(f"created workstream ids not found: {ids}")
    return ids


def _assert_created_truth_and_surfaces(repo_root: Path, *, workstream_ids: dict[str, str]) -> None:
    registry = json.loads((repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").read_text())
    assert [row["component_id"] for row in registry["components"]] == [_COMPONENT_ID]
    assert (repo_root / "odylith" / "registry" / "source" / "components" / _COMPONENT_ID / "CURRENT_SPEC.md").is_file()

    idea_paths = list((repo_root / "odylith" / "radar" / "source" / "ideas").rglob("*.md"))
    assert any(_UMBRELLA_TITLE in path.read_text(encoding="utf-8") for path in idea_paths)
    assert any(_CHILD_TITLE_ONE in path.read_text(encoding="utf-8") for path in idea_paths)
    assert any(_CHILD_TITLE_TWO in path.read_text(encoding="utf-8") for path in idea_paths)

    catalog = json.loads((repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").read_text())
    assert [row["diagram_id"] for row in catalog["diagrams"]] == [_DIAGRAM_ID]
    assert (repo_root / "odylith" / "atlas" / "source" / f"{_DIAGRAM_SLUG}.mmd").is_file()

    bug_paths = list((repo_root / "odylith" / "casebook" / "bugs").glob("*.md"))
    assert any(_BUG_TITLE in path.read_text(encoding="utf-8") for path in bug_paths)

    stream_path = repo_root / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl"
    assert _COMPASS_SUMMARY in stream_path.read_text(encoding="utf-8")

    releases = json.loads((repo_root / "odylith" / "radar" / "source" / "releases" / "releases.v1.json").read_text())
    assert [row["release_id"] for row in releases["releases"]] == [_RELEASE_ID]
    release_events = repo_root / "odylith" / "radar" / "source" / "releases" / "release-assignment-events.v1.jsonl"
    assert workstream_ids["umbrella"] in release_events.read_text(encoding="utf-8")
    assert _RELEASE_ID in release_events.read_text(encoding="utf-8")

    program_path = repo_root / "odylith" / "radar" / "source" / "programs" / f"{workstream_ids['umbrella']}.execution-waves.v1.json"
    program = json.loads(program_path.read_text(encoding="utf-8"))
    assert program["umbrella_id"] == workstream_ids["umbrella"]
    assert [row["wave_id"] for row in program["waves"]] == ["W1", "W2", _WAVE_ID]
    custom_wave = next(row for row in program["waves"] if row["wave_id"] == _WAVE_ID)
    assert custom_wave["primary_workstreams"] == [workstream_ids["child_two"]]

    assert _COMPONENT_ID in (repo_root / "odylith" / "registry" / "registry-payload.v1.js").read_text(encoding="utf-8")
    assert _UMBRELLA_TITLE in (repo_root / "odylith" / "radar" / "backlog-payload.v1.js").read_text(encoding="utf-8")
    assert _DIAGRAM_ID in (repo_root / "odylith" / "atlas" / "mermaid-payload.v1.js").read_text(encoding="utf-8")
    assert _BUG_TITLE in (repo_root / "odylith" / "casebook" / "casebook-payload.v1.js").read_text(encoding="utf-8")
    assert _COMPASS_SUMMARY in (repo_root / "odylith" / "compass" / "runtime" / "current.v1.json").read_text(encoding="utf-8")
