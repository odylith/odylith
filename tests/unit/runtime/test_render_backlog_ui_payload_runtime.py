from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import render_backlog_ui_payload_runtime as payload_runtime


def test_attach_delivery_scope_signals_annotates_entries(monkeypatch) -> None:
    class _FakeDeliveryPayloadRuntime:
        @staticmethod
        def load_delivery_surface_payload(**_kwargs):
            return {
                "workstreams": {
                    "B-040": {
                        "scope_signal": {
                            "rank": 1,
                            "rung": "R1",
                            "token": "background_trace",
                            "budget_class": "cache_only",
                            "promoted_default": False,
                        }
                    },
                    "B-071": {
                        "scope_signal": {
                            "rank": 4,
                            "rung": "R4",
                            "token": "actionable_priority",
                            "budget_class": "escalated_reasoning",
                            "promoted_default": True,
                        }
                    },
                }
            }

    monkeypatch.setattr(payload_runtime, "delivery_surface_payload_runtime", _FakeDeliveryPayloadRuntime())
    entries = [{"idea_id": "B-040"}, {"idea_id": "B-071"}]

    payload_runtime._attach_delivery_scope_signals(  # noqa: SLF001
        entries=entries,
        repo_root=Path("/tmp"),
        runtime_mode="standalone",
    )

    assert entries[0]["scope_signal_rank"] == 1
    assert entries[0]["scope_signal_budget_class"] == "cache_only"
    assert entries[0]["scope_signal_promoted_default"] is False
    assert entries[1]["scope_signal_rank"] == 4
    assert entries[1]["scope_signal_budget_class"] == "escalated_reasoning"
    assert entries[1]["scope_signal_promoted_default"] is True
