from __future__ import annotations

import importlib.util
import io
import json
import tarfile
from pathlib import Path

from odylith.install.managed_runtime import managed_runtime_platform_by_slug, supported_managed_runtime_feature_packs

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module():
    path = REPO_ROOT / "scripts" / "release" / "publish_release_assets.py"
    spec = importlib.util.spec_from_file_location("publish_release_assets", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_install_script_verifies_signed_release_assets_before_activation(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    text = output_path.read_text(encoding="utf-8")
    assert "gh release download" not in text
    assert "release-manifest.json" in text
    assert "release-manifest.json.sigstore.json" in text
    assert "build-provenance.v1.json" in text
    assert "odylith.sbom.spdx.json" in text
    assert 'runtime_asset_name="$(detect_runtime_asset)"' in text
    assert "odylith-runtime-darwin-arm64.tar.gz" in text
    assert "odylith-runtime-linux-arm64.tar.gz" in text
    assert "odylith-runtime-linux-x86_64.tar.gz" in text
    assert "Intel macOS and Windows are not supported in this release." in text
    assert "say() {" in text
    assert "step() {" in text
    assert "banner() {" in text
    assert "require_command() {" in text
    assert "detect_repo_root() {" in text
    assert "describe_repo_root_choice() {" in text
    assert "platform_display_name() {" in text
    assert "allow_local_http_asset() {" in text
    assert "fetch_asset() {" in text
    assert "http://127.0.0.1/*|http://127.0.0.1:*/*|http://localhost/*|http://localhost:*/*|http://[::1]/*|http://[::1]:*/*" in text
    assert "--proto '=https' --tlsv1.2 --retry 3" in text
    assert " ██████╗ ██████╗ ██╗   ██╗██╗     ██╗████████╗██╗  ██╗" in text
    assert "██╔═══██╗██╔══██╗╚██╗ ██╔╝██║     ██║╚══██╔══╝██║  ██║" in text
    assert " ╚═════╝ ╚═════╝    ╚═╝   ╚══════╝╚═╝   ╚═╝   ╚═╝  ╚═╝" in text
    assert "repo_root_reason='agents'" in text
    assert "repo_root_reason='git'" in text
    assert "repo_root_reason='folder'" in text
    assert "No root AGENTS.md was found above this directory. Odylith will create one at the detected Git root." in text
    assert "No enclosing AGENTS.md or .git was found. Odylith will treat the current folder as the repo root and create a root AGENTS.md here." in text
    assert "Git-aware features stay limited until this folder is backed by Git." in text
    assert "working-tree intelligence, background autospawn, and git-fsmonitor watcher help stay reduced for now." in text
    assert 'say "Odylith is getting this repo ready."' in text
    assert 'say "Working in repo: $repo_root."' in text
    assert 'say "No setup questions. Odylith will pick the right managed assets for this machine."' in text
    assert 'say "Your repo\'s own Python toolchain stays untouched."' in text
    assert "sigstore_stderr_is_benign() {" in text
    assert "verify_sigstore_identity() {" in text
    assert "grep -Eiq 'unsupported key type:[[:space:]]*7'" in text
    assert "grep -Eiq 'tuf.*offline|offline.*tuf'" in text
    assert 'step "Fetching the secure bootstrap runtime"' in text
    assert 'step "Verifying signed release evidence"' in text
    assert 'step "Activating Odylith"' in text
    assert 'say "Finishing the full Odylith setup inside the managed runtime."' in text
    assert 'say "First install may take a minute. Later upgrades reuse unchanged runtime layers so routine updates stay lean."' in text
    assert 'say "Odylith is live."' in text
    assert 'say \'Quick posture check: ./.odylith/bin/odylith version --repo-root "$repo_root"\'' in text
    assert "runtime-members.txt" in text
    assert "managed runtime bundle contains unexpected member path" in text
    assert "managed runtime bundle contains unsafe member path" in text
    assert "managed runtime bundle contains unsafe link target" in text
    assert "bootstrap_runtime=\"$tmpdir/bootstrap/runtime\"" in text
    assert "bootstrap_python=\"$bootstrap_runtime/bin/python\"" in text
    assert "\"$bootstrap_python\" -m sigstore verify identity \"$asset_path\"" in text
    assert "2>\"$stderr_path\"" in text
    assert "verify_sigstore_identity \"$tmpdir/$runtime_asset_name\" \"$tmpdir/$runtime_asset_name.sigstore.json\"" in text
    assert "validate_release.py" in text
    assert "expected_supported_platforms" in text
    assert "runtime_asset_to_slug" in text
    assert "re.fullmatch(rf'odylith-{re.escape(version)}-.*\\.whl', name)" in text
    assert "release manifest supported_platforms mismatch" in text
    assert "managed runtime bundle metadata python version mismatch" in text
    assert "managed runtime bundle metadata source wheel mismatch" in text
    assert "managed runtime bundle missing required paths" in text
    assert "runtime-verification.v1.json" in text
    assert "write_runtime_trust.py" in text
    assert "from odylith.install.runtime_integrity import write_managed_runtime_trust" in text
    assert "\"$version_root/bin/python\" \"$tmpdir/write_runtime_trust.py\" \"$repo_root\" \"$version_root\"" in text
    assert "rm -rf \"$version_root\"" in text
    assert "mkdir -p \"$state_root/runtime/versions\" \"$state_root/bin\"" in text
    assert "mv \"$bootstrap_runtime\" \"$version_root\"" in text
    assert "-m sigstore verify identity" in text
    assert "require_command curl" in text
    assert "require_command tar" in text
    assert "banner" in text
    assert "detect_repo_root" in text
    assert "version_root=\"$state_root/runtime/versions/$release_version\"" in text
    assert "\"$state_root/bin/odylith\" install --repo-root \"$repo_root\" --version \"$release_version\" --align-pin" in text
    assert text.index("\"$version_root/bin/python\" \"$tmpdir/write_runtime_trust.py\" \"$repo_root\" \"$version_root\"") < text.index(
        "\"$state_root/bin/odylith\" install --repo-root \"$repo_root\" --version \"$release_version\" --align-pin"
    )
    assert "read -p" not in text
    assert "select " not in text
    assert "unset VIRTUAL_ENV" in text
    assert "unset CONDA_PREFIX" in text
    assert "unset PYTHONHOME" in text
    assert "unset PYTHONPATH" in text
    assert "export PYTHONNOUSERSITE=1" in text
    assert text.index("unset VIRTUAL_ENV") < text.index("bootstrap_python=\"$bootstrap_runtime/bin/python\"")
    assert text.index("detect_repo_root") < text.index("fetch_asset \"$release_base_url/$runtime_asset_name\"")
    assert "AGENTS.md not found" not in text


def test_publish_release_assets_rejects_non_canonical_release_context() -> None:
    module = _load_module()

    try:
        module._require_canonical_release_context(repo="someone-else/odylith")  # noqa: SLF001
    except ValueError as exc:
        assert "canonical repo" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected canonical release context validation to fail")


def test_publish_release_assets_accepts_canonical_github_actions_context(monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "odylith/odylith")
    monkeypatch.setenv("GITHUB_ACTOR", "freedom-research")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")

    module._require_canonical_release_context(repo="odylith/odylith")  # noqa: SLF001


def test_release_manifest_tracks_third_party_attribution_asset(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "release-manifest.json"
    wheel = tmp_path / "odylith-1.2.3-py3-none-any.whl"
    install_sh = tmp_path / "install.sh"
    provenance = tmp_path / "build-provenance.v1.json"
    sbom = tmp_path / "odylith.sbom.spdx.json"
    attribution = tmp_path / "THIRD_PARTY_ATTRIBUTION.md"
    runtime_bundle = tmp_path / "odylith-runtime-linux-x86_64.tar.gz"

    wheel.write_bytes(b"wheel")
    install_sh.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    provenance.write_text("{}", encoding="utf-8")
    sbom.write_text("{}", encoding="utf-8")
    attribution.write_text("# attribution\n", encoding="utf-8")
    runtime_bundle.write_bytes(b"runtime")

    module._write_release_manifest(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        wheel=wheel,
        install_sh=install_sh,
        provenance=provenance,
        sbom=sbom,
        third_party_attribution=attribution,
        feature_packs=[],
        runtime_bundles=[
            (
                next(
                    item
                    for item in module.supported_managed_runtime_platforms()
                    if item.slug == "linux-x86_64"
                ),
                runtime_bundle,
            )
        ],
    )

    payload = output_path.read_text(encoding="utf-8")
    assert "THIRD_PARTY_ATTRIBUTION.md" in payload


def test_local_provenance_defaults_to_authoritative_actor_for_canonical_repo(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.delenv("GITHUB_ACTOR", raising=False)

    output_path = tmp_path / "build-provenance.v1.json"
    wheel = tmp_path / "odylith-1.2.3-py3-none-any.whl"
    runtime_bundle = tmp_path / "odylith-runtime-linux-x86_64.tar.gz"

    wheel.write_bytes(b"wheel")
    runtime_bundle.write_bytes(b"runtime")

    module._write_provenance(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        allow_local=True,
        feature_packs=[],
        wheel=wheel,
        runtime_bundles=[
            (
                next(
                    item
                    for item in module.supported_managed_runtime_platforms()
                    if item.slug == "linux-x86_64"
                ),
                runtime_bundle,
            )
        ],
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["actor"] == "freedom-research"


def test_publish_release_assets_uses_supported_macos_wheel_tags() -> None:
    module = _load_module()
    platforms = {item.slug: item for item in module.supported_managed_runtime_platforms()}

    darwin_arm64 = module._pip_platform_args(platforms["darwin-arm64"])  # noqa: SLF001

    assert darwin_arm64 == ("macosx_12_0_arm64", "cp313")
    assert "darwin-x86_64" not in platforms


def test_context_engine_feature_pack_omits_watchdog_on_linux() -> None:
    feature_pack = next(
        item for item in supported_managed_runtime_feature_packs() if item.pack_id == "odylith-context-engine-memory"
    )

    darwin_requirements = feature_pack.python_requirements_for_platform(managed_runtime_platform_by_slug("darwin-arm64"))
    linux_arm64_requirements = feature_pack.python_requirements_for_platform(
        managed_runtime_platform_by_slug("linux-arm64")
    )
    linux_x86_64_requirements = feature_pack.python_requirements_for_platform(
        managed_runtime_platform_by_slug("linux-x86_64")
    )

    assert "watchdog>=6.0,<7.0" in darwin_requirements
    assert "watchdog>=6.0,<7.0" not in linux_arm64_requirements
    assert "watchdog>=6.0,<7.0" not in linux_x86_64_requirements
    assert linux_arm64_requirements == (
        "lancedb==0.30.0",
        "tantivy>=0.25.1,<0.26.0",
    )
    assert linux_x86_64_requirements == (
        "lancedb==0.30.0",
        "tantivy>=0.25.1,<0.26.0",
    )


def test_runtime_bundle_builder_rewrites_upstream_root_without_extracting_case_colliding_paths(tmp_path: Path) -> None:
    module = _load_module()
    upstream_archive = tmp_path / "upstream.tar.gz"
    output_archive = tmp_path / "output.tar.gz"
    with tarfile.open(upstream_archive, "w:gz") as archive:
        for directory in (
            "python",
            "python/share",
            "python/share/terminfo",
            "python/share/terminfo/n",
            "python/share/terminfo/N",
        ):
            info = tarfile.TarInfo(directory)
            info.type = tarfile.DIRTYPE
            archive.addfile(info)
        for name, payload in (
            ("python/share/terminfo/n/ncr260vt300wpp", b"lower\n"),
            ("python/share/terminfo/N/NCR260VT300WPP", b"upper\n"),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    with tarfile.open(output_archive, "w:gz") as archive:
        module._copy_upstream_archive_into_runtime_bundle(  # noqa: SLF001
            upstream_archive_path=upstream_archive,
            destination_archive=archive,
            source_root="python",
            target_root="runtime",
        )

    with tarfile.open(output_archive, "r:gz") as archive:
        names = set(archive.getnames())

    assert "runtime/share/terminfo/n/ncr260vt300wpp" in names
    assert "runtime/share/terminfo/N/NCR260VT300WPP" in names
    assert "python/share/terminfo/n/ncr260vt300wpp" not in names


def test_runtime_wrapper_writer_creates_bin_directory(tmp_path: Path) -> None:
    module = _load_module()
    runtime_root = tmp_path / "runtime"

    module._write_runtime_odylith_wrapper(runtime_root=runtime_root)  # noqa: SLF001

    wrapper = runtime_root / "bin" / "odylith"
    assert wrapper.is_file()
    assert 'exec "$script_dir/python" -m odylith.cli "$@"' in wrapper.read_text(encoding="utf-8")


def test_release_upload_artifacts_include_raw_runtime_bundles_and_attribution(tmp_path: Path) -> None:
    module = _load_module()
    wheel = tmp_path / "odylith-1.2.3-py3-none-any.whl"
    install_sh = tmp_path / "install.sh"
    release_manifest = tmp_path / "release-manifest.json"
    provenance = tmp_path / "build-provenance.v1.json"
    sbom = tmp_path / "odylith.sbom.spdx.json"
    sha256sums = tmp_path / "SHA256SUMS"
    attribution = tmp_path / "THIRD_PARTY_ATTRIBUTION.md"
    runtime_bundle = tmp_path / "odylith-runtime-linux-x86_64.tar.gz"
    signature_bundle = tmp_path / "odylith-runtime-linux-x86_64.tar.gz.sigstore.json"

    artifacts = module._release_upload_artifacts(  # noqa: SLF001
        wheel=wheel,
        install_sh=install_sh,
        release_manifest=release_manifest,
        provenance=provenance,
        sbom=sbom,
        sha256sums=sha256sums,
        third_party_attribution=attribution,
        feature_packs=[],
        runtime_bundles=[
            (
                next(
                    item
                    for item in module.supported_managed_runtime_platforms()
                    if item.slug == "linux-x86_64"
                ),
                runtime_bundle,
            )
        ],
        signature_bundles=[signature_bundle],
    )

    names = [path.name for path in artifacts]
    assert "THIRD_PARTY_ATTRIBUTION.md" in names
    assert "odylith-runtime-linux-x86_64.tar.gz" in names
    assert "SHA256SUMS" in names
    assert "odylith-runtime-linux-x86_64.tar.gz.sigstore.json" in names


def test_release_preflight_uses_isolated_temp_dist_dir() -> None:
    text = (REPO_ROOT / "bin" / "release-preflight").read_text(encoding="utf-8")
    shared = (REPO_ROOT / "bin" / "_odylith.sh").read_text(encoding="utf-8")

    assert 'preflight_root="$(mktemp -d "${TMPDIR:-/tmp}/odylith-release-preflight.XXXXXX")"' in text
    assert 'dist_dir="$preflight_root/dist"' in text
    assert 'trap \'rm -rf "$preflight_root"\' EXIT' in text
    assert 'run_release_proof_steps "$resolved_version" "$dist_dir"' in text
    assert 'run_release_proof_steps() {' in shared
    assert '"$odylith_python" "$odylith_host_repo_root/scripts/sync_version_truth.py" --repo-root . sync' in shared
    assert '"$odylith_python" -m hatch build --target wheel "$dist_dir"' in shared
    assert '--dist-dir "$dist_dir" --allow-local' in shared
    assert 'ODYLITH_RELEASE_PREFLIGHT_DIST_DIR="$dist_dir"' in shared
    assert 'glob.glob(os.path.join(dist_dir, "*.whl"))' in shared
    assert 'scripts/release/local_release_smoke.py --version "$resolved_version" --dist-dir "$dist_dir"' in shared


def test_release_candidate_is_pr_safe_non_publishing_current_checkout_lane() -> None:
    text = (REPO_ROOT / "bin" / "release-candidate").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")

    assert 'resolved_version="${requested_version:-${VERSION:-$(current_source_version)}}"' in text
    assert 'require_clean_worktree' in text
    assert 'run_release_proof_steps "$resolved_version" "$dist_dir"' in text
    assert 'benchmark compare --repo-root . --baseline last-shipped' in text
    assert 'release_version_session.py' not in text
    assert 'release_worktree.py' not in text
    assert 'release-candidate:' in makefile
    assert './bin/release-candidate "$(VERSION)"' in makefile
    assert "make release-candidate" in help_text


def test_lane_show_wraps_lane_status() -> None:
    text = (REPO_ROOT / "bin" / "lane-show").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")

    assert 'odylith_cli lane status --repo-root . "$@"' in text
    assert "lane-show:" in makefile
    assert "./bin/lane-show" in makefile
    assert "make lane-show" in help_text


def test_release_candidate_workflow_is_pull_request_safe() -> None:
    text = (REPO_ROOT / ".github" / "workflows" / "release-candidate.yml").read_text(encoding="utf-8")

    assert "pull_request:" in text
    assert "workflow_dispatch:" in text
    assert "make lane-show" in text
    assert "make release-candidate" in text
    assert "permissions:" in text
    assert "contents: read" in text
    assert "make dogfood-activate" not in text
    assert "gh release create" not in text
    assert "publish_release_assets.py" not in text


def test_dogfood_activate_bootstraps_missing_launcher_before_upgrade() -> None:
    text = (REPO_ROOT / "bin" / "dogfood-activate").read_text(encoding="utf-8")

    assert 'if [[ ! -x "$odylith_launcher" ]]; then' in text
    assert 'odylith_cli doctor --repo-root . --repair' in text
    assert text.index('odylith_cli doctor --repo-root . --repair') < text.index('launcher_cli upgrade --repo-root .')


def test_dev_validate_surfaces_detached_source_local_lane() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")
    dev_validate = (REPO_ROOT / "bin" / "dev-validate").read_text(encoding="utf-8")
    validate = (REPO_ROOT / "bin" / "validate").read_text(encoding="utf-8")

    assert "dev-validate:" in makefile
    assert "./bin/dev-validate" in makefile
    assert "make dev-validate" in help_text
    assert "detached source-local" in help_text
    assert '--dev-source-local' in dev_validate
    assert 'maintainer dev lane: validating detached source-local workspace changes' in dev_validate
    assert 'if [[ "${1:-}" == "--dev-source-local" ]]; then' in validate
    assert 'if [[ "$dev_source_local" != "true" ]]; then' in validate
    assert 'sync_args+=(--check-clean)' in validate
