from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator


def _live_style_fact_packet() -> dict[str, object]:
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
                    "text": (
                        "Verified plan closeouts landed across the window: "
                        "Odylith Release Reset, Full-Stack Runtime Packaging, and Hosted-Asset Proof (B-005) -> "
                        "odylith canonical release version session and maintainer runbook; odylith managed runtime bundles "
                        "and supported platform contract plus follow-on closeout deliverables; "
                        "Odylith Product Self-Governance and Repo Boundary (B-001) -> "
                        "odylith product self governance and repo boundary."
                    ),
                },
                {
                    "id": "F-002",
                    "section_key": "completed",
                    "voice_hint": "operator",
                    "kind": "execution_highlight",
                    "text": "Most concrete portfolio movement: Workstream lineage merge update across 15 workstreams.",
                },
            ],
        },
        {
            "key": "current_execution",
            "label": "Current execution",
            "facts": [
                {
                    "id": "F-003",
                    "section_key": "current_execution",
                    "voice_hint": "executive",
                    "kind": "direction",
                    "text": (
                        "Odylith Lane Boundary, Runtime, and Toolchain Clarity (B-027) is the flagship lane and is "
                        "in active implementation because the current ambiguity shows up exactly where Odylith should be "
                        "strongest: maintainer execution in the product repo and consumer execution inside repos with "
                        "their own Python toolchains."
                    ),
                },
                {
                    "id": "F-004",
                    "section_key": "current_execution",
                    "voice_hint": "operator",
                    "kind": "signal",
                    "text": "Primary execution signal: Workstream lineage merge update across 15 workstreams.",
                },
                {
                    "id": "F-005",
                    "section_key": "current_execution",
                    "voice_hint": "operator",
                    "kind": "self_host_status",
                    "text": (
                        "Live install posture check: Odylith product repo reports repo role `product_repo`, posture "
                        "`detached_source_local`, runtime source `source_checkout`, active `source-local`, repo pin `0.1.7`, "
                        "launcher present, and release eligibility `no`."
                    ),
                },
                {
                    "id": "F-006",
                    "section_key": "current_execution",
                    "voice_hint": "operator",
                    "kind": "portfolio_posture",
                    "text": (
                        "Active lanes are converting plans into concrete implementation outcomes. Live focus lanes: "
                        "Odylith Lane Boundary, Runtime, and Toolchain Clarity (B-027), "
                        "Odylith Honest Benchmark Improvement, Anti-Gaming Integrity, and Independent Proof (B-022)."
                    ),
                },
            ],
        },
        {
            "key": "next_planned",
            "label": "Next planned",
            "facts": [
                {
                    "id": "F-007",
                    "section_key": "next_planned",
                    "voice_hint": "operator",
                    "kind": "forcing_function",
                    "text": (
                        "Immediate forcing function is Odylith Complex-Repo Benchmark Corpus Expansion and Frontier Improvement "
                        "(B-021): Neighboring benchmark truth surfaces still lag the README unless Registry,."
                    ),
                },
                {
                    "id": "F-008",
                    "section_key": "next_planned",
                    "voice_hint": "operator",
                    "kind": "follow_on",
                    "text": (
                        "Then move Odylith Complex-Repo Benchmark Corpus Expansion and Frontier Improvement (B-021): "
                        "The tracked corpus still needs more developer-core local coding slices:."
                    ),
                },
            ],
        },
        {
            "key": "risks_to_watch",
            "label": "Risks to watch",
            "facts": [
                {
                    "id": "F-011",
                    "section_key": "risks_to_watch",
                    "voice_hint": "operator",
                    "kind": "risk_posture",
                    "text": (
                        "Primary blocker is an open P1 bug: Registry live forensics miss source owned bundle mirror "
                        "component activity."
                    ),
                },
                {
                    "id": "F-012",
                    "section_key": "risks_to_watch",
                    "voice_hint": "operator",
                    "kind": "self_host_posture",
                    "text": (
                        "Odylith product repo is running detached source-local runtime `source-local`; release gating stays "
                        "blocked until the active runtime returns to repo pin `0.1.7`."
                    ),
                },
            ],
        },
    ]
    facts = []
    for section in sections:
        facts.extend(section["facts"])
    return {
        "version": "v1",
        "window": "24h",
        "scope": {
            "mode": "global",
            "idea_id": "",
            "label": "Global",
            "status": "mixed",
        },
        "summary": {
            "window_hours": 24,
            "freshness": {
                "bucket": "recent",
                "latest_evidence_utc": "2026-04-05T16:55:00Z",
                "source": "transaction",
            },
            "self_host": {
                "repo_role": "product_repo",
                "posture": "detached_source_local",
                "runtime_source": "source_checkout",
                "pinned_version": "0.1.7",
                "active_version": "source-local",
                "launcher_present": True,
                "release_eligible": False,
            },
            "storyline": {
                "flagship_lane": "Odylith Lane Boundary, Runtime, and Toolchain Clarity (B-027)",
                "direction": (
                    "the current ambiguity shows up exactly where Odylith should be strongest: maintainer execution in "
                    "the product repo and consumer execution inside repos with their own Python toolchains"
                ),
                "proof": "Workstream lineage merge update across 15 workstreams.",
                "forcing_function": (
                    "Odylith Complex-Repo Benchmark Corpus Expansion and Frontier Improvement (B-021): Neighboring benchmark "
                    "truth surfaces still lag the README unless Registry,."
                ),
                "use_story": (
                    "Odylith maintainers working in the product repo need a crisp distinction between pinned dogfood proof "
                    "and detached `source-local` source work."
                ),
                "architecture_consequence": (
                    "Publish one explicit lane matrix across docs, guidance, skills, specs, backlog truth, and Atlas."
                ),
                "watch_item": "Registry live forensics miss source owned bundle mirror component activity.",
            },
        },
        "sections": sections,
        "facts": facts,
    }


