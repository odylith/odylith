from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator
from odylith.runtime.reasoning import odylith_reasoning


class _FakeProvider:
    def __init__(self, result):  # noqa: ANN001
        self._result = result
        self.calls = 0
        self.last_request = None

    def generate_structured(self, *, request):  # noqa: ANN001
        self.calls += 1
        self.last_request = request
        return self._result

    def generate_finding(self, *, prompt_payload):  # noqa: ANN001, ARG002
        raise AssertionError("Compass standup narration should use structured generation only.")


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


def _fact_packet(
    *,
    freshness_bucket: str = "recent",
    include_freshness_fact: bool = False,
    scope_mode: str = "scoped",
    idea_id: str = "B-101",
    window: str = "48h",
    self_host: dict[str, object] | None = None,
) -> dict[str, object]:
    current_execution_facts = [
        {
            "id": "F-002",
            "section_key": "current_execution",
            "voice_hint": "executive",
            "kind": "direction",
            "text": "Compass is being steered around AI-first standup narration.",
        },
        {
            "id": "F-003",
            "section_key": "current_execution",
            "voice_hint": "operator",
            "kind": "signal",
            "text": "Primary execution signal: updated Compass narrative to capture implementation intent.",
        },
        {
            "id": "F-004",
            "section_key": "current_execution",
            "voice_hint": "operator",
            "kind": "timeline",
            "text": "Timeline signal: projected at roughly 5 days.",
        },
    ]
    if include_freshness_fact:
        current_execution_facts.append(
            {
                "id": "F-009",
                "section_key": "current_execution",
                "voice_hint": "operator",
                "kind": "freshness",
                "text": "Freshness signal is stale: latest linked execution proof is more than a day old, so a new checkpoint is needed before momentum claims stay credible.",
            }
        )
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
                    "text": "Verified milestone closeout landed for Compass.",
                }
            ],
        },
        {
            "key": "current_execution",
            "label": "Current execution",
            "facts": current_execution_facts,
        },
        {
            "key": "next_planned",
            "label": "Next planned",
            "facts": [
                {
                    "id": "F-005",
                    "section_key": "next_planned",
                    "voice_hint": "operator",
                    "kind": "forcing_function",
                    "text": "Immediate forcing function is to land implement compass renderer.",
                }
            ],
        },
        {
            "key": "why_this_matters",
            "label": "Why this matters",
            "facts": [
                {
                    "id": "F-006",
                    "section_key": "why_this_matters",
                    "voice_hint": "executive",
                    "kind": "executive_impact",
                    "text": "Platform maintainers need deterministic execution status.",
                },
                {
                    "id": "F-007",
                    "section_key": "why_this_matters",
                    "voice_hint": "operator",
                    "kind": "operator_leverage",
                    "text": "The architecture move is to use a generated executive dashboard, which gives operators a clearer contract and lower coordination risk.",
                },
            ],
        },
        {
            "key": "risks_to_watch",
            "label": "Risks to watch",
            "facts": [
                {
                    "id": "F-008",
                    "section_key": "risks_to_watch",
                    "voice_hint": "operator",
                    "kind": "risk_posture",
                    "text": "No critical blockers are currently surfaced.",
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
            "mode": scope_mode,
            "idea_id": idea_id if scope_mode == "scoped" else "",
            "label": f"Compass Workstream ({idea_id})" if scope_mode == "scoped" else "Global",
        },
        "summary": {
            "window_hours": 24 if window == "24h" else 48,
            "freshness": {
                "bucket": freshness_bucket,
                "latest_evidence_utc": "2026-03-13T19:30:00Z",
                "source": "transaction",
            },
            **({"self_host": self_host} if isinstance(self_host, dict) else {}),
            "storyline": {
                "use_story": "Platform maintainers need deterministic execution status.",
                "architecture_consequence": "The architecture move is to use a generated executive dashboard, which gives operators a clearer contract and lower coordination risk.",
            },
        },
        "sections": sections,
        "facts": facts,
    }


def _set_fact_text(
    packet: dict[str, object],
    *,
    kind: str,
    text: str,
) -> dict[str, object]:
    clone = json.loads(json.dumps(packet))
    for fact in clone.get("facts", []):
        if isinstance(fact, dict) and str(fact.get("kind", "")).strip() == kind:
            fact["text"] = text
    for section in clone.get("sections", []):
        if not isinstance(section, dict):
            continue
        for fact in section.get("facts", []):
            if isinstance(fact, dict) and str(fact.get("kind", "")).strip() == kind:
                fact["text"] = text
    return clone


def _now_utc_iso() -> str:
    current = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0)
    return current.isoformat().replace("+00:00", "Z")


