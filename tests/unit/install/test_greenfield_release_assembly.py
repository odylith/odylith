"""Release assembly contracts; all packages and grades here are synthetic fixtures."""

from copy import deepcopy
import io
import json
import tarfile
import os
from pathlib import Path
import subprocess
import sys
import zipfile
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
def canonical_package(tmp_path, monkeypatch):
    """Real Git/package bytes; no corpus, build, provider or custody mock."""
    import hosted_release_custody as hosted
    # External crypto is a synthetic boundary here; package/census/receipt readers are real.
    monkeypatch.setattr(hosted, 'verify_sigstore_asset', lambda **kwargs: None)
    repo = tmp_path / "source"
    repo.mkdir()
    files = {"src/odylith/__init__.py": "__version__ = '0.1.15'\n",
             "src/odylith/bundle/assets/example.txt": "sealed asset\n",
             "scripts/release/example.py": "# frozen driver\n",
             "pyproject.toml": '[tool.hatch.build.targets.wheel]\npackages = ["src/odylith"]\n'}
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), "-c", "core.hooksPath=/dev/null", "-c", "user.name=freedom-research", "-c", "user.email=maintainer@odylith.ai", *args], text=True).strip()
    git("init", "--initial-branch=main")
    git("add", ".")
    git("-c", "user.name=freedom-research", "-c", "user.email=maintainer@odylith.ai", "commit", "-m", "Synthetic custody tree")
    revision = git("rev-parse", "HEAD")
    session = tmp_path / "locks/release-session.json"
    save(session, {"head_sha": revision, "version": "0.1.15"})
    root = session.parent / "greenfield-release" / revision
    dist = root / "dist"
    dist.mkdir(parents=True)
    wheel_path = dist / "odylith-0.1.15-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as wheel:
        for name in files:
            if name.startswith("src/odylith/"):
                wheel.write(repo / name, name.removeprefix("src/"))
        for name, text in {"METADATA": "Metadata-Version: 2.4\nName: odylith\nVersion: 0.1.15\n",
                           "WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
                           "RECORD": ""}.items():
            wheel.writestr("odylith-0.1.15.dist-info/" + name, text)
    (dist / "install.sh").write_text("#!/bin/sh\nexit 0\n")
    from odylith.install.managed_runtime import supported_managed_runtime_platforms, supported_managed_runtime_feature_packs
    runtime_assets, feature_assets = {}, {}
    for platform in supported_managed_runtime_platforms():
        (dist / platform.asset_name).write_bytes(b"synthetic runtime asset, never installed")
        runtime_assets[platform.slug] = {"name": platform.asset_name, "sha256": sha256_file(dist / platform.asset_name)}
    for pack in supported_managed_runtime_feature_packs():
        feature_assets[pack.pack_id] = {}
        for platform in supported_managed_runtime_platforms():
            name = pack.asset_name(platform)
            (dist / name).write_bytes(b"synthetic feature asset, never installed")
            feature_assets[pack.pack_id][platform.slug] = {"name": name, "sha256": sha256_file(dist / name)}
    (dist / "odylith.sbom.spdx.json").write_text("{}\n")
    (dist / "THIRD_PARTY_ATTRIBUTION.md").write_text("Synthetic attribution\n")
    save(dist / "build-provenance.v1.json", {"version": "odylith-release-provenance.v1",
        "repo": "odylith/odylith", "actor": "freedom-research", "tag": "v0.1.15", "release_version": "0.1.15",
        "source_tree": {"head": revision, "dirty": False},
        "workflow": {"sha": revision, "path": ".github/workflows/release.yml", "ref": "refs/heads/main", "run_id": "123", "run_attempt": "1"},
        "artifacts": {"wheel": {"name": wheel_path.name, "sha256": sha256_file(wheel_path)},
                      "runtime_bundles": runtime_assets, "feature_packs": feature_assets}})
    save(dist / "release-manifest.json", {"assets": {
        path.name: {"sha256": sha256_file(path)} for path in dist.iterdir()}})
    (dist / "SHA256SUMS").write_text("".join(
        sha256_file(path) + "  " + path.name + "\n" for path in sorted(dist.iterdir())))
    for path in list(dist.iterdir()):
        if path.name != "SHA256SUMS":
            (dist / (path.name + ".sigstore.json")).write_text('{"synthetic_signature_fixture": true}\n')
    (root / "package-logs").mkdir()
    (root / "package-logs/local-smoke.log").write_text("synthetic local smoke completed\n")
    with zipfile.ZipFile(root / 'package-logs/hosted-workflow.zip', 'w') as archive:
        archive.writestr('release/1_Build.txt', 'synthetic actual workflow log fixture\n')
    save(root / 'package-logs/hosted-steps.json', {'total_count': 1, 'jobs': [{'run_id': 123, 'run_attempt': 1,
        'status': 'completed', 'conclusion': 'success', 'steps': [{'name': name, 'status': 'completed', 'conclusion': 'success'} for name in hosted.BUILD_STEPS.values()]}]})
    next_id = 100
    def asset(path):
        nonlocal next_id
        next_id += 1
        return {"name": path.name, "id": next_id, "size": path.stat().st_size, "sha256": sha256_file(path)}
    candidate = {"version": hosted.LOCAL_VERSION, "repository": "odylith/odylith", "tag": "v0.1.15",
        "implementation_revision": revision, "source_tree": git("rev-parse", "HEAD^{tree}"),
        "release_id": 99, "build_run_id": 123, "build_run_attempt": 1,
        "distribution_assets": [asset(path) for path in sorted(dist.iterdir())],
        "workflow_evidence": {"archive_sha256": sha256_file(root / 'package-logs/hosted-workflow.zip'),
            "steps_sha256": sha256_file(root / 'package-logs/hosted-steps.json')}}
    save(root / 'hosted-acquisition.v1.json', candidate)
    kwargs = dict(proof_root=root, session_path=session, repo_root=repo,
                  implementation_revision=revision, version="0.1.15")
    return dict(root=root, dist=dist, repo=repo, revision=revision, git=git, kwargs=kwargs)


