from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import time

import pytest

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


class _FailingProvider:
    def __init__(self, *, provider_name: str, failure_code: str, failure_detail: str = "") -> None:
        self.provider_name = provider_name
        self.last_failure_code = ""
        self.last_failure_detail = ""
        self.calls = 0
        self._failure_code = failure_code
        self._failure_detail = failure_detail or failure_code

    def generate_structured(self, *, request):  # noqa: ANN001, ARG002
        self.calls += 1
        self.last_failure_code = self._failure_code
        self.last_failure_detail = self._failure_detail
        return None

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
    include_window_coverage_fact: bool = False,
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
    if include_window_coverage_fact:
        current_execution_facts.append(
            {
                "id": "F-010",
                "section_key": "current_execution",
                "voice_hint": "operator",
                "kind": "window_coverage",
                "text": "Work moved across 3 workstreams: B-101, B-102, and B-103.",
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
                "use_story": "Platform maintainers need clear execution status.",
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


def _median_ms(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[len(ordered) // 2]


def _assert_unavailable(brief: dict[str, object], *, reason: str) -> None:
    assert brief["status"] == "unavailable"
    assert brief["source"] == "unavailable"
    assert brief["diagnostics"]["reason"] == reason
    assert brief["sections"] == []


def _valid_provider_result() -> dict[str, object]:
    return {
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [
                    {
                        "text": "Compass milestone closeout landed. That takes one old loose end off the board.",
                        "fact_ids": ["F-001"],
                    },
                ],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "bullets": [
                    {
                        "text": "AI-first standup narration still needs care. If this drifts, Compass starts sounding like a dashboard again.",
                        "fact_ids": ["F-002"],
                    },
                    {
                        "text": "The latest narrative update kept the implementation intent visible instead of flattening it.",
                        "fact_ids": ["F-003"],
                    },
                    {
                        "text": "The packet still projects roughly 5 days, so this is not done yet.",
                        "fact_ids": ["F-004"],
                    },
                ],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "bullets": [
                    {
                        "text": "Next is landing the Compass renderer cleanly.",
                        "fact_ids": ["F-005"],
                    },
                ],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "bullets": [
                    {"text": "No hard blocker is surfaced right now.", "fact_ids": ["F-008"]},
                ],
            },
        ]
    }


def _canned_provider_result() -> dict[str, object]:
    payload = _valid_provider_result()
    payload["sections"][0]["bullets"][0]["text"] = (
        "No portfolio milestone closed in the last 24 hours, but the repo did switch onto runtime 0.1.9 and kept "
        "hosted install smoke compatible, so shipped-runtime proof did not drift."
    )
    payload["sections"][1]["bullets"] = [
        {
            "text": (
                "Release feedback closure, benchmark re-proof, and GA lane hardening is the live top lane because "
                "this is the moment to remove release exceptions before they calcify into normal practice."
            ),
            "fact_ids": ["F-002"],
        },
        {
            "text": (
                "The clearest field signal is the current repository running pinned runtime 0.1.9, which keeps "
                "proof tied to the shipped experience instead of a drifting local setup."
            ),
            "fact_ids": ["F-003"],
        },
        {
            "text": (
                "Self-host posture is clean: the product repo passed on pinned dogfood 0.1.10 with the launcher "
                "present, so live repo posture overrides any older release-story assumptions."
            ),
            "fact_ids": ["F-004"],
        },
    ]
    payload["sections"][2]["bullets"] = [
        {
            "text": (
                "Benchmark corpus expansion comes next because nearby truth surfaces still lag the README, and that "
                "mismatch weakens the benchmark story where maintainers expect the written contract to hold."
            ),
            "fact_ids": ["F-005"],
        },
        {
            "text": (
                "Then the corpus needs more developer-core local coding slices, which broadens frontier proof beyond "
                "the current sample and makes the benchmark harder to game."
            ),
            "fact_ids": ["F-005"],
        },
    ]
    return payload


def _second_wave_canned_provider_result() -> dict[str, object]:
    payload = _valid_provider_result()
    payload["sections"][0]["bullets"] = [
        {
            "text": (
                "Two lingering plan closeouts landed, clearing old ambiguity around lane boundaries, runtime, "
                "toolchain, and the starter surface before that debt hardens into operating habit."
            ),
            "fact_ids": ["F-001"],
        },
        {
            "text": (
                "This repo also moved onto runtime 0.1.9 at the pin, so the baseline shifted from planning to a "
                "concrete posture operators can verify."
            ),
            "fact_ids": ["F-001"],
        },
    ]
    payload["sections"][1]["bullets"] = [
        {
            "text": (
                "Release feedback closure, benchmark re-proof, and GA lane hardening is getting the work now because "
                "the evidence is freshest right after release, before temporary exceptions become normal."
            ),
            "fact_ids": ["F-002"],
        },
        {
            "text": (
                "Under that lane, the concrete proof thread is preparing the v0.1.8 release proof so the release "
                "story gets checked against evidence instead of narrative."
            ),
            "fact_ids": ["F-003"],
        },
        {
            "text": (
                "Cross-surface runtime freshness and browser hardening is moving alongside release work because UX "
                "drift and runtime drift tend to surface together for operators."
            ),
            "fact_ids": ["F-004"],
        },
    ]
    payload["sections"][2]["bullets"] = [
        {
            "text": (
                "Benchmark corpus expansion is next so nearby truth surfaces stop lagging the README; closing that "
                "gap keeps the benchmark story honest when people inspect the surrounding evidence."
            ),
            "fact_ids": ["F-005"],
        },
        {
            "text": (
                "More developer-core local coding slices follow after that, which broadens the tracked corpus and "
                "keeps frontier proof tied to real maintainer work."
            ),
            "fact_ids": ["F-005"],
        },
    ]
    return payload


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
    assert len(brief["sections"]) == 4
    first_bullet = brief["sections"][0]["bullets"][0]
    assert "voice" not in first_bullet
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


def test_build_standup_brief_fails_closed_after_repeated_empty_provider_replies(tmp_path: Path) -> None:
    provider = _QueuedProvider([None, None])

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="provider_empty")
    assert provider.calls == 2


def test_build_standup_brief_fails_closed_for_invalid_provider_output(tmp_path: Path) -> None:
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

    _assert_unavailable(brief, reason="validation_failed")


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

    _assert_unavailable(brief, reason="validation_failed")


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

    _assert_unavailable(brief, reason="validation_failed")


def test_provider_request_contract_emphasizes_maintainer_voice_without_a_dedicated_why_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        narrator,
        "_provider_request_profile",
        lambda config=None: odylith_reasoning.StructuredReasoningProfile(  # noqa: ARG005
            provider="claude-cli",
            model="",
            reasoning_effort="medium",
        ),
    )
    request = narrator._provider_request(fact_packet=_fact_packet())  # noqa: SLF001

    assert "thoughtful maintainer talking to a teammate" in request.system_prompt.lower()
    assert "friendly, calm, direct, simple, factual, precise, and human" in request.system_prompt.lower()
    assert "use short plain sentences first" in request.system_prompt.lower()
    assert "stagey metaphor" in request.system_prompt.lower()
    assert "most of the work here was in" in request.system_prompt.lower()
    assert "x and y are still moving together" in request.system_prompt.lower()
    assert "x is there because" in request.system_prompt.lower()
    assert "celebrate real wins with restraint" in request.system_prompt.lower()
    assert "steady and reassuring without softening the truth" in request.system_prompt.lower()
    assert "do not force workstream roll calls just to prove coverage" in request.system_prompt.lower()
    assert "do not sound like a dashboard, status bot, executive memo" in request.system_prompt.lower()
    assert "do not print raw fact ids in prose" in request.system_prompt.lower()
    assert "x is there because" in request.system_prompt.lower()
    assert "over the last 48 hours" in request.system_prompt.lower()
    assert request.model == ""
    assert request.reasoning_effort == "medium"
    assert request.timeout_seconds == 60.0

    assert "voice_values" not in request.prompt_payload["brief_contract"]
    assert all("required_voice_counts" not in section for section in request.prompt_payload["brief_contract"]["sections"])
    assert all(section["key"] != "why_this_matters" for section in request.prompt_payload["brief_contract"]["sections"])
    rules = " ".join(request.prompt_payload["brief_contract"]["writing_contract"]["rules"]).lower()
    assert request.prompt_payload["brief_contract"]["writing_contract"]["target_style"] == "friendly grounded maintainer narration"
    assert "thoughtful maintainer talking to a teammate" in rules
    assert "celebrate real wins with restraint" in rules
    assert "steady and reassuring without hiding the truth" in rules
    assert "use ordinary words another maintainer can understand on first read" in rules
    assert "if a tired maintainer would have to reread the sentence" in rules
    assert "vary sentence openings naturally" in rules
    assert "avoid recurring signature openings" in rules
    assert "state the unresolved problem directly" in rules
    assert "instead of forcing a workstream roll call" in rules
    assert "do not lead bullets by restating long workstream titles" in rules
    assert "carry consequence inside the relevant bullet" in rules
    assert "do not write bullets as 'next up is', 'what matters here is', 'most of the work here was in'" in rules
    assert "do not keep reopening bullets with repeated 'over the last 48 hours'" in rules
    assert "do not use stock timing wrappers, rhetorical tests, stagey metaphors, or dashboard-wise abstractions" in rules
    assert "keep each bullet visibly tethered to the cited fact language" in rules
    assert "do not smooth the whole brief into the same polished claim-then-consequence sentence pattern" in rules
    assert request.prompt_payload["brief_contract"]["style_examples"]["celebration"][0].startswith(
        "Good one to get over the line:"
    )
    assert request.prompt_payload["brief_contract"]["style_examples"]["reassurance"][0].startswith(
        "Small but real reassurance:"
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

    _assert_unavailable(brief, reason="validation_failed")


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
        "text": "Verified milestone closeout landed for Compass. (F-001)",
        "fact_ids": ["F-001"],
    }
    valid["sections"][1]["bullets"][1] = {
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

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_accepts_freshness_evidence_when_packet_is_stale(tmp_path: Path) -> None:
    valid = _valid_provider_result()
    valid["sections"][1]["bullets"] = [
        {
            "text": "Compass standup narration is still the live problem. AI-first standup narration can still collapse into dashboard prose.",
            "fact_ids": ["F-002"],
        },
        {
            "text": "Updated Compass narrative to capture implementation intent is still the clearest proof point.",
            "fact_ids": ["F-003"],
        },
        {
            "text": "Latest linked execution proof is more than a day old, so a new checkpoint is needed before momentum claims stay credible.",
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

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_attention_now_priority_wrapper(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][1]["bullets"][0]["text"] = (
        "Release feedback closure and GA lane hardening are getting the attention now because the evidence is still fresh."
    )
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="24h", scope_mode="global", idea_id=""),
        generated_utc="2026-04-08T21:32:50Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_canned_release_summary_patterns(tmp_path: Path) -> None:
    provider = _FakeProvider(_canned_provider_result())

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="24h", scope_mode="global", idea_id=""),
        generated_utc="2026-04-08T21:32:50Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_second_wave_cached_stock_framing(tmp_path: Path) -> None:
    provider = _FakeProvider(_second_wave_canned_provider_result())

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="48h", scope_mode="global", idea_id=""),
        generated_utc="2026-04-08T22:05:45Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_repeated_polished_cadence_even_with_fact_overlap(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][0]["bullets"][0]["text"] = "Compass closeout landed, so Compass finally has firmer footing."
    invalid["sections"][1]["bullets"][0]["text"] = (
        "Compass narration is still live, so Compass can still flatten the work into dashboard prose."
    )
    invalid["sections"][1]["bullets"][1]["text"] = (
        "Compass narrative was updated, so implementation intent is easier to see in the packet."
    )
    invalid["sections"][2]["bullets"][0]["text"] = "Compass renderer is next, so the surface can catch up."
    invalid["sections"][3]["bullets"][0]["text"] = (
        "The fallback risk is quiet, so operators can miss when the brief contract starts drifting."
    )

    provider = _FakeProvider(invalid)
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_internal_stock_templates(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][2]["bullets"][0]["text"] = (
        "Name the next concrete checkpoint so the lane stops reading like broad cleanup."
    )
    invalid["sections"][3]["bullets"][0]["text"] = (
        "Making that lane contract explicit across docs, guidance, specs, and Atlas would stop operators from guessing."
    )

    provider = _FakeProvider(invalid)
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_stagey_metaphor_voice(tmp_path: Path) -> None:
    packet = _set_fact_text(
        _fact_packet(),
        kind="plan_completion",
        text="First-turn bootstrap work closed and the reasoning-package boundary cleanup closed with it.",
    )
    invalid = _valid_provider_result()
    invalid["sections"][0]["bullets"][0]["text"] = (
        "First-turn bootstrap work closed and the reasoning-package boundary cleanup closed with it. The start of a turn is less muddy now."
    )
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc="2026-04-09T03:30:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_packet_bookkeeping_paraphrase(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][0]["bullets"][0]["text"] = (
        "Local Provider Autodetect and Compass AI Brief Recovery plans are confirmed complete. "
        "The repo now has those behaviors as known outcomes rather than pending items, which shrinks uncertainty for operator onboarding."
    )
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="24h", scope_mode="global", idea_id=""),
        generated_utc="2026-04-11T08:18:18Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_live_snapshot_stock_framing(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][0]["bullets"] = [
        {
            "text": "The repo saw concrete movement: the live Compass runtime snapshot was updated.",
            "fact_ids": ["F-001"],
        }
    ]
    invalid["sections"][1]["bullets"] = [
        {
            "text": (
                "The team is implementing a shared sync-scoped session so root path, profile, truth-root, "
                "canonical path tokens, and parsed idea specs are carried together."
            ),
            "fact_ids": ["F-002"],
        },
        {
            "text": "The updated live snapshot is still the same proof point, showing this is active execution rather than a stale report.",
            "fact_ids": ["F-003"],
        },
        {
            "text": "Primary lane timing is still projected at roughly 5 days, so this is a current, immediate track.",
            "fact_ids": ["F-004"],
        },
    ]
    invalid["sections"][2]["bullets"] = [
        {
            "text": "B-021 is next: land the Compass renderer cleanly.",
            "fact_ids": ["F-005"],
        }
    ]
    invalid["sections"][3]["bullets"] = [
        {
            "text": "A P1 blocker is still open: no hard blocker is surfaced right now.",
            "fact_ids": ["F-008"],
        }
    ]
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-04-12T16:30:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_dashboard_polish_phrasing(tmp_path: Path) -> None:
    packet = _fact_packet(scope_mode="global", idea_id="", include_window_coverage_fact=True)
    invalid = _valid_provider_result()
    invalid["sections"][1]["bullets"][0]["text"] = "Benchmark integrity is the thing under active implementation now."
    invalid["sections"][1]["bullets"][2]["text"] = (
        "Window coverage spans 3 touched workstreams, with the clearest movement around B-101, B-102, and B-103."
    )
    invalid["sections"][1]["bullets"][2]["fact_ids"] = ["F-010"]
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc="2026-04-09T03:35:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_window_coverage_and_corpus_stock_wrappers(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][1]["bullets"][2]["text"] = (
        "A lot moved in this window. B-063, B-060, B-001, B-005, B-020, and B-022 carried most of it."
    )
    invalid["sections"][1]["bullets"][2]["fact_ids"] = ["F-004"]
    invalid["sections"][2]["bullets"][0]["text"] = (
        "That push needs more developer-core local coding slices, so the next loop is extending corpus coverage before more GA hardening decisions settle as default operating practice."
    )
    invalid["sections"][2]["bullets"][0]["fact_ids"] = ["F-005"]
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="48h", scope_mode="global", idea_id=""),
        generated_utc="2026-04-09T17:25:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_stock_rollcall_linkage_and_existence_wrappers(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][1]["bullets"] = [
        {
            "text": "`B-025` is there because Compass can still drift between surfaces.",
            "fact_ids": ["F-002"],
        },
        {
            "text": "`B-025` and `B-071` are still moving together.",
            "fact_ids": ["F-003"],
        },
        {
            "text": "Most of the work here was in `B-025`, `B-071`, and `B-080`.",
            "fact_ids": ["F-010"],
        },
    ]
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="48h", scope_mode="global", idea_id="", include_window_coverage_fact=True),
        generated_utc="2026-04-10T21:19:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_local_developer_core_coding_slices_wrapper(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][2]["bullets"][0]["text"] = (
        "The next concrete unlock is more local developer-core coding slices inside B-021's frontier path."
    )
    invalid["sections"][2]["bullets"][0]["fact_ids"] = ["F-005"]
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="48h", scope_mode="global", idea_id=""),
        generated_utc="2026-04-09T17:29:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_newly_observed_release_summary_wrappers(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][1]["bullets"] = [
        {
            "text": (
                "Work is now driving through v0.1.10 release feedback and GA hardening in B-060. That work is "
                "happening while release memory is still fresh, so fixes are likely to land cleanly before they drift "
                "into tribal guidance."
            ),
            "fact_ids": ["F-002"],
        },
        {
            "text": (
                "There is a live-version split to keep in view: repo execution is on 0.1.9, while pinned dogfood "
                "self-host checks show 0.1.10 with the launcher present."
            ),
            "fact_ids": ["F-003"],
        },
        {
            "text": (
                "Release planning and execution are running together in B-063 and B-060, so release decisions are "
                "being shaped by proof as it happens rather than backfilled after the fact."
            ),
            "fact_ids": ["F-004"],
        },
        {
            "text": "Most of the movement this window sat in B-063, B-060, B-001, B-005, B-020, and B-022.",
            "fact_ids": ["F-010"],
        },
    ]
    invalid["sections"][2]["bullets"] = [
        {
            "text": (
                "Next step is B-021: pull Registry, Radar, Atlas, Compass, and benchmark docs back into the "
                "benchmark corpus so proof covers the broader maintainer surface instead of a narrow slice."
            ),
            "fact_ids": ["F-005"],
        },
        {
            "text": (
                "The follow-on adds more real maintainer coding work to corpus coverage through the CLI contract, "
                "which is intended to keep proof from being a paperwork pass."
            ),
            "fact_ids": ["F-005"],
        },
    ]
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="48h", scope_mode="global", idea_id="", include_window_coverage_fact=True),
        generated_utc="2026-04-09T18:42:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_managerial_next_move_wrapper(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][2]["bullets"][0]["text"] = "The next move is landing the Compass renderer cleanly."
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-04-09T03:37:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_rejects_real_footing_stagecraft(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][0]["bullets"][0]["text"] = "Compass closeout landed, and the proof finally has real footing."
    provider = _FakeProvider(invalid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-04-09T03:38:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    _assert_unavailable(brief, reason="validation_failed")


def test_build_standup_brief_accepts_plainspoken_grounded_maintainer_voice(tmp_path: Path) -> None:
    valid = {
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [
                    {
                        "text": "Compass milestone closeout landed. That takes one old loose end off the board.",
                        "fact_ids": ["F-001"],
                    },
                ],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "bullets": [
                    {
                        "text": "AI-first standup narration still needs care. If this drifts, Compass starts sounding like a dashboard again.",
                        "fact_ids": ["F-002"],
                    },
                    {
                        "text": "The latest narrative update kept the implementation intent visible instead of flattening it.",
                        "fact_ids": ["F-003"],
                    },
                    {
                        "text": "The packet still projects roughly 5 days, so this is not done yet.",
                        "fact_ids": ["F-004"],
                    },
                ],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "bullets": [
                    {
                        "text": "Next is landing the Compass renderer cleanly.",
                        "fact_ids": ["F-005"],
                    },
                ],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "bullets": [
                    {
                        "text": "No hard blocker is surfaced right now.",
                        "fact_ids": ["F-008"],
                    },
                ],
            },
        ]
    }
    provider = _FakeProvider(valid)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-04-09T03:40:00Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"