def _valid_provider_result() -> dict[str, object]:
    return {
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [
                    {
                        "voice": "operator",
                        "text": "Compass finally has a standup brief that reads like someone made a call, not like the UI restated metadata.",
                        "fact_ids": ["F-001"],
                    },
                ],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "bullets": [
                    {
                        "voice": "executive",
                        "text": "The live brief is still where Compass has to earn trust, because it can flatten the work behind it into dashboard prose.",
                        "fact_ids": ["F-002"],
                    },
                    {
                        "voice": "operator",
                        "text": "Right now the clearest signal is that the narrative layer was updated to capture implementation intent.",
                        "fact_ids": ["F-003"],
                    },
                    {
                        "voice": "operator",
                        "text": "The schedule still matters here: projected at roughly 5 days.",
                        "fact_ids": ["F-004"],
                    },
                ],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "bullets": [
                    {
                        "voice": "operator",
                        "text": "Next up is to land the Compass renderer cleanly.",
                        "fact_ids": ["F-005"],
                    },
                ],
            },
            {
                "key": "why_this_matters",
                "label": "Why this matters",
                "bullets": [
                    {
                        "voice": "executive",
                        "text": "What is at stake here is whether maintainers can read execution status without translating dashboard prose.",
                        "fact_ids": ["F-006"],
                    },
                    {
                        "voice": "operator",
                        "text": "A sharper brief makes operators spend less time decoding the screen and more time acting on it.",
                        "fact_ids": ["F-007"],
                    },
                ],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "bullets": [
                    {"voice": "operator", "text": "No critical blockers are currently surfaced.", "fact_ids": ["F-008"]},
                ],
            },
        ]
    }


def test_build_standup_brief_accepts_valid_provider_output(tmp_path: Path) -> None:
    provider = _FakeProvider(_valid_provider_result())

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"
    assert len(brief["sections"]) == 5
    first_bullet = brief["sections"][0]["bullets"][0]
    assert first_bullet["fact_ids"] == ["F-001"]
    assert brief["evidence_lookup"]["F-001"]["text"] == "Verified milestone closeout landed for Compass."
    cache_path = narrator.standup_brief_cache_path(repo_root=tmp_path)
    assert cache_path.is_file()
    cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cache_payload["entries"]
    assert provider.calls == 1


def test_build_standup_brief_retries_one_transient_empty_provider_reply(tmp_path: Path) -> None:
    provider = _QueuedProvider([None, _valid_provider_result()])

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"
    assert provider.calls == 2


def test_build_standup_brief_uses_deterministic_fallback_after_repeated_empty_provider_replies(tmp_path: Path) -> None:
    provider = _QueuedProvider([None, None])

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "provider_empty"
    assert brief["sections"]
    assert provider.calls == 2


def test_build_standup_brief_uses_deterministic_fallback_for_invalid_provider_output(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][1]["bullets"][1]["text"] = "src/odylith/runtime/surfaces/render_compass_dashboard.py is the current execution focus."
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"
    assert brief["sections"]


def test_build_standup_brief_rejects_wordy_filler_output(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][1]["bullets"][1]["text"] = (
        "In the same window the current portfolio direction around Compass became much clearer because the team kept "
        "adding more and more explanatory words here than a crisp standup bullet should ever need for one proof point."
    )
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


