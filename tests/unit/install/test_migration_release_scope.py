"""Real Git scope must survive commits and fail closed when unavailable."""

from pathlib import Path
import subprocess

import pytest

from odylith.install import migration_observer


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=True,
    )
    return result.stdout.decode().strip()


def _commit(root: Path) -> str:
    _git(root, "add", "--all")
    _git(root, "commit", "-qm", "Fixture checkpoint")
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "freedom-research")
    _git(root, "config", "user.email", "freedom@freedompreetham.org")
    (root / "README.md").write_text("Published behavior.\n", encoding="utf-8")
    base = _commit(root)
    _git(root, "tag", "v1.0.0")
    return root, base


def _observe(root: Path, **kwargs: object):
    return migration_observer.observe_surface_migration_needs(
        repo_root=root, target_version="1.0.1", **kwargs,
    )


def test_missing_git_is_not_a_successful_empty_observation(tmp_path: Path) -> None:
    report = _observe(tmp_path)
    assert not report.ok
    assert report.scope_error
    assert report.as_dict()["scope"]["kind"] == "unavailable"


def test_release_scope_preserves_obligation_across_commit(repository) -> None:
    root, base = repository
    (root / "README.md").write_text("Changed supported behavior.\n", encoding="utf-8")
    dirty = _observe(root, base_ref="v1.0.0", require_release_scope=True)
    candidate = _commit(root)
    clean = _observe(root, base_ref="v1.0.0", require_release_scope=True)

    assert not dirty.ok and not clean.ok
    assert dirty.changed_paths == clean.changed_paths == ("README.md",)
    assert dirty.needs == clean.needs
    assert clean.base_commit == base
    assert clean.candidate_commit == candidate
    assert clean.scope_kind == "release_comparison"


def test_completed_assessment_survives_commit_but_not_changed_content(repository) -> None:
    root, _ = repository
    (root / "README.md").write_text("New supported behavior.\n", encoding="utf-8")
    first = _observe(root, base_ref="v1.0.0")
    record = root / "odylith/radar/source/ideas/assessment.md"
    record.parent.mkdir(parents=True)
    marker = first.needs[0].governance_marker
    record.write_text(
        f"status: finished\nidea_id: B-999\ntitle: Release assessment\n\n{marker}\n",
        encoding="utf-8",
    )
    _commit(root)
    assert _observe(root, base_ref="v1.0.0").ok
    (root / "README.md").write_text("A different supported behavior.\n", encoding="utf-8")
    changed = _observe(root, base_ref="v1.0.0")
    assert not changed.ok
    assert changed.needs[0].governance_marker != marker


def test_release_scope_combines_committed_staged_unstaged_and_untracked(repository) -> None:
    root, _ = repository
    docs = root / "docs"
    docs.mkdir()
    (docs / "committed.md").write_text("Committed\n", encoding="utf-8")
    _commit(root)
    (docs / "staged.md").write_text("Staged\n", encoding="utf-8")
    _git(root, "add", "docs/staged.md")
    (root / "README.md").write_text("Unstaged\n", encoding="utf-8")
    (docs / "untracked.md").write_text("Untracked\n", encoding="utf-8")
    report = _observe(root, base_ref="v1.0.0")
    assert set(report.changed_paths) == {
        "README.md", "docs/committed.md", "docs/staged.md", "docs/untracked.md",
    }


def test_committed_rename_keeps_deleted_source_in_scope(repository) -> None:
    root, _ = repository
    _git(root, "mv", "README.md", "retired-readme.txt")
    _commit(root)
    report = _observe(root, base_ref="v1.0.0")
    assert "README.md" in report.changed_paths
    assert "public-docs-and-release-guidance" in report.blocked_need_ids