def test_build_standup_brief_skips_invalid_exact_cache_entry(tmp_path: Path) -> None:
    packet = _fact_packet(window="24h", scope_mode="global", idea_id="")
    fingerprint = narrator.standup_brief_fingerprint(fact_packet=packet)
    cache_path = narrator.standup_brief_cache_path(repo_root=tmp_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
                "entries": {
                    fingerprint: {
                        "generated_utc": _now_utc_iso(),
                        "sections": _canned_provider_result()["sections"],
                        "evidence_lookup": {},
                        "context": {
                            "window": "24h",
                            "scope_mode": "global",
                            "scope_id": "",
                        },
                    }
                },
            },
            indent=2,
        )
        + "\n",
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
    assert narrator.has_reusable_cached_brief(repo_root=tmp_path, fact_packet=packet) is True


def test_build_standup_brief_repairs_one_invalid_provider_response(tmp_path: Path) -> None:
    invalid = _valid_provider_result()
    invalid["sections"][3]["bullets"][0]["text"] = "src/odylith/runtime/surfaces/render_compass_dashboard.py is the risk to watch."
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
    assert "self_host" not in provider_packet["summary"]
    current_execution = next(
        section for section in provider_packet["sections"] if section["key"] == "current_execution"
    )
    assert len(current_execution["facts"]) <= 3
    assert current_execution["facts"][0]["id"] == "F-002"