def test_build_standup_brief_rejects_cross_section_fact_citations(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][2]["bullets"][0]["fact_ids"] = ["F-003"]
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


def test_provider_request_contract_emphasizes_maintainer_voice_and_explicit_why() -> None:
    request = narrator._provider_request(fact_packet=_fact_packet())  # noqa: SLF001

    assert "strong maintainer speaking off notes" in request.system_prompt.lower()
    assert "make the why explicit" in request.system_prompt.lower()
    assert "write with stance" in request.system_prompt.lower()
    assert "do not write in first-person singular" in request.system_prompt.lower()
    assert "do not invent a house style or signature lead-in" in request.system_prompt.lower()
    assert "the real center of gravity is" in request.system_prompt.lower()
    assert "attention stays on" in request.system_prompt.lower()
    assert "live self-host or install posture facts" in request.system_prompt.lower()
    assert request.reasoning_effort == "medium"
    assert request.timeout_seconds == 30.0

    why_contract = next(
        section for section in request.prompt_payload["brief_contract"]["sections"] if section["key"] == "why_this_matters"
    )
    assert "customer or product use-story" in why_contract["objective"].lower()
    assert "architecture or operator consequence" in why_contract["objective"].lower()
    assert "maintainer-delivered standup" in " ".join(request.prompt_payload["brief_contract"]["writing_contract"]["rules"]).lower()
    rules = " ".join(request.prompt_payload["brief_contract"]["writing_contract"]["rules"]).lower()
    assert "vary sentence openings naturally" in rules
    assert "avoid recurring signature openings" in rules
    assert "state the unresolved problem directly" in rules
    assert "do not wrap priority in generic labels" in rules
    assert request.prompt_payload["brief_contract"]["style_examples"]["completed"][0].startswith(
        "This window finally cleared two lingering obligations"
    )
    assert request.prompt_payload["brief_contract"]["style_examples"]["current_execution_executive"][0].startswith(
        "The unresolved piece in `B-027` is the lane boundary"
    )


def test_build_standup_brief_rejects_first_person_global_provider_voice(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][0]["bullets"][0]["text"] = "I closed the big cleanup work for Compass."
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h"),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