@pytest.mark.parametrize("name", ['with space.md', 'quoted"file.md', 'line\nbreak.md'])
def test_git_paths_are_not_porcelain_display_strings(repository, name: str) -> None:
    root, _ = repository
    docs = root / "docs"
    docs.mkdir()
    (docs / name).write_text("New guidance\n", encoding="utf-8")
    report = _observe(root, base_ref="v1.0.0")
    assert report.changed_paths == (f"docs/{name}",)
    marker = report.needs[0].governance_marker
    _commit(root)
    assert _observe(root, base_ref="v1.0.0").needs[0].governance_marker == marker


@pytest.mark.parametrize("base_ref", ["", "absent-ref", "--help"])
def test_release_scope_refuses_missing_or_invalid_baseline(repository, base_ref: str) -> None:
    root, _ = repository
    report = _observe(root, base_ref=base_ref, require_release_scope=True)
    assert not report.ok
    assert report.scope_error
    assert report.scope_kind == "unavailable"


def test_release_scope_cannot_be_narrowed_by_injected_paths(repository) -> None:
    root, _ = repository
    report = _observe(root, base_ref="v1.0.0", changed_paths=())
    assert not report.ok
    assert report.scope_error


def test_valid_unchanged_release_scope_retains_comparison_evidence(repository) -> None:
    root, base = repository
    report = _observe(root, base_ref="v1.0.0", require_release_scope=True)
    assert report.ok
    assert report.changed_paths == report.needs == ()
    assert report.base_commit == report.candidate_commit == base
    assert report.scope_kind == "release_comparison"
    assert not report.scope_error


def test_sibling_published_release_uses_endpoint_trees_not_merge_base(repository) -> None:
    root, base = repository
    (root / "README.md").write_text("Published release preparation\n", encoding="utf-8")
    published = _commit(root)
    _git(root, "checkout", "--detach", base)
    (root / "README.md").write_text("Next release candidate\n", encoding="utf-8")
    candidate = _commit(root)
    report = _observe(root, base_ref=published)
    assert not report.ok
    assert not report.scope_error
    assert report.scope_kind == "release_comparison"
    assert report.base_commit == published
    assert report.candidate_commit == candidate
    assert report.changed_paths == ("README.md",)


def test_worktree_only_observation_is_explicitly_diagnostic(repository) -> None:
    root, _ = repository
    report = _observe(root)
    assert report.ok
    assert report.scope_kind == "working_tree"
    assert not report.base_commit


def test_release_assessment_binds_predecessor_and_file_mode(repository) -> None:
    root, base = repository
    (root / "README.md").write_text("Intermediate contract\n", encoding="utf-8")
    intermediate = _commit(root)
    (root / "README.md").write_text("Candidate contract\n", encoding="utf-8")
    earlier = _observe(root, base_ref=base)
    later = _observe(root, base_ref=intermediate)
    assert earlier.needs[0].governance_marker != later.needs[0].governance_marker
    (root / "README.md").chmod(0o755)
    mode_change = _observe(root, base_ref=base)
    assert mode_change.needs[0].governance_marker != earlier.needs[0].governance_marker


def test_git_path_identity_preserves_backslash_and_trailing_space(repository) -> None:
    root, _ = repository
    path = root / "docs" / "literal\\name.md "
    path.parent.mkdir()
    path.write_text("Supported guidance\n", encoding="utf-8")
    report = _observe(root, base_ref="v1.0.0")
    assert report.changed_paths == ("docs/literal\\name.md ",)
    first_marker = report.needs[0].governance_marker
    path.write_text("Changed guidance\n", encoding="utf-8")
    assert _observe(root, base_ref="v1.0.0").needs[0].governance_marker != first_marker


@pytest.mark.parametrize("flag", ["--skip-worktree", "--assume-unchanged"])
def test_hidden_tracked_content_cannot_be_assessed_as_deleted(repository, flag: str) -> None:
    root, _ = repository
    (root / "README.md").write_text("Changed candidate contract\n", encoding="utf-8")
    _commit(root)
    _git(root, "update-index", flag, "README.md")
    (root / "README.md").unlink()
    report = _observe(root, base_ref="v1.0.0")
    assert not report.ok
    assert report.scope_kind == "unavailable"
    assert "hidden tracked" in report.scope_error
