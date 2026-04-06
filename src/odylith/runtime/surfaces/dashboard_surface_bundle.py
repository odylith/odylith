"""Shared static-surface bundling helpers for installed dashboard tools.

This module keeps generated dashboard entrypoints on a single-page-per-surface
contract while separating presentation (HTML/CSS), data bootstrap, and control
runtime into explicit generated assets. Newer surfaces can keep the same HTML
entrypoint while treating the adjacent JS data asset as a lightweight manifest
that fans out into optional shard bundles loaded on demand.

Design constraints:
- local `file:` viewing must continue to work without a web server;
- renderers keep owning their exact DOM/CSS/JS behavior so UI/UX stays stable;
- the shared layer only externalizes payload/control bootstrapping and writes
  canonical adjacent assets.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import html
import json
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_INLINE_SCRIPT_RE = re.compile(r"<script>(?P<body>.*?)</script>", flags=re.DOTALL)


@dataclass(frozen=True)
class SurfaceBundlePaths:
    """Resolved generated asset paths for one dashboard surface."""

    html_path: Path
    payload_js_path: Path
    control_js_path: Path


@dataclass(frozen=True)
class SurfaceBundleSpec:
    """Specification describing how to externalize one renderer output."""

    asset_prefix: str
    payload_global_name: str
    control_bootstrap_snippet: str
    control_bootstrap_replacement: str
    embedded_json_script_id: str | None = None
    shell_embed_only: "ShellEmbedOnlySpec | None" = None


@dataclass(frozen=True)
class ShellEmbedOnlySpec:
    """Describe how an embedded tool canonicalizes top-level access back to the shell.

    The installed dashboard product is shell-owned: Radar, Atlas, Compass, Registry,
    and the shell are expected to render inside the tooling shell's dedicated
    iframes. Direct opens remain compatibility routes only, so this contract
    maps any standalone child-surface access back into `odylith/index.html` while
    preserving the surface-specific route state needed by the shell.
    """

    shell_tab: str
    shell_frame_id: str
    shell_href: str = "../index.html"
    query_passthrough: tuple[tuple[str, tuple[str, ...]], ...] = ()


def build_paths(*, output_path: Path, asset_prefix: str) -> SurfaceBundlePaths:
    """Return the canonical adjacent bundle asset paths for a surface."""

    output_dir = output_path.parent
    return SurfaceBundlePaths(
        html_path=output_path,
        payload_js_path=output_dir / f"{asset_prefix}-payload.v1.js",
        control_js_path=output_dir / f"{asset_prefix}-app.v1.js",
    )


def standard_surface_bundle_spec(
    *,
    asset_prefix: str,
    payload_global_name: str,
    embedded_json_script_id: str,
    bootstrap_binding_name: str,
    allow_missing_embedded_json: bool = False,
    replacement_fallback_expression: str = "{}",
    shell_tab: str | None = None,
    shell_frame_id: str | None = None,
    shell_href: str = "../index.html",
    query_passthrough: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> SurfaceBundleSpec:
    """Build the standard static-surface bundle contract used by Odylith dashboards."""

    text_accessor = f'document.getElementById("{embedded_json_script_id}").textContent'
    if allow_missing_embedded_json:
        control_bootstrap_snippet = (
            f'const {bootstrap_binding_name} = JSON.parse({text_accessor} || "{{}}");'
        )
    else:
        control_bootstrap_snippet = f'const {bootstrap_binding_name} = JSON.parse({text_accessor});'
    control_bootstrap_replacement = (
        f'const {bootstrap_binding_name} = window["{payload_global_name}"] || {replacement_fallback_expression};'
    )
    if bool(shell_tab) != bool(shell_frame_id):
        raise ValueError("shell_tab and shell_frame_id must be provided together")
    shell_embed_only = (
        ShellEmbedOnlySpec(
            shell_tab=str(shell_tab or "").strip(),
            shell_frame_id=str(shell_frame_id or "").strip(),
            shell_href=shell_href,
            query_passthrough=query_passthrough,
        )
        if shell_tab and shell_frame_id
        else None
    )
    return SurfaceBundleSpec(
        asset_prefix=asset_prefix,
        payload_global_name=payload_global_name,
        embedded_json_script_id=embedded_json_script_id,
        control_bootstrap_snippet=control_bootstrap_snippet,
        control_bootstrap_replacement=control_bootstrap_replacement,
        shell_embed_only=shell_embed_only,
    )


def render_payload_js(*, global_name: str, payload: Mapping[str, Any]) -> str:
    """Return a file-safe JS wrapper that exposes payload data on `window`."""

    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return (
        f"window[{json.dumps(global_name, ensure_ascii=False)}] = {payload_json};\n"
    )


def render_payload_merge_js(*, global_name: str, payload: Mapping[str, Any]) -> str:
    """Return JS that merges a shard payload into an existing window global."""

    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    quoted = json.dumps(global_name, ensure_ascii=False)
    return (
        f"window[{quoted}] = Object.assign(window[{quoted}] || {{}}, {payload_json});\n"
    )


def append_query_param(*, href: str, name: str, value: str) -> str:
    """Return `href` with one query param merged in without dropping existing params."""

    raw_href = str(href or "").strip()
    param_name = str(name or "").strip()
    param_value = str(value or "").strip()
    if not raw_href or not param_name or not param_value:
        return raw_href
    parts = urlsplit(raw_href)
    items = [(key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True) if key != param_name]
    items.append((param_name, param_value))
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(items, doseq=True),
            parts.fragment,
        )
    )


def _bundle_asset_version_token(*, payload_js: str, control_js: str) -> str:
    digest = hashlib.sha256()
    digest.update(payload_js.encode("utf-8"))
    digest.update(b"\0")
    digest.update(control_js.encode("utf-8"))
    return digest.hexdigest()[:12]


def _replace_embedded_json_script(
    *,
    html_text: str,
    script_id: str,
    payload_href: str,
) -> str:
    pattern = re.compile(
        rf'<script id="{re.escape(script_id)}" type="application/json">.*?</script>',
        flags=re.DOTALL,
    )
    replacement = (
        f'<script id="{html.escape(script_id, quote=True)}" '
        f'src="{html.escape(payload_href, quote=True)}"></script>'
    )
    updated, count = pattern.subn(replacement, html_text, count=1)
    if count != 1:
        raise ValueError(f"could not locate embedded json script id `{script_id}`")
    return updated


def _externalize_control_script(
    *,
    html_text: str,
    control_bootstrap_snippet: str,
    control_bootstrap_replacement: str,
    payload_href: str,
    control_href: str,
    has_separate_payload_script: bool,
) -> tuple[str, str]:
    replacement_block = (
        f'<script src="{html.escape(control_href, quote=True)}"></script>'
        if has_separate_payload_script
        else (
            f'<script src="{html.escape(payload_href, quote=True)}"></script>\n'
            f'  <script src="{html.escape(control_href, quote=True)}"></script>'
        )
    )

    for match in _INLINE_SCRIPT_RE.finditer(html_text):
        body = match.group("body")
        if control_bootstrap_snippet not in body:
            continue
        control_js = body.replace(control_bootstrap_snippet, control_bootstrap_replacement, 1).strip()
        updated_html = (
            html_text[: match.start()]
            + replacement_block
            + html_text[match.end() :]
        )
        return updated_html, f"{control_js}\n"
    raise ValueError("could not locate inline control script for surface bundle externalization")


def _render_shell_embed_guard(spec: ShellEmbedOnlySpec) -> str:
    """Return JS that forces child tools back into the canonical tooling shell.

    The guard only permits the surface to remain mounted when it is hosted
    inside the shell's expected iframe. Any other top-level or ad hoc embedded
    access is canonicalized back to the shell entrypoint so one product keeps
    one doorway. The emitted guard also exposes a redirect-in-progress signal so
    surfaces with async bootstrap work can fail closed while handoff to the
    shell is underway instead of logging transient fetch warnings.
    """

    rules = [
        {
            "target": target,
            "sources": list(sources),
        }
        for target, sources in spec.query_passthrough
    ]
    return (
        "const __ODYLITH_SHELL_REDIRECT_IN_PROGRESS__ = (function enforceShellOwnedSurfaceAccess() {\n"
        "  try {\n"
        f"    const expectedFrameId = {json.dumps(spec.shell_frame_id, ensure_ascii=False)};\n"
        "    const frameElement = window.frameElement;\n"
        "    const actualFrameId = frameElement && typeof frameElement.id === \"string\" ? frameElement.id : \"\";\n"
        "    if (window.parent && window.parent !== window && actualFrameId === expectedFrameId) {\n"
        "      return false;\n"
        "    }\n"
        f"    const shellUrl = new URL({json.dumps(spec.shell_href, ensure_ascii=False)}, window.location.href);\n"
        "    const currentParams = new URLSearchParams(window.location.search || \"\");\n"
        "    const nextParams = new URLSearchParams();\n"
        f"    nextParams.set(\"tab\", {json.dumps(spec.shell_tab, ensure_ascii=False)});\n"
        f"    const passthroughRules = {json.dumps(rules, ensure_ascii=False, separators=(',', ':'))};\n"
        "    for (const rule of passthroughRules) {\n"
        "      if (!rule || !rule.target) continue;\n"
        "      const sources = Array.isArray(rule.sources) && rule.sources.length ? rule.sources : [rule.target];\n"
        "      let selected = \"\";\n"
        "      for (const sourceKey of sources) {\n"
        "        const token = String(currentParams.get(sourceKey) || \"\").trim();\n"
        "        if (token) {\n"
        "          selected = token;\n"
        "          break;\n"
        "        }\n"
        "      }\n"
        "      if (selected) {\n"
        "        nextParams.set(rule.target, selected);\n"
        "      }\n"
        "    }\n"
        "    shellUrl.search = nextParams.toString() ? `?${nextParams.toString()}` : \"\";\n"
        "    shellUrl.hash = \"\";\n"
        "    if (window.__ODYLITH_SHELL_REDIRECTING__ === true && window.__ODYLITH_SHELL_REDIRECT_TARGET__ === shellUrl.toString()) {\n"
        "      return true;\n"
        "    }\n"
        "    const targetWindow = window.top && window.top !== window ? window.top : window;\n"
        "    if (targetWindow.location && targetWindow.location.href === shellUrl.toString()) {\n"
        "      return false;\n"
        "    }\n"
        "    window.__ODYLITH_SHELL_REDIRECTING__ = true;\n"
        "    window.__ODYLITH_SHELL_REDIRECT_TARGET__ = shellUrl.toString();\n"
        "    if (typeof window.stop === \"function\") {\n"
        "      window.stop();\n"
        "    }\n"
        "    targetWindow.location.replace(shellUrl.toString());\n"
        "    return true;\n"
        "  } catch (_error) {\n"
        "    // Fail open so renderer-local logic can still surface diagnostics if the shell route cannot be resolved.\n"
        "    return false;\n"
        "  }\n"
        "})();\n\n"
    )


def _render_shell_embed_inline_guard(spec: ShellEmbedOnlySpec) -> str:
    """Return a minimal inline guard that runs before child-surface scripts load."""

    rules = [
        {
            "target": target,
            "sources": list(sources),
        }
        for target, sources in spec.query_passthrough
    ]
    return (
        "<script>\n"
        "(function enforceShellOwnedSurfaceAccessInline() {\n"
        "  try {\n"
        f"    const expectedFrameId = {json.dumps(spec.shell_frame_id, ensure_ascii=False)};\n"
        "    const frameElement = window.frameElement;\n"
        "    const actualFrameId = frameElement && typeof frameElement.id === \"string\" ? frameElement.id : \"\";\n"
        "    if (window.parent && window.parent !== window && actualFrameId === expectedFrameId) {\n"
        "      return;\n"
        "    }\n"
        f"    const shellUrl = new URL({json.dumps(spec.shell_href, ensure_ascii=False)}, window.location.href);\n"
        "    const currentParams = new URLSearchParams(window.location.search || \"\");\n"
        "    const nextParams = new URLSearchParams();\n"
        f"    nextParams.set(\"tab\", {json.dumps(spec.shell_tab, ensure_ascii=False)});\n"
        f"    const passthroughRules = {json.dumps(rules, ensure_ascii=False, separators=(',', ':'))};\n"
        "    for (const rule of passthroughRules) {\n"
        "      if (!rule || !rule.target) continue;\n"
        "      const sources = Array.isArray(rule.sources) && rule.sources.length ? rule.sources : [rule.target];\n"
        "      let selected = \"\";\n"
        "      for (const sourceKey of sources) {\n"
        "        const token = String(currentParams.get(sourceKey) || \"\").trim();\n"
        "        if (token) {\n"
        "          selected = token;\n"
        "          break;\n"
        "        }\n"
        "      }\n"
        "      if (selected) {\n"
        "        nextParams.set(rule.target, selected);\n"
        "      }\n"
        "    }\n"
        "    shellUrl.search = nextParams.toString() ? `?${nextParams.toString()}` : \"\";\n"
        "    shellUrl.hash = \"\";\n"
        "    if (window.__ODYLITH_SHELL_REDIRECTING__ === true && window.__ODYLITH_SHELL_REDIRECT_TARGET__ === shellUrl.toString()) {\n"
        "      return;\n"
        "    }\n"
        "    const targetWindow = window.top && window.top !== window ? window.top : window;\n"
        "    if (targetWindow.location && targetWindow.location.href === shellUrl.toString()) {\n"
        "      return;\n"
        "    }\n"
        "    window.__ODYLITH_SHELL_REDIRECTING__ = true;\n"
        "    window.__ODYLITH_SHELL_REDIRECT_TARGET__ = shellUrl.toString();\n"
        "    if (typeof window.stop === \"function\") {\n"
        "      window.stop();\n"
        "    }\n"
        "    targetWindow.location.replace(shellUrl.toString());\n"
        "  } catch (_error) {\n"
        "    // Fail open so embedded surfaces can still load if canonical shell handoff cannot be resolved.\n"
        "  }\n"
        "})();\n"
        "</script>"
    )


def _inject_shell_embed_inline_guard(*, html_text: str, spec: ShellEmbedOnlySpec) -> str:
    """Insert the shell redirect guard before the first surface script tag."""

    marker = "<script"
    index = html_text.find(marker)
    if index == -1:
        raise ValueError("could not locate script tag for shell embed guard injection")
    guard = _render_shell_embed_inline_guard(spec)
    return f"{html_text[:index]}{guard}\n  {html_text[index:]}"


def externalize_surface_bundle(
    *,
    html_text: str,
    payload: Mapping[str, Any],
    paths: SurfaceBundlePaths,
    spec: SurfaceBundleSpec,
) -> tuple[str, str, str]:
    """Split one renderer-local HTML output into HTML + payload JS + control JS."""

    payload_href = paths.payload_js_path.name
    control_href = paths.control_js_path.name

    has_separate_payload_script = spec.embedded_json_script_id is not None
    updated_html = html_text
    if spec.embedded_json_script_id is not None:
        updated_html = _replace_embedded_json_script(
            html_text=updated_html,
            script_id=spec.embedded_json_script_id,
            payload_href=payload_href,
        )

    updated_html, control_js = _externalize_control_script(
        html_text=updated_html,
        control_bootstrap_snippet=spec.control_bootstrap_snippet,
        control_bootstrap_replacement=spec.control_bootstrap_replacement,
        payload_href=payload_href,
        control_href=control_href,
        has_separate_payload_script=has_separate_payload_script,
    )
    if spec.shell_embed_only is not None:
        updated_html = _inject_shell_embed_inline_guard(
            html_text=updated_html,
            spec=spec.shell_embed_only,
        )
        control_js = _render_shell_embed_guard(spec.shell_embed_only) + control_js
    payload_js = render_payload_js(
        global_name=spec.payload_global_name,
        payload=payload,
    )
    asset_version = _bundle_asset_version_token(payload_js=payload_js, control_js=control_js)
    versioned_payload_href = append_query_param(href=payload_href, name="v", value=asset_version)
    versioned_control_href = append_query_param(href=control_href, name="v", value=asset_version)
    updated_html = updated_html.replace(
        f'src="{html.escape(payload_href, quote=True)}"',
        f'src="{html.escape(versioned_payload_href, quote=True)}"',
    )
    updated_html = updated_html.replace(
        f'src="{html.escape(control_href, quote=True)}"',
        f'src="{html.escape(versioned_control_href, quote=True)}"',
    )
    return updated_html, payload_js, control_js
