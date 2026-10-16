from __future__ import annotations

import copy
import json
import stat
from pathlib import Path

import pytest

from odylith import cli
from odylith.runtime.governance import component_authoring
from odylith.runtime.governance import component_cli
from odylith.runtime.governance import component_description_update


def _seed_registry(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    registry_path = tmp_path / "odylith/registry/source/component_registry.v1.json"
    spec_path = tmp_path / "odylith/registry/source/components/target/CURRENT_SPEC.md"
    payload: dict[str, object] = {
        "version": "v1",
        "catalog_note": "preserve me",
        "components": [
            {
                "component_id": "target",
                "name": "Target",
                "what_it_is": "Old description.",
                "owner": "product",
                "nested": {"z": 1, "a": 2},
            },
            {
                "component_id": "other",
                "name": "Other",
                "what_it_is": "Other description.",
                "owner": "platform",
            },
        ],
        "tail": ["unchanged"],
    }
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# Target\n\nSentinel spec.\n", encoding="utf-8")
    return registry_path, spec_path, payload


def test_cli_updates_only_description_preserves_spec_and_refreshes_once(monkeypatch, tmp_path: Path, capsys) -> None:
    registry_path, spec_path, before = _seed_registry(tmp_path)
    registry_path.chmod(0o640)
    before_spec = spec_path.read_bytes()
    refreshes: list[dict[str, object]] = []
    monkeypatch.setattr(
        component_description_update.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **kwargs: refreshes.append(kwargs),
    )
    monkeypatch.setattr(
        component_description_update.owned_surface_refresh,
        "print_dashboard_handoff",
        lambda **_kwargs: None,
    )

    rc = cli.main(
        [
            "component",
            "update-description",
            "--id",
            "target",
            "--what-it-is",
            "Current description.",
            "--repo-root",
            str(tmp_path),
        ]
    )

    assert rc == 0
    after = json.loads(registry_path.read_text(encoding="utf-8"))
    expected = copy.deepcopy(before)
    expected["components"][0]["what_it_is"] = "Current description."  # type: ignore[index]
    assert after == expected
    assert list(after) == list(before)
    assert list(after["components"][0]) == list(before["components"][0])  # type: ignore[index]
    assert stat.S_IMODE(registry_path.stat().st_mode) == 0o640
    assert spec_path.read_bytes() == before_spec
    assert refreshes == [
        {
            "repo_root": tmp_path.resolve(),
            "surface": "registry",
            "operation_label": "Component description update",
        }
    ]
    assert "odylith component update-description updated" in capsys.readouterr().out


def test_cli_dry_run_json_does_not_write_or_refresh(monkeypatch, tmp_path: Path, capsys) -> None:
    registry_path, spec_path, _payload = _seed_registry(tmp_path)
    before_registry = registry_path.read_bytes()
    before_spec = spec_path.read_bytes()
    monkeypatch.setattr(
        component_description_update.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("dry-run refreshed Registry")),
    )

    rc = cli.main(
        [
            "component",
            "update-description",
            f"--repo-root={tmp_path}",
            "--id",
            "target",
            "--what-it-is",
            "Preview description.",
            "--dry-run",
            "--json",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert output["mode"] == "dry-run"
    assert output["component_id"] == "target"
    assert output["previous_what_it_is"] == "Old description."
    assert output["what_it_is"] == "Preview description."
    assert registry_path.read_bytes() == before_registry
    assert spec_path.read_bytes() == before_spec


@pytest.mark.parametrize(
    ("component_id", "description", "message"),
    [
        ("", "Valid.", "non-empty exact"),
        (" target", "Valid.", "non-empty exact"),
        ("unknown", "Valid.", "Unknown Registry component ID"),
        ("target", "   ", "must not be blank"),
    ],
)
def test_invalid_target_or_description_fails_before_write(
    monkeypatch,
    tmp_path: Path,
    component_id: str,
    description: str,
    message: str,
) -> None:
    registry_path, spec_path, _payload = _seed_registry(tmp_path)
    before_registry = registry_path.read_bytes()
    before_spec = spec_path.read_bytes()
    monkeypatch.setattr(
        component_description_update,
        "atomic_write_bytes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("invalid input wrote Registry")),
    )

    with pytest.raises(ValueError, match=message):
        component_description_update.update_description(
            repo_root=tmp_path,
            component_id=component_id,
            what_it_is=description,
        )

    assert registry_path.read_bytes() == before_registry
    assert spec_path.read_bytes() == before_spec


@pytest.mark.parametrize(
    "payload",
    [
        "{not json",
        "[]",
        '{"components": {}}',
        '{"components": ["not an object"]}',
        '{"components": [{"component_id": "target", "what_it_is": ""}]}',
        (
            '{"components": ['
            '{"component_id": "target", "what_it_is": "One."},'
            '{"component_id": "target", "what_it_is": "Two."}'
            "]}"
        ),
    ],
)
def test_malformed_or_duplicate_registry_fails_before_write(monkeypatch, tmp_path: Path, payload: str) -> None:
    registry_path = tmp_path / "odylith/registry/source/component_registry.v1.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(payload, encoding="utf-8")
    before = registry_path.read_bytes()
    monkeypatch.setattr(
        component_description_update,
        "atomic_write_bytes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("malformed Registry was overwritten")),
    )

    with pytest.raises(ValueError):
        component_description_update.update_description(
            repo_root=tmp_path,
            component_id="target",
            what_it_is="Replacement.",
        )

    assert registry_path.read_bytes() == before


@pytest.mark.parametrize("duplicate_flag", ["--id", "--what-it-is"])
def test_duplicate_cli_value_is_rejected_before_update(
    monkeypatch,
    tmp_path: Path,
    duplicate_flag: str,
) -> None:
    _seed_registry(tmp_path)
    monkeypatch.setattr(
        component_description_update,
        "update_description",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("duplicate CLI input reached update")),
    )
    argv = [
        "component",
        "update-description",
        "--repo-root",
        str(tmp_path),
        "--id",
        "target",
        "--what-it-is",
        "Replacement.",
        duplicate_flag,
        "duplicate",
    ]

    with pytest.raises(SystemExit) as excinfo:
        cli.main(argv)

    assert excinfo.value.code == 2


def test_main_branch_guard_blocks_before_component_dispatch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_guard_product_repo_main_branch", lambda **_kwargs: 19)
    monkeypatch.setattr(
        component_cli,
        "dispatch",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("blocked command dispatched")),
    )

    rc = cli.main(
        [
            "component",
            "update-description",
            "--repo-root",
            str(tmp_path),
            "--id",
            "target",
            "--what-it-is",
            "Replacement.",
        ]
    )

    assert rc == 19