def _canonical_custody_refs(value):
    package_ref = {"path": str(value["root"] / "prepared-package.v3.json"),
                   "sha256": sha256_file(value["root"] / "prepared-package.v3.json")}
    checkpoint = save(value["root"] / "checkpoint.json", {"status": "passed",
        "head": value["revision"], "tree": value["receipt"]["source_tree"], "current_source_pins_unchanged": True})
    executable = Path(sys.executable).resolve()
    profile = {"implementation_revision": value["revision"], "trusted_executable": str(executable),
               "executable_sha256": sha256_file(executable), "profile_id": "synthetic-no-model",
               "model": "synthetic", "reasoning_effort": "none", "argv_shape_sha256": "a" * 64}
    profile_ref = save(value["root"] / "profile.json", profile)
    activation = save(value["root"] / "activation.json", {"status": "activated_after_package_pass",
        "implementation_revision": value["revision"], "prepared_package": package_ref,
        "source_export": str(value["root"] / "source-export"), "distribution": str(value["dist"]),
        "profile": profile, "file_pins": {str(executable): sha256_file(executable)}})
    return {"checkpoint": checkpoint, "prepared_package": package_ref, "activation": activation, "profile": profile_ref}


def test_normal_prepare_receipt_reaches_actual_composition_custody(canonical_package):
    value = canonical_package
    receipt = assembly.prepare_release_package(**value["kwargs"])
    package_ref = {"path": str(value["root"] / "prepared-package.v3.json"),
                   "sha256": sha256_file(value["root"] / "prepared-package.v3.json")}
    value["receipt"] = receipt
    custody = _canonical_custody_refs(value)
    common = public._composition_release_custody(custody)
    assert common["commit"] == value["revision"]
    assert common["prepared_package_sha256"] == package_ref["sha256"]
    assert assembly.verify_prepared_release_package(**value["kwargs"]) == receipt
    # Terminal package revalidation consumes the exact same normal receipt without
    # calling or mocking the independent semantic qualifier.
    evidence_ref = save(value["root"] / "public-refs.json", {"scope": "synthetic package-binding test only"})
    save(value["root"] / "terminal-attempt.v1.json", {
        "version": assembly.PREPARED_PACKAGE_VERSION + ".terminal-attempt.v1", "status": "claimed",
        "prepared_package_sha256": package_ref["sha256"], "composed_public_evidence": evidence_ref})
    (value["root"] / "build-provenance.v1.json").write_bytes((value["dist"] / "build-provenance.v1.json").read_bytes())
    assembly.verify_terminal_release_claim(proof_root=value["root"], implementation_revision=value["revision"],
        distribution_root=value["dist"], evidence_ref=evidence_ref,
        distribution_provenance_path=value["root"] / "build-provenance.v1.json")


@pytest.fixture
def prepared(canonical_package):
    value = canonical_package
    receipt = assembly.prepare_release_package(**value["kwargs"])
    (value["root"] / "build-provenance.v1.json").write_bytes((value["dist"] / "build-provenance.v1.json").read_bytes())
    return {**value, "session": value["kwargs"]["session_path"], "receipt": receipt}


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
    elif mutation == "head": value["git"]("commit", "--allow-empty", "-m", "Different head")
    elif mutation == "untracked": (value["repo"] / "untracked.py").write_text("unexpected")
    elif mutation == "session": save(value["session"], {"head_sha": REVISION, "version": "0.1.16"})
    else: (value["root"] / "package-logs/local-smoke.log").write_text("changed")
    if mutation in {"head", "untracked"}:
        with pytest.raises(RuntimeError, match="clean canonical"):
            assembly.prepare_release_package(**value["kwargs"])
        assert assembly.verify_prepared_release_package(**value["kwargs"]) == value["receipt"]
    else:
        with pytest.raises((RuntimeError, FileNotFoundError)):
            assembly.verify_prepared_release_package(**value["kwargs"])


def public_fixture(prepared, monkeypatch):
    dist, root = prepared["dist"], prepared["root"]
    custody = _canonical_custody_refs(prepared)
    declaration = save(root / "composition-declaration.json", {"release_custody": custody})
    path = root / "composition-evidence.json"
    evidence = {"version": public.PUBLIC_COMPOSITION_MODE, "declaration": declaration,
        "primary": {}, "high": {}, "genuine_edit": {}}
    save(path, evidence)
    calls = []
    report = {"status": "passed", "passed": True, "evidence_refs": evidence,
        "same_release_observations": public._composition_release_custody(custody)}
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
    assembly.verify_terminal_release_claim(proof_root=prepared["root"], implementation_revision=prepared["revision"],
        distribution_root=prepared["dist"], evidence_ref=claim["composed_public_evidence"],
        distribution_provenance_path=prepared["root"] / "build-provenance.v1.json")


