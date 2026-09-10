"""Select current or retained workstream context without replaying saved intent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_engine_store as store


def select_session_workstream(
    *,
    repo_root: Path,
    candidate_workstreams: Sequence[Mapping[str, Any]],
    changed_paths: Sequence[str],
    explicit_workstream: str,
    retained_workstream: str,
    hot_path: bool,
    impact_selection: Mapping[str, Any],
) -> dict[str, Any]:
    explicit = str(explicit_workstream or "").strip().upper()
    retained = str(retained_workstream or "").strip().upper() if not explicit and not hot_path else ""
    if hot_path and explicit:
        reason = f"Using explicit workstream override `{explicit}`."
        return {
            "state": "explicit",
            "reason": reason,
            "why_selected": reason,
            "selected_workstream": {"entity_id": explicit},
            "top_candidate": {"entity_id": explicit},
            "score_gap": None,
            "confidence": "explicit",
            "candidate_count": len(candidate_workstreams),
            "ambiguity_class": "explicit",
            "strong_candidate_count": 1,
            "competing_candidates": [],
        }
    if hot_path and impact_selection:
        return dict(impact_selection)
    try:
        connection = store._connect(repo_root)
    except RuntimeError:
        reason = (
            f"Explicit workstream `{explicit}` cannot resolve because runtime projections are unavailable."
            if explicit
            else "Runtime projections are unavailable for deterministic session routing."
        )
        return {
            "state": "none",
            "reason": reason,
            "why_selected": reason,
            "selected_workstream": {},
            "top_candidate": dict(candidate_workstreams[0]) if candidate_workstreams and not explicit else {},
            "score_gap": None,
            "confidence": "none",
            "candidate_count": len(candidate_workstreams),
            "ambiguity_class": "runtime_unavailable",
            "strong_candidate_count": sum(
                1 for row in candidate_workstreams
                if int(dict(row.get("evidence", {})).get("strong_signal_count", 0) or 0) > 0
            ),
            "competing_candidates": [dict(row) for row in candidate_workstreams[1:4]],
        }
    try:
        selection = store._workstream_selection(
            connection=connection,
            # Retention requires a current canonical lookup, not a cached candidate.
            candidates=[] if retained else candidate_workstreams,
            explicit_workstream=explicit or retained,
            judgment_hint=store._load_judgment_workstream_hint(repo_root=repo_root, changed_paths=changed_paths),
        )
    finally:
        connection.close()
    if retained:
        resolved = selection["state"] == "explicit"
        reason = (
            f"Retained session workstream `{retained}` resolves in current projections. "
            "This is context, not a new execution instruction."
            if resolved
            else f"Retained session workstream `{retained}` no longer resolves in current projections."
        )
        selection.update(
            state="inferred_confident" if resolved else "none",
            reason=reason,
            why_selected=reason,
            confidence="high" if resolved else "none",
            ambiguity_class="retained_session" if resolved else "retained_missing",
        )
        if resolved:
            selection["selected_workstream"].pop("selection_reason", None)
    return selection