def test_validate_brief_response_does_not_inject_global_window_coverage_rollcall_when_missing() -> None:
    packet = _fact_packet(scope_mode="global", idea_id="", include_window_coverage_fact=True)
    response = {
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [{"text": "Closed the Compass milestone.", "fact_ids": ["F-001"]}],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "bullets": [
                    {"text": "Compass is being steered around AI-first standup narration.", "fact_ids": ["F-002"]},
                    {"text": "Updated Compass narrative to capture implementation intent.", "fact_ids": ["F-003"]},
                    {"text": "Projected at roughly 5 days.", "fact_ids": ["F-004"]},
                ],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "bullets": [{"text": "Land implement compass renderer.", "fact_ids": ["F-005"]}],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "bullets": [{"text": "No critical blockers are currently surfaced.", "fact_ids": ["F-008"]}],
            },
        ]
    }

    _sections, errors = narrator._validate_brief_response(  # noqa: SLF001
        response=response,
        fact_packet=packet,
    )

    assert not errors
    current_execution = next(section for section in _sections if section["key"] == "current_execution")
    assert [bullet["text"] for bullet in current_execution["bullets"]] == [
        "Compass is being steered around AI-first standup narration.",
        "Updated Compass narrative to capture implementation intent.",
        "Projected at roughly 5 days.",
    ]