def test_build_standup_brief_normalizes_joined_fact_id_tokens(tmp_path: Path) -> None:
    valid = _valid_provider_result()
    valid["sections"][1]["bullets"][1]["fact_ids"] = ["F-003','F-004"]
    provider = _FakeProvider(valid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"
    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    assert current_execution["bullets"][1]["fact_ids"] == ["F-003", "F-004"]


def test_build_standup_brief_strips_inline_fact_id_leakage_from_visible_text(tmp_path: Path) -> None:
    valid = _valid_provider_result()
    valid["sections"][0]["bullets"][0] = {
        "voice": "operator",
        "text": "Verified milestone closeout landed for Compass. (F-001)",
        "fact_ids": ["F-001"],
    }
    valid["sections"][1]["bullets"][1] = {
        "voice": "operator",
        "text": "Updated Compass narrative to capture implementation intent. F-003",
        "fact_ids": ["F-003"],
    }
    provider = _FakeProvider(valid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    completed = next(section for section in brief["sections"] if section["key"] == "completed")
    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    assert completed["bullets"][0]["text"] == "Verified milestone closeout landed for Compass."
    assert current_execution["bullets"][1]["text"] == "Updated Compass narrative to capture implementation intent."
    assert completed["bullets"][0]["fact_ids"] == ["F-001"]
    assert current_execution["bullets"][1]["fact_ids"] == ["F-003"]


def test_build_standup_brief_requires_freshness_evidence_when_packet_is_stale(tmp_path: Path) -> None:
    provider = _FakeProvider(_valid_provider_result())

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(freshness_bucket="stale", include_freshness_fact=True),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"
    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    assert current_execution["bullets"][-1]["fact_ids"] == ["F-009"]
    assert "Execution proof is getting stale." in current_execution["bullets"][-1]["text"]


def test_build_standup_brief_accepts_freshness_evidence_when_packet_is_stale(tmp_path: Path) -> None:
    valid = _valid_provider_result()
    valid["sections"][1]["bullets"] = [
        {
            "voice": "executive",
            "text": "The live brief is still where Compass has to earn trust, because it can flatten the work behind it into dashboard prose.",
            "fact_ids": ["F-002"],
        },
        {
            "voice": "operator",
            "text": "Right now the clearest signal is that the narrative layer was updated to capture implementation intent.",
            "fact_ids": ["F-003"],
        },
        {
            "voice": "operator",
            "text": "Execution proof is getting stale. The next checkpoint has to refresh proof before momentum claims stay credible.",
            "fact_ids": ["F-009"],
        },
    ]
    provider = _FakeProvider(valid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(freshness_bucket="stale", include_freshness_fact=True),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"


def test_build_standup_brief_rejects_overused_stock_leads(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][1]["bullets"][0]["text"] = "B-025 is where attention stays because Compass can drift stale."
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


def test_build_standup_brief_repairs_one_invalid_provider_response(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][4]["bullets"][0]["text"] = "src/odylith/runtime/surfaces/render_compass_dashboard.py is the risk to watch."
    provider = _QueuedProvider([invalid, _valid_provider_result()])

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"
    assert provider.calls == 2
    assert provider.requests[1].schema_name == "compass_standup_brief_repair"


def test_build_standup_brief_uses_exact_fingerprint_cache(tmp_path: Path) -> None:
    initial_provider = _FakeProvider(_valid_provider_result())
    current_iso = _now_utc_iso()
    first = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=current_iso,
        config=_reasoning_config(),
        provider=initial_provider,
    )
    assert first["status"] == "ready"
    assert initial_provider.calls == 1

    cached_provider = _FakeProvider(None)
    second = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=cached_provider,
    )

    assert second["status"] == "ready"
    assert second["source"] == "cache"
    assert cached_provider.calls == 0


def test_has_reusable_cached_brief_tracks_exact_reusable_entry(tmp_path: Path) -> None:
    provider = _FakeProvider(_valid_provider_result())
    packet = _fact_packet(window="48h", scope_mode="global", idea_id="")

    narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=provider,
    )

    assert narrator.has_reusable_cached_brief(repo_root=tmp_path, fact_packet=packet) is True
    assert narrator.has_reusable_cached_brief(
        repo_root=tmp_path,
        fact_packet=_set_fact_text(packet, kind="direction", text="A different 48h execution direction."),
    ) is False


def test_standup_brief_fingerprint_ignores_freshness_wording_drift() -> None:
    baseline = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")
    variant = _set_fact_text(
        baseline,
        kind="freshness",
        text=(
            "Freshness signal is stale: latest linked execution proof for Global is 17 minutes old, "
            "so another checkpoint should land before momentum claims stay credible."
        ),
    )

    assert narrator.standup_brief_fingerprint(fact_packet=baseline) == narrator.standup_brief_fingerprint(
        fact_packet=variant
    )


def test_standup_brief_fingerprint_ignores_freshness_marker_source_and_timestamp_drift() -> None:
    baseline = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")
    variant = json.loads(json.dumps(baseline))
    variant["summary"]["freshness"]["latest_evidence_utc"] = "2026-03-13T19:48:00Z"
    variant["summary"]["freshness"]["source"] = "event"

    assert narrator.standup_brief_fingerprint(fact_packet=baseline) == narrator.standup_brief_fingerprint(
        fact_packet=variant
    )