def test_deterministic_brief_uses_human_standup_register_for_live_style_packet(tmp_path: Path) -> None:
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_live_style_fact_packet(),
        generated_utc="2026-04-05T17:10:00Z",
    )

    assert brief["status"] == "ready"
    assert brief["source"] == "deterministic"

    completed = next(section for section in brief["sections"] if section["key"] == "completed")
    assert completed["bullets"][0]["text"].startswith("`B-005` finished release reset, full-stack runtime packaging, and hosted-asset proof;")
    assert "`B-005` finished release reset, full-stack runtime packaging, and hosted-asset proof" in completed["bullets"][0]["text"]
    assert "`B-001` finished product self-governance and repo boundary" in completed["bullets"][0]["text"]
    assert completed["bullets"][1]["text"] == (
        "Lineage was merged back together across 15 workstreams. The plans and links line up again."
    )

    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    assert current_execution["bullets"][0]["text"].startswith("`B-027` is still blocked on lane boundary clarity.")
    assert "like one runtime contract when they are not" in current_execution["bullets"][0]["text"]
    assert current_execution["bullets"][1]["text"].startswith("The product repo is still running detached `source-local`.")
    assert current_execution["bullets"][2]["text"] == (
        "`B-022` is right beside `B-027`. The proof work is close enough to tell us whether those changes actually hold."
    )

    next_planned = next(section for section in brief["sections"] if section["key"] == "next_planned")
    assert next_planned["bullets"][0]["text"] == (
        "`B-021` now needs to bring Registry and the other benchmark truth surfaces back into line with the README "
        "so the benchmark story stops drifting across surfaces."
    )
    assert next_planned["bullets"][1]["text"] == (
        "The corpus still needs more real maintainer coding work in it. Otherwise the benchmark gets cleaner without "
        "saying much about the work people actually do."
    )

    risks = next(section for section in brief["sections"] if section["key"] == "risks_to_watch")
    assert risks["bullets"][0]["text"] == (
        "The sharpest open risk is still the P1 around Registry live forensics missing source-owned bundle mirror "
        "component activity."
    )
    assert risks["bullets"][1]["text"] == (
        "Release gating stays constrained while the repo is running detached `source-local` instead of the pinned "
        "`0.1.7` runtime."
    )

    _validated_sections, errors = narrator._validate_brief_response(  # noqa: SLF001
        response={"sections": brief["sections"]},
        fact_packet=_live_style_fact_packet(),
    )
    assert not errors