@pytest.mark.parametrize("defect", ("unqualified", "revision", "tree", "distribution", "provenance", "consumed", "untracked"))
def test_bad_public_custody_never_claims_terminal_attempt(prepared, monkeypatch, defect):
    path, evidence, _, report = public_fixture(prepared, monkeypatch)
    if defect == "unqualified": report.update(status="failed", passed=False, issues=["missing family"])
    elif defect == "revision": report["same_release_observations"]["commit"] = "b" * 40
    elif defect == "tree": report["same_release_observations"]["tree"] = "c" * 40
    elif defect == "distribution": report["same_release_observations"]["distribution_root"] += "-other"
    elif defect == "untracked": (prepared["repo"] / "untracked.py").write_text("unexpected")
    elif defect == "provenance":
        declaration = json.loads(Path(evidence["declaration"]["path"]).read_bytes())
        declaration["release_custody"]["prepared_package"]["sha256"] = "0" * 64
        evidence["declaration"] = save(Path(evidence["declaration"]["path"]), declaration)
        save(path, evidence)
    else: (prepared["root"] / "final-holdout-ledger.v3.json").write_text("synthetic consumed marker")
    with pytest.raises(RuntimeError):
        assembly.claim_terminal_release(composed_public_evidence_path=path, **prepared["kwargs"])
    assert not (prepared["root"] / "terminal-attempt.v1.json").exists()


def test_public_authentication_uses_original_validator_and_original_refs(prepared, monkeypatch):
    path, evidence, calls, _ = public_fixture(prepared, monkeypatch)
    result = assembly.authenticate_composed_release_evidence(path=path,
        implementation_revision=prepared["revision"], distribution_root=prepared["dist"])
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
        save(prepared["root"] / "prepared-package.v3.json", {**prepared["receipt"], "status": "passed"})
    expected = {"artifact": "checksum", "claim": "terminal attempt", "public_ref": "terminal attempt",
                "receipt": "terminal claim", "provenance_copy": "terminal distribution"}[defect]
    with pytest.raises(RuntimeError, match=expected):
        assembly.verify_terminal_release_claim(proof_root=prepared["root"], implementation_revision=prepared["revision"],
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
        "--implementation-revision", prepared["revision"], "--distribution-provenance-file", str(provenance),
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
    assert 'GREENFIELD_RELEASE_BUILD_RUN_ID="$(GREENFIELD_RELEASE_BUILD_RUN_ID)" ./bin/release-preflight --prepare "$(VERSION)"' in makefile
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
odylith_release_repo="odylith/odylith"
odylith_release_ref="main"
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
        "PROOF_ROOT": str(proof), "EVENTS": str(events), "GREENFIELD_RELEASE_BUILD_RUN_ID": "123"}
    def run(phase):
        return subprocess.run(["bash", str(binary / "release-preflight"), "--canonical-exec", phase, "0.1.15"],
            env=environment, text=True, capture_output=True)
    environment.pop("GREENFIELD_RELEASE_BUILD_RUN_ID")
    result = run("--prepare")
    assert result.returncode == 2
    assert "gh workflow run release.yml --repo odylith/odylith --ref main -f operation=candidate -f tag=v0.1.15 -f expected_sha=" + REVISION in result.stderr
    assert not proof.exists() and not events.exists()
    environment["GREENFIELD_RELEASE_BUILD_RUN_ID"] = "123;exit 0"
    result = run("--prepare")
    assert result.returncode != 0 and "invalid hosted build run ID" in result.stderr
    assert not proof.exists() and not events.exists()
    environment["GREENFIELD_RELEASE_BUILD_RUN_ID"] = "123"
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
    assert 'hosted_release_custody.py" acquire' in shared
    assert '--build-run-id "$GREENFIELD_RELEASE_BUILD_RUN_ID"' in shared
    assert 'ODYLITH_RELEASE_REQUIRE_SIGSTORE_VERIFY=1' in shared
    preparation = shared.split('prepare_release_proof_package() {')[1].split('run_release_proof_steps() {')[0]
    assert 'hatch build' not in preparation
    assert 'publish_release_assets.py' not in preparation
    assert 'local_release_smoke.py' in preparation


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


def _custody_bytes(*roots):
    return {(str(root), path.relative_to(root).as_posix()):
            ("link", os.readlink(path)) if path.is_symlink() else
            ("file", sha256_file(path), path.stat().st_mode) if path.is_file() else ("directory",)
            for root in roots for path in root.rglob("*")}


def _refresh_fixture_assets(value):
    dist = value["dist"]
    payload = [path for path in sorted(dist.iterdir()) if not path.name.endswith(".sigstore.json")
               and path.name not in {"SHA256SUMS", "release-manifest.json"}]
    save(dist / "release-manifest.json", {"assets": {path.name: {"sha256": sha256_file(path)} for path in payload}})
    payload.append(dist / "release-manifest.json")
    (dist / "SHA256SUMS").write_text("".join(sha256_file(path) + "  " + path.name + "\n" for path in payload))
    for path in payload:
        (dist / (path.name + ".sigstore.json")).write_text("{}\n")


@pytest.mark.parametrize("defect", ("wheel_bytes", "wheel_missing", "wheel_extra", "wheel_duplicate", "wheel_alias",
    "wheel_link", "wheel_metadata_python", "invalid_zip", "checksum_missing", "checksum_extra", "checksum_duplicate",
    "checksum_hash", "checksum_self", "manifest_missing", "manifest_extra", "manifest_duplicate", "manifest_hash",
    "sidecar_missing", "sidecar_extra", "sidecar_nested", "sidecar_as_payload", "coordinated_extra", "provenance_family"))
