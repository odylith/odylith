"""Retain complete browser evidence for fixed-height governance shells."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def capture_state_screenshot(*, page: Any, output_dir: Path, state_name: str) -> Path:
    """Expand the active pane before Playwright captures the full document."""

    token = str(state_name or "").strip().casefold()
    if not token or any(not (char.isalnum() or char == "-") for char in token):
        raise RuntimeError("browser screenshot state name is unsafe")
    directory = Path(output_dir).expanduser()
    if directory.is_symlink():
        raise RuntimeError("browser screenshot output is unsafe")
    directory.mkdir(parents=True, exist_ok=True)
    directory = directory.resolve()
    target = directory / f"{token}.png"
    if target.exists() or target.is_symlink():
        raise RuntimeError(f"browser screenshot already exists: {token}")
    if token.startswith("mobile-"):
        viewport_target = directory / f"{token}-viewport.png"
        if viewport_target.exists() or viewport_target.is_symlink():
            raise RuntimeError(f"browser viewport screenshot already exists: {token}")
        page.screenshot(path=str(viewport_target), full_page=False)
    extent = page.evaluate(
        """() => {
            const pane = document.querySelector(".pane:not([hidden])");
            const child = pane?.tagName === "IFRAME" ? pane.contentDocument : null;
            const contentHeight = child
              ? Math.max(child.body?.scrollHeight || 0, child.documentElement?.scrollHeight || 0)
              : Math.max(pane?.scrollHeight || 0, pane?.clientHeight || 0);
            const viewport = pane?.closest(".viewport");
            if (pane && viewport && contentHeight > pane.clientHeight) {
              pane.style.height = `${contentHeight}px`;
              pane.style.bottom = "auto";
              viewport.style.height = `${contentHeight}px`;
              viewport.style.minHeight = `${contentHeight}px`;
              viewport.style.overflow = "visible";
              const shell = document.querySelector(".shell");
              if (shell) shell.style.height = "auto";
              document.documentElement.style.height = "auto";
              document.body.style.height = "auto";
            }
            return {
              contentHeight,
              viewportHeight: window.innerHeight,
              captureHeight: document.documentElement.scrollHeight
            };
        }"""
    )
    content_height = int(extent.get("contentHeight", 0) if isinstance(extent, dict) else 0)
    viewport_height = int(extent.get("viewportHeight", 0) if isinstance(extent, dict) else 0)
    capture_height = int(extent.get("captureHeight", 0) if isinstance(extent, dict) else 0)
    if content_height > viewport_height and capture_height <= viewport_height:
        raise RuntimeError("browser screenshot did not expand to below-fold content")
    page.screenshot(path=str(target), full_page=True)
    return target


__all__ = ["capture_state_screenshot"]
