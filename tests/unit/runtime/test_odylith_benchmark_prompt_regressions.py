from __future__ import annotations

from pathlib import Path

from odylith.runtime.evaluation import odylith_benchmark_prompt_payloads as prompt_payloads


def test_consumer_profile_prompt_payload_stays_on_named_specs_and_agents_surface(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "consumer_profile_compatibility",
            "allow_noop_completion": True,
            "required_paths": [
                "src/odylith/runtime/common/consumer_profile.py",
                "tests/unit/runtime/test_consumer_profile.py",
                "odylith/AGENTS.md",
                "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
                "odylith/registry/source/components/registry/CURRENT_SPEC.md",
            ],
        },
        prompt_payload={
            "context_packet": {
                "retrieval_plan": {
                    "selected_docs": [
                        "odylith/registry/source/component_registry.v1.json",
                        "odylith/registry/source/components/registry/CURRENT_SPEC.md",
                    ]
                }
            }
        },
        packet_source="impact",
        changed_paths=[
            "src/odylith/runtime/common/consumer_profile.py",
            "tests/unit/runtime/test_consumer_profile.py",
        ],
        full_payload={
            "docs": [
                "odylith/registry/source/component_registry.v1.json",
                "odylith/AGENTS.md",
                "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
                "odylith/registry/source/components/registry/CURRENT_SPEC.md",
            ]
        },
    )

    assert payload["docs"] == [
        "odylith/AGENTS.md",
        "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
        "odylith/registry/source/components/registry/CURRENT_SPEC.md",
    ]
    retrieval_plan = payload.get("context_packet", {}).get("retrieval_plan", {})
    assert "selected_docs" not in retrieval_plan
    assert any("component inventory" in hint for hint in payload["boundary_hints"])
    assert any("stop with no file changes" in hint for hint in payload["boundary_hints"])


def test_governed_surface_sync_prompt_payload_stays_on_named_governed_surfaces(tmp_path: Path) -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=tmp_path,
        scenario={
            "family": "governed_surface_sync",
            "allow_noop_completion": True,
            "required_paths": [
                "odylith/surfaces/GOVERNANCE_SURFACES.md",
                "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
                "odylith/radar/source/INDEX.md",
            ],
        },
        prompt_payload={
            "context_packet": {
                "retrieval_plan": {
                    "selected_docs": [
                        "odylith/registry/source/component_registry.v1.json",
                        "odylith/surfaces/GOVERNANCE_SURFACES.md",
                    ]
                }
            }
        },
        packet_source="governance_slice",
        changed_paths=[
            "odylith/surfaces/GOVERNANCE_SURFACES.md",
            "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
            "odylith/radar/source/INDEX.md",
        ],
        full_payload={
            "docs": [
                "odylith/registry/source/component_registry.v1.json",
                "odylith/surfaces/GOVERNANCE_SURFACES.md",
                "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
                "odylith/radar/source/INDEX.md",
            ]
        },
    )

    assert payload["docs"] == [
        "odylith/surfaces/GOVERNANCE_SURFACES.md",
        "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
        "odylith/radar/source/INDEX.md",
    ]
    retrieval_plan = payload.get("context_packet", {}).get("retrieval_plan", {})
    assert "selected_docs" not in retrieval_plan
    assert any("governance surface docs and the named Radar index only" in hint for hint in payload["boundary_hints"])
    assert any("stop with no file changes" in hint for hint in payload["boundary_hints"])


def test_compass_prompt_payload_is_stable_across_doc_orderings() -> None:
    scenario = {
        "family": "compass_brief_freshness",
        "allow_noop_completion": True,
        "required_paths": [
            "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
            "src/odylith/runtime/surfaces/compass_standup_brief_narrator.py",
            "tests/unit/runtime/test_compass_dashboard_runtime.py",
            "odylith/registry/source/components/compass/CURRENT_SPEC.md",
            "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
        ],
    }
    prompt_payload = {
        "context_packet": {
            "retrieval_plan": {
                "selected_docs": [
                    "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
                    "odylith/registry/source/components/compass/CURRENT_SPEC.md",
                ]
            }
        }
    }
    forward = prompt_payloads.supplement_live_prompt_payload(
        repo_root=Path("/tmp"),
        scenario=scenario,
        prompt_payload=prompt_payload,
        packet_source="impact",
        changed_paths=[
            "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
            "src/odylith/runtime/surfaces/compass_standup_brief_narrator.py",
            "tests/unit/runtime/test_compass_dashboard_runtime.py",
        ],
        full_payload={
            "docs": [
                "odylith/registry/source/components/compass/CURRENT_SPEC.md",
                "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
                "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
            ]
        },
    )
    reverse = prompt_payloads.supplement_live_prompt_payload(
        repo_root=Path("/tmp"),
        scenario=scenario,
        prompt_payload=prompt_payload,
        packet_source="impact",
        changed_paths=[
            "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
            "src/odylith/runtime/surfaces/compass_standup_brief_narrator.py",
            "tests/unit/runtime/test_compass_dashboard_runtime.py",
        ],
        full_payload={
            "docs": [
                "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
                "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
                "odylith/registry/source/components/compass/CURRENT_SPEC.md",
            ]
        },
    )

    assert forward == reverse
    assert forward["docs"] == [
        "odylith/registry/source/components/compass/CURRENT_SPEC.md",
        "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
    ]
    retrieval_plan = forward.get("context_packet", {}).get("retrieval_plan", {})
    assert "selected_docs" not in retrieval_plan
    assert any("stop with no file changes" in hint for hint in forward["boundary_hints"])


