"""Progressive disclosure must preserve complete standalone handoff prompts."""

from copy import deepcopy
from html import escape

import pytest

from odylith.runtime.project_intelligence.presenter import _host_handoff


def test_handoff_keeps_stage_outcome_visible_and_exact_prompt_in_closed_details() -> None:
    prompt = 'Keep Ω-case and <literal> text.\n\nDo not connect.\n  Preserve spacing.\n'
    project = {
        "host_handoff_title": "Start source creation",
        "host_handoff_prompts": [{
            "label": 'Build "first" slice', "when": "After the plan is accepted.",
            "prompt": prompt, "result": "One tested path.", "stop": "Before publication.",
        }],
    }
    original = deepcopy(project)

    html = _host_handoff(project)

    assert project == original
    assert html.count("<details>") == 1
    assert "<details open" not in html
    assert f"<code>{escape(prompt)}</code>" in html
    assert 'aria-label="Read full prompt: Build &quot;first&quot; slice"' in html
    assert "Read full prompt</summary>" in html
    assert html.index("Produces:") < html.index("<details>")
    assert html.index("Stops:") < html.index("<details>")
    assert "<literal>" not in html


@pytest.mark.parametrize("rows", [None, [], [{"prompt": " "}], [{"label": "Missing prompt"}]])
def test_handoff_without_a_usable_prompt_does_not_show_an_empty_disclosure(rows) -> None:
    assert _host_handoff({"host_handoff_prompts": rows}) == ""


def test_handoff_escapes_untrusted_prompt_and_summary_without_executing_markup() -> None:
    hostile = '</code><script>alert("not authority")</script>'
    html = _host_handoff({"host_handoff_prompts": [{"label": hostile, "prompt": hostile}]})

    assert "<script>" not in html
    assert f"<code>{escape(hostile)}</code>" in html
    assert f'aria-label="Read full prompt: {escape(hostile)}"' in html
