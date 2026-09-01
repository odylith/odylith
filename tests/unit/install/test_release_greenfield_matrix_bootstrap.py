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
        "GREENFIELD_MATRIX_DISTRIBUTION_PROVENANCE_FILE",
        "GREENFIELD_MATRIX_EVALUATION_SPLIT_MANIFEST",
        "GREENFIELD_MATRIX_FINAL_HOLDOUT_RUN_LEDGER",
        "GREENFIELD_MATRIX_IMPLEMENTATION_REVISION",
        "GREENFIELD_MATRIX_RELEASE_AUDIT_FILE",
        "GREENFIELD_MATRIX_RELEASE_AUDIT_REPO_ROOT",
        "GREENFIELD_MATRIX_RELEASE_INTENT",
        "GREENFIELD_MATRIX_SEALED_RELEASE_INPUT_ROOT",
        "GREENFIELD_MATRIX_SEMANTIC_ANNOTATIONS_FILE",
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


def _release_input_overrides(tmp_path: Path) -> dict[str, str]:
    sealed_root = tmp_path / "sealed-inputs"
    sealed_root.mkdir()
    case_file = sealed_root / "cases.json"
    annotations_file = sealed_root / "annotations.json"
    manifest_file = sealed_root / "evaluation-manifest.json"
    provenance_file = tmp_path / "build-provenance.v1.json"
    for path in (case_file, annotations_file, manifest_file, provenance_file):
        path.write_text("{}\n", encoding="utf-8")
    return {
        "GREENFIELD_MATRIX_CASE_FILE": str(case_file),
        "GREENFIELD_MATRIX_SEALED_RELEASE_INPUT_ROOT": str(sealed_root),
        "GREENFIELD_MATRIX_SEMANTIC_ANNOTATIONS_FILE": str(annotations_file),
        "GREENFIELD_MATRIX_EVALUATION_SPLIT_MANIFEST": str(manifest_file),
        "GREENFIELD_MATRIX_FINAL_HOLDOUT_RUN_LEDGER": str(tmp_path / "final-holdout-ledger.json"),
        "GREENFIELD_MATRIX_IMPLEMENTATION_REVISION": "a" * 40,
        "GREENFIELD_MATRIX_DISTRIBUTION_PROVENANCE_FILE": str(provenance_file),
    }


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


def test_greenfield_lifecycle_target_includes_transaction_commit_and_recovery_owners() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    for test_path in (
        "tests/unit/runtime/test_greenfield_create_transaction.py",
        "tests/unit/runtime/test_greenfield_apply_commit_only_boundary.py",
        "tests/unit/runtime/test_greenfield_transaction.py",
        "tests/unit/runtime/test_greenfield_commit_journal.py",
        "tests/unit/runtime/test_greenfield_commit_rollback.py",
        "tests/unit/install/test_greenfield_commit_recovery_proof.py",
    ):
        assert test_path in makefile


def test_greenfield_release_matrix_gates_on_explicit_profile_scorecard() -> None:
    scorecard = (REPO_ROOT / "scripts/release/greenfield_onboarding_quality_scorecard.py").read_text(
        encoding="utf-8"
    )
    matrix = (REPO_ROOT / "scripts/release/greenfield_preconfirm_matrix.py").read_text(
        encoding="utf-8"
    )

    assert "model_profile_proof: Mapping" in scorecard
    assert "unavailable_provider_proof: Mapping" in scorecard
    assert "natural_rescue_proof" not in scorecard
    assert "rescue_proof" not in scorecard
    assert "model_profile_proof=profile_proof" in matrix
    assert "unavailable_provider_proof=unavailable_provider" in matrix
    assert 'or onboarding_quality_scorecard.get("status") == "passed"' in matrix


