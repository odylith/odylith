from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_standup_brief_batch as batch
from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator


class _QueuedProvider:
    def __init__(self, results, *, failure_codes=None, failure_details=None):  # noqa: ANN001
        self._results = list(results)
        self._failure_codes = list(failure_codes or [])
        self._failure_details = list(failure_details or [])
        self.calls = 0
        self.requests = []
        self.last_failure_code = ""
        self.last_failure_detail = ""

    def generate_structured(self, *, request):  # noqa: ANN001
        self.calls += 1
        self.requests.append(request)
        if not self._results:
            self.last_failure_code = ""
            self.last_failure_detail = ""
            return None
        result = self._results.pop(0)
        failure_code = str(self._failure_codes.pop(0) if self._failure_codes else "").strip()
        failure_detail = str(self._failure_details.pop(0) if self._failure_details else "").strip()
        if result is None:
            self.last_failure_code = failure_code
            self.last_failure_detail = failure_detail
        else:
            self.last_failure_code = ""
            self.last_failure_detail = ""
        return result

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
        "sections": _provider_sections(packet),
    }


def _batch_response(scope_packets: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "briefs": [
            {
                "scope_id": scope_id,
                "sections": _provider_sections(packet),
            }
            for scope_id, packet in scope_packets.items()
        ]
    }


def _window_batch_response(window_packets: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "briefs": [
            {
                "window_key": window_key,
                "sections": _provider_sections(packet),
            }
            for window_key, packet in window_packets.items()
        ]
    }


def _bundle_response(
    *,
    global_packets: dict[str, dict[str, object]] | None = None,
    scoped_packets: dict[str, dict[str, dict[str, object]]] | None = None,
) -> dict[str, object]:
    briefs: list[dict[str, object]] = []
    for window_key, packet in (global_packets or {}).items():
        briefs.append(
            {
                "entry_kind": "global",
                "window_key": window_key,
                "sections": _provider_sections(packet),
            }
        )
    for window_key, window_packets in (scoped_packets or {}).items():
        for scope_id, packet in window_packets.items():
            briefs.append(
                {
                    "entry_kind": "scoped",
                    "window_key": window_key,
                    "scope_id": scope_id,
                    "sections": _provider_sections(packet),
                }
            )
    return {"briefs": briefs}


def _provider_sections(packet: dict[str, object]) -> list[dict[str, object]]:
    scope = packet.get("scope", {})
    idea_id = str(scope.get("idea_id", "")).strip() or "this workstream"
    return [
        {
            "key": "completed",
            "label": "Completed in this window",
            "bullets": [
                {
                    "text": f"Verified milestone closure landed for {idea_id}.",
                    "fact_ids": ["F-001"],
                }
            ],
        },
        {
            "key": "current_execution",
            "label": "Current execution",
            "bullets": [
                {
                    "text": f"{idea_id} is moving through real implementation work.",
                    "fact_ids": ["F-002"],
                },
                {
                    "text": f"The latest implementation update is still the clearest proof that {idea_id} is moving.",
                    "fact_ids": ["F-003"],
                },
            ],
        },
        {
            "key": "next_planned",
            "label": "Next planned",
            "bullets": [
                {
                    "text": f"Land the next checked step in {idea_id}.",
                    "fact_ids": ["F-004"],
                }
            ],
        },
        {
            "key": "risks_to_watch",
            "label": "Risks to watch",
            "bullets": [
                {
                    "text": f"{idea_id} still needs the next verified checkpoint.",
                    "fact_ids": ["F-005"],
                }
            ],
        },
    ]


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

    provider = _QueuedProvider([_single_scope_response(cold_packet)])
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
    assert provider.requests[0].schema_name == "compass_standup_brief"


def test_build_scoped_briefs_does_not_reuse_context_matched_cache_before_batch_provider(tmp_path: Path) -> None:
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

    assert "B-111" not in results
    assert results["B-222"]["source"] == "provider"
    assert provider.calls >= 1
    scoped_packets = provider.requests[0].prompt_payload["scoped_fact_packets"]
    assert {row["scope_id"] for row in scoped_packets} == {"B-111", "B-222"}


