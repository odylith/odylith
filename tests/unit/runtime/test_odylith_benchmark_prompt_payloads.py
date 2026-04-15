from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.evaluation import odylith_benchmark_prompt_payloads as prompt_payloads


def test_supplement_live_prompt_payload_adds_component_implementation_anchor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    implementation_path = repo_root / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router.py"
    implementation_path.parent.mkdir(parents=True, exist_ok=True)
    implementation_path.write_text("def route():\n    return None\n", encoding="utf-8")

    component_index = {
        "subagent-router": SimpleNamespace(
            component_id="subagent-router",
            path_prefixes=[
                "src/odylith/runtime/orchestration/subagent_router.py",
                "odylith/skills/odylith-subagent-router/SKILL.md",
            ],
        ),
        "odylith-chatter": SimpleNamespace(
            component_id="odylith-chatter",
            path_prefixes=[
                "AGENTS.md",
                "README.md",
                "docs/benchmarks/README.md",
                "docs/benchmarks/REVIEWER_GUIDE.md",
                "odylith/AGENTS.md",
                "odylith/skills/odylith-subagent-router/SKILL.md",
                "odylith/maintainer/AGENTS.md",
                "src/odylith/runtime/orchestration/subagent_router_runtime_policy.py",
            ],
        ),
    }

    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": component_index,
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={"family": "validation_heavy_fix", "intent": "implementation benchmark"},
        prompt_payload={"docs": ["odylith/registry/source/components/subagent-router/CURRENT_SPEC.md"]},
        packet_source="impact",
        changed_paths=["odylith/skills/odylith-subagent-router/SKILL.md"],
        full_payload={"components": [{"entity_id": "odylith-chatter"}, {"entity_id": "subagent-router"}]},
    )

    assert payload["implementation_anchors"] == ["src/odylith/runtime/orchestration/subagent_router.py"]
    assert payload["docs"] == ["odylith/registry/source/components/subagent-router/CURRENT_SPEC.md"]


def test_supplement_live_prompt_payload_suppresses_support_reads_for_strict_bounded_slice(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    implementation_path = repo_root / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router.py"
    implementation_path.parent.mkdir(parents=True, exist_ok=True)
    implementation_path.write_text("def route():\n    return None\n", encoding="utf-8")

    component_index = {
        "subagent-router": SimpleNamespace(
            component_id="subagent-router",
            path_prefixes=["src/odylith/runtime/orchestration/subagent_router.py"],
        ),
    }
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": component_index,
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "changed_paths": ["odylith/skills/odylith-subagent-router/SKILL.md"],
            "required_paths": ["odylith/skills/odylith-subagent-router/SKILL.md"],
            "acceptance_criteria": ["Keep the slice bounded to odylith/skills/odylith-subagent-router/SKILL.md."],
        },
        prompt_payload={},
        packet_source="impact",
        changed_paths=["odylith/skills/odylith-subagent-router/SKILL.md"],
        full_payload={"components": [{"entity_id": "subagent-router"}]},
    )

    assert payload["strict_boundary"] is True
    assert "implementation_anchors" not in payload
    assert "docs" not in payload


def test_supplement_live_prompt_payload_marks_exact_path_ambiguity_as_strict_boundary() -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=Path("/tmp"),
        scenario={
            "family": "exact_path_ambiguity",
            "changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
            "required_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
        },
        prompt_payload={
            "docs": ["odylith/runtime/README.md"],
            "context_packet": {
                "anchors": {"changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"]},
                "retrieval_plan": {"selected_docs": ["odylith/runtime/TRIBUNAL_AND_REMEDIATION.md"]},
            },
        },
        packet_source="session_brief",
        changed_paths=["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
        full_payload={},
    )

    assert payload["strict_boundary"] is True
    assert "docs" not in payload
    assert "relevant_docs" not in payload
    assert "implementation_anchors" not in payload
    assert payload["context_packet"]["anchors"]["changed_paths"] == ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"]
    assert "retrieval_plan" not in payload["context_packet"]


def test_supplement_live_prompt_payload_adds_architecture_component_anchors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    implementation_dir = repo_root / "src" / "odylith" / "runtime" / "context_engine"
    implementation_dir.mkdir(parents=True, exist_ok=True)
    (implementation_dir / "odylith_context_engine.py").write_text("def run():\n    return None\n", encoding="utf-8")
    spec_path = (
        repo_root
        / "odylith"
        / "registry"
        / "source"
        / "components"
        / "odylith-context-engine"
        / "CURRENT_SPEC.md"
    )
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# spec\n", encoding="utf-8")

    component_index = {
        "odylith-context-engine": SimpleNamespace(
            component_id="odylith-context-engine",
            path_prefixes=["src/odylith/runtime/context_engine"],
        ),
    }

    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": component_index,
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={"kind": "architecture"},
        prompt_payload={"architecture_audit": {"changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"]}},
        packet_source="architecture_dossier",
        changed_paths=["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
        full_payload={
            "topology_domains": [{"domain_id": "odylith-context-engine"}],
            "required_reads": ["docs/benchmarks/README.md"],
        },
    )

    audit = payload["architecture_audit"]
    assert audit["implementation_anchors"] == ["src/odylith/runtime/context_engine/odylith_context_engine.py"]
    assert audit["required_reads"][0] == "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md"


