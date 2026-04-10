const __ODYLITH_SHELL_REDIRECT_IN_PROGRESS__ = (function enforceShellOwnedSurfaceAccess() {
  try {
    const expectedFrameId = "frame-registry";
    const frameElement = window.frameElement;
    const actualFrameId = frameElement && typeof frameElement.id === "string" ? frameElement.id : "";
    if (window.parent && window.parent !== window && actualFrameId === expectedFrameId) {
      return false;
    }
    const shellUrl = new URL("../index.html", window.location.href);
    const currentParams = new URLSearchParams(window.location.search || "");
    const nextParams = new URLSearchParams();
    nextParams.set("tab", "registry");
    const passthroughRules = [{"target":"component","sources":["component"]}];
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

const DATA = window["__ODYLITH_REGISTRY_DATA__"] || {};
    const payload = DATA;
    const assetLoadCache = new Map();
    const listEl = document.getElementById("componentList");
    const detailEl = document.getElementById("detail");
    const timelineEl = document.getElementById("timeline");
    const timelineCountEl = document.getElementById("timelineCount");
    const searchEl = document.getElementById("search");
    const resetFiltersEl = document.getElementById("resetFilters");
    const kpisEl = document.getElementById("kpis");
    const qualificationFilterEl = document.getElementById("qualificationFilter");
    const categoryFilterEl = document.getElementById("categoryFilter");
    const diagnosticsEl = document.getElementById("diagnostics");
    const diagListEl = document.getElementById("diagList");

    const allComponents = Array.isArray(payload.components) ? payload.components.slice() : [];
    const REGISTRY_LIST_WINDOW_THRESHOLD = 160;
    const REGISTRY_LIST_OVERSCAN = 20;
    const REGISTRY_LIST_ROW_HEIGHT = 86;
    const REGISTRY_LIST_HEADER_HEIGHT = 30;
    let latestRenderedComponents = [];
    let latestListWindowKey = "";
    let listScrollFrame = 0;
    let activeQualification = "all";
    let activeCategory = "all";

    function loadScriptAsset(href) {
      const token = String(href || "").trim();
      if (!token) return Promise.resolve();
      const resolvedHref = new URL(token, window.location.href).toString();
      if (assetLoadCache.has(resolvedHref)) {
        return assetLoadCache.get(resolvedHref);
      }
      const promise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = resolvedHref;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`failed to load asset ${resolvedHref}`));
        document.head.appendChild(script);
      });
      assetLoadCache.set(resolvedHref, promise);
      return promise;
    }

    function detailManifest() {
      const manifest = payload.detail_manifest;
      return manifest && typeof manifest === "object" ? manifest : {};
    }

    async function loadDetailEntry(componentId) {
      const token = String(componentId || "").trim().toLowerCase();
      if (!token) return null;
      const loaded = window.__ODYLITH_REGISTRY_DETAIL_SHARDS__ || {};
      if (loaded[token] && typeof loaded[token] === "object") {
        return loaded[token];
      }
      const shardHref = String(detailManifest()[token] || "").trim();
      if (!shardHref) return null;
      await loadScriptAsset(shardHref);
      const resolved = window.__ODYLITH_REGISTRY_DETAIL_SHARDS__ || {};
      return resolved[token] && typeof resolved[token] === "object" ? resolved[token] : null;
    }

    async function loadRuntimePayload(path, params = {}) {
      const dataSource = payload.data_source && typeof payload.data_source === "object" ? payload.data_source : {};
      const base = String(dataSource.runtime_base_url || "").trim();
      const protocol = String(window.location.protocol || "").toLowerCase();
      if (!base || protocol === "file:") return null;
      try {
        const url = new URL(path.replace(/^\/+/, ""), base.endsWith("/") ? base : `${base}/`);
        Object.entries(params || {}).forEach(([key, value]) => {
          if (value === undefined || value === null || value === "") return;
          url.searchParams.set(key, String(value));
        });
        const response = await fetch(url.toString(), { headers: { "Accept": "application/json" } });
        if (!response.ok) return null;
        return await response.json();
      } catch (_error) {
        return null;
      }
    }

    function createStaticSnapshotRegistryDataSource() {
      return {
        backend: "staticSnapshot",
        async loadManifest() {
          return detailManifest();
        },
        async loadList(_params = {}) {
          return allComponents.slice();
        },
        async loadDetail(id) {
          return loadDetailEntry(id);
        },
        async loadDocument(_request = {}) {
          return null;
        },
        prefetch(id) {
          void loadDetailEntry(id);
        },
      };
    }

    function createRuntimeRegistryDataSource() {
      const fallback = createStaticSnapshotRegistryDataSource();
      return {
        backend: "runtime",
        async loadManifest() {
          const runtimePayload = await loadRuntimePayload("surfaces/registry/manifest");
          if (runtimePayload && typeof runtimePayload === "object") return runtimePayload;
          return fallback.loadManifest();
        },
        async loadList(params = {}) {
          const runtimePayload = await loadRuntimePayload("surfaces/registry/list", params);
          if (runtimePayload && Array.isArray(runtimePayload.components)) return runtimePayload.components;
          return fallback.loadList(params);
        },
        async loadDetail(id) {
          const runtimePayload = await loadRuntimePayload("surfaces/registry/detail", { component: id });
          if (runtimePayload && typeof runtimePayload === "object") return runtimePayload;
          return fallback.loadDetail(id);
        },
        async loadDocument(request = {}) {
          const runtimePayload = await loadRuntimePayload("surfaces/registry/document", request);
          if (runtimePayload && typeof runtimePayload === "object") return runtimePayload;
          return fallback.loadDocument(request);
        },
        prefetch(id) {
          void this.loadDetail(id);
        },
      };
    }

    function createRegistryDataSource() {
      const dataSource = payload.data_source && typeof payload.data_source === "object" ? payload.data_source : {};
      const preferred = String(dataSource.preferred_backend || "").trim();
      if (preferred === "runtime") {
        return createRuntimeRegistryDataSource();
      }
      return createStaticSnapshotRegistryDataSource();
    }

    const registryDataSource = createRegistryDataSource();

    function initSharedQuickTooltips() {
  const QUICK_TOOLTIP_BIND_KEY = null;
  if (QUICK_TOOLTIP_BIND_KEY && document.body && document.body.dataset[QUICK_TOOLTIP_BIND_KEY] === "1") {
    return;
  }
  if (QUICK_TOOLTIP_BIND_KEY && document.body) {
    document.body.dataset[QUICK_TOOLTIP_BIND_KEY] = "1";
  }

  const QUICK_TOOLTIP_ATTR = "data-tooltip";
  const QUICK_TOOLTIP_EXCLUDE_CLOSEST = [".component-btn"];
  const TOOLTIP_OFFSET_X = 12;
  const TOOLTIP_OFFSET_Y = 14;
  const tooltipEl = document.createElement("div");
  tooltipEl.className = "quick-tooltip";
  tooltipEl.hidden = true;
  tooltipEl.setAttribute("role", "tooltip");
  document.body.appendChild(tooltipEl);
  let tooltipTarget = null;

  function tooltipTextFromNode(node) {
    if (!node) return "";
    return String(node.getAttribute(QUICK_TOOLTIP_ATTR) || "").trim();
  }

  function shouldIgnoreTooltipNode(node) {
    if (!(node instanceof Element)) return true;
    return QUICK_TOOLTIP_EXCLUDE_CLOSEST.some((selector) => {
      if (!selector) return false;
      try {
        return Boolean(node.closest(selector));
      } catch (_error) {
        return false;
      }
    });
  }

  function tooltipNodeFromEventTarget(target) {
    const node = target instanceof Element ? target.closest(`[${QUICK_TOOLTIP_ATTR}]`) : null;
    if (!node || shouldIgnoreTooltipNode(node)) {
      return null;
    }
    return node;
  }

  function positionTooltip(clientX, clientY) {
    const x = Number.isFinite(clientX) ? clientX : 0;
    const y = Number.isFinite(clientY) ? clientY : 0;
    const maxX = Math.max(8, window.innerWidth - tooltipEl.offsetWidth - 8);
    const maxY = Math.max(8, window.innerHeight - tooltipEl.offsetHeight - 8);
    const left = Math.min(maxX, Math.max(8, x + TOOLTIP_OFFSET_X));
    const top = Math.min(maxY, Math.max(8, y + TOOLTIP_OFFSET_Y));
    tooltipEl.style.left = `${left}px`;
    tooltipEl.style.top = `${top}px`;
  }

  function hideTooltip() {
    tooltipTarget = null;
    tooltipEl.classList.remove("visible");
    tooltipEl.hidden = true;
    tooltipEl.textContent = "";
  }

  function showTooltip(node, clientX, clientY) {
    const text = tooltipTextFromNode(node);
    if (!text) {
      hideTooltip();
      return;
    }
    tooltipTarget = node;
    tooltipEl.textContent = text;
    tooltipEl.hidden = false;
    positionTooltip(clientX, clientY);
    tooltipEl.classList.add("visible");
  }

  document.addEventListener("pointerover", (event) => {
    const node = tooltipNodeFromEventTarget(event.target);
    if (!node) return;
    showTooltip(node, event.clientX, event.clientY);
  });

  document.addEventListener("pointermove", (event) => {
    if (!tooltipTarget) return;
    positionTooltip(event.clientX, event.clientY);
  });

  document.addEventListener("pointerout", (event) => {
    if (!tooltipTarget) return;
    const related = event.relatedTarget;
    if (related instanceof Element && tooltipTarget.contains(related)) {
      return;
    }
    if (event.target instanceof Element && !tooltipTarget.contains(event.target)) {
      return;
    }
    hideTooltip();
  });

  document.addEventListener("focusin", (event) => {
    const node = tooltipNodeFromEventTarget(event.target);
    if (!node) return;
    const rect = node.getBoundingClientRect();
    showTooltip(node, rect.left + (rect.width / 2), rect.top);
  });

  document.addEventListener("focusout", () => {
    hideTooltip();
  });
}

