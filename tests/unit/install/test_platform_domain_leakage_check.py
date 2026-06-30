from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.release import platform_domain_leakage_check as leakage


def test_domain_leakage_terms_use_distinctive_matrix_vocabulary() -> None:
    terms = set(leakage.domain_leakage_terms())

    assert {
        "quantum communication",
        "bell inequality",
        "qber",
        "chsh",
        "wafer lot",
        "carbon tariff",
        "pediatric therapy",
        "supply chain exception desk",
        "developer incident runbook",
        "anger management",
        "digestive health",
        "fifa tracker",
        "quantum tunneling",
        "wearable app",
    } <= terms
    assert "source" not in terms
    assert "project" not in terms
    assert "security" not in terms
    assert "evidence" not in terms


def test_domain_leakage_terms_can_exclude_historical_sentinels() -> None:
    terms = set(leakage.domain_leakage_terms(include_historical=False))

    assert "quantum communication" in terms
    assert "wearable app" not in terms


def test_default_matrix_cases_each_contribute_distinctive_leakage_terms() -> None:
    cases = leakage.default_cases()

    assert leakage.cases_missing_leakage_terms(cases) == ()
    assert all(leakage.case_leakage_terms(case) for case in cases)


def test_declared_leakage_terms_are_not_padded_with_required_quality_anchors() -> None:
    terms = leakage.case_leakage_terms(
        SimpleNamespace(
            required_terms=("wafer", "reliability", "agent"),
            leakage_terms=("wafer lot", "chamber exposure"),
        )
    )

    assert terms == ("chamber exposure", "wafer lot")


def test_case_leakage_terms_derive_distinctive_prompt_vocabulary() -> None:
    terms = set(
        leakage.case_leakage_terms(
            SimpleNamespace(
                name="quantum communication lab",
                prompt=(
                    "Create a greenfield proposal for a quantum communication lab that records "
                    "entangled photon pairs, Bell inequality checks, QBER thresholds, and CHSH "
                    "review evidence."
                ),
                required_terms=("quantum", "qber"),
                leakage_terms=("bell inequality",),
            )
        )
    )

    assert "bell inequality" in terms
    assert "entangled photon" in terms
    assert "quantum communication" in terms
    assert "quantum" not in terms
    assert "create" not in terms
    assert "greenfield proposal" not in terms


def test_source_text_terms_skip_platform_native_governance_phrases() -> None:
    terms = set(
        leakage.case_leakage_terms(
            SimpleNamespace(
                prompt=(
                    "Create an ICU review workspace that preserves handoff evidence, "
                    "tracks manual override exceptions, lets operators request review, "
                    "and publishes readiness for the support team."
                ),
                required_terms=("icu", "override"),
                leakage_terms=("ventilator event review",),
            )
        )
    )

    assert "ventilator event review" in terms
    assert "handoff evidence" not in terms
    assert "manual override" not in terms
    assert "operators request" not in terms
    assert "support team" not in terms


def test_source_text_terms_keep_domain_rich_phrases_without_declared_terms() -> None:
    terms = set(
        leakage.case_leakage_terms(
            SimpleNamespace(
                prompt=(
                    "Plan a tokamak experiment desk for plasma physicists to verify coil "
                    "configuration, diagnostic calibration, interlock exceptions, and "
                    "countdown telemetry evidence."
                ),
                required_terms=("tokamak", "plasma", "interlock"),
                leakage_terms=(),
            )
        )
    )

    assert "diagnostic calibration" in terms
    assert "calibration interlock" in terms
    assert "plasma physicists" in terms
    assert "countdown telemetry" in terms
    assert "a tokamak experiment" not in terms


def test_generic_required_anchors_do_not_reenter_leakage_custody_noise() -> None:
    terms = leakage.case_leakage_terms(
        SimpleNamespace(
            required_terms=("artifact", "protocol", "sample", "interpreter", "model"),
            leakage_terms=("lab sample custody",),
        )
    )

    assert terms == ("lab sample custody",)


def test_domain_leakage_terms_accept_custom_matrix_cases_without_required_anchor_noise() -> None:
    terms = set(
        leakage.domain_leakage_terms(
            (
                SimpleNamespace(
                    prompt="Coordinate xenobot culture transfer and organoid chamber evidence.",
                    required_terms=("xenobot", "tribunal", "agent", "casebook"),
                ),
                SimpleNamespace(
                    prompt="Compare neutrino observatory exposure logs before detector recalibration.",
                    required_terms=("neutrino observatory", "release"),
                ),
            ),
            include_historical=False,
        )
    )

    assert "xenobot culture" in terms
    assert "neutrino observatory" in terms
    assert "tribunal" not in terms
    assert "agent" not in terms
    assert "casebook" not in terms
    assert "release" not in terms