def test_greenfield_preconfirm_matrix_target_runs_installed_release_gate() -> None:
    text = (REPO_ROOT / "bin" / "greenfield-preconfirm-matrix").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")
    shared = (REPO_ROOT / "bin" / "_odylith.sh").read_text(encoding="utf-8")

    assert "greenfield-preconfirm-matrix:" in makefile
    assert './bin/greenfield-preconfirm-matrix "$(VERSION)" "$(DIST)"' in makefile
    assert 'requested_version="${1:-${VERSION:-$(current_source_version)}}"' in text
    assert 'temp_parent="${TEMP_PARENT:-${TMPDIR:-/tmp}}"' in text
    assert 'PYTHONPATH="$odylith_repo_root/src${PYTHONPATH:+:$PYTHONPATH}"' in text
    assert 'scripts/release/greenfield_preconfirm_matrix.py \\' in text
    assert 'extra_args=()' in text
    assert "require_current_component_forensics" in text
    assert "RESCUE_" + "SMOKE" not in text
    assert "NATURAL_" + "RESCUE_PROOF" not in text
    assert "--include-" + "natural-rescue-proof" not in text
    assert "--skip-" + "rescue-smoke" not in text
    assert 'BROWSER_PROOF:-1' in text
    assert '--include-browser-proof' in text
    assert 'browser_proof_enabled=0' in text
    assert 'COMMIT_RECOVERY_PROOF:-1' in text
    assert '--include-commit-recovery-proof' in text
    assert '--skip-commit-recovery-proof' in text
    assert 'release_case_file="${GREENFIELD_MATRIX_CASE_FILE:-}"' in text
    assert 'release_audit_file="${GREENFIELD_MATRIX_RELEASE_AUDIT_FILE:-}"' in text
    assert 'release_audit_repo_root="${GREENFIELD_MATRIX_RELEASE_AUDIT_REPO_ROOT:-}"' in text
    assert 'sealed_release_input_root="${GREENFIELD_MATRIX_SEALED_RELEASE_INPUT_ROOT:-}"' in text
    assert 'semantic_annotations_file="${GREENFIELD_MATRIX_SEMANTIC_ANNOTATIONS_FILE:-}"' in text
    assert 'evaluation_split_manifest="${GREENFIELD_MATRIX_EVALUATION_SPLIT_MANIFEST:-}"' in text
    assert 'final_holdout_run_ledger="${GREENFIELD_MATRIX_FINAL_HOLDOUT_RUN_LEDGER:-}"' in text
    assert 'implementation_revision="${GREENFIELD_MATRIX_IMPLEMENTATION_REVISION:-}"' in text
    assert 'distribution_provenance_file="${GREENFIELD_MATRIX_DISTRIBUTION_PROVENANCE_FILE:-}"' in text
    assert 'release_intent="${GREENFIELD_MATRIX_RELEASE_INTENT:-0}"' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_CASE_FILE' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_SEALED_RELEASE_INPUT_ROOT' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_SEMANTIC_ANNOTATIONS_FILE' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_EVALUATION_SPLIT_MANIFEST' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_FINAL_HOLDOUT_RUN_LEDGER' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_IMPLEMENTATION_REVISION' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_DISTRIBUTION_PROVENANCE_FILE' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_RELEASE_AUDIT_FILE' not in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires BROWSER_PROOF=1' in text
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT=1 requires COMMIT_RECOVERY_PROOF=1' in text
    assert 'GREENFIELD_MATRIX_RELEASE_AUDIT_FILE requires GREENFIELD_MATRIX_CASE_FILE' in text
    assert 'if [[ "$release_intent" == "1" || (' not in text
    assert '--proof-tier release' in text
    assert '--proof-tier discovery' in text
    assert '--release-audit-file "$release_audit_file"' in text
    assert '--release-audit-repo-root "$release_audit_repo_root"' in text
    assert '--sealed-release-input-root "$sealed_release_input_root"' in text
    assert '--semantic-annotations-file "$semantic_annotations_file"' in text
    assert '--evaluation-split-manifest "$evaluation_split_manifest"' in text
    assert '--final-holdout-run-ledger "$final_holdout_run_ledger"' in text
    assert '--implementation-revision "$implementation_revision"' in text
    assert '--distribution-provenance-file "$distribution_provenance_file"' in text
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
    assert "per-case browser surface state" in help_text
    assert "one-call model-first authoring" in help_text
    assert "GREENFIELD_MATRIX_TELEMETRY_JSONL" in help_text
    assert "GREENFIELD_MATRIX_STOP_AFTER_CLUSTER_FAILURES" in help_text
    assert "SIGKILL/same-hash-retry/fsync-rollback recovery" in help_text


