const __ODYLITH_SHELL_REDIRECT_IN_PROGRESS__ = (function enforceShellOwnedSurfaceAccess() {
  try {
    const expectedFrameId = "frame-atlas";
    const frameElement = window.frameElement;
    const actualFrameId = frameElement && typeof frameElement.id === "string" ? frameElement.id : "";
    if (window.parent && window.parent !== window && actualFrameId === expectedFrameId) {
      return false;
    }
    const shellUrl = new URL("../index.html", window.location.href);
    const currentParams = new URLSearchParams(window.location.search || "");
    const nextParams = new URLSearchParams();
    nextParams.set("tab", "atlas");
    const passthroughRules = [{"target":"workstream","sources":["workstream"]},{"target":"diagram","sources":["diagram"]}];
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

const payload = window["__ODYLITH_MERMAID_DATA__"] || {};
    const allDiagrams = payload.diagrams || [];
    const tooltipLookup = payload.tooltip_lookup && typeof payload.tooltip_lookup === "object"
      ? payload.tooltip_lookup
      : {};

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

    const workstreamTitleLookup = sanitizeLookupObject(tooltipLookup.workstream_titles);
    const diagramTitleLookup = sanitizeLookupObject(tooltipLookup.diagram_titles);

    const searchEl = document.getElementById("search");
    const kindFiltersEl = document.getElementById("kindFilters");
    const workstreamFilterEl = document.getElementById("workstreamFilter");
    const listEl = document.getElementById("diagramList");

    const statTotalEl = document.getElementById("statTotal");
    const statFreshEl = document.getElementById("statFresh");
    const statStaleEl = document.getElementById("statStale");

    const titleEl = document.getElementById("diagramTitle");
    const idEl = document.getElementById("diagramId");
    const kindEl = document.getElementById("diagramKind");
    const statusEl = document.getElementById("diagramStatus");
    const ownerEl = document.getElementById("diagramOwner");
    const reviewedEl = document.getElementById("diagramReviewed");
    const freshnessEl = document.getElementById("diagramFreshness");
    const freshnessCardEl = document.getElementById("diagramFreshnessCard");

    const sourceLinksEl = document.getElementById("sourceLinks");
    const sidebarToggleEl = document.getElementById("sidebarToggle");
    const sidebarCloseEl = document.getElementById("sidebarClose");
    const staleAlertEl = document.getElementById("staleAlert");
    const summaryEl = document.getElementById("diagramSummary");
    const componentListEl = document.getElementById("componentList");

    const backlogLinksEl = document.getElementById("backlogLinks");
    const planLinksEl = document.getElementById("planLinks");
    const docLinksEl = document.getElementById("docLinks");
    const codeLinksEl = document.getElementById("codeLinks");
    const registryLinksEl = document.getElementById("registryLinks");
    const surfaceLinksEl = document.getElementById("surfaceLinks");
    const ownerWorkstreamLinksEl = document.getElementById("ownerWorkstreamLinks");
    const activeWorkstreamLinksEl = document.getElementById("activeWorkstreamLinks");
    const historicalWorkstreamGroupEl = document.getElementById("historicalWorkstreamGroup");
    const historicalWorkstreamDisclosureEl = document.getElementById("historicalWorkstreamDisclosure");
    const historicalWorkstreamSummaryEl = document.getElementById("historicalWorkstreamSummary");
    const historicalWorkstreamLinksEl = document.getElementById("historicalWorkstreamLinks");

    const stageEl = document.getElementById("viewerStage");
    const imageEl = document.getElementById("viewerImage");
    const zoomReadoutEl = document.getElementById("zoomReadout");

    let activeList = allDiagrams.slice();
    let activeIndex = 0;
    let selectedDiagramId = "";
    let kindFilter = "all";
    let freshnessFilter = "all";
    let workstreamFilter = "all";
    let activeDiagram = null;

    let scale = 1;
    let offsetX = 0;
    let offsetY = 0;
    let dragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let panPointerId = null;
    let pinchState = null;
    const activePointers = new Map();

    const MIN_SCALE = 0.05;
    const MAX_SCALE = 5;
    const WORKSTREAM_ID_RE = /^B-\d{3,}$/;
    const DIAGRAM_ID_RE = /^D-\d{3,}$/;
    const DIAGRAM_COMPACT_RE = /^D(\d{3,})$/;
    const SIDEBAR_PREF_KEY = "mermaid.sidebar.collapsed";
    const TOOLING_BASE_HREF = "../../../../../../odylith/index.html";
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

    function normalizeSearchToken(value) {
      return String(value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "");
    }

    function escapeHtml(value) {
      return String(value || "").replace(/[&<>"']/g, (token) => {
        if (token === "&") return "&amp;";
        if (token === "<") return "&lt;";
        if (token === ">") return "&gt;";
        if (token === '"') return "&quot;";
        return "&#39;";
      });
    }

    function canonicalizeDiagramId(value) {
      let token = String(value || "").trim().toUpperCase();
      if (!token) return "";
      if (token.startsWith("DIAGRAM:")) {
        token = token.slice("DIAGRAM:".length).trim();
      }
      if (DIAGRAM_ID_RE.test(token)) {
        return token;
      }
      const compact = token.match(DIAGRAM_COMPACT_RE);
      if (compact) {
        return `D-${compact[1]}`;
      }
      return "";
    }

    function ownerWorkstreamsForDiagram(diagram) {
      const values = new Set();
      const listed = Array.isArray(diagram && diagram.related_workstreams)
        ? diagram.related_workstreams
        : [];
      listed.forEach((token) => {
        const workstream = String(token || "").trim();
        if (WORKSTREAM_ID_RE.test(workstream)) {
          values.add(workstream);
        }
      });
      return Array.from(values).sort();
    }

    function activeWorkstreamsForDiagram(diagram) {
      const values = new Set();
      const listed = Array.isArray(diagram && diagram.active_workstreams)
        ? diagram.active_workstreams
        : [];
      listed.forEach((token) => {
        const workstream = String(token || "").trim();
        if (WORKSTREAM_ID_RE.test(workstream)) {
          values.add(workstream);
        }
      });
      return Array.from(values).sort();
    }

    function historicalWorkstreamsForDiagram(diagram) {
      const values = new Set();
      const listed = Array.isArray(diagram && diagram.historical_workstreams)
        ? diagram.historical_workstreams
        : [];
      listed.forEach((token) => {
        const workstream = String(token || "").trim();
        if (WORKSTREAM_ID_RE.test(workstream)) {
          values.add(workstream);
        }
      });
      return Array.from(values).sort();
    }

    function relatedWorkstreamsForDiagram(diagram) {
      const values = new Set();
      ownerWorkstreamsForDiagram(diagram).forEach((workstream) => values.add(workstream));
      activeWorkstreamsForDiagram(diagram).forEach((workstream) => values.add(workstream));
      return Array.from(values).sort();
    }

    function allWorkstreamReferencesForDiagram(diagram) {
      const values = new Set();
      relatedWorkstreamsForDiagram(diagram).forEach((workstream) => values.add(workstream));
      historicalWorkstreamsForDiagram(diagram).forEach((workstream) => values.add(workstream));
      return Array.from(values).sort();
    }

    function diagramMatchesWorkstream(diagram, workstreamId) {
      const normalized = normalizeWorkstreamId(workstreamId);
      if (!normalized) return true;
      return relatedWorkstreamsForDiagram(diagram).includes(normalized);
    }

    function normalizeSelectedDiagramWorkstreamFilter() {
      const selectedToken = canonicalizeDiagramId(selectedDiagramId);
      if (!selectedToken || workstreamFilter === "all") {
        return;
      }
      const selectedDiagram = allDiagrams.find(
        (diagram) => canonicalizeDiagramId(diagram.diagram_id) === selectedToken
      );
      if (!selectedDiagram) {
        return;
      }
      if (diagramMatchesWorkstream(selectedDiagram, workstreamFilter)) {
        return;
      }
      workstreamFilter = "all";
      workstreamFilterEl.value = "all";
    }

    function setSidebarCollapsed(collapsed) {
      document.body.classList.toggle("sidebar-collapsed", collapsed);
      sidebarToggleEl.textContent = collapsed ? "Show Panel" : "Hide Panel";
      sidebarToggleEl.setAttribute("aria-expanded", String(!collapsed));
    }

    function currentAtlasNavigationState() {
      const rawWorkstream = workstreamFilter === "all" ? "" : String(workstreamFilter || "").trim();
      const workstream = WORKSTREAM_ID_RE.test(rawWorkstream) ? rawWorkstream : "";
      const diagram = canonicalizeDiagramId(activeDiagram && activeDiagram.diagram_id);
      return { workstream, diagram };
    }

    function syncAtlasNavigation(options = {}) {
      const state = currentAtlasNavigationState();
      const query = new URLSearchParams(window.location.search);
      query.delete("workstream");
      query.delete("diagram");
      if (state.workstream) query.set("workstream", state.workstream);
      if (state.diagram) query.set("diagram", state.diagram);

      const nextSearch = query.toString();
      const currentSearch = String(window.location.search || "").replace(/^\?/, "");
      if (nextSearch !== currentSearch) {
        const suffix = nextSearch ? `?${nextSearch}` : "";
        window.history.replaceState(null, "", `${window.location.pathname}${suffix}`);
      }

      if (options.notifyParent === false) return;
      try {
        if (window.parent && window.parent !== window) {
          window.parent.postMessage(
            {
              type: "odylith-atlas-navigate",
              state: {
                tab: "atlas",
                workstream: state.workstream,
                diagram: state.diagram,
              },
            },
            "*",
          );
        }
      } catch (_error) {
        // Fall open: local URL remains canonical for direct Atlas browsing.
      }
    }

    function clamp(value, low, high) {
      return Math.min(high, Math.max(low, value));
    }

    function applyTransform() {
      imageEl.style.transform = `translate(calc(-50% + ${offsetX}px), calc(-50% + ${offsetY}px)) scale(${scale})`;
      zoomReadoutEl.textContent = `Zoom ${Math.round(scale * 100)}%`;
    }

    function resetView() {
      scale = 1;
      offsetX = 0;
      offsetY = 0;
      applyTransform();
    }

    function diagramDimensions(diagram) {
      const vbw = Number(diagram && diagram.svg_viewbox_width ? diagram.svg_viewbox_width : 0);
      const vbh = Number(diagram && diagram.svg_viewbox_height ? diagram.svg_viewbox_height : 0);
      if (Number.isFinite(vbw) && Number.isFinite(vbh) && vbw > 0 && vbh > 0) {
        return { width: vbw, height: vbh };
      }
      const iw = imageEl.naturalWidth || 0;
      const ih = imageEl.naturalHeight || 0;
      if (!iw || !ih) {
        return null;
      }
      return { width: iw, height: ih };
    }

    function applyImageBoxSizing(diagram) {
      const dims = diagramDimensions(diagram);
      if (!dims) {
        imageEl.style.width = "";
        imageEl.style.height = "";
        return;
      }
      // SVGs that declare percentage sizing report tiny intrinsic dimensions in
      // <img>. Keep the image box aligned with Atlas's viewBox-based fit math.
      imageEl.style.width = `${dims.width}px`;
      imageEl.style.height = `${dims.height}px`;
    }

    function computedFitScale(diagram) {
      const dims = diagramDimensions(diagram);
      if (!dims) {
        return null;
      }
      const sw = stageEl.clientWidth || 1;
      const sh = stageEl.clientHeight || 1;
      return Math.min(sw / dims.width, sh / dims.height);
    }

    function applyInitialView(diagram) {
      const dims = diagramDimensions(diagram);
      if (!dims) {
        resetView();
        return;
      }
      const rawFitScale = computedFitScale(diagram);
      if (rawFitScale === null) {
        resetView();
        return;
      }

      // Start near the full-bounds fit with a small safety margin so diagrams
      // feel snug on first paint without clipping at the edges.
      let initialFactor = 0.98;
      const MIN_INITIAL_FIT_FACTOR = 0.94;

      const rawOverrideFactor = Number(diagram && diagram.initial_view_fit_factor ? diagram.initial_view_fit_factor : 0);
      if (Number.isFinite(rawOverrideFactor) && rawOverrideFactor > 0) {
        initialFactor = clamp(rawOverrideFactor, MIN_INITIAL_FIT_FACTOR, initialFactor);
      }

      const target = rawFitScale * initialFactor;
      scale = clamp(target, MIN_SCALE, 1);
      offsetX = 0;
      offsetY = 0;
      applyTransform();
    }

    function fitView() {
      const rawFitScale = computedFitScale(activeDiagram);
      if (rawFitScale === null) {
        resetView();
        return;
      }
      scale = clamp(rawFitScale, MIN_SCALE, MAX_SCALE);
      offsetX = 0;
      offsetY = 0;
      applyTransform();
    }

    function zoomBy(factor, centerX, centerY) {
      zoomTo(scale * factor, centerX, centerY);
    }

    function zoomTo(targetScale, centerX, centerY) {
      const oldScale = scale;
      const newScale = clamp(targetScale, MIN_SCALE, MAX_SCALE);
      if (newScale === oldScale) {
        return;
      }
      const px = centerX - stageEl.clientWidth / 2;
      const py = centerY - stageEl.clientHeight / 2;
      offsetX = px - ((px - offsetX) / oldScale) * newScale;
      offsetY = py - ((py - offsetY) / oldScale) * newScale;
      scale = newScale;
      applyTransform();
    }

    function clearNode(node) {
      while (node.firstChild) {
        node.removeChild(node.firstChild);
      }
    }

    function renderLinkList(node, links) {
      clearNode(node);
      if (!links || !links.length) {
        return;
      }
      links.forEach((item) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = item.href;
        const target = String(item && item.target ? item.target : "_blank").trim() || "_blank";
        a.target = target;
        if (target === "_blank") {
          a.rel = "noreferrer";
        }
        a.textContent = item.file;
        li.appendChild(a);
        node.appendChild(li);
      });
    }

    function workstreamTitleForId(ideaId) {
      const token = String(ideaId || "").trim();
      if (!token) return "";
      const explicit = String(workstreamTitleLookup[token] || "").trim();
      if (explicit) return explicit;
      return token;
    }

    function diagramButtonTooltip(diagram) {
      const diagramId = canonicalizeDiagramId(diagram.diagram_id) || String(diagram.diagram_id || "").trim();
      const mapped = String(diagramTitleLookup[diagramId] || "").trim();
      if (mapped) return mapped;
      const title = String(diagram.title || "").trim();
      if (title) return title;
      return diagramId || "Diagram";
    }

    function normalizeWorkstreamId(value) {
      const token = String(value || "").trim();
      return WORKSTREAM_ID_RE.test(token) ? token : "";
    }

    function renderWorkstreamList(node, ids) {
      clearNode(node);
      if (!ids.length) {
        return;
      }

      ids.forEach((id) => {
        const li = document.createElement("li");
        li.className = "context-link-item";

        const a = document.createElement("a");
        a.className = "workstream-pill-link";
        a.href = `${TOOLING_BASE_HREF}?tab=radar&workstream=${encodeURIComponent(id)}`;
        a.textContent = id;
        const tooltip = workstreamTitleForId(id);
        a.setAttribute("data-tooltip", tooltip);
        a.setAttribute("aria-label", tooltip);
        a.target = "_top";
        li.appendChild(a);
        node.appendChild(li);
      });
    }

    function renderWorkstreamContext(diagram) {
      const ownerIds = ownerWorkstreamsForDiagram(diagram);
      const activeIds = activeWorkstreamsForDiagram(diagram);
      const historicalIds = historicalWorkstreamsForDiagram(diagram);

      renderWorkstreamList(ownerWorkstreamLinksEl, ownerIds);
      renderWorkstreamList(activeWorkstreamLinksEl, activeIds);

      if (!historicalIds.length) {
        historicalWorkstreamGroupEl.hidden = true;
        historicalWorkstreamDisclosureEl.open = false;
        historicalWorkstreamSummaryEl.textContent = "";
        clearNode(historicalWorkstreamLinksEl);
        return;
      }

      historicalWorkstreamGroupEl.hidden = false;
      historicalWorkstreamSummaryEl.textContent =
        historicalIds.length === 1
          ? "1 historical reference"
          : `${historicalIds.length} historical references`;
      renderWorkstreamList(historicalWorkstreamLinksEl, historicalIds);
    }

    function renderSourceLinks(diagram) {
      clearNode(sourceLinksEl);
      const sources = [
        { label: "Mermaid Source", href: diagram.source_mmd_href },
        { label: "SVG", href: diagram.source_svg_href },
      ];
      if (diagram.source_png_href) {
        sources.push({ label: "PNG", href: diagram.source_png_href });
      }
      sources.forEach((source) => {
        const a = document.createElement("a");
        a.className = "source-link";
        a.href = source.href;
        a.textContent = source.label;
        a.target = "_blank";
        a.rel = "noreferrer";
        sourceLinksEl.appendChild(a);
      });
    }

    function renderComponents(diagram) {
      clearNode(componentListEl);
      (diagram.components || []).forEach((component) => {
        const card = document.createElement("article");
        card.className = "component-card";

        const heading = document.createElement("strong");
        heading.textContent = component.name;

        const body = document.createElement("p");
        body.textContent = component.description;

        card.appendChild(heading);
        card.appendChild(body);
        componentListEl.appendChild(card);
      });
    }

    function renderAlert(diagram) {
      if (diagram.freshness === "stale" && (diagram.stale_reasons || []).length) {
        staleAlertEl.classList.add("visible");
        staleAlertEl.innerHTML = `<strong>Update Required:</strong> ${diagram.stale_reasons.join(" ")}`;
      } else {
        staleAlertEl.classList.remove("visible");
        staleAlertEl.textContent = "";
      }
    }

    function clearActiveDiagram() {
      activeDiagram = null;
      titleEl.textContent = "";
      idEl.textContent = "";
      kindEl.textContent = "";
      statusEl.textContent = "";
      ownerEl.textContent = "";
      reviewedEl.textContent = "";
      freshnessEl.textContent = "";
      freshnessCardEl?.classList.remove("ok", "warn");
      summaryEl.textContent = "";
      clearNode(sourceLinksEl);
      clearNode(componentListEl);
      clearNode(backlogLinksEl);
      clearNode(planLinksEl);
      clearNode(docLinksEl);
      clearNode(codeLinksEl);
      clearNode(registryLinksEl);
      clearNode(surfaceLinksEl);
      clearNode(ownerWorkstreamLinksEl);
      clearNode(activeWorkstreamLinksEl);
      clearNode(historicalWorkstreamLinksEl);
      historicalWorkstreamGroupEl.hidden = true;
      historicalWorkstreamDisclosureEl.open = false;
      historicalWorkstreamSummaryEl.textContent = "";
      staleAlertEl.classList.remove("visible");
      staleAlertEl.textContent = "";
      imageEl.removeAttribute("src");
      imageEl.dataset.fallbackApplied = "";
    }

    function applyMeta(diagram) {
      activeDiagram = diagram;
      titleEl.textContent = diagram.title;
      idEl.textContent = diagram.diagram_id;
      kindEl.textContent = diagram.kind;
      statusEl.textContent = diagram.status;
      ownerEl.textContent = diagram.owner;
      reviewedEl.textContent = diagram.last_reviewed_utc;
      freshnessEl.textContent = diagram.freshness === "stale" ? "Needs Update" : "Fresh";
      freshnessCardEl?.classList.toggle("warn", diagram.freshness === "stale");
      freshnessCardEl?.classList.toggle("ok", diagram.freshness !== "stale");

      summaryEl.textContent = diagram.summary;

      imageEl.onload = () => applyInitialView(diagram);
      imageEl.onerror = () => {
        const fallback = String(diagram.source_png_href || "").trim();
        if (!fallback) return;
        if (imageEl.dataset.fallbackApplied === "1") return;
        imageEl.dataset.fallbackApplied = "1";
        imageEl.src = fallback;
      };
      imageEl.dataset.fallbackApplied = "";
      applyImageBoxSizing(diagram);
      imageEl.src = diagram.source_svg_href;

      renderSourceLinks(diagram);
      renderComponents(diagram);
      renderAlert(diagram);

      renderLinkList(backlogLinksEl, diagram.related_backlog);
      renderLinkList(planLinksEl, diagram.related_plans);
      renderLinkList(docLinksEl, diagram.related_docs);
      renderLinkList(codeLinksEl, diagram.related_code);
      renderLinkList(registryLinksEl, diagram.related_registry);
      renderLinkList(surfaceLinksEl, diagram.related_surfaces);
      renderWorkstreamContext(diagram);
    }

    function setActive(index) {
      if (!activeList.length) {
        selectedDiagramId = "";
        clearActiveDiagram();
        syncAtlasNavigation();
        return;
      }
      activeIndex = clamp(index, 0, activeList.length - 1);
      const diagram = activeList[activeIndex];
      selectedDiagramId = canonicalizeDiagramId(diagram.diagram_id) || String(diagram.diagram_id || "").trim();
      applyMeta(diagram);

      const allItems = listEl.querySelectorAll(".diagram-item");
      allItems.forEach((node, nodeIndex) => {
        node.classList.toggle("active", nodeIndex === activeIndex);
      });
      syncAtlasNavigation();
    }

    function updateStats(sourceList) {
      const total = sourceList.length;
      let fresh = 0;
      let stale = 0;
      sourceList.forEach((item) => {
        if (item.freshness === "stale") {
          stale += 1;
        } else {
          fresh += 1;
        }
      });
      statTotalEl.textContent = String(total);
      statFreshEl.textContent = String(fresh);
      statStaleEl.textContent = String(stale);
    }

    function renderList() {
      clearNode(listEl);
      if (!activeList.length) {
        selectedDiagramId = "";
        clearActiveDiagram();
        syncAtlasNavigation();
        return;
      }

      activeList.forEach((diagram, idx) => {
        const li = document.createElement("li");
        li.className = "diagram-item";

        const button = document.createElement("button");
        button.className = "diagram-btn";
        button.type = "button";
        button.setAttribute("data-diagram", diagram.diagram_id);
        const tooltip = diagramButtonTooltip(diagram);
        button.setAttribute("data-tooltip", tooltip);
        button.setAttribute("aria-label", tooltip);

        const freshnessTag = diagram.freshness === "stale" ? '<span class="tag stale">Needs Update</span>' : '<span class="tag">Fresh</span>';
        button.innerHTML = `
          <div class="diagram-meta">
            <span class="tag">${diagram.diagram_id} · ${diagram.kind}</span>
            ${freshnessTag}
          </div>
          <div class="diagram-name">${diagram.title}</div>
          <div class="diagram-owner">${diagram.owner}</div>
        `;

        button.addEventListener("click", () => setActive(idx));
        li.appendChild(button);
        listEl.appendChild(li);
      });

      setActive(Math.min(activeIndex, activeList.length - 1));
    }

    function buildKindFilters() {
      clearNode(kindFiltersEl);
      const kinds = [...new Set(allDiagrams.map((item) => item.kind))].sort();
      const all = ["all", ...kinds];
      all.forEach((kindToken) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip" + (kindToken === kindFilter ? " active" : "");
        chip.textContent = kindToken;
        chip.addEventListener("click", () => {
          kindFilter = kindToken;
          buildKindFilters();
          applyFilters();
        });
        kindFiltersEl.appendChild(chip);
      });
    }

    function buildWorkstreamFilter() {
      const values = new Set();
      allDiagrams.forEach((diagram) => {
        relatedWorkstreamsForDiagram(diagram).forEach((id) => {
          if (id) values.add(id);
        });
      });
      const options = ["all", ...Array.from(values).sort()];
      clearNode(workstreamFilterEl);
      options.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value === "all" ? "All Workstreams" : value;
        if (value === workstreamFilter) {
          option.selected = true;
        }
        workstreamFilterEl.appendChild(option);
      });
    }

    function applyFilters() {
      const needle = String(searchEl.value || "").trim().toLowerCase();
      const normalizedNeedle = normalizeSearchToken(needle);
      normalizeSelectedDiagramWorkstreamFilter();
      const selectedToken = canonicalizeDiagramId(selectedDiagramId);
      activeList = allDiagrams.filter((diagram) => {
        const diagramToken = canonicalizeDiagramId(diagram.diagram_id);
        if (kindFilter !== "all" && diagram.kind !== kindFilter) {
          return false;
        }
        if (freshnessFilter !== "all" && diagram.freshness !== freshnessFilter) {
          return false;
        }
        if (workstreamFilter !== "all") {
          const related = relatedWorkstreamsForDiagram(diagram);
          if (!related.includes(workstreamFilter)) {
            return false;
          }
        }

        if (!needle) {
          return true;
        }

        const textParts = [
          diagram.diagram_id,
          diagramToken,
          diagram.title,
          diagram.summary,
          diagram.kind,
          diagram.owner,
          diagram.status,
          diagram.last_reviewed_utc,
          ...allWorkstreamReferencesForDiagram(diagram),
          ...(diagram.components || []).map((item) => `${item.name} ${item.description}`),
        ];
        const text = textParts.join(" ").toLowerCase();
        if (text.includes(needle)) {
          return true;
        }
        if (!normalizedNeedle) {
          return false;
        }
        const normalizedText = normalizeSearchToken(textParts.join(" "));
        return normalizedText.includes(normalizedNeedle);
      });

      if (!activeList.length && selectedToken) {
        const fallback = allDiagrams.find(
          (diagram) => canonicalizeDiagramId(diagram.diagram_id) === selectedToken
        );
        if (fallback) {
          if (workstreamFilter !== "all" && !diagramMatchesWorkstream(fallback, workstreamFilter)) {
            workstreamFilter = "all";
            workstreamFilterEl.value = "all";
            applyFilters();
            return;
          }
          activeList = [fallback];
        }
      }

      const selectedIndex = selectedToken
        ? activeList.findIndex((diagram) => canonicalizeDiagramId(diagram.diagram_id) === selectedToken)
        : -1;
      activeIndex = selectedIndex >= 0 ? selectedIndex : 0;
      updateStats(activeList);
      renderList();
    }

    function moveSelection(delta) {
      if (!activeList.length) {
        return;
      }
      setActive(clamp(activeIndex + delta, 0, activeList.length - 1));
    }

    function pointerRecord(event) {
      return {
        x: event.clientX,
        y: event.clientY,
        type: event.pointerType,
      };
    }

    function touchPointers() {
      return [...activePointers.values()].filter((item) => item.type === "touch");
    }

    function distance(a, b) {
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      return Math.sqrt((dx * dx) + (dy * dy));
    }

    function center(a, b) {
      return {
        x: (a.x + b.x) / 2,
        y: (a.y + b.y) / 2,
      };
    }

    function beginPan(event) {
      dragging = true;
      panPointerId = event.pointerId;
      dragStartX = event.clientX - offsetX;
      dragStartY = event.clientY - offsetY;
      stageEl.classList.add("dragging");
    }

    function endPan() {
      dragging = false;
      panPointerId = null;
      stageEl.classList.remove("dragging");
    }

    document.querySelectorAll("[data-freshness]").forEach((chip) => {
      chip.addEventListener("click", () => {
        freshnessFilter = chip.getAttribute("data-freshness") || "all";
        document.querySelectorAll("[data-freshness]").forEach((node) => node.classList.remove("active"));
        chip.classList.add("active");
        applyFilters();
      });
    });

    sidebarToggleEl.addEventListener("click", () => {
      const next = !document.body.classList.contains("sidebar-collapsed");
      setSidebarCollapsed(next);
      try {
        localStorage.setItem(SIDEBAR_PREF_KEY, next ? "1" : "0");
      } catch (err) {
        // no-op
      }
    });

    sidebarCloseEl.addEventListener("click", () => {
      setSidebarCollapsed(true);
      try {
        localStorage.setItem(SIDEBAR_PREF_KEY, "1");
      } catch (err) {
        // no-op
      }
    });

    searchEl.addEventListener("input", applyFilters);
    workstreamFilterEl.addEventListener("change", () => {
      workstreamFilter = workstreamFilterEl.value || "all";
      applyFilters();
      syncAtlasNavigation();
    });

    document.getElementById("zoomIn").addEventListener("click", () => {
      zoomBy(1.14, stageEl.clientWidth / 2, stageEl.clientHeight / 2);
    });

    document.getElementById("zoomOut").addEventListener("click", () => {
      zoomBy(0.88, stageEl.clientWidth / 2, stageEl.clientHeight / 2);
    });

    document.getElementById("fit").addEventListener("click", fitView);
    document.getElementById("reset").addEventListener("click", resetView);
    document.getElementById("prevDiagram").addEventListener("click", () => moveSelection(-1));
    document.getElementById("nextDiagram").addEventListener("click", () => moveSelection(1));

    stageEl.addEventListener("pointerdown", (event) => {
      activePointers.set(event.pointerId, pointerRecord(event));
      stageEl.setPointerCapture(event.pointerId);

      const touches = touchPointers();
      if (touches.length >= 2) {
        endPan();
        const a = touches[0];
        const b = touches[1];
        pinchState = {
          startDistance: Math.max(1, distance(a, b)),
          startScale: scale,
        };
        return;
      }

      if (!pinchState) {
        beginPan(event);
      }
    });

    stageEl.addEventListener("pointermove", (event) => {
      if (activePointers.has(event.pointerId)) {
        activePointers.set(event.pointerId, pointerRecord(event));
      }

      const touches = touchPointers();
      if (touches.length >= 2) {
        if (!pinchState) {
          const a = touches[0];
          const b = touches[1];
          pinchState = {
            startDistance: Math.max(1, distance(a, b)),
            startScale: scale,
          };
        }
        const a = touches[0];
        const b = touches[1];
        const rect = stageEl.getBoundingClientRect();
        const midpoint = center(a, b);
        const ratio = distance(a, b) / Math.max(1, pinchState.startDistance);
        zoomTo(pinchState.startScale * ratio, midpoint.x - rect.left, midpoint.y - rect.top);
        return;
      }

      if (pinchState) {
        pinchState = null;
      }

      if (dragging && event.pointerId === panPointerId) {
        offsetX = event.clientX - dragStartX;
        offsetY = event.clientY - dragStartY;
        applyTransform();
      }
    });

    function stopPointer(event) {
      activePointers.delete(event.pointerId);
      if (event.pointerId === panPointerId) {
        endPan();
      }

      if (touchPointers().length < 2) {
        pinchState = null;
      }

      try {
        stageEl.releasePointerCapture(event.pointerId);
      } catch (err) {
        // no-op
      }
    }

    stageEl.addEventListener("pointerup", stopPointer);
    stageEl.addEventListener("pointercancel", stopPointer);

    // Desktop trackpad pinch commonly arrives as wheel+ctrlKey.
    // Accept only that path; plain wheel scrolling must not zoom.
    stageEl.addEventListener("wheel", (event) => {
      if (!event.ctrlKey) {
        return;
      }
      event.preventDefault();
      const rect = stageEl.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      zoomBy(event.deltaY < 0 ? 1.08 : 0.92, x, y);
    }, { passive: false });

    window.addEventListener("keydown", (event) => {
      const key = event.key;
      if (key === "+" || key === "=") {
        zoomBy(1.14, stageEl.clientWidth / 2, stageEl.clientHeight / 2);
      } else if (key === "-") {
        zoomBy(0.88, stageEl.clientWidth / 2, stageEl.clientHeight / 2);
      } else if (key === "0") {
        resetView();
      } else if (key.toLowerCase() === "f") {
        fitView();
      } else if (key === "ArrowUp") {
        moveSelection(-1);
      } else if (key === "ArrowDown") {
        moveSelection(1);
      }
    });

    window.addEventListener("resize", () => fitView());

    let sidebarCollapsed = false;
    try {
      sidebarCollapsed = localStorage.getItem(SIDEBAR_PREF_KEY) === "1";
    } catch (err) {
      sidebarCollapsed = false;
    }
    setSidebarCollapsed(sidebarCollapsed);

    const params = new URLSearchParams(window.location.search);
    const paramWorkstream = (params.get("workstream") || "").trim();
    const paramDiagram = (params.get("diagram") || "").trim();
    if (WORKSTREAM_ID_RE.test(paramWorkstream)) {
      workstreamFilter = paramWorkstream;
    }
    const normalizedParamDiagram = canonicalizeDiagramId(paramDiagram);
    if (normalizedParamDiagram) {
      selectedDiagramId = normalizedParamDiagram;
    } else if (paramDiagram) {
      selectedDiagramId = paramDiagram;
    }

    buildKindFilters();
    buildWorkstreamFilter();
    applyFilters();
