from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_engineering_notes_runtime as engineering_notes_runtime


def test_load_make_target_notes_uses_make_target_regex_and_ignores_special_targets(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    (repo_root / "Makefile").write_text(
        "\n".join(
            [
                "# Build the project",
                "build:",
                "\t@echo build",
                "",
                "# Hidden target",
                ".PHONY: build",
                "",
                "# Pattern target",
                "%.o: %.c",
                "",
                "# Nested target",
                "subdir/task:",
                "\t@echo skip",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    mk_dir = repo_root / "mk"
    mk_dir.mkdir()
    (mk_dir / "extra.mk").write_text(
        "\n".join(
            [
                "# Package artifacts",
                "package-release:",
                "\t@echo package",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = engineering_notes_runtime._load_make_target_notes(  # noqa: SLF001
        repo_root=repo_root,
        component_rows=(),
    )

    by_id = {row["note_id"]: row for row in rows}
    assert "make:Makefile:build" in by_id
    assert by_id["make:Makefile:build"]["summary"] == "Build the project"
    assert by_id["make:Makefile:build"]["path_refs"] == ["Makefile"]
    assert "make:mk/extra.mk:package-release" in by_id
    assert by_id["make:mk/extra.mk:package-release"]["summary"] == "Package artifacts"
    assert all(".PHONY" not in row["note_id"] for row in rows)
    assert all("%.o" not in row["note_id"] for row in rows)
    assert all("subdir/task" not in row["note_id"] for row in rows)