def test_standup_brief_fingerprint_changes_when_self_host_status_changes() -> None:
    baseline = _fact_packet(
        include_freshness_fact=True,
        scope_mode="global",
        idea_id="",
        window="24h",
        self_host={
            "repo_role": "product_repo",
            "posture": "pinned_release",
            "runtime_source": "pinned_runtime",
            "pinned_version": "0.1.4",
            "active_version": "0.1.4",
            "launcher_present": True,
            "release_eligible": True,
        },
    )
    variant = json.loads(json.dumps(baseline))
    variant["summary"]["self_host"]["active_version"] = "0.1.3"
    variant["summary"]["self_host"]["release_eligible"] = False

    assert narrator.standup_brief_fingerprint(fact_packet=baseline) != narrator.standup_brief_fingerprint(
        fact_packet=variant
    )


def test_provider_request_payload_uses_compact_fact_packet_view() -> None:
    packet = _fact_packet(
        include_freshness_fact=True,
        scope_mode="global",
        idea_id="",
        window="24h",
        self_host={
            "repo_role": "product_repo",
            "posture": "pinned_release",
            "runtime_source": "pinned_runtime",
            "pinned_version": "0.1.4",
            "active_version": "0.1.4",
            "launcher_present": True,
            "release_eligible": True,
        },
    )

    payload = narrator._provider_request_payload(fact_packet=packet)
    provider_packet = payload["fact_packet"]

    assert "facts" not in provider_packet
    assert provider_packet["summary"]["freshness_bucket"] == "recent"
    assert "latest_evidence_utc" not in provider_packet["summary"]
    assert "source" not in provider_packet["summary"]
    assert provider_packet["summary"]["self_host"] == {
        "repo_role": "product_repo",
        "posture": "pinned_release",
        "runtime_source": "pinned_runtime",
        "pinned_version": "0.1.4",
        "active_version": "0.1.4",
        "launcher_present": True,
        "release_eligible": True,
    }
    current_execution = next(
        section for section in provider_packet["sections"] if section["key"] == "current_execution"
    )
    assert len(current_execution["facts"]) <= 4
    assert current_execution["facts"][0]["id"] == "F-002"


def test_provider_request_payload_keeps_48h_in_same_live_voice_as_24h() -> None:
    payload = narrator._provider_request_payload(
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="48h")
    )

    assert payload["brief_contract"]["window_contract"] == {
        "window": "48h",
        "rule": (
            "Treat 48h as the same live standup voice as 24h. Zoom out on evidence, but do not switch into "
            "retrospective, wrap-up, or strategy-memo mode."
        ),
    }
    assert (
        "keep 24h and 48h in the same spoken maintainer register; only the evidence window widens"
        in payload["brief_contract"]["writing_contract"]["rules"]
    )


def test_provider_request_payload_is_smaller_than_raw_fact_packet_json() -> None:
    packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")

    payload = narrator._provider_request_payload(fact_packet=packet)

    raw_size = len(json.dumps(packet, sort_keys=True))
    compact_size = len(json.dumps(payload["fact_packet"], sort_keys=True))
    assert compact_size < raw_size


def test_build_standup_brief_reuses_exact_cache_when_only_freshness_wording_changes(tmp_path: Path) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded_packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=seeded_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded_provider.calls == 1

    cached_provider = _FakeProvider(None)
    updated_packet = _set_fact_text(
        seeded_packet,
        kind="freshness",
        text=(
            "Freshness signal is stale: latest linked execution proof for Global is 18 minutes old, "
            "so another checkpoint should land before momentum claims stay credible."
        ),
    )
    cached = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=updated_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=cached_provider,
    )

    assert cached["status"] == "ready"
    assert cached["source"] == "cache"
    assert cached["cache_mode"] == "exact"
    assert cached_provider.calls == 0


