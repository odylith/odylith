from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_local_release_assets_target_builds_maintainer_installable_assets() -> None:
    text = (REPO_ROOT / "bin" / "local-release-assets").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")

    assert "local-release-assets:" in makefile
    assert './bin/local-release-assets "$(VERSION)" "$(DIST)"' in makefile
    assert 'requested_version="${1:-${VERSION:-$(current_source_version)}}"' in text
    assert 'dist_dir="${TMPDIR:-/tmp}/odylith-local-release-${requested_version}"' in text
    assert 'rm -rf "$dist_dir"' in text
    assert '"$odylith_python" -m hatch build --target wheel "$dist_dir"' in text
    assert 'scripts/release/publish_release_assets.py \\' in text
    assert '--tag "v${requested_version}"' in text
    assert '--dist-dir "$dist_dir"' in text
    assert "--allow-local" in text
    assert "scripts/release/platform_domain_leakage_check.py" in text
    assert '--repo-root "$odylith_repo_root" --dist-dir "$dist_dir"' in text
    assert "ODYLITH_RELEASE_BASE_URL=http://127.0.0.1:8123" in text
    assert 'ODYLITH_RELEASE_MAINTAINER_ROOT="${odylith_repo_root}"' in text
    assert "make local-release-assets" in help_text


def test_greenfield_post_confirm_matrix_target_runs_installed_release_gate() -> None:
    text = (REPO_ROOT / "bin" / "greenfield-post-confirm-matrix").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")
    shared = (REPO_ROOT / "bin" / "_odylith.sh").read_text(encoding="utf-8")

    assert "greenfield-post-confirm-matrix:" in makefile
    assert './bin/greenfield-post-confirm-matrix "$(VERSION)" "$(DIST)"' in makefile
    assert 'requested_version="${1:-${VERSION:-$(current_source_version)}}"' in text
    assert 'temp_parent="${TEMP_PARENT:-/Users/freedom/mock}"' in text
    assert 'scripts/release/greenfield_post_confirm_matrix.py \\' in text
    assert 'extra_args=(--include-rescue-smoke)' in text
    assert 'RESCUE_SMOKE:-1' in text
    assert '--skip-rescue-smoke' in text
    assert 'BROWSER_PROOF:-1' in text
    assert '--include-browser-proof' in text
    assert 'ensure_playwright_chromium' in text
    assert '"$odylith_python" -m playwright install chromium >/dev/null' in shared
    assert 'proof_json="${GREENFIELD_MATRIX_OUTPUT_JSON:-$dist_dir/greenfield-post-confirm-matrix.v1.json}"' in text
    assert "scripts/release/platform_domain_leakage_check.py" in text
    assert '--repo-root "$odylith_repo_root" --dist-dir "$dist_dir"' in text
    assert '--dist-dir "$dist_dir"' in text
    assert '--version "$requested_version"' in text
    assert '--temp-parent "$temp_parent"' in text
    assert '--output-json "$proof_json"' in text
    assert "make greenfield-post-confirm-matrix" in help_text
    assert "write greenfield-post-confirm-matrix.v1.json" in help_text
    assert "per-case generated browser surface state proof" in help_text
    assert "installed CLI auto-rescue wiring smoke" in help_text
    assert "BROWSER_PROOF=0 skips that lane only for local debugging" in help_text


def test_release_candidate_is_pr_safe_non_publishing_current_checkout_lane() -> None:
    text = (REPO_ROOT / "bin" / "release-candidate").read_text(encoding="utf-8")
    shared = (REPO_ROOT / "bin" / "_odylith.sh").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")

    assert 'resolved_version="${requested_version:-${VERSION:-$(current_source_version)}}"' in text
    assert "candidate proof must evaluate the checked-out source tree" in text
    assert "git restore -- AGENTS.md CLAUDE.md .agents .claude .codex odylith/compass/runtime" in text
    assert "git clean -fd -- .agents .claude .codex odylith/compass/runtime" in text
    assert 'require_clean_worktree' in text
    assert 'run_release_proof_steps "$resolved_version" "$dist_dir"' in text
    assert 'benchmark_override_mode="$(release_benchmark_override_mode "$resolved_version")"' in text
    assert "skip_proof_and_compare" in text
    assert "tracked maintainer override marks benchmark proof advisory for this exact release" in text
    assert 'benchmark compare --repo-root . --baseline last-shipped' in text
    assert 'scripts/release/greenfield_post_confirm_matrix.py \\' in shared
    assert "scripts/release/platform_domain_leakage_check.py" in shared
    assert 'ensure_playwright_chromium' in shared
    assert '--include-browser-proof' in shared
    assert '--output-json "$dist_dir/greenfield-post-confirm-matrix.v1.json"' in shared
    assert 'release_version_session.py' not in text
    assert 'release_worktree.py' not in text
    assert 'release-candidate:' in makefile
    assert './bin/release-candidate "$(VERSION)"' in makefile
    assert "make release-candidate" in help_text