def test_supplement_live_prompt_payload_keeps_architecture_strict_boundary_without_support_reads() -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=Path("/tmp"),
        scenario={
            "changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
            "required_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
            "acceptance_criteria": ["Keep the slice bounded to odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md."],
        },
        prompt_payload={"architecture_audit": {"changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"]}},
        packet_source="architecture_dossier",
        changed_paths=["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
        full_payload={"topology_domains": [{"domain_id": "odylith-context-engine"}]},
    )

    audit = payload["architecture_audit"]
    assert audit["strict_boundary"] is True
    assert "implementation_anchors" not in audit
    assert "required_reads" not in audit


def test_supplement_live_prompt_payload_keeps_doc_only_architecture_reviews_free_of_code_anchor_widening(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    benchmark_runner = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py"
    benchmark_runner.parent.mkdir(parents=True, exist_ok=True)
    benchmark_runner.write_text("def run():\n    return None\n", encoding="utf-8")
    benchmark_spec = (
        repo_root / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md"
    )
    benchmark_spec.parent.mkdir(parents=True, exist_ok=True)
    benchmark_spec.write_text("# benchmark\n", encoding="utf-8")
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": {
            "benchmark": SimpleNamespace(
                component_id="benchmark",
                path_prefixes=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            )
        },
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "kind": "architecture",
            "required_paths": [
                "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "README.md",
                "odylith/MAINTAINER_RELEASE_RUNBOOK.md",
            ],
        },
        prompt_payload={"architecture_audit": {"changed_paths": ["odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd"]}},
        packet_source="architecture_dossier",
        changed_paths=["odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd"],
        full_payload={
            "topology_domains": [{"domain_id": "benchmark"}],
            "required_reads": ["docs/benchmarks/README.md"],
        },
    )

    audit = payload["architecture_audit"]
    assert "implementation_anchors" not in audit
    assert audit["required_reads"] == [
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        "odylith/MAINTAINER_RELEASE_RUNBOOK.md",
        "README.md",
    ]


def test_supplement_live_prompt_payload_keeps_governance_family_docs_and_code_anchors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    benchmark_runner = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py"
    benchmark_graphs = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_graphs.py"
    benchmark_runner.parent.mkdir(parents=True, exist_ok=True)
    benchmark_runner.write_text("def run():\n    return None\n", encoding="utf-8")
    benchmark_graphs.write_text("def render():\n    return None\n", encoding="utf-8")
    benchmark_spec = (
        repo_root / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md"
    )
    benchmark_spec.parent.mkdir(parents=True, exist_ok=True)
    benchmark_spec.write_text("# spec\n", encoding="utf-8")
    component_index = {
        "benchmark": SimpleNamespace(
            component_id="benchmark",
            path_prefixes=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        ),
    }
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": component_index,
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={"family": "release_publication", "intent": "benchmark publication closeout"},
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=["README.md"],
        full_payload={
            "components": [{"entity_id": "benchmark"}],
            "docs": [
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
            ],
        },
    )

    assert payload["docs"] == [
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
    ]
    assert payload["implementation_anchors"] == [
        "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
        "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
    ]


def test_release_publication_required_docs_keep_release_baseline_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    benchmark_runner = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py"
    benchmark_runner.parent.mkdir(parents=True, exist_ok=True)
    benchmark_runner.write_text("def run():\n    return None\n", encoding="utf-8")
    benchmark_spec = (
        repo_root / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md"
    )
    benchmark_spec.parent.mkdir(parents=True, exist_ok=True)
    benchmark_spec.write_text("# spec\n", encoding="utf-8")
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": {
            "benchmark": SimpleNamespace(
                component_id="benchmark",
                path_prefixes=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            )
        },
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "release_publication",
            "intent": "benchmark publication closeout",
            "required_paths": [
                "docs/benchmarks/README.md",
                "docs/benchmarks/METRICS_AND_PRIORITIES.md",
                "docs/benchmarks/REVIEWER_GUIDE.md",
                "docs/benchmarks/release-baselines.v1.json",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=["README.md"],
        full_payload={"components": [{"entity_id": "benchmark"}], "docs": []},
    )

    assert "docs/benchmarks/release-baselines.v1.json" in payload["docs"]
    assert payload["docs"][:4] == [
        "docs/benchmarks/release-baselines.v1.json",
        "docs/benchmarks/REVIEWER_GUIDE.md",
        "docs/benchmarks/METRICS_AND_PRIORITIES.md",
        "docs/benchmarks/README.md",
    ]
    assert "odylith/registry/source/components/benchmark/CURRENT_SPEC.md" in payload["docs"]