def test_build_single_scope_brief_fails_closed_when_exact_cache_is_missing(tmp_path: Path) -> None:
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

    assert results == {}
    assert provider.calls == 2


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


def test_build_scoped_briefs_single_scope_uses_single_scope_narrator_path(tmp_path: Path) -> None:
    packets = {
        "B-320": _fact_packet(idea_id="B-320"),
    }
    provider = _QueuedProvider([_single_scope_response(packets["B-320"])])

    results = batch.build_scoped_briefs(
        repo_root=tmp_path,
        fact_packets_by_scope=packets,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
        pack_size=8,
    )

    assert sorted(results) == ["B-320"]
    assert provider.calls == 1
    assert provider.requests[0].schema_name == "compass_standup_brief"


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


def test_build_scoped_briefs_aborts_fanout_on_provider_budget_failure(tmp_path: Path) -> None:
    packets = {
        "B-551": _fact_packet(idea_id="B-551"),
        "B-552": _fact_packet(idea_id="B-552"),
        "B-553": _fact_packet(idea_id="B-553"),
    }
    provider = _QueuedProvider(
        [None],
        failure_codes=["credits_exhausted"],
        failure_details=["insufficient_quota: out of credits"],
    )

    results = batch.build_scoped_briefs(
        repo_root=tmp_path,
        fact_packets_by_scope=packets,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
        pack_size=8,
    )

    assert results == {}
    assert provider.calls == 1
    assert provider.requests[0].schema_name == "compass_standup_brief_batch"


def test_build_scoped_briefs_keeps_partial_ready_results_when_repair_hits_provider_failure(tmp_path: Path) -> None:
    packets = {
        "B-561": _fact_packet(idea_id="B-561"),
        "B-562": _fact_packet(idea_id="B-562"),
    }
    provider = _QueuedProvider(
        [
            _batch_response({"B-561": packets["B-561"]}),
            None,
        ],
        failure_codes=["", "provider_error"],
        failure_details=["", "Codex CLI exited with status 1."],
    )

    results = batch.build_scoped_briefs(
        repo_root=tmp_path,
        fact_packets_by_scope=packets,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
        pack_size=8,
    )

    assert sorted(results) == ["B-561"]
    assert provider.calls == 2
    assert provider.requests[1].schema_name == "compass_standup_brief_batch_repair"


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


def test_build_window_briefs_reuses_exact_cache_before_batch_provider(tmp_path: Path) -> None:
    cached_packet = _fact_packet(idea_id="B-701", window="24h")
    cold_packet = _fact_packet(idea_id="B-702", window="48h")
    generated_utc = _generated_utc()
    seed_provider = _QueuedProvider([_single_scope_response(cached_packet)])
    narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=cached_packet,
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=seed_provider,
    )

    provider = _QueuedProvider([_window_batch_response({"48h": cold_packet})])
    results = batch.build_window_briefs(
        repo_root=tmp_path,
        fact_packets_by_window={
            "24h": cached_packet,
            "48h": cold_packet,
        },
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=provider,
    )

    assert results["24h"]["source"] == "cache"
    assert results["48h"]["source"] == "provider"
    assert provider.calls == 1
    window_packets = provider.requests[0].prompt_payload["window_fact_packets"]
    assert len(window_packets) == 1
    assert window_packets[0]["window_key"] == "48h"


def test_build_window_briefs_batches_global_windows_into_one_provider_call(tmp_path: Path) -> None:
    packets = {
        "24h": _fact_packet(idea_id="B-801", window="24h"),
        "48h": _fact_packet(idea_id="B-802", window="48h"),
    }
    provider = _QueuedProvider([_window_batch_response(packets)])

    results = batch.build_window_briefs(
        repo_root=tmp_path,
        fact_packets_by_window=packets,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
    )

    assert sorted(results) == ["24h", "48h"]
    assert provider.calls == 1
    assert provider.requests[0].schema_name == "compass_standup_brief_window_batch"
    assert len(provider.requests[0].prompt_payload["window_fact_packets"]) == 2