def test_required_terms_do_not_create_platform_custody_false_positives() -> None:
    terms = set(
        leakage.case_leakage_terms(
            SimpleNamespace(
                prompt=(
                    "Plan wildfire evacuation review with smoke window forecasts, subtitle evidence notes, "
                    "ballast crew timing, and ingredient substitution approvals."
                ),
                required_terms=("smoke", "subtitle", "ballast", "substitution"),
                leakage_terms=(),
            )
        )
    )

    assert "smoke" not in terms
    assert "subtitle" not in terms
    assert "ballast" not in terms
    assert "substitution" not in terms
    assert any("wildfire" in term for term in terms)


def test_source_text_terms_do_not_cross_case_field_boundaries() -> None:
    terms = set(
        leakage.case_leakage_terms(
            SimpleNamespace(
                name="geothermal drilling window planner",
                prompt="Plan a new geothermal drilling board for borehole approval.",
                required_terms=("geothermal", "drilling"),
                leakage_terms=(),
            )
        )
    )

    assert "planner plan" not in terms
    assert "geothermal drilling" in terms


def test_explicit_leakage_terms_can_use_platform_words_inside_project_phrase() -> None:
    terms = leakage.case_leakage_terms(
        SimpleNamespace(
            required_terms=("agent", "tool", "tribunal"),
            leakage_terms=("agent tool permission tribunal",),
        )
    )

    assert terms == ("agent tool permission tribunal",)


def test_scan_repo_blocks_fixture_terms_in_platform_code(tmp_path: Path) -> None:
    platform_file = tmp_path / "src" / "odylith" / "runtime" / "example.py"
    platform_file.parent.mkdir(parents=True)
    platform_file.write_text('PROMPT = "quantum onboarding should never live here"\\n', encoding="utf-8")

    findings = leakage.scan_repo(tmp_path, terms=("quantum",))

    assert findings == (
        leakage.LeakageFinding(location="src/odylith/runtime/example.py", term="quantum", line=1),
    )


def test_current_platform_source_does_not_carry_historical_conflict_domain_phrase() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    assert leakage.scan_repo(repo_root, terms=("conflict of interest",)) == ()


def test_scan_repo_allows_fixture_terms_in_governance_evidence(tmp_path: Path) -> None:
    evidence_file = tmp_path / "odylith" / "casebook" / "bugs" / "repro.md"
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text("quantum failure reproduced here\\n", encoding="utf-8")

    assert leakage.scan_repo(tmp_path, terms=("quantum",)) == ()


def test_scan_repo_blocks_fixture_terms_in_component_forensics(tmp_path: Path) -> None:
    forensics_file = (
        tmp_path
        / "odylith"
        / "registry"
        / "source"
        / "components"
        / "release"
        / "FORENSICS.v1.json"
    )
    forensics_file.parent.mkdir(parents=True)
    forensics_file.write_text(
        '{"timeline":[{"summary":"quantum scenario copied into Registry"}]}\\n',
        encoding="utf-8",
    )

    findings = leakage.scan_repo(tmp_path, terms=("quantum",))

    assert findings == (
        leakage.LeakageFinding(
            location="odylith/registry/source/components/release/FORENSICS.v1.json",
            term="quantum",
            line=1,
        ),
    )


def test_scan_repo_blocks_fixture_terms_in_root_codex_guidance(tmp_path: Path) -> None:
    guidance_file = tmp_path / ".codex" / "agents" / "example.toml"
    guidance_file.parent.mkdir(parents=True)
    guidance_file.write_text('description = "digestive health must not live here"\\n', encoding="utf-8")

    findings = leakage.scan_repo(tmp_path, terms=("digestive health",))

    assert findings == (
        leakage.LeakageFinding(location=".codex/agents/example.toml", term="digestive health", line=1),
    )


def test_scan_repo_blocks_fixture_terms_in_docs(tmp_path: Path) -> None:
    docs_file = tmp_path / "docs" / "operator.md"
    docs_file.parent.mkdir(parents=True)
    docs_file.write_text("wearable app should stay out of platform docs\\n", encoding="utf-8")

    findings = leakage.scan_repo(tmp_path, terms=("wearable app",))

    assert findings == (
        leakage.LeakageFinding(location="docs/operator.md", term="wearable app", line=1),
    )


