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


def test_provider_request_contract_emphasizes_maintainer_voice_without_a_dedicated_why_section() -> None:
    request = narrator._provider_request(fact_packet=_fact_packet())  # noqa: SLF001

    assert "strong maintainer speaking off notes" in request.system_prompt.lower()
    assert "plainspoken grounded maintainer narration" in request.system_prompt.lower()
    assert "use ordinary words another maintainer can understand on first read" in request.system_prompt.lower()
    assert "pressure point" in request.system_prompt.lower()
    assert "muddy" in request.system_prompt.lower()
    assert "window coverage spans" in request.system_prompt.lower()
    assert "carry consequence inside the relevant bullet" in request.system_prompt.lower()
    assert "write with stance" in request.system_prompt.lower()
    assert "do not write in first-person singular" in request.system_prompt.lower()
    assert "do not invent a house style or signature lead-in" in request.system_prompt.lower()
    assert "the real center of gravity is" in request.system_prompt.lower()
    assert "attention stays on" in request.system_prompt.lower()
    assert "self-host posture is clean" in request.system_prompt.lower()
    assert "next up is" in request.system_prompt.lower()
    assert "what matters here is" in request.system_prompt.lower()
    assert "over the last 48 hours" in request.system_prompt.lower()
    assert "the schedule still matters here" in request.system_prompt.lower()
    assert "if odylith is genuinely better" in request.system_prompt.lower()
    assert "work is now driving through" in request.system_prompt.lower()
    assert "there is a live-version split to keep in view" in request.system_prompt.lower()
    assert "release planning and execution are running together" in request.system_prompt.lower()
    assert "most of the movement this window sat in" in request.system_prompt.lower()
    assert "next step is" in request.system_prompt.lower()
    assert "the follow-on adds" in request.system_prompt.lower()
    assert "live self-host or install posture facts" in request.system_prompt.lower()
    assert request.model == "gpt-5.3-codex-spark"
    assert request.reasoning_effort == "low"
    assert request.timeout_seconds == 30.0

    assert "voice_values" not in request.prompt_payload["brief_contract"]
    assert all("required_voice_counts" not in section for section in request.prompt_payload["brief_contract"]["sections"])
    assert all(section["key"] != "why_this_matters" for section in request.prompt_payload["brief_contract"]["sections"])
    assert "maintainer-delivered standup" in " ".join(request.prompt_payload["brief_contract"]["writing_contract"]["rules"]).lower()
    rules = " ".join(request.prompt_payload["brief_contract"]["writing_contract"]["rules"]).lower()
    assert request.prompt_payload["brief_contract"]["writing_contract"]["target_style"] == "plainspoken grounded maintainer narration"
    assert "use ordinary words another maintainer can understand on first read" in rules
    assert "stay open and free-flowing without sounding polished, sloganized, or performed" in rules
    assert "if a sentence sounds like a dashboard trying to sound wise" in rules
    assert "vary sentence openings naturally" in rules
    assert "avoid recurring signature openings" in rules
    assert "state the unresolved problem directly" in rules
    assert "do not wrap priority in generic labels" in rules
    assert "do not lead bullets by restating long workstream titles" in rules
    assert "do not narrate self-host status with slogan language" in rules
    assert "carry customer need or operator consequence inside the relevant bullet" in rules
    assert "do not write bullets as 'next up is' or 'what matters here is'" in rules
    assert "do not keep reopening 48h bullets with 'over the last 48 hours'" in rules
    assert "do not use stock timing wrappers" in rules
    assert "do not use stagey metaphors or dashboard-wise abstractions" in rules
    assert "keep each bullet visibly tethered to the cited fact language" in rules
    assert "do not smooth the whole brief into the same polished claim-then-consequence sentence pattern" in rules
    assert request.prompt_payload["brief_contract"]["style_examples"]["completed"][0].startswith(
        "Two cleanup threads finally got put away."
    )
    assert request.prompt_payload["brief_contract"]["style_examples"]["current_execution_executive"][0].startswith(
        "Most of the work right now is in `B-022`."
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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"
    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    assert current_execution["bullets"][-1]["fact_ids"] == ["F-009"]
    assert "latest linked execution proof is more than a day old" in current_execution["bullets"][-1]["text"].lower()


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


def test_build_standup_brief_rejects_canned_release_summary_patterns(tmp_path: Path) -> None:
    provider = _FakeProvider(_canned_provider_result())

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="24h", scope_mode="global", idea_id=""),
        generated_utc="2026-04-08T21:32:50Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


def test_build_standup_brief_rejects_second_wave_cached_stock_framing(tmp_path: Path) -> None:
    provider = _FakeProvider(_second_wave_canned_provider_result())

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(window="48h", scope_mode="global", idea_id=""),
        generated_utc="2026-04-08T22:05:45Z",
        config=_reasoning_config(),
        provider=provider,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"
    assert brief["notice"]["reason"] == "validation_failed"


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


def test_validate_brief_response_injects_global_window_coverage_evidence_when_missing() -> None:
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
    assert current_execution["bullets"][-1]["text"] == "This window mostly ran through B-101, B-102, and B-103."
    assert current_execution["bullets"][-1]["fact_ids"] == ["F-010"]


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
        "keep 24h and 48h in the same spoken maintainer register; only the evidence window widens"
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


