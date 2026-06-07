from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.project_intelligence.source_launch import build_source_launch_handoff


def test_greenfield_source_launch_prompts_keep_sun_burn_copy_complete(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"sunrecover\"\n", encoding="utf-8")
    first_path = (
        "A user opens the app after a burn, captures a photo and answers the intake questions, and immediately receives "
        "a severity read and a first-24-hours action plan. Over the following days the app prompts daily check-ins, "
        "compares new photos and symptom scores against the baseline, updates the plan as the burn settles and the tan "
        "fades, and marks the episode healed — or surfaces a clear escalation warning if severity or warning signs cross "
        "a safety threshold."
    )
    handoff = build_source_launch_handoff(
        repo_root=tmp_path,
        title="SunRecover — sunburn relief and skin-recovery coach",
        first_path=first_path,
        actors=(
            ("", "Sun-exposed Individual: contributes information, review, or action needed", ""),
            ("", "Caregiver: reviews the result", ""),
        ),
        components=(
            {"label": "Intake and Severity Assessment Engine", "responsibility": "Captures intake and severity state."},
            {"label": "Staged Recovery-plan Generator", "responsibility": "Returns the first care plan."},
        ),
        risks=(
            {
                "statement": (
                    "A first-24-hours action plan can be wrong or misleading when the information behind it is incomplete, "
                    "stale, inconsistent, or interpreted incorrectly. The weak inputs are a photo and the intake questions; "
                    "Sun-exposed Individual may then act on a result that does not match the real situation."
                )
            },
        ),
        validation=(
            "The accepted first path proves answering the intake questions, receiving a severity read and a first-24-hours "
            "action plan, prompting daily check-ins, and comparing new photos and symptom scores against the baseline.",
        ),
        non_goals=(),
    )
    encoded = json.dumps(handoff, sort_keys=True)

    assert "Current signal: existing repo language signals point to Python. Confirm that Python is still" in encoded
    assert "Sun-exposed Individual changes or reads" in encoded
    assert "Caregiver" in encoded
    assert "comparing new photos and symptom scores against the baseline" in encoded
    assert "a photo and answers" not in encoded
    assert "a photo and the intake." not in encoded
    assert "contributes information" not in encoded
    assert "proof gates for the accepted first path proves" not in encoded
    assert "comparing new photos." not in encoded