def test_deterministic_brief_uses_distinct_48h_wording_when_fact_selection_is_similar(tmp_path: Path) -> None:
    packet_24h = _live_style_fact_packet()
    packet_48h = _live_style_fact_packet()
    packet_48h["window"] = "48h"
    packet_48h["summary"] = dict(packet_48h["summary"], window_hours=48)

    brief_24h = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet_24h,
        generated_utc="2026-04-05T17:10:00Z",
    )
    brief_48h = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet_48h,
        generated_utc="2026-04-05T17:10:00Z",
    )

    completed_24h = next(section for section in brief_24h["sections"] if section["key"] == "completed")
    completed_48h = next(section for section in brief_48h["sections"] if section["key"] == "completed")

    assert completed_24h["bullets"][1]["text"] != completed_48h["bullets"][1]["text"]
    assert completed_48h["bullets"][1]["text"] == (
        "Lineage was merged back together across 15 workstreams. The plans and links match again."
    )

    signal_packet_24h = _live_style_fact_packet()
    signal_packet_48h = _live_style_fact_packet()
    signal_packet_48h["window"] = "48h"
    signal_packet_48h["summary"] = dict(signal_packet_48h["summary"], window_hours=48)
    for packet in (signal_packet_24h, signal_packet_48h):
        packet["sections"][1]["facts"] = [
            fact for fact in packet["sections"][1]["facts"] if fact["kind"] in {"direction", "signal"}
        ]
    signal_brief_24h = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=signal_packet_24h,
        generated_utc="2026-04-05T17:10:00Z",
    )
    signal_brief_48h = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=signal_packet_48h,
        generated_utc="2026-04-05T17:10:00Z",
    )
    signal_current_24h = next(section for section in signal_brief_24h["sections"] if section["key"] == "current_execution")
    signal_current_48h = next(section for section in signal_brief_48h["sections"] if section["key"] == "current_execution")
    assert signal_current_24h["bullets"][1]["text"] != signal_current_48h["bullets"][1]["text"]
    assert signal_current_48h["bullets"][1]["text"].endswith("still reads the same when you widen the window to 48h.")


def test_deterministic_global_brief_lists_all_touched_window_workstreams(tmp_path: Path) -> None:
    packet = _live_style_fact_packet()
    packet["sections"][1]["facts"].append(
        {
            "id": "F-999",
            "section_key": "current_execution",
            "voice_hint": "operator",
            "kind": "window_coverage",
            "text": "Work moved across 3 workstreams: B-027, B-022, and B-021.",
        }
    )

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc="2026-04-05T17:10:00Z",
    )

    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    bullet_texts = [bullet["text"] for bullet in current_execution["bullets"]]
    assert any(
        text == "Work moved across 3 workstreams: B-027, B-022, and B-021."
        for text in bullet_texts
    )