def test_build_standup_brief_reuses_runtime_snapshot_when_local_cache_is_missing(tmp_path: Path) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"

    runtime_dir = tmp_path / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text(
        json.dumps(
            {
                "standup_brief": {
                    "24h": seeded,
                    "48h": {
                        "status": "ready",
                        "source": "deterministic",
                        "fingerprint": "ignore-48h",
                        "generated_utc": _now_utc_iso(),
                        "sections": [],
                    },
                },
                "standup_brief_scoped": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    narrator.standup_brief_cache_path(repo_root=tmp_path).unlink()

    cached_provider = _FakeProvider(None)
    cached = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=cached_provider,
    )

    assert cached["status"] == "ready"
    assert cached["source"] == "cache"
    assert cached["cache_mode"] == "exact"
    assert cached_provider.calls == 0


def test_build_standup_brief_ignores_runtime_snapshot_from_older_brief_contract(tmp_path: Path) -> None:
    packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="48h")

    runtime_dir = tmp_path / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text(
        json.dumps(
            {
                "standup_brief": {
                    "48h": {
                        "status": "ready",
                        "source": "provider",
                        "fingerprint": narrator.standup_brief_fingerprint(fact_packet=packet),
                        "generated_utc": _now_utc_iso(),
                        "sections": _valid_provider_result()["sections"],
                        "evidence_lookup": {},
                    },
                },
                "standup_brief_scoped": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    provider = _FakeProvider(_valid_provider_result())
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"
    assert provider.calls == 1


def test_build_standup_brief_bypasses_expired_cache_entry(tmp_path: Path) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    first = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2020-01-01T00:00:00Z",
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert first["status"] == "ready"
    assert seeded_provider.calls == 1

    refreshed_provider = _FakeProvider(_valid_provider_result())
    second = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=refreshed_provider,
    )

    assert second["status"] == "ready"
    assert second["source"] == "provider"
    assert refreshed_provider.calls == 1


def test_build_standup_brief_reuses_cache_when_live_provider_is_deferred(tmp_path: Path) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"
    assert seeded_provider.calls == 1

    deferred_provider = _FakeProvider(None)
    cached = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=deferred_provider,
        allow_provider=False,
    )

    assert cached["status"] == "ready"
    assert cached["source"] == "cache"
    assert cached["cache_mode"] == "exact"
    assert deferred_provider.calls == 0


def test_build_standup_brief_can_bypass_exact_cache_for_explicit_live_refresh(tmp_path: Path) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"
    assert seeded_provider.calls == 1

    refreshed_provider = _FakeProvider(_valid_provider_result())
    refreshed = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=refreshed_provider,
        allow_provider=True,
        prefer_provider=True,
    )

    assert refreshed["status"] == "ready"
    assert refreshed["source"] == "provider"
    assert refreshed_provider.calls == 1


def test_build_standup_brief_full_refresh_can_fall_back_to_exact_current_packet_cache(tmp_path: Path) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"

    refreshed = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=_QueuedProvider([None, None]),
        allow_provider=True,
        prefer_provider=True,
        allow_cache_recovery=False,
        allow_deterministic_fallback=False,
    )

    assert refreshed["status"] == "ready"
    assert refreshed["source"] == "cache"
    assert refreshed["cache_mode"] == "exact"


def test_build_standup_brief_full_refresh_fails_closed_when_no_exact_cache_is_available(tmp_path: Path) -> None:
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(include_freshness_fact=True),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=_QueuedProvider([None, None]),
        allow_provider=True,
        prefer_provider=True,
        allow_cache_recovery=False,
        allow_deterministic_fallback=False,
    )

    assert brief["status"] == "unavailable"
    assert brief["source"] == "unavailable"
    assert brief["diagnostics"]["reason"] == "provider_empty"


def test_build_standup_brief_uses_current_deterministic_brief_when_provider_returns_empty_for_changed_packet(
    tmp_path: Path,
) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"

    fallback_provider = _QueuedProvider([None, None])
    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(include_freshness_fact=True),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=fallback_provider,
    )

    assert fallback["status"] == "ready"
    assert fallback["source"] == "deterministic"
    assert fallback["notice"]["reason"] == "provider_empty"
    assert fallback["notice"]["title"] == "Showing deterministic local brief"
    assert fallback_provider.calls == 2


