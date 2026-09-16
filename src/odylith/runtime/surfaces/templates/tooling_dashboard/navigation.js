// Own shell routes, history and document-bound embedded navigation.
function createToolingShellNavigation({ panes, payload, onState, localStorageRead, localStorageWrite }) {
    const shellStateStorageKey = `odylith.shell.state:${window.location.pathname}`;
    const DIAGRAM_ID_RE = /^D-\d{3,}$/;
    const DIAGRAM_COMPACT_RE = /^D(\d{3,})$/;
    function canonicalizeDiagramToken(value) {
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

    const CASEBOOK_SORT_DEFAULT = "newest";
    const CASEBOOK_SORT_TOKENS = new Set(["newest", "oldest", "bug-id", "priority", "status"]);

    function canonicalizeCasebookSortToken(value) {
      const token = String(value || "").trim().toLowerCase();
      return CASEBOOK_SORT_TOKENS.has(token) ? token : CASEBOOK_SORT_DEFAULT;
    }

    const tabStateMemory = {
      project: {},
      radar: { workstream: "", view: "" },
      atlas: { workstream: "", diagram: "" },
      compass: { workstream: "", window: "", date: "", audit_day: "" },
      registry: { component: "" },
      casebook: { bug: "", severity: "", status: "", sort: CASEBOOK_SORT_DEFAULT },
    };

    function sanitizeShellState(rawState) {
      const tabToken = String(rawState && rawState.tab ? rawState.tab : "").trim().toLowerCase();
      const tab = tabToken === "project"
        ? "project"
        : (tabToken === "atlas"
          ? "atlas"
          : (tabToken === "compass" ? "compass" : (tabToken === "registry" ? "registry" : (tabToken === "casebook" ? "casebook" : (tabToken === "radar" ? "radar" : "project")))));
      const workstream = /^B-\d{3,}$/.test(String(rawState && rawState.workstream ? rawState.workstream : "").trim())
        ? String(rawState.workstream).trim()
        : "";
      const state = {
        tab,
        workstream: "",
        component: "",
        bug: "",
        severity: "",
        status: "",
        sort: CASEBOOK_SORT_DEFAULT,
        diagram: "",
        view: "",
        window: "",
        date: "",
        audit_day: "",
      };
      if (tab === "radar") {
        state.workstream = workstream;
        const viewToken = String(rawState && rawState.view ? rawState.view : "").trim().toLowerCase();
        state.view = (viewToken === "spec" || viewToken === "plan") ? viewToken : "";
        return state;
      }
      if (tab === "atlas") {
        state.workstream = workstream;
        state.diagram = canonicalizeDiagramToken(rawState && rawState.diagram ? rawState.diagram : "");
        return state;
      }
      if (tab === "compass") {
        state.workstream = workstream;
        const windowToken = String(rawState && rawState.window ? rawState.window : "").trim().toLowerCase();
        state.window = (windowToken === "24h" || windowToken === "48h") ? windowToken : "";
        const dateToken = String(rawState && rawState.date ? rawState.date : "").trim();
        state.date = (dateToken === "live" || /^\d{4}-\d{2}-\d{2}$/.test(dateToken)) ? dateToken : "";
        const auditDayToken = String(rawState && rawState.audit_day ? rawState.audit_day : "").trim();
        state.audit_day = /^\d{4}-\d{2}-\d{2}$/.test(auditDayToken) ? auditDayToken : "";
        return state;
      }
      if (tab === "registry") {
        state.component = String(rawState && rawState.component ? rawState.component : "").trim().toLowerCase();
        return state;
      }
      if (tab === "project") {
        return state;
      }
      state.bug = String(rawState && rawState.bug ? rawState.bug : "").trim();
      state.severity = String(rawState && rawState.severity ? rawState.severity : "").trim().toLowerCase();
      state.status = String(rawState && rawState.status ? rawState.status : "").trim().toLowerCase();
      state.sort = canonicalizeCasebookSortToken(rawState && rawState.sort ? rawState.sort : "");
      return state;
    }

    function rememberTabState(rawState) {
      const state = sanitizeShellState(rawState || {});
      try {
        localStorageWrite(shellStateStorageKey, JSON.stringify(state));
      } catch (_error) {
        // Ignore storage serialization failures and keep the in-memory state only.
      }
      if (state.tab === "radar") {
        tabStateMemory.radar = { workstream: state.workstream, view: state.view };
        return state;
      }
      if (state.tab === "atlas") {
        tabStateMemory.atlas = { workstream: state.workstream, diagram: state.diagram };
        return state;
      }
      if (state.tab === "compass") {
        tabStateMemory.compass = {
          workstream: state.workstream,
          window: state.window,
          date: state.date,
          audit_day: state.audit_day,
        };
        return state;
      }
      if (state.tab === "registry") {
        tabStateMemory.registry = { component: state.component };
        return state;
      }
      if (state.tab === "project") {
        tabStateMemory.project = {};
        return state;
      }
      tabStateMemory.casebook = {
        bug: state.bug,
        severity: state.severity,
        status: state.status,
        sort: state.sort,
      };
      return state;
    }

    function rememberedTabState(tab) {
      return sanitizeShellState({ tab, ...(tabStateMemory[tab] || {}) });
    }

    function readStateFromUrl() {
      const params = new URLSearchParams(window.location.search);
      if (!params.toString()) {
        const rememberedState = localStorageRead(shellStateStorageKey);
        if (rememberedState) {
          try {
            const parsedState = JSON.parse(rememberedState);
            if (parsedState && typeof parsedState === "object") {
              return sanitizeShellState(parsedState);
            }
          } catch (_error) {
            // Ignore corrupt stored state and fall back to the default shell route.
          }
        }
      }
      const scopeToken = (params.get("scope") || "").trim();
      const workstreamToken = (params.get("workstream") || "").trim();
      const normalizedScopeToken = /^B-\d{3,}$/.test(scopeToken) ? scopeToken : "";
      const normalizedWorkstreamToken = /^B-\d{3,}$/.test(workstreamToken) ? workstreamToken : "";
      const componentToken = (params.get("component") || "").trim().toLowerCase();
      const bugToken = (params.get("bug") || "").trim();
      const severityToken = (params.get("severity") || "").trim().toLowerCase();
      const statusToken = (params.get("status") || "").trim().toLowerCase();
      const sortToken = (params.get("sort") || "").trim().toLowerCase();
      const tabToken = (params.get("tab") || "").trim().toLowerCase();
      const knownTab = ["project", "atlas", "compass", "registry", "casebook", "radar"].includes(tabToken)
        ? tabToken
        : "";
      const tab = knownTab
        || (normalizedWorkstreamToken || normalizedScopeToken ? "radar" : "")
        || (componentToken ? "registry" : "")
        || (bugToken || severityToken || statusToken || sortToken ? "casebook" : "")
        || (canonicalizeDiagramToken(params.get("diagram") || "") ? "atlas" : "")
        || "project";
      // Compass prefers `scope`, but still accepts legacy `workstream` query links.
      const activeWorkstreamToken = tab === "compass"
        ? (normalizedScopeToken || normalizedWorkstreamToken)
        : (normalizedWorkstreamToken || normalizedScopeToken);
      return sanitizeShellState({
        tab,
        workstream: activeWorkstreamToken,
        component: componentToken,
        bug: bugToken,
        severity: severityToken,
        status: statusToken,
        sort: sortToken,
        diagram: canonicalizeDiagramToken(params.get("diagram") || ""),
        view: (params.get("view") || "").trim(),
        window: (params.get("window") || "").trim().toLowerCase(),
        date: (params.get("date") || "").trim(),
        audit_day: (params.get("audit_day") || "").trim(),
      });
    }

    function buildFrameHref(baseHref, query) {
      const rawHref = String(baseHref || "").trim();
      if (!rawHref) return "";
      const hashIndex = rawHref.indexOf("#");
      const hash = hashIndex >= 0 ? rawHref.slice(hashIndex) : "";
      const withoutHash = hashIndex >= 0 ? rawHref.slice(0, hashIndex) : rawHref;
      const queryIndex = withoutHash.indexOf("?");
      const path = queryIndex >= 0 ? withoutHash.slice(0, queryIndex) : withoutHash;
      const merged = new URLSearchParams(queryIndex >= 0 ? withoutHash.slice(queryIndex + 1) : "");
      if (query && typeof query.forEach === "function") {
        query.forEach((value, key) => {
          merged.set(key, value);
        });
      }
      const qs = merged.toString();
      return `${path}${qs ? `?${qs}` : ""}${hash}`;
    }

    function buildRadarQuery(state) {
      const query = new URLSearchParams();
      if (state.workstream) query.set("workstream", state.workstream);
      if (state.view) query.set("view", state.view);
      return query;
    }

    function buildAtlasQuery(state) {
      const query = new URLSearchParams();
      if (state.workstream) query.set("workstream", state.workstream);
      const diagram = canonicalizeDiagramToken(state.diagram || "");
      if (diagram) query.set("diagram", diagram);
      return query;
    }

    function buildCompassQuery(state) {
      const query = new URLSearchParams();
      if (state.workstream) query.set("scope", state.workstream);
      if (state.window) query.set("window", state.window);
      if (state.date) query.set("date", state.date);
      if (state.audit_day) query.set("audit_day", state.audit_day);
      return query;
    }

    function buildRegistryQuery(state) {
      const query = new URLSearchParams();
      if (state.component) query.set("component", state.component);
      return query;
    }

    function buildCasebookQuery(state) {
      const query = new URLSearchParams();
      if (state.bug) query.set("bug", state.bug);
      if (state.severity) query.set("severity", state.severity);
      if (state.status) query.set("status", state.status);
      const sort = canonicalizeCasebookSortToken(state.sort || "");
      if (sort !== CASEBOOK_SORT_DEFAULT) query.set("sort", sort);
      return query;
    }

    function frameHrefsForState(state) {
      return {
        project: "",
        radar: buildFrameHref(payload.radar_href, buildRadarQuery(state)),
        atlas: buildFrameHref(payload.atlas_href, buildAtlasQuery(state)),
        compass: buildFrameHref(payload.compass_href, buildCompassQuery(state)),
        registry: buildFrameHref(payload.registry_href, buildRegistryQuery(state)),
        casebook: buildFrameHref(payload.casebook_href, buildCasebookQuery(state)),
      };
    }

    function dashboardQueryString(state) {
      const query = new URLSearchParams();
      query.set("tab", state.tab);
      if (state.tab === "compass") {
        if (state.workstream) query.set("scope", state.workstream);
      } else if (state.tab === "registry") {
        if (state.component) query.set("component", state.component);
      } else if (state.tab === "casebook") {
        if (state.bug) query.set("bug", state.bug);
        if (state.severity) query.set("severity", state.severity);
        if (state.status) query.set("status", state.status);
        const sort = canonicalizeCasebookSortToken(state.sort || "");
        if (sort !== CASEBOOK_SORT_DEFAULT) query.set("sort", sort);
      } else if (state.workstream) {
        query.set("workstream", state.workstream);
      }
      const diagram = canonicalizeDiagramToken(state.diagram || "");
      if (diagram) query.set("diagram", diagram);
      if (state.view) query.set("view", state.view);
      if (state.window) query.set("window", state.window);
      if (state.date) query.set("date", state.date);
      if (state.audit_day) query.set("audit_day", state.audit_day);
      const token = query.toString();
      return token ? `?${token}` : "";
    }

    function buildTabActivationState(tab) {
      const current = readStateFromUrl();
      if (current.tab === tab) {
        return current;
      }
      return rememberedTabState(tab);
    }


    const entries = {};
    // Children own canonical filters; only record identity constrains selection.
    const selectionField = { radar: "workstream", atlas: "diagram", compass: "workstream",
      registry: "component", casebook: "bug" };
    let activeEntry = null;
    let settled = document.readyState === "complete";
    let started = false;

    function routeEquals(left, right) {
      return dashboardQueryString(left) === dashboardQueryString(right);
    }

    function permitsDefaults(requested, rendered, allowDefaults) {
      return Object.keys(requested).every((key) =>
        requested[key] === rendered[key] || (allowDefaults && requested[key] === ""));
    }

    function isInitialBlank(frame) {
      // Only the inherited initial Document is read. Real opaque file Documents
      // communicate through the same channel as HTTP Documents.
      return frame.contentDocument?.URL === "about:blank";
    }

    function showState(raw, historyMode = "replace") {
      const next = rememberTabState(raw);
      const search = dashboardQueryString(next);
      if (historyMode === "push") {
        window.history.pushState(null, "", window.location.pathname + search);
      } else if (historyMode === "replace" && window.location.search !== search) {
        window.history.replaceState(null, "", window.location.pathname + search);
      }
      onState(next);
      return next;
    }

    function replaceDocument(entry) {
      entry.bridge.revoke();
      entry.admitted = false;
      entry.awaitingLoad = true;
      entry.needsReplacement = false;
      entry.frame.dataset.navigationOutcome = "loading";
      const href = frameHrefsForState(entry.target)[entry.tab];
      entry.frame.contentWindow.location.replace(new URL(href, window.location.href).href);
    }

    function acceptSnapshot(entry, snapshot) {
      if (!snapshot || typeof snapshot !== "object"
          || !snapshot.requested || typeof snapshot.requested !== "object"
          || (snapshot.rendered !== null && typeof snapshot.rendered !== "object")
          || (snapshot.outcome === "ready" && !snapshot.rendered)
          || !["loading", "ready", "empty", "degraded"].includes(snapshot.outcome)) return;
      if (!settled || activeEntry !== entry || !entry.target || entry.awaitingLoad) return;
      const requested = sanitizeShellState({ ...snapshot.requested, tab: entry.tab });
      const rendered = snapshot.rendered
        ? sanitizeShellState({ ...snapshot.rendered, tab: entry.tab }) : null;
      if (!entry.admitted) {
        const requestedMatches = permitsDefaults(entry.target, requested, entry.allowDefaults);
        const currentMatches = rendered && snapshot.outcome !== "loading" && routeEquals(entry.target, rendered);
        if (!requestedMatches && !currentMatches) {
          replaceDocument(entry);
          return;
        }
        entry.admitted = true;
      }
      entry.frame.dataset.navigationOutcome = snapshot.outcome;
      if (snapshot.outcome === "loading" || !rendered) return;
      const key = selectionField[entry.tab];
      if (entry.target[key] !== rendered[key] && !(entry.allowDefaults && entry.target[key] === "")) {
        // An unavailable selection may normalize its filters, but cannot invent
        // another record or erase the explicit request. Late old records fail.
        if (rendered[key] !== "" || !["empty", "degraded"].includes(snapshot.outcome)) return;
        rendered[key] = entry.target[key];
      }
      entry.target = showState(rendered);
      entry.allowDefaults = false;
    }

    function acceptNavigation(entry, intent) {
      if (activeEntry !== entry || !entry.admitted || !intent
          || typeof intent !== "object" || !intent.route
          || typeof intent.route !== "object"
          || typeof intent.replaceDocument !== "boolean") return;
      entry.target = showState({ ...intent.route, tab: entry.tab });
      entry.allowDefaults = false;
      if (intent.replaceDocument) replaceDocument(entry);
    }

    for (const [tab, frame] of Object.entries(panes)) {
      if (tab === "project" || !frame) continue;
      const entry = { tab, frame, target: null, admitted: false,
        awaitingLoad: false, needsReplacement: false, allowDefaults: true };
      entry.bridge = window.OdylithFrameBridge.frame({
        frame,
        onActor: () => { entry.admitted = false; },
        onSnapshot: (snapshot) => acceptSnapshot(entry, snapshot),
        onNavigate: (intent) => acceptNavigation(entry, intent),
      });
      entry.onLoad = () => {
        entry.awaitingLoad = false;
        entry.admitted = false;
        if (activeEntry !== entry) {
          entry.bridge.revoke();
          return;
        }
        if (settled) reconcile(entry);
        else if (!isInitialBlank(frame)) entry.bridge.bind();
      };
      frame.addEventListener("load", entry.onLoad);
      entries[tab] = entry;
    }

    function reconcile(entry) {
      if (!settled || !entry || entry.awaitingLoad) return;
      if (entry.needsReplacement || isInitialBlank(entry.frame)) {
        replaceDocument(entry);
      } else {
        // Rebinding a channel is not a Document load or a new route request.
        entry.bridge.bind();
      }
    }

    function activate(raw, options = {}) {
      const state = sanitizeShellState(raw);
      const nextEntry = entries[state.tab] || null;
      if (activeEntry && activeEntry !== nextEntry) activeEntry.bridge.revoke();
      activeEntry = nextEntry;
      if (nextEntry) {
        // Keep changed history intent across bootstrap and in-flight loads.
        if (nextEntry.target && !routeEquals(nextEntry.target, state)) nextEntry.needsReplacement = true;
        if (!nextEntry.target || !routeEquals(nextEntry.target, state)) nextEntry.admitted = false;
        nextEntry.target = state;
        nextEntry.allowDefaults = options.allowDefaults !== false;
      }
      showState(state, options.historyMode || "replace");
      reconcile(nextEntry);
    }

    function settle() {
      settled = true;
      reconcile(activeEntry);
    }

    function replay() {
      activate(readStateFromUrl(), { historyMode: "replay" });
    }

    function suspend() {
      for (const entry of Object.values(entries)) entry.bridge.revoke();
    }

    function restore(event) {
      if (!event.persisted) return;
      settled = true;
      replay();
    }

    function dispose() {
      suspend();
      for (const entry of Object.values(entries)) {
        entry.frame.removeEventListener("load", entry.onLoad);
        entry.bridge.dispose();
      }
      window.removeEventListener("load", settle);
      window.removeEventListener("popstate", replay);
      window.removeEventListener("pagehide", suspend);
      window.removeEventListener("pageshow", restore);
    }

    return {
      readState: readStateFromUrl,
      activate,
      selectTab(tab) {
        activate(buildTabActivationState(tab), { historyMode: "push" });
      },
      reload() {
        if (activeEntry) replaceDocument(activeEntry);
      },
      start() {
        if (started) return;
        started = true;
        window.addEventListener("load", settle);
        window.addEventListener("popstate", replay);
        window.addEventListener("pagehide", suspend);
        window.addEventListener("pageshow", restore);
        activate(readStateFromUrl(), { historyMode: "replace" });
      },
      dispose,
    };
}