def test_deterministic_brief_humanizes_scoped_runtime_lane_packet(tmp_path: Path) -> None:
    fact_packet = {
        "version": "v1",
        "window": "24h",
        "scope": {
            "mode": "scoped",
            "idea_id": "B-027",
            "label": "Odylith Lane Boundary, Runtime, and Toolchain Clarity (B-027)",
            "status": "implementation",
        },
        "summary": {
            "storyline": {
                "flagship_lane": "Odylith Lane Boundary, Runtime, and Toolchain Clarity (B-027)",
                "use_story": (
                    "Odylith maintainers working in the product repo and needing a crisp distinction between pinned "
                    "dogfood proof and detached `source-local` source work, odylith's runtime isolation contract is "
                    "correct, but the language around it is still spread across docs and easy to collapse into one false question."
                ),
                "architecture_consequence": (
                    "The architecture move is to publish one explicit lane matrix across constitutional docs, AGENTS "
                    "guidance, shared guidelines, shared and maintainer skills, component specs, backlog truth, and "
                    "Atlas diagrams, which gives operators a clearer contract and lower coordination risk."
                ),
            }
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
                        "kind": "execution_highlight",
                        "text": "Most concrete movement: Added product code + runtime tests across 2 workstreams.",
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
                        "text": (
                            "Odylith Lane Boundary, Runtime, and Toolchain Clarity (B-027) is in active implementation "
                            "because the current ambiguity shows up exactly where Odylith should be strongest: maintainer "
                            "execution in the product repo and consumer execution in repos with their own Python toolchains."
                        ),
                    },
                    {
                        "id": "F-003",
                        "section_key": "current_execution",
                        "voice_hint": "operator",
                        "kind": "checklist",
                        "text": (
                            "Plan posture: checklist progress is 6/64; execution checklist closure is underway while "
                            "implementation execution remains active."
                        ),
                    },
                    {
                        "id": "F-004",
                        "section_key": "current_execution",
                        "voice_hint": "operator",
                        "kind": "timeline",
                        "text": "Timeline signal: projected at roughly 11 days (high confidence).",
                    },
                ],
            },
            {
                "key": "next_planned",
                "label": "Next planned",
                "facts": [
                    {
                        "id": "F-005",
                        "section_key": "next_planned",
                        "voice_hint": "operator",
                        "kind": "fallback_next",
                        "text": (
                            "Immediate forcing function is to turn the next open checklist item into a named checkpoint "
                            "for Odylith Lane Boundary, Runtime, and Toolchain Clarity (B-027) so the current ambiguity "
                            "shows up exactly where Odylith should be strongest: maintainer execution in the product repo "
                            "and consumer execution in repos with their own Python toolchains."
                        ),
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
                        "text": (
                            "Primary watch item is closure discipline: 58 plan items remain open for Odylith Lane "
                            "Boundary, Runtime, and Toolchain Clarity (B-027)."
                        ),
                    }
                ],
            },
        ],
    }

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=fact_packet,
        generated_utc="2026-04-05T18:10:00Z",
    )

    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    assert current_execution["bullets"][1]["text"] == (
        "58 checklist items are still open."
    )
    assert current_execution["bullets"][2]["text"] == (
        "Projected at roughly 11 days (high confidence)."
    )

    next_planned = next(section for section in brief["sections"] if section["key"] == "next_planned")
    assert next_planned["bullets"][0]["text"] == (
        "The next open checklist item still needs a name so the lane boundary stops blurring maintainer and consumer execution."
    )

    risks = next(section for section in brief["sections"] if section["key"] == "risks_to_watch")
    assert risks["bullets"][0]["text"] == (
        "58 plan items remain open on `B-027`."
    )