def test_build_standup_brief_uses_current_deterministic_brief_when_live_provider_is_deferred_and_fingerprint_changes(
    tmp_path: Path,
) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"

    deferred_provider = _FakeProvider(None)
    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(include_freshness_fact=True),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=deferred_provider,
        allow_provider=False,
    )

    assert fallback["status"] == "ready"
    assert fallback["source"] == "deterministic"
    assert fallback["notice"]["reason"] == "provider_deferred"
    assert fallback["notice"]["title"] == "Showing deterministic local brief"
    assert deferred_provider.calls == 0


def test_build_standup_brief_does_not_reuse_cached_brief_when_global_self_host_posture_changes(
    tmp_path: Path,
) -> None:
    baseline_packet = _fact_packet(
        scope_mode="global",
        idea_id="",
        window="24h",
        self_host={
            "repo_role": "product_repo",
            "posture": "pinned_release",
            "runtime_source": "pinned_runtime",
            "pinned_version": "0.1.4",
            "active_version": "0.1.4",
            "launcher_present": True,
            "release_eligible": True,
        },
    )
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=baseline_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"

    changed_packet = json.loads(json.dumps(baseline_packet))
    changed_packet["summary"]["self_host"]["active_version"] = "0.1.3"
    changed_packet["summary"]["self_host"]["posture"] = "diverged_verified_version"
    changed_packet["summary"]["self_host"]["release_eligible"] = False

    assert narrator.standup_brief_fingerprint(fact_packet=baseline_packet) != narrator.standup_brief_fingerprint(
        fact_packet=changed_packet
    )

    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=changed_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    assert fallback["status"] == "ready"
    assert fallback["source"] == "deterministic"
    assert fallback["notice"]["reason"] == "provider_deferred"
    assert fallback["notice"]["title"] == "Showing deterministic local brief"


def test_build_standup_brief_does_not_reuse_cache_for_different_scope_or_window(tmp_path: Path) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"

    no_match = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(idea_id="B-202"),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )
    assert no_match["status"] == "ready"
    assert no_match["source"] == "deterministic"
    assert no_match["notice"]["reason"] == "provider_deferred"

    no_window_match = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", window="24h"),
        generated_utc=_now_utc_iso(),
        provider=None,
    )
    assert no_window_match["status"] == "ready"
    assert no_window_match["source"] == "deterministic"
    assert no_window_match["notice"]["reason"] == "provider_unavailable"


def test_build_standup_brief_does_not_reuse_stale_last_known_good_cache(tmp_path: Path) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2020-01-01T00:00:00Z",
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"

    stale_fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(include_freshness_fact=True),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    assert stale_fallback["status"] == "ready"
    assert stale_fallback["source"] == "deterministic"
    assert stale_fallback["notice"]["reason"] == "provider_deferred"
    assert stale_fallback["notice"]["title"] == "Showing deterministic local brief"


def test_build_standup_brief_uses_deterministic_brief_when_live_global_exact_cache_is_stale_and_provider_returns_empty(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    class _FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return cls(2026, 3, 22, 15, 30, 18, tzinfo=tz or dt.timezone.utc)

    monkeypatch.setattr(narrator.dt, "datetime", _FixedDateTime)

    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h", freshness_bucket="live"),
        generated_utc="2026-03-22T15:10:53Z",
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"

    fallback_provider = _QueuedProvider([None, None])
    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h", freshness_bucket="live"),
        generated_utc="2026-03-22T15:30:18Z",
        config=_reasoning_config(),
        provider=fallback_provider,
    )

    assert fallback["status"] == "ready"
    assert fallback["source"] == "deterministic"
    assert fallback["notice"]["reason"] == "provider_empty"
    assert fallback["notice"]["title"] == "Showing deterministic local brief"
    assert fallback_provider.calls == 2


