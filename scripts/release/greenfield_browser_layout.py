"""Shared readable-layout assertions for Greenfield browser proof states."""

from __future__ import annotations

from typing import Any


def layout_issues(root: Any, *, label: str) -> tuple[str, ...]:
    """Check viewport fit and visible copy without brittle pixel snapshots."""

    state = root.evaluate(
        """(node) => {
            const doc = node.ownerDocument;
            const viewportWidth = doc.documentElement.clientWidth;
            const text = String(node.innerText || "").trim();
            const clipped = Array.from(node.querySelectorAll("h1, h2, h3, p, [role='status'], [role='alert']"))
              .filter((item) => {
                const style = doc.defaultView.getComputedStyle(item);
                if (style.display === "none" || style.visibility === "hidden") return false;
                const clipsX = style.overflowX === "hidden" || style.overflowX === "clip";
                const clipsY = style.overflowY === "hidden" || style.overflowY === "clip";
                const lineClamp = Number.parseInt(style.webkitLineClamp || "0", 10);
                if (lineClamp > 0) return false;
                return (clipsX && item.scrollWidth > item.clientWidth + 4)
                  || (clipsY && item.scrollHeight > item.clientHeight + 4);
              });
            return {
              horizontalOverflow: Math.max(0, node.scrollWidth - viewportWidth),
              clippedTextCount: clipped.length,
              visibleCopyLength: text.length
            };
        }"""
    )
    return layout_assertion_issues(
        label=label,
        horizontal_overflow=int(state.get("horizontalOverflow", 0) if isinstance(state, dict) else 0),
        clipped_text_count=int(state.get("clippedTextCount", 0) if isinstance(state, dict) else 0),
        visible_copy_length=int(state.get("visibleCopyLength", 0) if isinstance(state, dict) else 0),
    )


def layout_assertion_issues(
    *, label: str, horizontal_overflow: int, clipped_text_count: int, visible_copy_length: int
) -> tuple[str, ...]:
    issues: list[str] = []
    if horizontal_overflow > 4:
        issues.append(f"browser surface {label} overflows the viewport horizontally")
    if clipped_text_count:
        issues.append(f"browser surface {label} clips visible status or content copy")
    if visible_copy_length < 12:
        issues.append(f"browser surface {label} does not expose meaningful visible copy")
    return tuple(issues)


__all__ = ["layout_assertion_issues", "layout_issues"]
