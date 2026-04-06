from __future__ import annotations

from odylith.runtime.context_engine import tooling_context_retrieval as retrieval


def test_selected_guidance_chunks_uses_family_hint_for_family_specific_chunks() -> None:
    guidance_catalog = {
        "chunks": [
            {
                "chunk_id": "consumer-compat-guidance",
                "note_kind": "workflow",
                "title": "Consumer compatibility",
                "summary": "Stay on the named consumer profile surfaces.",
                "canonical_source": "odylith/agents-guidelines/SECURITY_AND_TRUST.md",
                "chunk_path": "odylith/agents-guidelines/SECURITY_AND_TRUST.md",
                "task_families": ["consumer_profile_compatibility"],
                "component_affinity": [],
                "workstreams": [],
                "path_refs": [],
                "path_prefixes": [],
            }
        ]
    }

    rows = retrieval.selected_guidance_chunks(
        {},
        guidance_catalog=guidance_catalog,
        packet_kind="impact",
        family_hint="consumer_profile_compatibility",
    )

    assert len(rows) == 1
    assert rows[0]["chunk_id"] == "consumer-compat-guidance"
    assert rows[0]["evidence_summary"]["matched_by"] == ["task_family"]


def test_selected_guidance_chunks_skips_family_specific_chunks_when_family_hint_does_not_match() -> None:
    guidance_catalog = {
        "chunks": [
            {
                "chunk_id": "consumer-compat-guidance",
                "note_kind": "workflow",
                "title": "Consumer compatibility",
                "summary": "Stay on the named consumer profile surfaces.",
                "canonical_source": "odylith/agents-guidelines/SECURITY_AND_TRUST.md",
                "chunk_path": "odylith/agents-guidelines/SECURITY_AND_TRUST.md",
                "task_families": ["consumer_profile_compatibility"],
                "component_affinity": [],
                "workstreams": [],
                "path_refs": [],
                "path_prefixes": [],
            }
        ]
    }

    rows = retrieval.selected_guidance_chunks(
        {},
        guidance_catalog=guidance_catalog,
        packet_kind="impact",
        family_hint="release_publication",
    )

    assert rows == []