def test_validate_brief_response_accepts_fact_tethered_live_narration_without_false_fallback() -> None:
    packet = _fact_packet(scope_mode="global", idea_id="", window="48h", include_window_coverage_fact=True)
    response = {
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [
                    {
                        "text": "Verified Compass milestone landed, so the renderer stopped drifting between turns.",
                        "fact_ids": ["F-001"],
                    }
                ],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "bullets": [
                    {
                        "text": (
                            "Compass is being steered around AI-first standup narration because the brief still has "
                            "to sound like a maintainer, not a form."
                        ),
                        "fact_ids": ["F-002"],
                    },
                    {
                        "text": (
                            "Updated Compass narrative to capture implementation intent, which keeps the active path "
                            "anchored to the cited work."
                        ),
                        "fact_ids": ["F-003"],
                    },
                    {
                        "text": "Work moved across B-101, B-102, and B-103 in this window.",
                        "fact_ids": ["F-010"],
                    },
                ],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "bullets": [
                    {
                        "text": "Land implement compass renderer so the same brief contract survives the next refresh.",
                        "fact_ids": ["F-005"],
                    }
                ],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "bullets": [
                    {
                        "text": "No critical blockers are currently surfaced.",
                        "fact_ids": ["F-008"],
                    }
                ],
            },
        ]
    }

    _sections, errors = narrator._validate_brief_response(  # noqa: SLF001
        response=response,
        fact_packet=packet,
    )

    assert not errors


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
        "keep 24h and 48h in the same live spoken maintainer register; only the evidence window widens"
        in payload["brief_contract"]["writing_contract"]["rules"]
    )


def test_provider_request_payload_is_smaller_than_raw_fact_packet_json() -> None:
    packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")

    payload = narrator._provider_request_payload(fact_packet=packet)

    raw_size = len(json.dumps(packet, sort_keys=True))
    compact_size = len(json.dumps(payload["fact_packet"], sort_keys=True))
    assert compact_size < raw_size


def test_provider_empty_retry_uses_smaller_compact_second_request() -> None:
    packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")

    requests = narrator._provider_requests_for_empty_retry(fact_packet=packet)  # noqa: SLF001

    assert len(requests) == 2
    first_size = len(json.dumps(requests[0].prompt_payload["fact_packet"], sort_keys=True))
    second_size = len(json.dumps(requests[1].prompt_payload["fact_packet"], sort_keys=True))
    assert requests[0].schema_name == "compass_standup_brief"
    assert requests[1].schema_name == "compass_standup_brief_compact_retry"
    assert second_size < first_size


def test_build_standup_brief_retries_empty_provider_with_compact_request(tmp_path: Path) -> None:
    provider = _QueuedProvider([None, _valid_provider_result()])
    packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"
    assert provider.calls == 2
    assert provider.requests[0].schema_name == "compass_standup_brief"
    assert provider.requests[1].schema_name == "compass_standup_brief_compact_retry"


