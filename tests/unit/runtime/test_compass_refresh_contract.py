from __future__ import annotations

from odylith.runtime.surfaces import compass_refresh_contract


def test_normalize_refresh_profile_defaults_to_shell_safe() -> None:
    assert compass_refresh_contract.normalize_refresh_profile("") == "shell-safe"
    assert compass_refresh_contract.normalize_refresh_profile("bogus") == "shell-safe"


def test_full_refresh_contract_switches_live_provider_and_fallback_policy() -> None:
    assert compass_refresh_contract.full_refresh_requested("full")
    assert compass_refresh_contract.prefer_live_provider("full")
    assert not compass_refresh_contract.allow_stale_cache_recovery("full")
    assert not compass_refresh_contract.allow_deterministic_fallback("full")

    assert not compass_refresh_contract.full_refresh_requested("shell-safe")
    assert not compass_refresh_contract.prefer_live_provider("shell-safe")
    assert compass_refresh_contract.allow_stale_cache_recovery("shell-safe")
    assert compass_refresh_contract.allow_deterministic_fallback("shell-safe")


def test_scoped_provider_worker_limit_expands_only_for_full_refresh() -> None:
    assert compass_refresh_contract.scoped_provider_max_workers("shell-safe", scoped_packets=8) == 4
    assert compass_refresh_contract.scoped_provider_max_workers("full", scoped_packets=8) == 6
    assert compass_refresh_contract.scoped_provider_max_workers("full", scoped_packets=2) == 2


def test_brief_satisfies_full_refresh_accepts_clean_provider_and_cache_briefs() -> None:
    assert compass_refresh_contract.brief_satisfies_full_refresh({"status": "ready", "source": "provider"})
    assert compass_refresh_contract.brief_satisfies_full_refresh({"status": "ready", "source": "cache"})


def test_brief_satisfies_full_refresh_rejects_deterministic_or_noticed_briefs() -> None:
    assert not compass_refresh_contract.brief_satisfies_full_refresh(
        {"status": "ready", "source": "deterministic"}
    )
    assert not compass_refresh_contract.brief_satisfies_full_refresh(
        {
            "status": "ready",
            "source": "cache",
            "notice": {"reason": "provider_timeout"},
        }
    )
    assert not compass_refresh_contract.brief_satisfies_full_refresh({"status": "unavailable", "source": "provider"})
