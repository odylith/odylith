from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.surfaces import compass_standup_brief_maintenance as maintenance


def _brief(*, source: str) -> dict[str, object]:
    return {
        "status": "ready",
        "source": source,
        "fingerprint": f"{source}-fingerprint",
        "generated_utc": "2026-04-09T00:00:00Z",
        "sections": [],
        "evidence_lookup": {},
    }


def _signal(*, rung: str, budget_class: str) -> dict[str, object]:
    return {
        "rung": rung,
        "budget_class": budget_class,
        "rank": int(str(rung).replace("R", "")),
    }


def test_enqueue_request_only_selects_active_scope_candidates(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    state_path = maintenance.maintenance_state_path(repo_root=repo_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "active_pid": 0,
                "entries": {
                    "scoped:24h:B-004": {
                        "fingerprint": "fp-B-004",
                        "status": "failed",
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        maintenance.compass_standup_brief_narrator,
        "has_reusable_cached_brief",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        maintenance.compass_standup_brief_narrator,
        "standup_brief_fingerprint",
        lambda *, fact_packet: f"fp-{fact_packet['scope_id']}",
    )

    request = maintenance.enqueue_request(
        repo_root=repo_root,
        generated_utc="2026-04-09T00:00:00Z",
        runtime_input_fingerprint="runtime-fp",
        global_fact_packets={"24h": {"scope_id": "global-24h"}},
        global_briefs={"24h": _brief(source="cache")},
        scoped_fact_packets={
            "24h": {
                "B-001": {"scope_id": "B-001"},
                "B-002": {"scope_id": "B-002"},
                "B-003": {"scope_id": "B-003"},
                "B-004": {"scope_id": "B-004"},
            }
        },
        scoped_briefs={
            "24h": {
                "B-001": _brief(source="deterministic"),
                "B-002": _brief(source="deterministic"),
                "B-003": _brief(source="cache"),
                "B-004": _brief(source="deterministic"),
            }
        },
        scope_signals={
            "24h": {
                "B-001": _signal(rung="R3", budget_class="fast_simple"),
                "B-002": _signal(rung="R1", budget_class="cache_only"),
                "B-003": _signal(rung="R3", budget_class="fast_simple"),
                "B-004": _signal(rung="R3", budget_class="fast_simple"),
            }
        },
    )

    assert request["global"] == {}
    assert sorted(request["scoped"]["24h"]) == ["B-001"]


def test_run_pending_request_warms_cache_and_patches_current_runtime(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    current_json_path = repo_root / "odylith/compass/runtime/current.v1.json"
    current_js_path = repo_root / "odylith/compass/runtime/current.v1.js"
    current_json_path.parent.mkdir(parents=True, exist_ok=True)
    current_payload = {
        "runtime_contract": {"input_fingerprint": "runtime-fp"},
        "standup_brief": {"24h": _brief(source="deterministic")},
        "standup_brief_scoped": {"24h": {"B-001": _brief(source="deterministic")}},
        "digest": {"24h": ["old global"]},
        "digest_scoped": {"24h": {"B-001": ["old scope"]}},
    }
    current_json_path.write_text(json.dumps(current_payload, indent=2) + "\n", encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")

    request_path = maintenance.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-09T00:00:00Z",
                "runtime_input_fingerprint": "runtime-fp",
                "global": {
                    "24h": {
                        "fingerprint": "global-fp",
                        "fact_packet": {"scope_id": "global-24h"},
                    }
                },
                "scoped": {
                    "24h": {
                        "B-001": {
                            "fingerprint": "scope-fp",
                            "fact_packet": {"scope_id": "B-001"},
                        }
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(
        maintenance.compass_standup_brief_narrator,
        "build_standup_brief",
        lambda **_kwargs: {
            **_brief(source="provider"),
            "sections": [
                {
                    "key": "completed",
                    "label": "Completed in this window",
                    "bullets": [{"text": "Global live narration.", "fact_ids": []}],
                }
            ],
        },
    )
    monkeypatch.setattr(
        maintenance.compass_standup_brief_batch,
        "build_scoped_briefs",
        lambda **_kwargs: {
            "B-001": {
                **_brief(source="provider"),
                "sections": [
                    {
                        "key": "current_execution",
                        "label": "Current execution",
                        "bullets": [{"text": "Scoped live narration.", "fact_ids": []}],
                    }
                ],
            }
        },
    )

    result = maintenance.run_pending_request(repo_root=repo_root)
    updated_payload = json.loads(current_json_path.read_text(encoding="utf-8"))
    state = json.loads(maintenance.maintenance_state_path(repo_root=repo_root).read_text(encoding="utf-8"))

    assert result["warmed"] == 2
    assert result["failed"] == 0
    assert result["patched_current_runtime"] is True
    assert updated_payload["standup_brief"]["24h"]["source"] == "provider"
    assert updated_payload["standup_brief_scoped"]["24h"]["B-001"]["source"] == "provider"
    assert any("Global live narration." in line for line in updated_payload["digest"]["24h"])
    assert any("Scoped live narration." in line for line in updated_payload["digest_scoped"]["24h"]["B-001"])
    assert state["entries"]["global:24h"]["status"] == "ready"
    assert state["entries"]["scoped:24h:B-001"]["status"] == "ready"


def test_maybe_spawn_background_starts_worker_once(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    request_path = maintenance.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps({"version": "v1", "global": {"24h": {}}}, indent=2) + "\n", encoding="utf-8")

    calls: list[list[str]] = []

    class _FakePopen:
        def __init__(self, command: list[str]) -> None:
            self.pid = 4321
            calls.append(command)

    monkeypatch.setattr(
        maintenance.subprocess,
        "Popen",
        lambda command, **_kwargs: _FakePopen(list(command)),
    )

    pid = maintenance.maybe_spawn_background(repo_root=repo_root)
    state = json.loads(maintenance.maintenance_state_path(repo_root=repo_root).read_text(encoding="utf-8"))

    assert pid == 4321
    assert calls and "odylith.runtime.surfaces.compass_standup_brief_maintenance" in calls[0]
    assert state["active_pid"] == 4321