def test_explicit_workstream_prompt_payload_does_not_expand_beyond_required_skill() -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=Path("/tmp"),
        scenario={
            "family": "explicit_workstream",
            "required_paths": ["odylith/skills/odylith-subagent-orchestrator/SKILL.md"],
        },
        prompt_payload={
            "context_packet": {
                "retrieval_plan": {
                    "selected_docs": [
                        "odylith/runtime/TRIBUNAL_AND_REMEDIATION.md",
                        "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
                    ]
                }
            }
        },
        packet_source="governance_slice",
        changed_paths=[],
        full_payload={
            "docs": [
                "odylith/runtime/TRIBUNAL_AND_REMEDIATION.md",
                "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            ]
        },
    )

    assert payload["docs"] == ["odylith/skills/odylith-subagent-orchestrator/SKILL.md"]
    assert payload["context_packet"]["anchors"]["explicit_paths"] == ["odylith/skills/odylith-subagent-orchestrator/SKILL.md"]
    retrieval_plan = payload.get("context_packet", {}).get("retrieval_plan", {})
    assert "selected_docs" not in retrieval_plan
    assert any("listed skills" in hint for hint in payload["boundary_hints"])


def test_daemon_security_prompt_payload_prefers_noop_when_validator_already_passes() -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=Path("/tmp"),
        scenario={
            "family": "daemon_security",
            "allow_noop_completion": True,
            "required_paths": [
                "src/odylith/runtime/context_engine/odylith_context_engine.py",
                "src/odylith/install/repair.py",
                "tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py",
                "odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md",
                "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
            ],
        },
        prompt_payload={
            "context_packet": {
                "retrieval_plan": {
                    "selected_docs": [
                        "odylith/registry/source/component_registry.v1.json",
                        "odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md",
                    ]
                }
            }
        },
        packet_source="governance_slice",
        changed_paths=[
            "src/odylith/runtime/context_engine/odylith_context_engine.py",
            "src/odylith/install/repair.py",
            "tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py",
        ],
        full_payload={
            "docs": [
                "odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md",
                "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
                "odylith/registry/source/component_registry.v1.json",
            ]
        },
    )

    assert payload["docs"] == [
        "odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md",
        "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    ]
    retrieval_plan = payload.get("context_packet", {}).get("retrieval_plan", {})
    assert "selected_docs" not in retrieval_plan
    assert any("stop with no file changes" in hint for hint in payload["boundary_hints"])
    assert any("Do not widen into `src/odylith/cli.py`" in hint for hint in payload["boundary_hints"])


def test_component_governance_prompt_payload_prefers_noop_when_bounded_validators_pass() -> None:
    payload = prompt_payloads.supplement_live_prompt_payload(
        repo_root=Path("/tmp"),
        scenario={
            "family": "component_governance",
            "allow_noop_completion": True,
            "required_paths": [
                "odylith/registry/source/component_registry.v1.json",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
                "odylith/atlas/source/catalog/diagrams.v1.json",
                "tests/unit/runtime/test_validate_component_registry_contract.py",
                "tests/unit/runtime/test_render_mermaid_catalog.py",
            ],
        },
        prompt_payload={
            "context_packet": {
                "retrieval_plan": {
                    "selected_docs": [
                        "docs/benchmarks/README.md",
                        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                    ]
                }
            }
        },
        packet_source="governance_slice",
        changed_paths=[
            "odylith/registry/source/component_registry.v1.json",
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
            "tests/unit/runtime/test_validate_component_registry_contract.py",
            "tests/unit/runtime/test_render_mermaid_catalog.py",
        ],
        full_payload={
            "docs": [
                "odylith/registry/source/component_registry.v1.json",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "odylith/atlas/source/catalog/diagrams.v1.json",
                "docs/benchmarks/README.md",
            ]
        },
    )

    assert payload["docs"] == ["odylith/atlas/source/catalog/diagrams.v1.json"]
    assert payload["context_packet"]["anchors"]["explicit_paths"] == [
        "odylith/atlas/source/catalog/diagrams.v1.json"
    ]
    retrieval_plan = payload.get("context_packet", {}).get("retrieval_plan", {})
    assert "selected_docs" not in retrieval_plan
    assert any("stop with no file changes" in hint for hint in payload["boundary_hints"])