def test_build_window_briefs_repairs_missing_window_without_falling_back_to_singles(tmp_path: Path) -> None:
    packets = {
        "24h": _fact_packet(idea_id="B-901", window="24h"),
        "48h": _fact_packet(idea_id="B-902", window="48h"),
    }
    provider = _QueuedProvider(
        [
            _window_batch_response({"24h": packets["24h"]}),
            _window_batch_response({"48h": packets["48h"]}),
        ]
    )

    results = batch.build_window_briefs(
        repo_root=tmp_path,
        fact_packets_by_window=packets,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
        fallback_to_single=False,
    )

    assert sorted(results) == ["24h", "48h"]
    assert provider.calls == 2
    assert provider.requests[0].schema_name == "compass_standup_brief_window_batch"
    assert provider.requests[1].schema_name == "compass_standup_brief_window_batch_repair"


def test_build_brief_bundle_reuses_cache_and_warms_globals_and_scopes_in_one_provider_call(tmp_path: Path) -> None:
    cached_global = _fact_packet(idea_id="B-701", window="24h")
    cold_global = _fact_packet(idea_id="B-702", window="48h")
    cached_scope = _fact_packet(idea_id="B-011", window="24h")
    cold_scope = _fact_packet(idea_id="B-012", window="24h")
    generated_utc = _generated_utc()

    seed_provider = _QueuedProvider([
        _single_scope_response(cached_global),
        _single_scope_response(cached_scope),
    ])
    narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=cached_global,
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=seed_provider,
    )
    narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=cached_scope,
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=seed_provider,
    )

    provider = _QueuedProvider(
        [
            _bundle_response(
                global_packets={"48h": cold_global},
                scoped_packets={"24h": {"B-012": cold_scope}},
            )
        ]
    )
    results = batch.build_brief_bundle(
        repo_root=tmp_path,
        global_fact_packets_by_window={"24h": cached_global, "48h": cold_global},
        scoped_fact_packets_by_window={"24h": {"B-011": cached_scope, "B-012": cold_scope}},
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=provider,
    )

    assert results["global"]["24h"]["source"] == "cache"
    assert results["global"]["48h"]["source"] == "provider"
    assert results["scoped"]["24h"]["B-011"]["source"] == "cache"
    assert results["scoped"]["24h"]["B-012"]["source"] == "provider"
    assert provider.calls == 1
    assert provider.requests[0].schema_name == "compass_standup_brief_bundle"


def test_build_brief_bundle_repairs_missing_entries_once_without_scoped_fanout(tmp_path: Path) -> None:
    packets_global = {
        "24h": _fact_packet(idea_id="B-801", window="24h"),
        "48h": _fact_packet(idea_id="B-802", window="48h"),
    }
    packets_scoped = {
        "24h": {
            "B-021": _fact_packet(idea_id="B-021", window="24h"),
            "B-048": _fact_packet(idea_id="B-048", window="24h"),
        }
    }
    provider = _QueuedProvider(
        [
            _bundle_response(
                global_packets={"24h": packets_global["24h"]},
                scoped_packets={"24h": {"B-021": packets_scoped["24h"]["B-021"]}},
            ),
            _bundle_response(
                global_packets={"48h": packets_global["48h"]},
                scoped_packets={"24h": {"B-048": packets_scoped["24h"]["B-048"]}},
            ),
        ]
    )

    results = batch.build_brief_bundle(
        repo_root=tmp_path,
        global_fact_packets_by_window=packets_global,
        scoped_fact_packets_by_window=packets_scoped,
        generated_utc=_generated_utc(),
        config=_reasoning_config(),
        provider=provider,
    )

    assert sorted(results["global"]) == ["24h", "48h"]
    assert sorted(results["scoped"]["24h"]) == ["B-021", "B-048"]
    assert provider.calls == 2
    assert provider.requests[0].schema_name == "compass_standup_brief_bundle"
    assert provider.requests[1].schema_name == "compass_standup_brief_bundle_repair"
