from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _run_greenfield_preconfirm_matrix(
    tmp_path: Path,
    *,
    overrides: dict[str, str],
    fake_python_body: str | None = None,
) -> subprocess.CompletedProcess[str]:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "install.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        fake_python_body or "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$FAKE_PYTHON_LOG\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    environment = os.environ.copy()
    for name in (
        "BROWSER_PROOF",
        "COMMIT_RECOVERY_PROOF",
        "GREENFIELD_MATRIX_CASE_FILE",
        "GREENFIELD_MATRIX_RELEASE_AUDIT_FILE",
        "GREENFIELD_MATRIX_RELEASE_INTENT",
        "NATURAL_RESCUE_PROOF",
        "RESCUE_SMOKE",
    ):
        environment.pop(name, None)
    environment.update(
        {
            "FAKE_PYTHON_LOG": str(tmp_path / "fake-python.log"),
            "ODYLITH_PYTHON": str(fake_python),
            "ODYLITH_REPO_ROOT_OVERRIDE": str(REPO_ROOT),
            "TEMP_PARENT": str(tmp_path),
            **overrides,
        }
    )
    return subprocess.run(
        [str(REPO_ROOT / "bin" / "greenfield-preconfirm-matrix"), "0.1.15", str(dist_dir)],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_local_release_assets_target_builds_maintainer_installable_assets() -> None:
    text = (REPO_ROOT / "bin" / "local-release-assets").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")

    assert "local-release-assets:" in makefile
    assert './bin/local-release-assets "$(VERSION)" "$(DIST)"' in makefile
    assert 'requested_version="${1:-${VERSION:-$(current_source_version)}}"' in text
    assert 'dist_dir="${TMPDIR:-/tmp}/odylith-local-release-${requested_version}"' in text
    assert 'rm -rf "$dist_dir"' in text
    assert "require_current_component_forensics" in text
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


def test_greenfield_preconfirm_matrix_target_runs_installed_release_gate() -> None:
    text = (REPO_ROOT / "bin" / "greenfield-preconfirm-matrix").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")
    shared = (REPO_ROOT / "bin" / "_odylith.sh").read_text(encoding="utf-8")

    assert "greenfield-preconfirm-matrix:" in makefile
    assert './bin/greenfield-preconfirm-matrix "$(VERSION)" "$(DIST)"' in makefile
    assert 'requested_version="${1:-${VERSION:-$(current_source_version)}}"' in text
    assert 'temp_parent="${TEMP_PARENT:-${TMPDIR:-/tmp}}"' in text
    assert 'scripts/release/greenfield_preconfirm_matrix.py \\' in text
    assert 'extra_args=()' in text
    assert 'rescue_smoke_enabled=1' in text
    assert "require_current_component_forensics" in text
    assert 'RESCUE_SMOKE:-1' in text
    assert '--skip-rescue-smoke' in text
    assert 'NATURAL_RESCUE_PROOF:-1' in text
    assert '--include-natural-rescue-proof' in text
    assert '--skip-natural-rescue-proof' in text
    assert 'BROWSER_PROOF:-1' in text
    assert '--include-browser-proof' in text
    assert 'browser_proof_enabled=0' in text
    assert 'COMMIT_RECOVERY_PROOF:-1' in text
    assert '--include-commit-recovery-proof' in text
    assert '--skip-commit-recovery-proof' in text
    assert 'release_case_file="${GREENFIELD_MATRIX_CASE_FILE:-}"' in text
    assert 'release_audit_file="${GREENFIELD_MATRIX_RELEASE_AUDIT_FILE:-}"' in text
    assert 'release_intent="${GREENFIELD_MATRIX_RELEASE_INTENT:-0}"' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_CASE_FILE' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_RELEASE_AUDIT_FILE' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires RESCUE_SMOKE=1' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires NATURAL_RESCUE_PROOF=1' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires BROWSER_PROOF=1' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires COMMIT_RECOVERY_PROOF=1' in text
    assert 'GREENFIELD_MATRIX_RELEASE_AUDIT_FILE requires GREENFIELD_MATRIX_CASE_FILE' in text
    assert 'if [[ "$release_intent" == "1" || (' in text
    assert '--proof-tier release' in text
    assert '--proof-tier discovery' in text
    assert '--release-audit-file "$release_audit_file"' in text
    assert 'ensure_playwright_chromium' in text
    assert '"$odylith_python" -m playwright install chromium >/dev/null' in shared
    assert 'proof_json="${GREENFIELD_MATRIX_OUTPUT_JSON:-$dist_dir/greenfield-preconfirm-matrix.v1.json}"' in text
    assert 'GREENFIELD_MATRIX_TELEMETRY_JSONL' in text
    assert 'GREENFIELD_MATRIX_CAMPAIGN_PHASE' in text
    assert 'GREENFIELD_MATRIX_STOP_AFTER_FAILURES' in text
    assert 'GREENFIELD_MATRIX_STOP_AFTER_CLUSTER_FAILURES' in text
    assert 'GREENFIELD_MATRIX_REQUIRED_STRESSORS' in text
    assert 'GREENFIELD_MATRIX_REQUIRE_HIGH_VARIANCE_STRESSORS' in text
    assert "scripts/release/platform_domain_leakage_check.py" in text
    assert '--repo-root "$odylith_repo_root" --dist-dir "$dist_dir"' in text
    assert '--dist-dir "$dist_dir"' in text
    assert '--version "$requested_version"' in text
    assert 'wrapper_temp_root="$(mktemp -d "$temp_parent/odylith-greenfield-wrapper-run.XXXXXX")"' in text
    assert 'trap cleanup_wrapper_temp_root EXIT' in text
    assert 'trap preserve_wrapper_temp_root_on_signal INT TERM' in text
    assert '--temp-parent "$wrapper_temp_root"' in text
    assert '--output-json "$proof_json"' in text
    assert "make greenfield-preconfirm-matrix" in help_text
    assert "write greenfield-preconfirm-matrix.v1.json" in help_text
    assert "per-case generated browser surface state proof" in help_text
    assert "installed CLI auto-rescue wiring smoke" in help_text
    assert "host-planned structured rescue proof" in help_text
    assert "GREENFIELD_MATRIX_TELEMETRY_JSONL" in help_text
    assert "GREENFIELD_MATRIX_STOP_AFTER_CLUSTER_FAILURES" in help_text
    assert "NATURAL_RESCUE_PROOF=0" in help_text
    assert "automatically downgrades the run to discovery proof" in help_text


@pytest.mark.parametrize(
    ("overrides", "expected_error"),
    (
        (
            {},
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_CASE_FILE",
        ),
        (
            {"GREENFIELD_MATRIX_CASE_FILE": "/missing/cases.json"},
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 case file is missing: /missing/cases.json",
        ),
        (
            {"GREENFIELD_MATRIX_CASE_FILE": "{case_file}"},
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_RELEASE_AUDIT_FILE",
        ),
        (
            {
                "GREENFIELD_MATRIX_CASE_FILE": "{case_file}",
                "GREENFIELD_MATRIX_RELEASE_AUDIT_FILE": "/missing/audit.json",
            },
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 audit file is missing: /missing/audit.json",
        ),
        (
            {
                "GREENFIELD_MATRIX_CASE_FILE": "{case_file}",
                "GREENFIELD_MATRIX_RELEASE_AUDIT_FILE": "{audit_file}",
                "RESCUE_SMOKE": "0",
            },
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires RESCUE_SMOKE=1",
        ),
        (
            {
                "GREENFIELD_MATRIX_CASE_FILE": "{case_file}",
                "GREENFIELD_MATRIX_RELEASE_AUDIT_FILE": "{audit_file}",
                "NATURAL_RESCUE_PROOF": "0",
            },
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires NATURAL_RESCUE_PROOF=1",
        ),
        (
            {
                "GREENFIELD_MATRIX_CASE_FILE": "{case_file}",
                "GREENFIELD_MATRIX_RELEASE_AUDIT_FILE": "{audit_file}",
                "BROWSER_PROOF": "0",
            },
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires BROWSER_PROOF=1",
        ),
        (
            {
                "GREENFIELD_MATRIX_CASE_FILE": "{case_file}",
                "GREENFIELD_MATRIX_RELEASE_AUDIT_FILE": "{audit_file}",
                "COMMIT_RECOVERY_PROOF": "0",
            },
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires COMMIT_RECOVERY_PROOF=1",
        ),
    ),
)
def test_greenfield_preconfirm_matrix_release_intent_rejects_missing_prerequisites(
    tmp_path: Path,
    overrides: dict[str, str],
    expected_error: str,
) -> None:
    case_file = tmp_path / "cases.json"
    audit_file = tmp_path / "audit.json"
    case_file.write_text("{}\n", encoding="utf-8")
    audit_file.write_text("{}\n", encoding="utf-8")
    resolved_overrides = {
        name: value.format(case_file=case_file, audit_file=audit_file)
        for name, value in overrides.items()
    }

    result = _run_greenfield_preconfirm_matrix(
        tmp_path,
        overrides={"GREENFIELD_MATRIX_RELEASE_INTENT": "1", **resolved_overrides},
    )

    assert result.returncode != 0
    assert expected_error in result.stderr


def test_greenfield_preconfirm_matrix_without_release_intent_runs_discovery_proof(tmp_path: Path) -> None:
    case_file = tmp_path / "cases.json"
    case_file.write_text("{}\n", encoding="utf-8")

    result = _run_greenfield_preconfirm_matrix(
        tmp_path,
        overrides={
            "BROWSER_PROOF": "0",
            "GREENFIELD_MATRIX_CASE_FILE": str(case_file),
        },
    )

    assert result.returncode == 0, result.stderr
    invocations = (tmp_path / "fake-python.log").read_text(encoding="utf-8")
    assert "--proof-tier discovery" in invocations
    assert not list(tmp_path.glob("odylith-greenfield-wrapper-run.*"))


def test_greenfield_preconfirm_matrix_release_intent_runs_release_proof(tmp_path: Path) -> None:
    case_file = tmp_path / "cases.json"
    audit_file = tmp_path / "audit.json"
    case_file.write_text("{}\n", encoding="utf-8")
    audit_file.write_text("{}\n", encoding="utf-8")

    result = _run_greenfield_preconfirm_matrix(
        tmp_path,
        overrides={
            "GREENFIELD_MATRIX_RELEASE_INTENT": "1",
            "GREENFIELD_MATRIX_CASE_FILE": str(case_file),
            "GREENFIELD_MATRIX_RELEASE_AUDIT_FILE": str(audit_file),
        },
    )

    assert result.returncode == 0, result.stderr
    invocations = (tmp_path / "fake-python.log").read_text(encoding="utf-8")
    assert "--proof-tier release" in invocations
    assert "--include-commit-recovery-proof" in invocations


def test_greenfield_preconfirm_matrix_preserves_its_outer_temp_root_after_nonzero_controller_exit(
    tmp_path: Path,
) -> None:
    temp_parent = tmp_path / "outer-temp"

    result = _run_greenfield_preconfirm_matrix(
        tmp_path,
        overrides={"TEMP_PARENT": str(temp_parent)},
        fake_python_body=(
            '#!/usr/bin/env bash\n'
            'if [[ "$*" == *"greenfield_preconfirm_matrix.py"* ]]; then\n'
            '  kill -KILL "$$"\n'
            'fi\n'
            'printf \'%s\\n\' "$*" >> "$FAKE_PYTHON_LOG"\n'
        ),
    )

    assert result.returncode != 0
    preserved_roots = list(temp_parent.glob("odylith-greenfield-wrapper-run.*"))
    assert len(preserved_roots) == 1, result.stderr
    shutil.rmtree(preserved_roots[0])


def test_greenfield_preconfirm_matrix_preserves_its_outer_temp_root_after_interrupt(
    tmp_path: Path,
) -> None:
    temp_parent = tmp_path / "outer-temp"
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "install.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    ready_file = tmp_path / "controller-ready"
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import os\n"
        "import signal\n"
        "import sys\n"
        "\n"
        "if any(arg.endswith('greenfield_preconfirm_matrix.py') for arg in sys.argv[1:]):\n"
        "    Path(os.environ['FAKE_CONTROLLER_READY_FILE']).write_text('ready', encoding='utf-8')\n"
        "    signal.signal(signal.SIGINT, lambda _signal, _frame: sys.exit(130))\n"
        "    signal.pause()\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        {
            "ODYLITH_PYTHON": str(fake_python),
            "ODYLITH_REPO_ROOT_OVERRIDE": str(REPO_ROOT),
            "TEMP_PARENT": str(temp_parent),
            "FAKE_CONTROLLER_READY_FILE": str(ready_file),
        }
    )
    process = subprocess.Popen(
        [str(REPO_ROOT / "bin" / "greenfield-preconfirm-matrix"), "0.1.15", str(dist_dir)],
        cwd=REPO_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        for _ in range(100):
            if ready_file.is_file() and list(temp_parent.glob("odylith-greenfield-wrapper-run.*")):
                break
            time.sleep(0.01)
        assert ready_file.is_file()
        os.killpg(process.pid, signal.SIGINT)
        _stdout, stderr = process.communicate(timeout=10)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=10)

    assert process.returncode == 130
    assert "retained temporary evidence at:" in stderr
    preserved_roots = list(temp_parent.glob("odylith-greenfield-wrapper-run.*"))
    assert len(preserved_roots) == 1
    shutil.rmtree(preserved_roots[0])


