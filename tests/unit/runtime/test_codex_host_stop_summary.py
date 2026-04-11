from __future__ import annotations

from odylith.runtime.surfaces import codex_host_stop_summary


def test_log_codex_stop_summary_logs_meaningful_updates(monkeypatch) -> None:
    seen: list[tuple[str, str, list[str] | None]] = []

    def _fake_run_compass_log(*, project_dir: str, summary: str, workstreams: list[str] | None = None) -> bool:
        seen.append((project_dir, summary, workstreams))
        return True

    monkeypatch.setattr(codex_host_stop_summary.codex_host_shared, "run_compass_log", _fake_run_compass_log)

    logged = codex_host_stop_summary.log_codex_stop_summary(
        ".",
        message="Implemented the Codex host dispatcher and validated the focused B-088 runtime tests.",
    )

    assert logged is True
    assert seen
    assert seen[0][0] == "."
    assert "B-088" in seen[0][1]
    assert seen[0][2] == ["B-088"]


def test_log_codex_stop_summary_ignores_non_meaningful_messages(monkeypatch) -> None:
    monkeypatch.setattr(
        codex_host_stop_summary.codex_host_shared,
        "run_compass_log",
        lambda **_: (_ for _ in ()).throw(AssertionError("should not log")),
    )

    assert codex_host_stop_summary.log_codex_stop_summary(".", message="Would you like a follow-up?") is False
