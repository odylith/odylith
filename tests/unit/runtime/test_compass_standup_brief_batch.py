from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_standup_brief_batch as batch
from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator


class _QueuedProvider:
    def __init__(self, results):  # noqa: ANN001
        self._results = list(results)
        self.calls = 0
        self.requests = []

    def generate_structured(self, *, request):  # noqa: ANN001
        self.calls += 1
        self.requests.append(request)
        if not self._results:
            return None
        return self._results.pop(0)

    def generate_finding(self, *, prompt_payload):  # noqa: ANN001, ARG002
        raise AssertionError("Compass standup narration should use structured generation only.")


def _reasoning_config() -> odylith_reasoning.ReasoningConfig:
    return odylith_reasoning.ReasoningConfig(
        mode="auto",
        provider="openai-compatible",
        model="gpt-test",
        base_url="https://example.invalid",
        api_key="secret",
        scope_cap=5,
        timeout_seconds=3.0,
        codex_bin="codex",
        codex_reasoning_effort="high",
    )


def _generated_utc() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fact_packet(*, idea_id: str, window: str = "24h") -> dict[str, object]:
    sections = [
        {
            "key": "completed",
            "label": "Completed in this window",
            "facts": [
                {
                    "id": "F-001",
                    "section_key": "completed",
                    "voice_hint": "operator",
                    "kind": "plan_completion",
                    "text": f"Verified milestone closure landed for {idea_id}.",
                }
            ],
        },
        {
            "key": "current_execution",
            "label": "Current execution",
            "facts": [
                {
                    "id": "F-002",
                    "section_key": "current_execution",
                    "voice_hint": "executive",
                    "kind": "direction",
                    "text": f"{idea_id} is moving through real implementation work.",
                },
                {
                    "id": "F-003",
                    "section_key": "current_execution",
                    "voice_hint": "operator",
                    "kind": "signal",
                    "text": f"Primary execution signal: {idea_id} recorded a concrete implementation update.",
                },
            ],
        },
        {
            "key": "next_planned",
            "label": "Next planned",
            "facts": [
                {
                    "id": "F-004",
                    "section_key": "next_planned",
                    "voice_hint": "operator",
                    "kind": "forcing_function",
                    "text": f"Land the next checked step in {idea_id}.",
                }
            ],
        },
        {
            "key": "risks_to_watch",
            "label": "Risks to watch",
            "facts": [
                {
                    "id": "F-005",
                    "section_key": "risks_to_watch",
                    "voice_hint": "operator",
                    "kind": "risk_posture",
                    "text": f"{idea_id} still needs the next verified checkpoint.",
                }
            ],
        },
    ]
    facts = []
    for section in sections:
        facts.extend(section["facts"])
    return {
        "version": "v1",
        "window": window,
        "scope": {
            "mode": "scoped",
            "idea_id": idea_id,
            "label": f"Compass Workstream ({idea_id})",
            "status": "implementation",
        },
        "summary": {
            "window_hours": 24 if window == "24h" else 48,
            "freshness": {
                "bucket": "recent",
                "latest_evidence_utc": "2026-04-08T21:00:00Z",
                "source": "transaction",
            },
            "storyline": {
                "flagship_lane": idea_id,
                "direction": f"{idea_id} is moving through real implementation work.",
                "proof": f"Latest execution evidence is tied directly to {idea_id}.",
                "forcing_function": f"Land the next checked step in {idea_id}.",
                "use_story": "Maintainers need the workstream story in ordinary words.",
                "architecture_consequence": "The workstream stays easier to trust when the brief stays concrete.",
                "watch_item": f"{idea_id} still needs the next verified checkpoint.",
            },
        },
        "facts": facts,
        "sections": sections,
    }


def _single_scope_response(packet: dict[str, object]) -> dict[str, object]:
    return {
        "sections": narrator._deterministic_sections(fact_packet=packet),  # noqa: SLF001
    }


