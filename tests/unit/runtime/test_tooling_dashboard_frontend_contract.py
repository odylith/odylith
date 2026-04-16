from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import tooling_dashboard_frontend_contract as contract


@pytest.fixture(autouse=True)
def _clear_tooling_shell_contract_caches() -> None:
    contract.load_tooling_shell_style_css.cache_clear()
    contract.load_tooling_shell_control_js.cache_clear()
    yield
    contract.load_tooling_shell_style_css.cache_clear()
    contract.load_tooling_shell_control_js.cache_clear()


def _seed_tooling_shell_assets(tmp_path: Path) -> Path:
    asset_root = tmp_path / "tooling_dashboard"
    asset_root.mkdir(parents=True, exist_ok=True)
    template_root = contract._template_asset_path("page.html.j2").parent
    for source_path in template_root.iterdir():
        if not source_path.is_file():
            continue
        (asset_root / source_path.name).write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    return asset_root


def test_tooling_shell_header_contract_matches_current_source() -> None:
    contract.assert_tooling_shell_header_contract()


def test_tooling_shell_header_contract_rejects_template_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asset_root = _seed_tooling_shell_assets(tmp_path)
    page_path = asset_root / "page.html.j2"
    page_path.write_text(
        page_path.read_text(encoding="utf-8").replace(
            "</nav>",
            '<button id="tab-mutant" type="button" class="tab">Mutant</button></nav>',
            1,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(contract, "_template_asset_path", lambda filename: asset_root / filename)

    with pytest.raises(ValueError, match=r"page\.html\.j2"):
        contract.assert_tooling_shell_header_contract()


def test_tooling_shell_header_contract_rejects_style_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asset_root = _seed_tooling_shell_assets(tmp_path)
    style_path = asset_root / "style.css"
    style_path.write_text(
        style_path.read_text(encoding="utf-8").replace("gap: 10px;", "gap: 11px;", 1),
        encoding="utf-8",
    )
    monkeypatch.setattr(contract, "_template_asset_path", lambda filename: asset_root / filename)

    with pytest.raises(ValueError, match=r"style\.css"):
        contract.assert_tooling_shell_header_contract()


def test_tooling_shell_frontend_contract_loads_cheatsheet_modules() -> None:
    style_css = contract.load_tooling_shell_style_css()
    control_js = contract.load_tooling_shell_control_js()

    assert ".brief-drawer-cheatsheet" in style_css
    assert "--surface-identifier-chip-padding: 2px 10px;" in style_css
    assert "--surface-identifier-font-size: 14px;" in style_css
    assert "--surface-identifier-font-weight: 500;" in style_css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING};"
    ) in style_css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE};"
    ) in style_css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}: "
        f"{dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT};"
    ) in style_css
    assert ".operator-readout .operator-readout-copy a.brief-inline-link {" in style_css
    assert "font-size: var(--surface-identifier-font-size, 14px);" in style_css
    assert "font-weight: var(--surface-identifier-font-weight, 500);" in style_css
    assert ".agent-cheatsheet-search-input" in style_css
    assert ".agent-cheatsheet-empty[hidden]" in style_css
    assert "initToolingShellCheatsheetDrawer" in control_js
    assert 'document.getElementById("agentCheatsheetResults")' in control_js
    assert 'const CASEBOOK_SORT_DEFAULT = "newest";' in control_js
    assert 'casebook: { bug: "", severity: "", status: "", sort: CASEBOOK_SORT_DEFAULT }' in control_js
    assert 'if (sort !== CASEBOOK_SORT_DEFAULT) query.set("sort", sort);' in control_js
    assert 'const sortToken = canonicalizeCasebookSortToken(raw.sort || "");' in control_js
