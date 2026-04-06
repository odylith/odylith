from __future__ import annotations

from odylith.runtime.surfaces import tooling_dashboard_template_context as context


def test_build_template_context_defaults_to_odylith_shell_copy() -> None:
    built = context.build_template_context(
        {
            "shell_repo_label": "Repo · Odylith",
            "shell_repo_name": "odylith",
            "shell_version_label": "v0.1.6",
        },
        welcome_html="<section>Welcome</section>",
        system_status_html="<section>Status</section>",
        maintainer_notes_html="<section>Notes</section>",
        cheatsheet_html="<section>Cheatsheet</section>",
    )

    assert built.shell_title == "Odylith"
    assert built.shell_subtitle == "Delivery Governance and Intelligence"
    assert built.welcome_html == "<section>Welcome</section>"
    assert built.system_status_html == "<section>Status</section>"
    assert built.maintainer_notes_html == "<section>Notes</section>"
    assert built.cheatsheet_html == "<section>Cheatsheet</section>"
    assert built.version_story_href == ""
    assert built.version_story_label == "What changed since my version?"
    assert built.style_css
    assert built.control_script


def test_build_template_context_switches_title_in_ablation_mode() -> None:
    built = context.build_template_context(
        {
            "shell_repo_label": "Repo · Odylith",
            "odylith_switch": {"enabled": False, "mode": "disabled"},
        },
        welcome_html="",
        system_status_html="",
        maintainer_notes_html="",
        cheatsheet_html="",
    )

    assert built.shell_title == "Odylith Dashboard"
    assert "ablated for comparison runs" in built.shell_subtitle
