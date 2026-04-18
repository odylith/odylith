from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


RUNTIME_LAYER_CONTRACT = "odylith_guidance_behavior_runtime_layers.v1"
RUNTIME_LAYER_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "layer": "context_engine",
        "purpose": "Context packets attach the compact guidance-behavior summary without running full validation on the hot path.",
        "source_tokens": {
            "src/odylith/runtime/context_engine/tooling_context_packet_builder.py": (
                "guidance_behavior_runtime.summary_for_packet",
                "guidance_behavior_summary",
                "recommended_commands",
            ),
            "src/odylith/runtime/context_engine/odylith_context_engine_packet_summary_runtime.py": (
                "guidance_behavior_status",
                "guidance_behavior_case_count",
            ),
        },
    },
    {
        "layer": "execution_engine",
        "purpose": "Execution handshakes and runtime-surface snapshots carry the validator command as recommended validation.",
        "source_tokens": {
            "src/odylith/runtime/context_engine/execution_engine_handshake.py": (
                "guidance_behavior_runtime.summary_from_sources",
                "validator_command",
                "recommended_validation",
            ),
            "src/odylith/runtime/execution_engine/runtime_surface_governance.py": (
                "guidance_behavior_runtime.summary_from_sources",
                "validator_command",
                "recommended_commands",
            ),
        },
    },
    {
        "layer": "memory_substrate",
        "purpose": "Memory contracts retain the summary in compact context and evidence packets.",
        "source_tokens": {
            "src/odylith/runtime/memory/tooling_memory_contracts.py": (
                "guidance_behavior_runtime.summary_from_sources",
                "guidance_behavior_summary",
                "context_packet.v1",
                "evidence_pack.v1",
            ),
            "src/odylith/runtime/governance/guidance_behavior_runtime.py": (
                "def compact_summary",
                "def summary_from_sources",
                "def summary_for_packet",
                "commands_with_validator",
                "tribunal_signal",
            ),
        },
    },
    {
        "layer": "intervention_engine",
        "purpose": "Intervention evidence treats material guidance-behavior state as a first-class evidence class.",
        "source_tokens": {
            "src/odylith/runtime/intervention_engine/alignment_evidence.py": (
                "guidance_behavior_contract",
                "Guidance behavior validation is not passing.",
                "tribunal_signal",
            ),
        },
    },
    {
        "layer": "tribunal",
        "purpose": "The runtime summary emits a Tribunal-ready signal that intervention evidence can reference.",
        "source_tokens": {
            "src/odylith/runtime/governance/guidance_behavior_runtime.py": (
                "tribunal_signal",
                "Guidance Behavior Contract",
                "Use the validator command for proof",
            ),
            "src/odylith/runtime/intervention_engine/alignment_evidence.py": (
                "_guidance_behavior_summary_from_observation",
                "Guidance Behavior Contract",
            ),
        },
    },
)


def _dedupe_strings(values: list[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def runtime_layer_contract_summary() -> dict[str, Any]:
    source_refs = _dedupe_strings(
        [
            path
            for contract in RUNTIME_LAYER_CONTRACTS
            for path in dict(contract.get("source_tokens", {})).keys()
        ]
    )
    return {
        "contract": RUNTIME_LAYER_CONTRACT,
        "layers": [str(contract.get("layer", "")).strip() for contract in RUNTIME_LAYER_CONTRACTS],
        "source_refs": source_refs,
        "hot_path": {
            "full_validation": False,
            "provider_calls": False,
            "summary_only": True,
        },
    }


def validate_runtime_layer_contracts(*, repo_root: Path) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    evidence: list[str] = []
    for contract in RUNTIME_LAYER_CONTRACTS:
        layer = str(contract.get("layer", "")).strip()
        source_tokens = contract.get("source_tokens", {})
        if not isinstance(source_tokens, Mapping):
            failures.append(
                {
                    "check_id": "guidance_behavior_runtime_layer_integration",
                    "message": f"runtime layer `{layer}` does not declare source token checks",
                }
            )
            continue
        for raw_path, raw_tokens in source_tokens.items():
            relative_path = str(raw_path or "").strip()
            path = repo_root / relative_path
            if not path.is_file():
                failures.append(
                    {
                        "check_id": "guidance_behavior_runtime_layer_integration",
                        "message": f"runtime layer `{layer}` integration file is missing",
                        "path": relative_path,
                    }
                )
                continue
            text = path.read_text(encoding="utf-8")
            missing_tokens = [
                str(token)
                for token in raw_tokens
                if str(token) and str(token) not in text
            ]
            if missing_tokens:
                failures.append(
                    {
                        "check_id": "guidance_behavior_runtime_layer_integration",
                        "message": f"runtime layer `{layer}` is missing integration token(s): {', '.join(missing_tokens)}",
                        "path": relative_path,
                    }
                )
                continue
            evidence.append(relative_path)
    summary = runtime_layer_contract_summary()
    return {
        "id": "guidance_behavior_runtime_layer_integration",
        "status": "passed" if not failures else "failed",
        "contract": RUNTIME_LAYER_CONTRACT,
        "layers": summary["layers"],
        "evidence": _dedupe_strings(evidence),
        "failures": failures,
    }


__all__ = [
    "RUNTIME_LAYER_CONTRACT",
    "RUNTIME_LAYER_CONTRACTS",
    "runtime_layer_contract_summary",
    "validate_runtime_layer_contracts",
]