def test_install_runtime_component_scope_drops_unrelated_component_specs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    release_spec = repo_root / "odylith" / "registry" / "source" / "components" / "release" / "CURRENT_SPEC.md"
    context_engine_spec = (
        repo_root
        / "odylith"
        / "registry"
        / "source"
        / "components"
        / "odylith-context-engine"
        / "CURRENT_SPEC.md"
    )
    release_spec.parent.mkdir(parents=True, exist_ok=True)
    context_engine_spec.parent.mkdir(parents=True, exist_ok=True)
    release_spec.write_text("# release\n", encoding="utf-8")
    context_engine_spec.write_text("# context\n", encoding="utf-8")
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": {
            "release": SimpleNamespace(
                component_id="release",
                path_prefixes=["src/odylith/install/manager.py"],
            ),
            "odylith-context-engine": SimpleNamespace(
                component_id="odylith-context-engine",
                path_prefixes=["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            ),
        },
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "install_upgrade_runtime",
            "component": "release",
            "required_paths": [
                "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
                "odylith/registry/source/components/release/CURRENT_SPEC.md",
            ],
        },
        prompt_payload={
            "docs": [
                "odylith/registry/source/components/release/CURRENT_SPEC.md",
                "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
            ]
        },
        packet_source="impact",
        changed_paths=["src/odylith/install/manager.py"],
        full_payload={
            "components": [{"entity_id": "release"}, {"entity_id": "odylith-context-engine"}],
            "docs": [
                "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
                "odylith/registry/source/components/release/CURRENT_SPEC.md",
                "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
            ],
        },
    )

    assert payload["docs"] == [
        "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
        "odylith/registry/source/components/release/CURRENT_SPEC.md",
    ]


def test_supplement_live_prompt_payload_keeps_agents_guidance_docs_when_impact_report_surfaces_them(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    release_spec = repo_root / "odylith" / "registry" / "source" / "components" / "release" / "CURRENT_SPEC.md"
    release_spec.parent.mkdir(parents=True, exist_ok=True)
    release_spec.write_text("# release spec\n", encoding="utf-8")
    component_index = {
        "release": SimpleNamespace(
            component_id="release",
            path_prefixes=[
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
            ],
        ),
    }

    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": component_index,
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={"family": "release_publication", "intent": "benchmark publication closeout"},
        prompt_payload={},
        packet_source="impact",
        changed_paths=["README.md"],
        full_payload={
            "components": [{"entity_id": "release"}],
            "docs": [
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                "odylith/registry/source/components/release/CURRENT_SPEC.md",
            ],
        },
    )

    assert set(payload["docs"]) == {
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
        "odylith/registry/source/components/release/CURRENT_SPEC.md",
    }


def test_browser_surface_reliability_treats_html_as_read_only_supporting_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    render_path = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "render_tooling_dashboard.py"
    onboarding_path = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "shell_onboarding.py"
    render_path.parent.mkdir(parents=True, exist_ok=True)
    render_path.write_text("def render():\n    return None\n", encoding="utf-8")
    onboarding_path.write_text("def onboarding():\n    return None\n", encoding="utf-8")
    dashboard_spec = (
        repo_root / "odylith" / "registry" / "source" / "components" / "dashboard" / "CURRENT_SPEC.md"
    )
    dashboard_spec.parent.mkdir(parents=True, exist_ok=True)
    dashboard_spec.write_text("# dashboard\n", encoding="utf-8")
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": {
            "dashboard": SimpleNamespace(
                component_id="dashboard",
                path_prefixes=["src/odylith/runtime/surfaces/render_tooling_dashboard.py"],
            )
        },
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "browser_surface_reliability",
            "component": "dashboard",
            "required_paths": [
                "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                "src/odylith/runtime/surfaces/shell_onboarding.py",
                "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
                "odylith/index.html",
            ],
        },
        prompt_payload={"docs": ["odylith/index.html", "odylith/compass/compass.html"]},
        packet_source="impact",
        changed_paths=[
            "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
            "src/odylith/runtime/surfaces/shell_onboarding.py",
            "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
        ],
        full_payload={
            "components": [{"entity_id": "dashboard"}],
            "docs": [
                "odylith/index.html",
                "odylith/compass/compass.html",
                "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
            ],
        },
    )

    assert payload["strict_boundary"] is True
    assert "docs" not in payload
    assert "implementation_anchors" not in payload
    assert payload["context_packet"]["anchors"]["explicit_paths"] == ["odylith/index.html"]
    assert any("rendered read surfaces" in hint for hint in payload["boundary_hints"])
    assert any("real rendered shell path" in hint.lower() for hint in payload["boundary_hints"])
    assert any("shared helper" in hint.lower() for hint in payload["boundary_hints"])
    assert any("benchmark runner, prompt, or evaluation sources" in hint for hint in payload["boundary_hints"])
    assert any("reopen-pill" in hint for hint in payload["boundary_hints"])


