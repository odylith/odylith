from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[3]
REVISION = "a" * 40


def _dispatch(tmp_path: Path, *, qualifier_exit: int, omit_sidecar: bool = False) -> tuple[subprocess.CompletedProcess[str], list[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    dispatch = bin_dir / "release-dispatch"
    shutil.copy2(REPO_ROOT / "bin/release-dispatch", dispatch)
    (bin_dir / "_odylith.sh").write_text(
        """#!/usr/bin/env bash
odylith_repo_root="$FAKE_REPO_ROOT"
odylith_python="$FAKE_PYTHON"
odylith_release_repo="odylith/odylith"
odylith_release_ref="main"
require_version() { :; }
require_cmd() { :; }
require_canonical_release_checkout() { :; }
resolve_release_session_version() { printf '0.1.15\\n'; }
release_session_field() { printf '%s\\n' "$FAKE_REVISION"; }
greenfield_release_proof_root() { printf '%s\\n' "$FAKE_PROOF_ROOT"; }
require_file() { [[ -f "$1" ]] || { printf 'missing: %s\\n' "$1" >&2; exit 1; }; }
""",
        encoding="utf-8",
    )
    proof_root = tmp_path / "proof" / REVISION
    proof_root.mkdir(parents=True)
    proof_files = [
        "final-holdout-ledger.v3.json",
        "build-provenance.v1.json",
    ]
    if not omit_sidecar:
        proof_files.append("onboarding-review-sidecar.v2.json")
    for name in proof_files:
        (proof_root / name).write_text("{}\n", encoding="utf-8")
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$FAKE_PYTHON_LOG\"\nexit \"$FAKE_QUALIFICATION_EXIT\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$FAKE_GH_LOG\"\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    python_log = tmp_path / "qualifier.log"
    gh_log = tmp_path / "gh.log"
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "FAKE_REPO_ROOT": str(tmp_path),
        "FAKE_PYTHON": str(fake_python),
        "FAKE_REVISION": REVISION,
        "FAKE_PROOF_ROOT": str(proof_root),
        "FAKE_PYTHON_LOG": str(python_log),
        "FAKE_QUALIFICATION_EXIT": str(qualifier_exit),
        "FAKE_GH_LOG": str(gh_log),
        "GREENFIELD_ONBOARDING_REVIEW_SIDECAR": str(tmp_path / "untrusted-override.json"),
    }
    result = subprocess.run(
        [str(dispatch), "--canonical-exec", "0.1.15"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    python_calls = python_log.read_text(encoding="utf-8").splitlines() if python_log.exists() else []
    gh_calls = gh_log.read_text(encoding="utf-8").splitlines() if gh_log.exists() else []
    return result, python_calls, gh_calls


def test_release_dispatch_stops_before_gh_when_review_is_missing_or_rejected(tmp_path: Path) -> None:
    missing, no_verifier, no_gh = _dispatch(tmp_path / "missing", qualifier_exit=0, omit_sidecar=True)
    assert missing.returncode != 0
    assert no_verifier == []
    assert no_gh == []

    rejected, verifier_calls, no_gh = _dispatch(tmp_path / "rejected", qualifier_exit=1)
    assert rejected.returncode != 0
    assert len(verifier_calls) == 1
    assert "--implementation-revision " + REVISION in verifier_calls[0]
    assert no_gh == []


def test_release_dispatch_uses_canonical_proof_then_calls_gh_once(tmp_path: Path) -> None:
    accepted, verifier_calls, gh_calls = _dispatch(tmp_path, qualifier_exit=0)

    assert accepted.returncode == 0
    assert len(verifier_calls) == 1
    assert "/proof/" + REVISION + "/onboarding-review-sidecar.v2.json" in verifier_calls[0]
    assert len(gh_calls) == 1
    assert gh_calls[0] == (
        "workflow run release.yml --repo odylith/odylith --ref main "
        "-f tag=v0.1.15 -f expected_sha=" + REVISION
    )
