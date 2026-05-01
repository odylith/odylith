from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import tarfile
import zipfile
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


def _extract_shell_function(script_text: str, name: str, next_name: str) -> str:
    start = script_text.index(f"{name}() {{")
    end = script_text.index(f"{next_name}() {{")
    return script_text[start:end].strip()


def _extract_shell_block(script_text: str, start_marker: str, end_marker: str) -> str:
    start = script_text.index(start_marker)
    end = script_text.index(end_marker)
    return script_text[start:end].strip()


def _run_detect_repo_root(*, tmp_path: Path, install_script_text: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    helper = tmp_path / "detect_repo_root.sh"
    detect_repo_root = _extract_shell_function(install_script_text, "detect_repo_root", "describe_repo_root_choice")
    helper.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                detect_repo_root,
                'cd "$1"',
                "detect_repo_root",
                'printf \'%s\\n%s\\n\' \"$repo_root\" \"$repo_root_reason\"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)
    return subprocess.run(
        ["bash", str(helper), str(cwd)],
        check=False,
        capture_output=True,
        text=True,
    )


def _run_verify_sigstore_identity(
    *,
    tmp_path: Path,
    install_script_text: str,
    stderr_text: str = "",
    stdout_text: str = "",
    exit_code: int = 0,
) -> subprocess.CompletedProcess[str]:
    helper = tmp_path / "verify_sigstore_identity.sh"
    fake_python = tmp_path / "fake-bootstrap-python"
    asset_path = tmp_path / "asset.txt"
    bundle_path = tmp_path / "asset.txt.sigstore.json"
    shell_block = _extract_shell_block(
        install_script_text,
        "sigstore_normalize_line() {",
        'release_version="${ODYLITH_VERSION:-latest}"',
    )
    asset_path.write_text("payload\n", encoding="utf-8")
    bundle_path.write_text("{}\n", encoding="utf-8")
    fake_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "printf '%s' \"${ODYLITH_FAKE_SIGSTORE_STDOUT:-}\"",
                "printf '%s' \"${ODYLITH_FAKE_SIGSTORE_STDERR:-}\" >&2",
                "exit \"${ODYLITH_FAKE_SIGSTORE_EXIT:-0}\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    helper.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/odylith-sigstore.XXXXXX")"',
                'trap \'rm -rf "$tmpdir"\' EXIT',
                f'bootstrap_python="{fake_python}"',
                'signer_identity="freedom-research"',
                'oidc_issuer="https://token.actions.githubusercontent.com"',
                shell_block,
                'verify_sigstore_identity "$1" "$2"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)
    env = {
        "ODYLITH_FAKE_SIGSTORE_STDERR": stderr_text,
        "ODYLITH_FAKE_SIGSTORE_STDOUT": stdout_text,
        "ODYLITH_FAKE_SIGSTORE_EXIT": str(exit_code),
    }
    return subprocess.run(
        ["bash", str(helper), str(asset_path), str(bundle_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _run_generated_install_decision(
    *,
    tmp_path: Path,
    install_script_text: str,
    repo_root: Path,
    fake_pin_version: str = "",
    fake_active_version: str = "",
    fake_last_known_good_version: str = "",
) -> subprocess.CompletedProcess[str]:
    helper = tmp_path / "install_decision.sh"
    command_log = tmp_path / "command.log"
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    fake_python = version_root / "bin" / "python"
    fake_python.parent.mkdir(parents=True, exist_ok=True)
    fake_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'if [[ "${1:-}" == */read_install_versions.py ]]; then',
                '  printf "%s\\t%s\\t%s\\n" "${ODYLITH_FAKE_PIN_VERSION:-}" "${ODYLITH_FAKE_ACTIVE_VERSION:-}" "${ODYLITH_FAKE_LAST_KNOWN_GOOD_VERSION:-}"',
                "  exit 0",
                "fi",
                f'printf "%s\\n" "$*" >> "{command_log}"',
                "exit 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    decision_block = _extract_shell_block(
        install_script_text,
        'pin_path="$repo_root/odylith/runtime/source/product-version.v1.json"',
        'say "done   Install finished."',
    )
    helper.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/odylith-install-decision.XXXXXX")"',
                'trap \'rm -rf "$tmpdir"\' EXIT',
                f'repo_root="{repo_root}"',
                'state_root="$repo_root/.odylith"',
                'release_version="1.2.3"',
                'version_root="$state_root/runtime/versions/$release_version"',
                "say() { :; }",
                decision_block,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)
    return subprocess.run(
        ["bash", str(helper)],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ODYLITH_FAKE_PIN_VERSION": fake_pin_version,
            "ODYLITH_FAKE_ACTIVE_VERSION": fake_active_version,
            "ODYLITH_FAKE_LAST_KNOWN_GOOD_VERSION": fake_last_known_good_version,
        },
    )