def test_actual_prepare_refuses_inner_relation_defects_without_a_success_receipt(canonical_package, defect):
    value, dist = canonical_package, canonical_package["dist"]
    wheel_path = next(dist.glob("*.whl"))
    if defect.startswith("wheel_"):
        with zipfile.ZipFile(wheel_path) as archive:
            rows = [(row, archive.read(row)) for row in archive.infolist()]
        name = "odylith/__init__.py"
        with zipfile.ZipFile(wheel_path, "w") as archive:
            for row, content in rows:
                if row.filename == name and defect == "wheel_missing": continue
                archive.writestr(row, b"changed source" if row.filename == name and defect == "wheel_bytes" else content)
            if defect in {"wheel_extra", "wheel_duplicate", "wheel_metadata_python", "wheel_alias", "wheel_link"}:
                added = name if defect == "wheel_duplicate" else "odylith/new.py" if defect in {"wheel_extra", "wheel_link"} else                     "odylith-0.1.15.dist-info/evil.py" if defect == "wheel_metadata_python" else "odylith/../odylith/alias.py"
                info = zipfile.ZipInfo(added)
                if defect == "wheel_link": info.external_attr = 0o120777 << 16
                if defect == "wheel_duplicate":
                    with pytest.warns(UserWarning, match="Duplicate name"):
                        archive.writestr(info, b"unexpected")
                else:
                    archive.writestr(info, b"unexpected")
        provenance = json.loads((dist / "build-provenance.v1.json").read_text())
        provenance["artifacts"]["wheel"]["sha256"] = sha256_file(wheel_path)
        save(dist / "build-provenance.v1.json", provenance)
        _refresh_fixture_assets(value)
    elif defect == "invalid_zip":
        wheel_path.write_text("not a ZIP")
        provenance = json.loads((dist / "build-provenance.v1.json").read_text())
        provenance["artifacts"]["wheel"]["sha256"] = sha256_file(wheel_path)
        save(dist / "build-provenance.v1.json", provenance)
        _refresh_fixture_assets(value)
    elif defect.startswith("checksum_"):
        path = dist / "SHA256SUMS"
        rows = path.read_text().splitlines()
        if defect == "checksum_missing": rows.pop()
        elif defect == "checksum_extra": rows.append("a" * 64 + "  unknown.txt")
        elif defect == "checksum_duplicate": rows.append(rows[0])
        elif defect == "checksum_hash": rows[0] = "a" * 64 + rows[0][64:]
        else: rows.append(sha256_file(path) + "  SHA256SUMS")
        path.write_text("\n".join(rows) + "\n")
    elif defect.startswith("manifest_"):
        path = dist / "release-manifest.json"
        manifest = json.loads(path.read_text())
        key = next(iter(manifest["assets"]))
        if defect == "manifest_missing": manifest["assets"].pop(key)
        elif defect == "manifest_extra": manifest["assets"]["unknown.txt"] = {"sha256": "a" * 64}
        elif defect == "manifest_hash": manifest["assets"][key]["sha256"] = "a" * 64
        if defect == "manifest_duplicate":
            path.write_text('{"assets":{},"assets":' + json.dumps(manifest["assets"]) + '}')
        else: save(path, manifest)
        checksum_path = dist / "SHA256SUMS"
        checksum_path.write_text("\n".join(sha256_file(path) + "  release-manifest.json" if row.endswith("  release-manifest.json") else row
            for row in checksum_path.read_text().splitlines()) + "\n")
    elif defect == "sidecar_missing": (dist / "install.sh.sigstore.json").unlink()
    elif defect == "sidecar_extra": (dist / "unknown.sigstore.json").write_text("{}")
    elif defect == "sidecar_nested": (dist / "install.sh.sigstore.json.sigstore.json").write_text("{}")
    elif defect == "sidecar_as_payload":
        with (dist / "SHA256SUMS").open("a") as stream:
            stream.write(sha256_file(dist / "install.sh.sigstore.json") + "  install.sh.sigstore.json\n")
    elif defect == "coordinated_extra":
        (dist / "unknown.py").write_text("arbitrary new owner")
        _refresh_fixture_assets(value)
    else:
        provenance = json.loads((dist / "build-provenance.v1.json").read_text())
        provenance["artifacts"]["runtime_bundles"].pop(next(iter(provenance["artifacts"]["runtime_bundles"])))
        save(dist / "build-provenance.v1.json", provenance)
        _refresh_fixture_assets(value)
    with pytest.raises((RuntimeError, ValueError)):
        assembly.prepare_release_package(**value["kwargs"])
    assert not (value["root"] / "prepared-package.v3.json").exists()


@pytest.mark.parametrize("defect", ("bytes", "missing", "extra", "duplicate", "alias", "unsafe", "link"))
def test_verifier_rejects_archive_relations_even_when_outer_digest_is_rebound(prepared, defect):
    value, path = prepared, prepared["root"] / "source.tar.gz"
    with tarfile.open(path, "r:gz") as archive:
        rows = [(row, archive.extractfile(row).read() if row.isfile() else None) for row in archive]
    target = "source-export/src/odylith/__init__.py"
    with tarfile.open(path, "w:gz") as archive:
        for row, content in rows:
            if row.name == target and defect == "missing": continue
            if row.name == target and defect == "bytes": content = b"changed immutable source"
            if content is not None: row.size = len(content)
            archive.addfile(row, io.BytesIO(content) if content is not None else None)
        if defect not in {"bytes", "missing"}:
            name = target if defect == "duplicate" else "source-export//alias.py" if defect == "alias" else                 "../escape" if defect == "unsafe" else "source-export/extra.py"
            row = tarfile.TarInfo(name)
            if defect == "link": row.type, row.linkname = tarfile.SYMTYPE, "src/odylith/__init__.py"
            archive.addfile(row, io.BytesIO(b""))
    receipt = value["receipt"]
    receipt["source_archive"]["sha256"] = sha256_file(path)
    save(value["root"] / "prepared-package.v3.json", receipt)
    before = _custody_bytes(value["root"], value["repo"])
    with pytest.raises((RuntimeError, ValueError)):
        assembly.verify_prepared_release_package(**value["kwargs"])
    assert _custody_bytes(value["root"], value["repo"]) == before


