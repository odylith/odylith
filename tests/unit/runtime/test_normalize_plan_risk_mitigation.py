"""Regression coverage for plan risk/mitigation normalization."""

from __future__ import annotations

from pathlib import Path

import pytest
from markdown_it import MarkdownIt

from odylith.runtime.governance import normalize_plan_risk_mitigation as normalizer


def _seed_plan(path: Path, *, body: str) -> None:
    """Write a plan fixture file for normalization tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_normalize_risk_section_rewrites_inline_and_top_level_mitigation(tmp_path: Path) -> None:
    plan_path = tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-02-28-demo.md"
    _seed_plan(
        plan_path,
        body=(
            "Status: In progress\n\n"
            "## Risks / Mitigations\n\n"
            "- [x] Risk: drift in workflow mapping. Mitigation: enforce command contract.\n"
            "- [x] Risk: docs can drift from behavior.\n"
            "- [x] Mitigation: validate docs in CI.\n\n"
            "## Validation/Test Plan\n\n"
            "- [x] baseline.\n"
        ),
    )

    changed, paths = normalizer.normalize_plan_risk_mitigation(repo_root=tmp_path, check_only=False)
    assert changed == 1
    assert paths == ["odylith/technical-plans/in-progress/2026-02-28-demo.md"]

    rendered = plan_path.read_text(encoding="utf-8")
    assert "## Risks & Mitigations" in rendered
    assert "- [x] Risk: drift in workflow mapping." in rendered
    assert "  - [x] Mitigation: enforce command contract." in rendered
    assert "- [x] Risk: docs can drift from behavior." in rendered
    assert "  - [x] Mitigation: validate docs in CI." in rendered


def test_main_check_returns_2_when_normalization_needed(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_plan(
        tmp_path / "odylith" / "technical-plans" / "done" / "2026-02" / "2026-02-28-demo.md",
        body=(
            "Status: Done\n\n"
            "## Risks & Mitigations\n\n"
            "- [x] Risk: example risk.\n"
            "- [x] Mitigation: example mitigation.\n"
        ),
    )

    rc = normalizer.main(["--repo-root", str(tmp_path), "--check"])
    assert rc == 2
    out = capsys.readouterr().out
    assert "plan risk/mitigation normalization FAILED" in out
    assert "would change: odylith/technical-plans/done/2026-02/2026-02-28-demo.md" in out


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            "- [x] Risk: a stale lease can\n"
            "  outlive its worker.\n"
            "  - [ ] Mitigation: expire the lease.\n",
            "- [x] Risk: a stale lease can outlive its worker.\n"
            "  - [ ] Mitigation: expire the lease.\n",
            id="wrapped-risk",
        ),
        pytest.param(
            "* [ ] Risk: a queue can stall.\n"
            "* [X] Mitigation: retry from the last\n"
            "  acknowledged offset.\n",
            "- [ ] Risk: a queue can stall.\n"
            "  - [x] Mitigation: retry from the last acknowledged offset.\n",
            id="wrapped-top-level-mitigation",
        ),
        pytest.param(
            "- [X] Risk: a response may contain\n"
            "  partial results from\n"
            "  separate shards.\n"
            "  * [x] Mitigation: compare the received\n"
            "    shard count with the request.\n"
            "  * [ ] Mitigation: reject incomplete\n"
            "    responses before caching.\n"
            "- [ ] Risk: a key may be reused.\n"
            "  - [x] Mitigation: rotate it.\n",
            "- [x] Risk: a response may contain partial results from separate shards.\n"
            "  - [x] Mitigation: compare the received shard count with the request.\n"
            "  - [ ] Mitigation: reject incomplete responses before caching.\n"
            "- [ ] Risk: a key may be reused.\n"
            "  - [x] Mitigation: rotate it.\n",
            id="multiple-wrapped-items-and-next-risk",
        ),
        pytest.param(
            "- [x] Risk: an export may stop. Mitigation: resume at the\n"
            "  recorded checkpoint.\n",
            "- [x] Risk: an export may stop.\n"
            "  - [x] Mitigation: resume at the recorded checkpoint.\n",
            id="wrapped-inline-pair",
        ),
        pytest.param(
            "- Risk: a deployment may overlap.\n"
            "  - retain the lock until\n"
            "    shutdown completes.\n",
            "- [ ] Risk: a deployment may overlap.\n"
            "  - [ ] Mitigation: retain the lock until shutdown completes.\n",
            id="wrapped-unlabeled-nested-mitigation",
        ),
    ],
)
def test_normalize_preserves_wrapped_list_item_ownership(source: str, expected: str) -> None:
    document = "## Risks & Mitigations\n\n" + source
    rendered = normalizer.normalize_risk_mitigation_markdown(document)

    assert rendered == "## Risks & Mitigations\n\n" + expected
    assert normalizer.normalize_risk_mitigation_markdown(rendered) == rendered


def test_normalize_wrapped_items_preserves_paragraph_and_section_boundaries() -> None:
    source = (
        "Introductory text.\n\n"
        "## Risks & Mitigations\n\n"
        "- [x] Risk: a reader may observe\n"
        "  a partial write.\n"
        "  - [ ] Mitigation: use an atomic\n"
        "    replacement.\n\n"
        "    This paragraph is not a continuation after a blank line.\n\n"
        "- [ ] Risk: an index can grow.\n\n"
        "Unindented prose is not a list continuation.\n"
        "- [x] Risk: a client can disconnect.\n"
        "  - [x] Mitigation: discard the\n"
        "    pending response.\n\n"
        "### Review notes\n\n"
        "Keep the evidence.\n\n"
        "## Validation/Test Plan\n\n"
        "  Leave this section unchanged.\n"
    )
    expected = (
        "Introductory text.\n\n"
        "## Risks & Mitigations\n\n"
        "- [x] Risk: a reader may observe a partial write.\n"
        "  - [ ] Mitigation: use an atomic replacement.\n\n"
        "    This paragraph is not a continuation after a blank line.\n\n"
        "- [ ] Risk: an index can grow.\n"
        "  - [ ] Mitigation: TODO (add explicit mitigation).\n"
        "\n"
        "Unindented prose is not a list continuation.\n"
        "- [x] Risk: a client can disconnect.\n"
        "  - [x] Mitigation: discard the pending response.\n\n"
        "### Review notes\n\n"
        "Keep the evidence.\n\n"
        "## Validation/Test Plan\n\n"
        "  Leave this section unchanged.\n"
    )

    rendered = normalizer.normalize_risk_mitigation_markdown(source)

    assert rendered == expected
    assert normalizer.normalize_risk_mitigation_markdown(rendered) == rendered


def test_normalize_preserves_lazy_risk_continuation() -> None:
    source = (
        "## Risks & Mitigations\n\n"
        "- [x] Risk: a stale lease can\n"
        "outlive its worker.\n"
        "  - [ ] Mitigation: expire the lease.\n"
    )
    assert normalizer.normalize_risk_mitigation_markdown(source) == (
        "## Risks & Mitigations\n\n"
        "- [x] Risk: a stale lease can outlive its worker.\n"
        "  - [ ] Mitigation: expire the lease.\n"
    )


@pytest.mark.parametrize("example", [
    "```text\n- Risk: quoted input\n```",
    "~~~text\n- Risk: quoted input\n~~~",
    "    - Risk: quoted input",
    "> Risk: quoted input\n> Mitigation: quoted response",
    "<pre>\nRisk: quoted input\nMitigation: quoted response\n</pre>",
])
def test_normalize_does_not_interpret_literal_or_quoted_blocks(example: str) -> None:
    source = (
        "## Risks & Mitigations\n\n"
        "- [x] Risk: a source example may be mistaken for a live record.\n"
        "  - [x] Mitigation: retain its literal presentation.\n\n"
        "The following is source input, not another record.\n\n"
        + example + "\n"
    )
    assert normalizer.normalize_risk_mitigation_markdown(source) == source


def test_normalize_does_not_select_risk_headings_inside_examples() -> None:
    source = "```markdown\n## Risks & Mitigations\n- Risk: quoted input\n```\n"
    assert normalizer.normalize_risk_mitigation_markdown(source) == source


@pytest.mark.parametrize("heading", ["## Risks", "## Risks&Mitigations", "## Risks/Mitigations", "Risks & Mitigations\n-------------------"])
def test_normalize_recognizes_actual_risk_heading_variants(heading: str) -> None:
    body = "\n\n- [x] Risk: a record can be lost.\n  - [x] Mitigation: keep a verified copy.\n"
    assert normalizer.normalize_risk_mitigation_markdown(heading + body) == "## Risks & Mitigations" + body


@pytest.mark.parametrize("boundary", [
    "### Review notes\n\nKeep the evidence.",
    "> Reviewer note",
    "1. Separate numbered item",
    "---",
    "***",
    "___",
    "```text\nquoted example\n```",
    "~~~text\nquoted example\n~~~",
])
def test_normalize_preserves_structural_boundaries(boundary: str) -> None:
    source = (
        "## Risks & Mitigations\n\n"
        "- [x] Risk: preserve this item.\n"
        "  - [x] Mitigation: preserve this relationship.\n\n"
        + boundary + "\n"
    )
    assert normalizer.normalize_risk_mitigation_markdown(source) == source


@pytest.mark.parametrize("owned_block", [
    "",
    "  Renewal requires the original lease identity.\n\n",
    "  ```text\n  lease  identity\n  ```\n\n",
    "  > Keep the original lease identity.\n\n",
])
def test_normalize_preserves_loose_list_ancestry(owned_block: str) -> None:
    source = (
        "## Risks & Mitigations\n\n"
        "- [x] Risk: a lease can expire.\n\n"
        + owned_block
        + "  - [ ] Mitigation: renew the same lease.\n"
    )
    rendered = normalizer.normalize_risk_mitigation_markdown(source)
    assert "TODO" not in rendered
    assert "Unspecified risk" not in rendered
    assert MarkdownIt("commonmark").render(rendered) == MarkdownIt("commonmark").render(source)
    assert normalizer.normalize_risk_mitigation_markdown(rendered) == rendered


@pytest.mark.parametrize("literal", [
    "`the Mitigation: retry command`",
    "``the Mitigation: `retry` command``",
    "[the Mitigation: retry command](https://example.invalid/command)",
    "![the Mitigation: retry command](example.png)",
])
def test_normalize_does_not_promote_literal_inline_labels(literal: str) -> None:
    source = (
        "## Risks & Mitigations\n\n"
        f"- [x] Risk: output can include {literal} literally.\n"
        "  - [ ] Mitigation: preserve the source.\n"
    )
    assert normalizer.normalize_risk_mitigation_markdown(source) == source


@pytest.mark.parametrize("body", [
    "- [x] Risk: `a  b` is not `a b`.\n  - [ ] Mitigation: retain both spaces.\n",
    "- [x] Risk: the first line.  \n  The second line.\n  - [ ] Mitigation: preserve the hard break.\n",
    "- [x] Risk: the first line.\\\n  The second line.\n  - [ ] Mitigation: preserve the hard break.\n",
    "- [x] Risk: whitespace matters.\n  - [ ] Mitigation: preserve this line.  \n    And this line.\n",
    "- [x] Risk: whitespace matters.\n  - [ ] Mitigation: preserve this line.\\\n    And this line.\n",
    "- [x] Risk: whitespace matters.\n\n  ```text\n  a  \n  b\t\n  ```\n\n  - [ ] Mitigation: preserve the code.\n",
    "- [x] Risk: whitespace matters.\n  - [ ] Mitigation: preserve the code.\n\n```text\na  \nb\t\n```\n",
])
def test_normalize_preserves_markdown_significant_whitespace(body: str) -> None:
    source = "## Risks & Mitigations\n\n" + body
    rendered = normalizer.normalize_risk_mitigation_markdown(source)
    assert MarkdownIt("commonmark").render(rendered) == MarkdownIt("commonmark").render(source)
    assert rendered == source


def test_normalize_does_not_rewrite_unrelated_document_bytes() -> None:
    source = "An unrelated document.\n\n```text\na  \n"
    assert normalizer.normalize_risk_mitigation_markdown(source) == source


@pytest.mark.parametrize("enclosed", [
    "<code>the Mitigation: test</code>",
    "<kbd>the Mitigation: test</kbd>",
    "<span title='quoted > boundary'>the Mitigation: test</span>",
    "<span><em>the Mitigation: test</em></span>",
    "*a risk Mitigation: a fix*",
    "**a risk Mitigation: a fix**",
    "_a risk Mitigation: a fix_",
    "***a risk Mitigation: a fix***",
])
def test_normalize_preserves_inline_container_ownership(enclosed: str) -> None:
    source = (
        "## Risks & Mitigations\n\n"
        f"- [x] Risk: keep {enclosed} literally.\n"
        "  - [ ] Mitigation: retain it.\n"
    )
    rendered = normalizer.normalize_risk_mitigation_markdown(source)
    assert MarkdownIt("commonmark").render(rendered) == MarkdownIt("commonmark").render(source)
    assert rendered == source
    assert normalizer.normalize_risk_mitigation_markdown(rendered) == rendered


@pytest.mark.parametrize("enclosed", [
    "<code>the Mitigation: test</code>",
    "*the Mitigation: test*",
])
def test_normalize_splits_real_label_after_closed_inline_container(enclosed: str) -> None:
    source = f"## Risks & Mitigations\n\n- [x] Risk: keep {enclosed}. Mitigation: retain it.\n"
    expected = (
        f"## Risks & Mitigations\n\n- [x] Risk: keep {enclosed}.\n"
        "  - [x] Mitigation: retain it.\n"
    )
    rendered = normalizer.normalize_risk_mitigation_markdown(source)
    assert rendered == expected
    assert MarkdownIt("commonmark").render(rendered) == MarkdownIt("commonmark").render(expected)


@pytest.mark.parametrize("void_element", ["<br>", "<img src='example.png'>"])
def test_normalize_recognizes_labels_after_void_html(void_element: str) -> None:
    source = (
        "## Risks & Mitigations\n\n"
        f"- [x] Risk: output may include {void_element}. Mitigation: preserve it.\n"
    )
    expected = (
        "## Risks & Mitigations\n\n"
        f"- [x] Risk: output may include {void_element}.\n"
        "  - [x] Mitigation: preserve it.\n"
    )
    assert normalizer.normalize_risk_mitigation_markdown(source) == expected


def test_ambiguous_html_does_not_skip_other_risk_relationships() -> None:
    enclosed = (
        "- [x] Risk: preserve an unclosed <code>Mitigation: example.\n"
        "  - [ ] Mitigation: retain the authored example.\n"
    )
    source = (
        "## Risks & Mitigations\n\n" + enclosed
        + "- [x] Risk: a second lease can expire.\n"
        "- [ ] Mitigation: renew the second lease.\n"
    )
    expected = (
        "## Risks & Mitigations\n\n" + enclosed
        + "- [x] Risk: a second lease can expire.\n"
        "  - [ ] Mitigation: renew the second lease.\n"
    )
    assert normalizer.normalize_risk_mitigation_markdown(source) == expected
