const __ODYLITH_SHELL_REDIRECT_IN_PROGRESS__ = (function enforceShellOwnedSurfaceAccess() {
  try {
    const expectedFrameId = "frame-compass";
    const frameElement = window.frameElement;
    const actualFrameId = frameElement && typeof frameElement.id === "string" ? frameElement.id : "";
    if (window.parent && window.parent !== window && actualFrameId === expectedFrameId) {
      return false;
    }
    const shellUrl = new URL("../index.html", window.location.href);
    const currentParams = new URLSearchParams(window.location.search || "");
    const nextParams = new URLSearchParams();
    nextParams.set("tab", "compass");
    const passthroughRules = [{"target":"scope","sources":["scope","workstream"]},{"target":"window","sources":["window"]},{"target":"date","sources":["date"]},{"target":"audit_day","sources":["audit_day"]}];
    for (const rule of passthroughRules) {
      if (!rule || !rule.target) continue;
      const sources = Array.isArray(rule.sources) && rule.sources.length ? rule.sources : [rule.target];
      let selected = "";
      for (const sourceKey of sources) {
        const token = String(currentParams.get(sourceKey) || "").trim();
        if (token) {
          selected = token;
          break;
        }
      }
      if (selected) {
        nextParams.set(rule.target, selected);
      }
    }
    shellUrl.search = nextParams.toString() ? `?${nextParams.toString()}` : "";
    shellUrl.hash = "";
    if (window.__ODYLITH_SHELL_REDIRECTING__ === true && window.__ODYLITH_SHELL_REDIRECT_TARGET__ === shellUrl.toString()) {
      return true;
    }
    const targetWindow = window.top && window.top !== window ? window.top : window;
    if (targetWindow.location && targetWindow.location.href === shellUrl.toString()) {
      return false;
    }
    window.__ODYLITH_SHELL_REDIRECTING__ = true;
    window.__ODYLITH_SHELL_REDIRECT_TARGET__ = shellUrl.toString();
    if (typeof window.stop === "function") {
      window.stop();
    }
    targetWindow.location.replace(shellUrl.toString());
    return true;
  } catch (_error) {
    // Fail open so renderer-local logic can still surface diagnostics if the shell route cannot be resolved.
    return false;
  }
})();

const SHELL = window["__ODYLITH_COMPASS_SHELL_DATA__"] || {};
window.__ODYLITH_COMPASS_SHELL__ = SHELL && typeof SHELL === "object" ? SHELL : {};
init();