@pytest.mark.parametrize("defect", ("export_bytes", "export_missing", "export_extra", "export_directory", "export_link",
    "sidecar_bytes", "anchor_missing", "anchor_relative", "anchor_symlink", "anchor_alternate", "old_version", "extra_field", "duplicate_key", "wrong_tree", "bindings_duplicate"))
def test_current_receipt_and_export_refusals_are_read_only(prepared, tmp_path, defect):
    value, receipt = prepared, prepared["receipt"]
    export = Path(receipt["source_export"]["path"])
    path = export / "src/odylith/__init__.py"
    if defect == "export_bytes": path.write_text("changed")
    elif defect == "export_missing": path.unlink()
    elif defect == "export_extra": (export / "extra.py").write_text("extra")
    elif defect == "export_directory": (export / "extra-directory").mkdir()
    elif defect == "export_link":
        path.unlink(); path.symlink_to(value["repo"] / "src/odylith/__init__.py")
    elif defect == "sidecar_bytes": (value["dist"] / "install.sh.sigstore.json").write_text("changed")
    elif defect == "anchor_missing": receipt.pop("source_repository")
    elif defect == "anchor_relative": receipt["source_repository"] = "."
    elif defect == "anchor_symlink":
        link = tmp_path / "repo-link"; link.symlink_to(value["repo"], target_is_directory=True)
        receipt["source_repository"] = str(link)
    elif defect == "anchor_alternate":
        alternate = tmp_path / "other-source"; alternate.mkdir(); receipt["source_repository"] = str(alternate)
    elif defect == "old_version": receipt["version"] = "odylith.greenfield.prepared-release-package.v1"
    elif defect == "wrong_tree": receipt["source_tree"] = "b" * 40
    elif defect == "bindings_duplicate": receipt["wheel_source_bindings"].append(receipt["wheel_source_bindings"][0])
    elif defect == "extra_field": receipt["unexpected"] = True
    receipt_path = value["root"] / "prepared-package.v3.json"
    save(receipt_path, receipt)
    if defect == "duplicate_key":
        receipt_path.write_text(receipt_path.read_text().rstrip()[:-1] + ',"status":"prepared"}')
    before = _custody_bytes(value["root"], value["repo"])
    with pytest.raises(RuntimeError):
        assembly.verify_prepared_release_package(**value["kwargs"])
    assert _custody_bytes(value["root"], value["repo"]) == before


def test_source_verification_ignores_git_redirects_and_replacements_and_never_recaptures(prepared, monkeypatch, tmp_path):
    value = prepared
    original = (value["repo"] / "src/odylith/__init__.py").read_text()
    (value["repo"] / "src/odylith/__init__.py").write_text("replacement source")
    value["git"]("add", "."); value["git"]("commit", "-m", "Replacement tree")
    other = value["git"]("rev-parse", "HEAD")
    value["git"]("reset", "--hard", value["revision"])
    value["git"]("replace", value["revision"], other)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "wrong-git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(tmp_path / "wrong-objects"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.worktree")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(tmp_path))
    calls = []
    check_output = assembly.subprocess.check_output
    def observe(argv, **kwargs):
        calls.append(argv)
        assert kwargs["env"]["GIT_NO_LAZY_FETCH"] == "1"
        assert kwargs["env"]["GIT_OPTIONAL_LOCKS"] == "0"
        return check_output(argv, **kwargs)
    monkeypatch.setattr(assembly.subprocess, "check_output", observe)
    from odylith.install import archive_safety
    monkeypatch.setattr(archive_safety, "extract_validated_archive", lambda **_: pytest.fail("verifier extracted source"))
    before = _custody_bytes(value["root"], value["repo"])
    assert assembly.verify_prepared_release_package(**value["kwargs"]) == value["receipt"]
    assert not any("archive" in call for call in calls)
    assert len(calls) <= 20  # constant plumbing, not a process per file
    assert (Path(value["receipt"]["source_export"]["path"]) / "src/odylith/__init__.py").read_text() == original
    assert _custody_bytes(value["root"], value["repo"]) == before


@pytest.mark.parametrize("defect", ("missing_anchor", "relative_anchor", "malformed_anchor", "symlink_anchor", "other_repository",
    "missing_object", "wrong_tree", "old_version", "extra_receipt_field", "wrong_receipt_hash", "old_custody_refs",
    "activation_receipt", "activation_head", "activation_export", "activation_dist", "activation_profile", "profile_head", "checkpoint_tree"))