def test_scan_repo_blocks_fixture_terms_in_release_scripts(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "release" / "proof.py"
    script.parent.mkdir(parents=True)
    script.write_text('PROMPT = "quantum onboarding should never live here"\\n', encoding="utf-8")

    findings = leakage.scan_repo(tmp_path, terms=("quantum",))

    assert findings == (
        leakage.LeakageFinding(location="scripts/release/proof.py", term="quantum", line=1),
    )


def test_scan_repo_allows_release_fixture_catalog_vocabulary(tmp_path: Path) -> None:
    fixture = tmp_path / "scripts" / "release" / "greenfield_post_confirm_matrix_cases.py"
    fixture.parent.mkdir(parents=True)
    fixture.write_text('PROMPT = "quantum communication fixture lives here"\\n', encoding="utf-8")

    assert leakage.scan_repo(tmp_path, terms=("quantum communication",)) == ()


def test_scan_repo_blocks_wrapped_phrase_leakage(tmp_path: Path) -> None:
    platform_file = tmp_path / "src" / "odylith" / "runtime" / "example.py"
    platform_file.parent.mkdir(parents=True)
    platform_file.write_text('VALUE = "personalized\nnotification delivery"\\n', encoding="utf-8")

    findings = leakage.scan_repo(tmp_path, terms=("personalized notification delivery",))

    assert findings == (
        leakage.LeakageFinding(
            location="src/odylith/runtime/example.py",
            term="personalized notification delivery",
            line=1,
        ),
    )


def test_scan_repo_blocks_identifier_shaped_phrase_leakage(tmp_path: Path) -> None:
    platform_file = tmp_path / "src" / "odylith" / "runtime" / "example.py"
    platform_file.parent.mkdir(parents=True)
    platform_file.write_text(
        "securityDisclosureCouncilPrompt = True\n"
        "securitydisclosurecouncilprompt = True\n",
        encoding="utf-8",
    )

    findings = leakage.scan_repo(tmp_path, terms=("security disclosure council",))

    assert findings == (
        leakage.LeakageFinding(
            location="src/odylith/runtime/example.py",
            term="security disclosure council",
            line=1,
        ),
        leakage.LeakageFinding(
            location="src/odylith/runtime/example.py",
            term="security disclosure council",
            line=2,
        ),
    )


def test_scan_dist_blocks_fixture_terms_inside_runtime_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "odylith-0.1.15-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("odylith/runtime/example.py", 'VALUE = "wafer custody"\\n')
        zf.writestr("tests/test_fixture.py", 'VALUE = "wafer custody"\\n')

    findings = leakage.scan_dist(tmp_path, terms=("wafer",))

    assert findings == (
        leakage.LeakageFinding(
            location="wheel:odylith-0.1.15-py3-none-any.whl:odylith/runtime/example.py",
            term="wafer",
            line=1,
        ),
    )


def test_scan_dist_blocks_fixture_terms_inside_runtime_tarball(tmp_path: Path) -> None:
    archive = tmp_path / "odylith-runtime-linux-x86_64.tar.gz"
    payload = tmp_path / "payload" / "runtime" / "lib" / "python3.13" / "site-packages" / "odylith"
    runtime_file = payload / "runtime" / "example.py"
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text('VALUE = "fifa tracker must not be shipped"\\n', encoding="utf-8")
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(tmp_path / "payload" / "runtime", arcname="runtime")

    findings = leakage.scan_dist(tmp_path, terms=("fifa tracker",))

    assert findings == (
        leakage.LeakageFinding(
            location=(
                "tar:odylith-runtime-linux-x86_64.tar.gz:"
                "runtime/lib/python3.13/site-packages/odylith/runtime/example.py"
            ),
            term="fifa tracker",
            line=1,
        ),
    )


def test_scan_dist_ignores_third_party_runtime_tarball_files(tmp_path: Path) -> None:
    archive = tmp_path / "odylith-runtime-linux-x86_64.tar.gz"
    payload = tmp_path / "payload" / "runtime" / "lib" / "python3.13" / "site-packages" / "third_party"
    third_party_file = payload / "example.py"
    third_party_file.parent.mkdir(parents=True)
    third_party_file.write_text('VALUE = "fifa tracker in dependency fixture"\\n', encoding="utf-8")
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(tmp_path / "payload" / "runtime", arcname="runtime")

    assert leakage.scan_dist(tmp_path, terms=("fifa tracker",)) == ()


def test_scan_dist_allows_matrix_proof_json_as_evidence(tmp_path: Path) -> None:
    proof = tmp_path / "greenfield-post-confirm-matrix-20260629.v1.json"
    proof.write_text('{"case": "quantum communication lab"}\\n', encoding="utf-8")

    assert leakage.scan_dist(tmp_path, terms=("quantum",)) == ()


def test_main_returns_failed_status_for_platform_leak(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    platform_file = tmp_path / "src" / "odylith" / "runtime" / "example.py"
    platform_file.parent.mkdir(parents=True)
    platform_file.write_text('PROMPT = "qber must not be hardcoded"\\n', encoding="utf-8")

    exit_code = leakage.main(["--repo-root", str(tmp_path)])

    assert exit_code == 1
    assert "platform domain leakage check failed" in capsys.readouterr().err