def test_deterministic_brief_humanizes_scoped_benchmark_lane_packet(tmp_path: Path) -> None:
    fact_packet = {
        "version": "v1",
        "window": "24h",
        "scope": {
            "mode": "scoped",
            "idea_id": "B-021",
            "label": "Odylith Complex-Repo Benchmark Corpus Expansion and Frontier Improvement (B-021)",
            "status": "implementation",
        },
        "summary": {
            "storyline": {
                "flagship_lane": "Odylith Complex-Repo Benchmark Corpus Expansion and Frontier Improvement (B-021)",
                "use_story": (
                    "For - Primary: Odylith evaluators and maintainers who need the benchmark to reflect the real work "
                    "a serious coding agent performs in a complex governed repo, odylith's benchmark story is credible "
                    "and stronger than `odylith_off`, but the current published diagnostic report `74cbe36427f2c375` "
                    "and live proof report `926bfeab4e887ade` are both still on `hold`."
                ),
                "architecture_consequence": (
                    "The architecture move is to expand the corpus around these higher-signal developer shapes and bring "
                    "Registry truth surfaces back into line with the README, which gives operators a clearer contract and "
                    "lower coordination risk."
                ),
            }
        },
        "sections": [
            {
                "key": "next_planned",
                "label": "Next planned",
                "facts": [
                    {
                        "id": "F-001",
                        "section_key": "next_planned",
                        "voice_hint": "operator",
                        "kind": "forcing_function",
                        "text": (
                            "Immediate forcing function is Odylith Complex-Repo Benchmark Corpus Expansion and Frontier "
                            "Improvement (B-021): Neighboring benchmark truth surfaces still lag the README unless Registry,."
                        ),
                    },
                    {
                        "id": "F-002",
                        "section_key": "next_planned",
                        "voice_hint": "operator",
                        "kind": "follow_on",
                        "text": (
                            "Then move Odylith Complex-Repo Benchmark Corpus Expansion and Frontier Improvement (B-021): "
                            "The tracked corpus still needs more developer-core local coding slices:."
                        ),
                    },
                ],
            },
        ],
    }

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=fact_packet,
        generated_utc="2026-04-05T18:10:00Z",
    )

    next_planned = next(section for section in brief["sections"] if section["key"] == "next_planned")
    assert next_planned["bullets"][0]["text"] == (
        "Bring Registry and the other benchmark truth surfaces back into line with the README so the "
        "benchmark story stops drifting across surfaces."
    )
    assert next_planned["bullets"][1]["text"] == (
        "The corpus still needs more real maintainer coding work in it. Otherwise the benchmark gets cleaner without "
        "saying much about the work people actually do."
    )

    assert all(section["key"] != "why_this_matters" for section in brief["sections"])


def test_deterministic_brief_does_not_reuse_known_canned_fallback_phrases(tmp_path: Path) -> None:
    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_live_style_fact_packet(),
        generated_utc="2026-04-05T17:10:00Z",
    )

    prose = " ".join(
        bullet["text"]
        for section in brief["sections"]
        for bullet in section["bullets"]
    )

    assert "something concrete to steer against" not in prose
    assert "live posture and the release gate are aligned on the same path" not in prose
    assert "A lot moved in this window" not in prose
    assert "Most of the movement this window sat in" not in prose
    assert "A lot happened, but most of it came through" not in prose
    assert "is moving with it too" not in prose
    assert "already proved the cost of local heuristics" not in prose
    assert "It is clearer now which lanes are active again" not in prose
    assert "developer-core local coding slices" not in prose
    assert "local developer-core coding slices" not in prose
    assert "finished completed release members" not in prose


