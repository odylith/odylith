"""Shared client-side runtime snippets for generated dashboard surfaces.

These helpers centralize small browser-side interaction contracts that must
stay behaviorally identical across Radar, Atlas, Compass, Registry, and
Shell. Renderers should pass only explicit per-surface exceptions instead of
copying near-identical JavaScript blocks.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from odylith.runtime.surfaces import dashboard_ui_primitives


def quick_tooltip_runtime_js(
    *,
    tooltip_attr: str = "data-tooltip",
    excluded_closest_selectors: Sequence[str] = (),
    binding_guard_dataset_key: str | None = None,
    function_name: str = "initSharedQuickTooltips",
) -> str:
    """Return the shared floating-tooltip runtime for generated dashboards.

    Parameters are intentionally narrow so renderers can preserve current
    behavior without forking the runtime:
    - ``tooltip_attr`` keeps the runtime reusable for any attribute-based
      tooltip trigger contract.
    - ``excluded_closest_selectors`` allows a surface to opt certain nodes out
      of shared hover handling while leaving the rest of the behavior intact.
    - ``binding_guard_dataset_key`` preserves idempotent rebinding for surfaces
      that may re-enter their bootstrap path.
    """

    excluded = [str(selector).strip() for selector in excluded_closest_selectors if str(selector).strip()]
    return f"""
function {function_name}() {{
  const QUICK_TOOLTIP_BIND_KEY = {json.dumps(binding_guard_dataset_key, ensure_ascii=False)};
  if (QUICK_TOOLTIP_BIND_KEY && document.body && document.body.dataset[QUICK_TOOLTIP_BIND_KEY] === "1") {{
    return;
  }}
  if (QUICK_TOOLTIP_BIND_KEY && document.body) {{
    document.body.dataset[QUICK_TOOLTIP_BIND_KEY] = "1";
  }}

  const QUICK_TOOLTIP_ATTR = {json.dumps(tooltip_attr, ensure_ascii=False)};
  const QUICK_TOOLTIP_EXCLUDE_CLOSEST = {json.dumps(excluded, ensure_ascii=False, separators=(",", ":"))};
  const TOOLTIP_OFFSET_X = 12;
  const TOOLTIP_OFFSET_Y = 14;
  const tooltipEl = document.createElement("div");
  tooltipEl.className = "quick-tooltip";
  tooltipEl.hidden = true;
  tooltipEl.setAttribute("role", "tooltip");
  document.body.appendChild(tooltipEl);
  let tooltipTarget = null;

  function tooltipTextFromNode(node) {{
    if (!node) return "";
    return String(node.getAttribute(QUICK_TOOLTIP_ATTR) || "").trim();
  }}

  function shouldIgnoreTooltipNode(node) {{
    if (!(node instanceof Element)) return true;
    return QUICK_TOOLTIP_EXCLUDE_CLOSEST.some((selector) => {{
      if (!selector) return false;
      try {{
        return Boolean(node.closest(selector));
      }} catch (_error) {{
        return false;
      }}
    }});
  }}

  function tooltipNodeFromEventTarget(target) {{
    const node = target instanceof Element ? target.closest(`[${{QUICK_TOOLTIP_ATTR}}]`) : null;
    if (!node || shouldIgnoreTooltipNode(node)) {{
      return null;
    }}
    return node;
  }}

  function positionTooltip(clientX, clientY) {{
    const x = Number.isFinite(clientX) ? clientX : 0;
    const y = Number.isFinite(clientY) ? clientY : 0;
    const maxX = Math.max(8, window.innerWidth - tooltipEl.offsetWidth - 8);
    const maxY = Math.max(8, window.innerHeight - tooltipEl.offsetHeight - 8);
    const left = Math.min(maxX, Math.max(8, x + TOOLTIP_OFFSET_X));
    const top = Math.min(maxY, Math.max(8, y + TOOLTIP_OFFSET_Y));
    tooltipEl.style.left = `${{left}}px`;
    tooltipEl.style.top = `${{top}}px`;
  }}

  function hideTooltip() {{
    tooltipTarget = null;
    tooltipEl.classList.remove("visible");
    tooltipEl.hidden = true;
    tooltipEl.textContent = "";
  }}

  function showTooltip(node, clientX, clientY) {{
    const text = tooltipTextFromNode(node);
    if (!text) {{
      hideTooltip();
      return;
    }}
    tooltipTarget = node;
    tooltipEl.textContent = text;
    tooltipEl.hidden = false;
    positionTooltip(clientX, clientY);
    tooltipEl.classList.add("visible");
  }}

  document.addEventListener("pointerover", (event) => {{
    const node = tooltipNodeFromEventTarget(event.target);
    if (!node) return;
    showTooltip(node, event.clientX, event.clientY);
  }});

  document.addEventListener("pointermove", (event) => {{
    if (!tooltipTarget) return;
    positionTooltip(event.clientX, event.clientY);
  }});

  document.addEventListener("pointerout", (event) => {{
    if (!tooltipTarget) return;
    const related = event.relatedTarget;
    if (related instanceof Element && tooltipTarget.contains(related)) {{
      return;
    }}
    if (event.target instanceof Element && !tooltipTarget.contains(event.target)) {{
      return;
    }}
    hideTooltip();
  }});

  document.addEventListener("focusin", (event) => {{
    const node = tooltipNodeFromEventTarget(event.target);
    if (!node) return;
    const rect = node.getBoundingClientRect();
    showTooltip(node, rect.left + (rect.width / 2), rect.top);
  }});

  document.addEventListener("focusout", () => {{
    hideTooltip();
  }});
}}

{function_name}();
""".strip()


def quick_tooltip_bundle(
    *,
    selector: str = ".quick-tooltip",
    border_color: str = "rgba(191, 219, 254, 0.5)",
    tooltip_attr: str = "data-tooltip",
    excluded_closest_selectors: Sequence[str] = (),
    binding_guard_dataset_key: str | None = None,
    function_name: str = "initSharedQuickTooltips",
) -> tuple[str, str]:
    """Return the shared quick-tooltip CSS/runtime bundle for a surface.

    The visible contract stays centralized here so renderers only specify the
    tiny set of deltas that differ by surface, such as guard keys, exclusion
    selectors, or a slightly different border tint.
    """

    css = "\n\n".join(
        (
            dashboard_ui_primitives.quick_tooltip_surface_css(
                selector=selector,
                border_color=border_color,
            ),
            dashboard_ui_primitives.tooltip_typography_css(
                selector=selector,
            ),
        )
    )
    runtime = quick_tooltip_runtime_js(
        tooltip_attr=tooltip_attr,
        excluded_closest_selectors=excluded_closest_selectors,
        binding_guard_dataset_key=binding_guard_dataset_key,
        function_name=function_name,
    )
    return css, runtime


__all__ = [
    "quick_tooltip_bundle",
    "quick_tooltip_runtime_js",
]
