"""Authored Markdown is formatted structurally without rewriting source claims."""

from pathlib import Path
from xml.etree import ElementTree

import pytest

from odylith.runtime.surfaces import backlog_rich_text


def render(source: str, *, preview: bool = False) -> str:
    if preview:
        return backlog_rich_text.render_section_body(repo_root=Path("."), lines=source.splitlines(), preview=True)
    return backlog_rich_text.render_section_body(repo_root=Path("."), lines=source.splitlines())


def test_inline_step_text_and_code_remain_literal() -> None:
    source = "Keep `__sample_id__` and `1. first 2. second` intact. Read 1. first 2. second without inventing steps."
    root = ElementTree.fromstring("<div>" + render(source) + "</div>")
    assert [node.text for node in root.findall(".//code")] == ["__sample_id__", "1. first 2. second"]
    assert root.find(".//ol") is None
    assert "Read 1. first 2. second without inventing steps." in "".join(root.itertext())


def test_nested_lists_and_balanced_link_targets_keep_markdown_structure() -> None:
    source = "**Proposed deliverable**\n\n- Parent\n  - Child with [evidence](docs/review_(draft).md)\n- Peer"
    root = ElementTree.fromstring("<div>" + render(source) + "</div>")
    assert root.find("./p/strong").text == "Proposed deliverable"
    assert root.find("./ul/li/ul/li/a").attrib["href"] == "docs/review_(draft).md"
    assert len(root.findall(".//li")) == 3


@pytest.mark.parametrize("url", ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,attack", "data:image/png;base64,AA", "file:///private/record"])
def test_unsafe_link_destinations_are_inert(url: str) -> None:
    rendered = render(f"[untrusted]({url})")
    assert "<a " not in rendered
    assert "<img " not in rendered


@pytest.mark.parametrize("url", ["docs/review_(draft).md", "https://example.com/review_(draft)", "http://example.com/review"])
def test_safe_links_keep_their_exact_target(url: str) -> None:
    root = ElementTree.fromstring("<div>" + render(f"[evidence]({url})") + "</div>")
    link = root.find(".//a")
    assert link.attrib["href"] == url
    assert link.text == "evidence"
    if url.startswith("http"):
        assert link.attrib["rel"] == "noopener noreferrer"


def test_raw_html_images_and_script_terminators_are_inert() -> None:
    source = '<img src="https://example.com/image" onerror="alert(1)">\n\n</script><script>attack()</script>\n\n![Image description](https://example.com/image)'
    rendered = render(source)
    assert "<img" not in rendered and "<script" not in rendered and "</script>" not in rendered
    assert "Image description" in rendered


def test_long_paragraphs_and_legacy_commands_are_not_rewritten() -> None:
    source = "Fresh evidence remains conditional. " * 20 + "Run `python -m scripts.run_clean_snapshot_strict_sync --repo-root .` only if approved."
    root = ElementTree.fromstring("<div>" + render(source) + "</div>")
    assert len(root.findall("./p")) == 1
    assert root.find(".//code").text == "python -m scripts.run_clean_snapshot_strict_sync --repo-root ."
    assert "".join(root.itertext()).strip() == source.replace("`", "")


def test_preview_formats_without_nested_links_controls_images_or_executable_fences() -> None:
    source = "**Proposed deliverable** with `__sample_id__`.\n\n- [x] [Reviewed](https://example.com/review)\n- [ ] Pending\n\n![Description](https://example.com/image)\n\n```mermaid\nflowchart TD; A-->B\n```"
    rendered = render(source, preview=True)
    assert "<strong>Proposed deliverable</strong>" in rendered
    assert "<code>__sample_id__</code>" in rendered
    for prohibited in ("<a ", "<input", "<img", 'class="mermaid"', " id=", " name="):
        assert prohibited not in rendered
    assert "Reviewed" in rendered and "Pending" in rendered and "Description" in rendered
    assert "flowchart TD; A--&gt;B" in rendered


def test_detail_checklists_are_noneditable_and_keep_state() -> None:
    rendered = render("- [x] Keep `__sample_id__`\n- [ ] Await review")
    assert rendered.count('type="checkbox"') == 2
    assert rendered.count(" disabled") == 2
    assert rendered.count(" checked") == 1
    assert "<code>__sample_id__</code>" in rendered


@pytest.mark.parametrize("marker", [r"\[x]", "&#91;x]", "`[x]`"])
@pytest.mark.parametrize("preview", [False, True], ids=["detail", "preview"])
def test_literal_checklist_markers_do_not_claim_completion(marker: str, preview: bool) -> None:
    rendered = render(f"- {marker} Document the literal marker", preview=preview)
    assert 'type="checkbox"' not in rendered and 'aria-label="Complete"' not in rendered
    assert "[x]" in rendered


def test_legitimate_nested_checklists_keep_their_hierarchy_and_state() -> None:
    rendered = render("- [x] Parent\n  - [ ] Child\n- Ordinary peer")
    assert rendered.count('type="checkbox"') == 2
    assert rendered.count(" checked") == 1
    assert rendered.count("<ul>") == 2
    assert rendered.index("Parent") < rendered.index("Child") < rendered.index("Ordinary peer")


def test_detail_mermaid_and_ordinary_fences_keep_their_existing_roles() -> None:
    source = '```mermaid\nflowchart TD; A-->B\n```\n\n```python\nprint("<literal>")\n```'
    rendered = render(source)
    assert 'class="mermaid">flowchart TD; A--&gt;B' in rendered
    assert '<pre class="code language-python"><code>print(&quot;&lt;literal&gt;&quot;)' in rendered


def test_section_projection_does_not_promote_front_matter_to_a_section() -> None:
    source = "---\nidea_id: B-001\n---\n\n## Problem\nKeep the record.\n"
    assert backlog_rich_text.extract_section_bodies(source) == [("Problem", ["Keep the record."])]
