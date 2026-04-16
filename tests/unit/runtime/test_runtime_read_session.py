from __future__ import annotations

from pathlib import Path

from odylith.runtime.common.cache_budget_policy import CacheBudgetPolicy
from odylith.runtime.common.cache_budget_policy import MemoryStats
from odylith.runtime.context_engine import runtime_read_session


def test_runtime_read_session_caches_builder_once(tmp_path: Path) -> None:
    policy = CacheBudgetPolicy(
        mode="normal",
        low_ram=False,
        memory=MemoryStats(total_bytes=16, available_bytes=8, source="test", detected=True),
        hot_path_budget_bytes=1024 * 1024,
        show_working_budget_bytes=1024 * 1024,
    )
    session = runtime_read_session.RuntimeReadSession(
        repo_root=tmp_path,
        requested_scope="reasoning",
        cache_policy=policy,
    )
    calls = {"count": 0}

    def _build() -> dict[str, str]:
        calls["count"] += 1
        return {"value": "cached"}

    first = session.get_or_compute(namespace="query", key="one", builder=_build)
    second = session.get_or_compute(namespace="query", key="one", builder=_build)

    assert first == {"value": "cached"}
    assert second == {"value": "cached"}
    assert calls["count"] == 1


def test_namespaced_cache_view_clears_only_its_namespace() -> None:
    left = runtime_read_session.shared_process_cache_view("left_test")
    right = runtime_read_session.shared_process_cache_view("right_test")
    left.clear()
    right.clear()

    left["one"] = ("a", 1)
    right["two"] = ("b", 2)
    left.clear()

    assert left.get("one") is None
    assert right["two"] == ("b", 2)
    right.clear()


def test_activate_runtime_read_session_clears_low_ram_session_cache(tmp_path: Path) -> None:
    policy = CacheBudgetPolicy(
        mode="low_ram",
        low_ram=True,
        memory=MemoryStats(total_bytes=4, available_bytes=1, source="test", detected=True),
        hot_path_budget_bytes=1024 * 1024,
        show_working_budget_bytes=1024 * 1024,
    )
    session = runtime_read_session.RuntimeReadSession(
        repo_root=tmp_path,
        requested_scope="reasoning",
        cache_policy=policy,
    )
    session.get_or_compute(namespace="query", key="one", builder=lambda: {"ok": True})
    assert len(session._cache) == 1  # noqa: SLF001
    session.clear()
    assert len(session._cache) == 0  # noqa: SLF001