def test_browser_surface_reliability_uses_strict_boundary_for_rendered_html_only_residuals(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    render_path = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "render_tooling_dashboard.py"
    compass_shell = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "render_compass_shell.py"
    browser_test = repo_root / "tests" / "integration" / "runtime" / "test_surface_browser_smoke.py"
    render_path.parent.mkdir(parents=True, exist_ok=True)
    compass_shell.parent.mkdir(parents=True, exist_ok=True)
    browser_test.parent.mkdir(parents=True, exist_ok=True)
    render_path.write_text("def render():\n    return None\n", encoding="utf-8")
    compass_shell.write_text("def render_compass():\n    return None\n", encoding="utf-8")
    browser_test.write_text("def test_browser():\n    assert True\n", encoding="utf-8")
    dashboard_spec = (
        repo_root / "odylith" / "registry" / "source" / "components" / "dashboard" / "CURRENT_SPEC.md"
    )
    dashboard_spec.parent.mkdir(parents=True, exist_ok=True)
    dashboard_spec.write_text("# dashboard\n", encoding="utf-8")
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": {
            "dashboard": SimpleNamespace(
                component_id="dashboard",
                path_prefixes=[
                    "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                    "src/odylith/runtime/surfaces/render_compass_shell.py",
                ],
            )
        },
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "browser_surface_reliability",
            "component": "dashboard",
            "required_paths": [
                "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                "src/odylith/runtime/surfaces/render_compass_shell.py",
                "tests/integration/runtime/test_surface_browser_smoke.py",
                "odylith/index.html",
                "odylith/compass/compass.html",
            ],
        },
        prompt_payload={
            "docs": [
                "odylith/index.html",
                "odylith/compass/compass.html",
                "odylith/runtime/README.md",
            ],
            "context_packet": {
                "anchors": {
                    "changed_paths": [
                        "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                        "src/odylith/runtime/surfaces/render_compass_shell.py",
                    ]
                },
                "retrieval_plan": {"selected_docs": ["odylith/runtime/README.md"]},
            },
        },
        packet_source="impact",
        changed_paths=[
            "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
            "src/odylith/runtime/surfaces/render_compass_shell.py",
            "tests/integration/runtime/test_surface_browser_smoke.py",
        ],
        full_payload={
            "components": [{"entity_id": "dashboard"}],
            "docs": [
                "odylith/index.html",
                "odylith/compass/compass.html",
                "odylith/runtime/README.md",
            ],
        },
    )

    assert payload["strict_boundary"] is True
    assert "docs" not in payload
    assert "implementation_anchors" not in payload
    assert "boundary_hints" in payload
    assert payload["context_packet"]["anchors"]["changed_paths"] == [
        "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
        "src/odylith/runtime/surfaces/render_compass_shell.py",
    ]
    assert payload["context_packet"]["anchors"]["explicit_paths"] == [
        "odylith/index.html",
        "odylith/compass/compass.html",
    ]
    assert "retrieval_plan" not in payload["context_packet"]


