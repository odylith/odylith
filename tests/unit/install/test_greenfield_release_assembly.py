"""Release assembly contracts; all packages and grades here are synthetic fixtures."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_public_qualification as public
import greenfield_release_qualification as assembly
from greenfield_matrix_release_artifacts import sha256_file
from greenfield_model_profile_proof import model_profile_release_proof
from tests.unit.install.test_greenfield_public_qualification import saved_public, _bound_evidence
from tests.unit.install.test_greenfield_onboarding_review import (
    evidence as onboarding_evidence, _passing_release_qualification,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
REVISION = "a" * 40


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n")
    return {"path": str(path), "sha256": sha256_file(path)}


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    session = tmp_path / "locks/release-session.json"
    save(session, {"head_sha": REVISION, "version": "0.1.15"})
    root = session.parent / "greenfield-release" / REVISION
    dist = root / "dist"
    dist.mkdir(parents=True)
    for name in ("install.sh", "fixture.whl", "SHA256SUMS"):
        (dist / name).write_text(name + " synthetic bytes")
    wheel = {"name": "fixture.whl", "sha256": sha256_file(dist / "fixture.whl")}
    save(dist / "build-provenance.v1.json", {"version": "odylith-release-provenance.v1",
        "source_tree": {"head": REVISION, "dirty": False}, "workflow": {"sha": REVISION},
        "artifacts": {"wheel": wheel}})
    save(dist / "release-manifest.json", {"assets": {"fixture.whl": {"sha256": wheel["sha256"]}}})
    (root / "package-logs").mkdir()
    for phase in ("wheel", "assets", "smoke"):
        (root / "package-logs" / (phase + ".log")).write_text("synthetic successful phase\n")
    # The actual shell canonical check owns main/origin/auth; isolate package byte custody here.
    git_state = {"HEAD": REVISION, "HEAD^{tree}": "b" * 40, "--exclude-standard": ""}
    monkeypatch.setattr(assembly.subprocess, "check_output", lambda argv, **_: git_state[argv[-1]])
    monkeypatch.setattr(assembly.subprocess, "run", lambda *_, **__: None)
    kwargs = dict(proof_root=root, session_path=session, repo_root=tmp_path,
        implementation_revision=REVISION, version="0.1.15")
    receipt = assembly.prepare_release_package(**kwargs)
    (root / "build-provenance.v1.json").write_bytes((dist / "build-provenance.v1.json").read_bytes())
    return dict(root=root, dist=dist, session=session, kwargs=kwargs, receipt=receipt, git_state=git_state)


def test_package_prepare_is_not_release_or_holdout_proof(prepared):
    value = prepared
    assert assembly.verify_prepared_release_package(**value["kwargs"]) == value["receipt"]
    assert value["receipt"]["status"] == "prepared"
    assert not list(value["root"].glob("*holdout*"))
    assert not (value["root"] / "matrix-result.v1.json").exists()
    with pytest.raises(FileExistsError):
        assembly.prepare_release_package(**value["kwargs"])


@pytest.mark.parametrize("mutation", ("artifact", "added", "removed", "symlink", "head", "untracked", "session", "log"))
def test_prepared_package_refuses_changed_source_session_or_any_distribution_byte(prepared, mutation):
    value = prepared
    if mutation == "artifact": (value["dist"] / "install.sh").write_text("changed")
    elif mutation == "added": (value["dist"] / "extra.txt").write_text("changed")
    elif mutation == "removed": (value["dist"] / "install.sh").unlink()
    elif mutation == "symlink":
        path = value["dist"] / "install.sh"
        target = value["root"] / "outside-install.sh"
        target.write_bytes(path.read_bytes()); path.unlink(); path.symlink_to(target)
    elif mutation == "head": value["git_state"]["HEAD"] = "c" * 40
    elif mutation == "untracked": value["git_state"]["--exclude-standard"] = "scripts/release/sitecustomize.py"
    elif mutation == "session": save(value["session"], {"head_sha": REVISION, "version": "0.1.16"})
    else: (value["root"] / "package-logs/smoke.log").write_text("changed")
    with pytest.raises((RuntimeError, FileNotFoundError)):
        assembly.verify_prepared_release_package(**value["kwargs"])


def public_fixture(prepared, monkeypatch):
    dist, root = prepared["dist"], prepared["root"]
    declaration = save(root / "composition-declaration.json", {"release_custody": {
        "build_provenance": {"path": str(dist / "build-provenance.v1.json"),
            "sha256": sha256_file(dist / "build-provenance.v1.json")}}})
    path = root / "composition-evidence.json"
    evidence = {"version": public.PUBLIC_COMPOSITION_MODE, "declaration": declaration,
        "primary": {}, "high": {}, "genuine_edit": {}}
    save(path, evidence)
    calls = []
    report = {"status": "passed", "passed": True, "evidence_refs": evidence,
        "same_release_observations": {"commit": REVISION, "tree": "b" * 40, "distribution_root": str(dist)}}
    def qualify(*, evidence):
        calls.append(deepcopy(evidence))
        return deepcopy(report)
    monkeypatch.setattr(public, "qualify_composed_public_evidence", qualify)
    return path, evidence, calls, report


def test_terminal_claim_reuses_exact_package_and_cannot_reenter(prepared, monkeypatch):
    path, evidence, calls, _ = public_fixture(prepared, monkeypatch)
    before = {p: p.read_bytes() for p in prepared["dist"].iterdir()}
    claim = assembly.claim_terminal_release(composed_public_evidence_path=path, **prepared["kwargs"])
    assert claim["status"] == "claimed" and calls == [evidence]
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert not (prepared["root"] / "final-holdout-ledger.v3.json").exists()
    assert not (prepared["root"] / "matrix-result.v1.json").exists()
    with pytest.raises(FileExistsError):
        assembly.claim_terminal_release(composed_public_evidence_path=path, **prepared["kwargs"])
    assembly.verify_terminal_release_claim(proof_root=prepared["root"], implementation_revision=REVISION,
        distribution_root=prepared["dist"], evidence_ref=claim["composed_public_evidence"],
        distribution_provenance_path=prepared["root"] / "build-provenance.v1.json")


@pytest.mark.parametrize("defect", ("unqualified", "revision", "tree", "distribution", "provenance", "consumed", "untracked"))
def test_bad_public_custody_never_claims_terminal_attempt(prepared, monkeypatch, defect):
    path, evidence, _, report = public_fixture(prepared, monkeypatch)
    if defect == "unqualified": report.update(status="failed", passed=False, issues=["missing family"])
    elif defect == "revision": report["same_release_observations"]["commit"] = "b" * 40
    elif defect == "tree": report["same_release_observations"]["tree"] = "c" * 40
    elif defect == "distribution": report["same_release_observations"]["distribution_root"] += "-other"
    elif defect == "untracked": prepared["git_state"]["--exclude-standard"] = "scripts/release/sitecustomize.py"
    elif defect == "provenance":
        declaration = json.loads(Path(evidence["declaration"]["path"]).read_bytes())
        declaration["release_custody"]["build_provenance"]["sha256"] = "0" * 64
        evidence["declaration"] = save(Path(evidence["declaration"]["path"]), declaration)
        save(path, evidence)
    else: (prepared["root"] / "final-holdout-ledger.v3.json").write_text("synthetic consumed marker")
    with pytest.raises(RuntimeError):
        assembly.claim_terminal_release(composed_public_evidence_path=path, **prepared["kwargs"])
    assert not (prepared["root"] / "terminal-attempt.v1.json").exists()


def test_public_authentication_uses_original_validator_and_original_refs(prepared, monkeypatch):
    path, evidence, calls, _ = public_fixture(prepared, monkeypatch)
    result = assembly.authenticate_composed_release_evidence(path=path,
        implementation_revision=REVISION, distribution_root=prepared["dist"])
    assert calls == [evidence]
    assert result["evidence_ref"] == {"path": str(path), "sha256": sha256_file(path)}
    assert result["qualification"]["evidence_refs"] == evidence


@pytest.mark.parametrize("defect", ("artifact", "claim", "public_ref", "receipt", "provenance_copy"))
def test_terminal_revalidation_refuses_changed_package_or_claim(prepared, monkeypatch, defect):
    path, _, _, _ = public_fixture(prepared, monkeypatch)
    claim = assembly.claim_terminal_release(composed_public_evidence_path=path, **prepared["kwargs"])
    if defect == "artifact": (prepared["dist"] / "install.sh").write_text("changed")
    elif defect == "claim":
        claim["status"] = "passed"
        save(prepared["root"] / "terminal-attempt.v1.json", claim)
    elif defect == "public_ref": claim["composed_public_evidence"]["sha256"] = "0" * 64
    elif defect == "provenance_copy":
        copy = prepared["root"] / "build-provenance.v1.json"
        save(copy, {**json.loads(copy.read_bytes()), "same_revision_other_package": True})
    else:
        save(prepared["root"] / "prepared-package.v1.json", {**prepared["receipt"], "status": "passed"})
    with pytest.raises(RuntimeError):
        assembly.verify_terminal_release_claim(proof_root=prepared["root"], implementation_revision=REVISION,
            distribution_root=prepared["dist"], evidence_ref=claim["composed_public_evidence"],
            distribution_provenance_path=prepared["root"] / "build-provenance.v1.json")


def test_missing_public_gate_stops_before_any_holdout_or_provider_entry(tmp_path):
    args = SimpleNamespace(final_holdout_run_ledger=str(tmp_path / "ledger.json"))
    with pytest.raises(RuntimeError, match="requires qualified composed public evidence"):
        assembly.authenticate_terminal_release_inputs(args)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("defect", ("missing_public", "provenance_copy", "provenance_path"))
def test_actual_terminal_entry_refuses_unbound_public_or_provenance_before_protected_owner(prepared, monkeypatch, defect):
    from tests.unit.install.test_greenfield_preconfirm_matrix_proof_scope import _module
    matrix = _module()
    path, _, _, _ = public_fixture(prepared, monkeypatch)
    assembly.claim_terminal_release(composed_public_evidence_path=path, **prepared["kwargs"])
    copy = prepared["root"] / "build-provenance.v1.json"
    if defect == "provenance_copy":
        save(copy, {**json.loads(copy.read_bytes()), "same_revision_other_package": True})
    provenance = prepared["dist"] / "build-provenance.v1.json" if defect == "provenance_path" else copy
    argv = ["--dist-dir", str(prepared["dist"]), "--proof-tier", "release",
        "--campaign-phase", "gate", "--evidence-output-dir", str(prepared["root"] / "retained-evidence"),
        "--sealed-release-input-root", str(prepared["root"] / "synthetic-sealed-inputs"),
        "--output-json", str(prepared["root"] / "matrix-result.v1.json"),
        "--implementation-revision", REVISION, "--distribution-provenance-file", str(provenance),
        "--final-holdout-run-ledger", str(prepared["root"] / "final-holdout-ledger.v3.json")]
    if defect != "missing_public": argv.extend(["--composed-public-evidence", str(path)])
    monkeypatch.setattr(matrix, "_require_profile_argv_template", lambda _argv: ("synthetic-unused",))
    monkeypatch.setattr(matrix, "_require_sealed_release_input_root", lambda **_: None)
    monkeypatch.setattr(matrix, "_raise_for_invalid_campaign_policy", lambda **_: None)
    monkeypatch.setattr(matrix, "validate_retained_evidence_output_dir", lambda **_: None)
    monkeypatch.setattr(matrix, "_final_holdout_run_from_args", lambda *_a, **_k: pytest.fail("protected owner entered"))
    monkeypatch.setattr(matrix, "_execute_matrix_campaign", lambda **_: pytest.fail("provider entered"))
    with pytest.raises(RuntimeError, match="requires qualified composed|provenance differs"):
        matrix.main(argv)
    assert not (prepared["root"] / "final-holdout-ledger.v3.json").exists()


@pytest.fixture
def composed_bounds(saved_public, tmp_path, monkeypatch):
    saved = saved_public
    evidence = {"primary": {"source": saved["config"], "timing": saved["bound"]},
        "high": {"source": deepcopy(saved["config"]),
            "timing": _bound_evidence(tmp_path / "high", saved["base"], saved["config"], saved["review"]["reviewer"])}}
    def qualify(*, evidence):
        profiles, issues = {}, []
        for name in ("primary", "high"):
            family = evidence.get(name, {})
            _, report, problems = public.validate_measured_public_bound(results=saved["results"],
                source_evidence=family.get("source"), bound_evidence=family.get("timing"))
            profiles[name] = {"measured_public_bound": report}
            issues.extend(problems)
        return {"status": "failed" if issues else "passed", "passed": not issues,
            "issues": issues, "model_profile_proofs": profiles}
    # Only composition membership/custody is isolated; both original timing validators run unmodified.
    monkeypatch.setattr(public, "qualify_composed_public_evidence", qualify)
    return saved, evidence


def test_terminal_keeps_both_authenticated_bounds_without_inventing_aggregate(composed_bounds):
    saved, evidence = composed_bounds
    proof = model_profile_release_proof(saved["results"], require_complete=True, composed_public_evidence=evidence)
    assert proof["status"] == "passed", proof
    assert proof["whole_journey_release_bound_seconds"] is None
    assert proof["whole_journey_bound_status"] == "authenticated_measured_public_families"
    families = proof["measured_public_families"]
    assert families["consumer_timing_custody"] == "unproved"
    assert families["evidence_refs"] == evidence
    assert set(families["families"]) == {"primary", "high"}
    for name, report in families["families"].items():
        assert report["evidence_refs"] == evidence[name]["timing"]
        assert report["qualification_scope"] == public.PUBLIC_MEASURED_BOUND_SCOPE


@pytest.mark.parametrize("family", ("primary", "high"))
@pytest.mark.parametrize("defect", ("absent", "changed"))
def test_terminal_does_not_accept_absent_or_changed_family_timing(composed_bounds, family, defect):
    saved, evidence = composed_bounds
    if defect == "absent": evidence[family].pop("timing")
    else: Path(evidence[family]["timing"]["decision"]["path"]).write_text("{}\n")
    proof = model_profile_release_proof(saved["results"], require_complete=True, composed_public_evidence=evidence)
    assert proof["status"] == "failed" and proof["whole_journey_bound_status"] == "unqualified"


@pytest.mark.parametrize("family", ("primary", "high"))
@pytest.mark.parametrize("outside_operational_contract", (False, True))
def test_public_measurements_do_not_regrade_distinct_terminal_timing(composed_bounds, family, outside_operational_contract):
    saved, evidence = composed_bounds
    # Both family decisions authentically cover their original rows; terminal observation is distinct.
    decision_ref = evidence[family]["timing"]["decision"]
    decision = json.loads(Path(decision_ref["path"]).read_bytes())
    maximum = max(row.evidence["model_profile"]["stage_observation"]["whole_journey_seconds"]
        for row in saved["results"])
    decision["finite_bound_seconds"] = maximum + 1.0
    evidence[family]["timing"]["decision"] = save(Path(decision_ref["path"]), decision)
    record_ref = evidence[family]["timing"]["review_record"]
    record = json.loads(Path(record_ref["path"]).read_bytes())
    record["decision_sha256"] = evidence[family]["timing"]["decision"]["sha256"]
    evidence[family]["timing"]["review_record"] = save(Path(record_ref["path"]), record)
    terminal = deepcopy(saved["results"])
    row = terminal[0]
    stage = row.evidence["model_profile"]["stage_observation"]
    delta = 700.0 if outside_operational_contract else 2.0
    stage["source_ledger_elapsed_seconds"] += delta
    stage["whole_journey_seconds"] += delta
    proof = model_profile_release_proof(terminal, require_complete=True, composed_public_evidence=evidence)
    assert proof["status"] == ("failed" if outside_operational_contract else "passed"), proof
    assert proof["whole_journey_release_bound_seconds"] is None
    assert proof["measured_public_families"]["families"][family]["finite_bound_seconds"] == maximum + 1.0
    assert proof["measured_public_families"]["terminal_observation_timing_scope"] == "existing_profile_and_whole_journey_operational_contract"


def test_review_cannot_add_composition_to_a_prior_diagnostic(tmp_path):
    with pytest.raises(RuntimeError, match="cannot add public composition"):
        assembly.authenticate_review_composition(base={}, base_path=tmp_path / "matrix.json",
            evidence_path=tmp_path / "later-composition.json")


@pytest.fixture
def terminal_review_inputs(prepared, saved_public, monkeypatch):
    path, evidence, calls, report = public_fixture(prepared, monkeypatch)
    _, measured, issues = public.validate_measured_public_bound(results=saved_public["results"],
        source_evidence=saved_public["config"], bound_evidence=saved_public["bound"])
    assert issues == ()
    report["model_profile_proofs"] = {name: {"measured_public_bound": deepcopy(measured)}
        for name in ("primary", "high")}
    assembly.claim_terminal_release(composed_public_evidence_path=path, **prepared["kwargs"])
    base = deepcopy(saved_public["base"])
    base["composed_public_evidence"] = {"path": str(path), "sha256": sha256_file(path)}
    base["model_profile_proof"] = model_profile_release_proof(saved_public["results"], require_complete=True,
        composed_public_evidence=evidence)
    base_path = prepared["root"] / "matrix-result.v1.json"
    save(base_path, base)
    return dict(base=base, base_path=base_path, path=path, calls=calls, report=report, prepared=prepared)


def test_review_reauthenticates_original_refs_and_rebuilds_terminal_profile(terminal_review_inputs):
    value = terminal_review_inputs
    before = value["base_path"].read_bytes()
    count = len(value["calls"])
    result = assembly.authenticate_review_composition(base=value["base"], base_path=value["base_path"])
    assert len(value["calls"]) == count + 2  # package identity, then original observations against both bounds
    assert result["evidence_ref"] == value["base"]["composed_public_evidence"]
    assert result["qualification"] == value["report"]
    assert value["base_path"].read_bytes() == before


@pytest.mark.parametrize("defect", ("public_bytes", "profile_refs", "observation", "package_bytes", "different_input", "provenance_copy"))
def test_review_cannot_accept_stale_refs_or_forged_terminal_profile(terminal_review_inputs, defect):
    value = terminal_review_inputs
    override = None
    if defect == "public_bytes": value["path"].write_text("{}\n")
    elif defect == "profile_refs": value["base"]["model_profile_proof"]["measured_public_families"]["evidence_refs"] = {}
    elif defect == "observation": value["base"]["results"][0]["status"] = "failed"
    elif defect == "package_bytes": (value["prepared"]["dist"] / "install.sh").write_text("changed")
    elif defect == "provenance_copy":
        copy = value["prepared"]["root"] / "build-provenance.v1.json"
        save(copy, {**json.loads(copy.read_bytes()), "same_revision_other_package": True})
    else: override = value["path"].with_name("another-config.json")
    with pytest.raises(RuntimeError):
        assembly.authenticate_review_composition(base=value["base"], base_path=value["base_path"], evidence_path=override)


def test_dispatch_rebuilds_sidecar_with_same_original_composition(onboarding_evidence, tmp_path, monkeypatch):
    report = {"evidence_ref": {"path": "synthetic-original-input", "sha256": "5" * 64},
        "qualification": {"same_release_observations": {"commit": REVISION}}}
    calls = []
    def authenticate(**kwargs):
        calls.append(kwargs)
        return deepcopy(report)
    monkeypatch.setattr(assembly, "authenticate_review_composition", authenticate)
    sidecar, ledger, provenance = _passing_release_qualification(onboarding_evidence, tmp_path)
    result = assembly.verify_release_qualification(sidecar_path=sidecar, final_holdout_ledger_path=ledger,
        distribution_provenance_path=provenance, implementation_revision=REVISION)
    assert result["status"] == "passed" and result["composed_public_evidence_sha256"] == "5" * 64
    assert len(calls) == 3  # original finalization, dispatch sidecar reconstruction, dispatch identity gate
    report["evidence_ref"]["sha256"] = "6" * 64
    with pytest.raises(RuntimeError, match="stale, forged, or incomplete"):
        assembly.verify_release_qualification(sidecar_path=sidecar, final_holdout_ledger_path=ledger,
            distribution_provenance_path=provenance, implementation_revision=REVISION)


def test_make_preflight_defaults_to_prepare_and_exposes_explicit_terminal_target():
    makefile = (REPO_ROOT / "Makefile").read_text()
    assert "release-preflight: release-preflight-prepare" in makefile
    assert '@./bin/release-preflight --prepare "$(VERSION)"' in makefile
    assert '@./bin/release-preflight --complete "$(VERSION)"' in makefile


def test_actual_terminal_shell_uses_prepared_dist_and_forwards_exact_public_input(tmp_path):
    dist = tmp_path / "proof/dist"
    dist.mkdir(parents=True)
    (dist / "build-provenance.v1.json").write_text('{"fixture":true}\n')
    binaries = tmp_path / "bin"
    binaries.mkdir()
    matrix = binaries / "greenfield-preconfirm-matrix"
    matrix.write_text(f"#!{sys.executable}\nimport json, os, pathlib, sys\n"
        "pathlib.Path(os.environ['CAPTURE']).write_text(json.dumps({'argv': sys.argv[1:], "
        "'public': os.environ['GREENFIELD_MATRIX_COMPOSED_PUBLIC_EVIDENCE'], "
        "'revision': os.environ['GREENFIELD_MATRIX_IMPLEMENTATION_REVISION']}))\n")
    matrix.chmod(0o755)
    # The terminal helper reads current HEAD; this local stub records the source identity only.
    git = binaries / "git"
    git.write_text("#!/bin/bash\nprintf '%s\\n' '" + REVISION + "'\n")
    git.chmod(0o755)
    public_input = str(tmp_path / "original public evidence.json")
    capture = tmp_path / "capture.json"
    environment = {**os.environ, "ODYLITH_REPO_ROOT_OVERRIDE": str(tmp_path),
        "CAPTURE": str(capture), "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
        "GREENFIELD_MATRIX_RELEASE_INTENT": "1", "GREENFIELD_MATRIX_COMPOSED_PUBLIC_EVIDENCE": public_input,
        "GREENFIELD_MATRIX_DISTRIBUTION_PROVENANCE_FILE": str(dist.parent / "build-provenance.v1.json")}
    code = 'source "$1"\nprepare_release_proof_package() { exit 91; }\nrun_release_proof_steps 0.1.15 "$2" terminal\n'
    result = subprocess.run(["bash", "-c", code, "test", str(REPO_ROOT / "bin/_odylith.sh"), str(dist)],
        env=environment, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(capture.read_text()) == {"argv": ["0.1.15", str(dist)],
        "public": public_input, "revision": REVISION}
    assert not (dist.parent / "package-logs").exists()


def test_matrix_wrapper_forwards_original_composed_path_on_terminal_lane(tmp_path):
    from tests.unit.install.test_release_greenfield_matrix_bootstrap import (
        _release_input_overrides, _run_greenfield_preconfirm_matrix,
    )
    overrides = _release_input_overrides(tmp_path)
    public_input = tmp_path / "original-composition.json"
    public_input.write_text("{}\n")
    overrides.update(GREENFIELD_MATRIX_RELEASE_INTENT="1", BROWSER_PROOF="1", COMMIT_RECOVERY_PROOF="1",
        GREENFIELD_MATRIX_COMPOSED_PUBLIC_EVIDENCE=str(public_input))
    result = _run_greenfield_preconfirm_matrix(tmp_path, overrides=overrides)
    assert result.returncode == 0, result.stderr
    log = (tmp_path / "fake-python.log").read_text()
    assert "--composed-public-evidence " + str(public_input) in log


def test_preflight_prepare_cannot_dispatch_matrix_and_complete_cannot_rebuild(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "release-preflight").write_bytes((REPO_ROOT / "bin/release-preflight").read_bytes())
    proof = tmp_path / "proof"
    events = tmp_path / "events"
    python = tmp_path / "fake-python"
    python.write_text(f"#!{sys.executable}\nimport json, os, pathlib, sys\n"
        "args = sys.argv[1:]; phase = args[args.index('--package-phase') + 1]\n"
        "root = pathlib.Path(os.environ['PROOF_ROOT'])\n"
        "target = root / ('prepared.json' if phase == 'prepare' else 'terminal-attempt.json')\n"
        "with target.open('x') as stream: stream.write('synthetic test claim')\n"
        "with pathlib.Path(os.environ['EVENTS']).open('a') as stream: stream.write(phase + '\\n')\n")
    python.chmod(0o755)
    helper = '''set -euo pipefail
odylith_repo_root="$FIXTURE_ROOT"
odylith_host_repo_root="$FIXTURE_ROOT"
odylith_python="$FAKE_PYTHON"
odylith_release_session_file="$FIXTURE_ROOT/session.json"
die() { echo "$*" >&2; exit 1; }
require_version() { :; }
require_canonical_release_checkout() { :; }
resolve_release_session_version() { echo 0.1.15; }
release_session_field() { echo aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; }
greenfield_release_proof_root() { echo "$PROOF_ROOT"; }
prepare_release_proof_package() { echo build >> "$EVENTS"; }
run_release_proof_steps() { echo matrix >> "$EVENTS"; }
'''
    (binary / "_odylith.sh").write_text(helper)
    environment = {**os.environ, "FIXTURE_ROOT": str(tmp_path), "FAKE_PYTHON": str(python),
        "PROOF_ROOT": str(proof), "EVENTS": str(events)}
    def run(phase):
        return subprocess.run(["bash", str(binary / "release-preflight"), "--canonical-exec", phase, "0.1.15"],
            env=environment, text=True, capture_output=True)
    result = run("--prepare")
    assert result.returncode == 0, result.stderr
    assert "release package prepared" in result.stdout and "remain pending" in result.stdout
    assert events.read_text().splitlines() == ["build", "prepare"]
    environment.update({name: "synthetic-unused-path" for name in (
        "GREENFIELD_MATRIX_CASE_FILE", "GREENFIELD_MATRIX_SEALED_RELEASE_INPUT_ROOT",
        "GREENFIELD_MATRIX_SEMANTIC_ANNOTATIONS_FILE", "GREENFIELD_MATRIX_EVALUATION_SPLIT_MANIFEST",
        "GREENFIELD_MATRIX_LOWER_CAPABILITY_CONTROL_FILE", "GREENFIELD_MATRIX_COMPOSED_PUBLIC_EVIDENCE")})
    environment["GREENFIELD_MATRIX_RELEASE_INTENT"] = "1"
    result = run("--complete")
    assert result.returncode == 0, result.stderr
    assert events.read_text().splitlines() == ["build", "prepare", "claim", "matrix"]
    assert run("--complete").returncode != 0
    assert run("--prepare").returncode != 0
    assert events.read_text().splitlines() == ["build", "prepare", "claim", "matrix"]


def test_release_preflight_preserves_one_shot_dist_and_review_evidence() -> None:
    text = (REPO_ROOT / "bin" / "release-preflight").read_text(encoding="utf-8")
    shared = (REPO_ROOT / "bin" / "_odylith.sh").read_text(encoding="utf-8")

    assert 'preflight_root="$(greenfield_release_proof_root "$expected_sha")"' in text
    assert 'dist_dir="$preflight_root/dist"' in text
    assert 'if [[ -e "$preflight_root" || -L "$preflight_root" ]]; then' in text
    assert 'trap \'rm -rf "$preflight_root"\' EXIT' not in text
    assert 'GREENFIELD_MATRIX_OUTPUT_JSON="$preflight_root/matrix-result.v1.json"' in text
    assert 'GREENFIELD_MATRIX_EVIDENCE_OUTPUT_DIR="$preflight_root/retained-evidence"' in text
    assert 'GREENFIELD_MATRIX_FINAL_HOLDOUT_RUN_LEDGER="$preflight_root/final-holdout-ledger.v3.json"' in text
    assert 'ODYLITH_GREENFIELD_MATRIX_TEMP_PARENT="${TMPDIR:-/tmp}"' in text
    assert 'awaits independent Greenfield qualification' in text
    assert 'run_release_proof_steps "$resolved_version" "$dist_dir" terminal' in text
    assert 'prepare_release_proof_package "$resolved_version" "$dist_dir"' in text
    assert '--package-phase prepare "${package_args[@]}"' in text
    assert '--package-phase claim "${package_args[@]}"' in text
    assert 'GREENFIELD_MATRIX_COMPOSED_PUBLIC_EVIDENCE' in text
    assert 'run_release_proof_steps() {' in shared
    assert '"$odylith_python" "$odylith_host_repo_root/scripts/sync_version_truth.py" --repo-root . sync' in shared
    assert '"$odylith_python" -m hatch build --target wheel "$dist_dir"' in shared
    assert '--dist-dir "$dist_dir" --allow-local' in shared
    assert 'ODYLITH_RELEASE_PREFLIGHT_DIST_DIR="$dist_dir"' in shared
    assert 'glob.glob(os.path.join(dist_dir, "*.whl"))' in shared
    assert 'scripts/release/local_release_smoke.py --version "$resolved_version" --dist-dir "$dist_dir"' in shared


def test_release_candidate_benchmark_override_is_version_scoped() -> None:
    helper = (REPO_ROOT / "bin" / "_odylith.sh").read_text(encoding="utf-8")
    overrides = json.loads(
        (REPO_ROOT / "odylith" / "runtime" / "source" / "release-maintainer-overrides.v1.json").read_text(
            encoding="utf-8"
        )
    )
    bundled_overrides = json.loads(
        (
            REPO_ROOT
            / "src"
            / "odylith"
            / "bundle"
            / "assets"
            / "odylith"
            / "runtime"
            / "source"
            / "release-maintainer-overrides.v1.json"
        ).read_text(encoding="utf-8")
    )

    assert "release_benchmark_override_mode() {" in helper
    assert "release-maintainer-overrides.v1.json" in helper
    assert "benchmark_proof_overrides" in helper
    rows = {row["version"]: row for row in overrides["benchmark_proof_overrides"]}
    bundled_rows = {row["version"]: row for row in bundled_overrides["benchmark_proof_overrides"]}
    assert rows["0.1.12"]["mode"] == "skip_proof_and_compare"
    assert rows["0.1.12"]["owner"] == "release-maintainer"
    assert "CB-116" in rows["0.1.12"]["reason"]
    assert bundled_rows["0.1.12"] == rows["0.1.12"]


def test_release_candidate_workflow_is_manual_to_avoid_duplicate_pr_full_proof() -> None:
    text = (REPO_ROOT / ".github" / "workflows" / "release-candidate.yml").read_text(encoding="utf-8")

    assert "pull_request:" not in text
    assert "workflow_dispatch:" in text
    assert "make lane-show" in text
    assert "make release-candidate" in text
    assert "permissions:" in text
    assert "contents: read" in text
    assert "make dogfood-activate" not in text
    assert "gh release create" not in text
    assert "publish_release_assets.py" not in text
