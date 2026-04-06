from __future__ import annotations

from pathlib import Path

from odylith.runtime.memory import odylith_remote_retrieval


def test_remote_config_marks_active_mode_without_base_url_as_misconfigured(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ODYLITH_VESPA_URL", raising=False)
    monkeypatch.setenv("ODYLITH_VESPA_MODE", "remote_only")

    config = odylith_remote_retrieval.remote_config(repo_root=tmp_path)

    assert config["enabled"] is False
    assert config["status"] == "misconfigured"
    assert "base_url_missing" in config["blocking_issues"]
    assert "ODYLITH_VESPA_URL" in config["action"]


def test_remote_config_recovers_invalid_timeout_without_disabling_ready_remote(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ODYLITH_VESPA_URL", "https://vespa.example.test")
    monkeypatch.setenv("ODYLITH_VESPA_MODE", "augment")
    monkeypatch.setenv("ODYLITH_VESPA_TIMEOUT_SECONDS", "abc")

    config = odylith_remote_retrieval.remote_config(repo_root=tmp_path)

    assert config["enabled"] is True
    assert config["status"] == "ready"
    assert config["timeout_seconds"] == 20.0
    assert "invalid_timeout_seconds" in config["issues"]


def test_sync_remote_reports_misconfigured_state_without_network(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ODYLITH_VESPA_URL", raising=False)
    monkeypatch.setenv("ODYLITH_VESPA_MODE", "augment")

    payload = odylith_remote_retrieval.sync_remote(
        repo_root=tmp_path,
        documents=[{"doc_key": "doc-1"}],
        dry_run=False,
    )

    assert payload["status"] == "misconfigured"
    assert payload["enabled"] is False
    assert payload["errors"] == ["base_url_missing"]


def test_sync_remote_closes_http_client_after_partial_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            raise RuntimeError("boom")

    class _FakeClient:
        def __init__(self) -> None:
            self.closed = False
            self.calls = 0

        def post(self, endpoint: str, json: dict[str, object]) -> _FakeResponse:  # noqa: A002
            _ = endpoint
            _ = json
            self.calls += 1
            return _FakeResponse()

        def delete(self, endpoint: str) -> _FakeResponse:
            _ = endpoint
            self.calls += 1
            return _FakeResponse()

        def close(self) -> None:
            self.closed = True

    client = _FakeClient()
    monkeypatch.setattr(
        odylith_remote_retrieval,
        "remote_config",
        lambda **_: {
            "provider": "vespa_http",
            "enabled": True,
            "configured": True,
            "status": "ready",
            "mode": "augment",
            "base_url": "https://vespa.example.test",
            "schema": "odylith_memory",
            "namespace": "odylith",
            "ranking_profile": "",
            "timeout_seconds": 20.0,
            "prune_missing": False,
            "issues": [],
            "blocking_issues": [],
            "action": "",
            "token": "",
            "cert_path": "",
            "key_path": "",
        },
    )
    monkeypatch.setattr(odylith_remote_retrieval.httpx, "Client", lambda **_: client)

    payload = odylith_remote_retrieval.sync_remote(
        repo_root=tmp_path,
        documents=[{"doc_key": "doc-1", "content": "body"}],
        dry_run=False,
    )

    assert payload["status"] == "partial_error"
    assert client.calls == 1
    assert client.closed is True
