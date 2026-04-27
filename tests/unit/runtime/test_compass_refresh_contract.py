from __future__ import annotations

from odylith.runtime.surfaces import compass_refresh_contract


def test_normalize_refresh_profile_defaults_to_shell_safe() -> None:
    assert compass_refresh_contract.normalize_refresh_profile("") == "shell-safe"
    assert compass_refresh_contract.normalize_refresh_profile("bogus") == "shell-safe"
    assert compass_refresh_contract.normalize_refresh_profile("shell-safe") == "shell-safe"


def test_refresh_contract_keeps_shell_safe_provider_off_the_foreground_path() -> None:
    assert not compass_refresh_contract.allow_global_provider("shell-safe")
    assert not compass_refresh_contract.prefer_live_provider("shell-safe")


def test_scoped_provider_worker_limit_stays_bounded() -> None:
    assert compass_refresh_contract.scoped_provider_max_workers("shell-safe", scoped_packets=8) == 4
    assert compass_refresh_contract.scoped_provider_max_workers("shell-safe", scoped_packets=2) == 2