def _run_fetch_asset(
    *,
    tmp_path: Path,
    install_script_text: str,
    url: str,
    allow_insecure_localhost: bool = False,
    fake_curl_exit: int = 0,
    fake_curl_stderr: str = "",
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    helper = tmp_path / "fetch_asset.sh"
    destination = tmp_path / "asset.bin"
    command_log = tmp_path / "curl.args"
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(exist_ok=True)
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f'printf "%s\\n" "$*" > "{command_log}"',
                'destination=""',
                'while (($#)); do',
                '  case "$1" in',
                '    -o)',
                '      destination="$2"',
                "      shift 2",
                "      ;;",
                "    *) shift ;;",
                "  esac",
                "done",
                'if [[ "${FAKE_CURL_EXIT:-0}" != "0" ]]; then',
                '  printf "%s" "${FAKE_CURL_STDERR:-}" >&2',
                '  exit "${FAKE_CURL_EXIT}"',
                "fi",
                'printf "payload" > "$destination"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)
    fetch_block = _extract_shell_block(
        install_script_text,
        "allow_local_http_asset() {",
        'tmpdir="$(mktemp -d)"',
    )
    helper.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/odylith-fetch.XXXXXX")"',
                'trap \'rm -rf "$tmpdir"\' EXIT',
                f'local_release_allow_insecure="{"1" if allow_insecure_localhost else "0"}"',
                fetch_block,
                f'fetch_asset "{url}" "{destination}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)
    env = {
        **(extra_env or {}),
        "FAKE_CURL_EXIT": str(fake_curl_exit),
        "FAKE_CURL_STDERR": fake_curl_stderr,
        "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
    }
    return subprocess.run(
        ["bash", str(helper)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


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
    assert "printf '  %-6s %s\\n' \"$label\" \"$message\"" in text
    assert "progress_supported() {" in text
    assert "progress_start() {" in text
    assert "progress_done() {" in text
    assert "progress_clear() {" in text
    assert '[[ "${ODYLITH_INSTALL_PROGRESS:-1}" != "0" && -t 1 ]]' in text
    assert "printf '\\r  %-6s %s [%s] %ss'" in text
    assert "banner() {" in text
    assert 'if [[ "${ODYLITH_INSTALL_BANNER:-1}" == "0" ]]; then' in text
    assert "printf 'Odylith\\n'" in text
    assert "require_command() {" in text
    assert "detect_repo_root() {" in text
    assert 'local candidate git_candidate="" start_dir' in text
    assert "describe_repo_root_choice() {" in text
    assert "platform_display_name() {" in text
    assert "allow_local_http_asset() {" in text
    assert "release_url_scheme() {" in text
    assert "proxy_env_summary() {" in text
    assert "emit_fetch_failure() {" in text
    assert "fetch_asset() {" in text
    assert 'local_release_allow_insecure="${ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST:-0}"' in text
    assert "http://127.0.0.1/*|http://127.0.0.1:*/*|http://localhost/*|http://localhost:*/*|http://[::1]/*|http://[::1]:*/*" in text
    assert "--proto '=https' --tlsv1.2 --retry 3" in text
    assert "Odylith refused insecure localhost release assets." in text
    assert "Detected proxy/TLS environment" in text
    assert "Check VPN, proxy, firewall, TLS inspection, and certificate settings." in text
    assert " ██████╗ ██████╗ ██╗   ██╗██╗     ██╗████████╗██╗  ██╗" in text
    assert "██╔═══██╗██╔══██╗╚██╗ ██╔╝██║     ██║╚══██╔══╝██║  ██║" in text
    assert " ╚═════╝ ╚═════╝    ╚═╝   ╚══════╝╚═╝   ╚═╝   ╚═╝  ╚═╝" in text
    assert "repo_root_reason='guidance'" in text
    assert "repo_root_reason='git'" in text
    assert "repo_root_reason='folder'" in text
    assert "setup  Adding Odylith guidance to this Git repo." in text
    assert "setup  Adding Odylith guidance to this folder." in text
    assert "Git-aware help turns on after this folder has a .git directory." in text
    assert 'say "Preparing this repo."' in text
    assert 'say "repo   $repo_root"' in text
    assert 'say "host   $platform_name."' in text
    assert 'say "safe   Your repo\'s own toolchain stays untouched."' in text
    assert "sigstore_normalize_line() {" in text
    assert "sigstore_log_is_benign() {" in text
    assert "sigstore_log_is_continuation() {" in text
    assert "emit_sigstore_log() {" in text
    assert "verify_sigstore_identity() {" in text
    assert (
        "grep -Eiq '(WARNING[[:space:]]+)?(Failed to load a trusted root key:[[:space:]]*)?"
        "unsupported([[:space:]]+[^[:space:]]+:[0-9]+)?[[:space:]]+key type:[[:space:]]*7'"
        in text
    )
    assert "grep -Eiq 'tuf.*offline|offline.*tuf'" in text
    assert '>"$stdout_path" 2>"$stderr_path"' in text
    assert 'cat "$stdout_path"' not in text
    assert 'cat "$stderr_path"' not in text
    assert 'stripped="${line#"${line%%[![:space:]]*}"}"' in text
    assert 'line="$(sigstore_normalize_line "$line")"' in text
    assert 'sigstore_log_is_continuation "$folded" "$line" "$stripped"' in text
    assert 'folded="$folded $stripped"' in text
    assert 'progress_start "fetch" "Downloading Odylith."' in text
    assert 'progress_done "fetch" "Download complete."' in text
    assert 'progress_start "check" "Checking the release."' in text
    assert 'progress_done "check" "Release verified."' in text
    assert 'progress_start "setup" "Installing local runtime."' in text
    assert 'progress_done "setup" "Local runtime ready."' in text
    assert 'say "setup  Writing repo files and launchers."' in text
    assert 'migration_state_dir="$repo_root/.odylith/state/migrations"' in text
    assert 'rm -rf "$migration_state_dir"' in text
    assert 'ODYLITH_INSTALL_COMPACT=1 ODYLITH_BOOTSTRAP_RUNTIME_PRESTAGED=1 "$version_root/bin/python" -m odylith.cli install' in text
    assert 'say "done   Install finished."' in text
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
    assert 'pin_path="$repo_root/odylith/runtime/source/product-version.v1.json"' in text
    assert 'install_state_path="$repo_root/.odylith/install.json"' in text
    assert 'customer_tree_path="$repo_root/odylith/AGENTS.md"' in text
    assert 'if [[ -f "$pin_path" && -f "$install_state_path" && -f "$customer_tree_path" ]]; then' in text
    assert (
        '"$version_root/bin/python" -m odylith.cli upgrade --repo-root "$repo_root" --to "$release_version" --write-pin'
        in text
    )
    assert 'say "resume Completing local install."' in text
    assert 'rm -f "$install_state_path" "$state_root/runtime/current"' in text
    assert '"$version_root/bin/python" -m odylith.cli install --repo-root "$repo_root" --version "$release_version"' in text
    assert 'ln -sfn "$version_root" "$state_root/runtime/current"' not in text
    assert "--align-pin" not in text
    assert text.index("\"$version_root/bin/python\" \"$tmpdir/write_runtime_trust.py\" \"$repo_root\" \"$version_root\"") < text.index(
        'pin_path="$repo_root/odylith/runtime/source/product-version.v1.json"'
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


def test_generated_install_script_requires_explicit_flag_for_localhost_http_assets(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_fetch_asset(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        url="http://127.0.0.1:8123/release-manifest.json",
    )

    assert completed.returncode == 2
    assert "refused insecure localhost release assets" in completed.stderr
    assert "ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST=1" in completed.stderr
    assert not (tmp_path / "curl.args").exists()


def test_generated_install_script_allows_flagged_localhost_http_assets(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_fetch_asset(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        url="http://localhost:8123/release-manifest.json",
        allow_insecure_localhost=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    curl_args = (tmp_path / "curl.args").read_text(encoding="utf-8")
    assert "--proto" not in curl_args
    assert (tmp_path / "asset.bin").read_text(encoding="utf-8") == "payload"


def test_generated_install_script_rejects_non_local_http_assets(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_fetch_asset(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        url="http://example.invalid/release-manifest.json",
        allow_insecure_localhost=True,
    )

    assert completed.returncode == 2
    assert "refused non-HTTPS release assets" in completed.stderr
    assert "localhost HTTP" in completed.stderr
    assert not (tmp_path / "curl.args").exists()


def test_generated_install_script_fetch_failure_prints_enterprise_network_hints(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_fetch_asset(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        url="https://github.com/odylith/odylith/releases/download/v1.2.3/release-manifest.json",
        fake_curl_exit=56,
        fake_curl_stderr="curl: (56) proxy reset connection\n",
        extra_env={"HTTPS_PROXY": "http://proxy.local:8080", "SSL_CERT_FILE": "/tmp/company.pem"},
    )

    assert completed.returncode == 2
    assert "could not download a release asset" in completed.stderr
    assert "proxy reset connection" in completed.stderr
    assert "Detected proxy/TLS environment: HTTPS_PROXY, SSL_CERT_FILE" in completed.stderr
    assert "Check VPN, proxy, firewall, TLS inspection, and certificate settings." in completed.stderr
    assert not (tmp_path / "asset.bin").exists()


def test_generated_install_script_repairs_stale_uninstall_residue_without_upgrade_dump(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    repo_root = tmp_path / "stale-uninstall"
    install_state = repo_root / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True)
    install_state.write_text('{"active_version":"1.2.2"}\n', encoding="utf-8")
    old_runtime = repo_root / ".odylith" / "runtime" / "versions" / "1.2.2"
    old_runtime.mkdir(parents=True)
    current = repo_root / ".odylith" / "runtime" / "current"
    current.symlink_to(old_runtime)
    migration_state_dir = repo_root / ".odylith" / "state" / "migrations"
    migration_state_dir.mkdir(parents=True)
    stale_ledger = migration_state_dir / "v0.1.11-visible-intervention-value-engine.v1.json"
    stale_ledger.write_text('{"migration_id":"v0.1.11-visible-intervention-value-engine"}\n', encoding="utf-8")

    completed = _run_generated_install_decision(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        repo_root=repo_root,
    )

    command_log = (tmp_path / "command.log").read_text(encoding="utf-8")
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "-m odylith.cli install --repo-root" in command_log
    assert "-m odylith.cli upgrade --repo-root" not in command_log
    assert not install_state.exists()
    assert not current.exists()
    assert not migration_state_dir.exists()


def test_generated_install_script_upgrades_only_complete_existing_install(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    repo_root = tmp_path / "complete-install"
    install_state = repo_root / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True)
    install_state.write_text('{"active_version":"1.2.2"}\n', encoding="utf-8")
    pin_path = repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json"
    pin_path.parent.mkdir(parents=True)
    pin_path.write_text('{"odylith_version":"1.2.2"}\n', encoding="utf-8")
    (repo_root / "odylith" / "AGENTS.md").write_text("# Odylith\n", encoding="utf-8")

    completed = _run_generated_install_decision(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        repo_root=repo_root,
    )

    command_log = (tmp_path / "command.log").read_text(encoding="utf-8")
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "-m odylith.cli upgrade --repo-root" in command_log
    assert "-m odylith.cli install --repo-root" not in command_log
    assert install_state.exists()


def test_generated_install_script_repairs_complete_already_current_install_without_upgrade_dump(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    repo_root = tmp_path / "already-current"
    install_state = repo_root / ".odylith" / "install.json"
    install_state.parent.mkdir(parents=True)
    install_state.write_text('{"active_version":"1.2.3","last_known_good_version":"1.2.3"}\n', encoding="utf-8")
    pin_path = repo_root / "odylith" / "runtime" / "source" / "product-version.v1.json"
    pin_path.parent.mkdir(parents=True)
    pin_path.write_text('{"odylith_version":"1.2.3"}\n', encoding="utf-8")
    (repo_root / "odylith" / "AGENTS.md").write_text("# Odylith\n", encoding="utf-8")

    completed = _run_generated_install_decision(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        repo_root=repo_root,
        fake_pin_version="1.2.3",
        fake_active_version="1.2.3",
        fake_last_known_good_version="1.2.3",
    )

    command_log = (tmp_path / "command.log").read_text(encoding="utf-8")
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "-m odylith.cli install --repo-root" in command_log
    assert "-m odylith.cli upgrade --repo-root" not in command_log
    assert install_state.exists()


def test_generated_install_script_detect_repo_root_is_strict_mode_safe_from_nested_agents_path(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    repo_root = tmp_path / "fresh-install"
    repo_root.mkdir()
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    nested = repo_root / "workspace" / "nested"
    nested.mkdir(parents=True)

    completed = _run_detect_repo_root(tmp_path=tmp_path, install_script_text=output_path.read_text(encoding="utf-8"), cwd=nested)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout.splitlines() == [str(repo_root), "guidance"]


def test_generated_install_script_detect_repo_root_accepts_nested_claude_path(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    repo_root = tmp_path / "fresh-install"
    repo_root.mkdir()
    (repo_root / "CLAUDE.md").write_text("# Repo Root\n", encoding="utf-8")
    nested = repo_root / "workspace" / "nested"
    nested.mkdir(parents=True)

    completed = _run_detect_repo_root(tmp_path=tmp_path, install_script_text=output_path.read_text(encoding="utf-8"), cwd=nested)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout.splitlines() == [str(repo_root), "guidance"]


def test_generated_install_script_detect_repo_root_accepts_nested_project_claude_path(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    repo_root = tmp_path / "fresh-install"
    (repo_root / ".claude").mkdir(parents=True)
    (repo_root / ".claude" / "CLAUDE.md").write_text("# Project Root\n", encoding="utf-8")
    nested = repo_root / "workspace" / "nested"
    nested.mkdir(parents=True)

    completed = _run_detect_repo_root(tmp_path=tmp_path, install_script_text=output_path.read_text(encoding="utf-8"), cwd=nested)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout.splitlines() == [str(repo_root), "guidance"]


def test_generated_install_script_detect_repo_root_falls_back_to_current_folder_without_markers(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    nested = tmp_path / "plain" / "nested"
    nested.mkdir(parents=True)

    completed = _run_detect_repo_root(tmp_path=tmp_path, install_script_text=output_path.read_text(encoding="utf-8"), cwd=nested)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout.splitlines() == [str(nested), "folder"]


def test_generated_install_script_verify_sigstore_identity_suppresses_wrapped_trusted_root_warning(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        stderr_text=(
            "Failed to load a trusted root key: unsupported  trust.py:177\n"
            "                    key type: 7\n"
        ),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stderr == ""


def test_generated_install_script_verify_sigstore_identity_suppresses_rich_trusted_root_warning(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        stderr_text=(
            "WARNING  Failed to load a trusted root key: unsupported trust.py:177\n"
            "         key type: 7\n"
        ),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_generated_install_script_verify_sigstore_identity_suppresses_unindented_trusted_root_continuation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        stderr_text="Failed to load a trusted root key: unsupported trust.py:177\nkey type: 7\n",
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_generated_install_script_verify_sigstore_identity_suppresses_ansi_trusted_root_warning(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        stderr_text=(
            "\x1b[33mWARNING\x1b[0m  Failed to load a trusted root key: unsupported \x1b[2mtrust.py:177\x1b[0m\n"
            "         \x1b[2mkey type: 7\x1b[0m\n"
        ),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_generated_install_script_verify_sigstore_identity_suppresses_stdout_trusted_root_warning(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        stdout_text=(
            "WARNING  Failed to load a trusted root key: unsupported trust.py:177\n"
            "         key type: 7\n"
        ),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_generated_install_script_verify_sigstore_identity_preserves_success_stdout(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        stdout_text="OK: asset verified\n",
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout == "OK: asset verified\n"
    assert completed.stderr == ""


def test_generated_install_script_verify_sigstore_identity_suppresses_warning_with_success_stdout(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        stdout_text="OK: asset verified\n",
        stderr_text=(
            "WARNING  Failed to load a trusted root key: unsupported trust.py:177\n"
            "         key type: 7\n"
        ),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout == "OK: asset verified\n"
    assert completed.stderr == ""


def test_generated_install_script_verify_sigstore_identity_suppresses_split_warning_label(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        stderr_text=(
            "WARNING\n"
            "Failed to load a trusted root key: unsupported trust.py:177\n"
            "key type: 7\n"
        ),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_generated_install_script_verify_sigstore_identity_filters_benign_warning_on_failure(
    tmp_path: Path,
) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        exit_code=2,
        stderr_text=(
            "WARNING  Failed to load a trusted root key: unsupported trust.py:177\n"
            "         key type: 7\n"
            "error: certificate identity mismatch\n"
        ),
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "certificate identity mismatch" in completed.stderr
    assert "trusted root key" not in completed.stderr
    assert "trust.py:177" not in completed.stderr
    assert "key type: 7" not in completed.stderr


def test_generated_install_script_verify_sigstore_identity_preserves_unexpected_warning(tmp_path: Path) -> None:
    module = _load_module()
    output_path = tmp_path / "install.sh"

    module._write_install_script(  # noqa: SLF001
        output_path=output_path,
        tag="v1.2.3",
        repo="odylith/odylith",
        odylith_wheel="odylith-1.2.3-py3-none-any.whl",
    )

    completed = _run_verify_sigstore_identity(
        tmp_path=tmp_path,
        install_script_text=output_path.read_text(encoding="utf-8"),
        stderr_text=(
            "Failed to load a trusted root key: unsupported  trust.py:177\n"
            "                    key type: 7\n"
            "warning: unexpected verifier chatter\n"
        ),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "unexpected verifier chatter" in completed.stderr
    assert "unsupported  trust.py:177" not in completed.stderr


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


def test_extract_wheel_into_site_packages_preserves_extra_metadata(tmp_path: Path) -> None:
    module = _load_module()
    wheel_path = tmp_path / "odylith-1.2.3-py3-none-any.whl"
    site_packages = tmp_path / "site-packages"
    attribution_path = (
        "odylith-1.2.3.dist-info/extra_metadata/THIRD_PARTY_ATTRIBUTION.md"
    )

    with zipfile.ZipFile(wheel_path, "w") as archive:
        archive.writestr(attribution_path, "# attribution\n")

    module._extract_wheel_into_site_packages(  # noqa: SLF001
        wheel_path=wheel_path,
        site_packages=site_packages,
    )

    assert (site_packages / attribution_path).read_text(encoding="utf-8") == "# attribution\n"


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
    assert "ODYLITH_RELEASE_BASE_URL=http://127.0.0.1:8123" in text
    assert 'ODYLITH_RELEASE_MAINTAINER_ROOT="${odylith_repo_root}"' in text
    assert "make local-release-assets" in help_text


def test_release_candidate_is_pr_safe_non_publishing_current_checkout_lane() -> None:
    text = (REPO_ROOT / "bin" / "release-candidate").read_text(encoding="utf-8")
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    help_text = (REPO_ROOT / "bin" / "help").read_text(encoding="utf-8")

    assert 'resolved_version="${requested_version:-${VERSION:-$(current_source_version)}}"' in text
    assert "candidate proof must evaluate the checked-out source tree" in text
    assert "git restore -- AGENTS.md CLAUDE.md .agents .claude .codex odylith/compass/runtime" in text
    assert "git clean -fd -- .agents .claude .codex odylith/compass/runtime" in text
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
    assert text.index('odylith_cli doctor --repo-root . --repair') < text.index('source_version="$(current_source_version)"')


def test_dogfood_activate_uses_source_upgrade_across_release_boundaries() -> None:
    text = (REPO_ROOT / "bin" / "dogfood-activate").read_text(encoding="utf-8")

    assert 'source_version="$(current_source_version)"' in text
    assert 'version_status="$(launcher_cli version --repo-root .)"' in text
    assert 'active_version="$(printf \'%s\\n\' "$version_status" | sed -n \'s/^Active: //p\' | head -n 1)"' in text
    assert 'pinned_version="$(printf \'%s\\n\' "$version_status" | sed -n \'s/^Pinned: //p\' | head -n 1)"' in text
    assert 'if [[ -n "$source_version" && -n "$active_version" && "$source_version" != "$active_version" ]]; then' in text
    assert 'odylith_cli upgrade --repo-root . --to "$source_version" --write-pin' in text
    assert 'elif [[ -n "$source_version" && -n "$pinned_version" && "$source_version" == "$active_version" && "$source_version" == "$pinned_version" ]]; then' in text
    assert 'launcher_cli dashboard refresh --repo-root .' in text
    assert 'else' in text
    assert 'launcher_cli upgrade --repo-root .' in text


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
