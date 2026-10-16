from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_git_identity.py"
EXPECTED_NAME = "freedom-research"
EXPECTED_EMAIL = "freedom@freedompreetham.org"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_git_identity", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _run("git", "init", str(repo), cwd=tmp_path)
    _run("git", "config", "user.name", EXPECTED_NAME, cwd=repo)
    _run("git", "config", "user.email", EXPECTED_EMAIL, cwd=repo)
    _run("git", "config", "user.useConfigOnly", "true", cwd=repo)
    (repo / "README.md").write_text("# Test\n", encoding="utf-8")
    _run("git", "add", "README.md", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)
    return repo


def test_config_validation_accepts_canonical_local_identity(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)

    assert module.main(["config", "--repo-root", str(repo)]) == 0


def test_config_validation_rejects_wrong_local_email(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    _run("git", "config", "user.email", "wrong@example.com", cwd=repo)

    assert module.main(["config", "--repo-root", str(repo)]) == 1
    stderr = capsys.readouterr().err
    assert "local user.email must be" in stderr


def test_history_validation_accepts_external_human_contributor(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    _run("git", "config", "user.name", "Thejesh", cwd=repo)
    _run("git", "config", "user.email", "thejesh23@users.noreply.github.com", cwd=repo)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "external contribution", cwd=repo)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_rejects_partial_maintainer_identity(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": EXPECTED_NAME,
        "GIT_AUTHOR_EMAIL": "wrong@example.com",
        "GIT_COMMITTER_NAME": EXPECTED_NAME,
        "GIT_COMMITTER_EMAIL": "wrong@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "mismatched maintainer alias", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "maintainer authorship must use the exact" in stderr
    assert "maintainer committer identity must use the exact" in stderr


def test_history_validation_rejects_partial_maintainer_committer_only(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "External Contributor",
        "GIT_AUTHOR_EMAIL": "contributor@example.com",
        "GIT_COMMITTER_NAME": EXPECTED_NAME,
        "GIT_COMMITTER_EMAIL": "wrong@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "mismatched maintainer committer", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "maintainer committer identity must use the exact" in stderr


def test_history_validation_rejects_case_variant_maintainer_impersonation(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Freedom-Research",
        "GIT_AUTHOR_EMAIL": "wrong@example.com",
        "GIT_COMMITTER_NAME": "Freedom-Research",
        "GIT_COMMITTER_EMAIL": "wrong@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "case variant impersonation", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "maintainer authorship must use the exact" in stderr
    assert "maintainer committer identity must use the exact" in stderr


def test_history_validation_rejects_maintainer_prefix_impersonation(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "freedom_research-bot",
        "GIT_AUTHOR_EMAIL": "wrong@example.com",
        "GIT_COMMITTER_NAME": "freedom_research-bot",
        "GIT_COMMITTER_EMAIL": "wrong@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "maintainer prefix impersonation", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "maintainer authorship must use the exact" in stderr


def test_history_validation_rejects_collapsed_maintainer_and_greek_assistant_homographs(
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "freedomresearch-bot",
        "GIT_AUTHOR_EMAIL": "wrong@example.com",
        "GIT_COMMITTER_NAME": "Cοdex Agent",
        "GIT_COMMITTER_EMAIL": "automation@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "homograph impersonation", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "maintainer authorship must use the exact" in stderr
    assert "committer identity must not use an assistant" in stderr


def test_history_validation_rejects_assistant_author_identity(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "OpenAI Codex",
        "GIT_AUTHOR_EMAIL": "codex@openai.com",
        "GIT_COMMITTER_NAME": "OpenAI Codex",
        "GIT_COMMITTER_EMAIL": "codex@openai.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "assistant-authored commit", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author identity must not use an assistant" in stderr
    assert "committer identity must not use an assistant" in stderr


def test_history_validation_rejects_numbered_assistant_bot_identity(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "github-copilot[bot]",
        "GIT_AUTHOR_EMAIL": "12345+github-copilot[bot]@users.noreply.github.com",
        "GIT_COMMITTER_NAME": "github-copilot[bot]",
        "GIT_COMMITTER_EMAIL": "12345+github-copilot[bot]@users.noreply.github.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "assistant bot commit", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author identity must not use an assistant" in stderr
    assert "committer identity must not use an assistant" in stderr


def test_history_validation_rejects_obfuscated_assistant_identity(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "OpenAI Co\u200bdex Agent",
        "GIT_AUTHOR_EMAIL": "automation@example.com",
        "GIT_COMMITTER_NAME": "OpenAI Co\u200bdex Agent",
        "GIT_COMMITTER_EMAIL": "automation@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "obfuscated assistant identity", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author identity must not use an assistant" in stderr


def test_history_validation_rejects_assistant_brand_email_with_human_name(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "External Human",
        "GIT_AUTHOR_EMAIL": "gemini@google.com",
        "GIT_COMMITTER_NAME": "External Human",
        "GIT_COMMITTER_EMAIL": "gemini@google.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "assistant email identity", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author identity must not use an assistant" in stderr


def test_history_validation_rejects_generic_assistant_identity(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "AI Agent",
        "GIT_AUTHOR_EMAIL": "automation@example.com",
        "GIT_COMMITTER_NAME": "LLM Assistant",
        "GIT_COMMITTER_EMAIL": "automation@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "generic assistant identity", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author identity must not use an assistant" in stderr
    assert "committer identity must not use an assistant" in stderr


def test_history_validation_rejects_additional_coding_tool_identities(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Aider Bot",
        "GIT_AUTHOR_EMAIL": "aider-bot@example.com",
        "GIT_COMMITTER_NAME": "Amazon Q Developer",
        "GIT_COMMITTER_EMAIL": "amazon-q@amazon.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "coding tool identity", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author identity must not use an assistant" in stderr
    assert "committer identity must not use an assistant" in stderr


def test_history_validation_rejects_model_and_replit_agent_identities(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "GPT-5",
        "GIT_AUTHOR_EMAIL": "human@example.com",
        "GIT_COMMITTER_NAME": "Replit Agent",
        "GIT_COMMITTER_EMAIL": "automation@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "model identity", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author identity must not use an assistant" in stderr
    assert "committer identity must not use an assistant" in stderr


def test_history_validation_rejects_assistant_vendor_subdomain(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Claude",
        "GIT_AUTHOR_EMAIL": "service@agents.anthropic.com",
        "GIT_COMMITTER_NAME": "Claude",
        "GIT_COMMITTER_EMAIL": "service@agents.anthropic.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "vendor subdomain identity", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author identity must not use an assistant" in stderr


def test_history_validation_allows_human_name_matching_assistant_brand(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Gemini",
        "GIT_AUTHOR_EMAIL": "gemini.human@example.com",
        "GIT_COMMITTER_NAME": "Gemini",
        "GIT_COMMITTER_EMAIL": "gemini.human@example.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "human contribution", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_allows_human_brand_local_part_on_neutral_domain(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Claude Dupont",
        "GIT_AUTHOR_EMAIL": "claude@example.org",
        "GIT_COMMITTER_NAME": "Claude Dupont",
        "GIT_COMMITTER_EMAIL": "claude@example.org",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "human contribution", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_allows_human_brand_name_in_github_privacy_email(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Gemini Patel",
        "GIT_AUTHOR_EMAIL": "123+gemini-patel@users.noreply.github.com",
        "GIT_COMMITTER_NAME": "Gemini Patel",
        "GIT_COMMITTER_EMAIL": "123+gemini-patel@users.noreply.github.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "human contribution", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_allows_human_review_trailer_with_github_privacy_email(
    tmp_path: Path,
) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "human review",
        "-m",
        "Reviewed-By: Gemini Patel <456+gemini-patel@users.noreply.github.com>",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_allows_human_coauthor_trailer(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "paired contribution",
        "-m",
        "Co-Authored-By: Example Contributor <contributor@example.com>",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_allows_human_coauthor_with_brand_substring(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "paired contribution",
        "-m",
        "Co-Authored-By: Codexter Smith <person@example.com>",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_allows_human_review_trailer_with_brand_given_name(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "human review",
        "-m",
        "Reviewed-By: Gemini Patel",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_rejects_assistant_attribution_trailer(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "assistant attribution",
        "-m",
        "Co-Authored-By: OpenAI Codex <codex@openai.com>",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "commit message must not attribute work to an assistant" in stderr


def test_history_validation_rejects_folded_assistant_review_trailer(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "assistant review attribution",
        "-m",
        "Reviewed-By:\n OpenAI Codex <codex@openai.com>",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "commit message must not attribute work to an assistant" in stderr


def test_history_validation_rejects_unicode_hyphen_assistant_trailer(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "assistant attribution",
        "-m",
        "Co‑Authored‑By: OpenAI Codex <codex@openai.com>",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "commit message must not attribute work to an assistant" in stderr


def test_history_validation_rejects_generated_with_attribution(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "generated attribution",
        "-m",
        "Generated with OpenAI Codex",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "commit message must not attribute work to an assistant" in stderr


def test_history_validation_rejects_generated_by_attribution_in_prose(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "assistant attribution",
        "-m",
        "This commit was generated by OpenAI Codex.",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "commit message must not attribute work to an assistant" in stderr


def test_history_validation_rejects_hyphenated_generated_with_attribution(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "assistant attribution",
        "-m",
        "Generated-With: OpenAI Codex",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "commit message must not attribute work to an assistant" in stderr


def test_history_validation_rejects_reviewed_by_attribution_in_prose(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "assistant review attribution",
        "-m",
        "This patch was reviewed by OpenAI Codex.",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "commit message must not attribute work to an assistant" in stderr


def test_history_validation_rejects_affirmative_no_doubt_attribution(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "No doubt generated with OpenAI Codex.",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "commit message must not attribute work to an assistant" in stderr


def test_history_validation_allows_negated_assistant_attribution_statement(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "This patch was not reviewed by OpenAI Codex.",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_allows_non_assistant_generation_detail(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "Generated with deterministic seed 42.", cwd=repo)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_allows_non_assistant_generated_by_prose(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "Observations were generated by Gemini telescope instruments.",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_allows_policy_discussion_of_prohibited_trailer(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run(
        "git",
        "commit",
        "-m",
        "Policy forbids `Co-Authored-By: OpenAI Codex <codex@openai.com>`.",
        cwd=repo,
    )

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_accepts_canonical_author_with_github_committer(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": EXPECTED_NAME,
        "GIT_AUTHOR_EMAIL": EXPECTED_EMAIL,
        "GIT_COMMITTER_NAME": "GitHub",
        "GIT_COMMITTER_EMAIL": "noreply@github.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "merged", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_accepts_bounded_legacy_author_with_github_committer(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Freedom Preetham",
        "GIT_AUTHOR_EMAIL": EXPECTED_EMAIL,
        "GIT_COMMITTER_NAME": "GitHub",
        "GIT_COMMITTER_EMAIL": "noreply@github.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "merged", cwd=repo, env=env)
    cutoff = _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    monkeypatch.setattr(module, "LEGACY_MAINTAINER_HISTORY_CUTOFF", cutoff)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_rejects_fresh_legacy_alias_after_cutoff(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    cutoff = _run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    monkeypatch.setattr(module, "LEGACY_MAINTAINER_HISTORY_CUTOFF", cutoff)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Freedom Preetham",
        "GIT_AUTHOR_EMAIL": EXPECTED_EMAIL,
        "GIT_COMMITTER_NAME": "GitHub",
        "GIT_COMMITTER_EMAIL": "noreply@github.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "fresh legacy alias", cwd=repo, env=env)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "maintainer authorship must use the exact" in stderr


def test_history_validation_rejects_mailmap_laundered_assistant_identity(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    assistant_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "OpenAI Codex",
        "GIT_AUTHOR_EMAIL": "codex@openai.com",
        "GIT_COMMITTER_NAME": "OpenAI Codex",
        "GIT_COMMITTER_EMAIL": "codex@openai.com",
    }
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "assistant commit", cwd=repo, env=assistant_env)
    (repo / ".mailmap").write_text(
        f"{EXPECTED_NAME} <{EXPECTED_EMAIL}> OpenAI Codex <codex@openai.com>\n",
        encoding="utf-8",
    )
    _run("git", "add", ".mailmap", cwd=repo)
    _run("git", "commit", "-m", "mailmap", cwd=repo)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 1
    stderr = capsys.readouterr().err
    assert "author identity must not use an assistant" in stderr
    assert "committer identity must not use an assistant" in stderr


def test_history_validation_accepts_record_separator_in_message(tmp_path: Path) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "record\x1eseparator", cwd=repo)

    assert module.main(["history", "--repo-root", str(repo), "HEAD"]) == 0


def test_history_validation_rejects_revision_options(tmp_path: Path, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)

    assert module.main(["history", "--repo-root", str(repo), "--", "--max-count=0"]) == 2
    stderr = capsys.readouterr().err
    assert "revision selectors must not start with '-'" in stderr


def test_github_validation_accepts_canonical_account(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)

    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/gh" if name == "gh" else None)

    def fake_run_command(repo_root: Path, args: list[str]) -> str:
        assert repo_root == repo
        if args == ["gh", "api", "user"]:
            return json.dumps({"login": EXPECTED_NAME, "email": EXPECTED_EMAIL})
        if args == ["gh", "repo", "view", "odylith/odylith", "--json", "viewerPermission"]:
            return json.dumps({"viewerPermission": "ADMIN"})
        raise AssertionError(args)

    monkeypatch.setattr(module, "_run_command", fake_run_command)

    assert module.main(["github", "--repo-root", str(repo)]) == 0


def test_github_validation_rejects_wrong_account(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_module()
    repo = _init_repo(tmp_path)

    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/gh" if name == "gh" else None)

    def fake_run_command(repo_root: Path, args: list[str]) -> str:
        assert repo_root == repo
        if args == ["gh", "api", "user"]:
            return json.dumps({"login": "wrong-account", "email": "wrong@example.com"})
        if args == ["gh", "repo", "view", "odylith/odylith", "--json", "viewerPermission"]:
            return json.dumps({"viewerPermission": "READ"})
        raise AssertionError(args)

    monkeypatch.setattr(module, "_run_command", fake_run_command)

    assert module.main(["github", "--repo-root", str(repo)]) == 1
    stderr = capsys.readouterr().err
    assert "GitHub login must be 'freedom-research'" in stderr
    assert "GitHub email must be 'freedom@freedompreetham.org'" in stderr
    assert "GitHub permission for odylith/odylith must be" in stderr
