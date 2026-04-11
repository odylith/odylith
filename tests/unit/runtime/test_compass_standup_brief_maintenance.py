from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from odylith.runtime.surfaces import compass_standup_brief_maintenance as maintenance


def _brief(*, source: str, status: str = "ready") -> dict[str, object]:
    return {
        "status": status,
        "source": source,
        "fingerprint": f"{source}-fingerprint",
        "generated_utc": "2026-04-09T00:00:00Z",
        "sections": [],
        "evidence_lookup": {},
    }


def _signal(*, rung: str, budget_class: str, verified_completion: bool = False) -> dict[str, object]:
    return {
        "rung": rung,
        "budget_class": budget_class,
        "rank": int(str(rung).replace("R", "")),
        "feature_vector": {
            "verified_completion": bool(verified_completion),
        },
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
                "B-001": _brief(source="unavailable", status="unavailable"),
                "B-002": _brief(source="unavailable", status="unavailable"),
                "B-003": _brief(source="cache"),
                "B-004": _brief(source="unavailable", status="unavailable"),
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
    assert sorted(request["scoped"]["24h"]) == ["B-001", "B-002", "B-004"]


def test_enqueue_request_skips_failed_candidate_until_retry_window_expires(tmp_path: Path, monkeypatch) -> None:
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
                        "attempt_count": 2,
                        "next_retry_utc": "2099-01-01T00:00:00Z",
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
        global_fact_packets={},
        global_briefs={},
        scoped_fact_packets={"24h": {"B-004": {"scope_id": "B-004"}}},
        scoped_briefs={"24h": {"B-004": _brief(source="unavailable", status="unavailable")}},
        scope_signals={"24h": {"B-004": _signal(rung="R3", budget_class="fast_simple")}},
    )

    assert request == {}