def test_build_standup_brief_does_not_reuse_non_exact_validated_legacy_cache_entry(tmp_path: Path) -> None:
    packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")
    legacy_path = tmp_path / ".odylith" / "compass" / "standup-brief-cache.v18.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(
        json.dumps(
            {
                "version": "v18",
                "entries": {
                    "legacy-entry": {
                        "generated_utc": "2026-04-08T21:00:00Z",
                        "sections": _valid_provider_result()["sections"],
                        "evidence_lookup": narrator._brief_evidence_lookup(fact_packet=packet),  # noqa: SLF001
                        "context": {"window": "24h", "scope_mode": "global", "scope_id": ""},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    provider = _FakeProvider(None)
    generated_utc = _now_utc_iso()
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=provider,
        allow_provider=False,
    )

    assert brief["status"] == "unavailable"
    assert brief["source"] == "unavailable"
    assert provider.calls == 0
    migrated = narrator._load_cache(repo_root=tmp_path)["entries"]  # noqa: SLF001
    assert narrator.standup_brief_fingerprint(fact_packet=packet) not in migrated


def test_build_standup_brief_reuses_exact_cache_when_packet_only_changes_nonwinner_fact(
    tmp_path: Path,
) -> None:
    packet = _fact_packet(scope_mode="scoped", idea_id="B-025", window="24h")
    generated_utc = _now_utc_iso()
    seed_provider = _FakeProvider(_valid_provider_result())
    narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=generated_utc,
        config=_reasoning_config(),
        provider=seed_provider,
    )
    changed_packet = json.loads(json.dumps(packet))
    changed_fact = {
        "id": "F-099",
        "section_key": "current_execution",
        "voice_hint": "operator",
        "kind": "signal",
        "text": "A new checkpoint fact arrived, but the earlier cited work is still current.",
    }
    changed_packet["facts"].append(changed_fact)
    changed_packet["sections"][1]["facts"].append(changed_fact)
    provider = _FakeProvider(None)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=changed_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=provider,
        allow_provider=False,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "cache"
    assert brief["cache_mode"] == "exact"
    assert provider.calls == 0
    migrated = narrator._load_cache(repo_root=tmp_path)["entries"]  # noqa: SLF001
    assert narrator.standup_brief_fingerprint(fact_packet=changed_packet) in migrated


def test_build_standup_brief_ignores_invalid_legacy_cache_entry(tmp_path: Path) -> None:
    packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")
    invalid_sections = _valid_provider_result()["sections"]
    invalid_sections[0]["bullets"][0]["fact_ids"] = ["F-999"]
    legacy_path = tmp_path / ".odylith" / "compass" / "standup-brief-cache.v18.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(
        json.dumps(
            {
                "version": "v18",
                "entries": {
                    "legacy-entry": {
                        "generated_utc": "2026-04-08T21:00:00Z",
                        "sections": invalid_sections,
                        "evidence_lookup": {},
                        "context": {"window": "24h", "scope_mode": "global", "scope_id": ""},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    provider = _FakeProvider(None)
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=provider,
        allow_provider=False,
    )

    assert brief["status"] == "unavailable"


def test_build_standup_brief_fails_closed_without_exact_cache_for_current_packet(tmp_path: Path) -> None:
    packet = _fact_packet(include_freshness_fact=True, scope_mode="scoped", idea_id="B-025", window="24h")
    provider = _FakeProvider(None)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=provider,
        allow_provider=True,
    )

    _assert_unavailable(brief, reason="provider_empty")


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
                        "status": "unavailable",
                        "source": "unavailable",
                        "fingerprint": "ignore-48h",
                        "generated_utc": "",
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


def test_build_standup_brief_ignores_runtime_snapshot_entry_that_fails_current_voice_validation(
    tmp_path: Path,
) -> None:
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
                        "schema_version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
                        "fingerprint": narrator.standup_brief_fingerprint(fact_packet=packet),
                        "generated_utc": _now_utc_iso(),
                        "sections": {
                            "sections": []
                        }["sections"],
                        "evidence_lookup": narrator._brief_evidence_lookup(fact_packet=packet),  # noqa: SLF001
                    },
                },
                "standup_brief_scoped": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    invalid_sections = _valid_provider_result()["sections"]
    invalid_sections[1]["bullets"][-1]["text"] = "A lot moved in this window. B-101, B-102, and B-103 carried most of it."
    payload = json.loads((runtime_dir / "current.v1.json").read_text(encoding="utf-8"))
    payload["standup_brief"]["48h"]["sections"] = invalid_sections
    (runtime_dir / "current.v1.json").write_text(
        json.dumps(payload, ensure_ascii=False),
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


def test_build_standup_brief_reuses_exact_cache_even_when_it_is_old(tmp_path: Path) -> None:
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
    assert second["source"] == "cache"
    assert second["cache_mode"] == "exact"
    assert refreshed_provider.calls == 0


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
    )

    assert brief["status"] == "unavailable"
    assert brief["source"] == "unavailable"
    assert brief["diagnostics"]["reason"] == "provider_empty"


def test_build_standup_brief_fails_closed_when_provider_returns_empty_for_changed_packet(
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

    changed_packet = _set_fact_text(
        _fact_packet(),
        kind="direction",
        text="Compass narration split again across surfaces and needs hard repair.",
    )
    fallback_provider = _QueuedProvider([None, None])
    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=changed_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=fallback_provider,
    )

    _assert_unavailable(fallback, reason="provider_empty")
    assert fallback_provider.calls == 2


def test_build_standup_brief_fails_closed_when_live_provider_is_deferred_and_fingerprint_changes(
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

    changed_packet = _set_fact_text(
        _fact_packet(),
        kind="direction",
        text="Compass narration split again across surfaces and needs hard repair.",
    )
    deferred_provider = _FakeProvider(None)
    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=changed_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=deferred_provider,
        allow_provider=False,
    )

    _assert_unavailable(fallback, reason="provider_deferred")
    assert deferred_provider.calls == 0


def test_build_standup_brief_fails_closed_when_global_packet_changes_even_if_old_copy_still_reads_ok(
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

    _assert_unavailable(fallback, reason="provider_deferred")


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
    _assert_unavailable(no_match, reason="provider_deferred")

    no_window_match = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", window="24h"),
        generated_utc=_now_utc_iso(),
        provider=None,
    )
    _assert_unavailable(no_window_match, reason="provider_unavailable")


def test_build_standup_brief_does_not_reuse_global_cache_across_windows(tmp_path: Path) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="48h"),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )

    reused = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h"),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    assert seeded["status"] == "ready"
    _assert_unavailable(reused, reason="provider_deferred")


def test_build_standup_brief_does_not_reuse_scoped_cache_across_windows(
    tmp_path: Path,
) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="scoped", idea_id="B-101", window="48h"),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )

    reused = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(
            scope_mode="scoped",
            idea_id="B-101",
            window="24h",
            include_freshness_fact=True,
        ),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    assert seeded["status"] == "ready"
    _assert_unavailable(reused, reason="provider_deferred")


def test_build_standup_brief_rejects_exact_cached_current_execution_section_when_one_bullet_goes_stale(
    tmp_path: Path,
) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h"),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"
    assert seeded["source"] == "provider"

    cache_path = narrator.standup_brief_cache_path(repo_root=tmp_path)
    cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    entries = cache_payload["entries"]
    entry = next(
        value
        for value in entries.values()
        if isinstance(value, dict)
        and value.get("context", {}).get("scope_mode") == "global"
        and value.get("context", {}).get("window") == "24h"
    )
    entry["sections"][1]["bullets"][1]["text"] = (
        "Current execution target is the local repo posture: runtime 0.1.9 with repo pin 0.1.9, which is what operators and tests should be measuring against today."
    )
    cache_path.write_text(json.dumps(cache_payload, indent=2) + "\n", encoding="utf-8")

    reused = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h"),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    _assert_unavailable(reused, reason="provider_deferred")


