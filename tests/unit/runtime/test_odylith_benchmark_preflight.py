from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.evaluation import odylith_benchmark_runner as runner


def test_prime_benchmark_runtime_cache_requires_populated_guidance_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runner.store, "warm_projections", lambda **_: {"ok": True})
    monkeypatch.setattr(runner.store, "prime_reasoning_projection_cache", lambda **_: None)
    monkeypatch.setattr(
        runner.store.tooling_guidance_catalog,
        "load_guidance_catalog",
        lambda **_: {"chunk_count": 0, "source_doc_count": 0, "task_family_count": 0},
    )

    with pytest.raises(RuntimeError, match="populated guidance catalog"):
        runner._prime_benchmark_runtime_cache(repo_root=tmp_path)  # noqa: SLF001