def test_enqueue_request_keeps_all_scoped_candidates_in_bundle_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
    state_path = maintenance.maintenance_state_path(repo_root=repo_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "active_pid": 0,
                "entries": {
                    "scoped:24h:B-006": {
                        "fingerprint": "fp-B-006",
                        "status": "failed",
                        "attempt_count": 2,
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
        global_fact_packets={},
        global_briefs={},
        scoped_fact_packets={
            "24h": {
                "B-001": {"scope_id": "B-001"},
                "B-002": {"scope_id": "B-002"},
                "B-003": {"scope_id": "B-003"},
                "B-004": {"scope_id": "B-004"},
                "B-005": {"scope_id": "B-005"},
                "B-006": {"scope_id": "B-006"},
            }
        },
        scoped_briefs={
            "24h": {
                scope_id: _brief(source="unavailable", status="unavailable")
                for scope_id in ("B-001", "B-002", "B-003", "B-004", "B-005", "B-006")
            }
        },
        scope_signals={
            "24h": {
                "B-001": _signal(rung="R3", budget_class="fast_simple"),
                "B-002": _signal(rung="R3", budget_class="fast_simple"),
                "B-003": _signal(rung="R3", budget_class="fast_simple"),
                "B-004": _signal(rung="R3", budget_class="fast_simple"),
                "B-005": _signal(rung="R3", budget_class="fast_simple"),
                "B-006": _signal(rung="R1", budget_class="fast_simple"),
            }
        },
    )

    assert list(request["scoped"]["24h"]) == ["B-001", "B-002", "B-003", "B-004", "B-005", "B-006"]


def test_enqueue_request_preserves_scope_order_for_bundle_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
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
        global_fact_packets={},
        global_briefs={},
        scoped_fact_packets={
            "24h": {
                "B-001": {"scope_id": "B-001"},
                "B-012": {"scope_id": "B-012"},
                "B-025": {"scope_id": "B-025"},
                "B-048": {"scope_id": "B-048"},
                "B-063": {"scope_id": "B-063"},
            }
        },
        scoped_briefs={
            "24h": {
                scope_id: _brief(source="unavailable", status="unavailable")
                for scope_id in ("B-001", "B-012", "B-025", "B-048", "B-063")
            }
        },
        scope_signals={
            "24h": {
                "B-001": _signal(rung="R3", budget_class="fast_simple"),
                "B-012": _signal(rung="R3", budget_class="fast_simple", verified_completion=True),
                "B-025": _signal(rung="R3", budget_class="fast_simple"),
                "B-048": _signal(rung="R3", budget_class="fast_simple"),
                "B-063": _signal(rung="R3", budget_class="fast_simple"),
            }
        },
    )

    assert list(request["scoped"]["24h"]) == ["B-001", "B-012", "B-025", "B-048", "B-063"]


def test_run_pending_request_warms_cache_and_patches_current_runtime(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    current_json_path = repo_root / "odylith/compass/runtime/current.v1.json"
    current_js_path = repo_root / "odylith/compass/runtime/current.v1.js"
    current_json_path.parent.mkdir(parents=True, exist_ok=True)
    current_payload = {
        "runtime_contract": {"input_fingerprint": "runtime-fp"},
        "standup_brief": {"24h": _brief(source="unavailable", status="unavailable")},
        "standup_brief_scoped": {"24h": {"B-001": _brief(source="unavailable", status="unavailable")}},
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
        maintenance.compass_standup_brief_batch,
        "build_brief_bundle",
        lambda **_kwargs: {
            "global": {
                "24h": {
                    **_brief(source="provider"),
                    "sections": [
                        {
                            "key": "completed",
                            "label": "Completed in this window",
                            "bullets": [{"text": "Global live narration.", "fact_ids": []}],
                        }
                    ],
                }
            },
            "scoped": {
                "24h": {
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
                }
            },
        },
    )

    result = maintenance.run_pending_request(repo_root=repo_root)
    updated_payload = json.loads(current_json_path.read_text(encoding="utf-8"))
    state = json.loads(maintenance.maintenance_state_path(repo_root=repo_root).read_text(encoding="utf-8"))

    assert result["warmed"] == 2
    assert result["failed"] == 0
    assert result["patched_current_runtime"] is True
    assert result["request_retained"] is False
    assert updated_payload["standup_brief"]["24h"]["source"] == "provider"
    assert updated_payload["standup_brief_scoped"]["24h"]["B-001"]["source"] == "provider"
    assert any("Global live narration." in line for line in updated_payload["digest"]["24h"])
    assert any("Scoped live narration." in line for line in updated_payload["digest_scoped"]["24h"]["B-001"])
    assert state["entries"]["global:24h"]["status"] == "ready"
    assert state["entries"]["scoped:24h:B-001"]["status"] == "ready"
    assert not request_path.exists()


def test_run_pending_request_failed_scoped_result_sets_retry_backoff(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    request_path = maintenance.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-09T00:00:00Z",
                "runtime_input_fingerprint": "runtime-fp",
                "scoped": {
                    "24h": {
                        "B-021": {
                            "fingerprint": "scope-fp",
                            "fact_packet": {"scope_id": "B-021"},
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
        maintenance.compass_standup_brief_batch,
        "build_brief_bundle",
        lambda **_kwargs: {"global": {}, "scoped": {}},
    )

    result = maintenance.run_pending_request(repo_root=repo_root)
    state = json.loads(maintenance.maintenance_state_path(repo_root=repo_root).read_text(encoding="utf-8"))
    entry = state["entries"]["scoped:24h:B-021"]
    retained_request = json.loads(request_path.read_text(encoding="utf-8"))

    assert result["warmed"] == 0
    assert result["failed"] == 1
    assert result["request_retained"] is True
    assert result["next_retry_utc"]
    assert entry["status"] == "failed"
    assert entry["source"] == "unavailable"
    assert entry["attempt_count"] == 1
    assert retained_request["scoped"]["24h"]["B-021"]["fingerprint"] == "scope-fp"
    retry_dt = dt.datetime.fromisoformat(entry["next_retry_utc"].replace("Z", "+00:00"))
    attempted_dt = dt.datetime.fromisoformat(entry["attempted_utc"].replace("Z", "+00:00"))
    assert retry_dt > attempted_dt


def test_pending_request_delay_seconds_waits_until_retry_window(tmp_path: Path) -> None:
    state_entries = {
        "scoped:24h:B-021": {
            "fingerprint": "scope-fp",
            "status": "failed",
            "next_retry_utc": "2099-01-01T00:05:00Z",
        }
    }
    request = {
        "version": "v1",
        "generated_utc": "2026-04-09T00:00:00Z",
        "runtime_input_fingerprint": "runtime-fp",
        "scoped": {
            "24h": {
                "B-021": {
                    "fingerprint": "scope-fp",
                    "fact_packet": {"scope_id": "B-021"},
                }
            }
        },
    }

    delay = maintenance._pending_request_delay_seconds(  # noqa: SLF001
        request=request,
        state_entries=state_entries,
    )

    assert delay is not None
    assert delay > 0


def test_pending_request_payload_keeps_all_unresolved_scoped_entries() -> None:
    request = {
        "version": "v1",
        "generated_utc": "2026-04-09T00:00:00Z",
        "runtime_input_fingerprint": "runtime-fp",
        "scoped": {
            "24h": {
                "B-001": {
                    "fingerprint": "fp-B-001",
                    "fact_packet": {"scope_id": "B-001"},
                },
                "B-002": {
                    "fingerprint": "fp-B-002",
                    "fact_packet": {"scope_id": "B-002"},
                },
                "B-003": {
                    "fingerprint": "fp-B-003",
                    "fact_packet": {"scope_id": "B-003"},
                },
                "B-004": {
                    "fingerprint": "fp-B-004",
                    "fact_packet": {"scope_id": "B-004"},
                },
                "B-005": {
                    "fingerprint": "fp-B-005",
                    "fact_packet": {"scope_id": "B-005"},
                },
                "B-006": {
                    "fingerprint": "fp-B-006",
                    "fact_packet": {"scope_id": "B-006"},
                },
            }
        },
    }
    state_entries = {
        "scoped:24h:B-006": {
            "fingerprint": "stale-B-006",
            "status": "failed",
            "attempt_count": 2,
        }
    }

    payload = maintenance._pending_request_payload(  # noqa: SLF001
        request=request,
        state_entries=state_entries,
    )

    assert list(payload["scoped"]["24h"]) == ["B-001", "B-002", "B-003", "B-004", "B-005", "B-006"]


def test_failure_brief_for_fact_packet_uses_matching_state_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    state_path = maintenance.maintenance_state_path(repo_root=repo_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "active_pid": 0,
                "entries": {
                    "scoped:24h:B-012": {
                        "fingerprint": "scope-fp",
                        "status": "failed",
                        "source": "",
                        "attempted_utc": "2026-04-11T02:12:02Z",
                        "attempt_count": 3,
                        "next_retry_utc": "2026-04-11T04:12:02Z",
                        "diagnostics": {
                            "reason": "provider_error",
                            "title": "Standup brief provider failed",
                            "message": "Compass hit a narration provider error while warming this brief. Compass will retry on backoff.",
                            "provider_failure_code": "provider_error",
                        },
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
        "standup_brief_fingerprint",
        lambda **_kwargs: "scope-fp",
    )

    brief = maintenance.failure_brief_for_fact_packet(
        repo_root=repo_root,
        window_key="24h",
        scope_id="B-012",
        fact_packet={"scope": {"mode": "scoped"}},
        generated_utc="2026-04-11T03:08:33Z",
    )

    assert brief is not None
    assert brief["diagnostics"]["reason"] == "provider_error"
    assert brief["diagnostics"]["next_retry_utc"] == "2026-04-11T04:12:02Z"


@pytest.mark.parametrize(
    ("status", "source", "attempt_count", "failure_code", "failure_reason", "expected"),
    [
        ("failed", "unavailable", 1, "", "", 300),
        ("failed", "unavailable", 3, "", "", 1200),
        ("provider_unavailable", "none", 1, "", "", 1800),
        ("provider_unavailable", "none", 4, "", "", 14400),
        ("provider_unavailable", "none", 5, "", "", 21600),
        ("failed", "unavailable", 1, "credits_exhausted", "", 1800),
        ("failed", "unavailable", 1, "", "invalid_batch", 1800),
    ],
)
def test_retry_backoff_seconds_scales_and_caps(
    status: str,
    source: str,
    attempt_count: int,
    failure_code: str,
    failure_reason: str,
    expected: int,
) -> None:
    assert maintenance._retry_backoff_seconds(  # noqa: SLF001
        status=status,
        source=source,
        attempt_count=attempt_count,
        failure_code=failure_code,
        failure_reason=failure_reason,
    ) == expected


def test_run_pending_request_records_provider_failure_diagnostics_and_patches_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
    current_json_path = repo_root / "odylith/compass/runtime/current.v1.json"
    current_js_path = repo_root / "odylith/compass/runtime/current.v1.js"
    current_json_path.parent.mkdir(parents=True, exist_ok=True)
    current_json_path.write_text(
        json.dumps(
            {
                "runtime_contract": {"input_fingerprint": "runtime-fp"},
                "standup_brief": {},
                "standup_brief_scoped": {
                    "24h": {
                        "B-021": {
                            **_brief(source="unavailable", status="unavailable"),
                            "diagnostics": {"reason": "provider_deferred"},
                        }
                    }
                },
                "digest": {},
                "digest_scoped": {"24h": {"B-021": []}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")

    request_path = maintenance.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-09T00:00:00Z",
                "runtime_input_fingerprint": "runtime-fp",
                "scoped": {
                    "24h": {
                        "B-021": {
                            "fingerprint": "scope-fp",
                            "fact_packet": {"scope_id": "B-021"},
                        }
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    class _FakeProvider:
        last_failure_code = "credits_exhausted"
        last_failure_detail = "insufficient_quota: out of credits"

    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: _FakeProvider())
    monkeypatch.setattr(
        maintenance.compass_standup_brief_batch,
        "build_brief_bundle",
        lambda **_kwargs: {"global": {}, "scoped": {}},
    )

    result = maintenance.run_pending_request(repo_root=repo_root)
    state = json.loads(maintenance.maintenance_state_path(repo_root=repo_root).read_text(encoding="utf-8"))
    payload = json.loads(current_json_path.read_text(encoding="utf-8"))
    entry = state["entries"]["scoped:24h:B-021"]
    brief = payload["standup_brief_scoped"]["24h"]["B-021"]

    assert result["failed"] == 1
    assert entry["status"] == "failed"
    assert entry["diagnostics"]["provider_failure_code"] == "credits_exhausted"
    assert "credits" in entry["diagnostics"]["provider_failure_detail"].lower()
    assert brief["diagnostics"]["reason"] == "credits_exhausted"
    assert brief["diagnostics"]["provider_failure_code"] == "credits_exhausted"
    assert "provider budget" in brief["diagnostics"]["title"].lower()
    assert brief["diagnostics"]["next_retry_utc"] == entry["next_retry_utc"]


def test_run_pending_request_records_global_provider_unavailable_and_patches_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
    current_json_path = repo_root / "odylith/compass/runtime/current.v1.json"
    current_js_path = repo_root / "odylith/compass/runtime/current.v1.js"
    current_json_path.parent.mkdir(parents=True, exist_ok=True)
    current_json_path.write_text(
        json.dumps(
            {
                "runtime_contract": {"input_fingerprint": "runtime-fp"},
                "standup_brief": {
                    "24h": {
                        **_brief(source="unavailable", status="unavailable"),
                        "diagnostics": {"reason": "provider_deferred"},
                    }
                },
                "standup_brief_scoped": {},
                "digest": {"24h": []},
                "digest_scoped": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
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
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: None)

    result = maintenance.run_pending_request(repo_root=repo_root)
    state = json.loads(maintenance.maintenance_state_path(repo_root=repo_root).read_text(encoding="utf-8"))
    payload = json.loads(current_json_path.read_text(encoding="utf-8"))
    entry = state["entries"]["global:24h"]
    brief = payload["standup_brief"]["24h"]

    assert result["failed"] == 1
    assert result["request_retained"] is True
    assert entry["status"] == "provider_unavailable"
    assert entry["source"] == "none"
    assert entry["diagnostics"]["provider_failure_code"] == "provider_unavailable"
    assert brief["diagnostics"]["reason"] == "provider_unavailable"
    assert brief["diagnostics"]["provider_failure_code"] == "provider_unavailable"
    assert "provider unavailable" in brief["diagnostics"]["title"].lower()
    assert brief["diagnostics"]["next_retry_utc"] == entry["next_retry_utc"]


def test_stamp_request_runtime_input_fingerprint_patches_current_runtime_from_existing_failure_state(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    current_json_path = repo_root / "odylith/compass/runtime/current.v1.json"
    current_js_path = repo_root / "odylith/compass/runtime/current.v1.js"
    current_json_path.parent.mkdir(parents=True, exist_ok=True)
    current_json_path.write_text(
        json.dumps(
            {
                "runtime_contract": {"input_fingerprint": "runtime-fp"},
                "standup_brief": {
                    "24h": {
                        **_brief(source="unavailable", status="unavailable"),
                        "diagnostics": {"reason": "provider_deferred"},
                    }
                },
                "standup_brief_scoped": {},
                "digest": {"24h": []},
                "digest_scoped": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")

    request_path = maintenance.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-09T00:00:00Z",
                "runtime_input_fingerprint": "",
                "global": {
                    "24h": {
                        "fingerprint": "global-fp",
                        "fact_packet": {"scope_id": "global-24h"},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    state_path = maintenance.maintenance_state_path(repo_root=repo_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "active_pid": 0,
                "entries": {
                    "global:24h": {
                        "fingerprint": "global-fp",
                        "status": "failed",
                        "source": "",
                        "attempted_utc": "2026-04-09T00:01:00Z",
                        "attempt_count": 1,
                        "next_retry_utc": "2026-04-09T00:21:00Z",
                        "diagnostics": {
                            "reason": "provider_error",
                            "title": "Brief unavailable right now",
                            "message": "The narration provider failed on the last attempt. Compass will retry on backoff.",
                            "provider": "codex-cli",
                            "provider_failure_code": "provider_error",
                            "provider_failure_detail": "Codex CLI exited with status 1.",
                        },
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    maintenance.stamp_request_runtime_input_fingerprint(
        repo_root=repo_root,
        runtime_input_fingerprint="runtime-fp",
    )

    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    runtime_payload = json.loads(current_json_path.read_text(encoding="utf-8"))

    assert request_payload["runtime_input_fingerprint"] == "runtime-fp"
    assert runtime_payload["standup_brief"]["24h"]["diagnostics"]["reason"] == "provider_error"
    assert runtime_payload["standup_brief"]["24h"]["diagnostics"]["provider_failure_code"] == "provider_error"
    assert runtime_payload["standup_brief"]["24h"]["diagnostics"]["next_retry_utc"] == "2026-04-09T00:21:00Z"


def test_run_pending_request_preserves_stamped_runtime_input_fingerprint_when_rewriting_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
    current_json_path = repo_root / "odylith/compass/runtime/current.v1.json"
    current_js_path = repo_root / "odylith/compass/runtime/current.v1.js"
    current_json_path.parent.mkdir(parents=True, exist_ok=True)
    current_json_path.write_text(
        json.dumps(
            {
                "runtime_contract": {"input_fingerprint": "runtime-fp"},
                "standup_brief": {},
                "standup_brief_scoped": {},
                "digest": {},
                "digest_scoped": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")

    request_path = maintenance.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-09T00:00:00Z",
                "runtime_input_fingerprint": "",
                "global": {
                    "24h": {
                        "fingerprint": "global-fp",
                        "fact_packet": {"scope_id": "global-24h"},
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

    def _fake_build_brief_bundle(**_kwargs):  # noqa: ANN003
        maintenance.stamp_request_runtime_input_fingerprint(
            repo_root=repo_root,
            runtime_input_fingerprint="runtime-fp",
        )
        return {"global": {}, "scoped": {}}

    monkeypatch.setattr(
        maintenance.compass_standup_brief_batch,
        "build_brief_bundle",
        _fake_build_brief_bundle,
    )

    result = maintenance.run_pending_request(repo_root=repo_root)
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))

    assert result["request_retained"] is True
    assert request_payload["runtime_input_fingerprint"] == "runtime-fp"


def test_maybe_spawn_background_starts_worker_once(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    request_path = maintenance.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "global": {
                    "24h": {
                        "fingerprint": "global-fp",
                        "fact_packet": {"scope_id": "global-24h"},
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

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


def test_maybe_spawn_background_ignores_empty_or_malformed_requests(tmp_path: Path) -> None:
    repo_root = tmp_path
    request_path = maintenance.maintenance_request_path(repo_root=repo_root)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "global": {"24h": {}},
                "scoped": {"24h": {"B-021": {"fingerprint": "", "fact_packet": {}}}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert maintenance.maybe_spawn_background(repo_root=repo_root) == 0
