from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
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


def test_greenfield_source_launch_prompts_keep_fragments_clause_safe(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"therapy-workspace\"\n", encoding="utf-8")
    first_path = (
        "A pediatric therapy agency practice workspace user can coordinate referral intake, guardian consent, "
        "therapist assignment, care-plan readiness. Visit evidence. Exception review for children served across "
        "multiple schools."
    )

    handoff = build_source_launch_handoff(
        repo_root=tmp_path,
        title="Pediatric Therapy Agency Practice Workspace",
        first_path=first_path,
        actors=(
            ("", "Pediatric Therapy Agency Practice Workspace User: coordinates the work", ""),
            ("", "Pediatric Therapy Agency proof reviewer: reviews the result", ""),
        ),
        components=(
            {
                "label": "Pediatric Therapy Agency Practice Workspace Intake",
                "responsibility": "Captures intake evidence and result visibility.",
            },
        ),
        risks=("Exception review for children served across multiple schools can be wrong or misleading.",),
        validation=("Success proof includes coordinating referral intake, guardian consent, therapist assignment, care-plan readiness, visiting evidence, and reviewing for children served across multiple schools.",),
        non_goals=("Authentication, billing, full UI, database persistence, and external APIs.",),
    )
    encoded = json.dumps(handoff, sort_keys=True)

    assert "., validation points" not in encoded
    assert "., input validation" not in encoded
    assert "and receive Pediatric therapy agency practice workspace user coordinates" not in encoded
    for row in handoff["prompts"]:
        assert generated_public_copy_issues(f"Project implementation prompt `{row['label']}`", row) == ()


def test_greenfield_source_launch_prompts_suppress_repeated_action_outcome(tmp_path: Path) -> None:
    cases = (
        (
            "Security Disclosure Council",
            "A security disclosure council user can receive a disclosure and receive a disclosure.",
            "receive a disclosure and receive a disclosure",
            "capture the information needed to receive a disclosure and return a disclosure",
        ),
        (
            "Port Berth Carbon Tariff",
            "A port berth carbon tariff user can review compliance exceptions and receive compliance exceptions.",
            "review compliance exceptions and receive compliance exceptions",
            "capture the information needed to review compliance exceptions and return compliance exceptions",
        ),
    )
    for title, first_path, duplicated_path, duplicated_capability in cases:
        handoff = build_source_launch_handoff(
            repo_root=tmp_path,
            title=title,
            first_path=first_path,
            actors=(("", f"{title} User: coordinates the work", ""),),
            components=(),
            risks=(),
            validation=(),
            non_goals=(),
        )
        encoded = json.dumps(handoff, sort_keys=True).casefold()

        assert duplicated_path not in encoded
        assert duplicated_capability not in encoded
        for row in handoff["prompts"]:
            assert generated_public_copy_issues(f"Project implementation prompt `{row['label']}`", row) == ()