def test_real_custody_reader_refuses_rebound_invalid_current_records(prepared, tmp_path, defect):
    value = prepared
    refs = _canonical_custody_refs(value)
    key = "prepared_package"
    if defect == "missing_anchor": value["receipt"].pop("source_repository")
    elif defect == "relative_anchor": value["receipt"]["source_repository"] = "."
    elif defect == "malformed_anchor": value["receipt"]["source_repository"] = []
    elif defect == "symlink_anchor":
        link = tmp_path / "anchor-link"; link.symlink_to(value["repo"], target_is_directory=True)
        value["receipt"]["source_repository"] = str(link)
    elif defect == "other_repository":
        other = tmp_path / "other-repository"; other.mkdir(); value["receipt"]["source_repository"] = str(other)
    elif defect == "missing_object":
        (value["repo"] / ".git/objects" / value["revision"][:2] / value["revision"][2:]).unlink()
    elif defect == "wrong_tree": value["receipt"]["source_tree"] = "b" * 40
    elif defect == "old_version": value["receipt"]["version"] = "odylith.greenfield.prepared-release-package.v1"
    elif defect == "extra_receipt_field": value["receipt"]["unexpected"] = True
    elif defect == "wrong_receipt_hash": refs["prepared_package"]["sha256"] = "a" * 64
    elif defect == "old_custody_refs": refs["build"] = refs["prepared_package"]
    elif defect.startswith("activation_"):
        key = "activation"
        data = json.loads(Path(refs[key]["path"]).read_text())
        field = {"receipt": "prepared_package", "head": "implementation_revision", "export": "source_export",
                 "dist": "distribution", "profile": "profile"}[defect.removeprefix("activation_")]
        data[field] = {} if field in {"prepared_package", "profile"} else "wrong"
        refs[key] = save(Path(refs[key]["path"]), data)
    elif defect == "profile_head":
        key = "profile"; data = json.loads(Path(refs[key]["path"]).read_text()); data["implementation_revision"] = "b" * 40
        refs[key] = save(Path(refs[key]["path"]), data)
    else:
        key = "checkpoint"; data = json.loads(Path(refs[key]["path"]).read_text()); data["tree"] = "b" * 40
        refs[key] = save(Path(refs[key]["path"]), data)
    if defect in {"missing_anchor", "relative_anchor", "malformed_anchor", "symlink_anchor", "other_repository", "wrong_tree", "old_version", "extra_receipt_field"}:
        refs[key] = save(Path(refs[key]["path"]), value["receipt"])
        activation = json.loads(Path(refs["activation"]["path"]).read_text())
        activation["prepared_package"] = refs[key]
        refs["activation"] = save(Path(refs["activation"]["path"]), activation)
    before = _custody_bytes(value["root"], value["repo"])
    with pytest.raises((RuntimeError, ValueError)):
        public._composition_release_custody(refs)
    assert _custody_bytes(value["root"], value["repo"]) == before


@pytest.mark.parametrize("failed_phase", ("validate", "acquire", "smoke", None))
def test_actual_prepare_shell_never_reaches_seal_after_a_failed_phase(tmp_path, failed_phase):
    source = tmp_path / "source"
    source.mkdir()
    events = tmp_path / "events"
    fake = tmp_path / "phase-python"
    fake.write_text(f"#!{sys.executable}\nimport os, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "phase = 'acquire' if any(x.endswith('hosted_release_custody.py') for x in args) else 'smoke' if any(x.endswith('local_release_smoke.py') for x in args) else None\n"
        "if phase:\n"
        " with pathlib.Path(os.environ['EVENTS']).open('a') as stream: stream.write(phase + '\\n')\n"
        " if os.environ.get('FAILED_PHASE') == phase: raise SystemExit(23)\n"
        " if phase == 'acquire':\n"
        "  root = pathlib.Path(args[args.index('--proof-root') + 1]); (root / 'package-logs').mkdir(); (root / 'dist').mkdir()\n")
    fake.chmod(0o755)
    dist = tmp_path / "package/dist"
    dist.parent.mkdir()
    script = ('source "$1"\nvalidate_release_proof_source() { printf "validate\\n" >> "$EVENTS"; '
        '[[ "$FAILED_PHASE" != validate ]] || return 23; }\n'
        'prepare_release_proof_package 0.1.15 "$2"\nprintf "seal\\n" >> "$EVENTS"\n')
    environment = {**os.environ, "ODYLITH_REPO_ROOT_OVERRIDE": str(source), "ODYLITH_HOST_REPO_ROOT": str(source),
        "ODYLITH_PYTHON": str(fake), "EVENTS": str(events), "FAILED_PHASE": failed_phase or "", "GREENFIELD_RELEASE_BUILD_RUN_ID": "123"}
    result = subprocess.run(["bash", "-c", script, "test", str(REPO_ROOT / "bin/_odylith.sh"), str(dist)],
        env=environment, text=True, capture_output=True)
    observed = events.read_text().splitlines() if events.exists() else []
    expected = ["validate", "acquire", "smoke"]
    if failed_phase:
        assert result.returncode != 0
        assert observed == expected[:expected.index(failed_phase) + 1]
        assert "seal" not in observed
    else:
        assert result.returncode == 0, result.stderr
        assert observed == expected + ["seal"]


