const __ODYLITH_SHELL_REDIRECT_IN_PROGRESS__ = (function enforceShellOwnedSurfaceAccess() {
  try {
    const expectedFrameId = "frame-radar";
    const frameElement = window.frameElement;
    const actualFrameId = frameElement && typeof frameElement.id === "string" ? frameElement.id : "";
    if (window.parent && window.parent !== window && actualFrameId === expectedFrameId) {
      return false;
    }
    const shellUrl = new URL("../index.html", window.location.href);
    const currentParams = new URLSearchParams(window.location.search || "");
    const nextParams = new URLSearchParams();
    nextParams.set("tab", "radar");
    const passthroughRules = [{"target":"view","sources":["view"]},{"target":"workstream","sources":["workstream"]}];
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

(async () => {
    const DATA = window["__ODYLITH_BACKLOG_DATA__"] || {};
    const assetLoadCache = new Map();
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
      const payload = DATA.detail_manifest;
      return payload && typeof payload === "object" ? payload : {};
    }
    function standaloneManifest() {
      const payload = window.__ODYLITH_BACKLOG_STANDALONE_MANIFEST__;
      return payload && typeof payload === "object" ? payload : {};
    }
    async function ensureStandaloneManifestLoaded() {
      const existing = standaloneManifest();
      if (Object.keys(existing).length) return existing;
      const href = String(DATA.standalone_manifest_href || "").trim();
      if (!href) return {};
      await loadScriptAsset(href);
      return standaloneManifest();
    }
    async function loadStandaloneDocument(viewToken, workstreamToken) {
      const key = `${String(viewToken || "").trim()}:${String(workstreamToken || "").trim()}`;
      const loadedDocs = window.__ODYLITH_BACKLOG_DOCUMENT_SHARDS__ || {};
      if (typeof loadedDocs[key] === "string" && loadedDocs[key].trim()) {
        return loadedDocs[key];
      }
      const manifest = await ensureStandaloneManifestLoaded();
      const shardHref = String(manifest[key] || "").trim();
      if (!shardHref) return "";
      await loadScriptAsset(shardHref);
      const resolved = window.__ODYLITH_BACKLOG_DOCUMENT_SHARDS__ || {};
      return typeof resolved[key] === "string" ? resolved[key] : "";
    }
    async function loadDetailEntry(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) return null;
      const loaded = window.__ODYLITH_BACKLOG_DETAIL_SHARDS__ || {};
      if (loaded[token] && typeof loaded[token] === "object") {
        return loaded[token];
      }
      const shardHref = String(detailManifest()[token] || "").trim();
      if (!shardHref) return null;
      await loadScriptAsset(shardHref);
      const resolved = window.__ODYLITH_BACKLOG_DETAIL_SHARDS__ || {};
      return resolved[token] && typeof resolved[token] === "object" ? resolved[token] : null;
    }
    async function loadRuntimePayload(path, params = {}) {
      const dataSource = DATA.data_source && typeof DATA.data_source === "object" ? DATA.data_source : {};
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
    function createStaticSnapshotBacklogDataSource() {
      return {
        backend: "staticSnapshot",
        async loadManifest() {
          return {
            detail: detailManifest(),
            documents: await ensureStandaloneManifestLoaded(),
          };
        },
        async loadList(_params = {}) {
          return Array.isArray(DATA.entries) ? DATA.entries.slice() : [];
        },
        async loadDetail(id) {
          return loadDetailEntry(id);
        },
        async loadDocument(request = {}) {
          return loadStandaloneDocument(request.view, request.id);
        },
        prefetch(id) {
          void loadDetailEntry(id);
        },
      };
    }
    function createRuntimeBacklogDataSource() {
      const fallback = createStaticSnapshotBacklogDataSource();
      return {
        backend: "runtime",
        async loadManifest() {
          const payload = await loadRuntimePayload("surfaces/backlog/manifest");
          if (payload && typeof payload === "object") return payload;
          return fallback.loadManifest();
        },
        async loadList(params = {}) {
          const payload = await loadRuntimePayload("surfaces/backlog/list", params);
          if (payload && Array.isArray(payload.entries)) return payload.entries;
          return fallback.loadList(params);
        },
        async loadDetail(id) {
          const payload = await loadRuntimePayload("surfaces/backlog/detail", { workstream: id });
          if (payload && typeof payload === "object") return payload;
          return fallback.loadDetail(id);
        },
        async loadDocument(request = {}) {
          const payload = await loadRuntimePayload("surfaces/backlog/document", {
            workstream: request.id,
            view: request.view,
          });
          if (payload && typeof payload.html === "string") return payload.html;
          return fallback.loadDocument(request);
        },
        prefetch(id) {
          void this.loadDetail(id);
        },
      };
    }
    function createBacklogDataSource() {
      const dataSource = DATA.data_source && typeof DATA.data_source === "object" ? DATA.data_source : {};
      const preferred = String(dataSource.preferred_backend || "").trim();
      if (preferred === "runtime") {
        return createRuntimeBacklogDataSource();
      }
      return createStaticSnapshotBacklogDataSource();
    }
    const backlogDataSource = createBacklogDataSource();
    function copyElementAttributes(target, source) {
      if (!target || !source) return;
      for (const attr of Array.from(target.attributes || [])) {
        target.removeAttribute(attr.name);
      }
      for (const attr of Array.from(source.attributes || [])) {
        target.setAttribute(attr.name, attr.value);
      }
    }
    function appendStandaloneNodes(target, nodes) {
      for (const node of nodes) {
        if (node.nodeType === Node.ELEMENT_NODE && node.tagName.toLowerCase() === "script") {
          const script = document.createElement("script");
          for (const attr of Array.from(node.attributes || [])) {
            script.setAttribute(attr.name, attr.value);
          }
          if (node.textContent) {
            script.textContent = node.textContent;
          }
          target.appendChild(script);
          continue;
        }
        target.appendChild(document.importNode(node, true));
      }
    }
    function replaceStandaloneDocument(standaloneHtml) {
      const parser = new DOMParser();
      const parsed = parser.parseFromString(standaloneHtml, "text/html");
      if (!parsed || !parsed.documentElement || !parsed.body) {
        return false;
      }
      const nextRoot = parsed.documentElement;
      const nextHead = parsed.head || parsed.createElement("head");
      const nextBody = parsed.body;
      const nextHeadNodes = Array.from(nextHead.childNodes || []);
      const nextBodyNodes = Array.from(nextBody.childNodes || []);
      copyElementAttributes(document.documentElement, nextRoot);
      copyElementAttributes(document.head, nextHead);
      copyElementAttributes(document.body, nextBody);
      document.title = parsed.title || document.title;
      document.head.replaceChildren();
      document.body.replaceChildren();
      appendStandaloneNodes(document.head, nextHeadNodes);
      appendStandaloneNodes(document.body, nextBodyNodes);
      return true;
    }
    const urlParams = new URLSearchParams(window.location.search);
    const workstreamParam = (urlParams.get("workstream") || "").trim().toUpperCase();
    const viewParam = (urlParams.get("view") || "").trim().toLowerCase();
    if ((viewParam === "spec" || viewParam === "plan") && workstreamParam) {
      const standaloneHtml = await backlogDataSource.loadDocument({ id: workstreamParam, view: viewParam });
      if (typeof standaloneHtml === "string" && standaloneHtml.trim()) {
        try {
          if (window.parent && window.parent !== window) {
            window.parent.postMessage({
              type: "odylith-radar-navigate",
              state: { workstream: workstreamParam, view: viewParam },
            }, "*");
          }
        } catch (_error) {
          // Ignore parent-shell sync failures; standalone rendering must still work.
        }
        replaceStandaloneDocument(standaloneHtml);
        return;
      }
    }

    const state = {
      query: "",
      section: "all",
      phase: "all",
      activity: "all",
      lane: "all",
      priority: "all",
      sort: "rank",
      mixBy: "complexity",
      selectedIdeaId: ""
    };

    const el = {
      stats: document.getElementById("stats"),
      query: document.getElementById("query"),
      section: document.getElementById("section"),
      phase: document.getElementById("phase"),
      activity: document.getElementById("activity"),
      lane: document.getElementById("lane"),
      priority: document.getElementById("priority"),
      sort: document.getElementById("sort"),
      meta: document.getElementById("meta"),
      analyticsPanel: document.getElementById("analytics-panel"),
      analyticsToggleHint: document.getElementById("analytics-toggle-hint"),
      graphVelocity: document.getElementById("graph-velocity"),
      graphCycle: document.getElementById("graph-cycle"),
      graphMix: document.getElementById("graph-mix"),
      mixByComplexity: document.getElementById("mix-by-complexity"),
      mixBySize: document.getElementById("mix-by-size"),
      list: document.getElementById("list"),
      detail: document.getElementById("detail"),
      detailEmpty: document.getElementById("detail-empty"),
      empty: document.getElementById("empty")
    };
    function initSharedQuickTooltips() {
  const QUICK_TOOLTIP_BIND_KEY = null;
  if (QUICK_TOOLTIP_BIND_KEY && document.body && document.body.dataset[QUICK_TOOLTIP_BIND_KEY] === "1") {
    return;
  }
  if (QUICK_TOOLTIP_BIND_KEY && document.body) {
    document.body.dataset[QUICK_TOOLTIP_BIND_KEY] = "1";
  }

  const QUICK_TOOLTIP_ATTR = "data-tooltip";
  const QUICK_TOOLTIP_EXCLUDE_CLOSEST = [];
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

    const ANALYTICS_OPEN_PREF_KEY = "odylith.backlog.analytics.open.v1";

    const loadedList = await backlogDataSource.loadList({});
    const all = Array.isArray(loadedList) ? loadedList : [];
    const allIdeaIds = new Set(all.map((row) => String(row.idea_id || "").trim()).filter(Boolean));
    const BACKLOG_LIST_WINDOW_THRESHOLD = 180;
    const BACKLOG_LIST_OVERSCAN = 24;
    const BACKLOG_LIST_ROW_HEIGHT = 88;
    const BACKLOG_LIST_HEADER_HEIGHT = 40;
    let latestRenderedRows = [];
    let latestListWindowKey = "";
    let listScrollFrame = 0;

    function handleLinkedWorkstreamClick(event) {
      const trigger = event.target.closest("[data-link-idea]");
      if (!trigger) return;
      event.preventDefault();
      const ideaId = String(trigger.getAttribute("data-link-idea") || "").trim();
      if (!ideaId || !allIdeaIds.has(ideaId)) return;
      state.selectedIdeaId = ideaId;
      render();
      el.detail?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    el.detail.addEventListener("click", handleLinkedWorkstreamClick);
    if (el.analyticsPanel) {
      el.analyticsPanel.addEventListener("toggle", () => {
        syncAnalyticsToggleHint();
        try {
          window.localStorage.setItem(ANALYTICS_OPEN_PREF_KEY, el.analyticsPanel.open ? "1" : "0");
        } catch (_error) {
          // ignore localStorage write failures
        }
        void renderAnalytics(sortRows(applyFilters()));
      });
    }
    el.list.addEventListener("scroll", () => {
      if (latestRenderedRows.length <= BACKLOG_LIST_WINDOW_THRESHOLD) return;
      if (listScrollFrame) return;
      listScrollFrame = window.requestAnimationFrame(() => {
        listScrollFrame = 0;
        renderList(latestRenderedRows, { fromScroll: true });
      });
    });

    function uniqueValues(field) {
      return [...new Set(all.map((row) => String(row[field] || "").trim()).filter(Boolean))].sort();
    }

    function stageLabel(value) {
      const token = String(value || "").trim().toLowerCase();
      if (token === "queued") return "idea";
      return token || "unknown";
    }

    function prettyLabel(value) {
      const token = String(value || "").trim();
      if (!token) return "-";
      if (token.includes("-")) return token;
      return token.charAt(0).toUpperCase() + token.slice(1);
    }

    function syncParentShellSelection() {
      try {
        if (!window.parent || window.parent === window) return;
        window.parent.postMessage({
          type: "odylith-radar-navigate",
          state: {
            workstream: String(state.selectedIdeaId || "").trim(),
            view: "",
          },
        }, "*");
      } catch (_error) {
        // Ignore parent-shell sync failures; local radar interactions must still work.
      }
    }

    function laneLabel(value) {
      const token = String(value || "").trim().toLowerCase();
      if (!token) return "-";
      if (token === "both") return "Cross-lane (Platform + Service)";
      if (token === "platform") return "Platform only";
      if (token === "service" || token === "services") return "Service only";
      return prettyLabel(token);
    }

    function formatCompactTimestamp(value) {
      const token = String(value || "").trim();
      if (!token) return "-";
      const parsed = Date.parse(token);
      if (Number.isNaN(parsed)) return token;
      const ts = new Date(parsed);
      const formatter = new Intl.DateTimeFormat([], {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZoneName: "short",
      });
      const partLookup = Object.fromEntries(
        formatter.formatToParts(ts).map((part) => [part.type, part.value]),
      );
      return [
        partLookup.month || "",
        partLookup.day || "",
        (partLookup.hour && partLookup.minute) ? `${partLookup.hour}:${partLookup.minute}` : "",
        partLookup.timeZoneName || "",
      ].filter(Boolean).join(" ");
    }

    function seedSelect(select, values, formatter) {
      values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = formatter ? formatter(value) : value;
        select.appendChild(option);
      });
    }

    seedSelect(el.lane, uniqueValues("impacted_lanes"), (value) => laneLabel(value));
    seedSelect(el.priority, uniqueValues("priority"));

    function escapeHtml(value) {
      return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function tooltipLookupPayload() {
      const payload = DATA.tooltip_lookup;
      return payload && typeof payload === "object" ? payload : {};
    }

    function sanitizeLookupObject(value) {
      const lookup = Object.create(null);
      if (!value || typeof value !== "object") return lookup;
      Object.entries(value).forEach(([keyRaw, valueRaw]) => {
        const key = String(keyRaw || "").trim();
        const text = String(valueRaw || "").trim();
        if (!key || !text) return;
        lookup[key] = text;
      });
      return lookup;
    }

    function sanitizeLookupListObject(value) {
      const lookup = Object.create(null);
      if (!value || typeof value !== "object") return lookup;
      Object.entries(value).forEach(([keyRaw, valueRaw]) => {
        const key = normalizeDiagramId(keyRaw);
        if (!key || !Array.isArray(valueRaw)) return;
        const tokens = normalizeIdList(valueRaw);
        if (!tokens.length) return;
        lookup[key] = tokens;
      });
      return lookup;
    }

    function normalizeDiagramId(value) {
      let token = String(value || "").trim().toUpperCase();
      if (!token) return "";
      if (token.startsWith("DIAGRAM:")) {
        token = token.slice("DIAGRAM:".length).trim();
      }
      if (/^D-\d{3,}$/.test(token)) {
        return token;
      }
      const compact = token.match(/^D(\d{3,})$/);
      if (compact) {
        return `D-${compact[1]}`;
      }
      return "";
    }

    const rawTooltipLookup = tooltipLookupPayload();
    const workstreamTitleLookup = sanitizeLookupObject(rawTooltipLookup.workstream_titles);
    const diagramTitleLookup = sanitizeLookupObject(rawTooltipLookup.diagram_titles);
    const componentTitleLookup = sanitizeLookupObject(rawTooltipLookup.component_titles);
    const diagramWorkstreamLookup = sanitizeLookupListObject(rawTooltipLookup.diagram_related_workstreams);

    function workstreamTooltip(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) return "";
      return workstreamTitleLookup[token] || token;
    }

    function diagramTooltip(diagramId) {
      const token = normalizeDiagramId(diagramId);
      if (!token) return "";
      return diagramTitleLookup[token] || token;
    }

    function atlasDiagramHref(diagramId, selectedIdeaId) {
      const token = normalizeDiagramId(diagramId);
      if (!token) return "../../odylith/index.html?tab=atlas";
      const workstreamId = String(selectedIdeaId || "").trim();
      const owners = Array.isArray(diagramWorkstreamLookup[token]) ? diagramWorkstreamLookup[token] : [];
      if (workstreamId && owners.includes(workstreamId)) {
        return `../../odylith/index.html?tab=atlas&workstream=${encodeURIComponent(workstreamId)}&diagram=${encodeURIComponent(token)}`;
      }
      return `../../odylith/index.html?tab=atlas&diagram=${encodeURIComponent(token)}`;
    }

    function componentTooltip(componentId, fallback = "") {
      const token = String(componentId || "").trim().toLowerCase();
      const fallbackText = String(fallback || "").trim();
      if (!token) return fallbackText;
      return componentTitleLookup[token] || fallbackText || token;
    }

    function syncAnalyticsToggleHint() {
      const expanded = Boolean(el.analyticsPanel && el.analyticsPanel.open);
      if (el.analyticsToggleHint) {
        el.analyticsToggleHint.textContent = expanded ? "Hide" : "Show";
      }
    }

    function setAnalyticsExpanded(expanded) {
      if (!el.analyticsPanel) return;
      el.analyticsPanel.open = Boolean(expanded);
      syncAnalyticsToggleHint();
    }

    function loadAnalyticsPreference() {
      let saved = "";
      try {
        saved = String(window.localStorage.getItem(ANALYTICS_OPEN_PREF_KEY) || "").trim();
      } catch (_error) {
        saved = "";
      }
      if (saved === "1") {
        setAnalyticsExpanded(true);
        return;
      }
      if (saved === "0") {
        setAnalyticsExpanded(false);
        return;
      }
      syncAnalyticsToggleHint();
    }

    function statBlock(label, value) {
      return `<div class="stat"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(value)}</div></div>`;
    }

    function summarizeVisibleSections(rows) {
      const counts = {
        queued: 0,
        execution: 0,
        parked: 0,
        finished: 0,
      };
      (Array.isArray(rows) ? rows : []).forEach((row) => {
        const section = String(row && row.section ? row.section : "").trim().toLowerCase();
        if (section === "execution") {
          counts.execution += 1;
          return;
        }
        if (section === "parked") {
          counts.parked += 1;
          return;
        }
        if (section === "finished") {
          counts.finished += 1;
          return;
        }
        if (section === "active") {
          counts.queued += 1;
        }
      });
      return counts;
    }

    function summaryStatRows(rows, waveSummary) {
      const counts = summarizeVisibleSections(rows);
      const wavePrograms = Number(waveSummary && waveSummary.program_count ? waveSummary.program_count : 0);
      const activeWaves = Number(waveSummary && waveSummary.active_wave_count ? waveSummary.active_wave_count : 0);
      const statRows = [
        statBlock("Index Updated", DATA.index_updated_display || "-"),
        statBlock("Queued", counts.queued),
        statBlock("Execution", counts.execution),
        statBlock("Parked", counts.parked),
        statBlock("Finished", counts.finished),
      ];
      if (wavePrograms > 0) {
        statRows.push(statBlock("Wave Programs", wavePrograms));
        statRows.push(statBlock("Active Waves", activeWaves));
      }
      return statRows;
    }

    function parseIsoDateToken(value) {
      const token = String(value || "").trim();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(token)) return null;
      const parsed = new Date(`${token}T00:00:00Z`);
      if (Number.isNaN(parsed.getTime())) return null;
      return parsed;
    }

    function toIsoDate(value) {
      return value.toISOString().slice(0, 10);
    }

    function toWeekBucket(value) {
      const copy = new Date(value.getTime());
      const day = (copy.getUTCDay() + 6) % 7;
      copy.setUTCDate(copy.getUTCDate() - day);
      return toIsoDate(copy);
    }

    function fromIsoDateToken(value) {
      return parseIsoDateToken(value);
    }

    function shiftDays(value, days) {
      const copy = new Date(value.getTime());
      copy.setUTCDate(copy.getUTCDate() + days);
      return copy;
    }

    function resolveFinishedDate(row) {
      return parseIsoDateToken(
        row.execution_end_date_display
        || row.execution_end_date
        || row.finished_sort_date_display
        || row.finished_sort_date
        || row.idea_date_display
        || row.idea_date
      );
    }

    function resolveExecutionDays(row) {
      const direct = String(row.execution_duration_days || "").trim();
      if (/^\d+$/.test(direct)) return Number.parseInt(direct, 10);
      const start = parseIsoDateToken(row.execution_start_date_display || row.execution_start_date);
      const end = parseIsoDateToken(row.execution_end_date_display || row.execution_end_date);
      if (!start || !end) return null;
      const delta = Math.floor((end.getTime() - start.getTime()) / 86400000);
      return delta >= 0 ? delta : null;
    }

    function movingAverage(values, windowSize) {
      const out = [];
      for (let idx = 0; idx < values.length; idx += 1) {
        const left = Math.max(0, idx - windowSize + 1);
        const window = values.slice(left, idx + 1);
        const avg = window.reduce((acc, item) => acc + item, 0) / window.length;
        out.push(Number(avg.toFixed(2)));
      }
      return out;
    }

    function percentile(values, p) {
      if (!values.length) return 0;
      const sorted = [...values].sort((a, b) => a - b);
      const pos = Math.max(0, Math.ceil((p / 100) * sorted.length) - 1);
      return sorted[Math.min(pos, sorted.length - 1)];
    }

    function niceCeil(value) {
      if (!Number.isFinite(value) || value <= 0) return 1;
      if (value <= 5) return Math.ceil(value);
      if (value <= 20) return Math.ceil(value / 2) * 2;
      return Math.ceil(value / 5) * 5;
    }

    function buildRecentWeekWindow(rows, weeksCount) {
      let anchor = new Date();
      rows.forEach((row) => {
        const finished = resolveFinishedDate(row);
        if (finished && finished > anchor) anchor = finished;
      });
      const anchorWeek = fromIsoDateToken(toWeekBucket(anchor)) || new Date();
      const window = [];
      for (let idx = weeksCount - 1; idx >= 0; idx -= 1) {
        const weekDate = shiftDays(anchorWeek, -7 * idx);
        const week = toIsoDate(weekDate);
        window.push({ week, label: week.slice(5) });
      }
      return window;
    }

    function buildVelocitySeries(rows, window) {
      const counts = new Map();
      rows
        .filter((row) => row.section === "finished")
        .forEach((row) => {
          const finished = resolveFinishedDate(row);
          if (!finished) return;
          const week = toWeekBucket(finished);
          counts.set(week, (counts.get(week) || 0) + 1);
        });
      const ordered = window.map((item) => ({
        week: item.week,
        label: item.label,
        count: counts.get(item.week) || 0,
      }));
      const ma = movingAverage(ordered.map((item) => item.count), 4);
      return ordered.map((item, idx) => ({ ...item, movingAvg: ma[idx] }));
    }

    function buildCycleSeries(rows, window) {
      const buckets = new Map();
      rows
        .filter((row) => row.section === "finished")
        .forEach((row) => {
          const finished = resolveFinishedDate(row);
          const days = resolveExecutionDays(row);
          if (!finished || days === null) return;
          const week = toWeekBucket(finished);
          const values = buckets.get(week) || [];
          values.push(days);
          buckets.set(week, values);
        });
      return window.map((item) => {
        const values = buckets.get(item.week) || [];
        if (!values.length) {
          return { week: item.week, label: item.label, median: null, p85: null, samples: 0 };
        }
        return {
          week: item.week,
          label: item.label,
          median: percentile(values, 50),
          p85: percentile(values, 85),
          samples: values.length,
        };
      });
    }

    function buildMixSeries(rows, byField, window) {
      const weekly = new Map();
      const totals = new Map();
      const weekSet = new Set(window.map((item) => item.week));
      rows
        .filter((row) => row.section === "finished")
        .forEach((row) => {
          const finished = resolveFinishedDate(row);
          if (!finished) return;
          const week = toWeekBucket(finished);
          if (!weekSet.has(week)) return;
          const categoryRaw = String(row[byField] || "").trim();
          const category = categoryRaw || "unknown";
          const weekBucket = weekly.get(week) || new Map();
          weekBucket.set(category, (weekBucket.get(category) || 0) + 1);
          weekly.set(week, weekBucket);
          totals.set(category, (totals.get(category) || 0) + 1);
        });

      const topCategories = [...totals.entries()]
        .sort((a, b) => {
          if (b[1] !== a[1]) return b[1] - a[1];
          return String(a[0]).localeCompare(String(b[0]));
        })
        .slice(0, 4)
        .map(([label]) => label);
      if (!topCategories.length) {
        return {
          weeks: window.map((item) => item.week),
          labels: window.map((item) => item.label),
          categories: [],
          values: [],
          totalFinished: 0,
          activeWeeks: 0,
        };
      }
      const categories = totals.size > topCategories.length ? [...topCategories, "other"] : [...topCategories];
      const weeks = window.map((item) => item.week);
      const labels = window.map((item) => item.label);

      let totalFinished = 0;
      let activeWeeks = 0;
      const values = weeks.map((week) => {
        const bucket = weekly.get(week) || new Map();
        const row = {};
        let other = 0;
        let weekTotal = 0;
        bucket.forEach((count, key) => {
          if (topCategories.includes(key)) {
            row[key] = count;
            weekTotal += count;
          } else {
            other += count;
          }
        });
        if (categories.includes("other")) {
          row.other = other;
          weekTotal += other;
        }
        totalFinished += weekTotal;
        if (weekTotal > 0) activeWeeks += 1;
        return row;
      });

      return { weeks, labels, categories, values, totalFinished, activeWeeks };
    }

    function buildPath(points, getX, getY, key) {
      const path = [];
      let open = false;
      points.forEach((point, idx) => {
        const value = point[key];
        if (!Number.isFinite(value)) {
          open = false;
          return;
        }
        path.push(`${open ? "L" : "M"}${getX(idx)},${getY(value)}`);
        open = true;
      });
      return path.join(" ");
    }

    function renderLineChart(target, points, config) {
      if (!points.length) {
        target.innerHTML = "";
        return;
      }
      const finiteValues = points
        .flatMap((point) => [point[config.primaryKey], point[config.secondaryKey]])
        .filter((value) => Number.isFinite(value));
      if (!finiteValues.length) {
        target.innerHTML = "";
        return;
      }
      const width = 560;
      const height = 220;
      const margin = { top: 12, right: 10, bottom: 30, left: 38 };
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const xAt = (idx) => (
        points.length <= 1
          ? margin.left + (plotWidth / 2)
          : margin.left + ((idx / (points.length - 1)) * plotWidth)
      );

      const yMax = niceCeil(Math.max(...finiteValues));
      const yAt = (value) => margin.top + ((yMax - value) / yMax) * plotHeight;

      const primaryPath = buildPath(points, xAt, yAt, config.primaryKey);
      const secondaryPath = buildPath(points, xAt, yAt, config.secondaryKey);
      const yTicks = [...new Set([0, Number((yMax / 2).toFixed(1)), yMax])];
      const xLabelStep = Math.max(1, Math.ceil(points.length / 6));

      const gridHtml = yTicks
        .map((tick) => {
          const y = yAt(tick);
          return `
            <line class="chart-grid" x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" />
            <text class="chart-axis" x="${margin.left - 6}" y="${y + 3}" text-anchor="end">${tick}</text>
          `;
        })
        .join("");

      const barsHtml = config.barsKey
        ? points
          .map((point, idx) => {
            const value = point[config.barsKey];
            if (!Number.isFinite(value) || value <= 0) return "";
            const slotWidth = points.length <= 1 ? plotWidth : plotWidth / points.length;
            const barWidth = Math.max(7, slotWidth * 0.62);
            const x = points.length <= 1
              ? margin.left + (plotWidth / 2) - (barWidth / 2)
              : margin.left + (idx * slotWidth) + ((slotWidth - barWidth) / 2);
            const y = yAt(value);
            const h = (margin.top + plotHeight) - y;
            return `<rect class="chart-bar-primary" x="${x}" y="${y}" width="${barWidth}" height="${Math.max(1, h)}"></rect>`;
          })
          .join("")
        : "";

      const xLabelsHtml = points
        .map((point, idx) => {
          if (idx % xLabelStep !== 0 && idx !== points.length - 1) return "";
          return `<text class="chart-axis" x="${xAt(idx)}" y="${height - 8}" text-anchor="middle">${escapeHtml(point.label)}</text>`;
        })
        .join("");

      const primaryPoints = points
        .map((point, idx) => (
          Number.isFinite(point[config.primaryKey])
            ? `<circle class="chart-point-primary" cx="${xAt(idx)}" cy="${yAt(point[config.primaryKey])}" r="3"></circle>`
            : ""
        ))
        .join("");
      const secondaryPoints = points
        .map((point, idx) => (
          Number.isFinite(point[config.secondaryKey])
            ? `<circle class="chart-point-secondary" cx="${xAt(idx)}" cy="${yAt(point[config.secondaryKey])}" r="3"></circle>`
            : ""
        ))
        .join("");

      target.innerHTML = `
        <div class="chart-wrap">
          <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(config.ariaLabel)}">
            ${gridHtml}
            ${barsHtml}
            <path class="chart-line-primary" d="${primaryPath}"></path>
            <path class="chart-line-secondary" d="${secondaryPath}"></path>
            ${primaryPoints}
            ${secondaryPoints}
            ${xLabelsHtml}
          </svg>
        </div>
        <div class="chart-legend">
          <span class="legend-item"><span class="legend-dot" style="background:#0f766e"></span>${escapeHtml(config.primaryLabel)}</span>
          <span class="legend-item"><span class="legend-dot" style="background:#2563eb"></span>${escapeHtml(config.secondaryLabel)}</span>
          ${config.barsLabel ? `<span class="legend-item"><span class="legend-dot" style="background:rgba(37,99,235,0.55)"></span>${escapeHtml(config.barsLabel)}</span>` : ""}
        </div>
        ${config.summaryText ? `<div class="graph-note">${escapeHtml(config.summaryText)}</div>` : ""}
      `;
    }

    function renderMixChart(target, mixData, byField) {
      if (!mixData.weeks.length || !mixData.categories.length) {
        target.innerHTML = "";
        return;
      }
      const width = 560;
      const height = 220;
      const margin = { top: 12, right: 10, bottom: 30, left: 38 };
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const palette = ["#0f766e", "#2563eb", "#ea580c", "#7c3aed", "#dc2626"];
      const colorByCategory = new Map(mixData.categories.map((category, idx) => [category, palette[idx % palette.length]]));

      const totalsByWeek = mixData.values.map((row) =>
        mixData.categories.reduce((sum, category) => sum + Number(row[category] || 0), 0)
      );
      const yMax = Math.max(1, ...totalsByWeek);
      const xLabelStep = Math.max(1, Math.ceil(mixData.weeks.length / 6));

      const barGap = 8;
      const slotWidth = plotWidth / mixData.weeks.length;
      const barWidth = Math.max(10, slotWidth - barGap);

      const yAt = (value) => margin.top + ((yMax - value) / yMax) * plotHeight;
      const yTicks = [0, Math.round(yMax / 2), yMax];

      const gridHtml = yTicks
        .map((tick) => {
          const y = yAt(tick);
          return `
            <line class="chart-grid" x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" />
            <text class="chart-axis" x="${margin.left - 6}" y="${y + 3}" text-anchor="end">${tick}</text>
          `;
        })
        .join("");

      const barsHtml = mixData.weeks
        .map((week, idx) => {
          const row = mixData.values[idx];
          let running = 0;
          const x = margin.left + idx * slotWidth + Math.max(0, (slotWidth - barWidth) / 2);
          const segments = mixData.categories.map((category) => {
            const count = Number(row[category] || 0);
            if (!count) return "";
            const yBottom = yAt(running);
            running += count;
            const yTop = yAt(running);
            const heightRect = Math.max(1, yBottom - yTop);
            return `<rect x="${x}" y="${yTop}" width="${barWidth}" height="${heightRect}" fill="${colorByCategory.get(category)}"></rect>`;
          }).join("");
          return segments;
        })
        .join("");

      const xLabelsHtml = mixData.weeks
        .map((week, idx) => {
          if (idx % xLabelStep !== 0 && idx !== mixData.weeks.length - 1) return "";
          const x = margin.left + idx * slotWidth + (slotWidth / 2);
          const label = Array.isArray(mixData.labels) ? mixData.labels[idx] : week.slice(5);
          return `<text class="chart-axis" x="${x}" y="${height - 8}" text-anchor="middle">${escapeHtml(label)}</text>`;
        })
        .join("");

      const legendHtml = mixData.categories
        .map((category) => {
          const label = category === "other" ? "Other" : category;
          return `<span class="legend-item"><span class="legend-dot" style="background:${colorByCategory.get(category)}"></span>${escapeHtml(label)}</span>`;
        })
        .join("");

      target.innerHTML = `
        <div class="chart-wrap">
          <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Delivery mix by ${escapeHtml(byField)} over time">
            ${gridHtml}
            ${barsHtml}
            ${xLabelsHtml}
          </svg>
        </div>
        <div class="chart-legend">${legendHtml}</div>
        <div class="graph-note">Last ${mixData.weeks.length}w: ${mixData.totalFinished} completed across ${mixData.activeWeeks} active week(s).</div>
      `;
    }

    function syncMixToggleUi() {
      const complexityActive = state.mixBy === "complexity";
      el.mixByComplexity.classList.toggle("active", complexityActive);
      el.mixBySize.classList.toggle("active", !complexityActive);
    }

    function renderGraphs(rows) {
      const weekWindow = buildRecentWeekWindow(rows, 12);
      const velocity = buildVelocitySeries(rows, weekWindow);
      const velocityTotal = velocity.reduce((sum, item) => sum + Number(item.count || 0), 0);
      const velocityAvg = (velocityTotal / Math.max(1, velocity.length)).toFixed(2);
      renderLineChart(el.graphVelocity, velocity, {
        primaryKey: "count",
        secondaryKey: "movingAvg",
        primaryLabel: "Finished/week",
        secondaryLabel: "4-week moving avg",
        barsKey: "count",
        barsLabel: "Finished bars",
        ariaLabel: "Execution velocity trend",
        summaryText: `Last ${velocity.length}w: ${velocityTotal} completed · avg ${velocityAvg}/week.`,
      });

      const cycle = buildCycleSeries(rows, weekWindow);
      const weeksWithSamples = cycle.filter((item) => item.samples > 0).length;
      const latestCycle = [...cycle].reverse().find((item) => item.samples > 0);
      const lowSample = cycle.reduce((sum, item) => sum + Number(item.samples || 0), 0) < 3;
      renderLineChart(el.graphCycle, cycle, {
        primaryKey: "median",
        secondaryKey: "p85",
        primaryLabel: "Median days",
        secondaryLabel: "P85 days",
        ariaLabel: "Cycle time trend",
        summaryText: latestCycle
          ? `Weeks with samples: ${weeksWithSamples}/${cycle.length} · latest median ${latestCycle.median}d, p85 ${latestCycle.p85}d${lowSample ? " (low sample confidence)." : "."}`
          : "",
      });

      syncMixToggleUi();
      const field = state.mixBy === "size" ? "sizing" : "complexity";
      renderMixChart(el.graphMix, buildMixSeries(rows, field, weekWindow), field);
    }

    function renderAnalytics(rows) {
      if (!el.analyticsPanel || !el.analyticsPanel.open) {
        el.graphVelocity.innerHTML = "";
        el.graphCycle.innerHTML = "";
        el.graphMix.innerHTML = "";
        syncMixToggleUi();
        return;
      }
      renderGraphs(rows);
    }

    function applyFilters() {
      const q = state.query.trim().toLowerCase();
      const exactIdeaIdQuery = q && all.some((row) => String(row.idea_id || "").trim().toLowerCase() === q);
      return all.filter((row) => {
        if (state.section !== "all" && row.section !== state.section) return false;
        if (state.phase !== "all") {
          if (row.section !== "execution") return false;
          if (stageLabel(row.status) !== state.phase) return false;
        }
        if (state.activity !== "all") {
          if (row.section !== "execution") return false;
          const stateToken = normalizeExecutionState(row.execution_state);
          const activity = (
            stateToken === "actively_executing"
            || stateToken === "planning_active"
          ) ? "active" : "quiet";
          if (activity !== state.activity) return false;
        }
        if (state.lane !== "all" && row.impacted_lanes !== state.lane) return false;
        if (state.priority !== "all" && row.priority !== state.priority) return false;
        if (!q) return true;
        const ideaId = String(row.idea_id || "").trim().toLowerCase();
        if (exactIdeaIdQuery) {
          return ideaId === q;
        }
        const hay = String(row.search_text || [
          row.idea_id,
          row.title,
          row.ordering_rationale,
          row.rationale_text,
          Array.isArray(row.rationale_bullets) ? row.rationale_bullets.join(" ") : "",
        ].join(" ")).toLowerCase();
        return hay.includes(q);
      });
    }

    function sortRows(rows) {
      const sectionOrder = { execution: 0, parked: 1, active: 2, finished: 3 };
      const executionStatusOrder = { implementation: 0, planning: 1 };
      const executionStateOrder = {
        actively_executing: 0,
        planning_active: 1,
        planned_only: 2,
        implementation_no_live_signal: 2,
        inactive: 3,
      };
      const copy = [...rows];
      copy.sort((a, b) => {
        if (a.section !== b.section) return (sectionOrder[a.section] ?? 99) - (sectionOrder[b.section] ?? 99);
        if (a.section === "execution") {
          const leftState = executionStateOrder[normalizeExecutionState(a.execution_state)] ?? 99;
          const rightState = executionStateOrder[normalizeExecutionState(b.execution_state)] ?? 99;
          if (leftState !== rightState) return leftState - rightState;
          const left = executionStatusOrder[String(a.status || "").toLowerCase()] ?? 99;
          const right = executionStatusOrder[String(b.status || "").toLowerCase()] ?? 99;
          if (left !== right) return left - right;
          if (b.ordering_score !== a.ordering_score) return b.ordering_score - a.ordering_score;
          if (state.sort === "date") {
            const dateCmp = String(b.date).localeCompare(String(a.date));
            if (dateCmp !== 0) return dateCmp;
          }
        }
        if (a.section === "finished") {
          const completedCmp = String(b.finished_sort_date || b.date).localeCompare(
            String(a.finished_sort_date || a.date)
          );
          if (completedCmp !== 0) return completedCmp;
          const planDateCmp = String(b.plan_file_date || "").localeCompare(
            String(a.plan_file_date || "")
          );
          if (planDateCmp !== 0) return planDateCmp;
          const updatedCmp = String(b.plan_updated_date || "").localeCompare(
            String(a.plan_updated_date || "")
          );
          if (updatedCmp !== 0) return updatedCmp;
        }
        if (a.section === "parked") {
          const updatedCmp = String(b.plan_updated_date || "").localeCompare(
            String(a.plan_updated_date || "")
          );
          if (updatedCmp !== 0) return updatedCmp;
          const dateCmp = String(b.date).localeCompare(String(a.date));
          if (dateCmp !== 0) return dateCmp;
        }
        if (a.section !== "finished" && (state.sort === "score" || a.section === "execution")) {
          if (b.ordering_score !== a.ordering_score) return b.ordering_score - a.ordering_score;
        } else if (a.section !== "finished" && state.sort === "date") {
          const dateCmp = String(b.date).localeCompare(String(a.date));
          if (dateCmp !== 0) return dateCmp;
        }
        if (a.rank_num !== b.rank_num) return a.rank_num - b.rank_num;
        return String(a.idea_id).localeCompare(String(b.idea_id));
      });
      return copy;
    }

    function statusChipClass(status) {
      const token = stageLabel(status);
      if (token === "planning") return "status-chip status-planning";
      if (token === "implementation") return "status-chip status-implementation";
      if (token === "parked") return "status-chip status-parked";
      if (token === "finished") return "status-chip status-finished";
      return "status-chip";
    }

    function executionStageLabel(status) {
      const token = stageLabel(status);
      if (token === "planning") return "Planning";
      if (token === "implementation") return "Implementation";
      if (token === "finished") return "Finished";
      if (token === "idea") return "Idea";
      return prettyLabel(token);
    }

    function normalizeExecutionState(value) {
      const token = String(value || "").trim().toLowerCase();
      if (
        token === "actively_executing"
        || token === "planning_active"
        || token === "planned_only"
        || token === "implementation_no_live_signal"
        || token === "inactive"
      ) {
        return token;
      }
      return "inactive";
    }

    function executionStateLabel(value) {
      const token = normalizeExecutionState(value);
      if (token === "actively_executing") return "Live: Active";
      if (token === "planning_active") return "Plan: Active";
      if (token === "planned_only") return "Plan: Quiet";
      if (token === "implementation_no_live_signal") return "Live: Quiet";
      return "Live: Quiet";
    }

    function executionSignalTooltip(status, value, activeWindowMinutes) {
      const stage = executionStageLabel(status);
      const token = normalizeExecutionState(value);
      const windowMinutes = Number.isFinite(Number(activeWindowMinutes)) && Number(activeWindowMinutes) > 0
        ? Math.round(Number(activeWindowMinutes))
        : 15;
      const activityLabel = stage === "Planning"
        ? "odylith/technical-plans/spec activity"
        : (stage === "Implementation" ? "code/test activity" : "workstream activity");
      if (token === "actively_executing" || token === "planning_active") {
        return `${stage} phase with active ${activityLabel} in the last ${windowMinutes} minutes.`;
      }
      return `${stage} phase with quiet ${activityLabel} in the last ${windowMinutes} minutes.`;
    }

    function executionActiveWindowMinutes(meta) {
      const raw = meta && typeof meta === "object" ? Number(meta.active_window_minutes) : NaN;
      if (Number.isFinite(raw) && raw > 0) {
        return Math.round(raw);
      }
      return 15;
    }

    function executionStateClass(value) {
      const token = normalizeExecutionState(value);
      if (token === "actively_executing") return "exec-actively-executing";
      if (token === "planning_active") return "exec-planning-active";
      if (token === "planned_only") return "exec-planned-only";
      if (token === "implementation_no_live_signal") return "exec-implementation-no-live-signal";
      if (token === "inactive") return "exec-signal-quiet";
      return "";
    }

    function rowHtml(row) {
      const rankLabel = row.section === "execution"
        ? "Pipeline"
        : (row.section === "finished" ? "Finished" : (row.section === "parked" ? "Parked" : `Rank #${row.rank}`));
      const rankChipClass = row.section === "execution"
        ? "rank-chip-execution"
        : (row.section === "finished" ? "rank-chip-finished" : (row.section === "parked" ? "rank-chip-parked" : "rank-chip-active"));
      const activeClass = row.idea_id === state.selectedIdeaId ? "active" : "";
      const ageRaw = String(row.idea_age_days || "-");
      const ageLabel = /^\d+$/.test(ageRaw) ? `${ageRaw}d` : ageRaw;
      const executionDaysRaw = String(row.execution_duration_days || row.execution_age_days || "-");
      const executionDays = /^\d+$/.test(executionDaysRaw) ? `${executionDaysRaw}d` : "n/a";
      const wsType = workstreamTypeInfo(row);
      const typeChips = (() => {
        if (wsType.type === "umbrella") {
          return `<span class="chip ws-umbrella">Umbrella</span>`;
        }
        if (wsType.type === "child") {
          const parentToken = compactWorkstreamId(wsType.parent);
          const childLabel = parentToken ? `↳ ${parentToken}` : "↳";
          const parentTooltip = workstreamTooltip(wsType.parent);
          const tooltip = parentTooltip ? `Parent workstream: ${parentTooltip}` : "";
          const tooltipAttrs = tooltip
            ? ` data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}"`
            : "";
          return `<span class="chip ws-child"${tooltipAttrs}>${escapeHtml(childLabel)}</span>`;
        }
        return "";
      })();
      const executionState = String(row.execution_state || "").trim().toLowerCase();
      const executionMeta = row.execution_state_meta && typeof row.execution_state_meta === "object"
        ? row.execution_state_meta
        : {};
      const activeWindowMinutes = executionActiveWindowMinutes(executionMeta);
      const stageChip = row.section === "execution" || row.section === "parked"
        ? `<span class="chip ${escapeHtml(statusChipClass(row.status))}" data-tooltip="Canonical backlog stage for this workstream.">${escapeHtml(executionStageLabel(row.status))}</span>`
        : "";
      const executionChip = row.section === "execution"
        ? `<span class="chip execution-chip ${escapeHtml(executionStateClass(executionState))}" data-tooltip="${escapeHtml(executionSignalTooltip(row.status, executionState, activeWindowMinutes))}">${escapeHtml(executionStateLabel(executionState))}</span>`
        : "";
      const waveChips = executionWaveRoleChips(row);
      return `
        <button class="row ${activeClass}" data-idea-id="${escapeHtml(row.idea_id)}">
          <div class="row-top">
            <span class="rank-chip ${escapeHtml(rankChipClass)}">${escapeHtml(rankLabel)}</span>
            <strong class="row-title">${escapeHtml(row.title)}</strong>
          </div>
          <div class="row-meta">
            <p class="row-id">${escapeHtml(row.idea_id)}</p>
            <div class="row-chips">${typeChips}${stageChip}${executionChip}</div>
          </div>
          <div class="row-chips">
            ${waveChips}
            <span class="chip">Age ${escapeHtml(ageLabel)}</span>
            <span class="chip">Exec ${escapeHtml(executionDays)}</span>
          </div>
        </button>
      `;
    }

    function sectionLabel(section) {
      if (section === "execution") return "Delivery Pipeline";
      if (section === "active") return "Idea Stage";
      if (section === "parked") return "Parked";
      if (section === "finished") return "Finished";
      return "Other";
    }

    function backlogListItemHeight(item) {
      return item && item.kind === "header" ? BACKLOG_LIST_HEADER_HEIGHT : BACKLOG_LIST_ROW_HEIGHT;
    }

    function buildBacklogListItems(rows) {
      const sectionOrder = ["execution", "parked", "active", "finished"];
      const items = [];
      sectionOrder.forEach((sectionKey) => {
        const grouped = rows.filter((row) => row.section === sectionKey);
        if (!grouped.length) return;
        items.push({
          kind: "header",
          key: `header:${sectionKey}`,
          sectionKey,
          label: sectionLabel(sectionKey),
          count: grouped.length,
        });
        grouped.forEach((row) => {
          items.push({ kind: "row", key: `row:${row.idea_id}`, row });
        });
      });
      const ungrouped = rows.filter((row) => !sectionOrder.includes(String(row.section || "")));
      if (ungrouped.length) {
        items.push({
          kind: "header",
          key: "header:other",
          sectionKey: "other",
          label: "Other",
          count: ungrouped.length,
        });
        ungrouped.forEach((row) => {
          items.push({ kind: "row", key: `row:${row.idea_id}`, row });
        });
      }
      return items;
    }

    function backlogListOffsetForIndex(items, index) {
      let offset = 0;
      for (let cursor = 0; cursor < index; cursor += 1) {
        offset += backlogListItemHeight(items[cursor]);
      }
      return offset;
    }

    function ensureBacklogSelectionVisible(items, selectedIdeaId) {
      if (items.length <= BACKLOG_LIST_WINDOW_THRESHOLD) return;
      const selectedIndex = items.findIndex((item) => item.kind === "row" && item.row.idea_id === selectedIdeaId);
      if (selectedIndex < 0) return;
      const viewportHeight = Math.max(1, Number(el.list.clientHeight || 640));
      const scrollTop = Number(el.list.scrollTop || 0);
      const top = backlogListOffsetForIndex(items, selectedIndex);
      const bottom = top + BACKLOG_LIST_ROW_HEIGHT;
      if (top >= scrollTop && bottom <= (scrollTop + viewportHeight)) return;
      el.list.scrollTop = Math.max(0, top - Math.max(24, Math.round(viewportHeight * 0.3)));
    }

    function elementFullyVisibleWithinContainer(container, element) {
      if (!container || !element) return false;
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      return elementRect.top >= containerRect.top && elementRect.bottom <= containerRect.bottom;
    }

    function resolveBacklogListWindow(items) {
      if (items.length <= BACKLOG_LIST_WINDOW_THRESHOLD) {
        return { beforePx: 0, afterPx: 0, items, key: `all:${items.length}` };
      }
      const viewportHeight = Math.max(1, Number(el.list.clientHeight || 640));
      const scrollTop = Number(el.list.scrollTop || 0);
      const startPx = Math.max(0, scrollTop - (BACKLOG_LIST_OVERSCAN * BACKLOG_LIST_ROW_HEIGHT));
      const endPx = scrollTop + viewportHeight + (BACKLOG_LIST_OVERSCAN * BACKLOG_LIST_ROW_HEIGHT);
      let cursorPx = 0;
      let startIndex = 0;
      while (startIndex < items.length) {
        const nextPx = cursorPx + backlogListItemHeight(items[startIndex]);
        if (nextPx >= startPx) break;
        cursorPx = nextPx;
        startIndex += 1;
      }
      const beforePx = cursorPx;
      let endIndex = startIndex;
      while (endIndex < items.length && cursorPx < endPx) {
        cursorPx += backlogListItemHeight(items[endIndex]);
        endIndex += 1;
      }
      let afterPx = 0;
      for (let cursor = endIndex; cursor < items.length; cursor += 1) {
        afterPx += backlogListItemHeight(items[cursor]);
      }
      return {
        beforePx,
        afterPx,
        items: items.slice(startIndex, endIndex),
        key: `${startIndex}:${endIndex}`,
      };
    }

    function renderList(rows, options = {}) {
      latestRenderedRows = Array.isArray(rows) ? rows.slice() : [];
      if (!rows.length) {
        el.list.innerHTML = "";
        state.selectedIdeaId = "";
        latestListWindowKey = "empty";
        return;
      }
      if (!rows.some((row) => row.idea_id === state.selectedIdeaId)) {
        state.selectedIdeaId = rows[0].idea_id;
      }
      const items = buildBacklogListItems(rows);
      if (!options.fromScroll && !options.preserveListScroll) {
        ensureBacklogSelectionVisible(items, state.selectedIdeaId);
      }
      const windowed = resolveBacklogListWindow(items);
      if (options.fromScroll && windowed.key === latestListWindowKey) {
        return;
      }
      latestListWindowKey = windowed.key;
      const chunks = [];
      if (windowed.beforePx > 0) {
        chunks.push(`<div class="list-spacer" aria-hidden="true" style="height:${windowed.beforePx}px"></div>`);
      }
      windowed.items.forEach((item) => {
        if (item.kind === "header") {
          const sectionClass = item.sectionKey === "other" ? "" : ` list-section-${escapeHtml(item.sectionKey)}`;
          chunks.push(
            `<div class="list-section-head${sectionClass}">${escapeHtml(item.label)} (${item.count})</div>`
          );
          return;
        }
        chunks.push(rowHtml(item.row));
      });
      if (windowed.afterPx > 0) {
        chunks.push(`<div class="list-spacer" aria-hidden="true" style="height:${windowed.afterPx}px"></div>`);
      }
      el.list.innerHTML = chunks.join("");
      el.list.querySelectorAll(".row").forEach((button) => {
        button.addEventListener("click", () => {
          const preserveListScroll = elementFullyVisibleWithinContainer(el.list, button);
          state.selectedIdeaId = button.dataset.ideaId || "";
          render({ preserveListScroll });
        });
        const ideaId = String(button.dataset.ideaId || "").trim();
        if (ideaId) {
          button.addEventListener("mouseenter", () => {
            backlogDataSource.prefetch(ideaId);
          });
          button.addEventListener("focus", () => {
            backlogDataSource.prefetch(ideaId);
          });
        }
      });
    }

    function toBulletHtml(row) {
      const bullets = Array.isArray(row.rationale_bullets) ? row.rationale_bullets.filter(Boolean) : [];
      const lines = bullets.length ? bullets : [row.ordering_rationale || "No decision basis recorded."];
      if (lines.length === 1) {
        return `<p>${escapeHtml(lines[0])}</p>`;
      }
      return `<ul class="bullets">${lines.map((line) => renderDecisionBasisLine(line)).join("")}</ul>`;
    }

    function decisionBasisLabel(label) {
      const token = String(label || "").trim().toLowerCase();
      if (token === "why now" || token === "why this moved") return "Why now";
      if (token === "expected outcome" || token === "expected value capture") return "Expected outcome";
      if (token === "tradeoff" || token === "cost/risk tradeoff") return "Tradeoff";
      if (token === "deferred for now" || token === "what is deferred and why") return "Deferred for now";
      if (token === "ranking basis" || token === "override note") return "Ranking basis";
      return humanizeToken(label);
    }

    function renderDecisionBasisLine(line) {
      const raw = String(line || "").trim();
      const match = raw.match(/^([^:]+):\s*(.+)$/);
      if (!match) return `<li>${escapeHtml(raw)}</li>`;
      const [, label, body] = match;
      return `<li>${escapeHtml(decisionBasisLabel(label))}: ${escapeHtml(body)}</li>`;
    }

    function splitInlineBulletText(value) {
      const raw = String(value || "").trim();
      if (!raw) return [];
      const normalized = raw.replace(/\s+/g, " ").trim();
      const looksLikeInlineList = normalized.startsWith("- ")
        || normalized.includes(". - ")
        || normalized.includes("; - ")
        || normalized.includes("? - ")
        || normalized.includes("! - ");
      if (!looksLikeInlineList) return [];
      const body = normalized.startsWith("- ") ? normalized.slice(2) : normalized;
      return body
        .split(/\s+-\s+/)
        .map((token) => token.trim())
        .filter(Boolean);
    }

    function successMetricsHtml(row) {
      const explicitMetrics = Array.isArray(row.success_metrics_items)
        ? row.success_metrics_items.map((token) => String(token || "").trim()).filter(Boolean)
        : [];
      const raw = String(row.success_metrics || "").trim();
      const inlineMetrics = explicitMetrics.length ? [] : splitInlineBulletText(raw);
      const metrics = explicitMetrics.length ? explicitMetrics : inlineMetrics;
      const shouldRenderList = explicitMetrics.length > 0
        || metrics.length > 1
        || (metrics.length === 1 && raw.startsWith("- "));
      if (shouldRenderList) {
        return `<ul class="bullets">${metrics.map((metric) => `<li>${escapeHtml(metric)}</li>`).join("")}</ul>`;
      }
      return `<p>${escapeHtml(raw || "Not captured in the idea spec yet.")}</p>`;
    }

    function summarySectionHtml(value, fallback) {
      const raw = String(value || "").trim();
      const bullets = splitInlineBulletText(raw);
      if (bullets.length) {
        return `<ul class="bullets">${bullets.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
      }
      return `<p>${escapeHtml(raw || fallback || "Not captured in the idea spec yet.")}</p>`;
    }

    function normalizeIdList(values) {
      if (!Array.isArray(values)) return [];
      const intentionalEmptyTokens = new Set(["none", "n/a", "na", "null", "nil", "-"]);
      return values
        .map((value) => String(value || "").trim())
        .filter((token) => token && !intentionalEmptyTokens.has(token.toLowerCase()));
    }

    function normalizeDiagramIdList(values) {
      const normalized = [];
      const seen = new Set();
      normalizeIdList(values)
        .map((token) => normalizeDiagramId(token))
        .forEach((token) => {
          if (!token || seen.has(token)) return;
          seen.add(token);
          normalized.push(token);
        });
      return normalized;
    }

    function traceabilityPayload() {
      const payload = DATA.traceability_index || DATA.traceability_graph;
      return payload && typeof payload === "object" ? payload : {};
    }

    function workstreamTrace(ideaId) {
      const payload = traceabilityPayload();
      const rows = Array.isArray(payload.workstreams) ? payload.workstreams : [];
      return rows.find((row) => row.idea_id === ideaId) || null;
    }

    function executionWavePayload() {
      const payload = DATA.execution_waves;
      if (payload && typeof payload === "object") {
        return payload;
      }
      return { summary: {}, programs: [], workstreams: {} };
    }

    function executionWavePrograms() {
      const payload = executionWavePayload();
      return Array.isArray(payload.programs) ? payload.programs : [];
    }

    function executionWaveProgramByUmbrella(umbrellaId) {
      const token = String(umbrellaId || "").trim();
      if (!token) return null;
      return executionWavePrograms().find((row) => String(row && row.umbrella_id ? row.umbrella_id : "").trim() === token) || null;
    }

    function workstreamWavePrograms(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) return [];
      const payload = executionWavePayload();
      const byWorkstream = payload && payload.workstreams && typeof payload.workstreams === "object"
        ? payload.workstreams
        : {};
      return Array.isArray(byWorkstream[token]) ? byWorkstream[token] : [];
    }

    function waveStatusChipClass(status) {
  const token = String(status || "").trim().toLowerCase();
  if (token === "active") return "wave-status-active";
  if (token === "planned") return "wave-status-planned";
  if (token === "blocked") return "wave-status-blocked";
  if (token === "complete") return "wave-status-complete";
  return "wave-status-other";
}

function executionWavePercent(numerator, denominator) {
  const value = Number(numerator || 0);
  const total = Number(denominator || 0);
  if (!Number.isFinite(value) || !Number.isFinite(total) || total <= 0) return "";
  const boundedValue = Math.min(Math.max(value, 0), total);
  return `${Math.round((boundedValue / total) * 100)}%`;
}

function executionWaveProgressRatio(value) {
  const ratio = Number(value);
  if (!Number.isFinite(ratio)) return null;
  return Math.min(Math.max(ratio, 0), 1);
}

function executionWaveRefIdeaId(ref) {
  if (!ref || typeof ref !== "object") return "";
  return String(ref.idea_id || ref.workstream_id || "").trim();
}

function executionWaveResolvedStatus(ref, options = {}) {
  const explicitStatus = String(ref && ref.status ? ref.status : "").trim().toLowerCase();
  if (explicitStatus) return explicitStatus;
  const resolveWorkstreamStatus = typeof options.resolveWorkstreamStatus === "function"
    ? options.resolveWorkstreamStatus
    : null;
  if (!resolveWorkstreamStatus) return "";
  const resolvedStatus = String(resolveWorkstreamStatus(ref) || "").trim().toLowerCase();
  return resolvedStatus;
}

function executionWaveResolvedProgress(ref, options = {}) {
  const resolveWorkstreamProgress = typeof options.resolveWorkstreamProgress === "function"
    ? options.resolveWorkstreamProgress
    : null;
  if (!resolveWorkstreamProgress) return null;
  return executionWaveProgressRatio(resolveWorkstreamProgress(ref));
}

function executionWaveStatusIsClosed(status) {
  return status === "finished" || status === "complete" || status === "parked" || status === "superseded";
}

function executionWaveWorkstreamCompletion(workstreams, options = {}) {
  const rows = Array.isArray(workstreams) ? workstreams : [];
  let totalCount = 0;
  let completeCount = 0;
  rows.forEach((row) => {
    const ideaId = executionWaveRefIdeaId(row);
    if (!ideaId) return;
    totalCount += 1;
    const status = executionWaveResolvedStatus(row, options);
    if (executionWaveStatusIsClosed(status)) {
      completeCount += 1;
    }
  });
  return {
    totalCount,
    completeCount,
    progress_ratio: totalCount > 0 ? (completeCount / totalCount) : 0,
    percent: executionWavePercent(completeCount, totalCount),
  };
}

function executionWaveWorkstreamProgress(workstreams, options = {}) {
  const rows = Array.isArray(workstreams) ? workstreams : [];
  let totalCount = 0;
  let progressTotal = 0;
  rows.forEach((row) => {
    const ideaId = executionWaveRefIdeaId(row);
    if (!ideaId) return;
    totalCount += 1;
    const explicitProgress = executionWaveResolvedProgress(row, options);
    if (explicitProgress !== null) {
      progressTotal += explicitProgress;
      return;
    }
    const status = executionWaveResolvedStatus(row, options);
    progressTotal += executionWaveStatusIsClosed(status) ? 1 : 0;
  });
  return {
    totalCount,
    progress_ratio: totalCount > 0 ? (progressTotal / totalCount) : 0,
    percent: executionWavePercent(progressTotal, totalCount),
  };
}

function executionWaveWaveCompletion(wave, options = {}) {
  if (!wave || typeof wave !== "object") {
    return { totalCount: 0, completeCount: 0, progress_ratio: 0, percent: "" };
  }
  const gateRefs = Array.isArray(wave.gate_refs) ? wave.gate_refs : [];
  if (gateRefs.length) return executionWaveWorkstreamCompletion(gateRefs, options);
  const allMembers = Array.isArray(wave.all_workstreams) ? wave.all_workstreams : [];
  return executionWaveWorkstreamCompletion(allMembers, options);
}

function executionWaveWaveProgress(wave, options = {}) {
  if (!wave || typeof wave !== "object") {
    return { totalCount: 0, progress_ratio: 0, percent: "" };
  }
  const gateRefs = Array.isArray(wave.gate_refs) ? wave.gate_refs : [];
  if (gateRefs.length) return executionWaveWorkstreamProgress(gateRefs, options);
  const allMembers = Array.isArray(wave.all_workstreams) ? wave.all_workstreams : [];
  return executionWaveWorkstreamProgress(allMembers, options);
}

function executionWaveProgramCompletion(program, options = {}) {
  if (!program || typeof program !== "object") {
    return { totalCount: 0, completeCount: 0, progress_ratio: 0, percent: "" };
  }
  const waves = Array.isArray(program.waves) ? program.waves : [];
  const dedupedMembers = [];
  const seen = new Set();
  waves.forEach((wave) => {
    const gateRefs = Array.isArray(wave && wave.gate_refs) ? wave.gate_refs : [];
    const members = gateRefs.length
      ? gateRefs
      : (Array.isArray(wave && wave.all_workstreams) ? wave.all_workstreams : []);
    members.forEach((member) => {
      const ideaId = executionWaveRefIdeaId(member);
      if (!ideaId || seen.has(ideaId)) return;
      seen.add(ideaId);
      dedupedMembers.push(member);
    });
  });
  return executionWaveWorkstreamCompletion(dedupedMembers, options);
}

function executionWaveProgramProgress(program, options = {}) {
  if (!program || typeof program !== "object") {
    return { totalCount: 0, progress_ratio: 0, percent: "" };
  }
  const waves = Array.isArray(program.waves) ? program.waves : [];
  const dedupedMembers = [];
  const seen = new Set();
  waves.forEach((wave) => {
    const gateRefs = Array.isArray(wave && wave.gate_refs) ? wave.gate_refs : [];
    const members = gateRefs.length
      ? gateRefs
      : (Array.isArray(wave && wave.all_workstreams) ? wave.all_workstreams : []);
    members.forEach((member) => {
      const ideaId = executionWaveRefIdeaId(member);
      if (!ideaId || seen.has(ideaId)) return;
      seen.add(ideaId);
      dedupedMembers.push(member);
    });
  });
  return executionWaveWorkstreamProgress(dedupedMembers, options);
}

function executionWaveSummaryLine(program, options = {}) {
  if (!program || typeof program !== "object") return "";
  const currentWave = program.current_wave && typeof program.current_wave === "object"
    ? String(program.current_wave.label || program.current_wave.wave_id || "").trim()
    : "";
  const active = Array.isArray(program.active_waves)
    ? program.active_waves.map((row) => String(row && row.label ? row.label : "").trim()).filter(Boolean)
    : [];
  const blocked = Array.isArray(program.blocked_waves)
    ? program.blocked_waves.map((row) => String(row && row.label ? row.label : "").trim()).filter(Boolean)
    : [];
  const nextWave = program.next_wave && typeof program.next_wave === "object"
    ? String(program.next_wave.label || "").trim()
    : "";
  const programCompletion = executionWaveProgramCompletion(program, options);
  const parts = [];
  if (currentWave) parts.push(`Current: ${currentWave}`);
  if (active.length) {
    const otherActive = currentWave ? active.filter((label) => label !== currentWave) : active;
    if (!currentWave) parts.push(`Active now: ${active.join(", ")}`);
    else if (otherActive.length) parts.push(`Also active: ${otherActive.join(", ")}`);
  }
  if (nextWave && nextWave !== currentWave) parts.push(`Next: ${nextWave}`);
  if (blocked.length) parts.push(`Blocked: ${blocked.join(", ")}`);
  if (programCompletion.totalCount > 0) parts.push(`Closed gate workstreams: ${programCompletion.completeCount}/${programCompletion.totalCount}`);
  return parts.join(" · ");
}

function renderExecutionWaveMemberChips(members, selectedWorkstreamId, options = {}) {
  const rows = Array.isArray(members) ? members : [];
  const emptyStateClass = String(options.emptyStateClass || "execution-wave-empty").trim() || "execution-wave-empty";
  const renderMemberChip = typeof options.renderMemberChip === "function"
    ? options.renderMemberChip
    : null;
  if (!rows.length) return `<span class="${emptyStateClass}">None</span>`;
  if (!renderMemberChip) return `<span class="${emptyStateClass}">None</span>`;
  return rows
    .map((member) => {
      const ideaId = String(member && member.idea_id ? member.idea_id : "").trim();
      if (!ideaId) return "";
      return renderMemberChip(ideaId, { selected: ideaId === String(selectedWorkstreamId || "").trim() });
    })
    .filter(Boolean)
    .join("");
}

function renderExecutionWaveGateRows(gateRefs, selectedWorkstreamId, options = {}) {
  const rows = Array.isArray(gateRefs) ? gateRefs : [];
  const escapeHtml = typeof options.escapeHtml === "function" ? options.escapeHtml : (value) => String(value || "");
  const emptyStateClass = String(options.emptyStateClass || "execution-wave-empty").trim() || "execution-wave-empty";
  const renderMemberChip = typeof options.renderMemberChip === "function"
    ? options.renderMemberChip
    : null;
  const planHrefForPath = typeof options.planHrefForPath === "function"
    ? options.planHrefForPath
    : () => "";
  if (!rows.length) return `<span class="${emptyStateClass}">No explicit gate refs.</span>`;
  return rows
    .map((gate) => {
      const ideaId = String(gate && gate.workstream_id ? gate.workstream_id : "").trim();
      const label = String(gate && gate.label ? gate.label : "").trim();
      const planPath = String(gate && gate.plan_path ? gate.plan_path : "").trim();
      const planLabel = planPath ? planPath.split("/").pop() : "";
      const planHref = planPath ? String(planHrefForPath(planPath) || "").trim() : "";
      const chips = [];
      if (renderMemberChip && ideaId) {
        chips.push(renderMemberChip(ideaId, { selected: ideaId === String(selectedWorkstreamId || "").trim() }));
      }
      if (planLabel) {
        if (planHref) {
          chips.push(`<a class="label execution-wave-label wave-chip-program execution-wave-plan-link" href="${escapeHtml(planHref)}" target="_top">${escapeHtml(planLabel)}</a>`);
        } else {
          chips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(planLabel)}</span>`);
        }
      }
      return `
        <div class="execution-wave-gate">
          <div class="execution-wave-gate-label">${escapeHtml(label || "Gate reference")}</div>
          ${chips.length ? `<div class="execution-wave-gate-meta">${chips.join("")}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function renderExecutionWaveProgram(program, selectedWorkstreamId, context, options = {}) {
  if (!program || typeof program !== "object") return "";
  const escapeHtml = typeof options.escapeHtml === "function" ? options.escapeHtml : (value) => String(value || "");
  const waves = Array.isArray(program.waves) ? program.waves : [];
  if (!waves.length) return "";
  const showProgramFocusTitle = options.hideProgramFocusTitle !== true;

  const contextMeta = context && typeof context === "object" ? context : null;
  const selectedWorkstream = String(selectedWorkstreamId || "").trim();
  const currentWaveId = program.current_wave && typeof program.current_wave === "object"
    ? String(program.current_wave.wave_id || "").trim()
    : "";
  const selectedBadgeLabel = String(options.selectedBadgeLabel || "Selected").trim() || "Selected";
  const selectedCardClass = String(options.selectedCardClass || "is-member").trim() || "is-member";
  const selectedNoteBuilder = typeof options.selectedNoteText === "function"
    ? options.selectedNoteText
    : () => String(options.selectedNoteText || "").trim();

  const contextChips = [];
  if (contextMeta) {
    const waveSpan = String(contextMeta.wave_span_label || "").trim();
    const roleLabel = String(contextMeta.role_label || "").trim();
    if (waveSpan) contextChips.push(`<span class="label execution-wave-label wave-status-active">${escapeHtml(waveSpan)}</span>`);
    if (roleLabel) contextChips.push(`<span class="label execution-wave-label wave-role-chip">${escapeHtml(roleLabel)}</span>`);
    if (contextMeta.has_next_wave) contextChips.push('<span class="label execution-wave-label wave-status-planned">Next relevant</span>');
  } else {
    const waveCount = Number(program.wave_count || 0);
    if (waveCount > 0) {
      contextChips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${waveCount}-wave program`)}</span>`);
    }
  }

  const cardsHtml = waves.map((wave) => {
    const primaryMembers = Array.isArray(wave.primary_workstreams) ? wave.primary_workstreams : [];
    const carriedMembers = Array.isArray(wave.carried_workstreams) ? wave.carried_workstreams : [];
    const inBandMembers = Array.isArray(wave.in_band_workstreams) ? wave.in_band_workstreams : [];
    const allMembers = Array.isArray(wave.all_workstreams) ? wave.all_workstreams : [];
    const isSelectedMember = allMembers.some((member) => String(member && member.idea_id ? member.idea_id : "").trim() === selectedWorkstream);
    const gateRefs = Array.isArray(wave.gate_refs) ? wave.gate_refs : [];
    const summary = String(wave.summary || "").trim();
    const waveLabel = String(wave.label || wave.wave_id || "").trim();
    const waveStatus = String(wave.status_label || wave.status || "").trim();
    const waveTone = waveStatusChipClass(wave.status);
    const compactSummaryLine = String(wave.compact_summary_line || "").trim();
    const gatePreview = String(wave.gate_preview_summary || "").trim();
    const dependsOnLabels = Array.isArray(wave.depends_on_labels)
      ? wave.depends_on_labels.map((token) => String(token || "").trim()).filter(Boolean)
      : [];
    const isCurrentWave = Boolean(wave.is_current_wave) || (
      currentWaveId && currentWaveId === String(wave.wave_id || "").trim()
    );
    const totalWaveCount = Number(program.wave_count || waves.length || 0);
    const sequenceCount = Number(wave.sequence || 0);
    const sequenceChip = `${sequenceCount} of ${totalWaveCount}`;
    const waveProgress = executionWaveWaveProgress(wave, options);
    const progressChip = waveProgress.percent ? `${waveProgress.percent} progress` : "";
    const openByDefault = Boolean(wave.default_open) || isSelectedMember;
    const openAttr = openByDefault ? " open" : "";
    const selectedNote = isSelectedMember ? String(selectedNoteBuilder(selectedWorkstream, contextMeta) || "").trim() : "";
    const supportBlocks = [];
    if (gatePreview) {
      supportBlocks.push(`
        <div class="execution-wave-highlight">
          <div class="execution-wave-highlight-label">Gate focus</div>
          <div class="execution-wave-highlight-copy">${escapeHtml(gatePreview)}</div>
        </div>
      `);
    }
    if (selectedNote) {
      supportBlocks.push(`
        <div class="execution-wave-highlight">
          <div class="execution-wave-highlight-label">Selected scope</div>
          <div class="execution-wave-highlight-copy execution-wave-highlight-copy-strong">${escapeHtml(selectedNote)}</div>
        </div>
      `);
    }
    const supportPanelHtml = supportBlocks.length
      ? `<div class="execution-wave-panel execution-wave-support-panel">${supportBlocks.join("")}</div>`
      : "";
    const dependsOnHtml = dependsOnLabels.length
      ? dependsOnLabels.map((label) => `<span class="label execution-wave-label wave-status-planned">${escapeHtml(label)}</span>`).join("")
      : '<span class="execution-wave-empty">Starts here</span>';
    const memberPanelsHtml = [
      { label: "Depends On", contentHtml: dependsOnHtml },
      { label: "Primary", contentHtml: renderExecutionWaveMemberChips(primaryMembers, selectedWorkstream, options) },
      { label: "Carried", contentHtml: renderExecutionWaveMemberChips(carriedMembers, selectedWorkstream, options) },
      { label: "In Band", contentHtml: renderExecutionWaveMemberChips(inBandMembers, selectedWorkstream, options) },
    ]
      .map(({ label, contentHtml }) => `
        <div class="execution-wave-panel">
          <div class="execution-wave-group-label">${escapeHtml(label)}</div>
          <div class="execution-wave-group-body">${contentHtml}</div>
        </div>
      `)
      .join("");
    const cardClassNames = ["execution-wave-card", escapeHtml(waveTone)];
    if (isSelectedMember) cardClassNames.push(escapeHtml(selectedCardClass));
    if (isCurrentWave) cardClassNames.push("is-current-wave");
    return `
      <details class="${cardClassNames.join(" ")}"${openAttr}>
        <summary class="execution-wave-card-summary">
          <div class="execution-wave-card-shell">
            <div class="execution-wave-card-copy">
              <div class="execution-wave-title-row">
                <div class="execution-wave-title">${escapeHtml(waveLabel)}</div>
                <span class="label execution-wave-label wave-chip-program">${escapeHtml(sequenceChip)}</span>
                ${progressChip ? `<span class="label execution-wave-label wave-progress-chip">${escapeHtml(progressChip)}</span>` : ""}
              </div>
              <div class="execution-wave-sub">${escapeHtml(summary || "No wave summary recorded.")}</div>
              ${compactSummaryLine ? `<div class="execution-wave-compact"><div class="execution-wave-compact-line execution-wave-compact-line-strong">${escapeHtml(compactSummaryLine)}</div></div>` : ""}
            </div>
            <div class="execution-wave-card-meta">
              <div class="execution-wave-card-stat-rail">
                ${isCurrentWave ? '<span class="label execution-wave-label wave-current-chip">Current wave</span>' : ""}
                <span class="label execution-wave-label ${escapeHtml(waveTone)}">${escapeHtml(waveStatus)}</span>
                <span class="label execution-wave-label wave-program-chip">${escapeHtml(`${Number(wave.member_count || 0)} member${Number(wave.member_count || 0) === 1 ? "" : "s"}`)}</span>
                ${gateRefs.length ? `<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${gateRefs.length} gate${gateRefs.length === 1 ? "" : "s"}`)}</span>` : ""}
                ${isSelectedMember ? `<span class="label execution-wave-label wave-role-chip">${escapeHtml(selectedBadgeLabel)}</span>` : ""}
              </div>
            </div>
          </div>
        </summary>
        <div class="execution-wave-card-body">
          ${supportPanelHtml ? `<div class="execution-wave-body-grid execution-wave-body-grid-top">${supportPanelHtml}</div>` : ""}
          <div class="execution-wave-body-grid execution-wave-body-grid-members">
            ${memberPanelsHtml}
          </div>
          ${gateRefs.length ? `<div class="execution-wave-panel"><div class="execution-wave-group-label">Gate Checks</div><div class="execution-wave-gates">${renderExecutionWaveGateRows(gateRefs, selectedWorkstream, options)}</div></div>` : ""}
        </div>
      </details>
    `;
  }).join("");

  const summaryLine = executionWaveSummaryLine(program, options);
  const umbrellaTitle = String(program.umbrella_title || "").trim();
  const umbrellaId = String(program.umbrella_id || "").trim();
  const programLabel = umbrellaTitle && umbrellaId
    ? `${umbrellaTitle} (${umbrellaId})`
    : (umbrellaTitle || umbrellaId);
  const contextLine = contextMeta
    ? `This workstream participates across ${String(contextMeta.wave_span_label || "").trim() || "the program"} as ${String(contextMeta.role_label || "").trim() || "a member"}.`
    : "Umbrella-owned execution waves for this program.";

  return `
    <div class="execution-wave-board">
      <div class="execution-wave-focus">
        <div class="execution-wave-focus-grid">
          <div class="execution-wave-focus-copy">
            ${showProgramFocusTitle ? `<div class="execution-wave-focus-title">${escapeHtml(programLabel)}</div>` : ""}
            <div class="execution-wave-focus-line">${escapeHtml(contextLine)}</div>
            ${summaryLine ? `<div class="execution-wave-focus-line execution-wave-focus-line-muted">${escapeHtml(summaryLine)}</div>` : ""}
          </div>
          <div class="execution-wave-focus-stat-rail">${contextChips.join("")}</div>
        </div>
      </div>
      <div class="execution-wave-sequence">${cardsHtml}</div>
    </div>
  `;
}

function renderExecutionWaveSection(sectionModel, options = {}) {
  const section = sectionModel && typeof sectionModel === "object" ? sectionModel : {};
  const entries = Array.isArray(section.entries) ? section.entries : [];
  if (!entries.length) return "";
  const escapeHtml = typeof options.escapeHtml === "function" ? options.escapeHtml : (value) => String(value || "");
  const sectionTitle = String(section.title || "Execution Waves").trim() || "Execution Waves";
  const programLabel = String(section.programLabel || "").trim();
  const contextLine = String(section.contextLine || "").trim();
  const summaryLine = String(section.summaryLine || "").trim();
  const selectedWorkstreamId = String(section.selectedWorkstreamId || "").trim();
  const sectionChips = Array.isArray(section.sectionChips)
    ? section.sectionChips.filter((row) => String(row || "").trim())
    : [];
  const boardWrapperClass = String(options.boardWrapperClass || "").trim();
  const boardsHtml = entries
    .map((entry) => renderExecutionWaveProgram(
      entry && entry.program ? entry.program : null,
      selectedWorkstreamId,
      entry && entry.context ? entry.context : null,
      options,
    ))
    .filter(Boolean)
    .map((boardHtml) => (
      boardWrapperClass
        ? `<div class="${escapeHtml(boardWrapperClass)}">${boardHtml}</div>`
        : boardHtml
    ))
    .join("");
  if (!boardsHtml) return "";
  const openAttr = section.openByDefault ? " open" : "";
  const sectionHeaderVariant = String(options.sectionHeaderVariant || "").trim().toLowerCase();
  if (sectionHeaderVariant === "compass") {
    return `
      <section class="block">
        <details class="execution-wave-section"${openAttr}>
          <summary class="execution-wave-section-summary execution-wave-section-summary-compass">
            <div class="execution-wave-section-copy">
              <div class="execution-wave-section-title">${escapeHtml(sectionTitle)}</div>
              ${programLabel ? `<div class="execution-wave-section-line">${escapeHtml(programLabel)}</div>` : ""}
              ${contextLine ? `<div class="execution-wave-section-line">${escapeHtml(contextLine)}</div>` : ""}
              ${summaryLine ? `<div class="execution-wave-section-line execution-wave-section-line-muted">${escapeHtml(summaryLine)}</div>` : ""}
            </div>
            <span class="execution-wave-section-toggle execution-wave-section-toggle-triangle" aria-hidden="true"></span>
            ${sectionChips.length ? `<div class="execution-wave-section-meta execution-wave-section-meta-bottom">${sectionChips.join("")}</div>` : ""}
          </summary>
          <div class="execution-wave-section-body">${boardsHtml}</div>
        </details>
      </section>
    `;
  }
  return `
    <section class="block">
      <details class="execution-wave-section"${openAttr}>
        <summary class="execution-wave-section-summary">
          <div class="execution-wave-section-copy">
            <div class="execution-wave-section-title">${escapeHtml(sectionTitle)}</div>
            ${programLabel ? `<div class="execution-wave-section-line">${escapeHtml(programLabel)}</div>` : ""}
            ${contextLine ? `<div class="execution-wave-section-line">${escapeHtml(contextLine)}</div>` : ""}
            ${summaryLine ? `<div class="execution-wave-section-line execution-wave-section-line-muted">${escapeHtml(summaryLine)}</div>` : ""}
          </div>
          <div class="execution-wave-section-meta">
            ${sectionChips.join("")}
            <span class="execution-wave-section-toggle execution-wave-section-toggle-triangle" aria-hidden="true"></span>
          </div>
        </summary>
        <div class="execution-wave-section-body">${boardsHtml}</div>
      </details>
    </section>
  `;
}

    function executionWaveRoleChips(row) {
      const trace = workstreamTrace(row.idea_id) || {};
      const workstreamType = String(trace.workstream_type || row.workstream_type || "").trim().toLowerCase();
      const directProgram = workstreamType === "umbrella" ? executionWaveProgramByUmbrella(row.idea_id) : null;
      if (directProgram) {
        const waveCount = Number(directProgram.wave_count || 0);
        const activeCount = Number(directProgram.active_wave_count || 0);
        const nextWave = directProgram.next_wave && typeof directProgram.next_wave === "object"
          ? String(directProgram.next_wave.wave_id || directProgram.next_wave.label || "").trim()
          : "";
        return [
          waveCount > 0 ? `<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${waveCount}-wave program`)}</span>` : "",
          activeCount > 0 ? `<span class="label execution-wave-label wave-status-active">${escapeHtml(`${activeCount} active`)}</span>` : "",
          nextWave ? `<span class="label execution-wave-label wave-status-planned">${escapeHtml(`Next ${nextWave}`)}</span>` : "",
        ].filter(Boolean).join("");
      }

      const programContexts = workstreamWavePrograms(row.idea_id);
      if (!programContexts.length) return "";
      const primary = programContexts[0];
      const activeClass = primary.has_active_wave ? "wave-status-active" : (primary.has_next_wave ? "wave-status-planned" : "wave-status-other");
      const waveLabel = String(primary.wave_span_label || "").trim();
      const roleLabel = String(primary.role_label || "").trim();
      const umbrellaId = String(primary.umbrella_id || "").trim();
      return [
        waveLabel ? `<span class="label execution-wave-label ${escapeHtml(activeClass)}">${escapeHtml(waveLabel)}</span>` : "",
        roleLabel ? `<span class="label execution-wave-label wave-role-chip">${escapeHtml(roleLabel)}</span>` : "",
        umbrellaId ? `<span class="label execution-wave-label wave-program-chip">${escapeHtml(umbrellaId)}</span>` : "",
      ].filter(Boolean).join("");
    }

    function workstreamTypeInfo(row) {
      const trace = workstreamTrace(row.idea_id) || {};
      const rawType = String(trace.workstream_type || row.workstream_type || "").trim().toLowerCase();
      const parent = String(trace.workstream_parent || row.workstream_parent || "").trim();
      if (rawType === "umbrella") {
        return { type: "umbrella", label: "Umbrella", parent: "" };
      }
      if (rawType === "child") {
        return { type: "child", label: "Child", parent };
      }
      return { type: "standalone", label: "", parent: "" };
    }

    function compactWorkstreamId(token) {
      const raw = String(token || "").trim();
      const matched = raw.match(/^B-(\d+)$/);
      if (matched) {
        return `B${matched[1]}`;
      }
      return raw;
    }

    function warningItems() {
      const payload = traceabilityPayload();
      const rich = Array.isArray(payload.warning_items) ? payload.warning_items : [];
      if (rich.length) {
        return rich.map((entry) => ({
          idea_id: String(entry.idea_id || "").trim(),
          severity: String(entry.severity || "warning").trim() || "warning",
          category: String(entry.category || "general").trim() || "general",
          message: String(entry.message || "").trim(),
          action: String(entry.action || "").trim(),
          source: String(entry.source || "").trim(),
        })).filter((entry) => entry.message);
      }
      const legacy = Array.isArray(payload.warnings) ? payload.warnings : [];
      return legacy
        .map((message) => String(message || "").trim())
        .filter(Boolean)
        .map((message) => ({
          idea_id: "",
          severity: "warning",
          category: "legacy",
          message,
          action: "Inspect traceability graph diagnostics and corresponding source files.",
          source: "",
        }));
    }

    function warningItemsForIdea(ideaId) {
      const rows = warningItems();
      return rows.filter((entry) => String(entry.idea_id || "") === String(ideaId || ""));
    }

    function workstreamLinkChip(ideaId, tone = "") {
      const token = String(ideaId || "").trim();
      if (!token) return "";
      const tooltip = workstreamTooltip(token);
      return `<button type="button" class="chip chip-link ${escapeHtml(tone)}" data-link-idea="${escapeHtml(token)}" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}">${escapeHtml(token)}</button>`;
    }

    function renderWorkstreamLinkSet(items, tone = "") {
      const values = normalizeIdList(items);
      if (!values.length) return `<span class="chip">None</span>`;
      return values.map((token) => workstreamLinkChip(token, tone)).join("");
    }

    function renderDiagramLinkSet(items, selectedIdeaId) {
      const values = normalizeDiagramIdList(items);
      if (!values.length) return "";
      return values
        .map((diagramId) => {
          const href = atlasDiagramHref(diagramId, selectedIdeaId);
          const tooltip = diagramTooltip(diagramId);
          return `<a class="chip chip-link chip-topology-diagram" href="${escapeHtml(href)}" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}" target="_top">${escapeHtml(diagramId)}</a>`;
        })
        .join("");
    }

    function compassScopeHref(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) {
        return "../../odylith/index.html?tab=compass";
      }
      return `../../odylith/index.html?tab=compass&workstream=${encodeURIComponent(token)}&date=live`;
    }

    function registryComponentsForRow(row) {
      const values = Array.isArray(row && row.registry_components) ? row.registry_components : [];
      const deduped = [];
      const seen = new Set();
      values.forEach((item) => {
        const componentId = String(item && item.component_id ? item.component_id : "").trim().toLowerCase();
        if (!componentId || seen.has(componentId)) return;
        seen.add(componentId);
        const name = String(item && item.name ? item.name : componentId).trim() || componentId;
        deduped.push({ component_id: componentId, name });
      });
      return deduped;
    }

    function registryHrefForRow(row) {
      const components = registryComponentsForRow(row);
      if (!components.length) {
        return "../../odylith/index.html?tab=registry";
      }
      return `../../odylith/index.html?tab=registry&component=${encodeURIComponent(components[0].component_id)}`;
    }

    function registryComponentHref(component) {
      const componentId = String(component && component.component_id || "").trim().toLowerCase();
      if (!componentId) {
        return "../../odylith/index.html?tab=registry";
      }
      return `../../odylith/index.html?tab=registry&component=${encodeURIComponent(componentId)}`;
    }

    function renderRegistryComponentLinkSet(row) {
      const components = registryComponentsForRow(row);
      if (!components.length) return "";
      return components
        .map((component) => {
          const componentId = String(component && component.component_id || "").trim().toLowerCase();
          const label = String(component && component.name || componentId || "Component").trim() || "Component";
          const tooltip = componentTooltip(componentId, `${label} (${componentId})`);
          return `<a class="chip chip-link chip-registry-component" href="${escapeHtml(registryComponentHref(component))}" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}" target="_top">${escapeHtml(label)}</a>`;
        })
        .join("");
    }

    function topologyRelationRow({ title, count, bodyHtml }) {
      const body = String(bodyHtml || "").trim()
        || `<span class="topology-rel-empty">None</span>`;
      return `
        <div class="topology-rel-row">
          <span class="topology-rel-title">${escapeHtml(title)}</span>
          <span class="topology-rel-count">${escapeHtml(String(count))}</span>
          <div class="topology-rel-body">${body}</div>
        </div>
      `;
    }

    function renderTopologyBoard(
      selectedIdeaId,
      parents,
      children,
      dependsOn,
      blocks,
      diagrams,
      reopens,
      reopenedBy,
      splitFrom,
      splitInto,
      mergedInto,
      mergedFrom
    ) {
      const parentValues = normalizeIdList(parents);
      const childrenValues = normalizeIdList(children);
      const dependsValues = normalizeIdList(dependsOn);
      const blocksValues = normalizeIdList(blocks);
      const diagramValues = normalizeDiagramIdList(diagrams);
      const reopensValues = normalizeIdList(reopens);
      const reopenedByValues = normalizeIdList(reopenedBy);
      const splitFromValues = normalizeIdList(splitFrom);
      const splitIntoValues = normalizeIdList(splitInto);
      const mergedIntoValues = normalizeIdList(mergedInto);
      const mergedFromValues = normalizeIdList(mergedFrom);
      const totalLinks =
        parentValues.length
        + childrenValues.length
        + dependsValues.length
        + blocksValues.length
        + diagramValues.length
        + reopensValues.length
        + reopenedByValues.length
        + splitFromValues.length
        + splitIntoValues.length
        + mergedIntoValues.length
        + mergedFromValues.length;

      const relationItems = [
        {
          title: "Parent",
          count: parentValues.length,
          bodyHtml: renderWorkstreamLinkSet(parentValues, "chip-topology-parent"),
        },
        {
          title: "Children",
          count: childrenValues.length,
          bodyHtml: renderWorkstreamLinkSet(childrenValues, "chip-topology-parent"),
        },
        {
          title: "Depends On",
          count: dependsValues.length,
          bodyHtml: renderWorkstreamLinkSet(dependsValues, "chip-topology-depends"),
        },
        {
          title: "Blocks",
          count: blocksValues.length,
          bodyHtml: renderWorkstreamLinkSet(blocksValues, "chip-topology-blocks"),
        },
        {
          title: "Related Diagrams",
          count: diagramValues.length,
          bodyHtml: renderDiagramLinkSet(diagramValues, selectedIdeaId) || `<span class="topology-rel-empty">None</span>`,
        },
        {
          title: "Reopens",
          count: reopensValues.length,
          bodyHtml: renderWorkstreamLinkSet(reopensValues, "chip-topology-parent"),
        },
        {
          title: "Reopened By",
          count: reopenedByValues.length,
          bodyHtml: renderWorkstreamLinkSet(reopenedByValues, "chip-topology-parent"),
        },
        {
          title: "Split From",
          count: splitFromValues.length,
          bodyHtml: renderWorkstreamLinkSet(splitFromValues, "chip-topology-depends"),
        },
        {
          title: "Split Into",
          count: splitIntoValues.length,
          bodyHtml: renderWorkstreamLinkSet(splitIntoValues, "chip-topology-depends"),
        },
        {
          title: "Merged Into",
          count: mergedIntoValues.length,
          bodyHtml: renderWorkstreamLinkSet(mergedIntoValues, "chip-topology-blocks"),
        },
        {
          title: "Merged From",
          count: mergedFromValues.length,
          bodyHtml: renderWorkstreamLinkSet(mergedFromValues, "chip-topology-blocks"),
        },
      ];
      const visibleRelationItems = relationItems.filter((item) => Number(item.count || 0) > 0);
      const relationRows = visibleRelationItems.map((item) => topologyRelationRow(item)).join("");
      const linkedRelationTypes = [
        parentValues,
        childrenValues,
        dependsValues,
        blocksValues,
        diagramValues,
        reopensValues,
        reopenedByValues,
        splitFromValues,
        splitIntoValues,
        mergedIntoValues,
        mergedFromValues,
      ].filter((values) => Array.isArray(values) && values.length > 0).length;

      return `
        <div class="topology-board">
          <div class="topology-focus">
            <span class="topology-focus-title">Selected</span>
            ${workstreamLinkChip(selectedIdeaId, "chip-topology-source")}
          </div>
          ${visibleRelationItems.length ? `
            <details class="topology-relations-panel">
              <summary>
                <span class="topology-relations-toggle">Relations</span>
                <span class="topology-relations-summary">${escapeHtml(String(linkedRelationTypes))} linked types · ${escapeHtml(String(totalLinks))} links</span>
              </summary>
              <div class="topology-relations">
                ${relationRows}
              </div>
            </details>
          ` : `<div class="topology-relations-empty">No linked relationships.</div>`}
        </div>
      `;
    }

    function resolveTopologyForIdea(ideaId, fallback = {}) {
      const token = String(ideaId || "").trim();
      const fallbackParents = normalizeIdList(fallback.parents);
      const fallbackChildren = normalizeIdList(fallback.children);
      const fallbackDepends = normalizeIdList(fallback.depends_on);
      const fallbackBlocks = normalizeIdList(fallback.blocks);
      const fallbackReopens = normalizeIdList(fallback.reopens);
      const fallbackReopenedBy = normalizeIdList(fallback.reopened_by);
      const fallbackSplitFrom = normalizeIdList(fallback.split_from);
      const fallbackSplitInto = normalizeIdList(fallback.split_into);
      const fallbackMergedInto = normalizeIdList(fallback.merged_into);
      const fallbackMergedFrom = normalizeIdList(fallback.merged_from);
      if (!token) {
        return {
          parents: fallbackParents,
          children: fallbackChildren,
          depends_on: fallbackDepends,
          blocks: fallbackBlocks,
          reopens: fallbackReopens,
          reopened_by: fallbackReopenedBy,
          split_from: fallbackSplitFrom,
          split_into: fallbackSplitInto,
          merged_into: fallbackMergedInto,
          merged_from: fallbackMergedFrom,
        };
      }

      const payload = traceabilityPayload();
      const edges = Array.isArray(payload.edges) ? payload.edges : [];
      const parentSet = new Set();
      const childSet = new Set();
      const dependsSet = new Set();
      const blocksSet = new Set();
      const reopensSet = new Set();
      const reopenedBySet = new Set();
      const splitFromSet = new Set();
      const splitIntoSet = new Set();
      const mergedIntoSet = new Set();
      const mergedFromSet = new Set();
      edges.forEach((edge) => {
        const source = String(edge.source || "").trim();
        const target = String(edge.target || "").trim();
        const kind = String(edge.edge_type || "").trim();
        if (!source || !target) return;
        if (kind === "parent_child") {
          if (source === token) childSet.add(target);
          if (target === token) parentSet.add(source);
          return;
        }
        if (kind === "depends_on" && target === token) {
          dependsSet.add(source);
          return;
        }
        if (kind === "blocks" && source === token) {
          blocksSet.add(target);
          return;
        }
        if (kind === "reopens") {
          if (source === token) reopensSet.add(target);
          if (target === token) reopenedBySet.add(source);
          return;
        }
        if (kind === "split") {
          if (source === token) splitIntoSet.add(target);
          if (target === token) splitFromSet.add(source);
          return;
        }
        if (kind === "merge") {
          if (source === token) mergedIntoSet.add(target);
          if (target === token) mergedFromSet.add(source);
        }
      });

      const edgeParents = [...parentSet].sort();
      const edgeChildren = [...childSet].sort();
      const edgeDepends = [...dependsSet].sort();
      const edgeBlocks = [...blocksSet].sort();
      const edgeReopens = [...reopensSet].sort();
      const edgeReopenedBy = [...reopenedBySet].sort();
      const edgeSplitFrom = [...splitFromSet].sort();
      const edgeSplitInto = [...splitIntoSet].sort();
      const edgeMergedInto = [...mergedIntoSet].sort();
      const edgeMergedFrom = [...mergedFromSet].sort();

      return {
        parents: edgeParents.length ? edgeParents : fallbackParents,
        children: edgeChildren.length ? edgeChildren : fallbackChildren,
        depends_on: edgeDepends.length ? edgeDepends : fallbackDepends,
        blocks: edgeBlocks.length ? edgeBlocks : fallbackBlocks,
        reopens: edgeReopens.length ? edgeReopens : fallbackReopens,
        reopened_by: edgeReopenedBy.length ? edgeReopenedBy : fallbackReopenedBy,
        split_from: edgeSplitFrom.length ? edgeSplitFrom : fallbackSplitFrom,
        split_into: edgeSplitInto.length ? edgeSplitInto : fallbackSplitInto,
        merged_into: edgeMergedInto.length ? edgeMergedInto : fallbackMergedInto,
        merged_from: edgeMergedFrom.length ? edgeMergedFrom : fallbackMergedFrom,
      };
    }

    function renderExecutionWaveMemberChip(ideaId, options = {}) {
      const token = String(ideaId || "").trim();
      if (!token) return "";
      const tooltip = workstreamTooltip(token);
      const tone = options && options.selected ? " wave-member-selected" : "";
      return `<button type="button" class="chip chip-link execution-wave-chip-link${tone}" data-link-idea="${escapeHtml(token)}" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}">${escapeHtml(token)}</button>`;
    }

    function renderExecutionWaveDetailSection(selected) {
      const directProgram = executionWaveProgramByUmbrella(selected.idea_id);
      const entries = [];
      if (directProgram) {
        entries.push({ program: directProgram, context: null });
      } else {
        const contexts = workstreamWavePrograms(selected.idea_id);
        contexts.forEach((context) => {
          const program = executionWaveProgramByUmbrella(context.umbrella_id);
          if (program) entries.push({ program, context });
        });
      }
      if (!entries.length) return "";

      const primaryEntry = entries[0] || {};
      const primaryProgram = primaryEntry.program && typeof primaryEntry.program === "object" ? primaryEntry.program : {};
      const primaryContext = primaryEntry.context && typeof primaryEntry.context === "object" ? primaryEntry.context : null;
      const programCount = entries.length;
      const activeWaveCount = entries.reduce((count, entry) => count + Number(entry && entry.program && entry.program.active_wave_count ? entry.program.active_wave_count : 0), 0);
      const waveCount = entries.reduce((count, entry) => count + Number(entry && entry.program && entry.program.wave_count ? entry.program.wave_count : 0), 0);
      const programLabel = `${String(primaryProgram.umbrella_title || primaryProgram.umbrella_id || "").trim()} (${String(primaryProgram.umbrella_id || "").trim()})`;
      const contextLine = primaryContext
        ? `This workstream participates across ${String(primaryContext.wave_span_label || "").trim() || "the program"} as ${String(primaryContext.role_label || "").trim() || "a member"}.`
        : "Umbrella-owned execution waves for this program.";
      const workstreamStatusById = new Map(
        (Array.isArray(DATA.entries) ? DATA.entries : [])
          .map((row) => {
            const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
            const status = String(row && row.status ? row.status : "").trim().toLowerCase();
            return [ideaId, status || ""];
          })
          .filter(([ideaId]) => ideaId)
      );
      const workstreamProgressById = new Map(
        (Array.isArray(DATA.entries) ? DATA.entries : [])
          .map((row) => {
            const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
            const plan = row && typeof row.plan === "object" ? row.plan : {};
            const progressRatio = Number(plan && plan.progress_ratio);
            return [ideaId, Number.isFinite(progressRatio) ? progressRatio : null];
          })
          .filter(([ideaId]) => ideaId)
      );
      const resolveWorkstreamStatus = (member) => {
        const ideaId = String(member && (member.idea_id || member.workstream_id) ? (member.idea_id || member.workstream_id) : "").trim();
        if (!ideaId || !workstreamStatusById.has(ideaId)) return "";
        return workstreamStatusById.get(ideaId);
      };
      const resolveWorkstreamProgress = (member) => {
        const ideaId = String(member && (member.idea_id || member.workstream_id) ? (member.idea_id || member.workstream_id) : "").trim();
        if (!ideaId || !workstreamProgressById.has(ideaId)) return null;
        return workstreamProgressById.get(ideaId);
      };
      const summaryLine = programCount === 1
        ? executionWaveSummaryLine(primaryProgram, { resolveWorkstreamStatus })
        : `${programCount} programs · ${activeWaveCount} active waves · ${waveCount} total waves`;
      const sectionChips = [];
      if (programCount > 1) {
        sectionChips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${programCount} programs`)}</span>`);
      } else if (Number(primaryProgram.wave_count || 0) > 0) {
        sectionChips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${Number(primaryProgram.wave_count || 0)}-wave program`)}</span>`);
        const programProgress = executionWaveProgramProgress(primaryProgram, { resolveWorkstreamStatus, resolveWorkstreamProgress });
        if (programProgress.percent) {
          sectionChips.push(`<span class="label execution-wave-label wave-progress-chip">${escapeHtml(`Overall ${programProgress.percent} progress`)}</span>`);
        }
      }
      if (activeWaveCount > 0) {
        sectionChips.push(`<span class="label execution-wave-label wave-status-active">${escapeHtml(`${activeWaveCount} active`)}</span>`);
      }
      if (primaryContext) {
        const waveSpan = String(primaryContext.wave_span_label || "").trim();
        const roleLabel = String(primaryContext.role_label || "").trim();
        if (waveSpan) sectionChips.push(`<span class="label execution-wave-label wave-status-planned">${escapeHtml(waveSpan)}</span>`);
        if (roleLabel) sectionChips.push(`<span class="label execution-wave-label wave-role-chip">${escapeHtml(roleLabel)}</span>`);
      }

      return renderExecutionWaveSection(
        {
          title: "Execution Waves",
          entries,
          selectedWorkstreamId: selected.idea_id,
          programLabel,
          contextLine,
          summaryLine,
          sectionChips,
        },
        {
          escapeHtml,
          emptyStateClass: "execution-wave-empty",
          renderMemberChip: renderExecutionWaveMemberChip,
          resolveWorkstreamStatus,
          resolveWorkstreamProgress,
          selectedBadgeLabel: "Selected",
          selectedCardClass: "is-member",
        },
      );
    }

    async function renderDetail(rows) {
      const selectedSummary = rows.find((row) => row.idea_id === state.selectedIdeaId);
      if (!selectedSummary) {
        el.detail.hidden = true;
        el.detailEmpty.hidden = true;
        el.detail.innerHTML = "";
        return;
      }
      el.detail.hidden = false;
      el.detailEmpty.hidden = true;
      el.detail.innerHTML = "";
      const loadedDetail = await backlogDataSource.loadDetail(selectedSummary.idea_id);
      if (String(state.selectedIdeaId || "").trim() !== String(selectedSummary.idea_id || "").trim()) {
        return;
      }
      const selected = loadedDetail && typeof loadedDetail === "object"
        ? { ...selectedSummary, ...loadedDetail }
        : selectedSummary;

      const rankLabel = selected.section === "execution"
        ? "Pipeline"
        : (selected.section === "finished" ? "Finished" : (selected.section === "parked" ? "Parked" : `Rank #${selected.rank}`));
      const rankChipClass = selected.section === "execution"
        ? "rank-chip-execution"
        : (selected.section === "finished" ? "rank-chip-finished" : (selected.section === "parked" ? "rank-chip-parked" : "rank-chip-active"));
      const rankingClass = selected.founder_override === "yes" ? "founder-override" : "score-ordered";
      const rankingText = selected.founder_override === "yes" ? "Priority Override" : "Score Ordered";
      const scoreWidth = Math.max(3, Math.min(100, selected.ordering_score));
      const statusClass = statusChipClass(selected.status);
      const stageDisplay = executionStageLabel(selected.status);
      const executionState = String(selected.execution_state || "").trim().toLowerCase();
      const executionMeta = selected.execution_state_meta && typeof selected.execution_state_meta === "object"
        ? selected.execution_state_meta
        : {};
      const activeWindowMinutes = executionActiveWindowMinutes(executionMeta);
      const executionSignalAt = String(executionMeta.source_ts_iso || "").trim();
      const executionSignalLabel = formatCompactTimestamp(executionSignalAt);
      const executionSignalChip = selected.section === "execution"
        ? `<span class="chip execution-chip ${escapeHtml(executionStateClass(executionState))}" data-tooltip="${escapeHtml(executionSignalTooltip(selected.status, executionState, activeWindowMinutes))}">${escapeHtml(executionStateLabel(executionState))}</span>`
        : "";
      const trace = workstreamTrace(selected.idea_id) || {};
      const fallbackTopology = {
        parents: trace.workstream_parent || selected.workstream_parent || "",
        children: Array.isArray(trace.workstream_children) ? trace.workstream_children : (Array.isArray(selected.workstream_children) ? selected.workstream_children : []),
        depends_on: Array.isArray(trace.workstream_depends_on) ? trace.workstream_depends_on : (Array.isArray(selected.workstream_depends_on) ? selected.workstream_depends_on : []),
        blocks: Array.isArray(trace.workstream_blocks) ? trace.workstream_blocks : (Array.isArray(selected.workstream_blocks) ? selected.workstream_blocks : []),
        reopens: trace.workstream_reopens || (Array.isArray(selected.workstream_reopens) ? selected.workstream_reopens : []),
        reopened_by: trace.workstream_reopened_by || (Array.isArray(selected.workstream_reopened_by) ? selected.workstream_reopened_by : []),
        split_from: trace.workstream_split_from || (Array.isArray(selected.workstream_split_from) ? selected.workstream_split_from : []),
        split_into: Array.isArray(trace.workstream_split_into) ? trace.workstream_split_into : (Array.isArray(selected.workstream_split_into) ? selected.workstream_split_into : []),
        merged_into: trace.workstream_merged_into || (Array.isArray(selected.workstream_merged_into) ? selected.workstream_merged_into : []),
        merged_from: Array.isArray(trace.workstream_merged_from) ? trace.workstream_merged_from : (Array.isArray(selected.workstream_merged_from) ? selected.workstream_merged_from : []),
      };
      const resolvedTopology = resolveTopologyForIdea(selected.idea_id, fallbackTopology);
      const parents = normalizeIdList(resolvedTopology.parents);
      const children = normalizeIdList(resolvedTopology.children);
      const dependsOn = normalizeIdList(resolvedTopology.depends_on);
      const blocks = normalizeIdList(resolvedTopology.blocks);
      const reopens = normalizeIdList(resolvedTopology.reopens);
      const reopenedBy = normalizeIdList(resolvedTopology.reopened_by);
      const splitFrom = normalizeIdList(resolvedTopology.split_from);
      const splitInto = normalizeIdList(resolvedTopology.split_into);
      const mergedInto = normalizeIdList(resolvedTopology.merged_into);
      const mergedFrom = normalizeIdList(resolvedTopology.merged_from);
      const diagrams = Array.isArray(trace.related_diagram_ids) ? trace.related_diagram_ids : (Array.isArray(selected.related_diagram_ids) ? selected.related_diagram_ids : []);
      const scopedWarnings = warningItemsForIdea(selected.idea_id);
      const graphWarnings = scopedWarnings;
      const warningsSectionHtml = graphWarnings.length
        ? `
        <section class="block">
          <h3>Warnings</h3>
          <p><strong>Warnings scoped to this workstream:</strong></p>
          <ul class="warning-list">${
            graphWarnings.slice(0, 8).map((item) => {
              const category = String(item.category || "general").trim();
              const severity = String(item.severity || "warning").trim();
              const message = String(item.message || "").trim();
              const action = String(item.action || "").trim();
              const source = String(item.source || "").trim();
              const metaBits = [
                category ? `category: ${category}` : "",
                severity ? `severity: ${severity}` : "",
                source ? `source: ${source}` : "",
              ].filter(Boolean);
              return `
                <li class="warning-item">
                  <p class="warning-title">${escapeHtml(message || "Warning")}</p>
                  ${action ? `<p class="warning-action"><strong>Action:</strong> ${escapeHtml(action)}</p>` : ""}
                  ${metaBits.length ? `<p class="warning-meta">${escapeHtml(metaBits.join(" · "))}</p>` : ""}
                </li>
              `;
            }).join("")
          }</ul>
        </section>
      `
        : "";

      const topologyBoardHtml = renderTopologyBoard(
        selected.idea_id,
        parents,
        children,
        dependsOn,
        blocks,
        diagrams,
        reopens,
        reopenedBy,
        splitFrom,
        splitInto,
        mergedInto,
        mergedFrom,
      );
      const registryComponents = registryComponentsForRow(selected);
      const registryComponentLinksHtml = renderRegistryComponentLinkSet(selected);
      const executionWaveSectionHtml = renderExecutionWaveDetailSection(selected);
      const implementedSummary = String(selected.implemented_summary || "").trim();
      const implementedSummaryHtml = implementedSummary
        ? `
        <section class="block">
          <h3>Implemented Summary</h3>
          ${summarySectionHtml(implementedSummary, "Not captured in the idea spec yet.")}
        </section>
      `
        : "";
      el.detail.innerHTML = `
        <header class="detail-header">
          <span class="rank-chip ${escapeHtml(rankChipClass)}">${escapeHtml(rankLabel)}</span>
          <h2 class="detail-title">${escapeHtml(selected.title)}</h2>
          <p class="detail-id">${escapeHtml(selected.idea_id)}</p>
          <div class="chips">
            <span class="chip chip-priority">${escapeHtml(selected.priority)}</span>
            <span class="chip ${statusClass}">${escapeHtml(stageDisplay)}</span>
            ${executionSignalChip}
            <span class="chip chip-lane">${escapeHtml(laneLabel(selected.impacted_lanes))}</span>
            <span class="chip chip-sizing">${escapeHtml(selected.sizing)} / ${escapeHtml(selected.complexity)}</span>
            <span class="chip ${rankingClass}">${rankingText}</span>
          </div>
          <div class="kpis">
            <div class="kpi"><div class="k">Ordering Score</div><div class="v">${escapeHtml(selected.ordering_score)}</div></div>
            <div class="kpi"><div class="k">Created Date</div><div class="v">${escapeHtml(selected.idea_date_display || selected.idea_date || "-")}</div></div>
            <div class="kpi"><div class="k">Age (days)</div><div class="v">${escapeHtml(selected.idea_age_days || "-")}</div></div>
            <div class="kpi"><div class="k">Execution Start</div><div class="v">${escapeHtml(selected.execution_start_date_display || selected.execution_start_date || "-")}</div></div>
            <div class="kpi"><div class="k">Execution End</div><div class="v">${escapeHtml(selected.execution_end_date_display || selected.execution_end_date || "-")}</div></div>
            <div class="kpi"><div class="k">Execution Days</div><div class="v">${escapeHtml(selected.execution_duration_days || selected.execution_age_days || "-")}</div></div>
            <div class="kpi"><div class="k">Live Signal At</div><div class="v v-compact" title="${escapeHtml(executionSignalAt || "-")}">${escapeHtml(executionSignalLabel)}</div></div>
            <div class="kpi"><div class="k">Confidence</div><div class="v">${escapeHtml(selected.confidence || "-")}</div></div>
          </div>
          <div class="meter">
            <div class="meter-head">
              <span>Score Signal</span><strong>${escapeHtml(selected.ordering_score)}</strong>
            </div>
            <div class="bar"><div class="fill" style="width: ${scoreWidth}%"></div></div>
          </div>
        </header>

        <section class="block">
          <h3>Traceability</h3>
          <div class="links">
            <a href="${escapeHtml(compassScopeHref(selected.idea_id))}" target="_top">Compass Scope</a>
            <a href="${escapeHtml(registryHrefForRow(selected))}" target="_top">Registry</a>
            <a href="${escapeHtml(selected.idea_ui_href || selected.idea_href)}">Workstream Spec</a>
            ${
              selected.promoted_to_plan_ui_href
                ? `<a href="${escapeHtml(selected.promoted_to_plan_ui_href)}">Technical Implementation Plan</a>`
                : ""
            }
          </div>
          ${registryComponents.length ? `
            <p class="trace-subhead">Registry Components</p>
            <div class="topology-rel-body">${registryComponentLinksHtml}</div>
          ` : ""}
        </section>

        <section class="block">
          <h3>Topology</h3>
          ${topologyBoardHtml}
        </section>

        ${executionWaveSectionHtml}

        ${warningsSectionHtml}

        ${implementedSummaryHtml}

        <section class="block">
          <h3>Problem</h3>
          ${summarySectionHtml(selected.problem, "Not captured in the idea spec yet.")}
        </section>

        <section class="block">
          <h3>Customer</h3>
          ${summarySectionHtml(selected.customer, "Not captured in the idea spec yet.")}
        </section>

        <section class="block">
          <h3>Opportunity</h3>
          ${summarySectionHtml(selected.opportunity, "Not captured in the idea spec yet.")}
        </section>

        <section class="block">
          <div class="split-grid">
            <article class="split-card">
              <h3>Product View</h3>
              ${summarySectionHtml(selected.founder_pov, "Not captured in the idea spec yet.")}
            </article>
            <article class="split-card">
              <h3>Decision Basis</h3>
              ${toBulletHtml(selected)}
            </article>
          </div>
        </section>

        <section class="block">
          <h3>Success Metrics</h3>
          ${successMetricsHtml(selected)}
        </section>

        <section class="block">
          <h3>Ordering Rationale</h3>
          <p>${escapeHtml(selected.ordering_rationale || "No ordering rationale recorded.")}</p>
        </section>

        <section class="block">
          <h3>Impacted Parts</h3>
          <p>${escapeHtml(selected.impacted_parts || "Not specified.")}</p>
        </section>
      `;
    }

    function render(options = {}) {
      const filtered = sortRows(applyFilters());
      if (filtered.length && !filtered.some((item) => item.idea_id === state.selectedIdeaId)) {
        state.selectedIdeaId = String(filtered[0].idea_id || "");
      }
      const executionWaveSummary = executionWavePayload().summary || {};
      el.stats.innerHTML = summaryStatRows(filtered, executionWaveSummary).join("");

      el.meta.textContent = `Showing ${filtered.length} of ${all.length} workstreams · Source: ${DATA.index_file}`;
      void renderAnalytics(filtered);
      renderList(filtered, { preserveListScroll: Boolean(options.preserveListScroll) });
      void renderDetail(filtered);
      el.empty.hidden = true;
      if (!filtered.length) {
        el.detail.hidden = true;
        el.detailEmpty.hidden = true;
      }

      syncParentShellSelection();
    }

    function bind(element, key) {
      element.addEventListener("input", () => {
        state[key] = element.value;
        render();
      });
      element.addEventListener("change", () => {
        state[key] = element.value;
        render();
      });
    }

    bind(el.query, "query");
    bind(el.section, "section");
    bind(el.phase, "phase");
    bind(el.activity, "activity");
    bind(el.lane, "lane");
    bind(el.priority, "priority");
    bind(el.sort, "sort");

    el.mixByComplexity.addEventListener("click", () => {
      state.mixBy = "complexity";
      render();
    });
    el.mixBySize.addEventListener("click", () => {
      state.mixBy = "size";
      render();
    });

    loadAnalyticsPreference();
    if (workstreamParam) {
      state.selectedIdeaId = workstreamParam;
    }
    if (viewParam === "graph") {
      setAnalyticsExpanded(true);
    }

    render();

    if (viewParam === "graph") {
      document.getElementById("analytics-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    })();
