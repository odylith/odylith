"""Dispatch one bounded Greenfield model stage and retain its exact receipt."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_json import (
    encode_greenfield_model_value,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
    GreenfieldModelRuntimeError,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    require_greenfield_model_profile_observation,
)
from odylith.runtime.reasoning import odylith_reasoning


@dataclass(frozen=True)
class GreenfieldModelStageResult:
    """One immutable structured response plus private and sealed observations."""

    response: dict[str, Any]
    observation: dict[str, Any]
    receipt: dict[str, Any]


def dispatch_greenfield_model_stage(
    *,
    role: str,
    schema_name: str,
    system_prompt: str,
    output_schema: Mapping[str, Any],
    prompt_payload: Mapping[str, Any],
    provider_factory: Callable[[], odylith_reasoning.ReasoningProvider | None] | None,
    profile_id: str,
    model: str,
    reasoning_effort: str,
    deadline: float,
    clock: Callable[[], float],
    observation: dict[str, Any],
) -> GreenfieldModelStageResult:
    """Run one declared role inside the caller's absolute shared deadline."""

    if deadline - clock() < 1.0:
        raise GreenfieldModelRuntimeError("timeout")
    if provider_factory is None:
        raise GreenfieldModelRuntimeError("unavailable")
    try:
        provider = provider_factory()
    except GreenfieldModelRuntimeError:
        raise
    except TimeoutError as exc:
        raise GreenfieldModelRuntimeError("timeout") from exc
    except Exception as exc:
        raise GreenfieldModelAuthoringError(
            "Greenfield model authoring is unavailable; no records were created."
        ) from exc
    if provider is None:
        raise GreenfieldModelRuntimeError("unavailable")
    timeout_seconds = deadline - clock()
    if timeout_seconds < 1.0:
        raise GreenfieldModelRuntimeError("timeout")
    before = odylith_reasoning.provider_failure_metadata(provider)
    require_greenfield_model_profile_observation(
        profile_id=profile_id,
        provider=before.get("provider", ""),
        model=model,
        reasoning_effort=reasoning_effort,
        effective_timeout_seconds=timeout_seconds,
        request_role=role,
    )
    request = odylith_reasoning.StructuredReasoningRequest(
        system_prompt=system_prompt,
        schema_name=schema_name,
        output_schema=deepcopy(dict(output_schema)),
        prompt_payload=deepcopy(dict(prompt_payload)),
        model=model,
        reasoning_effort=reasoning_effort,
        timeout_seconds=timeout_seconds,
    )
    frozen_request = encode_greenfield_model_value(asdict(request))
    observation.update(
        dispatched=True,
        request_role=role,
        profile_id=profile_id,
        timeout_seconds=timeout_seconds,
        model=model,
        reasoning_effort=reasoning_effort,
        request=deepcopy(dict(prompt_payload)),
    )
    started = clock()
    try:
        response = provider.generate_structured(request=request)
    except TimeoutError as exc:
        observation["provider"] = _categorical_provider_metadata(provider)
        raise GreenfieldModelRuntimeError("timeout") from exc
    except Exception as exc:
        observation["provider"] = _categorical_provider_metadata(provider)
        raise GreenfieldModelAuthoringError(
            "Greenfield model authoring is unavailable; no records were created."
        ) from exc
    finally:
        observation["elapsed_seconds"] = max(0.0, clock() - started)
    metadata = odylith_reasoning.provider_failure_metadata(provider)
    observation["provider"] = (
        metadata if isinstance(response, Mapping) else _categorical_provider_metadata(provider)
    )
    if encode_greenfield_model_value(asdict(request)) != frozen_request:
        raise GreenfieldModelAuthoringError(
            "Greenfield model provider changed its request; no records were created."
        )
    if clock() > deadline:
        raise GreenfieldModelRuntimeError("timeout")
    model_profile = {
        "profile_id": profile_id,
        "provider": metadata.get("provider", ""),
        "model": metadata.get("model") or model,
        "reasoning_effort": metadata.get("reasoning_effort") or reasoning_effort,
        "effective_timeout_seconds": timeout_seconds,
        "authoring_tier": get_greenfield_model_profile(profile_id).repair_tier,
    }
    require_greenfield_model_profile_observation(
        **model_profile,
        request_role=role,
    )
    if response is None and metadata.get("code") in {"timeout", "unavailable"}:
        raise GreenfieldModelRuntimeError(str(metadata["code"]))
    if not isinstance(response, Mapping):
        observation["response_shape"] = type(response).__name__
        raise GreenfieldModelAuthoringError(
            "Greenfield model authoring returned an invalid response; no records were created."
        )
    observation["response"] = deepcopy(response)
    return GreenfieldModelStageResult(
        response=deepcopy(dict(response)),
        observation=deepcopy(observation),
        receipt={
            "elapsed_seconds": observation["elapsed_seconds"],
            "model_profile": model_profile,
        },
    )


def _categorical_provider_metadata(provider: Any) -> dict[str, str]:
    """Retain non-sensitive failure identity without provider diagnostics."""

    value = odylith_reasoning.provider_failure_metadata(provider)
    return {
        key: value[key]
        for key in ("provider", "model", "reasoning_effort", "code")
    }


__all__ = ["GreenfieldModelStageResult", "dispatch_greenfield_model_stage"]