@pytest.mark.parametrize(
    ("command", "expected_flag"),
    [("register", "--responsibility"), ("update-description", "--what-it-is")],
)
def test_component_backend_help_bypasses_write_guard(
    monkeypatch,
    capsys,
    command: str,
    expected_flag: str,
) -> None:
    monkeypatch.setattr(
        cli,
        "_guard_product_repo_main_branch",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("read-only help reached write guard")),
    )

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["component", command, "--help"])

    assert excinfo.value.code == 0
    assert expected_flag in capsys.readouterr().out


@pytest.mark.parametrize("parent_depth", range(4))
@pytest.mark.parametrize("dry_run", [False, True])
def test_registry_rejects_in_repo_symlink_at_every_path_segment(
    monkeypatch, tmp_path: Path, parent_depth: int, dry_run: bool
) -> None:
    registry_path, spec_path, _payload = _seed_registry(tmp_path)
    before_registry = registry_path.read_bytes()
    before_spec = spec_path.read_bytes()
    linked_path = registry_path if parent_depth == 0 else registry_path.parents[parent_depth - 1]
    target = tmp_path / "unrelated-target"
    is_directory = linked_path.is_dir()
    linked_path.rename(target)
    linked_path.symlink_to(target, target_is_directory=is_directory)
    monkeypatch.setattr(
        component_description_update,
        "atomic_write_bytes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("redirected write")),
    )
    monkeypatch.setattr(
        component_description_update.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("redirected refresh")),
    )

    with pytest.raises(ValueError, match="symlink"):
        component_description_update.update_description(
            repo_root=tmp_path,
            component_id="target",
            what_it_is="Replacement.",
            dry_run=dry_run,
        )

    assert registry_path.read_bytes() == before_registry
    assert spec_path.read_bytes() == before_spec


def test_registry_symlink_cannot_escape_repo_root(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    external_odylith = tmp_path / "external-odylith"
    external_registry = external_odylith / "registry/source/component_registry.v1.json"
    external_registry.parent.mkdir(parents=True)
    external_registry.write_text(
        '{"components": [{"component_id": "target", "what_it_is": "Old."}]}\n',
        encoding="utf-8",
    )
    repo_root.mkdir()
    (repo_root / "odylith").symlink_to(external_odylith, target_is_directory=True)
    before = external_registry.read_bytes()
    monkeypatch.setattr(
        component_description_update,
        "atomic_write_bytes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("escaped Registry was written")),
    )

    with pytest.raises(ValueError, match="symlink"):
        component_description_update.update_description(
            repo_root=repo_root,
            component_id="target",
            what_it_is="Replacement.",
        )

    assert external_registry.read_bytes() == before


def test_refresh_failure_reports_that_description_was_already_written(monkeypatch, tmp_path: Path, capsys) -> None:
    registry_path, _spec_path, _payload = _seed_registry(tmp_path)
    monkeypatch.setattr(
        component_description_update.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("Component description update succeeded, but Registry refresh failed; retry registry refresh.")
        ),
    )

    rc = cli.main(
        [
            "component",
            "update-description",
            "--repo-root",
            str(tmp_path),
            "--id",
            "target",
            "--what-it-is",
            "Written before refresh.",
        ]
    )

    assert rc == 1
    assert json.loads(registry_path.read_text(encoding="utf-8"))["components"][0]["what_it_is"] == (
        "Written before refresh."
    )
    assert "succeeded, but Registry refresh failed" in capsys.readouterr().out


def test_register_route_and_backend_help_remain_owned_by_register_backend(monkeypatch, tmp_path: Path, capsys) -> None:
    forwarded: list[str] = []
    monkeypatch.setattr(component_authoring, "main", lambda argv: forwarded.extend(argv) or 0)

    rc = cli.main(["component", "register", f"--repo-root={tmp_path}", "--id", "new-component"])

    assert rc == 0
    assert forwarded == ["--repo-root", str(tmp_path), "--id", "new-component"]

    monkeypatch.undo()
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["component", "register", "--help"])
    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "usage: odylith component register" in output
    assert "--responsibility" in output
    assert "--risk" in output
