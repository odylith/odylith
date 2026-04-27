from __future__ import annotations

from pathlib import Path
import tomllib

from odylith.runtime import release_notes


def _front_matter_blocks(notes_root: Path):
    for path in sorted(notes_root.glob("v*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        assert end > 0, f"{path} has unclosed front matter"
        yield path, text[4:end]


def _has_unsafe_plain_scalar_colon(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.endswith(":"):
        return False
    if stripped.startswith("- "):
        return ": " in stripped[2:]
    if ": " not in stripped:
        return False
    key, value = stripped.split(": ", 1)
    if not key.replace("_", "").replace("-", "").isalnum():
        return False
    return ": " in value


def test_load_release_notes_source_parses_front_matter_and_normalizes_markdown(tmp_path) -> None:  # noqa: ANN001
    notes_root = tmp_path / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v0.1.6.md").write_text(
        (
            "---\n"
            "version: 0.1.6\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "note_link_label: Read note\n"
            "external_link_label: example.com\n"
            "reopen_label: v0.1.6\n"
            "summary: [Linked](https://example.com) summary\n"
            "highlights:\n"
            "  - `One` highlight\n"
            "  - Two highlight\n"
            "---\n\n"
            "# Heading\n\n"
            "First paragraph with **bold** copy.\n\n"
            "- Bullet one\n"
            "- Bullet two\n\n"
            "Second paragraph."
        ),
        encoding="utf-8",
    )

    note = release_notes.load_release_notes_source(repo_root=tmp_path, version="0.1.6")

    assert note is not None
    assert note.version == "0.1.6"
    assert note.title == "Heading"
    assert note.published_at == "2026-03-30T14:00:00Z"
    assert note.summary == "Linked summary"
    assert note.highlights == ("One highlight", "Two highlight")
    assert note.note_link_label == "Read note"
    assert note.external_link_label == "example.com"
    assert note.reopen_label == "v0.1.6"
    assert "First paragraph with **bold** copy." in note.body


def test_repo_has_authored_release_note_for_current_product_version() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    project = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    version = str(project.get("version", "")).strip()

    note = release_notes.load_release_notes_source(repo_root=repo_root, version=version)

    assert version
    assert note is not None
    assert note.version == version
    assert note.summary


def test_repo_release_note_front_matter_stays_github_yaml_safe() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    notes_roots = (
        repo_root / "odylith" / "runtime" / "source" / "release-notes",
        repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "runtime" / "source" / "release-notes",
    )

    unsafe_lines = []
    for notes_root in notes_roots:
        for path, front_matter in _front_matter_blocks(notes_root):
            for line_no, line in enumerate(front_matter.splitlines(), start=2):
                if _has_unsafe_plain_scalar_colon(line):
                    unsafe_lines.append(f"{path.relative_to(repo_root)}:{line_no}: {line.strip()}")

    assert unsafe_lines == []


def test_repo_has_authored_release_note_for_v0_1_9_release_prep() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    note = release_notes.load_release_notes_source(repo_root=repo_root, version="0.1.9")

    assert note is not None
    assert note.version == "0.1.9"
    assert note.title == "Surface Truth"
    assert note.highlights
    assert note.summary.startswith("Trustworthy governance surfaces")


def test_repo_has_authored_release_note_for_v0_1_10_release_prep() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    note = release_notes.load_release_notes_source(repo_root=repo_root, version="0.1.10")

    assert note is not None
    assert note.version == "0.1.10"
    assert note.title == "Boringly Trustworthy"
    assert note.highlights
    assert note.summary.startswith("Truthful Compass refresh")


def test_github_release_notes_url_points_at_tagged_markdown() -> None:
    assert release_notes.github_release_notes_url(version="0.1.7", release_tag="v0.1.7") == (
        "https://github.com/odylith/odylith/blob/v0.1.7/odylith/runtime/source/release-notes/v0.1.7.md"
    )