def test_build_standup_brief_rejects_cached_current_execution_when_freshness_evidence_is_missing(
    tmp_path: Path,
) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seed_packet = _fact_packet()
    target_packet = _fact_packet(freshness_bucket="aging", include_freshness_fact=True)
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=seed_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"

    cache_path = narrator.standup_brief_cache_path(repo_root=tmp_path)
    cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    seed_fingerprint = narrator.standup_brief_fingerprint(fact_packet=seed_packet)
    target_fingerprint = narrator.standup_brief_fingerprint(fact_packet=target_packet)
    entry = dict(cache_payload["entries"][seed_fingerprint])
    cache_payload["entries"][target_fingerprint] = entry
    entry["sections"][1]["bullets"] = [
        {
            "text": "Compass is being steered around AI-first standup narration.",
            "fact_ids": ["F-002"],
        },
        {
            "text": "Updated Compass narrative to capture implementation intent.",
            "fact_ids": ["F-003"],
        },
    ]
    cache_path.write_text(json.dumps(cache_payload, indent=2) + "\n", encoding="utf-8")

    reused = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=target_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    _assert_unavailable(reused, reason="provider_deferred")


def test_build_standup_brief_rejects_cached_risk_section_when_it_degrades_into_raw_counts(
    tmp_path: Path,
) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    target_packet = _fact_packet()
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=target_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"

    cache_path = narrator.standup_brief_cache_path(repo_root=tmp_path)
    cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    fingerprint = narrator.standup_brief_fingerprint(fact_packet=target_packet)
    entry = cache_payload["entries"][fingerprint]
    entry["sections"][3]["bullets"] = [
        {
            "text": "79 workstreams moved, 204 local changes landed, and 330 timeline events were recorded.",
            "fact_ids": ["F-008"],
        }
    ]
    cache_path.write_text(json.dumps(cache_payload, indent=2) + "\n", encoding="utf-8")

    reused = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=target_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    _assert_unavailable(reused, reason="provider_deferred")


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

    changed_packet = _set_fact_text(
        _fact_packet(),
        kind="direction",
        text="Compass narration split again across surfaces and needs hard repair.",
    )
    stale_fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=changed_packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    _assert_unavailable(stale_fallback, reason="provider_deferred")


def test_build_standup_brief_reuses_exact_global_cache_even_when_it_is_old(tmp_path: Path) -> None:
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

    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h", freshness_bucket="live"),
        generated_utc="2026-03-22T15:30:18Z",
        config=_reasoning_config(),
        provider=_QueuedProvider([None, None]),
    )

    assert fallback["status"] == "ready"
    assert fallback["source"] == "cache"
    assert fallback["cache_mode"] == "exact"


def test_build_standup_brief_reuses_recent_exact_global_cache_after_provider_empty(tmp_path: Path) -> None:
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

    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="24h", freshness_bucket="recent"),
        generated_utc="2026-03-22T16:10:18Z",
        config=_reasoning_config(),
        provider=_QueuedProvider([None, None]),
    )

    assert fallback["status"] == "ready"
    assert fallback["source"] == "cache"
    assert fallback["cache_mode"] == "exact"


def test_build_standup_brief_does_not_reuse_live_global_cache_when_window_fingerprint_changes(
    tmp_path: Path,
) -> None:
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

    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=stale_packet,
        generated_utc="2026-03-22T16:04:57Z",
        config=_reasoning_config(),
        provider=_QueuedProvider([None, None]),
    )

    _assert_unavailable(fallback, reason="provider_empty")


