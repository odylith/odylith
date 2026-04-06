from __future__ import annotations

from odylith.runtime.context_engine import odylith_context_cache


def test_cache_path_bounds_long_keys_without_colliding(tmp_path):
    shared_prefix = "odylith/radar/source/ideas/" + ("shared-segment-" * 20)
    cache_a = odylith_context_cache.cache_path(
        repo_root=tmp_path,
        namespace="backlog/idea-specs",
        key=f"{shared_prefix}alpha.md",
    )
    cache_b = odylith_context_cache.cache_path(
        repo_root=tmp_path,
        namespace="backlog/idea-specs",
        key=f"{shared_prefix}beta.md",
    )

    assert cache_a.name.endswith(".json")
    assert cache_b.name.endswith(".json")
    assert len(cache_a.name) < 255
    assert len(cache_b.name) < 255
    assert cache_a.name != cache_b.name


def test_write_json_if_changed_accepts_long_absolute_lock_keys(tmp_path):
    repo_root = tmp_path / ("relocated-repo-segment-" * 8)
    repo_root.mkdir(parents=True, exist_ok=True)
    target = repo_root / ".odylith" / "cache" / "odylith-context-engine" / "probe.json"
    long_lock_key = str(
        (
            repo_root
            / ".odylith"
            / "cache"
            / "odylith-context-engine"
            / "backlog"
            / "idea-specs"
            / (("very-long-cache-token-" * 12) + "probe.json")
        ).resolve()
    )

    wrote = odylith_context_cache.write_json_if_changed(
        repo_root=repo_root,
        path=target,
        payload={"status": "ok"},
        lock_key=long_lock_key,
    )

    lock_files = list((repo_root / ".odylith" / "locks" / "odylith-context-engine").glob("*.lock"))
    assert wrote is True
    assert target.is_file()
    assert len(lock_files) == 1
    assert len(lock_files[0].name) < 255
