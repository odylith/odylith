from __future__ import annotations

from pathlib import Path

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.project_intelligence.greenfield import build_greenfield_payload


def test_greenfield_project_dashboard_dedupes_overlapping_risk_labels() -> None:
    payload = build_greenfield_payload(
        proposal={
            "intent": {
                "title": "Shipping Ballast Water Compliance",
                "first_path": (
                    "A maritime compliance analyst reviews ballast water discharge evidence "
                    "and publishes a compliance decision."
                ),
            },
            "release_plan": {"label": "0.0.1"},
            "risks": [
                {"statement": "Compliance boundary can be wrong when jurisdiction evidence is incomplete."},
                {"statement": "Maritime compliance can fail when discharge evidence is stale."},
                {"statement": "Measurement reliability can fail when ballast readings drift."},
            ],
        },
        repo_root=Path("/tmp/nonexistent"),
    )
    encoded = " ".join(str(row) for row in [*payload["unknown"], *payload["blockers"]])

    assert "Compliance Compliance" not in encoded
    assert "Maritime Compliance boundary" in encoded
    assert generated_public_copy_issues("project dashboard preview", payload) == ()