def test_build_standup_brief_reuses_validated_legacy_cache_entry(tmp_path: Path) -> None:
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
        allow_cache_recovery=False,
        allow_deterministic_fallback=False,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "cache"
    assert brief["cache_mode"] == "exact"
    assert provider.calls == 0
    migrated = narrator._load_cache(repo_root=tmp_path)["entries"]  # noqa: SLF001
    assert narrator.standup_brief_fingerprint(fact_packet=packet) in migrated


def test_build_standup_brief_reuses_context_matched_current_cache_entry(tmp_path: Path) -> None:
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
        allow_cache_recovery=False,
        allow_deterministic_fallback=False,
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
        allow_cache_recovery=False,
        allow_deterministic_fallback=False,
    )

    assert brief["status"] == "unavailable"


def test_build_standup_brief_can_return_composed_current_packet_fallback(tmp_path: Path) -> None:
    packet = _fact_packet(include_freshness_fact=True, scope_mode="scoped", idea_id="B-025", window="24h")
    provider = _FakeProvider(None)

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc=_now_utc_iso(),
        config=_reasoning_config(),
        provider=provider,
        allow_provider=True,
        allow_cache_recovery=False,
        allow_deterministic_fallback=False,
        allow_composed_fallback=True,
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "composed"
    assert "notice" not in brief


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


def test_build_standup_brief_reuses_current_cached_brief_when_provider_returns_empty_for_changed_packet(
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
    assert fallback["source"] == "cache"
    assert fallback["cache_mode"] == "exact"
    assert "notice" not in fallback
    assert fallback_provider.calls == 0


def test_build_standup_brief_reuses_current_cached_brief_when_live_provider_is_deferred_and_fingerprint_changes(
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
    assert fallback["source"] == "cache"
    assert fallback["cache_mode"] == "exact"
    assert "notice" not in fallback
    assert deferred_provider.calls == 0


def test_build_standup_brief_reuses_cached_global_brief_when_changed_self_host_state_does_not_alter_cited_facts(
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
    assert fallback["source"] == "cache"
    assert fallback["cache_mode"] == "exact"
    assert "notice" not in fallback


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


def test_build_standup_brief_reuses_global_cache_across_windows_when_sections_still_validate(tmp_path: Path) -> None:
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
    assert reused["status"] == "ready"
    assert reused["source"] == "cache"
    assert reused["cache_mode"] == "exact"


def test_build_standup_brief_reuses_scoped_cache_across_windows_when_scope_matches_and_no_freshness_guard(
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
    assert reused["status"] == "ready"
    assert reused["source"] == "cache"
    assert reused["cache_mode"] == "exact"


def test_build_standup_brief_salvages_cached_current_execution_section_when_one_bullet_goes_stale(
    tmp_path: Path,
) -> None:
    seeded_provider = _FakeProvider(_valid_provider_result())
    seeded = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_fact_packet(scope_mode="global", idea_id="", window="48h"),
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
        and value.get("context", {}).get("window") == "48h"
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

    assert reused["status"] == "ready"
    assert reused["source"] == "cache"
    assert reused["cache_mode"] == "exact"
    current_execution_bullets = reused["sections"][1]["bullets"]
    assert current_execution_bullets[1]["text"] == (
        "Updated Compass narrative to capture implementation intent."
    )


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


def test_build_standup_brief_reuses_live_global_cache_when_exact_cache_is_stale(
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
    assert "notice" not in fallback


def test_build_standup_brief_reuses_recent_live_global_cache_when_exact_cache_is_stale(
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
    assert "notice" not in fallback


def test_build_standup_brief_reuses_live_global_cache_when_window_fingerprint_changes_but_context_matches(
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

    fallback = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=stale_packet,
        generated_utc="2026-03-22T16:04:57Z",
        config=_reasoning_config(),
        provider=_QueuedProvider([None, None]),
    )

    assert fallback["status"] == "ready"
    assert fallback["source"] == "cache"
    assert fallback["cache_mode"] == "exact"
    assert "notice" not in fallback


def test_build_standup_brief_recovers_live_global_cache_from_legacy_epoch_when_provider_is_deferred(
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

    assert recovered["status"] == "ready"
    assert recovered["source"] == "cache"
    assert recovered["cache_mode"] == "exact"
    assert "notice" not in recovered


def test_build_standup_brief_rewrites_cached_global_window_coverage_phrase_when_reusing_live_cache(
    tmp_path: Path,
) -> None:
    packet = _fact_packet(scope_mode="global", idea_id="", window="24h", include_window_coverage_fact=True)
    cache_path = tmp_path / ".odylith" / "compass" / "standup-brief-cache.v22.json"
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
                        "generated_utc": "2026-04-09T15:00:00Z",
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

    assert brief["status"] == "ready"
    assert brief["source"] == "cache"
    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    assert current_execution["bullets"][-1]["text"] == "This window mostly ran through B-101, B-102, and B-103."


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
    assert len(current_execution["bullets"]) >= 2
    assert all("voice" not in item for item in current_execution["bullets"])
    assert all(section["key"] != "why_this_matters" for section in brief["sections"])


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