def test_browser_surface_reliability_filters_non_required_retrieval_docs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    dashboard_spec = (
        repo_root / "odylith" / "registry" / "source" / "components" / "dashboard" / "CURRENT_SPEC.md"
    )
    dashboard_spec.parent.mkdir(parents=True, exist_ok=True)
    dashboard_spec.write_text("# dashboard\n", encoding="utf-8")
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": {
            "dashboard": SimpleNamespace(
                component_id="dashboard",
                path_prefixes=["src/odylith/runtime/surfaces/render_tooling_dashboard.py"],
            )
        },
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "browser_surface_reliability",
            "component": "dashboard",
            "required_paths": [
                "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                "src/odylith/runtime/surfaces/shell_onboarding.py",
                "src/odylith/cli.py",
                "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
                "tests/unit/runtime/test_render_tooling_dashboard.py",
                "odylith/index.html",
            ],
        },
        prompt_payload={
            "docs": ["odylith/index.html", "odylith/registry/source/components/dashboard/CURRENT_SPEC.md"],
            "context_packet": {
                "retrieval_plan": {
                    "selected_docs": [
                        "odylith/index.html",
                        "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
                    ]
                }
            },
        },
        packet_source="impact",
        changed_paths=[
            "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
            "src/odylith/runtime/surfaces/shell_onboarding.py",
            "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
        ],
        full_payload={
            "components": [{"entity_id": "dashboard"}],
            "docs": [
                "odylith/index.html",
                "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
            ],
        },
    )

    assert payload["strict_boundary"] is True
    assert "docs" not in payload
    assert "implementation_anchors" not in payload
    assert payload["context_packet"]["anchors"]["explicit_paths"] == [
        "src/odylith/cli.py",
        "tests/unit/runtime/test_render_tooling_dashboard.py",
        "odylith/index.html",
    ]
    assert "retrieval_plan" not in payload["context_packet"]
    assert any("Ignore unrelated dirty worktree changes" in hint for hint in payload["boundary_hints"])
    assert any(
        "install-state persistence and upgrade spotlight storage under `src/odylith/install/`" in hint
        for hint in payload["boundary_hints"]
    )