def test_greenfield_matrix_campaign_target_runs_tiered_harness() -> None:
    text = (REPO_ROOT / "bin" / "greenfield-matrix-campaign").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")

    assert "greenfield-matrix-campaign:" in makefile
    assert './bin/greenfield-matrix-campaign "$(VERSION)" "$(DIST)"' in makefile
    assert 'requested_version="${1:-${VERSION:-$(current_source_version)}}"' in text
    assert 'scripts/release/greenfield_matrix_campaign_runner.py \\' in text
    assert 'GREENFIELD_MATRIX_FAILED_CASE_FILES' in text
    assert 'GREENFIELD_MATRIX_REGRESSION_CASE_FILES' in text
    assert 'GREENFIELD_MATRIX_VOLUME_CASE_FILES' in text
    assert 'GREENFIELD_MATRIX_RELEASE_CASE_FILES' in text
    assert 'GREENFIELD_MATRIX_DISCOVERY_MAX_WORKERS' in text
    assert 'GREENFIELD_MATRIX_STOP_AFTER_FAILURES' in text
    assert 'GREENFIELD_MATRIX_STOP_AFTER_CLUSTER_FAILURES' in text
    assert 'GREENFIELD_MATRIX_REQUIRED_STRESSORS' in text
    assert 'GREENFIELD_MATRIX_CAMPAIGN_PROGRESS_JSONL' in text
    assert 'GREENFIELD_MATRIX_CAMPAIGN_PROGRESS_JSON' in text
    assert 'GREENFIELD_MATRIX_QUIET_PROGRESS' in text
    assert 'require_current_component_forensics' in text
    assert 'ensure_playwright_chromium' in text
    assert 'has_release_case_files=1' in text
    assert 'greenfield-matrix-campaign.v1.json' in text
    assert 'output_parent="$(dirname "$output_json")"' in text
    assert 'telemetry_dir="${GREENFIELD_MATRIX_CAMPAIGN_TELEMETRY_DIR:-$output_parent/greenfield-matrix-telemetry}"' in text
    assert "make greenfield-matrix-campaign" in help_text
    assert "exact failed subset, 60-case regression, 120-case discovery, 240-case discovery" in help_text
    assert "controlled concurrency" in help_text
    assert "merged campaign progress" in help_text
    assert "compact live progress lines" in help_text
    assert "GREENFIELD_MATRIX_QUIET_PROGRESS=1" in help_text


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
    assert 'scripts/release/greenfield_preconfirm_matrix.py \\' in shared
    assert "scripts/release/platform_domain_leakage_check.py" in shared
    assert 'sync-component-spec-requirements --repo-root "$odylith_repo_root" --check-only' in shared
    assert "Registry component forensics are stale for the checked-out source" in shared
    assert 'ensure_playwright_chromium' in shared
    assert '--proof-tier release' in shared
    assert '--include-natural-rescue-proof' in shared
    assert '--include-browser-proof' in shared
    assert '--output-json "$dist_dir/greenfield-preconfirm-matrix.v1.json"' in shared
    assert 'release_version_session.py' not in text
    assert 'release_worktree.py' not in text
    assert 'release-candidate:' in makefile
    assert './bin/release-candidate "$(VERSION)"' in makefile
    assert "make release-candidate" in help_text