@pytest.mark.parametrize('mode', ['discovery', 'canonical'])
@pytest.mark.parametrize('validation_fails', [False, True])
def test_real_discovery_and_canonical_callers_keep_full_validation_ownership(canonical_package, mode, validation_fails):
    value = canonical_package
    repo = value['repo']
    binary = repo / 'bin'
    binary.mkdir()
    for name in ('_odylith.sh', 'release-candidate'):
        (binary / name).write_bytes((REPO_ROOT / 'bin' / name).read_bytes())
        (binary / name).chmod(0o755)
    (binary / 'validate').write_text('#!/bin/sh\nprintf "validate\\n" >> "$EVENTS"\n'
        'if [ "$VALIDATION_FAILS" = 1 ]; then exit 23; fi\n')
    (binary / 'validate').chmod(0o755)
    (binary / 'greenfield-preconfirm-matrix').write_text('#!/bin/sh\nprintf "matrix\\n" >> "$EVENTS"\n')
    (binary / 'greenfield-preconfirm-matrix').chmod(0o755)
    value['git']('add', 'bin')
    value['git']('commit', '-m', 'Synthetic direct release callers')
    parent = value['root'].parent.parent.parent
    events = parent / ('events-' + mode)
    python = parent / 'fake-release-python'
    python.write_text(f'#!{sys.executable}\n'
        'import os, pathlib, shutil, sys\nargs = sys.argv[1:]\n'
        'if args[0] == "-": os.execv(sys.executable, [sys.executable, *args])\n'
        'if args[0] == "-m" and args[1] == "hatch":\n'
        ' phase = "wheel"; target = pathlib.Path(args[-1]); shutil.copyfile(os.environ["MINI_WHEEL"], target / pathlib.Path(os.environ["MINI_WHEEL"]).name)\n'
        'elif args[0] == "-m" and args[1] == "odylith.cli":\n'
        ' phase = "forensics" if "governance" in args else "benchmark" if "benchmark" in args else "self-host"\n'
        'elif args[0].endswith("sync_version_truth.py"): phase = "version"\n'
        'elif args[0].endswith("publish_release_assets.py"): phase = "assets"; assert "--allow-local" in args and "--candidate" not in args\n'
        'elif args[0].endswith("platform_domain_leakage_check.py"): phase = "leakage"\n'
        'elif args[0].endswith("local_release_smoke.py"): phase = "smoke"\n'
        'elif args[0].endswith("hosted_release_custody.py"):\n'
        ' phase = "acquire"; root = pathlib.Path(args[args.index("--proof-root") + 1]); (root / "dist").mkdir(); (root / "package-logs").mkdir()\n'
        'else: raise AssertionError(args)\n'
        'with pathlib.Path(os.environ["EVENTS"]).open("a") as stream: stream.write(phase + "\\n")\n')
    python.chmod(0o755)
    environment = dict(os.environ, ODYLITH_REPO_ROOT_OVERRIDE=str(repo), ODYLITH_HOST_REPO_ROOT=str(repo),
        ODYLITH_PYTHON=str(python), EVENTS=str(events), VALIDATION_FAILS='1' if validation_fails else '0',
        MINI_WHEEL=str(next(value['dist'].glob('*.whl'))), GREENFIELD_MATRIX_RELEASE_INTENT='0', TMPDIR=str(parent))
    environment.pop('GREENFIELD_RELEASE_BUILD_RUN_ID', None)
    environment.pop('ODYLITH_RELEASE_SESSION_FILE', None)
    if mode == 'discovery':
        argv = ['bash', str(binary / 'release-candidate'), '0.1.15']
    else:
        root = parent / 'canonical-acquisition'
        root.mkdir()
        environment['GREENFIELD_RELEASE_BUILD_RUN_ID'] = '123'
        environment['SYNTHETIC_HEAD'] = value['git']('rev-parse', 'HEAD')
        script = 'source "$1"\nrelease_session_field() { printf "%s\\n" "$SYNTHETIC_HEAD"; }\nprepare_release_proof_package 0.1.15 "$2"\nprintf "seal\\n" >> "$EVENTS"\n'
        argv = ['bash', '-c', script, 'test', str(binary / '_odylith.sh'), str(root / 'dist')]
    result = subprocess.run(argv, env=environment, cwd=repo, capture_output=True, text=True)
    observed = events.read_text().splitlines()
    if validation_fails:
        assert result.returncode == 23, result.stderr
        assert observed == ['version', 'version', 'validate']
    else:
        assert result.returncode == 0, result.stderr
        assert observed[:5] == ['version', 'version', 'validate', 'forensics', 'self-host']
        assert observed[5:] == (['wheel', 'assets', 'leakage', 'smoke', 'matrix', 'benchmark']
            if mode == 'discovery' else ['acquire', 'smoke', 'seal'])


@pytest.mark.parametrize("name", ("../escape/", "/absolute/", "unowned/", "odylith//alias/"))
def test_prepare_refuses_unsafe_or_unowned_zip_directories(canonical_package, name):
    value, dist = canonical_package, canonical_package["dist"]
    wheel_path = next(dist.glob("*.whl"))
    with zipfile.ZipFile(wheel_path, "a") as wheel:
        wheel.writestr(name, b"")
    provenance = json.loads((dist / "build-provenance.v1.json").read_text())
    provenance["artifacts"]["wheel"]["sha256"] = sha256_file(wheel_path)
    save(dist / "build-provenance.v1.json", provenance)
    _refresh_fixture_assets(value)
    with pytest.raises(RuntimeError, match="wheel"):
        assembly.prepare_release_package(**value["kwargs"])
    assert not (value["root"] / "prepared-package.v3.json").exists()


def test_linked_prepare_survives_build_cleanup_and_a_new_linked_caller(canonical_package, tmp_path):
    value = canonical_package
    build = tmp_path / 'build-checkout'
    value['git']('worktree', 'add', '--detach', str(build), value['revision'])
    kwargs = {**value['kwargs'], 'repo_root': build}
    receipt = assembly.prepare_release_package(**kwargs)
    value['git']('worktree', 'remove', str(build))
    next_build = tmp_path / 'next-checkout'
    value['git']('worktree', 'add', '--detach', str(next_build), value['revision'])
    assert assembly.verify_prepared_release_package(**{**kwargs, 'repo_root': next_build}) == receipt
    assert receipt['source_repository'] == str(value['repo'])


