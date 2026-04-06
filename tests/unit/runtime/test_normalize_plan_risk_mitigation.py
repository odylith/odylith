from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import normalize_plan_risk_mitigation as normalizer


def _seed_plan(path: Path, *, body: str) -> None:
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