def test_deterministic_brief_rewrites_current_regression_phrases_into_plainer_copy(tmp_path: Path) -> None:
    packet = _live_style_fact_packet()
    packet["sections"][1]["facts"] = [
        {
            "id": "F-100",
            "section_key": "current_execution",
            "voice_hint": "executive",
            "kind": "direction",
            "text": (
                "Odylith Honest Benchmark Improvement, Anti-Gaming Integrity, and Independent Proof (B-022) is the "
                "flagship lane and is in active implementation because once the benchmark starts shaping product claims, "
                "it must also resist the temptation to shape itself around those claims."
            ),
        },
        {
            "id": "F-101",
            "section_key": "current_execution",
            "voice_hint": "operator",
            "kind": "portfolio_posture",
            "text": (
                "Planning and implementation are running in parallel across active lanes. Live focus lanes: "
                "Odylith Honest Benchmark Improvement, Anti-Gaming Integrity, and Independent Proof (B-022), "
                "Odylith Product Self-Governance and Repo Boundary (B-001)."
            ),
        },
        {
            "id": "F-102",
            "section_key": "current_execution",
            "voice_hint": "operator",
            "kind": "window_coverage",
            "text": "Most of the movement this window sat in B-063, B-001, B-020, B-022, B-038, and B-062.",
        },
    ]
    packet["sections"][2]["facts"] = [
        {
            "id": "F-103",
            "section_key": "next_planned",
            "voice_hint": "operator",
            "kind": "forcing_function",
            "text": (
                "Immediate forcing function is Odylith Complex-Repo Benchmark Corpus Expansion and Frontier Improvement "
                "(B-021): Bring Registry, Radar, Atlas, Compass, and the benchmark docs back into."
            ),
        },
        {
            "id": "F-104",
            "section_key": "next_planned",
            "voice_hint": "operator",
            "kind": "follow_on",
            "text": (
                "Then move Odylith Complex-Repo Benchmark Corpus Expansion and Frontier Improvement (B-021): "
                "Add more real maintainer coding work to the tracked corpus: CLI contract."
            ),
        },
    ]
    packet["sections"][3]["facts"] = [
        {
            "id": "F-105",
            "section_key": "risks_to_watch",
            "voice_hint": "operator",
            "kind": "risk_posture",
            "text": "Primary blocker is an open P0 bug: Pinned dogfood proof benchmark can wedge mid corpus and block release proof.",
        }
    ]
    packet["facts"] = [fact for section in packet["sections"] for fact in section["facts"]]

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc="2026-04-09T18:40:00Z",
    )

    current_execution = next(section for section in brief["sections"] if section["key"] == "current_execution")
    assert current_execution["bullets"][0]["text"] == (
        "`B-022` is trying to make the benchmark hard to game. If it starts carrying product claims, it cannot "
        "quietly reshape itself to make those claims look better."
    )
    assert current_execution["bullets"][1]["text"] == (
        "`B-001` is right beside `B-022` too. The repo-boundary cleanup is being finished in the same pass."
    )
    assert current_execution["bullets"][2]["text"] == (
        "This window mostly ran through `B-063`, `B-001`, `B-020`, `B-022`, `B-038`, and `B-062`."
    )

    next_planned = next(section for section in brief["sections"] if section["key"] == "next_planned")
    assert next_planned["bullets"][0]["text"] == (
        "`B-021` now needs to bring Registry, Radar, Atlas, Compass, and the benchmark docs back into line with each other "
        "so the benchmark story stops drifting across surfaces."
    )
    assert next_planned["bullets"][1]["text"] == (
        "The corpus also needs more real maintainer coding work, starting with the CLI contract."
    )

    risks = next(section for section in brief["sections"] if section["key"] == "risks_to_watch")
    assert risks["bullets"][0]["text"] == (
        "The sharpest open risk is still the P0 around Pinned dogfood proof benchmark wedging mid-corpus and blocking release proof."
    )


def test_deterministic_brief_humanizes_artifact_refresh_and_execution_coherence_risk(tmp_path: Path) -> None:
    packet = _live_style_fact_packet()
    packet["sections"][0]["facts"] = [
        {
            "id": "F-200",
            "section_key": "completed",
            "voice_hint": "operator",
            "kind": "execution_highlight",
            "text": "Most concrete portfolio movement: Updated product code + odylith artifacts across 4 workstreams.",
        }
    ]
    packet["sections"][3]["facts"] = [
        {
            "id": "F-201",
            "section_key": "risks_to_watch",
            "voice_hint": "operator",
            "kind": "risk_posture",
            "text": (
                "Primary watch item is execution coherence across Odylith Complex-Repo Benchmark Corpus Expansion and "
                "Frontier Improvement (B-021) and Odylith Honest Benchmark Improvement, Anti-Gaming Integrity, and "
                "Independent Proof (B-022) while shared dependencies remain open."
            ),
        }
    ]
    packet["facts"] = [fact for section in packet["sections"] for fact in section["facts"]]

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=packet,
        generated_utc="2026-04-09T18:55:00Z",
    )

    completed = next(section for section in brief["sections"] if section["key"] == "completed")
    assert completed["bullets"][0]["text"] == "Product code and Odylith artifacts moved together this window."

    risks = next(section for section in brief["sections"] if section["key"] == "risks_to_watch")
    assert risks["bullets"][0]["text"] == (
        "`B-021` and `B-022` still need to move in step. If they drift, the proof gets cleaner faster than it gets "
        "more trustworthy."
    )