def test_build_standup_brief_does_not_recover_non_exact_legacy_global_cache_when_provider_is_deferred(
    tmp_path: Path,
) -> None:
    legacy_packet = _fact_packet(scope_mode="global", idea_id="", window="24h")
    legacy_fingerprint = narrator.standup_brief_fingerprint(fact_packet=legacy_packet)
    legacy_brief = narrator._ready_brief(  # noqa: SLF001
        source="provider",
        fingerprint=legacy_fingerprint,
        generated_utc="2026-04-09T15:00:00Z",
        sections=_valid_provider_result()["sections"],
        evidence_lookup=narrator._brief_evidence_lookup(fact_packet=legacy_packet),  # noqa: SLF001
    )
    legacy_cache_path = tmp_path / ".odylith" / "compass" / "standup-brief-cache.v21.json"
    legacy_cache_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_cache_path.write_text(
        json.dumps(
            {
                "version": "v21",
                "entries": {
                    legacy_fingerprint: {
                        "generated_utc": legacy_brief["generated_utc"],
                        "sections": legacy_brief["sections"],
                        "evidence_lookup": legacy_brief["evidence_lookup"],
                        "context": {"window": "24h", "scope_mode": "global", "scope_id": ""},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    recovered = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(
            scope_mode="global",
            idea_id="",
            window="24h",
            include_freshness_fact=True,
        ),
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    _assert_unavailable(recovered, reason="provider_deferred")


def test_build_standup_brief_rejects_cached_global_window_coverage_rollcall_when_reusing_live_cache(
    tmp_path: Path,
) -> None:
    packet = _fact_packet(scope_mode="global", idea_id="", window="24h", include_window_coverage_fact=True)
    cache_path = tmp_path / ".odylith" / "compass" / "standup-brief-cache.v23.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    sections = _valid_provider_result()["sections"]
    sections[1]["bullets"][-1] = {
        "text": "Most of the movement this window sat in B-101, B-102, and B-103.",
        "fact_ids": ["LEGACY-COVERAGE"],
    }
    cache_path.write_text(
        json.dumps(
            {
                "version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
                "entries": {
                    narrator.standup_brief_fingerprint(fact_packet=packet): {
                        "generated_utc": _now_utc_iso(),
                        "sections": sections,
                        "evidence_lookup": {
                            "LEGACY-COVERAGE": {
                                "text": "Work moved across 3 workstreams: B-101, B-102, and B-103.",
                                "section_key": "current_execution",
                                "kind": "window_coverage",
                            }
                        },
                        "context": {"window": "24h", "scope_mode": "global", "scope_id": ""},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    _assert_unavailable(brief, reason="provider_deferred")


def test_build_standup_brief_rejects_exact_cached_live_snapshot_stock_framing(
    tmp_path: Path,
) -> None:
    packet = _fact_packet(scope_mode="global", idea_id="", window="24h")
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=seeded_provider,
    )
    assert seeded["status"] == "ready"

    cache_path = narrator.standup_brief_cache_path(repo_root=tmp_path)
    cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    fingerprint = narrator.standup_brief_fingerprint(fact_packet=packet)
    entry = cache_payload["entries"][fingerprint]
    entry["sections"][0]["bullets"] = [
        {
            "text": "The repo saw concrete movement: the live Compass runtime snapshot was updated.",
            "fact_ids": ["F-001"],
        }
    ]
    entry["sections"][1]["bullets"] = [
        {
            "text": (
                "The team is implementing a shared sync-scoped session so root path, profile, truth-root, "
                "canonical path tokens, and parsed idea specs are carried together."
            ),
            "fact_ids": ["F-002"],
        },
        {
            "text": "The updated live snapshot is still the same proof point, showing this is active execution rather than a stale report.",
            "fact_ids": ["F-003"],
        },
        {
            "text": "Primary lane timing is still projected at roughly 5 days, so this is a current, immediate track.",
            "fact_ids": ["F-004"],
        },
    ]
    entry["sections"][2]["bullets"] = [
        {
            "text": "B-021 is next: land the Compass renderer cleanly.",
            "fact_ids": ["F-005"],
        }
    ]
    entry["sections"][3]["bullets"] = [
        {
            "text": "A P1 blocker is still open: no hard blocker is surfaced right now.",
            "fact_ids": ["F-008"],
        }
    ]
    cache_path.write_text(json.dumps(cache_payload, indent=2) + "\n", encoding="utf-8")

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    _assert_unavailable(brief, reason="provider_deferred")


def test_build_standup_brief_rejects_exact_cache_when_current_execution_workstream_anchor_drifted(
    tmp_path: Path,
) -> None:
    packet = {
        "version": "v1",
        "window": "24h",
        "scope": {"mode": "global", "idea_id": "", "label": "Global"},
        "summary": {
            "window_hours": 24,
            "freshness": {
                "bucket": "recent",
                "latest_evidence_utc": "2026-04-10T17:56:49Z",
                "source": "transaction",
            },
            "self_host": {
                "repo_role": "product_repo",
                "posture": "pinned_release",
                "runtime_source": "pinned_runtime",
                "pinned_version": "0.1.10",
                "active_version": "0.1.10",
                "launcher_present": True,
                "release_eligible": True,
            },
        },
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "facts": [
                    {
                        "id": "F-001",
                        "section_key": "completed",
                        "voice_hint": "operator",
                        "kind": "plan_completion",
                        "text": (
                            "Verified plan closeouts landed across the window: Context Engine Benchmark Family and "
                            "Grounding Quality Gates (B-068) -> odylith context engine benchmark family and grounding "
                            "quality gates; Cross-Host Contract Hardening and Codex-Claude Separation (B-069) -> "
                            "cross host contract hardening and codex claude separation."
                        ),
                    },
                    {
                        "id": "F-002",
                        "section_key": "completed",
                        "voice_hint": "operator",
                        "kind": "execution_highlight",
                        "text": "Most concrete portfolio movement: Harden Compass refresh and trust warning handling.",
                    },
                ],
            },
            {
                "key": "current_execution",
                "label": "Current execution",
                "facts": [
                    {
                        "id": "F-004",
                        "section_key": "current_execution",
                        "voice_hint": "operator",
                        "kind": "direction",
                        "text": (
                            "Cross-Surface Runtime Freshness and UX Browser Hardening (B-025) is the flagship lane "
                            "and is in active implementation because odylith cannot claim a live operating layer if "
                            "Compass can go stale or if the browser suite misses that regression."
                        ),
                        "workstreams": ["B-025"],
                    },
                    {
                        "id": "F-006",
                        "section_key": "current_execution",
                        "voice_hint": "operator",
                        "kind": "self_host_status",
                        "text": (
                            "Live self-host posture check passed: Odylith product repo is on pinned dogfood runtime "
                            "`0.1.10` with repo pin `0.1.10`, and the repo-local launcher is present."
                        ),
                    },
                    {
                        "id": "F-007",
                        "section_key": "current_execution",
                        "voice_hint": "operator",
                        "kind": "portfolio_posture",
                        "text": (
                            "Planning and implementation are running in parallel across active lanes, and some "
                            "implementation lanes still lack captured checklist progress Live focus lanes: "
                            "Cross-Surface Runtime Freshness and UX Browser Hardening (B-025), Scope Signal Ladder, "
                            "Cross-Surface Focus Gating, and Low-Signal Suppression (B-071)."
                        ),
                    },
                    {
                        "id": "F-008",
                        "section_key": "current_execution",
                        "voice_hint": "operator",
                        "kind": "window_coverage",
                        "text": "Most of the movement this window sat in B-025, B-071, B-048, B-060, B-068, and B-069.",
                        "workstreams": ["B-025", "B-071", "B-048", "B-060", "B-068", "B-069"],
                    },
                ],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "facts": [
                    {
                        "id": "F-010",
                        "section_key": "next_planned",
                        "voice_hint": "operator",
                        "kind": "forcing_function",
                        "text": (
                            "Immediate forcing function is Odylith Complex-Repo Benchmark Corpus Expansion and "
                            "Frontier Improvement (B-021): Bring Registry, Radar, Atlas, Compass, and the benchmark "
                            "docs back into."
                        ),
                    },
                    {
                        "id": "F-011",
                        "section_key": "next_planned",
                        "voice_hint": "operator",
                        "kind": "follow_on",
                        "text": (
                            "Then move Odylith Complex-Repo Benchmark Corpus Expansion and Frontier Improvement "
                            "(B-021): Add more real maintainer coding work to the tracked corpus: CLI contract."
                        ),
                    },
                ],
            },
            {
                "key": "risks_to_watch",
                "label": "Risks to watch",
                "facts": [
                    {
                        "id": "F-012",
                        "section_key": "risks_to_watch",
                        "voice_hint": "operator",
                        "kind": "risk_posture",
                        "text": (
                            "Primary watch item is execution coherence across Odylith Complex-Repo Benchmark Corpus "
                            "Expansion and Frontier Improvement (B-021) and Odylith Honest Benchmark Improvement, "
                            "Anti-Gaming Integrity, and Independent Proof (B-022) while shared dependencies remain open."
                        ),
                    }
                ],
            },
        ],
    }
    packet["facts"] = [fact for section in packet["sections"] for fact in section["facts"]]

    sections = [
        {
            "key": "completed",
            "label": "Completed in this window",
            "bullets": [
                {
                    "text": "Two benchmark hardening plans closed in this window, and Compass refresh handling got tightened with them.",
                    "fact_ids": ["F-001", "F-002"],
                }
            ],
        },
        {
            "key": "current_execution",
            "label": "Current execution",
            "bullets": [],
        },
        {
            "key": "next_planned",
            "label": "Next planned",
            "bullets": [
                {
                    "text": "Bring Registry, Radar, Atlas, Compass, and the benchmark docs back into line first.",
                    "fact_ids": ["F-010"],
                }
            ],
        },
        {
            "key": "risks_to_watch",
            "label": "Risks to watch",
            "bullets": [
                {
                    "text": "Execution coherence across B-021 and B-022 can still drift while the shared dependencies stay open.",
                    "fact_ids": ["F-012"],
                }
            ],
        },
    ]
    current_execution = next(section for section in sections if section["key"] == "current_execution")
    current_execution["bullets"] = [
        {
            "text": "`B-071` is there because each surface was still making its own guess about what mattered. This work puts one shared rule in place.",
            "fact_ids": ["F-004"],
        },
        {
            "text": "The product repo is on pinned dogfood runtime `0.1.10`. The release gate is using the same path maintainers are meant to use.",
            "fact_ids": ["F-006"],
        },
        {
            "text": "`B-071` and `B-025` are still moving together.",
            "fact_ids": ["F-007"],
        },
        {
            "text": "Most of the work here was in `B-071`, `B-025`, `B-080`, `B-021`, `B-060`, and `B-063`.",
            "fact_ids": ["F-008"],
        },
    ]

    cache_path = tmp_path / ".odylith" / "compass" / "standup-brief-cache.v23.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
                "entries": {
                    narrator.standup_brief_fingerprint(fact_packet=packet): {
                        "generated_utc": _now_utc_iso(),
                        "sections": sections,
                        "evidence_lookup": narrator._brief_evidence_lookup(fact_packet=packet),  # noqa: SLF001
                        "context": {"window": "24h", "scope_mode": "global", "scope_id": ""},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=None,
        allow_provider=False,
    )

    _assert_unavailable(brief, reason="provider_deferred")


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


def test_build_standup_brief_default_config_uses_auto_local_provider_contract(
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
        observed["provider"] = config.provider
        observed["repo_root"] = repo_root
        observed["require_auto_mode"] = require_auto_mode
        observed["allow_implicit_local_provider"] = allow_implicit_local_provider
        return provider

    monkeypatch.setattr(odylith_reasoning, "provider_from_config", _provider_from_config)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"
    assert observed["provider"] == "auto-local"
    assert observed["require_auto_mode"] is False
    assert observed["allow_implicit_local_provider"] is True
    assert narrator._default_compass_reasoning_config().codex_reasoning_effort == "medium"  # noqa: SLF001
    assert narrator._default_compass_reasoning_config().claude_reasoning_effort == "low"  # noqa: SLF001
    assert provider.calls == 1


def test_build_standup_brief_fails_over_to_alternate_local_provider_on_budget_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_provider = _FailingProvider(
        provider_name="codex-cli",
        failure_code="credits_exhausted",
        failure_detail="codex budget exhausted",
    )
    claude_provider = _FakeProvider(_valid_provider_result())

    def _provider_from_config(  # noqa: ANN001
        config,
        *,
        repo_root=None,
        require_auto_mode=True,
        allow_implicit_local_provider=False,
    ):
        assert repo_root == tmp_path
        assert require_auto_mode is False
        assert allow_implicit_local_provider is True
        if config.provider == "codex-cli":
            return codex_provider
        if config.provider == "claude-cli":
            return claude_provider
        return None

    monkeypatch.setattr(odylith_reasoning, "provider_from_config", _provider_from_config)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=3.0,
            codex_bin="codex",
            codex_reasoning_effort="medium",
            claude_bin="claude",
            claude_reasoning_effort="medium",
        ),
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "provider"
    assert brief["provider_decision"] == "provider_failover"
    assert codex_provider.calls == 2
    assert claude_provider.calls == 1


def test_unavailable_brief_for_budget_failure_names_provider_and_model() -> None:
    class _BudgetFailingProvider:
        provider_name = "codex-cli"
        last_failure_code = "credits_exhausted"
        last_failure_detail = "You've hit your usage limit for GPT-5.3-Codex-Spark."
        last_request_model = "gpt-5.3-codex-spark"
        last_request_reasoning_effort = "medium"

    brief = narrator.unavailable_brief_for_provider_failure(
        fingerprint="budget-hit",
        generated_utc="2026-04-14T17:28:00Z",
        provider=_BudgetFailingProvider(),
    )

    diagnostics = brief["diagnostics"]
    assert diagnostics["title"] == "Brief is waiting on Codex CLI budget"
    assert (
        diagnostics["message"]
        == "Compass could not warm this brief because the last narration attempt through Codex CLI using gpt-5.3-codex-spark may have hit a credit or budget limit. It will retry on backoff."
    )
    assert diagnostics["provider"] == "codex-cli"
    assert diagnostics["provider_model"] == "gpt-5.3-codex-spark"


def test_build_standup_brief_fails_closed_when_no_provider_or_cache(tmp_path: Path) -> None:
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
    )

    _assert_unavailable(brief, reason="provider_unavailable")


def test_build_standup_brief_fails_closed_when_live_provider_is_deferred_without_exact_cache(tmp_path: Path) -> None:
    provider = _FakeProvider(_valid_provider_result())

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(),
        generated_utc="2026-03-13T20:00:00Z",
        config=_reasoning_config(),
        provider=provider,
        allow_provider=False,
    )

    _assert_unavailable(brief, reason="provider_deferred")
    assert provider.calls == 0


def test_build_standup_brief_meets_hot_and_cold_latency_budgets(tmp_path: Path) -> None:
    packet = _fact_packet(include_freshness_fact=True, scope_mode="global", idea_id="", window="24h")
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=_FakeProvider(_valid_provider_result()),
    )
    assert seeded["source"] == "provider"

    hot_samples_ms: list[float] = []
    for _ in range(25):
        started = time.perf_counter()
        hot = narrator.build_standup_brief(
            repo_root=tmp_path,
            fact_packet=packet,
            generated_utc=_now_utc_iso(),
            config=_reasoning_config(),
            provider=None,
            allow_provider=False,
        )
        hot_samples_ms.append((time.perf_counter() - started) * 1000.0)
    assert hot["source"] == "cache"
    assert _median_ms(hot_samples_ms) < 50.0

    cold_root = tmp_path / "cold"
    cold_samples_ms: list[float] = []
    for _ in range(10):
        started = time.perf_counter()
        cold = narrator.build_standup_brief(
            repo_root=cold_root,
            fact_packet=packet,
            generated_utc=_now_utc_iso(),
            config=_reasoning_config(),
            provider=None,
            allow_provider=False,
        )
        cold_samples_ms.append((time.perf_counter() - started) * 1000.0)
    assert cold["source"] == "unavailable"
    assert _median_ms(cold_samples_ms) < 1000.0
