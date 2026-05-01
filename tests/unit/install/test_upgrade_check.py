from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from odylith.install import upgrade_check


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_upgrade_check_reports_newer_release_and_writes_cache(tmp_path: Path) -> None:
    calls: list[object] = []

    def fake_urlopen(request, *, timeout):  # noqa: ANN001
        calls.append((request, timeout))
        return _Response(
            {
                "tag_name": "v1.2.4",
                "html_url": "https://github.com/odylith/odylith/releases/tag/v1.2.4",
                "published_at": "2026-04-30T12:00:00Z",
            }
        )

    result = upgrade_check.check_for_available_upgrade(
        repo_root=tmp_path,
        current_version="1.2.3",
        now=datetime(2026, 4, 30, 12, tzinfo=UTC),
        urlopen=fake_urlopen,
    )

    assert result.update_available is True
    assert result.latest_version == "1.2.4"
    assert result.status == "upgrade_available"
    assert len(calls) == 1
    assert upgrade_check.upgrade_check_state_path(repo_root=tmp_path).is_file()
    assert "Run `./.odylith/bin/odylith upgrade --repo-root .`" in "\n".join(
        upgrade_check.upgrade_check_lines(result, explicit=True)
    )


def test_upgrade_check_uses_fresh_cache_without_remote_ping(tmp_path: Path) -> None:
    checked_at = datetime(2026, 4, 30, 12, tzinfo=UTC)
    first = upgrade_check.check_for_available_upgrade(
        repo_root=tmp_path,
        current_version="1.2.3",
        now=checked_at,
        urlopen=lambda *args, **kwargs: _Response({"tag_name": "v1.2.4"}),
    )

    def blocked_urlopen(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("fresh upgrade cache should avoid a remote request")

    second = upgrade_check.check_for_available_upgrade(
        repo_root=tmp_path,
        current_version="1.2.3",
        now=checked_at + timedelta(hours=1),
        urlopen=blocked_urlopen,
    )

    assert first.update_available is True
    assert second.from_cache is True
    assert second.update_available is True
    assert second.latest_version == "1.2.4"


def test_upgrade_check_can_be_disabled_without_cache_write(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(upgrade_check.UPGRADE_CHECK_MODE_ENV, "off")

    def blocked_urlopen(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("disabled upgrade check should not query remote")

    result = upgrade_check.check_for_available_upgrade(
        repo_root=tmp_path,
        current_version="1.2.3",
        urlopen=blocked_urlopen,
    )

    assert result.disabled is True
    assert result.status == "disabled"
    assert not upgrade_check.upgrade_check_state_path(repo_root=tmp_path).exists()


def test_upgrade_check_records_blocked_remote_as_nonfatal(tmp_path: Path) -> None:
    def blocked_urlopen(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise TimeoutError("proxy filtered")

    result = upgrade_check.check_for_available_upgrade(
        repo_root=tmp_path,
        current_version="1.2.3",
        urlopen=blocked_urlopen,
    )

    assert result.status == "unavailable"
    assert result.update_available is False
    assert "TimeoutError" in result.error
    assert upgrade_check.upgrade_check_state_path(repo_root=tmp_path).is_file()
    assert "non-fatal" in "\n".join(upgrade_check.upgrade_check_lines(result, explicit=True))


def test_upgrade_check_offline_reads_cache_only(tmp_path: Path) -> None:
    upgrade_check.check_for_available_upgrade(
        repo_root=tmp_path,
        current_version="1.2.3",
        urlopen=lambda *args, **kwargs: _Response({"tag_name": "v1.2.4"}),
    )

    result = upgrade_check.check_for_available_upgrade(
        repo_root=tmp_path,
        current_version="1.2.3",
        offline=True,
        urlopen=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("offline should not ping")),
    )

    assert result.from_cache is True
    assert result.update_available is True