def test_immutable_H_verification_ignores_unrelated_primary_branch_and_working_changes(prepared):
    value = prepared
    value['git']('commit', '--allow-empty', '-m', 'Later unrelated branch state')
    (value['repo'] / 'unrelated.txt').write_text('Uncommitted user change')
    before = _custody_bytes(value['root'], value['repo'])
    assert assembly.verify_prepared_release_package(**value['kwargs']) == value['receipt']
    assert _custody_bytes(value['root'], value['repo']) == before


@pytest.mark.parametrize('mutation', ('head', 'untracked', 'during_capture', 'after_seal'))
def test_actual_build_source_guards_prevent_a_successful_seal(canonical_package, monkeypatch, mutation):
    value = canonical_package
    def dirty(): (value['repo'] / 'unexpected.txt').write_text('uncommitted build change')
    if mutation == 'head': value['git']('commit', '--allow-empty', '-m', 'Different build head')
    elif mutation == 'untracked': dirty()
    elif mutation == 'during_capture':
        original = assembly._source_custody
        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            if kwargs.get('extract'): dirty()
            return result
        monkeypatch.setattr(assembly, '_source_custody', changed)
    else:
        original = assembly._exclusive_write_json
        def changed(path, snapshot):
            original(path, snapshot)
            dirty()
        monkeypatch.setattr(assembly, '_exclusive_write_json', changed)
    with pytest.raises(RuntimeError, match='clean canonical'):
        assembly.prepare_release_package(**value['kwargs'])
    assert not (value['root'] / 'prepared-package.v3.json').exists()
    if mutation in {'head', 'untracked'}:
        assert not (value['root'] / 'source.tar.gz').exists()


@pytest.mark.parametrize('change', ('caller', 'receipt'))
def test_unrelated_same_H_clone_cannot_replace_sealed_common_store(prepared, tmp_path, change):
    value = prepared
    clone = tmp_path / 'unrelated-clone'
    value['git']('clone', '--no-hardlinks', str(value['repo']), str(clone))
    kwargs = dict(value['kwargs'])
    if change == 'caller': kwargs['repo_root'] = clone
    else:
        value['receipt']['source_repository'] = str(clone)
        save(value['root'] / 'prepared-package.v3.json', value['receipt'])
    before = _custody_bytes(value['root'], value['repo'], clone)
    with pytest.raises(RuntimeError, match='anchor/common store'):
        assembly.verify_prepared_release_package(**kwargs)
    assert _custody_bytes(value['root'], value['repo'], clone) == before


@pytest.mark.parametrize('defect', ('duplicate_primary', 'missing_primary', 'symlink_primary', 'wrong_primary', 'symlink_git_dir', 'missing_blob'))
def test_persistent_anchor_metadata_and_objects_fail_closed(prepared, monkeypatch, tmp_path, defect):
    value = prepared
    original = assembly._source_git
    if defect == 'missing_blob':
        identity = value['git']('rev-parse', value['revision'] + ':src/odylith/__init__.py')
        (value['repo'] / '.git/objects' / identity[:2] / identity[2:]).unlink()
    else:
        link = tmp_path / 'root-link'
        link.symlink_to(value['repo'], target_is_directory=True)
        git_link = tmp_path / 'git-link'
        git_link.symlink_to(value['repo'] / '.git', target_is_directory=True)
        wrong = tmp_path / 'not-a-repository'
        wrong.mkdir()
        def changed(repo, *args, **kwargs):
            if args == ('worktree', 'list', '--porcelain', '-z'):
                selected = str(value['repo']) if defect == 'duplicate_primary' else str(tmp_path / 'absent') if defect == 'missing_primary' else str(link) if defect == 'symlink_primary' else str(wrong) if defect == 'wrong_primary' else None
                if selected:
                    row = ('worktree ' + selected).encode() + b'\0'
                    return row * 2 if defect == 'duplicate_primary' else row
            if args == ('rev-parse', '--path-format=absolute', '--git-dir') and defect == 'symlink_git_dir':
                return str(git_link).encode()
            return original(repo, *args, **kwargs)
        monkeypatch.setattr(assembly, '_source_git', changed)
    before = _custody_bytes(value['root'], value['repo'])
    with pytest.raises(RuntimeError):
        assembly.verify_prepared_release_package(**value['kwargs'])
    assert _custody_bytes(value['root'], value['repo']) == before


def test_legacy_receipt_is_preserved_and_never_reissued(canonical_package):
    value = canonical_package
    legacy = value['root'] / 'prepared-package.v1.json'
    legacy.write_text('{"version":"odylith.greenfield.prepared-release-package.v1","status":"prepared"}')
    before = legacy.read_bytes()
    with pytest.raises(FileExistsError): assembly.prepare_release_package(**value['kwargs'])
    assert legacy.read_bytes() == before
    assert not (value['root'] / 'prepared-package.v3.json').exists()


def test_verifier_requires_caller_repository_root_not_a_subdirectory(prepared):
    before = _custody_bytes(prepared['root'], prepared['repo'])
    with pytest.raises(RuntimeError, match='toplevel'):
        assembly.verify_prepared_release_package(**{**prepared['kwargs'], 'repo_root': prepared['repo'] / 'src'})
    assert _custody_bytes(prepared['root'], prepared['repo']) == before