initSharedQuickTooltips();

    function escapeHtml(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function humanizeToken(token) {
      return String(token || "")
        .replace(/_/g, " ")
        .replace(/-/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .replace(/\b\w/g, (m) => m.toUpperCase()) || "Unknown";
    }

    function pluralize(count, singular, plural) {
      return Number(count) === 1 ? singular : plural;
    }

    function clipText(value, limit = 180) {
      const raw = String(value || "").replace(/\s+/g, " ").trim();
      if (!raw || raw.length <= limit) return raw;
      const hard = Math.max(16, limit - 3);
      const boundary = raw.lastIndexOf(" ", hard);
      const cut = boundary > Math.floor(hard * 0.6) ? boundary : hard;
      return `${raw.slice(0, cut).replace(/[ ,;:-]+$/, "")}...`;
    }

    function normalizedEventKind(event) {
      return String(event && event.kind || "").trim().toLowerCase();
    }

    function isWorkspaceActivityEvent(event) {
      return normalizedEventKind(event) === "workspace_activity";
    }

    function isBaselineTimelineEvent(event) {
      return normalizedEventKind(event) === "feature_history";
    }

    function isExplicitTimelineEvent(event) {
      const kind = normalizedEventKind(event);
      return Boolean(kind) && kind !== "workspace_activity" && kind !== "feature_history";
    }

    function isSyntheticTimelineEvent(event) {
      return isWorkspaceActivityEvent(event);
    }

    function ensureSentence(value, fallback = "") {
      const raw = String(value || "").replace(/\s+/g, " ").trim();
      if (!raw) return String(fallback || "").trim();
      return /[.!?]$/.test(raw) ? raw : `${raw}.`;
    }

    function naturalList(values) {
      const items = (Array.isArray(values) ? values : [])
        .map((value) => String(value || "").trim())
        .filter(Boolean);
      if (!items.length) return "";
      if (items.length === 1) return items[0];
      if (items.length === 2) return `${items[0]} and ${items[1]}`;
      return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
    }

    function forensicCoverageLabel(coverage) {
      const status = String(coverage && coverage.status || "").trim().toLowerCase();
      if (status === "forensic_coverage_present") return "Forensic coverage present";
      if (status === "baseline_forensic_only") return "Baseline forensic only";
      if (status === "tracked_but_evidence_empty") return "Tracked but evidence-empty";
      return "Forensic coverage unknown";
    }

    function forensicCoverageReasonLabel(reason) {
      const token = String(reason || "").trim().toLowerCase();
      if (token === "no_explicit_event") return "no explicit event";
      if (token === "no_recent_path_match") return "no recent path match";
      if (token === "no_mapped_workstream_evidence") return "no mapped workstream evidence";
      return humanizeToken(token);
    }

    function forensicCoverageSummary(coverage) {
      const row = coverage && typeof coverage === "object" ? coverage : {};
      const status = String(row.status || "").trim().toLowerCase();
      const label = forensicCoverageLabel(row);
      const emptyReasons = Array.isArray(row.empty_reasons) ? row.empty_reasons.map(forensicCoverageReasonLabel).filter(Boolean) : [];
      const specHistoryCount = Number(row.spec_history_event_count || 0);
      if (status === "tracked_but_evidence_empty") {
        return emptyReasons.length
          ? `${label}: ${ensureSentence(naturalList(emptyReasons))}`
          : `${label}: no mapped forensic evidence channels are currently attached.`;
      }
      if (status === "baseline_forensic_only") {
        const historySummary = `${specHistoryCount} documented spec history ${pluralize(specHistoryCount, "checkpoint", "checkpoints")}`;
        return emptyReasons.length
          ? `${label}: ${historySummary}. Live evidence gaps: ${ensureSentence(naturalList(emptyReasons))}`
          : `${label}: ${historySummary}.`;
      }
      const explicitCount = Number(row.explicit_event_count || 0);
      const recentPathMatchCount = Number(row.recent_path_match_count || 0);
      const mappedWorkstreamEvidenceCount = Number(row.mapped_workstream_evidence_count || 0);
      return `${label}: explicit events ${explicitCount} · recent path matches ${recentPathMatchCount} · mapped workstream evidence ${mappedWorkstreamEvidenceCount} · spec history checkpoints ${specHistoryCount}.`;
    }

    function intelligenceConfidence(explicitCount, syntheticCount, workstreamCount, baselineCount = 0) {
      const explicit = Number(explicitCount || 0);
      const synthetic = Number(syntheticCount || 0);
      const workstreams = Number(workstreamCount || 0);
      const baseline = Number(baselineCount || 0);
      if (explicit >= 2 && workstreams > 0) return "High";
      if (explicit >= 1) return "Medium";
      if (synthetic > 0 || workstreams > 0) return "Low";
      if (baseline > 0) return "Low";
      return "Low";
    }

    function latestExplicitEvent(events) {
      return (Array.isArray(events) ? events : []).find((event) => isExplicitTimelineEvent(event)) || null;
    }

    function basenamePath(value) {
      const raw = String(value || "").trim().replace(/\\/g, "/");
      if (!raw) return "";
      const parts = raw.split("/").filter(Boolean);
      return parts.length ? parts[parts.length - 1] : raw;
    }

    function truthRootToken(value) {
      return String(value || "").trim().replace(/\\/g, "/").replace(/^\.\//, "").replace(/\/+$/, "");
    }

    function workspaceArtifactLabel(path) {
      const raw = String(path || "").trim();
      const truthRoots = DATA.consumer_truth_roots && typeof DATA.consumer_truth_roots === "object"
        ? DATA.consumer_truth_roots
        : {};
      const componentSpecsRoot = truthRootToken(truthRoots.component_specs);
      const runbooksRoot = truthRootToken(truthRoots.runbooks);
      if (!raw) return "";
      if (raw.startsWith("contracts/") || raw.startsWith("odylith/runtime/contracts/")) return "contract artifacts";
      if (raw.startsWith("odylith/registry/source/components/") && raw.endsWith("/FORENSICS.v1.json")) return "component forensics";
      if (componentSpecsRoot && componentSpecsRoot !== "odylith" && raw.startsWith(`${componentSpecsRoot}/`)) return "component spec";
      if (raw.startsWith("odylith/registry/source/components/") && raw.endsWith("/CURRENT_SPEC.md")) return "component spec";
      if (raw.startsWith("odylith/") && (raw.endsWith("/SPEC.md") || raw.endsWith("_SPEC.md"))) return "component spec";
      if (runbooksRoot && runbooksRoot !== "odylith" && raw.startsWith(`${runbooksRoot}/`)) return "runbook";
      if (raw.startsWith("src/odylith/runtime/")) return "odylith product code";
      if (raw.startsWith("odylith/")) return "odylith artifacts";
      return basenamePath(raw);
    }

    function compactNarrativeSummary(value, limit = 110) {
      const raw = String(value || "").replace(/\s+/g, " ").trim();
      if (!raw) return "";
      const prefix = "Recent workspace activity across tracked paths:";
      if (!raw.toLowerCase().startsWith(prefix.toLowerCase())) {
        return clipText(raw, limit);
      }

      let remainder = raw.slice(prefix.length).trim();
      let moreCount = 0;
      const moreMatch = remainder.match(/\+\s*(\d+)\s+more$/i);
      if (moreMatch) {
        moreCount = Number(moreMatch[1] || 0);
        remainder = remainder.slice(0, moreMatch.index).trim().replace(/[,\s]+$/, "");
      }

      const rawPaths = remainder
        .split(",")
        .map((token) => String(token || "").trim())
        .filter(Boolean);
      const labels = [];
      const seen = new Set();
      rawPaths.forEach((path) => {
        const label = workspaceArtifactLabel(path);
        if (!label || seen.has(label)) return;
        seen.add(label);
        labels.push(label);
      });
      const preview = labels.slice(0, 3);
      if (!preview.length) {
        return moreCount > 0
          ? `tracked component artifacts changed (+${moreCount} more)`
          : "tracked component artifacts changed";
      }
      const overflow = Math.max(0, labels.length - preview.length) + moreCount;
      return overflow > 0
        ? `${naturalList(preview)} changed (+${overflow} more)`
        : `${naturalList(preview)} changed`;
    }

    function summarizeOperatingShift(context) {
      const componentName = String(context.componentName || "This component").trim() || "This component";
      const latestObservedSummary = compactNarrativeSummary(context.latestSummary || "", 120);
      const latestExplicitSummary = compactNarrativeSummary(
        context.latestExplicit && context.latestExplicit.summary || "",
        120,
      );
      const primaryWorkstream = String(context.primaryWorkstream || "").trim();
      if (!context.latestEvent) {
        return `No mapped signal exists yet for ${componentName}; Registry is still under-observing this component.`;
      }
      if (!context.explicitCount && context.syntheticCount > 0) {
        return `Execution is touching ${componentName}, but the decision trail is missing. Latest observed move: ${latestObservedSummary}`;
      }
      if (context.hasImplementationSignal && context.hasDecisionSignal) {
        return primaryWorkstream
          ? `${componentName} is in governed execution on ${primaryWorkstream}. Latest explicit move: ${latestExplicitSummary || latestObservedSummary}`
          : `${componentName} is in governed execution, but the active workstream binding is incomplete. Latest explicit move: ${latestExplicitSummary || latestObservedSummary}`;
      }
      if (context.hasImplementationSignal) {
        return primaryWorkstream
          ? `${componentName} has moved into implementation on ${primaryWorkstream}. Latest explicit move: ${latestExplicitSummary || latestObservedSummary}`
          : `${componentName} has moved into implementation, but Registry still lacks a clean workstream binding. Latest explicit move: ${latestExplicitSummary || latestObservedSummary}`;
      }
      if (context.hasDecisionSignal) {
        return primaryWorkstream
          ? `${componentName} is being reshaped by active governance decisions on ${primaryWorkstream}. Latest decision: ${latestExplicitSummary || latestObservedSummary}`
          : `${componentName} is being reshaped by governance decisions ahead of implementation. Latest decision: ${latestExplicitSummary || latestObservedSummary}`;
      }
      if (context.latestExplicit) {
        return `${componentName} is active through explicit execution checkpoints. Latest checkpoint: ${latestExplicitSummary || latestObservedSummary}`;
      }
      return `${componentName} has recent mapped activity, but Registry still lacks a clear operating narrative. Latest signal: ${latestObservedSummary}`;
    }

    function summarizeDeliveryImpact(context) {
      const whyTracked = ensureSentence(
        context.whyTracked,
        "This component is tracked for delivery governance accountability."
      );
      if (!context.latestEvent) {
        return whyTracked;
      }
      if (!context.explicitCount && context.syntheticCount > 0) {
        return `${whyTracked} Right now that impact is visible through execution churn rather than an explicit governance checkpoint.`;
      }
      if (context.primaryWorkstream) {
        return `${whyTracked} Current delivery pressure is concentrating on ${context.primaryWorkstream}${context.workstreamOverflow > 0 ? ` and ${context.workstreamOverflow} related workstream${context.workstreamOverflow === 1 ? "" : "s"}` : ""}.`;
      }
      return `${whyTracked} The impact is real, but the active workstream boundary is still weakly attached in the evidence trail.`;
    }

    function summarizeGovernancePosture(context) {
      if (!context.latestEvent) {
        return "No governance posture can be inferred yet because Registry has no mapped component evidence.";
      }
      if (!context.explicitCount && context.syntheticCount > 0) {
        return "Weak posture: active edits are present, but no explicit decision, implementation, or execution checkpoint is mapped yet.";
      }
      if (context.explicitCount > 0 && !context.allWorkstreams.length) {
        return "Partial posture: explicit checkpoints exist, but they are not bound to a workstream, so cross-surface traceability is incomplete.";
      }
      if (context.explicitCount > 0 && context.syntheticCount > context.explicitCount) {
        return "Mixed posture: explicit governance exists, but local change is still outrunning the clean decision trail.";
      }
      if (context.explicitCount > 0 && context.allWorkstreams.length) {
        return "Strong posture: explicit checkpoints, workstream linkage, and forensic evidence are aligned for this component.";
      }
      return "Mapped activity is present, but the governance picture is still incomplete.";
    }

    function summarizeCrossSurfaceImpact(context) {
      const surfaces = [];
      if (context.workstreamPreview.length) {
        surfaces.push(`Radar workstreams ${context.workstreamPreview.join(", ")}${context.workstreamOverflow > 0 ? ` (+${context.workstreamOverflow})` : ""}`);
      }
      if (context.diagramPreview.length) {
        surfaces.push(`Atlas diagrams ${context.diagramPreview.join(", ")}${context.diagramOverflow > 0 ? ` (+${context.diagramOverflow})` : ""}`);
      }
      if (context.timelineEvents.length) {
        surfaces.push("Compass-linked evidence");
      }
      if (context.specPath) {
        surfaces.push("Registry living spec");
      }
      if (context.specRunbooks.length) {
        surfaces.push("runbooks");
      }
      if (context.specDeveloperDocs.length) {
        surfaces.push("developer docs");
      }
      if (!surfaces.length) {
        return "Cross-surface traceability is still thin; this component currently resolves mainly inside Registry.";
      }
      return `This component currently propagates into ${naturalList(surfaces)}.`;
    }

    function summarizeNextMove(context) {
      if (!context.latestEvent) {
        return "Capture the first explicit component checkpoint before relying on Registry for delivery interpretation.";
      }
      if (!context.explicitCount && context.syntheticCount > 0) {
        return "Log an explicit Compass decision or implementation checkpoint and attach the correct workstream before treating this as governed progress.";
      }
      if (context.explicitCount > 0 && !context.allWorkstreams.length) {
        return "Bind the next explicit checkpoint to the active workstream so Radar, Atlas, and Registry stay aligned.";
      }
      if (
        context.hasImplementationSignal &&
        !context.hasDecisionSignal &&
        (context.categoryToken === "governance_surface" || context.categoryToken === "governance_engine" || context.categoryToken === "control_gate")
      ) {
        return "Backfill explicit rationale if this implementation changes operator workflow, policy behavior, or delivery boundaries.";
      }
      if (context.hasDecisionSignal && !context.hasImplementationSignal && context.syntheticCount > 0) {
        return "Close the gap between decision capture and active edits before this component drifts into unguided implementation.";
      }
      return "Keep explicit checkpoints current as work closes and use Forensic Evidence to verify the final delivery state.";
    }

    function deliveryIntelligencePayload() {
      const payload = DATA.delivery_intelligence;
      return payload && typeof payload === "object" ? payload : {};
    }

    function intelligenceScope(scopeType, scopeId) {
      const token = String(scopeId || "").trim();
      if (!token) return null;
      const payload = deliveryIntelligencePayload();
      const bucket = payload[`${scopeType}s`];
      if (!bucket || typeof bucket !== "object") return null;
      const row = bucket[token];
      return row && typeof row === "object" ? row : null;
    }

    function componentIntelligenceSnapshot(componentId) {
      return intelligenceScope("component", componentId);
    }

    function scopeSignal(snapshot) {
      const value = snapshot && typeof snapshot.scope_signal === "object" ? snapshot.scope_signal : {};
      return value && typeof value === "object" ? value : {};
    }

    function scopeSignalRank(snapshot) {
      const signal = scopeSignal(snapshot);
      const numeric = Number(signal.rank);
      if (Number.isFinite(numeric)) return numeric;
      const rung = String(signal.rung || "").trim().toUpperCase();
      if (/^R\d+$/.test(rung)) return Number.parseInt(rung.slice(1), 10);
      return 0;
    }

    function registryComponentHref(componentId) {
      const token = String(componentId || "").trim();
      if (!token) return "../index.html?tab=registry";
      return `../index.html?tab=registry&component=${encodeURIComponent(token)}`;
    }

    function toneClassForCategory(category) {
      const token = String(category || "").trim().toLowerCase();
      if (token === "governance_surface") return "tone-gov";
      if (token === "governance_engine" || token === "control_gate") return "tone-engine";
      if (token === "infrastructure") return "tone-infra";
      if (token === "data") return "tone-data";
      return "";
    }

    function categoryDescription(category) {
      const token = String(category || "").trim().toLowerCase();
      if (token === "governance_surface") return "User-facing governance surfaces for planning, architecture, execution, and registry views.";
      if (token === "governance_engine") return "Shared governance intelligence and orchestration logic used across surfaces.";
      if (token === "control_gate") return "Validation and policy gates that enforce fail-closed governance behavior.";
      if (token === "infrastructure") return "Underlying cloud/runtime systems that host and execute the platform.";
      if (token === "data") return "Data-plane entities such as topics and interface contracts.";
      return "Component category used for inventory grouping.";
    }

    function productLayerLabel(layer) {
      const token = String(layer || "").trim().toLowerCase();
      if (!token) return "Unspecified";
      if (token === "shell_host") return "Shell Host";
      if (token === "evidence_surface") return "Evidence Surface";
      if (token === "memory_retrieval") return "Memory / Retrieval";
      if (token === "intelligence") return "Intelligence";
      if (token === "agent_execution") return "Agent Execution";
      if (token === "cli_bootstrap") return "CLI / Bootstrap";
      if (token === "optional_remote_control_plane") return "Optional Remote Control Plane";
      if (token === "consumer_distro") return "Consumer Distro";
      return token.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
    }

    function productLayerDescription(layer) {
      const token = String(layer || "").trim().toLowerCase();
      if (token === "shell_host") return "Owns the top-level Odylith shell and host routing surface.";
      if (token === "evidence_surface") return "Owns one of the operator-facing evidence and inspection surfaces.";
      if (token === "memory_retrieval") return "Owns the derived local memory, sparse recall, packet compaction, and dense-context telemetry substrate.";
      if (token === "intelligence") return "Owns case-building, reasoning, or remediation intelligence inside Odylith.";
      if (token === "agent_execution") return "Owns bounded agent routing, orchestration, or host-execution behavior.";
      if (token === "cli_bootstrap") return "Owns install, bootstrap, or operator command-entry boundaries for Odylith.";
      if (token === "optional_remote_control_plane") return "Owns optional remote/public-admin control-plane behavior attached to Odylith.";
      if (token === "consumer_distro") return "Owns consumer-specific compatibility readers and distro behavior over the neutral Odylith core.";
      return "Odylith product-layer placement for this component.";
    }

    function qualificationDescription(token) {
      const normalized = String(token || "").trim().toLowerCase();
      if (normalized === "curated") return "Approved first-class component record in the manifest.";
      if (normalized === "candidate") return "Reviewed candidate awaiting final lifecycle qualification.";
      return "Component qualification level.";
    }

    function eventKindLabel(kind) {
      const token = String(kind || "").trim();
      const normalized = token.toLowerCase();
      if (normalized === "feature_history") return "Feature history";
      if (normalized === "workspace_activity") return "Workspace activity";
      return token || "event";
    }

    function componentSearchText(row) {
      const aliases = Array.isArray(row.aliases) ? row.aliases.join(" ") : "";
      return [
        row.component_id || "",
        row.name || "",
        row.kind || "",
        row.category || "",
        row.qualification || "",
        row.owner || "",
        row.what_it_is || "",
        row.why_tracked || "",
        aliases,
      ].join(" ").toLowerCase();
    }

    function normalizeSearchToken(value) {
      return String(value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "");
    }

    function componentExactMatch(row, needle) {
      const normalizedNeedle = String(needle || "").trim().toLowerCase();
      if (!normalizedNeedle) return false;
      const componentId = String(row.component_id || "").trim().toLowerCase();
      const name = String(row.name || "").trim().toLowerCase();
      if (componentId === normalizedNeedle || name === normalizedNeedle) return true;
      const aliases = Array.isArray(row.aliases) ? row.aliases : [];
      if (aliases.some((alias) => String(alias || "").trim().toLowerCase() === normalizedNeedle)) return true;
      const compactNeedle = normalizeSearchToken(normalizedNeedle);
      if (!compactNeedle) return false;
      const exactTokens = [componentId, name, ...aliases.map((alias) => String(alias || "").trim().toLowerCase())]
        .map((token) => normalizeSearchToken(token))
        .filter(Boolean);
      return exactTokens.includes(compactNeedle);
    }

    function readState() {
      const params = new URLSearchParams(window.location.search || "");
      const component = String(params.get("component") || "").trim().toLowerCase();
      return { component };
    }

    function writeState(component) {
      const params = new URLSearchParams(window.location.search || "");
      params.delete("component");
      if (component) params.set("component", component);
      const query = params.toString();
      const suffix = query ? `?${query}` : "";
      const next = `${window.location.pathname}${suffix}`;
      if (next !== `${window.location.pathname}${window.location.search}`) {
        window.history.replaceState(null, "", next);
      }
      if (window.parent && window.parent !== window) {
        const state = { component };
        window.parent.postMessage({ type: "odylith-registry-navigate", state }, "*");
        window.parent.postMessage({ type: "odylith-registry-navigate", state }, "*");
      }
    }

    function countMapFromPayload(key) {
      const map = payload && payload.counts && payload.counts[key];
      if (!map || typeof map !== "object") return {};
      return map;
    }

    function sortedCategoryTokens() {
      const counts = countMapFromPayload("by_category");
      return Object.keys(counts).sort((a, b) => {
        const av = Number(counts[a] || 0);
        const bv = Number(counts[b] || 0);
        if (av !== bv) return bv - av;
        return a.localeCompare(b);
      });
    }

    function sortedQualificationTokens() {
      const counts = countMapFromPayload("by_qualification");
      return Object.keys(counts).sort((a, b) => {
        const av = Number(counts[a] || 0);
        const bv = Number(counts[b] || 0);
        if (av !== bv) return bv - av;
        return a.localeCompare(b);
      });
    }

    function generatedDateToken() {
      return String(payload.generated_local_date || "").trim() || "-";
    }

    function renderKpis(visibleCount) {
      const counts = payload.counts || {};
      const rows = [
        { label: "Registry Updated", value: generatedDateToken(), tooltip: "Generated date for this Registry view." },
        { label: "Visible Components", value: Number(visibleCount || 0), tooltip: "Components visible under current search and filters." },
        { label: "All Components", value: Number(counts.components || 0), tooltip: "Total first-class component inventory size." },
        { label: "Events", value: Number(counts.events || 0), tooltip: "Codex stream events visible to Registry." },
        { label: "Meaningful", value: Number(counts.meaningful_events || 0), tooltip: "Governance-relevant events." },
        { label: "Mapped Meaningful", value: Number(counts.mapped_meaningful_events || 0), tooltip: "Meaningful events with mapped components." },
      ];
      if (Number(counts.unmapped_meaningful_events || 0) > 0) {
        rows.push({
          label: "Unmapped Meaningful",
          value: Number(counts.unmapped_meaningful_events || 0),
          tooltip: "Meaningful events without mapped components.",
          warn: true,
        });
      }
      if (Number(counts.candidate_queue || 0) > 0) {
        rows.push({
          label: "Candidate Queue",
          value: Number(counts.candidate_queue || 0),
          tooltip: "Unresolved component tokens pending curated review.",
        });
      }
      kpisEl.innerHTML = rows
        .map((row) => (
          `<article class="kpi-card${row.warn ? " warn" : ""}" data-tooltip="${escapeHtml(row.tooltip || "")}">`
          + `<p class="kpi-label">${escapeHtml(row.label)}</p>`
          + `<p class="kpi-value">${escapeHtml(String(row.value))}</p>`
          + "</article>"
        ))
        .join("");
    }

    function renderDiagnostics() {
      const rows = Array.isArray(payload.diagnostics) ? payload.diagnostics.slice() : [];
      const candidates = Array.isArray(payload.candidate_queue) ? payload.candidate_queue : [];
      if (!rows.length && !candidates.length) {
        diagnosticsEl.hidden = true;
        return;
      }
      diagnosticsEl.hidden = false;
      diagnosticsEl.querySelector("summary").textContent = `Diagnostics (${rows.length + candidates.length})`;
      const items = [];
      rows.slice(0, 16).forEach((row) => {
        items.push(`<li class="diag-item">${escapeHtml(String(row || ""))}</li>`);
      });
      candidates.slice(0, 16).forEach((row) => {
        const token = String(row.token || "");
        const source = String(row.source || "");
        const context = String(row.context || "");
        items.push(
          `<li class="diag-item">candidate \`${escapeHtml(token)}\` from ${escapeHtml(source)}${context ? ` (${escapeHtml(context)})` : ""}</li>`
        );
      });
      diagListEl.innerHTML = items.join("");
    }

    function renderFilterControls() {
      const categoryCounts = countMapFromPayload("by_category");
      const qualificationCounts = countMapFromPayload("by_qualification");
      const categoryTokens = sortedCategoryTokens();
      const qualificationTokens = sortedQualificationTokens();

      if (!categoryTokens.includes(activeCategory)) activeCategory = "all";
      if (!qualificationTokens.includes(activeQualification)) activeQualification = "all";

      categoryFilterEl.innerHTML = [
        `<option value="all">All Categories (${allComponents.length})</option>`,
        ...categoryTokens.map((token) => `<option value="${escapeHtml(token)}">${escapeHtml(humanizeToken(token))} (${Number(categoryCounts[token] || 0)})</option>`),
      ].join("");
      categoryFilterEl.value = activeCategory;

      qualificationFilterEl.innerHTML = [
        `<option value="all">All Qualifications (${allComponents.length})</option>`,
        ...qualificationTokens.map((token) => `<option value="${escapeHtml(token)}">${escapeHtml(humanizeToken(token))} (${Number(qualificationCounts[token] || 0)})</option>`),
      ].join("");
      qualificationFilterEl.value = activeQualification;
    }

    function filteredComponents() {
      const needle = String(searchEl.value || "").trim().toLowerCase();
      const normalizedNeedle = normalizeSearchToken(needle);
      const categoryFilterToken = String(activeCategory || "all").trim().toLowerCase();
      const qualificationFilterToken = String(activeQualification || "all").trim().toLowerCase();
      const scoped = allComponents
        .filter((row) => {
          const category = String(row.category || "").trim().toLowerCase();
          const qualification = String(row.qualification || "").trim().toLowerCase();
          if (categoryFilterToken !== "all" && category !== categoryFilterToken) return false;
          if (qualificationFilterToken !== "all" && qualification !== qualificationFilterToken) return false;
          return true;
        })
        .sort((left, right) => {
          const leftCategory = String(left.category || "");
          const rightCategory = String(right.category || "");
          if (leftCategory !== rightCategory) return leftCategory.localeCompare(rightCategory);
          const leftRank = scopeSignalRank(componentIntelligenceSnapshot(left.component_id));
          const rightRank = scopeSignalRank(componentIntelligenceSnapshot(right.component_id));
          if (leftRank !== rightRank) return rightRank - leftRank;
          const leftName = String(left.name || left.component_id || "");
          const rightName = String(right.name || right.component_id || "");
          return leftName.localeCompare(rightName);
        });
      if (!needle) return scoped;
      const exactIdMatches = scoped.filter((row) => componentExactMatch(row, needle) && String(row.component_id || "").trim().toLowerCase() === needle);
      if (exactIdMatches.length) return exactIdMatches;
      const exactNameMatches = scoped.filter((row) => componentExactMatch(row, needle) && String(row.name || "").trim().toLowerCase() === needle);
      if (exactNameMatches.length) return exactNameMatches;
      const exactAliasMatches = scoped.filter((row) => {
        const aliases = Array.isArray(row.aliases) ? row.aliases : [];
        return componentExactMatch(row, needle) && aliases.some((alias) => String(alias || "").trim().toLowerCase() === needle);
      });
      if (exactAliasMatches.length) return exactAliasMatches;
      const normalizedExactMatches = normalizedNeedle
        ? scoped.filter((row) => componentExactMatch(row, normalizedNeedle))
        : [];
      if (normalizedExactMatches.length) return normalizedExactMatches;
      return scoped.filter((row) => {
        const searchText = componentSearchText(row);
        if (searchText.includes(needle)) return true;
        if (!normalizedNeedle) return false;
        return normalizeSearchToken(searchText).includes(normalizedNeedle);
      });
    }

    function groupedByCategory(items) {
      const groups = new Map();
      items.forEach((row) => {
        const category = String(row.category || "").trim().toLowerCase() || "uncategorized";
        if (!groups.has(category)) groups.set(category, []);
        groups.get(category).push(row);
      });
      return Array.from(groups.entries()).sort((left, right) => left[0].localeCompare(right[0]));
    }

    function selectDefault(items, requested) {
      if (!items.length) return "";
      const token = String(requested || "").trim().toLowerCase();
      if (token && items.some((row) => String(row.component_id || "").toLowerCase() === token)) {
        return token;
      }
      return String(items[0].component_id || "").trim().toLowerCase();
    }

    function registryListItemHeight(item) {
      return item && item.kind === "header" ? REGISTRY_LIST_HEADER_HEIGHT : REGISTRY_LIST_ROW_HEIGHT;
    }

    function buildRegistryListItems(items) {
      const renderItems = [];
      groupedByCategory(items).forEach(([category, rows]) => {
        renderItems.push({
          kind: "header",
          key: `header:${category}`,
          category,
          count: rows.length,
        });
        rows.forEach((row) => {
          renderItems.push({
            kind: "row",
            key: `row:${row.component_id}`,
            row,
          });
        });
      });
      return renderItems;
    }

    function registryListOffsetForIndex(items, index) {
      let offset = 0;
      for (let cursor = 0; cursor < index; cursor += 1) {
        offset += registryListItemHeight(items[cursor]);
      }
      return offset;
    }

    function ensureRegistrySelectionVisible(items, selectedId) {
      if (items.length <= REGISTRY_LIST_WINDOW_THRESHOLD) return;
      const selectedIndex = items.findIndex((item) => item.kind === "row" && String(item.row.component_id || "").toLowerCase() === selectedId);
      if (selectedIndex < 0) return;
      const viewportHeight = Math.max(1, Number(listEl.clientHeight || 640));
      const scrollTop = Number(listEl.scrollTop || 0);
      const top = registryListOffsetForIndex(items, selectedIndex);
      const bottom = top + REGISTRY_LIST_ROW_HEIGHT;
      if (top >= scrollTop && bottom <= (scrollTop + viewportHeight)) return;
      listEl.scrollTop = Math.max(0, top - Math.max(24, Math.round(viewportHeight * 0.3)));
    }

    function elementFullyVisibleWithinContainer(container, element) {
      if (!container || !element) return false;
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      return elementRect.top >= containerRect.top && elementRect.bottom <= containerRect.bottom;
    }

    function resolveRegistryListWindow(items) {
      if (items.length <= REGISTRY_LIST_WINDOW_THRESHOLD) {
        return { beforePx: 0, afterPx: 0, items, key: `all:${items.length}` };
      }
      const viewportHeight = Math.max(1, Number(listEl.clientHeight || 640));
      const scrollTop = Number(listEl.scrollTop || 0);
      const startPx = Math.max(0, scrollTop - (REGISTRY_LIST_OVERSCAN * REGISTRY_LIST_ROW_HEIGHT));
      const endPx = scrollTop + viewportHeight + (REGISTRY_LIST_OVERSCAN * REGISTRY_LIST_ROW_HEIGHT);
      let cursorPx = 0;
      let startIndex = 0;
      while (startIndex < items.length) {
        const nextPx = cursorPx + registryListItemHeight(items[startIndex]);
        if (nextPx >= startPx) break;
        cursorPx = nextPx;
        startIndex += 1;
      }
      const beforePx = cursorPx;
      let endIndex = startIndex;
      while (endIndex < items.length && cursorPx < endPx) {
        cursorPx += registryListItemHeight(items[endIndex]);
        endIndex += 1;
      }
      let afterPx = 0;
      for (let cursor = endIndex; cursor < items.length; cursor += 1) {
        afterPx += registryListItemHeight(items[cursor]);
      }
      return {
        beforePx,
        afterPx,
        items: items.slice(startIndex, endIndex),
        key: `${startIndex}:${endIndex}`,
      };
    }

    function renderList(items, selectedId, options = {}) {
      latestRenderedComponents = Array.isArray(items) ? items.slice() : [];
      if (!items.length) {
        listEl.innerHTML = "";
        latestListWindowKey = "empty";
        return;
      }
      const renderItems = buildRegistryListItems(items);
      if (!options.fromScroll && !options.preserveListScroll) {
        ensureRegistrySelectionVisible(renderItems, selectedId);
      }
      const windowed = resolveRegistryListWindow(renderItems);
      if (options.fromScroll && windowed.key === latestListWindowKey) {
        return;
      }
      latestListWindowKey = windowed.key;
      const blocks = [];
      if (windowed.beforePx > 0) {
        blocks.push(`<li class="list-spacer" aria-hidden="true" style="height:${windowed.beforePx}px"></li>`);
      }
      windowed.items.forEach((item) => {
        if (item.kind === "header") {
          blocks.push(`<li class="group-head">${escapeHtml(humanizeToken(item.category))} · ${item.count}</li>`);
          return;
        }
        const row = item.row;
          const categoryToken = String(row.category || "").trim().toLowerCase();
          const toneClass = toneClassForCategory(categoryToken);
          const coverage = row && typeof row.forensic_coverage === "object" ? row.forensic_coverage : {};
        blocks.push(`
          <li>
            <button type="button" class="component-btn${row.component_id === selectedId ? " active" : ""}" data-component="${escapeHtml(row.component_id)}">
              <span class="component-card-title">${escapeHtml(row.name || row.component_id)}</span>
              <span class="component-meta">${escapeHtml(row.component_id)} · ${escapeHtml(humanizeToken(row.kind))} · ${escapeHtml(humanizeToken(row.status || "active"))} · ${escapeHtml(forensicCoverageLabel(coverage))} · ${escapeHtml(Number(row.timeline_count || 0))} events</span>
              <span class="inline">
                <span class="label ${escapeHtml(toneClass)}">${escapeHtml(humanizeToken(categoryToken))}</span>
                <span class="label">${escapeHtml(humanizeToken(row.qualification || "curated"))}</span>
              </span>
            </button>
          </li>
        `);
      });
      if (windowed.afterPx > 0) {
        blocks.push(`<li class="list-spacer" aria-hidden="true" style="height:${windowed.afterPx}px"></li>`);
      }
      listEl.innerHTML = blocks.join("");

      listEl.querySelectorAll("button[data-component]").forEach((node) => {
        node.addEventListener("click", () => {
          const id = String(node.getAttribute("data-component") || "").trim().toLowerCase();
          if (!id) return;
          const preserveListScroll = elementFullyVisibleWithinContainer(listEl, node);
          applyState(id, { push: true, preserveListScroll });
        });
        const id = String(node.getAttribute("data-component") || "").trim().toLowerCase();
        if (id) {
          node.addEventListener("mouseenter", () => {
            registryDataSource.prefetch(id);
          });
          node.addEventListener("focus", () => {
            registryDataSource.prefetch(id);
          });
        }
      });
    }

    function hrefRadar(workstream) {
      const token = String(workstream || "").trim();
      return token ? `../index.html?tab=radar&workstream=${encodeURIComponent(token)}` : "../index.html?tab=radar";
    }

    function hrefAtlas(workstream, diagram) {
      const params = new URLSearchParams();
      params.set("tab", "atlas");
      if (workstream) params.set("workstream", workstream);
      if (diagram) params.set("diagram", diagram);
      return `../index.html?${params.toString()}`;
    }

    function hrefCompass(workstream) {
      const token = String(workstream || "").trim();
      return token
        ? `../index.html?tab=compass&scope=${encodeURIComponent(token)}&date=live`
        : "../index.html?tab=compass&date=live";
    }

    const WORKSTREAM_RE = /^B-\d{3,}$/;
    const DIAGRAM_RE = /^D-\d{3,}$/;

    function linkChip({ label, href, tone, tooltip }) {
      const resolvedHref = String(href || "").trim();
      if (!resolvedHref) return `<span class="label">${escapeHtml(label)}</span>`;
      return `<a class="detail-action-chip ${escapeHtml(tone || "")}" target="_top" href="${escapeHtml(resolvedHref)}" data-tooltip="${escapeHtml(tooltip || "")}">${escapeHtml(label)}</a>`;
    }

    function staticLabel(label, tooltip) {
      return `<span class="label" data-tooltip="${escapeHtml(tooltip || "")}">${escapeHtml(label)}</span>`;
    }

    function artifactChip(item, tooltip, className = "artifact") {
      const path = String(item && item.path || "").trim();
      const href = String(item && item.href || path).trim();
      if (!path || !href) return "";
      return `<a class="${escapeHtml(className)}" href="${escapeHtml(href)}" target="_top" data-tooltip="${escapeHtml(tooltip || "Artifact evidence path.")}">${escapeHtml(path)}</a>`;
    }

    function renderSpecLinkGroup(title, items, emptyLabel, tooltip) {
      const rows = Array.isArray(items) ? items.filter(Boolean) : [];
      return `
        <div class="spec-links-block">
          <p class="summary-row"><strong>${escapeHtml(title)}:</strong></p>
          <div class="artifact-list">
            ${rows.length
              ? rows.map((item) => artifactChip(item, tooltip)).join("")
              : `<span class="label">${escapeHtml(emptyLabel)}</span>`}
          </div>
        </div>
      `;
    }

    function normalizeRepoRelativePath(value) {
      const parts = [];
      String(value || "").split("/").forEach((segment) => {
        const token = String(segment || "").trim();
        if (!token || token === ".") return;
        if (token === "..") {
          if (parts.length) parts.pop();
          return;
        }
        parts.push(token);
      });
      return parts.join("/");
    }

    function specInlineTooltipAttrs(tooltip, ariaLabel = "") {
      const text = String(tooltip || "").trim();
      if (!text) return "";
      const label = String(ariaLabel || text).trim() || text;
      return ` data-tooltip="${escapeHtml(text)}" aria-label="${escapeHtml(label)}"`;
    }

    function specInlineLinkWorkstream(href, label) {
      const labelToken = String(label || "").trim();
      if (WORKSTREAM_RE.test(labelToken)) return labelToken;
      const rawHref = String(href || "").trim();
      const queryIndex = rawHref.indexOf("?");
      if (queryIndex === -1) return "";
      const params = new URLSearchParams(rawHref.slice(queryIndex + 1));
      const token = String(params.get("workstream") || "").trim();
      return WORKSTREAM_RE.test(token) ? token : "";
    }

    function specInlineLinkDiagram(href, label) {
      const labelToken = String(label || "").trim();
      if (DIAGRAM_RE.test(labelToken)) return labelToken;
      const rawHref = String(href || "").trim();
      const queryIndex = rawHref.indexOf("?");
      if (queryIndex === -1) return "";
      const params = new URLSearchParams(rawHref.slice(queryIndex + 1));
      const token = String(params.get("diagram") || "").trim();
      return DIAGRAM_RE.test(token) ? token : "";
    }

    function specInlineLinkTooltip(label, href) {
      const rawLabel = String(label || "").trim();
      const rawHref = String(href || "").trim();
      const workstream = specInlineLinkWorkstream(rawHref, rawLabel);
      if (workstream) {
        return `Workstream ${workstream}. Open linked plan.`;
      }
      const diagram = specInlineLinkDiagram(rawHref, rawLabel);
      if (diagram) {
        return `Diagram ${diagram}. Open linked diagram.`;
      }
      if (/^#/i.test(rawHref)) {
        return rawLabel ? `Jump to linked section ${rawLabel}.` : "Jump to linked section.";
      }
      if (/^(?:https?:|mailto:)/i.test(rawHref)) {
        return rawLabel ? `Open external link ${rawLabel}.` : "Open external link.";
      }
      const normalizedLabel = normalizeRepoRelativePath(rawLabel);
      if (normalizedLabel.includes("/")) {
        return `Open linked repository path ${clipText(normalizedLabel, 72)}.`;
      }
      return rawLabel
        ? `Open linked artifact ${clipText(rawLabel, 72)}.`
        : "Open linked artifact.";
    }

    function specInlineCodeTooltip(value) {
      const token = String(value || "").trim();
      if (!token) return "";
      if (WORKSTREAM_RE.test(token)) return `Workstream ${token} referenced in this spec.`;
      if (DIAGRAM_RE.test(token)) return `Diagram ${token} referenced in this spec.`;
      if (/^(?:dev|test|staging|prod)$/i.test(token)) return `Environment literal in this spec.`;
      if (/^(?:python|pytest|make|app)\b/i.test(token)) return "Command literal in this spec.";
      if (
        /^(?:odylith|docs|scripts|contracts|infra|services|app|tests|agents-guidelines|skills|mk)\//.test(token)
        || (token.includes("/") && /\.[a-z0-9]+$/i.test(token))
      ) {
        return `Repository path in this spec: ${clipText(token, 72)}.`;
      }
      if (/^[a-z][a-z0-9-]*$/i.test(token) && token.includes("-")) {
        return `Spec identifier: ${clipText(token, 72)}.`;
      }
      return `Spec literal: ${clipText(token, 72)}.`;
    }

    function specInlineAriaLabel(value, tooltip) {
      const token = String(value || "").trim();
      const help = String(tooltip || "").trim();
      if (!token) return help;
      if (!help) return token;
      return help.toLowerCase().includes(token.toLowerCase()) ? help : `${token}. ${help}`;
    }

    function resolveSpecHref(baseSpecPath, href) {
      const rawHref = String(href || "").trim();
      if (!rawHref) return "";
      if (/^(?:https?:|mailto:|#)/i.test(rawHref)) return rawHref;
      if (/^(?:odylith|docs|src|contracts|tests|agents-guidelines|skills|scripts|mk|infra|services|app|\.odylith)\//.test(rawHref)) {
        return `../../${rawHref.replace(/^\.?\//, "")}`;
      }
      const specPath = normalizeRepoRelativePath(baseSpecPath);
      const specDir = specPath ? specPath.split("/").slice(0, -1) : [];
      const resolvedParts = specDir.slice();
      rawHref.split("/").forEach((segment) => {
        const token = String(segment || "").trim();
        if (!token || token === ".") return;
        if (token === "..") {
          if (resolvedParts.length) resolvedParts.pop();
          return;
        }
        resolvedParts.push(token);
      });
      const repoRelative = resolvedParts.join("/");
      if (!repoRelative) return rawHref;
      return `../../${repoRelative}`;
    }

    function renderInlineMarkdown(value, baseSpecPath = "") {
      const raw = String(value || "");
      const inlineTokens = [];
      let tokenized = raw.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, href) => {
        const resolvedHref = resolveSpecHref(baseSpecPath, href);
        const tooltip = specInlineLinkTooltip(label, resolvedHref || href);
        const ariaLabel = specInlineAriaLabel(label, tooltip);
        const attrs = specInlineTooltipAttrs(tooltip, ariaLabel);
        const html = resolvedHref
          ? `<a href="${escapeHtml(resolvedHref)}" target="_top"${attrs}>${escapeHtml(String(label || "").trim())}</a>`
          : escapeHtml(String(label || "").trim());
        const index = inlineTokens.push(html) - 1;
        return `@@REGISTRY_INLINE_${index}@@`;
      });
      tokenized = tokenized.replace(/`([^`]+)`/g, (_, code) => {
        const tooltip = specInlineCodeTooltip(code);
        const attrs = specInlineTooltipAttrs(tooltip, specInlineAriaLabel(code, tooltip));
        const html = `<code${attrs}>${escapeHtml(String(code || "").trim())}</code>`;
        const index = inlineTokens.push(html) - 1;
        return `@@REGISTRY_INLINE_${index}@@`;
      });

      let html = escapeHtml(tokenized);
      html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/@@REGISTRY_INLINE_(\d+)@@/g, (_, index) => inlineTokens[Number(index)] || "");
      return html;
    }

    function renderSpecMarkdown(markdown, baseSpecPath = "") {
      const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
      const chunks = [];
      let paragraph = [];
      let listDepth = 0;
      const listItemOpen = {};
      const parseMarkdownTableCells = (value) => {
        const raw = String(value || "").trim();
        if (!raw.includes("|")) return [];
        let body = raw;
        if (body.startsWith("|")) body = body.slice(1);
        if (body.endsWith("|")) body = body.slice(0, -1);
        return body.split("|").map((cell) => String(cell || "").trim());
      };
      const isMarkdownTableSeparator = (value) => {
        const cells = parseMarkdownTableCells(value);
        return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")));
      };
      const normalizeMarkdownTableCells = (cells, width) => {
        const normalized = Array.isArray(cells) ? cells.slice(0, width) : [];
        while (normalized.length < width) normalized.push("");
        return normalized;
      };

      const flushParagraph = () => {
        if (!paragraph.length) return;
        chunks.push(`<p>${renderInlineMarkdown(paragraph.join(" "), baseSpecPath)}</p>`);
        paragraph = [];
      };
      const closeOneListLevel = () => {
        if (listDepth <= 0) return;
        if (listItemOpen[listDepth]) {
          chunks.push("</li>");
          listItemOpen[listDepth] = false;
        }
        chunks.push("</ul>");
        delete listItemOpen[listDepth];
        listDepth -= 1;
      };
      const closeAllLists = () => {
        while (listDepth > 0) closeOneListLevel();
      };
      const ensureListDepth = (targetDepth) => {
        while (listDepth < targetDepth) {
          if (listDepth > 0 && !listItemOpen[listDepth]) {
            chunks.push("<li>");
            listItemOpen[listDepth] = true;
          }
          chunks.push("<ul>");
          listDepth += 1;
          listItemOpen[listDepth] = false;
        }
        while (listDepth > targetDepth) closeOneListLevel();
      };

      for (let index = 0; index < lines.length; index += 1) {
        const raw = String(lines[index] || "");
        const token = raw.trim();
        if (/^<!--.*-->$/.test(token)) {
          flushParagraph();
          continue;
        }
        if (!token) {
          flushParagraph();
          closeAllLists();
          continue;
        }
        if (token.startsWith("### ")) {
          flushParagraph();
          closeAllLists();
          chunks.push(`<h5>${escapeHtml(token.slice(4).trim())}</h5>`);
          continue;
        }
        if (token.startsWith("## ")) {
          flushParagraph();
          closeAllLists();
          chunks.push(`<h4>${escapeHtml(token.slice(3).trim())}</h4>`);
          continue;
        }
        if (token.startsWith("# ")) {
          flushParagraph();
          closeAllLists();
          chunks.push(`<h3>${escapeHtml(token.slice(2).trim())}</h3>`);
          continue;
        }
        const headerCells = parseMarkdownTableCells(token);
        if (headerCells.length && index + 1 < lines.length && isMarkdownTableSeparator(lines[index + 1])) {
          flushParagraph();
          closeAllLists();
          const normalizedHeader = normalizeMarkdownTableCells(headerCells, headerCells.length);
          const bodyRows = [];
          index += 2;
          for (; index < lines.length; index += 1) {
            const rowRaw = String(lines[index] || "");
            const rowToken = rowRaw.trim();
            if (!rowToken) break;
            const rowCells = parseMarkdownTableCells(rowToken);
            if (!rowCells.length) {
              index -= 1;
              break;
            }
            bodyRows.push(normalizeMarkdownTableCells(rowCells, normalizedHeader.length));
          }
          const headerHtml = normalizedHeader
            .map((cell) => `<th>${renderInlineMarkdown(cell, baseSpecPath)}</th>`)
            .join("");
          const bodyHtml = bodyRows
            .map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell, baseSpecPath)}</td>`).join("")}</tr>`)
            .join("");
          chunks.push(
            `<div class="spec-table-scroll"><table class="spec-table"><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`
          );
          continue;
        }
        const bulletMatch = raw.match(/^(\s*)[-*+]\s+(.*)$/);
        if (bulletMatch) {
          flushParagraph();
          const indentSpaces = String(bulletMatch[1] || "").replace(/\t/g, "  ").length;
          const targetDepth = Math.max(1, Math.floor(indentSpaces / 2) + 1);
          ensureListDepth(targetDepth);
          if (listItemOpen[listDepth]) {
            chunks.push("</li>");
            listItemOpen[listDepth] = false;
          }
          chunks.push(`<li>${renderInlineMarkdown(String(bulletMatch[2] || "").trim(), baseSpecPath)}`);
          listItemOpen[listDepth] = true;
          continue;
        }
        closeAllLists();
        paragraph.push(token);
      }

      flushParagraph();
      closeAllLists();
      if (!chunks.length) return '<p class="empty">No spec content.</p>';
      return chunks.join("");
    }

    function extractTriggerPhrases(markdown, triggerTiers) {
      const phrases = [];
      const seen = new Set();

      const appendPhrase = (value) => {
        const token = String(value || "").trim();
        if (!token || seen.has(token)) return;
        seen.add(token);
        phrases.push(token);
      };

      const appendTierPhrases = (value) => {
        if (!Array.isArray(value)) return;
        value.forEach((item) => {
          const phrasesRaw = Array.isArray(item && item.trigger_phrases) ? item.trigger_phrases : [];
          phrasesRaw.forEach((phrase) => {
            appendPhrase(phrase);
          });
        });
      };

      if (triggerTiers && typeof triggerTiers === "object") {
        appendTierPhrases(triggerTiers.baseline);
        appendTierPhrases(triggerTiers.deep);
      }
      if (phrases.length) return phrases;

      const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
      let inTriggers = false;
      lines.forEach((line) => {
        const trimmed = String(line || "").trim();
        if (!inTriggers) {
          if (/^##\s+skill triggers\b/i.test(trimmed)) inTriggers = true;
          return;
        }
        if (/^##\s+/.test(trimmed)) {
          inTriggers = false;
          return;
        }
        const nestedPhrase = trimmed.match(/^-\s+"([^"]+)"/);
        if (nestedPhrase) {
          appendPhrase(nestedPhrase[1]);
          return;
        }
        const inlineTrigger = trimmed.match(/^-\s*Trigger phrases:\s*(.+)$/i);
        if (!inlineTrigger) return;
        const quoted = String(inlineTrigger[1] || "").match(/"([^"]+)"/g) || [];
        quoted.forEach((token) => {
          appendPhrase(token.replace(/^"|"$/g, ""));
        });
      });
      return phrases;
    }

    function uniqueTimelineArtifacts(events, maxItems, predicate) {
      const rows = [];
      const seen = new Set();
      events.forEach((event) => {
        const artifacts = Array.isArray(event.artifacts) ? event.artifacts : [];
        artifacts.forEach((item) => {
          const path = String(item && item.path || "").trim();
          if (!path || seen.has(path)) return;
          if (typeof predicate === "function" && !predicate(path)) return;
          seen.add(path);
          rows.push(item);
        });
      });
      return rows.slice(0, maxItems);
    }

    function uniqueEventWorkstreams(events) {
      const tokens = [];
      const seen = new Set();
      events.forEach((event) => {
        const ws = Array.isArray(event.workstreams) ? event.workstreams : [];
        ws.forEach((token) => {
          const value = String(token || "").trim();
          if (!value || seen.has(value)) return;
          seen.add(value);
          tokens.push(value);
        });
      });
      return tokens;
    }

    function contextRow(title, count, bodyHtml, tooltip, block = false) {
      return `
        <div class="context-row">
          <div class="context-title" data-tooltip="${escapeHtml(tooltip || "")}">${escapeHtml(title)}</div>
          <div class="context-count">${escapeHtml(String(count))}</div>
          <div class="context-values${block ? " block" : ""}">${bodyHtml || ""}</div>
        </div>
      `;
    }

    function renderDetail(row) {
      if (!row) {
        detailEl.innerHTML = "";
        return;
      }
      const workstreams = Array.isArray(row.workstreams) ? row.workstreams : [];
      const diagrams = Array.isArray(row.diagrams) ? row.diagrams : [];
      const diagramDetails = Array.isArray(row.diagram_details) ? row.diagram_details : [];
      const subcomponents = Array.isArray(row.subcomponents) ? row.subcomponents : [];
      const subcomponentDetails = Array.isArray(row.subcomponent_details) ? row.subcomponent_details : [];
      const aliases = Array.isArray(row.aliases) ? row.aliases : [];
      const sources = Array.isArray(row.sources) ? row.sources : [];
      const pathPrefixes = Array.isArray(row.path_prefixes) ? row.path_prefixes : [];
      const productLayer = String(row.product_layer || "").trim();
      const timelineEvents = Array.isArray(row.timeline) ? row.timeline : [];
      const liveTimelineEvents = timelineEvents.filter((event) => !isBaselineTimelineEvent(event));
      const forensicCoverage = row && typeof row.forensic_coverage === "object" ? row.forensic_coverage : {};
      const categoryToken = String(row.category || "").trim().toLowerCase();
      const latestEvent = liveTimelineEvents[0] || (timelineEvents.length ? timelineEvents[0] : null);
      const latestSummary = latestEvent
        ? String(latestEvent.summary || "(no summary)").trim()
        : "No mapped component-change event is currently available for this component.";
      const allWorkstreams = uniqueEventWorkstreams(timelineEvents);
      const workstreamPreview = allWorkstreams.slice(0, 4);
      const workstreamOverflow = Math.max(0, allWorkstreams.length - workstreamPreview.length);
      const diagramPreview = diagrams.slice(0, 3);
      const diagramOverflow = Math.max(0, diagrams.length - diagramPreview.length);
      const EVENT_WINDOW_DAYS = 14;
      const latestEventTs = latestEvent && typeof latestEvent.ts_iso === "string" ? Date.parse(latestEvent.ts_iso) : NaN;
      const windowAnchorTs = Number.isFinite(latestEventTs) ? latestEventTs : Date.now();
      const windowStartTs = windowAnchorTs - (EVENT_WINDOW_DAYS * 24 * 60 * 60 * 1000);
      const windowEvents = timelineEvents.filter((event) => {
        const ts = Date.parse(String(event && event.ts_iso || ""));
        return Number.isFinite(ts) ? ts >= windowStartTs : true;
      });
      const hasImplementationSignal = liveTimelineEvents.some((event) => String(event && event.kind || "").toLowerCase() === "implementation");
      const hasDecisionSignal = liveTimelineEvents.some((event) => String(event && event.kind || "").toLowerCase() === "decision");
      const latestExplicit = latestExplicitEvent(timelineEvents);
      const explicitExecutiveEvents = windowEvents.filter((event) => isExplicitTimelineEvent(event));
      const syntheticExecutiveEvents = windowEvents.filter((event) => isSyntheticTimelineEvent(event));
      const baselineExecutiveEvents = windowEvents.filter((event) => isBaselineTimelineEvent(event));
      const primaryWorkstream = workstreamPreview[0] || "";
      const componentName = String(row.name || row.component_id || "This component").trim() || "This component";
      const confidence = intelligenceConfidence(
        explicitExecutiveEvents.length,
        syntheticExecutiveEvents.length,
        allWorkstreams.length,
        baselineExecutiveEvents.length,
      );
      const intelligenceContext = {
        latestEvent,
        latestSummary,
        latestExplicit,
        whyTracked: row.why_tracked,
        componentName,
        categoryToken,
        hasImplementationSignal,
        hasDecisionSignal,
        explicitCount: explicitExecutiveEvents.length,
        syntheticCount: syntheticExecutiveEvents.length,
        baselineCount: baselineExecutiveEvents.length,
        allWorkstreams,
        workstreamPreview,
        workstreamOverflow,
        primaryWorkstream,
        diagramPreview,
        diagramOverflow,
        diagrams,
        timelineEvents,
        specPath: String(row.spec_ref || "").trim(),
        specRunbooks: Array.isArray(row.spec_runbooks) ? row.spec_runbooks : [],
        specDeveloperDocs: Array.isArray(row.spec_developer_docs) ? row.spec_developer_docs : [],
      };
      const metadata = [
        staticLabel(`Category: ${humanizeToken(row.category)}`, categoryDescription(row.category)),
        staticLabel(`Qualification: ${humanizeToken(row.qualification)}`, qualificationDescription(row.qualification)),
        staticLabel(`Kind: ${humanizeToken(row.kind)}`, "Component structure class."),
        staticLabel(`Owner: ${row.owner || "unknown"}`, "Declared ownership for governance routing."),
        staticLabel(`Status: ${humanizeToken(row.status || "unknown")}`, "Lifecycle state of this component record."),
      ].join("");

      const wsLinks = workstreams.length
        ? workstreams.map((ws) => linkChip({
            label: ws,
            href: hrefRadar(ws),
            tone: "tone-gov",
            tooltip: `Workstream ${ws}. Open Radar context.`,
          })).join("")
        : "";

      const diagramLinks = diagramDetails.length
        ? diagramDetails.map((item) => {
            const diagramId = String(item && item.diagram_id || "").trim();
            const diagramTitle = String(item && item.title || "").trim() || diagramId;
            if (!diagramId) return "";
            return linkChip({
              label: diagramId,
              href: hrefAtlas(workstreams[0] || "", diagramId),
              tooltip: `${diagramTitle}. Open Atlas context.`,
            });
          }).join("")
        : diagrams.length
        ? diagrams.map((dg) => linkChip({
            label: dg,
            href: hrefAtlas(workstreams[0] || "", dg),
            tooltip: `Diagram ${dg}. Open Atlas context.`,
          })).join("")
        : "";

      const aliasLabels = aliases.length
        ? aliases.map((token) => staticLabel(token, "Alias token used during component mapping.")).join("")
        : "";

      const sourceLabels = sources.length
        ? sources.map((token) => staticLabel(token, "Source that contributed this component linkage.")).join("")
        : "";

      const pathLabels = pathPrefixes.length
        ? pathPrefixes.map((token) => staticLabel(token, "Artifact prefix used for path-based mapping.")).join("")
        : "";
      const productLayerBody = productLayer
        ? `<p class="desc"><strong>${escapeHtml(productLayerLabel(productLayer))}.</strong> ${escapeHtml(productLayerDescription(productLayer))}</p>`
        : "";
      const subcomponentLinks = subcomponentDetails.length
        ? subcomponentDetails.map((item) => {
            const componentId = String(item && item.component_id || "").trim();
            const componentName = String(item && item.name || "").trim() || componentId;
            if (!componentId) return "";
            return linkChip({
              label: componentName,
              href: registryComponentHref(componentId),
              tooltip: `${componentId}. Open Registry component detail.`,
            });
          }).join("")
        : subcomponents.length
        ? subcomponents.map((componentId) => linkChip({
            label: componentId,
            href: registryComponentHref(componentId),
            tooltip: `${componentId}. Open Registry component detail.`,
          })).join("")
        : "";
      const emptyReasons = Array.isArray(forensicCoverage.empty_reasons)
        ? forensicCoverage.empty_reasons.map(forensicCoverageReasonLabel).filter(Boolean)
        : [];
      const forensicCoverageBody = String(forensicCoverage.status || "").trim().toLowerCase() === "tracked_but_evidence_empty"
        ? `<p class="desc">${escapeHtml(forensicCoverageLabel(forensicCoverage))}. ${escapeHtml(emptyReasons.length ? ensureSentence(naturalList(emptyReasons)) : "No mapped forensic evidence channels are currently attached.")}</p>`
        : `<p class="desc">${escapeHtml(forensicCoverageSummary(forensicCoverage))}</p>`;

      const rows = [
        contextRow("Forensic Coverage", Number(row.timeline_count || 0), forensicCoverageBody, "Registry coverage truth derived from explicit Compass events, recent path matches, and mapped workstream evidence.", true),
        contextRow("Metadata", 5, metadata, "Category, qualification, and ownership qualifiers."),
        contextRow("Product Layer", productLayer ? 1 : 0, productLayerBody, "Odylith product-layer placement for this component."),
        contextRow("Workstreams", workstreams.length, wsLinks, "Linked workstreams affecting this component."),
        contextRow("Diagrams", diagrams.length, diagramLinks, "Atlas diagrams that mention this component."),
        contextRow("Subcomponents", subcomponents.length, subcomponentLinks, "Explicit composed children for umbrella/platform components."),
        contextRow("Aliases", aliases.length, aliasLabels, "Alternate tokens used for resolution."),
        contextRow("Sources", sources.length, sourceLabels, "Inventory evidence sources."),
        contextRow("Path Prefixes", pathPrefixes.length, pathLabels, "Artifact prefixes used in event mapping."),
      ].join("");

      const displayName = String(row.name || row.component_id || "").trim();
      const fallbackToken = String(row.component_id || "").trim();
      const specPath = String(row.spec_ref || "").trim();
      const specLastUpdated = String(row.spec_last_updated || "").trim() || "Unknown";
      const specHistory = Array.isArray(row.spec_feature_history) ? row.spec_feature_history : [];
      const specMarkdown = String(row.spec_markdown || "").trim();
      const specRunbooks = Array.isArray(row.spec_runbooks) ? row.spec_runbooks : [];
      const specDeveloperDocs = Array.isArray(row.spec_developer_docs) ? row.spec_developer_docs : [];
      const triggerPhrases = extractTriggerPhrases(specMarkdown, row && row.skill_trigger_tiers);
      const specRendered = renderSpecMarkdown(specMarkdown, specPath);
      const triggerBlock = triggerPhrases.length
        ? `
          <details class="trigger-expand">
            <summary>
              <p class="summary-row trigger-summary-title"><strong>Triggers:</strong> ${escapeHtml(String(triggerPhrases.length))} phrase${triggerPhrases.length === 1 ? "" : "s"}</p>
            </summary>
            <div class="trigger-block">
              <ul class="trigger-list">
                ${triggerPhrases.map((phrase) => `<li>${escapeHtml(phrase)}</li>`).join("")}
              </ul>
            </div>
          </details>
        `
        : '<p class="summary-row"><strong>Triggers:</strong> No trigger phrases documented.</p>';

      detailEl.innerHTML = `
        <h2 class="component-name">${escapeHtml(displayName || fallbackToken)}</h2>
        <div class="summary-strip">
          <p class="summary-row"><strong>What it is:</strong> ${escapeHtml(row.what_it_is || "Not documented.")}</p>
          <p class="summary-row"><strong>Why tracked:</strong> ${escapeHtml(row.why_tracked || "Not documented.")}</p>
          ${productLayer ? `<p class="summary-row"><strong>Product layer:</strong> ${escapeHtml(productLayerLabel(productLayer))}</p>` : ""}
          <p class="summary-row"><strong>Forensic coverage:</strong> ${escapeHtml(forensicCoverageSummary(forensicCoverage))}</p>
          ${triggerBlock}
        </div>
        <details class="spec-expand">
          <summary>
            <div class="spec-summary-main">
              <p class="detail-disclosure-title spec-summary-title">Current Spec</p>
            </div>
            <span class="spec-summary-meta">
              <span class="label">Last updated ${escapeHtml(specLastUpdated)}</span>
              <span class="label">Feature entries ${escapeHtml(String(specHistory.length))}</span>
            </span>
          </summary>
          <div class="spec-expand-body">
            <p class="summary-row"><strong>Spec source:</strong> ${escapeHtml(specPath || "Not documented.")}</p>
            ${renderSpecLinkGroup(
              "Runbooks",
              specRunbooks,
              "No linked runbooks.",
              "Runbook linked to this component through workstream traceability."
            )}
            ${renderSpecLinkGroup(
              "Developer Docs",
              specDeveloperDocs,
              "No linked developer docs.",
              "Developer doc linked to this component through workstream traceability."
            )}
            <div class="spec-doc">${specRendered}</div>
          </div>
        </details>
        <details class="context-section">
          <summary>
            <div class="context-head">
              <span class="detail-disclosure-title context-toggle-label">Topology</span>
            </div>
            <div class="context-head-actions">
              <span class="label" data-tooltip="Linked workstreams count.">Workstreams ${workstreams.length}</span>
              <span class="label" data-tooltip="Linked diagrams count.">Diagrams ${diagrams.length}</span>
              <span class="label" data-tooltip="Mapped timeline events for this component.">Events ${Number(row.timeline_count || 0)}</span>
            </div>
          </summary>
          <div class="context-body">
            ${rows}
          </div>
        </details>
      `;
    }

    function renderTimeline(row) {
      const events = row && Array.isArray(row.timeline) ? row.timeline : [];
      const forensicCoverage = row && typeof row.forensic_coverage === "object" ? row.forensic_coverage : {};
      timelineCountEl.textContent = `${events.length} events`;
      if (!events.length) {
        timelineEl.innerHTML = "";
        return;
      }
      timelineEl.innerHTML = events.map((event) => {
        const workstreams = Array.isArray(event.workstreams) ? event.workstreams : [];
        const artifacts = Array.isArray(event.artifacts) ? event.artifacts : [];
        const wsPills = workstreams.length
          ? workstreams.map((ws) => linkChip({
              label: ws,
              href: hrefRadar(ws),
              tone: "tone-gov",
              tooltip: `Workstream ${ws}. Open Radar context.`,
            })).join("")
          : '<span class="label">No scope</span>';

        const artifactLinks = artifacts.length
          ? artifacts.map((item) => `<a class="artifact" href="${escapeHtml(item.href || item.path || "")}" target="_top" data-tooltip="Artifact evidence path for this event.">${escapeHtml(item.path || "artifact")}</a>`).join("")
          : '<span class="artifact">No artifacts</span>';

        return `
          <li class="event">
            <div class="event-top">
              <span class="label" data-tooltip="Codex stream event kind.">${escapeHtml(eventKindLabel(event.kind))}</span>
              <span class="label" data-tooltip="Component-link confidence for this event.">confidence: ${escapeHtml(event.confidence || "none")}</span>
              <span>${escapeHtml(event.ts_iso || "")}</span>
            </div>
            <p class="event-summary">${escapeHtml(event.summary || "(no summary)")}</p>
            <div class="inline">${wsPills}</div>
            <div class="artifact-list">${artifactLinks}</div>
          </li>
        `;
      }).join("");
    }

    async function renderSelectedComponent(selectedId, filtered) {
      const selectedSummary = filtered.find((row) => String(row.component_id || "").toLowerCase() === String(selectedId || "").toLowerCase()) || null;
      if (!selectedSummary) {
        detailEl.dataset.selectedComponent = "";
        renderDetail(null);
        renderTimeline(null);
        return;
      }
      const expectedSelected = String(selectedId || "").trim().toLowerCase();
      detailEl.dataset.selectedComponent = expectedSelected;
      detailEl.innerHTML = "";
      timelineCountEl.textContent = "";
      timelineEl.innerHTML = "";
      const loadedDetail = await registryDataSource.loadDetail(selectedId);
      if (String(detailEl.dataset.selectedComponent || "") !== expectedSelected) {
        return;
      }
      const selected = loadedDetail && typeof loadedDetail === "object"
        ? { ...selectedSummary, ...loadedDetail }
        : selectedSummary;
      renderDetail(selected);
      renderTimeline(selected);
    }

    function applyState(requestedId, options = {}) {
      renderFilterControls();
      const filtered = filteredComponents();
      renderKpis(filtered.length);
      const selectedId = selectDefault(filtered, requestedId);
      renderList(filtered, selectedId, { preserveListScroll: Boolean(options.preserveListScroll) });
      void renderSelectedComponent(selectedId, filtered);
      if (options.push) writeState(selectedId);
    }

    searchEl.addEventListener("input", () => {
      applyState(readState().component, { push: false });
    });
    listEl.addEventListener("scroll", () => {
      if (latestRenderedComponents.length <= REGISTRY_LIST_WINDOW_THRESHOLD) return;
      if (listScrollFrame) return;
      listScrollFrame = window.requestAnimationFrame(() => {
        listScrollFrame = 0;
        renderList(latestRenderedComponents, readState().component, { fromScroll: true });
      });
    });

    categoryFilterEl.addEventListener("change", () => {
      activeCategory = String(categoryFilterEl.value || "all").trim().toLowerCase() || "all";
      applyState(readState().component, { push: false });
    });

    qualificationFilterEl.addEventListener("change", () => {
      activeQualification = String(qualificationFilterEl.value || "all").trim().toLowerCase() || "all";
      applyState(readState().component, { push: false });
    });

    resetFiltersEl.addEventListener("click", () => {
      searchEl.value = "";
      activeCategory = "all";
      activeQualification = "all";
      applyState(readState().component, { push: false });
    });

    window.addEventListener("popstate", () => {
      applyState(readState().component, { push: false });
    });

    renderDiagnostics();
    applyState(readState().component, { push: false });