def test_build_standup_brief_uses_deterministic_brief_when_recent_global_exact_cache_is_stale_and_provider_returns_empty(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    class _FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return cls(2026, 3, 22, 16, 10, 18, tzinfo=tz or dt.timezone.utc)

    monkeypatch.setattr(narrator.dt, "datetime", _FixedDateTime)

    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h", freshness_bucket="recent"),
        generated_utc="2026-03-22T15:10:53Z",
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"

    fallback_provider = _QueuedProvider([None, None])
    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h", freshness_bucket="recent"),
        generated_utc="2026-03-22T16:10:18Z",
        config=_reasoning_config(),
        provider=fallback_provider,
    )

    assert fallback["status"] == "ready"
    assert fallback["source"] == "deterministic"
    assert fallback["notice"]["reason"] == "provider_empty"
    assert fallback["notice"]["title"] == "Showing deterministic local brief"
    assert fallback_provider.calls == 2


def test_build_standup_brief_does_not_reuse_stale_global_window_cache_when_provider_returns_empty(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    class _FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return cls(2026, 3, 22, 16, 4, 57, tzinfo=tz or dt.timezone.utc)

    monkeypatch.setattr(narrator.dt, "datetime", _FixedDateTime)

    seeded_packet = _fact_packet(scope_mode="global", idea_id="", window="24h", freshness_bucket="live")
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=seeded_packet,
        generated_utc="2026-03-22T15:10:53Z",
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"

    stale_packet = _fact_packet(
        scope_mode="global",
        idea_id="",
        window="24h",
        freshness_bucket="live",
        include_freshness_fact=True,
    )
    assert narrator.standup_brief_fingerprint(fact_packet=seeded_packet) != narrator.standup_brief_fingerprint(
        fact_packet=stale_packet
    )

    fallback_provider = _QueuedProvider([None, None])
    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=stale_packet,
        generated_utc="2026-03-22T16:04:57Z",
        config=_reasoning_config(),
        provider=fallback_provider,
    )

    assert fallback["status"] == "ready"
    assert fallback["source"] == "deterministic"
    assert fallback["notice"]["reason"] == "provider_empty"
    assert fallback["notice"]["title"] == "Showing deterministic local brief"
    assert fallback_provider.calls == 2


def test_build_standup_brief_ignores_disabled_odylith_mode_when_provider_is_runnable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeProvider(_valid_provider_result())
    observed: dict[str, object] = {}

    def _provider_from_config(  # noqa: ANN001
        config,
        *,
        repo_root=None,
        require_auto_mode=True,
        allow_implicit_local_provider=False,
    ):
        observed["mode"] = config.mode
        observed["repo_root"] = repo_root
        observed["require_auto_mode"] = require_auto_mode
        observed["allow_implicit_local_provider"] = allow_implicit_local_provider
        return provider

    monkeypatch.setattr(odylith_reasoning, "provider_from_config", _provider_from_config)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=odylith_reasoning.ReasoningConfig(
            mode="disabled",
            provider="codex-cli",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_bin="codex",
            codex_reasoning_effort="high",
        ),
        provider=None,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"
    assert observed["require_auto_mode"] is False
    assert observed["allow_implicit_local_provider"] is True
    assert observed["mode"] == "disabled"
    assert provider.calls == 1


def test_build_standup_brief_uses_deterministic_fallback_when_no_provider_or_cache(tmp_path: Path) -> None:
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "provider_unavailable"
    assert "deterministic local brief" in brief["notice"]["message"].lower()
    assert brief["sections"]
    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    why_this_matters = next(section for section in brief["sections"] if section["key"] == "why_this_matters")
    assert current_execution["bullets"][0]["voice"] == "executive"
    assert any(str(item.get("voice", "")) == "operator" for item in current_execution["bullets"][1:])
    assert [item["voice"] for item in why_this_matters["bullets"]] == ["executive", "operator"]


def test_build_standup_brief_can_defer_live_provider_and_use_deterministic_fallback(tmp_path: Path) -> None:
    provider = _FakeProvider(_valid_provider_result())

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
        allow_provider=False,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "provider_deferred"
    assert brief["notice"]["title"] == "Showing deterministic local brief"
    assert "deferred during this refresh" in brief["notice"]["message"].lower()
    assert provider.calls == 0