def test_merge_heavy_change_adds_bounded_noop_closeout_boundary_hint(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "merge_heavy_change",
            "allow_noop_completion": True,
            "required_paths": [
                "odylith/skills/odylith-subagent-router/SKILL.md",
                "odylith/runtime/SUBAGENT_OPERATIONS.md",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[
            "odylith/skills/odylith-subagent-router/SKILL.md",
            "odylith/runtime/SUBAGENT_OPERATIONS.md",
        ],
        full_payload={},
    )

    assert any("close successfully with no file changes" in hint for hint in payload["boundary_hints"])
    assert any("not a blocker for this bounded closeout" in hint for hint in payload["boundary_hints"])


def test_merge_heavy_change_keeps_changed_docs_in_focus_payload(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "merge_heavy_change",
            "allow_noop_completion": True,
            "required_paths": [
                "odylith/skills/odylith-subagent-router/SKILL.md",
                "odylith/runtime/SUBAGENT_OPERATIONS.md",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[
            "odylith/skills/odylith-subagent-router/SKILL.md",
            "odylith/runtime/SUBAGENT_OPERATIONS.md",
        ],
        full_payload={},
    )

    assert payload["docs"] == [
        "odylith/skills/odylith-subagent-router/SKILL.md",
        "odylith/runtime/SUBAGENT_OPERATIONS.md",
    ]
    assert payload["context_packet"]["anchors"]["explicit_paths"] == [
        "odylith/skills/odylith-subagent-router/SKILL.md",
        "odylith/runtime/SUBAGENT_OPERATIONS.md",
    ]


def test_cross_file_feature_strict_slice_keeps_all_bounded_skill_anchors(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "cross_file_feature",
            "changed_paths": [
                "odylith/skills/odylith-subagent-router/SKILL.md",
                "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
            ],
            "required_paths": [
                "odylith/skills/odylith-subagent-router/SKILL.md",
                "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
            ],
        },
        prompt_payload={
            "context_packet": {
                "anchors": {
                    "explicit_paths": [
                        "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
                    ]
                }
            }
        },
        packet_source="governance_slice",
        changed_paths=[
            "odylith/skills/odylith-subagent-router/SKILL.md",
            "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
        ],
        full_payload={},
    )

    assert payload["strict_boundary"] is True
    assert set(payload["context_packet"]["anchors"]["explicit_paths"]) == {
        "odylith/skills/odylith-subagent-router/SKILL.md",
        "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
    }
    assert any("narrow anchored orchestration slices" in hint for hint in payload["boundary_hints"])


def test_validation_heavy_fix_strict_slice_keeps_boundary_hints(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "validation_heavy_fix",
            "changed_paths": [
                "odylith/skills/odylith-subagent-router/SKILL.md",
                "odylith/runtime/SUBAGENT_OPERATIONS.md",
            ],
            "required_paths": [
                "odylith/skills/odylith-subagent-router/SKILL.md",
                "odylith/runtime/SUBAGENT_OPERATIONS.md",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[
            "odylith/skills/odylith-subagent-router/SKILL.md",
            "odylith/runtime/SUBAGENT_OPERATIONS.md",
        ],
        full_payload={},
    )

    assert payload["strict_boundary"] is True
    assert payload["context_packet"]["anchors"]["explicit_paths"] == [
        "odylith/skills/odylith-subagent-router/SKILL.md",
        "odylith/runtime/SUBAGENT_OPERATIONS.md",
    ]
    assert any("keep writable changes on the listed runtime and test anchors" in hint for hint in payload["boundary_hints"])


def test_component_governance_adds_catalog_sync_boundary_hint(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "component_governance",
            "required_paths": [
                "odylith/registry/source/component_registry.v1.json",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
                "odylith/atlas/source/catalog/diagrams.v1.json",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[
            "odylith/registry/source/component_registry.v1.json",
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
        ],
        full_payload={},
    )

    assert any("paired Atlas catalog or index artifacts synchronized" in hint for hint in payload["boundary_hints"])
    assert any("catalog or index artifact still needs the matching change" in hint for hint in payload["boundary_hints"])
    assert any("do not leave them as read-only support context" in hint for hint in payload["boundary_hints"])


def test_cross_surface_governance_sync_adds_preexisting_drift_closeout_boundary_hint(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "cross_surface_governance_sync",
            "required_paths": [
                "src/odylith/runtime/governance/sync_workstream_artifacts.py",
                "odylith/radar/source/INDEX.md",
                "odylith/technical-plans/INDEX.md",
                "odylith/atlas/source/catalog/diagrams.v1.json",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[
            "src/odylith/runtime/governance/sync_workstream_artifacts.py",
            "odylith/radar/source/INDEX.md",
            "odylith/technical-plans/INDEX.md",
        ],
        full_payload={},
    )

    assert any("focused sync validator passes" in hint for hint in payload["boundary_hints"])
    assert any("pre-existing repo drift" in hint for hint in payload["boundary_hints"])
    assert any("rendered Radar or Compass HTML" in hint for hint in payload["boundary_hints"])


def test_component_governance_keeps_atlas_catalog_json_as_live_support_doc(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    benchmark_runner = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py"
    benchmark_graphs = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_graphs.py"
    benchmark_runner.parent.mkdir(parents=True, exist_ok=True)
    benchmark_runner.write_text("def run():\n    return None\n", encoding="utf-8")
    benchmark_graphs.write_text("def render():\n    return None\n", encoding="utf-8")
    atlas_catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    atlas_catalog.parent.mkdir(parents=True, exist_ok=True)
    atlas_catalog.write_text("{}\n", encoding="utf-8")
    benchmark_spec = repo_root / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md"
    benchmark_spec.parent.mkdir(parents=True, exist_ok=True)
    benchmark_spec.write_text("# benchmark\n", encoding="utf-8")
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": {
            "benchmark": SimpleNamespace(
                component_id="benchmark",
                path_prefixes=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            )
        },
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "component_governance",
            "component": "benchmark",
            "required_paths": [
                "odylith/registry/source/component_registry.v1.json",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
                "odylith/atlas/source/catalog/diagrams.v1.json",
                "tests/unit/runtime/test_validate_component_registry_contract.py",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[
            "odylith/registry/source/component_registry.v1.json",
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
        ],
        full_payload={
            "components": [{"entity_id": "benchmark"}],
            "docs": ["odylith/atlas/source/catalog/diagrams.v1.json"],
        },
    )

    assert payload["docs"][0] == "odylith/atlas/source/catalog/diagrams.v1.json"


def test_cross_surface_governance_sync_drops_broad_hygiene_test_from_first_pass_anchors(tmp_path: Path) -> None:
    repo_root = tmp_path
    corpus_path = repo_root / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
    corpus_mirror = repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
    corpus_test = repo_root / "tests" / "unit" / "runtime" / "test_odylith_benchmark_corpus.py"
    hygiene_test = repo_root / "tests" / "unit" / "runtime" / "test_hygiene.py"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_mirror.parent.mkdir(parents=True, exist_ok=True)
    corpus_test.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text("{}\n", encoding="utf-8")
    corpus_mirror.write_text("{}\n", encoding="utf-8")
    corpus_test.write_text("def test_corpus():\n    assert True\n", encoding="utf-8")
    hygiene_test.write_text("def test_hygiene():\n    assert True\n", encoding="utf-8")

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "cross_surface_governance_sync",
            "required_paths": [
                "odylith/runtime/source/optimization-evaluation-corpus.v1.json",
                "src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json",
                "tests/unit/runtime/test_odylith_benchmark_corpus.py",
                "tests/unit/runtime/test_hygiene.py",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[
            "odylith/runtime/source/optimization-evaluation-corpus.v1.json",
            "src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json",
            "tests/unit/runtime/test_odylith_benchmark_corpus.py",
        ],
        full_payload={
            "components": [],
            "docs": [
                "tests/unit/runtime/test_odylith_benchmark_corpus.py",
                "tests/unit/runtime/test_hygiene.py",
            ],
        },
    )

    assert "tests/unit/runtime/test_odylith_benchmark_corpus.py" in payload["implementation_anchors"]
    assert "tests/unit/runtime/test_hygiene.py" not in payload["implementation_anchors"]


def test_cross_surface_governance_sync_prioritizes_catalog_before_idea_doc(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "cross_surface_governance_sync",
            "required_paths": [
                "src/odylith/runtime/governance/sync_workstream_artifacts.py",
                "odylith/radar/source/INDEX.md",
                "odylith/technical-plans/INDEX.md",
                "odylith/atlas/source/catalog/diagrams.v1.json",
                "odylith/registry/source/component_registry.v1.json",
                "odylith/radar/source/ideas/2026-03/2026-03-29-odylith-complex-repo-benchmark-corpus-expansion-and-frontier-improvement.md",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[],
        full_payload={},
    )

    assert payload["docs"][:4] == [
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "odylith/registry/source/component_registry.v1.json",
        "odylith/radar/source/INDEX.md",
        "odylith/technical-plans/INDEX.md",
    ]
    assert payload["context_packet"]["anchors"]["explicit_paths"] == [
        "odylith/radar/source/INDEX.md",
        "odylith/technical-plans/INDEX.md",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "odylith/registry/source/component_registry.v1.json",
        "odylith/radar/source/ideas/2026-03/2026-03-29-odylith-complex-repo-benchmark-corpus-expansion-and-frontier-improvement.md",
    ]


def test_browser_surface_reliability_prefers_renderer_anchor_before_cli_when_required_paths_are_ordered(
    tmp_path: Path,
) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "browser_surface_reliability",
            "required_paths": [
                "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                "src/odylith/runtime/surfaces/shell_onboarding.py",
                "src/odylith/cli.py",
                "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
                "tests/unit/runtime/test_render_tooling_dashboard.py",
                "odylith/index.html",
            ],
        },
        prompt_payload={},
        packet_source="impact",
        changed_paths=[],
        full_payload={},
    )

    assert payload["implementation_anchors"][:3] == [
        "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
        "src/odylith/runtime/surfaces/shell_onboarding.py",
        "src/odylith/cli.py",
    ]
    assert payload["implementation_anchors"][3] == "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py"


def test_browser_surface_reliability_avoids_component_spec_support_doc_noise(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    dashboard_spec = (
        repo_root / "odylith" / "registry" / "source" / "components" / "dashboard" / "CURRENT_SPEC.md"
    )
    dashboard_spec.parent.mkdir(parents=True, exist_ok=True)
    dashboard_spec.write_text("# dashboard\n", encoding="utf-8")
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": {
            "dashboard": SimpleNamespace(
                component_id="dashboard",
                path_prefixes=[
                    "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                ],
            )
        },
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "browser_surface_reliability",
            "component": "dashboard",
            "required_paths": [
                "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                "src/odylith/runtime/surfaces/shell_onboarding.py",
                "src/odylith/cli.py",
                "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
                "tests/unit/runtime/test_render_tooling_dashboard.py",
                "odylith/index.html",
            ],
        },
        prompt_payload={},
        packet_source="impact",
        changed_paths=[],
        full_payload={},
    )

    assert payload["docs"] == ["odylith/index.html"]
    assert any("fake sync or dashboard-refresh hooks" in hint for hint in payload["boundary_hints"])


def test_release_publication_support_docs_prioritize_baselines_specs_and_readmes(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "release_publication",
            "required_paths": [
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
                "README.md",
                "docs/benchmarks/README.md",
                "docs/benchmarks/METRICS_AND_PRIORITIES.md",
                "docs/benchmarks/REVIEWER_GUIDE.md",
                "docs/benchmarks/release-baselines.v1.json",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                "odylith/MAINTAINER_RELEASE_RUNBOOK.md",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[],
        full_payload={},
    )

    assert payload["docs"] == [
        "docs/benchmarks/release-baselines.v1.json",
        "docs/benchmarks/REVIEWER_GUIDE.md",
        "docs/benchmarks/METRICS_AND_PRIORITIES.md",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        "docs/benchmarks/README.md",
    ]
    assert any("generated SVGs as validator-produced outputs" in hint for hint in payload["boundary_hints"])
    assert any("rendered shell pages" in hint for hint in payload["boundary_hints"])
    assert payload["context_packet"]["anchors"]["explicit_paths"] == [
        "README.md",
        "docs/benchmarks/README.md",
        "docs/benchmarks/METRICS_AND_PRIORITIES.md",
        "docs/benchmarks/REVIEWER_GUIDE.md",
        "docs/benchmarks/release-baselines.v1.json",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
        "odylith/MAINTAINER_RELEASE_RUNBOOK.md",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
    ]


def test_release_publication_keeps_changed_doc_boundary_in_focus_payload(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "release_publication",
            "required_paths": [
                "README.md",
                "docs/benchmarks/README.md",
                "docs/benchmarks/REVIEWER_GUIDE.md",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                "odylith/maintainer/skills/release-benchmark-publishing/SKILL.md",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=[
            "README.md",
            "docs/benchmarks/README.md",
            "docs/benchmarks/REVIEWER_GUIDE.md",
            "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            "odylith/maintainer/skills/release-benchmark-publishing/SKILL.md",
        ],
        full_payload={},
    )

    assert payload["docs"] == [
        "README.md",
        "docs/benchmarks/README.md",
        "docs/benchmarks/REVIEWER_GUIDE.md",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
        "odylith/maintainer/skills/release-benchmark-publishing/SKILL.md",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
    ]
    assert payload["context_packet"]["anchors"]["explicit_paths"] == [
        "README.md",
        "docs/benchmarks/README.md",
        "docs/benchmarks/REVIEWER_GUIDE.md",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
        "odylith/maintainer/skills/release-benchmark-publishing/SKILL.md",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
    ]


def test_curated_docs_drop_packet_selected_docs_from_focus_payload(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "release_publication",
            "required_paths": [
                "docs/benchmarks/README.md",
                "docs/benchmarks/REVIEWER_GUIDE.md",
                "docs/benchmarks/release-baselines.v1.json",
            ],
        },
        prompt_payload={
            "docs": ["docs/benchmarks/README.md"],
            "context_packet": {
                "retrieval_plan": {
                    "selected_docs": [
                        "odylith/radar/radar.html",
                        "docs/benchmarks/REVIEWER_GUIDE.md",
                    ]
                }
            },
        },
        packet_source="governance_slice",
        changed_paths=[],
        full_payload={},
    )

    assert payload["docs"][0] == "docs/benchmarks/release-baselines.v1.json"
    assert "selected_docs" not in payload["context_packet"].get("retrieval_plan", {})


def test_docs_closeout_adds_explicit_docs_boundary_hint(tmp_path: Path) -> None:
    repo_root = tmp_path
    benchmark_graphs = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_graphs.py"
    benchmark_graphs.parent.mkdir(parents=True, exist_ok=True)
    benchmark_graphs.write_text("def render():\n    return None\n", encoding="utf-8")

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "docs_code_closeout",
            "required_paths": [
                "README.md",
                "docs/benchmarks/README.md",
                "docs/benchmarks/REVIEWER_GUIDE.md",
                "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
            ],
        },
        prompt_payload={},
        packet_source="governance_slice",
        changed_paths=["README.md", "docs/benchmarks/README.md", "docs/benchmarks/REVIEWER_GUIDE.md"],
        full_payload={
            "docs": [
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            ]
        },
    )

    assert any("keep writes on the listed README/docs surfaces" in hint for hint in payload["boundary_hints"])


def test_validation_heavy_fix_keeps_docs_read_only_and_runner_bounded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    benchmark_runner = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py"
    benchmark_tests = repo_root / "tests" / "unit" / "runtime" / "test_odylith_benchmark_runner.py"
    benchmark_runner.parent.mkdir(parents=True, exist_ok=True)
    benchmark_tests.parent.mkdir(parents=True, exist_ok=True)
    benchmark_runner.write_text("def run():\n    return None\n", encoding="utf-8")
    benchmark_tests.write_text("def test_runner():\n    assert True\n", encoding="utf-8")
    benchmark_spec = (
        repo_root / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md"
    )
    benchmark_spec.parent.mkdir(parents=True, exist_ok=True)
    benchmark_spec.write_text("# benchmark\n", encoding="utf-8")
    monkeypatch.setattr(
        prompt_payloads.store,
        "load_component_index",
        lambda repo_root, runtime_mode="local": {
            "benchmark": SimpleNamespace(
                component_id="benchmark",
                path_prefixes=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            )
        },
    )

    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=repo_root,
        scenario={
            "family": "validation_heavy_fix",
            "component": "benchmark",
            "required_paths": [
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                "tests/unit/runtime/test_odylith_benchmark_runner.py",
                "docs/benchmarks/REVIEWER_GUIDE.md",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            ],
        },
        prompt_payload={},
        packet_source="impact",
        changed_paths=[
            "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
            "tests/unit/runtime/test_odylith_benchmark_runner.py",
        ],
        full_payload={
            "components": [{"entity_id": "benchmark"}],
            "docs": [
                "docs/benchmarks/REVIEWER_GUIDE.md",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "README.md",
            ],
        },
    )

    assert any("keep writable changes on the listed runtime and test anchors" in hint for hint in payload["boundary_hints"])
    assert any("Do not rewrite benchmark expectation literals" in hint for hint in payload["boundary_hints"])
