from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import tooling_context_retrieval as retrieval
from odylith.runtime.common.consumer_profile import write_consumer_profile


def test_prioritize_docs_prefers_registry_component_specs() -> None:
    docs = [
        "docs/architecture.md",
        "odylith/registry/source/components/compass/CURRENT_SPEC.md",
        "docs/runbooks/triage.md",
    ]

    prioritized = retrieval.prioritize_docs(
        docs,
        repo_root=Path.cwd(),
        selected_guidance_chunks=[],
        components=[],
        changed_paths=[],
    )

    assert prioritized[0] == "odylith/registry/source/components/compass/CURRENT_SPEC.md"


def test_prioritize_bootstrap_docs_prefers_registry_component_specs() -> None:
    docs = [
        "docs/overview.md",
        "odylith/registry/source/components/compass/CURRENT_SPEC.md",
        "docs/runbooks/triage.md",
    ]

    prioritized = retrieval.prioritize_bootstrap_docs(
        docs,
        repo_root=Path.cwd(),
        selected_guidance_chunks=[],
        components=[],
        changed_paths=[],
    )

    assert prioritized[0] == "odylith/registry/source/components/compass/CURRENT_SPEC.md"


def test_prioritize_docs_uses_custom_consumer_truth_roots(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    (repo_root / "consumer-registry" / "source" / "components" / "compass").mkdir(parents=True)
    (repo_root / "consumer-runbooks" / "platform").mkdir(parents=True)
    write_consumer_profile(
        repo_root=repo_root,
        payload={
            "truth_roots": {
                "component_specs": "consumer-registry/source/components",
                "runbooks": "consumer-runbooks/platform",
            }
        },
    )
    docs = [
        "docs/overview.md",
        "consumer-runbooks/platform/router.md",
        "consumer-registry/source/components/compass/CURRENT_SPEC.md",
    ]

    prioritized = retrieval.prioritize_docs(
        docs,
        repo_root=repo_root,
        selected_guidance_chunks=[],
        components=[],
        changed_paths=[],
    )

    assert prioritized[:2] == [
        "consumer-registry/source/components/compass/CURRENT_SPEC.md",
        "consumer-runbooks/platform/router.md",
    ]