@pytest.mark.parametrize(
    ("missing_name", "expected_error"),
    (
        (
            "GREENFIELD_MATRIX_CASE_FILE",
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_CASE_FILE",
        ),
        (
            "GREENFIELD_MATRIX_SEALED_RELEASE_INPUT_ROOT",
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_SEALED_RELEASE_INPUT_ROOT",
        ),
        (
            "GREENFIELD_MATRIX_SEMANTIC_ANNOTATIONS_FILE",
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_SEMANTIC_ANNOTATIONS_FILE",
        ),
        (
            "GREENFIELD_MATRIX_EVALUATION_SPLIT_MANIFEST",
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_EVALUATION_SPLIT_MANIFEST",
        ),
        (
            "GREENFIELD_MATRIX_FINAL_HOLDOUT_RUN_LEDGER",
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_FINAL_HOLDOUT_RUN_LEDGER",
        ),
        (
            "GREENFIELD_MATRIX_IMPLEMENTATION_REVISION",
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_IMPLEMENTATION_REVISION",
        ),
        (
            "GREENFIELD_MATRIX_DISTRIBUTION_PROVENANCE_FILE",
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires GREENFIELD_MATRIX_DISTRIBUTION_PROVENANCE_FILE",
        ),
    ),
)
def test_greenfield_preconfirm_matrix_release_intent_rejects_missing_prerequisites(
    tmp_path: Path,
    missing_name: str,
    expected_error: str,
) -> None:
    overrides = _release_input_overrides(tmp_path)
    overrides.pop(missing_name)

    result = _run_greenfield_preconfirm_matrix(
        tmp_path,
        overrides={"GREENFIELD_MATRIX_RELEASE_INTENT": "1", **overrides},
    )

    assert result.returncode != 0
    assert expected_error in result.stderr


@pytest.mark.parametrize(
    ("disabled_flag", "expected_error"),
    (
        ("BROWSER_PROOF", "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires BROWSER_PROOF=1"),
        (
            "COMMIT_RECOVERY_PROOF",
            "GREENFIELD_MATRIX_RELEASE_INTENT=1 requires COMMIT_RECOVERY_PROOF=1",
        ),
    ),
)
def test_greenfield_preconfirm_matrix_release_intent_rejects_disabled_required_proof(
    tmp_path: Path,
    disabled_flag: str,
    expected_error: str,
) -> None:
    overrides = _release_input_overrides(tmp_path)

    result = _run_greenfield_preconfirm_matrix(
        tmp_path,
        overrides={
            "GREENFIELD_MATRIX_RELEASE_INTENT": "1",
            disabled_flag: "0",
            **overrides,
        },
    )

    assert result.returncode != 0
    assert expected_error in result.stderr


def test_greenfield_preconfirm_matrix_without_release_intent_runs_discovery_proof(tmp_path: Path) -> None:
    overrides = _release_input_overrides(tmp_path)

    result = _run_greenfield_preconfirm_matrix(
        tmp_path,
        overrides={
            "BROWSER_PROOF": "0",
            **overrides,
        },
    )

    assert result.returncode == 0, result.stderr
    invocations = (tmp_path / "fake-python.log").read_text(encoding="utf-8")
    assert "--proof-tier discovery" in invocations
    assert "--sealed-release-input-root" not in invocations
    assert "--semantic-annotations-file" not in invocations
    assert "--evaluation-split-manifest" not in invocations
    assert "--final-holdout-run-ledger" not in invocations
    assert not list(tmp_path.glob("odylith-greenfield-wrapper-run.*"))