def _batch_response(scope_packets: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "briefs": [
            {
                "scope_id": scope_id,
                "sections": narrator._deterministic_sections(fact_packet=packet),  # noqa: SLF001
            }
            for scope_id, packet in scope_packets.items()
        ]
    }


def test_build_scoped_briefs_reuses_exact_cache_before_batch_provider(tmp_path: Path) -> None:
    cached_packet = _fact_packet(idea_id="B-101")
    cold_packet = _fact_packet(idea_id="B-202")
    generated_utc = _generated_utc()
    seed_provider = _QueuedProvider([_single_scope_response(cached_packet)])
    narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=cached_packet,
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=seed_provider,
    )

    provider = _QueuedProvider([_batch_response({"B-202": cold_packet})])
    results = batch.build_scoped_briefs(
        repo_root=tmp_path,
        fact_packets_by_scope={
            "B-101": cached_packet,
            "B-202": cold_packet,
        },
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=provider,
    )

    assert results["B-101"]["source"] == "cache"
    assert results["B-202"]["source"] == "provider"
    assert provider.calls == 1
    scoped_packets = provider.requests[0].prompt_payload["scoped_fact_packets"]
    assert len(scoped_packets) == 1
    assert scoped_packets[0]["scope_id"] == "B-202"


def test_build_scoped_briefs_reuses_context_matched_cache_before_batch_provider(tmp_path: Path) -> None:
    cached_packet = _fact_packet(idea_id="B-111")
    changed_packet = json.loads(json.dumps(cached_packet))
    changed_fact = {
        "id": "F-099",
        "section_key": "current_execution",
        "voice_hint": "operator",
        "kind": "signal",
        "text": "Fresh packet drift arrived without invalidating the earlier cited story.",
    }
    changed_packet["facts"].append(changed_fact)
    changed_packet["sections"][1]["facts"].append(changed_fact)
    cold_packet = _fact_packet(idea_id="B-222")
    generated_utc = _generated_utc()
    seed_provider = _QueuedProvider([_single_scope_response(cached_packet)])
    narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=cached_packet,
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=seed_provider,
    )

    provider = _QueuedProvider([_batch_response({"B-222": cold_packet})])
    results = batch.build_scoped_briefs(
        repo_root=tmp_path,
        fact_packets_by_scope={
            "B-111": changed_packet,
            "B-222": cold_packet,
        },
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=provider,
    )

    assert results["B-111"]["source"] == "cache"
    assert results["B-222"]["source"] == "provider"
    assert provider.calls == 1
    scoped_packets = provider.requests[0].prompt_payload["scoped_fact_packets"]
    assert len(scoped_packets) == 1
    assert scoped_packets[0]["scope_id"] == "B-222"


def test_build_single_scope_brief_reuses_context_cache_before_composed_fallback(tmp_path: Path) -> None:
    cached_packet = _fact_packet(idea_id="B-111")
    changed_packet = json.loads(json.dumps(cached_packet))
    changed_fact = {
        "id": "F-099",
        "section_key": "current_execution",
        "voice_hint": "operator",
        "kind": "signal",
        "text": "Fresh packet drift arrived without invalidating the earlier cited story.",
    }
    changed_packet["facts"].append(changed_fact)
    changed_packet["sections"][1]["facts"].append(changed_fact)
    generated_utc = _generated_utc()
    seed_provider = _QueuedProvider([_single_scope_response(cached_packet)])
    narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=cached_packet,
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=seed_provider,
    )

    provider = _QueuedProvider([None])
    results = batch._build_single_scope_brief(  # noqa: SLF001
        repo_root=tmp_path,
        scope_id="B-111",
        fact_packet=changed_packet,
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=provider,
    )

    assert results["B-111"]["source"] == "cache"
    assert provider.calls == 0


