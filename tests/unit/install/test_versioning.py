from __future__ import annotations

from odylith.install.versioning import is_at_least, is_before, normalize_version, version_key


def test_normalize_version_accepts_plain_and_tagged_release_tokens() -> None:
    assert normalize_version("v0.1.12") == "0.1.12"
    assert normalize_version(" 0.1.12 ") == "0.1.12"


def test_version_key_orders_patch_numbers_and_suffixes() -> None:
    assert version_key("0.1.12") > version_key("0.1.9")
    assert version_key("0.1.12-rc1") > version_key("0.1.12")


def test_version_window_helpers_share_one_install_contract() -> None:
    assert is_at_least("v0.1.12", "0.1.11") is True
    assert is_before("0.1.10", "v0.1.11") is True
    assert is_before("", "0.1.11") is False
