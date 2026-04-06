from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import dashboard_template_runtime as runtime


def test_render_template_falls_back_without_jinja(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    template_root = tmp_path / "templates"
    template_root.mkdir(parents=True, exist_ok=True)
    (template_root / "demo.html.j2").write_text(
        "<h1>{{ title }}</h1>\n<div>{{ body | safe }}</div>\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(runtime, "_template_root", lambda: template_root)

    def _raise_runtime_error() -> None:
        raise RuntimeError("Jinja2 is not installed")

    monkeypatch.setattr(runtime, "build_environment", _raise_runtime_error)

    rendered = runtime.render_template(
        "demo.html.j2",
        title="<Title>",
        body="<strong>ok</strong>",
    )

    assert "<h1>&lt;Title&gt;</h1>" in rendered
    assert "<div><strong>ok</strong></div>" in rendered


def test_render_template_fallback_requires_context_keys(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    template_root = tmp_path / "templates"
    template_root.mkdir(parents=True, exist_ok=True)
    (template_root / "demo.html.j2").write_text("<p>{{ missing }}</p>\n", encoding="utf-8")

    monkeypatch.setattr(runtime, "_template_root", lambda: template_root)

    def _raise_runtime_error() -> None:
        raise RuntimeError("Jinja2 is not installed")

    monkeypatch.setattr(runtime, "build_environment", _raise_runtime_error)

    try:
        runtime.render_template("demo.html.j2")
    except KeyError as exc:
        assert "missing template context value" in str(exc)
    else:  # pragma: no cover - fail closed if fallback stops enforcing strict context.
        raise AssertionError("fallback renderer should fail on missing context values")