def test_build_scoped_briefs_batches_cold_scopes_into_bounded_packs(tmp_path: Path) -> None:
    packets = {
        "B-301": _fact_packet(idea_id="B-301"),
        "B-302": _fact_packet(idea_id="B-302"),
        "B-303": _fact_packet(idea_id="B-303"),
    }
    provider = _QueuedProvider(
        [
            _batch_response({key: packets[key] for key in ("B-301", "B-302")}),
            _batch_response({"B-303": packets["B-303"]}),
        ]
    )

    results = batch.build_scoped_briefs(
        repo_root=tmp_path,
        fact_packets_by_scope=packets,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
        pack_size=2,
    )

    assert sorted(results) == ["B-301", "B-302", "B-303"]
    assert all(results[scope_id]["source"] == "provider" for scope_id in results)
    assert provider.calls == 2
    assert len(provider.requests[0].prompt_payload["scoped_fact_packets"]) == 2
    assert len(provider.requests[1].prompt_payload["scoped_fact_packets"]) == 1


def test_build_scoped_briefs_repairs_invalid_batch_before_falling_back(tmp_path: Path) -> None:
    packets = {
        "B-401": _fact_packet(idea_id="B-401"),
        "B-402": _fact_packet(idea_id="B-402"),
    }
    provider = _QueuedProvider(
        [
            _batch_response({"B-401": packets["B-401"]}),
            _batch_response({"B-402": packets["B-402"]}),
        ]
    )

    results = batch.build_scoped_briefs(
        repo_root=tmp_path,
        fact_packets_by_scope=packets,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
        pack_size=8,
    )

    assert sorted(results) == ["B-401", "B-402"]
    assert all(results[scope_id]["source"] == "provider" for scope_id in results)
    assert provider.calls == 2
    assert provider.requests[1].schema_name == "compass_standup_brief_batch_repair"
    repair_packets = provider.requests[1].prompt_payload["scoped_fact_packets"]
    assert len(repair_packets) == 1
    assert repair_packets[0]["scope_id"] == "B-402"


def test_build_scoped_briefs_splits_unresolved_pack_before_retrying_singles(tmp_path: Path) -> None:
    packets = {
        "B-501": _fact_packet(idea_id="B-501"),
        "B-502": _fact_packet(idea_id="B-502"),
        "B-503": _fact_packet(idea_id="B-503"),
    }
    provider = _QueuedProvider(
        [
            _batch_response({"B-501": packets["B-501"]}),
            None,
            _batch_response({"B-502": packets["B-502"]}),
            _batch_response({"B-503": packets["B-503"]}),
        ]
    )

    results = batch.build_scoped_briefs(
        repo_root=tmp_path,
        fact_packets_by_scope=packets,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
        pack_size=8,
    )

    assert sorted(results) == ["B-501", "B-502", "B-503"]
    assert provider.calls == 4
    assert provider.requests[0].schema_name == "compass_standup_brief_batch"
    assert provider.requests[1].schema_name == "compass_standup_brief_batch_repair"
    assert provider.requests[2].schema_name == "compass_standup_brief_batch"
    assert provider.requests[3].schema_name == "compass_standup_brief_batch"
    assert len(provider.requests[2].prompt_payload["scoped_fact_packets"]) == 1
    assert len(provider.requests[3].prompt_payload["scoped_fact_packets"]) == 1


def test_build_scoped_briefs_respects_payload_char_budget(tmp_path: Path) -> None:
    packets = {
        "B-601": _fact_packet(idea_id="B-601"),
        "B-602": _fact_packet(idea_id="B-602"),
        "B-603": _fact_packet(idea_id="B-603"),
    }
    provider = _QueuedProvider(
        [
            _batch_response({"B-601": packets["B-601"]}),
            _batch_response({"B-602": packets["B-602"]}),
            _batch_response({"B-603": packets["B-603"]}),
        ]
    )

    results = batch.build_scoped_briefs(
        repo_root=tmp_path,
        fact_packets_by_scope=packets,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
        pack_size=8,
        max_pack_payload_chars=1,
    )

    assert sorted(results) == ["B-601", "B-602", "B-603"]
    assert provider.calls == 3
    assert all(len(request.prompt_payload["scoped_fact_packets"]) == 1 for request in provider.requests)