def test_greenfield_preconfirm_matrix_release_intent_runs_release_proof_without_audit(tmp_path: Path) -> None:
    overrides = _release_input_overrides(tmp_path)

    result = _run_greenfield_preconfirm_matrix(
        tmp_path,
        overrides={
            "GREENFIELD_MATRIX_RELEASE_INTENT": "1",
            **overrides,
        },
    )

    assert result.returncode == 0, result.stderr
    invocations = (tmp_path / "fake-python.log").read_text(encoding="utf-8")
    assert "--proof-tier release" in invocations
    assert "--include-commit-recovery-proof" in invocations
    assert f"--sealed-release-input-root {overrides['GREENFIELD_MATRIX_SEALED_RELEASE_INPUT_ROOT']}" in invocations
    assert f"--semantic-annotations-file {overrides['GREENFIELD_MATRIX_SEMANTIC_ANNOTATIONS_FILE']}" in invocations
    assert f"--evaluation-split-manifest {overrides['GREENFIELD_MATRIX_EVALUATION_SPLIT_MANIFEST']}" in invocations
    assert f"--final-holdout-run-ledger {overrides['GREENFIELD_MATRIX_FINAL_HOLDOUT_RUN_LEDGER']}" in invocations
    assert f"--implementation-revision {'a' * 40}" in invocations
    assert (
        f"--distribution-provenance-file {overrides['GREENFIELD_MATRIX_DISTRIBUTION_PROVENANCE_FILE']}"
        in invocations
    )
    assert "--release-audit-file" not in invocations


def test_greenfield_preconfirm_matrix_release_intent_forwards_optional_audit_under_sealed_root(
    tmp_path: Path,
) -> None:
    overrides = _release_input_overrides(tmp_path)
    sealed_root = Path(overrides["GREENFIELD_MATRIX_SEALED_RELEASE_INPUT_ROOT"])
    audit_file = sealed_root / "audit.json"
    audit_file.write_text("{}\n", encoding="utf-8")

    result = _run_greenfield_preconfirm_matrix(
        tmp_path,
        overrides={
            "GREENFIELD_MATRIX_RELEASE_INTENT": "1",
            "GREENFIELD_MATRIX_RELEASE_AUDIT_FILE": str(audit_file),
            **overrides,
        },
    )

    assert result.returncode == 0, result.stderr
    invocations = (tmp_path / "fake-python.log").read_text(encoding="utf-8")
    assert f"--release-audit-file {audit_file}" in invocations
    assert f"--release-audit-repo-root {sealed_root}" in invocations


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
    assert 'run_release_proof_steps "$resolved_version" "$dist_dir" discovery' in text
    assert 'benchmark_override_mode="$(release_benchmark_override_mode "$resolved_version")"' in text
    assert "skip_proof_and_compare" in text
    assert "tracked maintainer override marks benchmark proof advisory for this exact release" in text
    assert 'benchmark compare --repo-root . --baseline last-shipped' in text
    assert 'scripts/release/greenfield_preconfirm_matrix.py \\' not in shared
    assert '"$odylith_repo_root/bin/greenfield-preconfirm-matrix" "$resolved_version" "$dist_dir"' in shared
    assert "scripts/release/platform_domain_leakage_check.py" in shared
    assert 'sync-component-spec-requirements --repo-root "$odylith_repo_root" --check-only' in shared
    assert "Registry component forensics are stale for the checked-out source" in shared
    assert 'ensure_playwright_chromium' in shared
    assert 'GREENFIELD_MATRIX_RELEASE_INTENT="$matrix_release_intent"' in shared
    assert 'GREENFIELD_MATRIX_OUTPUT_JSON="$dist_dir/greenfield-preconfirm-matrix.v1.json"' in shared
    assert 'GREENFIELD_MATRIX_IMPLEMENTATION_REVISION="$implementation_revision"' in shared
    assert 'GREENFIELD_MATRIX_DISTRIBUTION_PROVENANCE_FILE="$distribution_provenance_file"' in shared
    assert 'implementation_revision="$(git -C "$odylith_repo_root" rev-parse HEAD)"' in shared
    assert 'distribution_provenance_file="$dist_dir/build-provenance.v1.json"' in shared
    assert "RESCUE_" + "SMOKE" not in shared
    assert "NATURAL_" + "RESCUE_PROOF" not in shared
    assert 'BROWSER_PROOF=1' in shared
    assert 'COMMIT_RECOVERY_PROOF=1' in shared
    assert "release candidate proof is non-disclosing" in shared
    assert 'release_version_session.py' not in text
    assert 'release_worktree.py' not in text
    assert 'release-candidate:' in makefile
    assert './bin/release-candidate "$(VERSION)"' in makefile
    assert "make release-candidate" in help_text
