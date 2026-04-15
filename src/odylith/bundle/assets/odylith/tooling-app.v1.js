const payload = window["__ODYLITH_TOOLING_DATA__"] || {};
    const shellTitle = document.title || "Odylith";
    const shellBrandName = shellTitle.replace(/\s+Dashboard$/, "") || "Odylith";
    const payloadScript = document.getElementById("toolingDashboardData");
    const tabTitles = {
      radar: "Radar",
      atlas: "Atlas",
      compass: "Compass",
      registry: "Registry",
      casebook: "Casebook",
    };
    const tabs = {
      radar: document.getElementById("tab-radar"),
      atlas: document.getElementById("tab-atlas"),
      compass: document.getElementById("tab-compass"),
      registry: document.getElementById("tab-registry"),
      casebook: document.getElementById("tab-casebook"),
    };
    const panes = {
      radar: document.getElementById("frame-radar"),
      atlas: document.getElementById("frame-atlas"),
      compass: document.getElementById("frame-compass"),
      registry: document.getElementById("frame-registry"),
      casebook: document.getElementById("frame-casebook"),
    };
    const paneVisitState = {
      radar: false,
      atlas: false,
      compass: false,
      registry: false,
      casebook: false,
    };
    const briefToggle = document.getElementById("gridBriefToggle");
    const briefDrawer = document.getElementById("gridBriefDrawer");
    const briefDrawerPanel = document.getElementById("gridBriefDrawerPanel");
    const briefClose = document.getElementById("gridBriefClose");
    const odylithToggle = document.getElementById("odylithToggle");
    const odylithDrawer = document.getElementById("odylithDrawer");
    const odylithDrawerPanel = document.getElementById("odylithDrawerPanel");
    const odylithClose = document.getElementById("odylithClose");
    const hasBriefDrawer = Boolean(briefToggle && briefDrawer && briefDrawerPanel && briefClose);
    const hasOdylithDrawer = Boolean(odylithToggle && odylithDrawer && odylithDrawerPanel && odylithClose);
    const viewport = document.querySelector(".viewport");
    const welcomeState = document.getElementById("shellWelcomeState");
    const recoveryDock = document.getElementById("shellRecoveryDock");
    const runtimeStatus = document.getElementById("shellRuntimeStatus");
    const runtimeStatusKicker = document.getElementById("shellRuntimeStatusKicker");
    const runtimeStatusTitle = document.getElementById("shellRuntimeStatusTitle");
    const runtimeStatusBody = document.getElementById("shellRuntimeStatusBody");
    const runtimeStatusMeta = document.getElementById("shellRuntimeStatusMeta");
    const runtimeStatusDismiss = document.getElementById("shellRuntimeStatusDismiss");
    const runtimeStatusReload = document.getElementById("shellRuntimeStatusReload");
    const welcomeReopen = document.getElementById("welcomeReopen");
    const upgradeSpotlight = document.getElementById("shellUpgradeSpotlight");
    const upgradeReopen = document.getElementById("upgradeReopen");
    const upgradeSpotlightBackdrop = document.getElementById("upgradeSpotlightBackdrop");
    const upgradeSpotlightDismiss = document.getElementById("upgradeSpotlightDismiss");
    const welcomeCopyPrompt = document.getElementById("welcomeCopyPrompt");
    const welcomeDismiss = document.getElementById("welcomeDismiss");
    const welcomeCopyStatus = document.getElementById("welcomeCopyStatus");
    const welcomeCopyButtons = Array.from(document.querySelectorAll("[data-welcome-copy][data-copy-text]"));
    const welcomeTabButtons = Array.from(document.querySelectorAll("[data-welcome-tab]"));
    const welcomeTaskCards = Array.from(document.querySelectorAll("[data-welcome-task]"));
    const welcomeTaskDoneButtons = Array.from(document.querySelectorAll("[data-welcome-task-done]"));
    const welcomeLaunchpadActive = Boolean(payload && payload.welcome_state && payload.welcome_state.show);
    const welcomeDismissKeyToken = welcomeState
      ? String(welcomeState.dataset.welcomeDismissKey || "").trim()
      : "";
    const welcomeDismissStorageKey = `odylith.welcome.dismissed:${window.location.pathname}:${welcomeDismissKeyToken || "default"}`;
    const upgradeSpotlightPayload = payload && payload.release_spotlight && typeof payload.release_spotlight === "object"
      ? payload.release_spotlight
      : null;
    const UPGRADE_SPOTLIGHT_MAX_AGE_MS = 30 * 60 * 1000;

    function parseIsoUtcMs(value) {
      const token = String(value || "").trim();
      if (!token) return 0;
      const parsed = Date.parse(token);
      return Number.isFinite(parsed) ? parsed : 0;
    }

    function resolveUpgradeSpotlightExpiryMs(rawPayload) {
      if (!rawPayload || typeof rawPayload !== "object") return 0;
      const explicitExpiry = parseIsoUtcMs(rawPayload.expires_utc);
      if (explicitExpiry > 0) {
        return explicitExpiry;
      }
      const recordedAt = parseIsoUtcMs(rawPayload.recorded_utc) || parseIsoUtcMs(rawPayload.release_published_at);
      return recordedAt > 0 ? recordedAt + UPGRADE_SPOTLIGHT_MAX_AGE_MS : 0;
    }

    const upgradeSpotlightExpiresAtMs = resolveUpgradeSpotlightExpiryMs(upgradeSpotlightPayload);
    let upgradeSpotlightActive = Boolean(
      upgradeSpotlightPayload
      && upgradeSpotlightPayload.show
      && String(upgradeSpotlightPayload.to_version || "").trim()
      && (!upgradeSpotlightExpiresAtMs || Date.now() < upgradeSpotlightExpiresAtMs)
    );
    function hasUpgradeSpotlight() {
      if (!upgradeSpotlightActive) return false;
      if (upgradeSpotlightExpiresAtMs && Date.now() >= upgradeSpotlightExpiresAtMs) {
        upgradeSpotlightActive = false;
        return false;
      }
      return true;
    }

    const upgradeSpotlightVersion = hasUpgradeSpotlight()
      ? String(upgradeSpotlightPayload.to_version || "").trim()
      : "";
    const upgradeSpotlightVersionLabel = upgradeSpotlightVersion && /^[0-9]/.test(upgradeSpotlightVersion)
      ? `v${upgradeSpotlightVersion}`
      : upgradeSpotlightVersion;
    const shellStateStorageKey = `odylith.shell.state:${window.location.pathname}`;
    const runtimeStatusDismissStorageKey = `odylith.runtime.status.dismissed:${window.location.pathname}`;
    const upgradeSpotlightRecordedToken = hasUpgradeSpotlight()
      ? String(upgradeSpotlightPayload.recorded_utc || upgradeSpotlightPayload.expires_utc || upgradeSpotlightPayload.release_published_at || "").trim()
      : "";
    const upgradeSpotlightKeyToken = hasUpgradeSpotlight()
      ? `${String(upgradeSpotlightPayload.from_version || "").trim()}->${String(upgradeSpotlightPayload.to_version || "").trim()}@${upgradeSpotlightRecordedToken || "unrecorded"}`
      : "";
    const upgradeSpotlightDismissStorageKey = upgradeSpotlightKeyToken
      ? `odylith.upgrade.spotlight.dismissed:${window.location.pathname}:${upgradeSpotlightKeyToken}`
      : "";
    const upgradeSpotlightReopenLabel = hasUpgradeSpotlight()
      ? String(
        upgradeSpotlightPayload.reopen_label
        || upgradeSpotlightPayload.title
        || upgradeSpotlightVersionLabel
        || ""
      ).trim()
      : "";
    const shouldDeferWelcomeUntilUpgradeCloses = Boolean(
      welcomeState
      && welcomeLaunchpadActive
      && !welcomeDismissed()
      && hasUpgradeSpotlight()
      && upgradeSpotlight
      && !upgradeSpotlightDismissed()
    );
    const DIAGRAM_ID_RE = /^D-\d{3,}$/;
    const DIAGRAM_COMPACT_RE = /^D(\d{3,})$/;
    const welcomeTaskStoragePrefix = `odylith.welcome.task:${window.location.pathname}:`;
    const shellPayloadGlobalName = "__ODYLITH_TOOLING_DATA__";
    const shellPayloadGeneratedUtc = String(payload.generated_utc || "").trim();
    const shellPayloadRefreshFingerprint = buildShellRefreshFingerprint(payload);
    let shellRefreshTimer = 0;
    let shellRefreshInFlight = false;
    const liveRefreshPayload = payload && payload.live_refresh && typeof payload.live_refresh === "object"
      ? payload.live_refresh
      : null;
    const initialSurfaceRuntimeStatus = payload && payload.surface_runtime_status && typeof payload.surface_runtime_status === "object"
      ? payload.surface_runtime_status
      : {};
    const runtimeProbeStateGlobalName = liveRefreshPayload
      ? String(liveRefreshPayload.state_global_name || "__ODYLITH_CONTEXT_ENGINE_STATE__").trim()
      : "__ODYLITH_CONTEXT_ENGINE_STATE__";
    let runtimeProbeTimer = 0;
    let runtimeProbeInFlight = false;
    let runtimeProbeFingerprint = "";
    let latestRuntimeStatusState = payload && typeof payload === "object"
      ? { ...payload, surface_runtime_status: initialSurfaceRuntimeStatus }
      : { surface_runtime_status: initialSurfaceRuntimeStatus };
    let runtimeStatusFingerprint = "";
    let runtimeStatusLayoutFrame = 0;
    let lastUserInteractionAtMs = Date.now();
    const runtimeAutoReloadAtByTab = Object.create(null);
    const ODYLITH_CHART_TEXT = "#27445e";
    const ODYLITH_AXIS_TEXT = "rgba(71, 98, 127, 0.82)";
    const ODYLITH_GRID_LINE = "rgba(148, 163, 184, 0.28)";
    const ODYLITH_CHART_PALETTE = {
      density: "#60a5fa",
      readiness: "#a78bfa",
      diversity: "#f59e0b",
      utility: "#2dd4bf",
      budget: "#2dd4bf",
      routeReady: "#38bdf8",
      spawnReady: "#c084fc",
      tokens: "#fb7185",
      execution: ["#7dd3fc", "#a78bfa", "#34d399", "#fb7185", "#f59e0b", "#60a5fa"],
      latencyImpact: "#7dd3fc",
      latencySession: "#34d399",
      latencyBootstrap: "#f59e0b",
      learningPacket: "#60a5fa",
      learningAlignment: "#f59e0b",
      learningYield: "#2dd4bf",
      learningRouter: "#c084fc",
      learningOrchestration: "#34d399",
      radar: "#7dd3fc",
    };
    const odylithChartState = {
      hydrated: false,
      instances: [],
      lastFingerprint: "",
      retryTimer: 0,
    };
    const odylithFallbackMarkup = new WeakMap();

    function readOdylithDrawerPayload() {
      return null;
    }

    function syncRecoveryDock() {
      const welcomeVisible = Boolean(welcomeState && !welcomeState.hidden);
      const upgradeVisible = Boolean(upgradeSpotlight && !upgradeSpotlight.hidden);
      const showWelcomeReopen = Boolean(welcomeReopen && welcomeLaunchpadActive && !welcomeVisible && !upgradeVisible);
      const showUpgradeReopen = Boolean(upgradeReopen && hasUpgradeSpotlight() && !upgradeVisible && !welcomeVisible);
      if (welcomeReopen) {
        welcomeReopen.hidden = !showWelcomeReopen;
        welcomeReopen.setAttribute("aria-hidden", String(!showWelcomeReopen));
        welcomeReopen.textContent = "Starter Guide";
      }
      if (upgradeReopen) {
        upgradeReopen.hidden = !showUpgradeReopen;
        upgradeReopen.setAttribute("aria-hidden", String(!showUpgradeReopen));
        upgradeReopen.textContent = upgradeSpotlightReopenLabel;
      }
      if (recoveryDock) {
        recoveryDock.hidden = !(showWelcomeReopen || showUpgradeReopen);
        recoveryDock.setAttribute("aria-hidden", String(recoveryDock.hidden));
      }
    }

    function setWelcomeHidden(hidden) {
      if (!welcomeState) return;
      const nextHidden = Boolean(hidden);
      welcomeState.hidden = nextHidden;
      welcomeState.setAttribute("aria-hidden", String(nextHidden));
      syncRecoveryDock();
    }

    function setWelcomeCopyStatus(message) {
      if (!welcomeCopyStatus) return;
      welcomeCopyStatus.textContent = String(message || "").trim();
    }

    function setUpgradeSpotlightHidden(hidden) {
      if (!upgradeSpotlight) return;
      const nextHidden = Boolean(hidden);
      upgradeSpotlight.hidden = nextHidden;
      upgradeSpotlight.setAttribute("aria-hidden", String(nextHidden));
      document.body.classList.toggle("shell-upgrade-spotlight-open", !nextHidden);
      syncRecoveryDock();
    }

    function eachBrowserStorage(visitor) {
      const areas = [];
      try {
        if (window.localStorage) {
          areas.push(window.localStorage);
        }
      } catch (_error) {
        // Ignore local storage failures in file-view shells.
      }
      try {
        if (window.sessionStorage) {
          areas.push(window.sessionStorage);
        }
      } catch (_error) {
        // Ignore session storage failures in stricter browser contexts.
      }
      areas.forEach((area) => {
        try {
          visitor(area);
        } catch (_error) {
          // Ignore individual storage area failures and try the next bucket.
        }
      });
    }

    function localStorageRead(key) {
      let value = null;
      eachBrowserStorage((area) => {
        if (value !== null) return;
        const nextValue = area.getItem(key);
        if (nextValue !== null) {
          value = nextValue;
        }
      });
      return value;
    }

    function localStorageWrite(key, value) {
      eachBrowserStorage((area) => {
        area.setItem(key, value);
      });
    }

    function runtimeStatusDismissed() {
      if (!runtimeStatusFingerprint) return false;
      return localStorageRead(runtimeStatusDismissStorageKey) === runtimeStatusFingerprint;
    }

    function setRuntimeStatusDismissed(dismissed) {
      localStorageWrite(runtimeStatusDismissStorageKey, dismissed && runtimeStatusFingerprint ? runtimeStatusFingerprint : "");
    }

    function syncRuntimeStatusLayout() {
      if (!viewport) return;
      if (!runtimeStatus || runtimeStatus.hidden) {
        viewport.style.setProperty("--runtime-status-offset", "0px");
        return;
      }
      const cardHeight = Math.ceil(runtimeStatus.getBoundingClientRect().height || 0);
      const slotOffset = cardHeight > 0 ? (cardHeight + 18) : 0;
      viewport.style.setProperty("--runtime-status-offset", `${slotOffset}px`);
    }

    function scheduleRuntimeStatusLayoutSync() {
      if (runtimeStatusLayoutFrame) {
        window.cancelAnimationFrame(runtimeStatusLayoutFrame);
      }
      runtimeStatusLayoutFrame = window.requestAnimationFrame(() => {
        runtimeStatusLayoutFrame = 0;
        syncRuntimeStatusLayout();
      });
    }

    function welcomeDismissed() {
      return localStorageRead(welcomeDismissStorageKey) === "1";
    }

    function setWelcomeDismissed(dismissed) {
      localStorageWrite(welcomeDismissStorageKey, dismissed ? "1" : "0");
    }

    function upgradeSpotlightDismissed() {
      if (!hasUpgradeSpotlight()) return true;
      if (!upgradeSpotlightDismissStorageKey) return false;
      return localStorageRead(upgradeSpotlightDismissStorageKey) === "1";
    }

    function setUpgradeSpotlightDismissed(dismissed) {
      if (!upgradeSpotlightDismissStorageKey) return;
      localStorageWrite(upgradeSpotlightDismissStorageKey, dismissed ? "1" : "0");
    }

    function expireUpgradeSpotlightWindow() {
      if (!upgradeSpotlightActive) return;
      upgradeSpotlightActive = false;
      setUpgradeSpotlightHidden(true);
      if (welcomeLaunchpadActive && !welcomeDismissed()) {
        setWelcomeHidden(false);
      } else {
        syncRecoveryDock();
      }
    }

    function scheduleUpgradeSpotlightExpiry() {
      if (!hasUpgradeSpotlight() || !upgradeSpotlightExpiresAtMs) return;
      const delayMs = upgradeSpotlightExpiresAtMs - Date.now();
      if (delayMs <= 0) {
        expireUpgradeSpotlightWindow();
        return;
      }
      window.setTimeout(expireUpgradeSpotlightWindow, delayMs);
    }

    function dismissUpgradeSpotlight() {
      setUpgradeSpotlightDismissed(true);
      setUpgradeSpotlightHidden(true);
      if (upgradeReopen && !upgradeReopen.hidden) {
        window.requestAnimationFrame(() => {
          upgradeReopen.focus();
        });
      }
    }

    function reopenUpgradeSpotlight() {
      if (!hasUpgradeSpotlight()) return;
      setUpgradeSpotlightDismissed(false);
      setUpgradeSpotlightHidden(false);
      if (upgradeSpotlightDismiss) {
        window.requestAnimationFrame(() => {
          upgradeSpotlightDismiss.focus();
        });
      }
    }

    function welcomeTaskStorageKey(taskId) {
      return `${welcomeTaskStoragePrefix}${String(taskId || "").trim().toLowerCase()}`;
    }

    function findWelcomeTaskCard(taskId) {
      const normalized = String(taskId || "").trim().toLowerCase();
      if (!normalized) return null;
      return welcomeTaskCards.find((card) => String(card.dataset.welcomeTask || "").trim().toLowerCase() === normalized) || null;
    }

    function findWelcomeTaskButtons(taskId) {
      const normalized = String(taskId || "").trim().toLowerCase();
      if (!normalized) return [];
      return welcomeTaskDoneButtons.filter((button) => String(button.dataset.welcomeTaskDone || "").trim().toLowerCase() === normalized);
    }

    function setWelcomeTaskComplete(taskId, complete) {
      const normalized = String(taskId || "").trim().toLowerCase();
      if (!normalized) return;
      const nextComplete = Boolean(complete);
      const card = findWelcomeTaskCard(normalized);
      if (card) {
        card.classList.toggle("is-complete", nextComplete);
      }
      findWelcomeTaskButtons(normalized).forEach((button) => {
        button.textContent = nextComplete ? "Done" : "Mark done";
        button.setAttribute("aria-pressed", String(nextComplete));
      });
      localStorageWrite(welcomeTaskStorageKey(normalized), nextComplete ? "1" : "0");
    }

    function initializeWelcomeTaskState() {
      welcomeTaskCards.forEach((card) => {
        const taskId = String(card.dataset.welcomeTask || "").trim().toLowerCase();
        if (!taskId) return;
        const complete = localStorageRead(welcomeTaskStorageKey(taskId)) === "1";
        setWelcomeTaskComplete(taskId, complete);
      });
    }

    function buildShellRefreshFingerprint(rawPayload) {
      if (!rawPayload || typeof rawPayload !== "object") return "";
      const fingerprintPayload = {};
      for (const [key, value] of Object.entries(rawPayload)) {
        if (key === "generated_utc" || key === "generated_local_date" || key === "generated_local_time") {
          continue;
        }
        fingerprintPayload[key] = value;
      }
      try {
        return JSON.stringify(fingerprintPayload);
      } catch (_error) {
        return "";
      }
    }

    function scheduleShellRefreshPoll(delayMs = 4000) {
      if (!payloadScript || !payloadScript.src || (!shellPayloadGeneratedUtc && !shellPayloadRefreshFingerprint)) return;
      if (shellRefreshTimer) {
        window.clearTimeout(shellRefreshTimer);
      }
      shellRefreshTimer = window.setTimeout(checkForShellRefresh, delayMs);
    }

    function checkForShellRefresh() {
      if (!payloadScript || !payloadScript.src || (!shellPayloadGeneratedUtc && !shellPayloadRefreshFingerprint)) return;
      if (shellRefreshInFlight) return;
      if (document.hidden) {
        scheduleShellRefreshPoll(4000);
        return;
      }
      shellRefreshInFlight = true;
      const previousPayload = window[shellPayloadGlobalName];
      const refreshProbe = document.createElement("script");
      const separator = payloadScript.src.includes("?") ? "&" : "?";
      refreshProbe.async = true;
      refreshProbe.src = `${payloadScript.src}${separator}refresh=${Date.now()}`;
      refreshProbe.onload = () => {
        shellRefreshInFlight = false;
        const nextPayload = window[shellPayloadGlobalName];
        const nextGeneratedUtc = nextPayload && typeof nextPayload === "object"
          ? String(nextPayload.generated_utc || "").trim()
          : "";
        const nextFingerprint = buildShellRefreshFingerprint(nextPayload);
        refreshProbe.remove();
        window[shellPayloadGlobalName] = previousPayload || {};
        if (
          (nextGeneratedUtc && nextGeneratedUtc !== shellPayloadGeneratedUtc)
          || (nextFingerprint && nextFingerprint !== shellPayloadRefreshFingerprint)
        ) {
          window.location.reload();
          return;
        }
        scheduleShellRefreshPoll(4000);
      };
      refreshProbe.onerror = () => {
        shellRefreshInFlight = false;
        refreshProbe.remove();
        window[shellPayloadGlobalName] = previousPayload || {};
        scheduleShellRefreshPoll(8000);
      };
      document.head.appendChild(refreshProbe);
    }

    function liveRefreshEnabled() {
      return Boolean(
        liveRefreshPayload
        && liveRefreshPayload.enabled
        && String(liveRefreshPayload.state_href || "").trim()
      );
    }

    function liveRefreshPollIntervalMs() {
      if (!liveRefreshPayload) return 20000;
      const parsed = Number.parseInt(String(liveRefreshPayload.poll_interval_ms || ""), 10);
      return Number.isFinite(parsed) && parsed >= 5000 ? parsed : 20000;
    }

    function liveRefreshWorktree() {
      return liveRefreshPayload && liveRefreshPayload.worktree && typeof liveRefreshPayload.worktree === "object"
        ? liveRefreshPayload.worktree
        : null;
    }

    function liveRefreshSurfacePolicies() {
      return liveRefreshPayload && liveRefreshPayload.surface_policies && typeof liveRefreshPayload.surface_policies === "object"
        ? liveRefreshPayload.surface_policies
        : {};
    }

    function liveRefreshSurfacePolicy(tab) {
      const token = String(tab || "").trim().toLowerCase();
      const policies = liveRefreshSurfacePolicies();
      return token && policies && typeof policies[token] === "object"
        ? policies[token]
        : null;
    }

    function liveRefreshAutoReloadIdleDebounceMs() {
      if (!liveRefreshPayload) return 3000;
      const parsed = Number.parseInt(String(liveRefreshPayload.auto_reload_idle_debounce_ms || ""), 10);
      return Number.isFinite(parsed) && parsed >= 0 ? parsed : 3000;
    }

    function liveRefreshAutoReloadMinIntervalMs() {
      if (!liveRefreshPayload) return 45000;
      const parsed = Number.parseInt(String(liveRefreshPayload.auto_reload_min_interval_ms || ""), 10);
      return Number.isFinite(parsed) && parsed >= 1000 ? parsed : 45000;
    }

    function liveRefreshPolicyId() {
      return liveRefreshPayload ? String(liveRefreshPayload.policy_id || "").trim() : "";
    }

    function runtimeSurfaceAutoReloadEnabled(tab) {
      const policy = liveRefreshSurfacePolicy(tab);
      return Boolean(policy && policy.auto_reload);
    }

    function runtimeStateUpdatedProjections(runtimeState) {
      if (!runtimeState || typeof runtimeState !== "object" || !Array.isArray(runtimeState.updated_projections)) {
        return [];
      }
      return runtimeState.updated_projections
        .map((token) => String(token || "").trim().toLowerCase())
        .filter(Boolean);
    }

    function buildRuntimeStateFingerprint(runtimeState) {
      if (!runtimeState || typeof runtimeState !== "object") return "";
      const fingerprintPayload = {
        updated_utc: String(runtimeState.updated_utc || "").trim(),
        projection_fingerprint: String(runtimeState.projection_fingerprint || "").trim(),
        projection_scope: String(runtimeState.projection_scope || "").trim(),
        updated_projections: Array.isArray(runtimeState.updated_projections) ? runtimeState.updated_projections : [],
      };
      try {
        return JSON.stringify(fingerprintPayload);
      } catch (_error) {
        return "";
      }
    }

    function buildRuntimeStatusFingerprint(posture) {
      if (!posture || typeof posture !== "object") return "";
      const fingerprintPayload = {
        kicker: String(posture.kicker || "").trim(),
        title: String(posture.title || "").trim(),
        body: String(posture.body || "").trim(),
        meta: String(posture.meta || "").trim(),
        tone: String(posture.tone || "").trim(),
        show_reload: Boolean(posture.showReload),
        reload_label: String(posture.reloadLabel || "").trim(),
      };
      try {
        return JSON.stringify(fingerprintPayload);
      } catch (_error) {
        return "";
      }
    }

    function runtimeReloadableForTab(tab) {
      if (!liveRefreshPayload || !Array.isArray(liveRefreshPayload.reloadable_tabs)) return false;
      return liveRefreshPayload.reloadable_tabs.includes(String(tab || "").trim().toLowerCase());
    }

    function runtimeStateAffectsTab(tab, runtimeState) {
      const policy = liveRefreshSurfacePolicy(tab);
      if (!policy) return false;
      const projectionKeys = Array.isArray(policy.projection_keys)
        ? policy.projection_keys.map((token) => String(token || "").trim().toLowerCase()).filter(Boolean)
        : [];
      if (!projectionKeys.length) return true;
      const updated = new Set(runtimeStateUpdatedProjections(runtimeState));
      if (!updated.size) return false;
      return projectionKeys.some((token) => updated.has(token));
    }

    function runtimeAutoReloadReadyForTab(tab) {
      if (!runtimeSurfaceAutoReloadEnabled(tab)) return false;
      const now = Date.now();
      if (document.hidden) return false;
      if ((now - lastUserInteractionAtMs) < liveRefreshAutoReloadIdleDebounceMs()) return false;
      const lastReloadAt = Number(runtimeAutoReloadAtByTab[String(tab || "").trim().toLowerCase()] || 0);
      if ((now - lastReloadAt) < liveRefreshAutoReloadMinIntervalMs()) return false;
      return true;
    }

    function recordUserInteraction() {
      lastUserInteractionAtMs = Date.now();
    }

    function buildRuntimeStatusPosture(runtimeState) {
      const fallbackPosture = {
        visible: false,
        tone: "",
        kicker: "",
        title: "",
        body: "",
        meta: "",
        showReload: false,
        reloadLabel: "",
      };
      const current = readStateFromUrl();
      const currentTab = current && typeof current === "object"
        ? String(current.tab || "").trim().toLowerCase()
        : "";
      if (!currentTab) return fallbackPosture;
      const surfaceRuntimeStatus = runtimeState && runtimeState.surface_runtime_status && typeof runtimeState.surface_runtime_status === "object"
        ? runtimeState.surface_runtime_status
        : initialSurfaceRuntimeStatus;
      const rawPosture = surfaceRuntimeStatus[currentTab];
      if (!rawPosture || typeof rawPosture !== "object") {
        return fallbackPosture;
      }
      return {
        visible: Boolean(rawPosture.visible),
        tone: String(rawPosture.tone || "").trim(),
        kicker: String(rawPosture.kicker || "").trim(),
        title: String(rawPosture.title || "").trim(),
        body: String(rawPosture.body || "").trim(),
        meta: String(rawPosture.meta || "").trim(),
        showReload: Boolean(rawPosture.showReload),
        reloadLabel: String(rawPosture.reloadLabel || "").trim(),
      };
    }

    function mergeRuntimeStatusState(runtimeState) {
      const baseState = runtimeState && typeof runtimeState === "object"
        ? { ...runtimeState }
        : {};
      if (!baseState.surface_runtime_status || typeof baseState.surface_runtime_status !== "object") {
        baseState.surface_runtime_status = initialSurfaceRuntimeStatus;
      }
      return baseState;
    }

    function applyRuntimeStatus(runtimeState) {
      if (!runtimeStatus || !runtimeStatusTitle || !runtimeStatusBody || !runtimeStatusMeta || !runtimeStatusReload || !runtimeStatusDismiss) {
        return;
      }
      latestRuntimeStatusState = mergeRuntimeStatusState(runtimeState);
      const posture = buildRuntimeStatusPosture(runtimeState);
      runtimeStatusFingerprint = posture.visible ? buildRuntimeStatusFingerprint(posture) : "";
      const dismissed = runtimeStatusDismissed();
      const visible = Boolean(posture.visible && !dismissed);
      runtimeStatus.hidden = !visible;
      runtimeStatus.setAttribute("aria-hidden", String(!visible));
      runtimeStatus.dataset.tone = visible ? String(posture.tone || "info") : "";
      if (runtimeStatusKicker) {
        runtimeStatusKicker.textContent = visible ? String(posture.kicker || "").trim() : "";
        runtimeStatusKicker.hidden = !(visible && String(posture.kicker || "").trim());
      }
      runtimeStatusTitle.textContent = visible ? String(posture.title || "").trim() : "";
      runtimeStatusBody.textContent = visible ? String(posture.body || "").trim() : "";
      runtimeStatusMeta.textContent = visible ? String(posture.meta || "").trim() : "";
      runtimeStatusMeta.hidden = !(visible && String(posture.meta || "").trim());
      runtimeStatusReload.hidden = !(visible && posture.showReload);
      runtimeStatusReload.setAttribute("aria-hidden", String(runtimeStatusReload.hidden));
      runtimeStatusReload.textContent = visible && posture.showReload
        ? String(posture.reloadLabel || "Reload view").trim()
        : "Reload view";
      runtimeStatusDismiss.hidden = !visible;
      runtimeStatusDismiss.setAttribute("aria-hidden", String(runtimeStatusDismiss.hidden));
      syncRecoveryDock();
      scheduleRuntimeStatusLayoutSync();
    }

    function scheduleRuntimeProbe(delayMs = liveRefreshPollIntervalMs()) {
      if (!liveRefreshEnabled()) return;
      if (runtimeProbeTimer) {
        window.clearTimeout(runtimeProbeTimer);
      }
      runtimeProbeTimer = window.setTimeout(checkForRuntimeProbe, delayMs);
    }

    function checkForRuntimeProbe() {
      if (!liveRefreshEnabled()) return;
      if (runtimeProbeInFlight) return;
      if (document.hidden) {
        scheduleRuntimeProbe(liveRefreshPollIntervalMs());
        return;
      }
      runtimeProbeInFlight = true;
      const previousPayload = window[runtimeProbeStateGlobalName];
      const refreshProbe = document.createElement("script");
      const sourceHref = String(liveRefreshPayload.state_href || "").trim();
      const separator = sourceHref.includes("?") ? "&" : "?";
      refreshProbe.async = true;
      refreshProbe.src = `${sourceHref}${separator}refresh=${Date.now()}`;
      refreshProbe.onload = () => {
        runtimeProbeInFlight = false;
        const nextPayload = mergeRuntimeStatusState(window[runtimeProbeStateGlobalName]);
        const nextFingerprint = buildRuntimeStateFingerprint(nextPayload);
        const priorFingerprint = runtimeProbeFingerprint;
        const hadFingerprint = Boolean(runtimeProbeFingerprint);
        refreshProbe.remove();
        window[runtimeProbeStateGlobalName] = previousPayload || {};
        if (nextFingerprint && nextFingerprint !== runtimeProbeFingerprint) {
          runtimeProbeFingerprint = nextFingerprint;
        }
        applyRuntimeStatus(nextPayload);
        if (hadFingerprint && nextFingerprint && nextFingerprint !== priorFingerprint) {
          const current = readStateFromUrl();
          if (runtimeStateAffectsTab(current.tab, nextPayload) && runtimeAutoReloadReadyForTab(current.tab)) {
            runtimeAutoReloadAtByTab[String(current.tab || "").trim().toLowerCase()] = Date.now();
            reloadActiveView();
          }
        }
        scheduleRuntimeProbe(liveRefreshPollIntervalMs());
      };
      refreshProbe.onerror = () => {
        runtimeProbeInFlight = false;
        refreshProbe.remove();
        window[runtimeProbeStateGlobalName] = previousPayload || {};
        scheduleRuntimeProbe(liveRefreshPollIntervalMs() * 2);
      };
      document.head.appendChild(refreshProbe);
    }

    async function copyText(text) {
      const token = String(text || "");
      if (!token) return false;
      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(token);
          return true;
        } catch (_error) {
          // Fall through to the textarea fallback.
        }
      }
      const helper = document.createElement("textarea");
      helper.value = token;
      helper.setAttribute("readonly", "readonly");
      helper.style.position = "fixed";
      helper.style.top = "-9999px";
      helper.style.opacity = "0";
      document.body.appendChild(helper);
      helper.select();
      helper.setSelectionRange(0, helper.value.length);
      let copied = false;
      try {
        copied = document.execCommand("copy");
      } catch (_error) {
        copied = false;
      }
      document.body.removeChild(helper);
      return copied;
    }

    function odylithSparkLabels(value, fallbackPrefix) {
      if (!Array.isArray(value) || !value.length) return [`${fallbackPrefix}1`];
      return value.map((item, index) => {
        const token = String(item || "").trim();
        return token || `${fallbackPrefix}${index + 1}`;
      });
    }

    function odylithNumericSeries(value, fallback = [0]) {
      if (!Array.isArray(value) || !value.length) return fallback.slice();
      return value.map((item) => {
        if (item === null || item === undefined || item === "") return null;
        const numeric = Number(item);
        return Number.isFinite(numeric) ? numeric : null;
      });
    }

    function odylithChartFingerprint(drawer) {
      if (!drawer || typeof drawer !== "object") return "none";
      try {
        return JSON.stringify(drawer.charts || {});
      } catch (_error) {
        return String(drawer.snapshot_time || "unknown");
      }
    }

    function clearOdylithCharts() {
      if (odylithChartState.retryTimer) {
        window.clearTimeout(odylithChartState.retryTimer);
        odylithChartState.retryTimer = 0;
      }
      odylithChartState.instances.forEach((chart) => {
        try {
          chart.dispose();
        } catch (_error) {
          // no-op
        }
      });
      document.querySelectorAll(".odylith-chart-canvas").forEach((element) => {
        const fallbackMarkup = odylithFallbackMarkup.get(element);
        if (typeof fallbackMarkup === "string" && fallbackMarkup) {
          element.innerHTML = fallbackMarkup;
          element.dataset.odylithChartState = "fallback";
        }
      });
      odylithChartState.instances = [];
      odylithChartState.hydrated = false;
    }

    function ensureOdylithChartPlaceholder(element, message) {
      if (!element) return;
      element.innerHTML = `<div class="odylith-chart-empty">${message}</div>`;
      element.dataset.odylithChartState = "placeholder";
    }

    function captureOdylithFallback(element) {
      if (!element || odylithFallbackMarkup.has(element)) return;
      odylithFallbackMarkup.set(element, element.innerHTML || "");
    }

    function restoreOdylithFallback(element) {
      if (!element) return;
      const fallbackMarkup = odylithFallbackMarkup.get(element);
      if (typeof fallbackMarkup === "string" && fallbackMarkup) {
        element.innerHTML = fallbackMarkup;
        element.dataset.odylithChartState = "fallback";
      }
    }

    function odylithBaseChartOption() {
      return {
        animationDuration: 360,
        animationDurationUpdate: 240,
        animationEasing: "cubicOut",
        animationEasingUpdate: "cubicOut",
        textStyle: {
          color: ODYLITH_CHART_TEXT,
          fontFamily: '"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
        },
        grid: {
          top: 40,
          left: 42,
          right: 22,
          bottom: 34,
          containLabel: false,
        },
        tooltip: {
          trigger: "axis",
          backgroundColor: "rgba(255, 255, 255, 0.97)",
          borderColor: "rgba(125, 159, 214, 0.4)",
          borderWidth: 1,
          textStyle: {
            color: ODYLITH_CHART_TEXT,
            fontSize: 11,
          },
          axisPointer: {
            lineStyle: { color: "rgba(96, 165, 250, 0.42)", width: 1 },
          },
          extraCssText: "box-shadow: 0 16px 28px rgba(31,56,94,0.12); border-radius: 12px; backdrop-filter: blur(6px);",
        },
        legend: {
          top: 2,
          itemWidth: 8,
          itemHeight: 8,
          itemGap: 12,
          textStyle: {
            color: ODYLITH_AXIS_TEXT,
            fontSize: 10,
            fontWeight: 600,
          },
        },
        xAxis: {
          type: "category",
          boundaryGap: false,
          axisLine: { lineStyle: { color: ODYLITH_GRID_LINE } },
          axisLabel: { color: ODYLITH_AXIS_TEXT, fontSize: 10, hideOverlap: true },
          splitLine: { show: false },
        },
        yAxis: {
          type: "value",
          axisLine: { show: false },
          axisLabel: { color: ODYLITH_AXIS_TEXT, fontSize: 10 },
          splitLine: { lineStyle: { color: ODYLITH_GRID_LINE } },
        },
      };
    }

    function odylithLineSeries(name, data, color, extra = {}) {
      return {
        name,
        type: "line",
        smooth: 0.26,
        symbol: "circle",
        symbolSize: 6,
        connectNulls: false,
        lineStyle: { width: 2, color },
        itemStyle: { color, borderColor: "#ffffff", borderWidth: 2 },
        emphasis: { focus: "series" },
        areaStyle: extra.area
          ? {
              color: new window.echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: `${color}${extra.areaAlpha || "30"}` },
                { offset: 1, color: "rgba(255,255,255,0)" },
              ]),
            }
          : undefined,
        data,
        ...extra,
      };
    }

    function odylithScoreFill(value) {
      const numeric = Number(value) || 0;
      if (numeric >= 80) return "#2dd4bf";
      if (numeric >= 60) return "#60a5fa";
      if (numeric >= 40) return "#f59e0b";
      return "#fb7185";
    }

    function odylithCompactInteger(value) {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) return "0";
      return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(numeric);
    }

    function odylithSignedDelta(value, suffix = "") {
      const numeric = Number(value);
      if (!Number.isFinite(numeric) || numeric === 0) return "";
      const rounded = Math.round(numeric);
      return `${rounded > 0 ? "+" : ""}${rounded}${suffix}`;
    }

    function buildControlStorySnapshotOption(chart) {
      const detail = chart && typeof chart.detail === "object" ? chart.detail : {};
      const rows = [
        ["Budget fit", Number(detail.budget_fit) || 0, ODYLITH_CHART_PALETTE.budget],
        ["Utility", Number(detail.utility) || 0, ODYLITH_CHART_PALETTE.utility],
        ["Alignment", Number(detail.alignment) || 0, ODYLITH_CHART_PALETTE.learningPacket],
        ["Yield", Number(detail.yield) || 0, ODYLITH_CHART_PALETTE.learningAlignment],
        ["Route ready", Number(detail.route_ready) || 0, ODYLITH_CHART_PALETTE.routeReady],
      ];
      const meta = [
        String(detail.recorded_at || "").trim(),
        String(detail.workstream || "").trim() ? `WS ${String(detail.workstream).trim()}` : "",
        String(detail.session_id || "").trim() ? `Session ${String(detail.session_id).trim()}` : "",
      ].filter(Boolean).join(" · ") || "Single routed slice available.";
      return {
        animationDuration: 360,
        animationDurationUpdate: 240,
        animationEasing: "cubicOut",
        animationEasingUpdate: "cubicOut",
        textStyle: {
          color: ODYLITH_CHART_TEXT,
          fontFamily: '"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
        },
        grid: {
          top: 86,
          left: 104,
          right: 20,
          bottom: 18,
          containLabel: false,
        },
        tooltip: {
          trigger: "item",
          backgroundColor: "rgba(255, 255, 255, 0.97)",
          borderColor: "rgba(125, 159, 214, 0.4)",
          borderWidth: 1,
          textStyle: { color: ODYLITH_CHART_TEXT, fontSize: 11 },
          extraCssText: "box-shadow: 0 16px 28px rgba(31,56,94,0.12); border-radius: 12px;",
          formatter: (params) => `${params.name}: ${Math.round(Number(params.value) || 0)}%`,
        },
        graphic: [
          {
            type: "text",
            left: 10,
            top: 8,
            silent: true,
            style: {
              text: `${odylithCompactInteger(detail.tokens)} tokens`,
              fill: ODYLITH_CHART_TEXT,
              font: '700 18px "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
            },
          },
          {
            type: "text",
            left: 10,
            top: 32,
            silent: true,
            style: {
              text: `${String(detail.label || "Latest")} · ${String(detail.budget_state || "Budget unknown")} · ${String(detail.state || "Unknown")}`,
              fill: ODYLITH_AXIS_TEXT,
              font: '600 10px "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
            },
          },
          {
            type: "text",
            left: 10,
            top: 48,
            silent: true,
            style: {
              text: meta,
              fill: ODYLITH_AXIS_TEXT,
              font: '500 10px "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
            },
          },
        ],
        xAxis: {
          type: "value",
          min: 0,
          max: 100,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: ODYLITH_AXIS_TEXT, fontSize: 10 },
          splitLine: { lineStyle: { color: ODYLITH_GRID_LINE } },
        },
        yAxis: {
          type: "category",
          inverse: true,
          data: rows.map((row) => row[0]),
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            color: ODYLITH_AXIS_TEXT,
            fontSize: 10,
            width: 88,
            overflow: "truncate",
          },
        },
        series: [
          {
            type: "bar",
            data: rows.map((row) => row[1]),
            barWidth: 12,
            showBackground: true,
            backgroundStyle: { color: "rgba(191, 219, 254, 0.18)", borderRadius: 999 },
            label: {
              show: true,
              position: "right",
              color: ODYLITH_CHART_TEXT,
              fontSize: 10,
              fontWeight: 700,
              formatter: (params) => `${Math.round(Number(params.value) || 0)}%`,
            },
            itemStyle: {
              borderRadius: [0, 6, 6, 0],
              color: (params) => rows[params.dataIndex][2],
            },
            emphasis: { focus: "series" },
          },
        ],
      };
    }

    function buildControlStoryLollipopOption(chart) {
      const base = odylithBaseChartOption();
      const labels = odylithSparkLabels(chart.labels, "P");
      const detail = chart && typeof chart.detail === "object" ? chart.detail : {};
      const latestSpend = `${odylithCompactInteger(detail.tokens)} tokens`;
      const tokenDelta = odylithSignedDelta(detail.token_delta, " tokens");
      const spendNote = tokenDelta ? `Latest spend ${latestSpend} (${tokenDelta} vs prior).` : `Latest spend ${latestSpend}.`;
      return {
        ...base,
        grid: { ...base.grid, top: 56, right: 24, bottom: 30 },
        xAxis: { ...base.xAxis, data: labels, boundaryGap: true },
        yAxis: {
          ...base.yAxis,
          min: 0,
          max: 100,
          name: "Signal",
          nameTextStyle: { color: ODYLITH_AXIS_TEXT, fontSize: 10, padding: [0, 0, 0, 6] },
        },
        graphic: [
          {
            type: "text",
            right: 10,
            top: 8,
            silent: true,
            style: {
              text: spendNote,
              fill: ODYLITH_AXIS_TEXT,
              font: '600 10px "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
            },
          },
        ],
        series: [
          odylithLineSeries("Utility", odylithNumericSeries(chart.utility, [0]), ODYLITH_CHART_PALETTE.utility, {
            smooth: false,
            symbolSize: 8,
            lineStyle: { width: 1.6, color: ODYLITH_CHART_PALETTE.utility },
            z: 4,
            markLine: {
              symbol: "none",
              silent: true,
              label: {
                color: ODYLITH_AXIS_TEXT,
                fontSize: 9,
                formatter: "operator floor",
              },
              lineStyle: {
                color: "rgba(37, 99, 235, 0.24)",
                type: "dashed",
              },
              data: [{ yAxis: 70 }],
            },
          }),
          odylithLineSeries("Alignment", odylithNumericSeries(chart.alignment, [0]), ODYLITH_CHART_PALETTE.learningPacket, {
            smooth: false,
            symbolSize: 8,
            lineStyle: { width: 1.6, color: ODYLITH_CHART_PALETTE.learningPacket },
            z: 5,
          }),
          odylithLineSeries("Yield", odylithNumericSeries(chart.yield, [0]), ODYLITH_CHART_PALETTE.learningAlignment, {
            smooth: false,
            symbolSize: 8,
            lineStyle: { width: 1.6, color: ODYLITH_CHART_PALETTE.learningAlignment },
            z: 5,
          }),
          odylithLineSeries("Route ready", odylithNumericSeries(chart.route_ready, [0]), ODYLITH_CHART_PALETTE.routeReady, {
            smooth: false,
            z: 4,
            lineStyle: { width: 1.75, color: ODYLITH_CHART_PALETTE.routeReady, type: "dashed" },
            symbolSize: 7,
          }),
        ],
      };
    }

    function buildControlStoryTrendOption(chart) {
      const base = odylithBaseChartOption();
      const labels = odylithSparkLabels(chart.labels, "P");
      const tokens = odylithNumericSeries(chart.tokens, [0]).map((value) => value ?? 0);
      const tokenMax = Math.max(1000, ...tokens, 0);
      return {
        ...base,
        axisPointer: {
          link: [{ xAxisIndex: [0, 1] }],
        },
        legend: {
          ...base.legend,
          top: 4,
        },
        tooltip: {
          trigger: "axis",
          axisPointer: {
            type: "line",
            lineStyle: { color: "rgba(96, 165, 250, 0.38)", width: 1 },
          },
          backgroundColor: "rgba(255, 255, 255, 0.97)",
          borderColor: "rgba(125, 159, 214, 0.4)",
          borderWidth: 1,
          textStyle: {
            color: ODYLITH_CHART_TEXT,
            fontSize: 11,
          },
          extraCssText: "box-shadow: 0 16px 28px rgba(31,56,94,0.12); border-radius: 12px; backdrop-filter: blur(6px);",
          formatter: (params) => {
            const rows = (Array.isArray(params) ? params : [params]).filter(Boolean);
            const axisLabel = rows.find((row) => String(row.axisValueLabel || "").trim())?.axisValueLabel || "";
            const order = ["Tokens", "Utility", "Alignment", "Yield", "Route ready"];
            rows.sort((left, right) => order.indexOf(left.seriesName) - order.indexOf(right.seriesName));
            const body = rows.map((row) => {
              const value = Array.isArray(row.value) ? row.value[row.value.length - 1] : row.value;
              const numeric = Number(value);
              const formattedValue = row.seriesName === "Tokens"
                ? `${odylithCompactInteger(numeric)} tokens`
                : `${Math.round(Number.isFinite(numeric) ? numeric : 0)}%`;
              return `${row.marker}${row.seriesName}: ${formattedValue}`;
            }).join("<br/>");
            return `${axisLabel ? `<strong>${axisLabel}</strong><br/>` : ""}${body}`;
          },
        },
        grid: [
          { top: 56, left: 44, right: 18, height: 74, containLabel: false },
          { top: 156, left: 44, right: 18, height: 66, containLabel: false },
        ],
        xAxis: [
          {
            ...base.xAxis,
            gridIndex: 0,
            data: labels,
            boundaryGap: true,
            axisTick: { show: false },
            axisLabel: { show: false },
          },
          {
            ...base.xAxis,
            gridIndex: 1,
            data: labels,
            boundaryGap: true,
            axisTick: { show: false },
            axisLabel: { color: ODYLITH_AXIS_TEXT, fontSize: 10, hideOverlap: true },
          },
        ],
        yAxis: [
          {
            ...base.yAxis,
            gridIndex: 0,
            min: 0,
            max: Math.ceil(tokenMax / 500) * 500,
            name: "Tokens",
            nameTextStyle: { color: ODYLITH_AXIS_TEXT, fontSize: 10, padding: [0, 0, 0, 4] },
          },
          {
            ...base.yAxis,
            gridIndex: 1,
            min: 0,
            max: 100,
            name: "Signal",
            axisLabel: { color: ODYLITH_AXIS_TEXT, fontSize: 10 },
            nameTextStyle: { color: ODYLITH_AXIS_TEXT, fontSize: 10, padding: [0, 0, 0, 6] },
          },
        ],
        graphic: [
          {
            type: "text",
            left: 44,
            top: 40,
            silent: true,
            style: {
              text: "Spend",
              fill: ODYLITH_AXIS_TEXT,
              font: '700 10px "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
            },
          },
          {
            type: "text",
            left: 44,
            top: 140,
            silent: true,
            style: {
              text: "Outcome signals",
              fill: ODYLITH_AXIS_TEXT,
              font: '700 10px "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
            },
          },
        ],
        series: [
          {
            name: "Tokens",
            type: "bar",
            xAxisIndex: 0,
            yAxisIndex: 0,
            barMaxWidth: 18,
            itemStyle: {
              color: new window.echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "#fb7185" },
                { offset: 1, color: "#fda4af" },
              ]),
              borderRadius: [7, 7, 0, 0],
            },
            emphasis: { focus: "series" },
            data: tokens,
          },
          odylithLineSeries("Utility", odylithNumericSeries(chart.utility, [0]), ODYLITH_CHART_PALETTE.utility, {
            xAxisIndex: 1,
            yAxisIndex: 1,
            smooth: 0.22,
            symbolSize: 5,
            lineStyle: { width: 2, color: ODYLITH_CHART_PALETTE.utility },
            z: 4,
            markLine: {
              symbol: "none",
              silent: true,
              label: {
                color: ODYLITH_AXIS_TEXT,
                fontSize: 9,
                formatter: "useful range",
              },
              lineStyle: {
                color: "rgba(37, 99, 235, 0.24)",
                type: "dashed",
              },
              data: [{ yAxis: 70 }],
            },
          }),
          odylithLineSeries("Alignment", odylithNumericSeries(chart.alignment, [0]), ODYLITH_CHART_PALETTE.learningPacket, {
            xAxisIndex: 1,
            yAxisIndex: 1,
            smooth: false,
            step: "middle",
            symbolSize: 5,
            lineStyle: { width: 1.85, color: ODYLITH_CHART_PALETTE.learningPacket },
            z: 5,
          }),
          odylithLineSeries("Yield", odylithNumericSeries(chart.yield, [0]), ODYLITH_CHART_PALETTE.learningAlignment, {
            xAxisIndex: 1,
            yAxisIndex: 1,
            smooth: false,
            symbolSize: 5,
            lineStyle: { width: 1.85, color: ODYLITH_CHART_PALETTE.learningAlignment },
            z: 5,
          }),
          odylithLineSeries("Route ready", odylithNumericSeries(chart.route_ready, [0]), ODYLITH_CHART_PALETTE.routeReady, {
            xAxisIndex: 1,
            yAxisIndex: 1,
            z: 4,
            lineStyle: { width: 1.75, color: ODYLITH_CHART_PALETTE.routeReady, type: "dashed" },
            symbolSize: 5,
          }),
        ],
      };
    }

    function buildControlStoryOption(drawer) {
      const chart = drawer && drawer.charts && typeof drawer.charts.control_story === "object"
        ? drawer.charts.control_story
        : {};
      const sampleCount = Number(chart.sample_count) || (Array.isArray(chart.labels) ? chart.labels.length : 0);
      const mode = String(chart.mode || "").trim() || (sampleCount <= 1 ? "snapshot" : sampleCount <= 3 ? "lollipop" : "trend");
      if (mode === "snapshot") return buildControlStorySnapshotOption(chart);
      if (mode === "lollipop") return buildControlStoryLollipopOption(chart);
      return buildControlStoryTrendOption(chart);
    }

    function buildExecutionFlowOption(drawer) {
      const chart = drawer && drawer.charts && typeof drawer.charts.execution_flow === "object"
        ? drawer.charts.execution_flow
        : {};
      const labels = odylithSparkLabels(chart.labels, "L");
      const values = odylithNumericSeries(chart.values, [0]).map((value) => value ?? 0);
      return {
        animationDuration: 360,
        animationDurationUpdate: 240,
        animationEasing: "cubicOut",
        animationEasingUpdate: "cubicOut",
        textStyle: {
          color: ODYLITH_CHART_TEXT,
          fontFamily: '"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
        },
        grid: {
          top: 34,
          left: 122,
          right: 24,
          bottom: 18,
          containLabel: false,
        },
        tooltip: {
          trigger: "item",
          backgroundColor: "rgba(255, 255, 255, 0.97)",
          borderColor: "rgba(125, 159, 214, 0.4)",
          borderWidth: 1,
          textStyle: { color: ODYLITH_CHART_TEXT, fontSize: 11 },
          extraCssText: "box-shadow: 0 16px 28px rgba(31,56,94,0.12); border-radius: 12px;",
        },
        graphic: chart.source
          ? [
              {
                type: "text",
                right: 10,
                top: 6,
                silent: true,
                style: {
                  text: String(chart.source),
                  fill: ODYLITH_AXIS_TEXT,
                  font: '600 10px "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
                },
              },
            ]
          : [],
        xAxis: {
          type: "value",
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: ODYLITH_AXIS_TEXT, fontSize: 10 },
          splitLine: { lineStyle: { color: ODYLITH_GRID_LINE } },
        },
        yAxis: {
          type: "category",
          inverse: true,
          data: labels,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            color: ODYLITH_AXIS_TEXT,
            fontSize: 10,
            width: 108,
            overflow: "truncate",
          },
        },
        series: [
          {
            type: "bar",
            barWidth: 14,
            roundCap: true,
            data: values,
            label: {
              show: true,
              position: "right",
              color: ODYLITH_CHART_TEXT,
              fontSize: 10,
              fontWeight: 700,
            },
            itemStyle: {
              borderRadius: [0, 6, 6, 0],
              color: (params) => ODYLITH_CHART_PALETTE.execution[params.dataIndex % ODYLITH_CHART_PALETTE.execution.length],
            },
            emphasis: { focus: "series" },
          },
        ],
      };
    }

    function buildSignalEnvelopeOption(drawer) {
      const base = odylithBaseChartOption();
      const chart = drawer && drawer.charts && typeof drawer.charts.signal_envelope === "object"
        ? drawer.charts.signal_envelope
        : {};
      const labels = odylithSparkLabels(chart.labels, "T");
      return {
        ...base,
        xAxis: { ...base.xAxis, data: labels },
        yAxis: { ...base.yAxis, max: 100, min: 0 },
        series: [
          odylithLineSeries("Density", odylithNumericSeries(chart.density, [0]), ODYLITH_CHART_PALETTE.density),
          odylithLineSeries("Readiness", odylithNumericSeries(chart.readiness, [0]), ODYLITH_CHART_PALETTE.readiness),
          odylithLineSeries("Diversity", odylithNumericSeries(chart.diversity, [0]), ODYLITH_CHART_PALETTE.diversity),
          odylithLineSeries("Utility", odylithNumericSeries(chart.utility, [0]), ODYLITH_CHART_PALETTE.utility, {
            area: true,
            areaAlpha: "16",
          }),
        ],
      };
    }

    function buildControlCalibrationOption(drawer) {
      const chart = drawer && drawer.charts && typeof drawer.charts.control_calibration === "object"
        ? drawer.charts.control_calibration
        : {};
      const labels = odylithSparkLabels(chart.labels, "C");
      const values = odylithNumericSeries(chart.values, [0]).map((value) => value ?? 0);
      return {
        animationDuration: 360,
        animationDurationUpdate: 240,
        animationEasing: "cubicOut",
        animationEasingUpdate: "cubicOut",
        textStyle: {
          color: ODYLITH_CHART_TEXT,
          fontFamily: '"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
        },
        grid: {
          top: 34,
          left: 122,
          right: 24,
          bottom: 24,
          containLabel: false,
        },
        tooltip: {
          trigger: "item",
          backgroundColor: "rgba(255, 255, 255, 0.97)",
          borderColor: "rgba(125, 159, 214, 0.4)",
          borderWidth: 1,
          textStyle: { color: ODYLITH_CHART_TEXT, fontSize: 11 },
          extraCssText: "box-shadow: 0 16px 28px rgba(31,56,94,0.12); border-radius: 12px;",
        },
        graphic: chart.source
          ? [
              {
                type: "text",
                right: 10,
                top: 8,
                silent: true,
                style: {
                  text: String(chart.source),
                  fill: ODYLITH_AXIS_TEXT,
                  font: '600 10px "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif',
                },
              },
            ]
          : [],
        xAxis: {
          type: "value",
          min: 0,
          max: 100,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: ODYLITH_AXIS_TEXT, fontSize: 10 },
          splitLine: { lineStyle: { color: ODYLITH_GRID_LINE } },
        },
        yAxis: {
          type: "category",
          inverse: true,
          data: labels,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            color: ODYLITH_AXIS_TEXT,
            fontSize: 10,
            width: 108,
            overflow: "truncate",
          },
        },
        series: [
          {
            type: "bar",
            barWidth: 14,
            roundCap: true,
            data: values,
            label: {
              show: true,
              position: "right",
              color: ODYLITH_CHART_TEXT,
              fontSize: 10,
              fontWeight: 700,
              formatter: ({ value }) => `${Math.round(Number(value) || 0)}`,
            },
            itemStyle: {
              borderRadius: [0, 6, 6, 0],
              color: (params) => odylithScoreFill(params.value),
            },
            markLine: {
              symbol: "none",
              silent: true,
              lineStyle: {
                color: "rgba(37, 99, 235, 0.24)",
                type: "dashed",
              },
              label: {
                color: ODYLITH_AXIS_TEXT,
                fontSize: 9,
                formatter: "maintainer floor",
              },
              data: [{ xAxis: 70 }],
            },
            emphasis: { focus: "series" },
          },
        ],
      };
    }

    function initializeOdylithCharts(force = false) {
      return;
    }

    function resizeOdylithCharts() {
      return;
    }

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

    const tabStateMemory = {
      radar: { workstream: "", view: "" },
      atlas: { workstream: "", diagram: "" },
      compass: { workstream: "", window: "", date: "", audit_day: "" },
      registry: { component: "" },
      casebook: { bug: "", severity: "", status: "" },
    };

    function sanitizeShellState(rawState) {
      const tabToken = String(rawState && rawState.tab ? rawState.tab : "").trim().toLowerCase();
      const tab = tabToken === "atlas"
        ? "atlas"
        : (tabToken === "compass" ? "compass" : (tabToken === "registry" ? "registry" : (tabToken === "casebook" ? "casebook" : "radar")));
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
      state.bug = String(rawState && rawState.bug ? rawState.bug : "").trim();
      state.severity = String(rawState && rawState.severity ? rawState.severity : "").trim().toLowerCase();
      state.status = String(rawState && rawState.status ? rawState.status : "").trim().toLowerCase();
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
      tabStateMemory.casebook = {
        bug: state.bug,
        severity: state.severity,
        status: state.status,
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
      const tabToken = (params.get("tab") || "").trim().toLowerCase();
      const tab = tabToken === "atlas"
        ? "atlas"
        : (tabToken === "compass" ? "compass" : (tabToken === "registry" ? "registry" : (tabToken === "casebook" ? "casebook" : "radar")));
      const scopeToken = (params.get("scope") || "").trim();
      const workstreamToken = (params.get("workstream") || "").trim();
      const normalizedScopeToken = /^B-\d{3,}$/.test(scopeToken) ? scopeToken : "";
      const normalizedWorkstreamToken = /^B-\d{3,}$/.test(workstreamToken) ? workstreamToken : "";
      const componentToken = (params.get("component") || "").trim().toLowerCase();
      const bugToken = (params.get("bug") || "").trim();
      const severityToken = (params.get("severity") || "").trim().toLowerCase();
      const statusToken = (params.get("status") || "").trim().toLowerCase();
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
        diagram: canonicalizeDiagramToken(params.get("diagram") || ""),
        view: (params.get("view") || "").trim(),
        window: (params.get("window") || "").trim().toLowerCase(),
        date: (params.get("date") || "").trim(),
        audit_day: (params.get("audit_day") || "").trim(),
      });
    }

    function readCompassStateFromFrame() {
      try {
        const frameWindow = panes.compass && panes.compass.contentWindow ? panes.compass.contentWindow : null;
        if (!frameWindow) return null;
        const params = new URLSearchParams(frameWindow.location.search || "");
        return {
          workstream: (() => {
            const scopeToken = (params.get("scope") || "").trim();
            return /^B-\d{3,}$/.test(scopeToken) ? scopeToken : "";
          })(),
          window: (params.get("window") || "").trim().toLowerCase(),
          date: (params.get("date") || "").trim(),
          audit_day: (params.get("audit_day") || "").trim(),
        };
      } catch (_error) {
        return null;
      }
    }

    function readRadarStateFromFrame() {
      try {
        const frameWindow = panes.radar && panes.radar.contentWindow ? panes.radar.contentWindow : null;
        if (!frameWindow) return null;
        const params = new URLSearchParams(frameWindow.location.search || "");
        const workstream = String(params.get("workstream") || "").trim();
        const view = String(params.get("view") || "").trim().toLowerCase();
        return {
          workstream: /^B-\d{3,}$/.test(workstream) ? workstream : "",
          view: (view === "spec" || view === "plan") ? view : "",
        };
      } catch (_error) {
        return null;
      }
    }

    function readAtlasStateFromFrame() {
      try {
        const frameWindow = panes.atlas && panes.atlas.contentWindow ? panes.atlas.contentWindow : null;
        if (!frameWindow) return null;
        const params = new URLSearchParams(frameWindow.location.search || "");
        const workstream = String(params.get("workstream") || "").trim();
        const diagram = canonicalizeDiagramToken(params.get("diagram") || "");
        return {
          workstream: /^B-\d{3,}$/.test(workstream) ? workstream : "",
          diagram,
        };
      } catch (_error) {
        return null;
      }
    }

    function readRegistryStateFromFrame() {
      try {
        const frameWindow = panes.registry && panes.registry.contentWindow ? panes.registry.contentWindow : null;
        if (!frameWindow) return null;
        const params = new URLSearchParams(frameWindow.location.search || "");
        const component = String(params.get("component") || "").trim().toLowerCase();
        return { component };
      } catch (_error) {
        return null;
      }
    }

    function readCasebookStateFromFrame() {
      try {
        const frameWindow = panes.casebook && panes.casebook.contentWindow ? panes.casebook.contentWindow : null;
        if (!frameWindow) return null;
        const params = new URLSearchParams(frameWindow.location.search || "");
        return {
          bug: String(params.get("bug") || "").trim(),
          severity: String(params.get("severity") || "").trim().toLowerCase(),
          status: String(params.get("status") || "").trim().toLowerCase(),
        };
      } catch (_error) {
        return null;
      }
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

    function frameAlreadyAtHref(frameEl, expectedHref) {
      if (!frameEl) return false;
      const attrHref = String(frameEl.getAttribute("src") || "").trim();
      if (attrHref === expectedHref) return true;
      try {
        const frameWindow = frameEl.contentWindow;
        if (!frameWindow || !frameWindow.location) return false;
        const expected = new URL(expectedHref, window.location.href);
        return frameWindow.location.pathname === expected.pathname
          && frameWindow.location.search === expected.search;
      } catch (_error) {
        return false;
      }
    }

    function syncFrameHref(frameEl, expectedHref) {
      if (frameAlreadyAtHref(frameEl, expectedHref)) return;
      frameEl.setAttribute("src", expectedHref);
    }

    function syncFrameForTab(tabKey, expectedHref, options = {}) {
      if (!tabKey || !expectedHref) return;
      const frameEl = panes[tabKey];
      if (!frameEl) return;
      const shouldLoad = options.forceLoad === true || paneVisitState[tabKey] === true;
      if (!shouldLoad) return;
      paneVisitState[tabKey] = true;
      syncFrameHref(frameEl, expectedHref);
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
      return query;
    }

    function frameHrefsForState(state) {
      return {
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

    function syncFrames(state) {
      const frameHrefs = frameHrefsForState(state);
      syncFrameForTab(state.tab, frameHrefs[state.tab], { forceLoad: true });
    }

    function reloadActiveView() {
      const current = readStateFromUrl();
      if (!runtimeReloadableForTab(current.tab)) return;
      const frameEl = panes[current.tab];
      if (!frameEl) return;
      const frameHrefs = frameHrefsForState(current);
      paneVisitState[current.tab] = true;
      try {
        if (frameEl.contentWindow && frameEl.contentWindow.location) {
          frameEl.contentWindow.location.reload();
          return;
        }
      } catch (_error) {
        // Fall through to reassigning the frame source.
      }
      frameEl.removeAttribute("src");
      frameEl.setAttribute("src", frameHrefs[current.tab]);
    }

    function setDrawerState(drawer, panel, toggle, open) {
      if (!drawer || !panel || !toggle) return;
      const expanded = Boolean(open);
      drawer.classList.toggle("open", expanded);
      drawer.dataset.open = expanded ? "true" : "false";
      panel.setAttribute("aria-hidden", String(!expanded));
      panel.hidden = !expanded;
      toggle.setAttribute("aria-expanded", String(expanded));
    }

    function setBriefDrawer(open) {
      if (!hasBriefDrawer) return;
      if (open && hasOdylithDrawer) {
        setDrawerState(odylithDrawer, odylithDrawerPanel, odylithToggle, false);
      }
      setDrawerState(briefDrawer, briefDrawerPanel, briefToggle, open);
    }

    function setOdylithDrawer(open) {
      if (!hasOdylithDrawer) return;
      if (open && hasBriefDrawer) {
        setDrawerState(briefDrawer, briefDrawerPanel, briefToggle, false);
      }
      setDrawerState(odylithDrawer, odylithDrawerPanel, odylithToggle, open);
      if (open) {
        window.requestAnimationFrame(() => {
          initializeOdylithCharts();
          resizeOdylithCharts();
        });
      }
    }

    function applyTab(state, options = {}) {
      const next = rememberTabState(state);
      const tab = next.tab;
      tabs.radar.setAttribute("aria-selected", String(tab === "radar"));
      tabs.atlas.setAttribute("aria-selected", String(tab === "atlas"));
      tabs.compass.setAttribute("aria-selected", String(tab === "compass"));
      tabs.registry.setAttribute("aria-selected", String(tab === "registry"));
      tabs.casebook.setAttribute("aria-selected", String(tab === "casebook"));
      panes.radar.hidden = tab !== "radar";
      panes.atlas.hidden = tab !== "atlas";
      panes.compass.hidden = tab !== "compass";
      panes.registry.hidden = tab !== "registry";
      panes.casebook.hidden = tab !== "casebook";
      if (options.syncFrames !== false) {
        syncFrames(next);
      }
      document.title = `${tabTitles[tab] || shellTitle} | ${shellBrandName}`;

      const nextSearch = dashboardQueryString(next);
      if (options.pushHistory) {
        window.history.pushState(null, "", `${window.location.pathname}${nextSearch}`);
      } else if (window.location.search !== nextSearch) {
        window.history.replaceState(null, "", `${window.location.pathname}${nextSearch}`);
      }
      applyRuntimeStatus(latestRuntimeStatusState || {});
    }

    tabs.radar.addEventListener("click", () => {
      applyTab(buildTabActivationState("radar"), { pushHistory: true });
    });
    tabs.atlas.addEventListener("click", () => {
      applyTab(buildTabActivationState("atlas"), { pushHistory: true });
    });
    tabs.compass.addEventListener("click", () => {
      applyTab(buildTabActivationState("compass"), { pushHistory: true });
    });
    tabs.registry.addEventListener("click", () => {
      applyTab(buildTabActivationState("registry"), { pushHistory: true });
    });
    tabs.casebook.addEventListener("click", () => {
      applyTab(buildTabActivationState("casebook"), { pushHistory: true });
    });
    welcomeCopyButtons.forEach((button) => {
      button.addEventListener("click", async () => {
        const copied = await copyText(button.dataset.copyText || "");
        if (copied) {
          setWelcomeCopyStatus(button.dataset.copyStatus || "Prompt copied. Paste it into your agent.");
        } else {
          setWelcomeCopyStatus("Copy failed. Copy the prompt manually from the card.");
        }
      });
    });
    if (welcomeDismiss) {
      welcomeDismiss.addEventListener("click", () => {
        if (welcomeLaunchpadActive) {
          setWelcomeDismissed(true);
        }
        setWelcomeHidden(true);
        if (welcomeReopen && !welcomeReopen.hidden) {
          window.requestAnimationFrame(() => {
            welcomeReopen.focus();
          });
        }
      });
    }
    if (welcomeReopen) {
      welcomeReopen.addEventListener("click", () => {
        if (welcomeLaunchpadActive) {
          setWelcomeDismissed(false);
        }
        setWelcomeCopyStatus("");
        setWelcomeHidden(false);
      });
    }
    welcomeTabButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const tab = String(button.dataset.welcomeTab || "").trim().toLowerCase();
        if (!tab || !tabs[tab] || !panes[tab]) return;
        const current = readStateFromUrl();
        applyTab({ ...current, tab }, { pushHistory: true });
        if (welcomeLaunchpadActive) {
          setWelcomeDismissed(true);
        }
        setWelcomeHidden(true);
      });
    });
    welcomeTaskDoneButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const taskId = String(button.dataset.welcomeTaskDone || "").trim().toLowerCase();
        if (!taskId) return;
        const card = findWelcomeTaskCard(taskId);
        const currentlyComplete = Boolean(card && card.classList.contains("is-complete"));
        setWelcomeTaskComplete(taskId, !currentlyComplete);
      });
    });
    if (!welcomeLaunchpadActive) {
      setWelcomeDismissed(false);
    } else if (welcomeDismissed()) {
      setWelcomeHidden(true);
    }
    if (upgradeSpotlightDismiss) {
      upgradeSpotlightDismiss.addEventListener("click", dismissUpgradeSpotlight);
    }
    if (upgradeSpotlightBackdrop) {
      upgradeSpotlightBackdrop.addEventListener("click", dismissUpgradeSpotlight);
    }
    if (upgradeReopen) {
      upgradeReopen.addEventListener("click", reopenUpgradeSpotlight);
    }
    if (upgradeSpotlightDismissed()) {
      setUpgradeSpotlightHidden(true);
    } else if (upgradeSpotlight) {
      setUpgradeSpotlightHidden(false);
    }
    if (shouldDeferWelcomeUntilUpgradeCloses) {
      setWelcomeHidden(true);
    }
    syncRecoveryDock();
    scheduleUpgradeSpotlightExpiry();
    initializeWelcomeTaskState();
    applyRuntimeStatus(mergeRuntimeStatusState(payload));
    scheduleShellRefreshPoll(4000);
    scheduleRuntimeProbe(1200);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        scheduleShellRefreshPoll(1200);
        scheduleRuntimeProbe(1200);
      }
    });
    ["pointerdown", "keydown", "focusin", "touchstart"].forEach((eventName) => {
      window.addEventListener(eventName, recordUserInteraction, { passive: true });
    });
    window.addEventListener("beforeunload", () => {
      if (shellRefreshTimer) {
        window.clearTimeout(shellRefreshTimer);
      }
      if (runtimeProbeTimer) {
        window.clearTimeout(runtimeProbeTimer);
      }
    });
    if (hasBriefDrawer) {
      briefToggle.addEventListener("click", () => {
        setBriefDrawer(!briefDrawer.classList.contains("open"));
      });
      briefClose.addEventListener("click", () => {
        setBriefDrawer(false);
        briefToggle.focus();
      });
    }
    if (hasOdylithDrawer) {
      odylithToggle.addEventListener("click", () => {
        setOdylithDrawer(!odylithDrawer.classList.contains("open"));
      });
      odylithClose.addEventListener("click", () => {
        setOdylithDrawer(false);
        odylithToggle.focus();
      });
    }
    if (runtimeStatusReload) {
      runtimeStatusReload.addEventListener("click", () => {
        reloadActiveView();
      });
    }
    if (runtimeStatusDismiss) {
      runtimeStatusDismiss.addEventListener("click", () => {
        setRuntimeStatusDismissed(true);
        applyRuntimeStatus(latestRuntimeStatusState || {});
      });
    }
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && upgradeSpotlight && !upgradeSpotlight.hidden) {
        dismissUpgradeSpotlight();
      } else if (event.key === "Escape" && welcomeState && !welcomeState.hidden) {
        if (welcomeLaunchpadActive) {
          setWelcomeDismissed(true);
        }
        setWelcomeHidden(true);
      } else if (event.key === "Escape" && hasBriefDrawer && briefDrawer.classList.contains("open")) {
        setBriefDrawer(false);
        briefToggle.focus();
      } else if (event.key === "Escape" && hasOdylithDrawer && odylithDrawer.classList.contains("open")) {
        setOdylithDrawer(false);
        odylithToggle.focus();
      }
    });

    panes.radar.addEventListener("load", () => {
      const current = readStateFromUrl();
      if (current.tab !== "radar") return;
      const frameState = readRadarStateFromFrame();
      if (!frameState) return;
      const next = {
        ...current,
        tab: "radar",
        workstream: frameState.workstream,
        view: frameState.view,
      };
      if (
        next.tab === current.tab
        && next.workstream === current.workstream
        && next.view === current.view
      ) {
        return;
      }
      applyTab(next, { pushHistory: false, syncFrames: false });
    });

    panes.compass.addEventListener("load", () => {
      const current = readStateFromUrl();
      if (current.tab !== "compass") return;
      const frameState = readCompassStateFromFrame();
      if (!frameState) return;
      const next = {
        ...current,
        tab: "compass",
        workstream: frameState.workstream,
        window: frameState.window || current.window,
        date: frameState.date || current.date,
        audit_day: frameState.audit_day || current.audit_day,
      };
      if (
        next.tab === current.tab
        && next.workstream === current.workstream
        && next.window === current.window
        && next.date === current.date
        && next.audit_day === current.audit_day
      ) {
        return;
      }
      applyTab(next, { pushHistory: false, syncFrames: false });
    });

    panes.atlas.addEventListener("load", () => {
      const current = readStateFromUrl();
      if (current.tab !== "atlas") return;
      const frameState = readAtlasStateFromFrame();
      if (!frameState) return;
      const next = {
        ...current,
        tab: "atlas",
        workstream: frameState.workstream,
        diagram: frameState.diagram || current.diagram,
      };
      if (
        next.tab === current.tab
        && next.workstream === current.workstream
        && next.diagram === current.diagram
      ) {
        return;
      }
      applyTab(next, { pushHistory: false, syncFrames: false });
    });

    panes.registry.addEventListener("load", () => {
      const current = readStateFromUrl();
      if (current.tab !== "registry") return;
      const frameState = readRegistryStateFromFrame();
      if (!frameState) return;
      const next = {
        ...current,
        tab: "registry",
        component: frameState.component || current.component,
      };
      if (
        next.tab === current.tab
        && next.component === current.component
      ) {
        return;
      }
      applyTab(next, { pushHistory: false, syncFrames: false });
    });

    panes.casebook.addEventListener("load", () => {
      const current = readStateFromUrl();
      if (current.tab !== "casebook") return;
      const frameState = readCasebookStateFromFrame();
      if (!frameState) return;
      const next = {
        ...current,
        tab: "casebook",
        bug: frameState.bug || current.bug,
        severity: frameState.severity || current.severity,
        status: frameState.status || current.status,
      };
      if (
        next.tab === current.tab
        && next.bug === current.bug
        && next.severity === current.severity
        && next.status === current.status
      ) {
        return;
      }
      applyTab(next, { pushHistory: false, syncFrames: false });
    });

    window.addEventListener("message", (event) => {
      const data = event.data && typeof event.data === "object" ? event.data : null;
      if (!data) return;
      const raw = data.state && typeof data.state === "object" ? data.state : {};
      const current = readStateFromUrl();

      if (data.type === "odylith-radar-navigate") {
        if (!event || event.source !== panes.radar.contentWindow) return;
        if (current.tab !== "radar") return;
        const workstreamToken = String(raw.workstream || "").trim();
        const viewToken = String(raw.view || "").trim().toLowerCase();
        const next = {
          ...current,
          tab: "radar",
          workstream: /^B-\d{3,}$/.test(workstreamToken) ? workstreamToken : "",
          view: (viewToken === "spec" || viewToken === "plan") ? viewToken : "",
        };
        applyTab(next, { pushHistory: false, syncFrames: false });
        return;
      }

      if (data.type === "odylith-compass-navigate") {
        if (!event || event.source !== panes.compass.contentWindow) return;
        if (current.tab !== "compass") return;
        const scopeToken = String(raw.scope || raw.workstream || "").trim();
        const windowToken = String(raw.window || "").trim().toLowerCase();
        const dateToken = String(raw.date || "").trim();
        const auditDayToken = String(raw.audit_day || "").trim();
        const next = {
          ...current,
          tab: "compass",
          workstream: /^B-\d{3,}$/.test(scopeToken) ? scopeToken : "",
          window: (windowToken === "24h" || windowToken === "48h") ? windowToken : (current.window || ""),
          date: (dateToken === "live" || /^\d{4}-\d{2}-\d{2}$/.test(dateToken)) ? dateToken : (current.date || ""),
          audit_day: /^\d{4}-\d{2}-\d{2}$/.test(auditDayToken) ? auditDayToken : "",
        };
        applyTab(next, { pushHistory: false, syncFrames: false });
        return;
      }

      if (data.type === "odylith-atlas-navigate") {
        if (!event || event.source !== panes.atlas.contentWindow) return;
        if (current.tab !== "atlas") return;
        const workstreamToken = String(raw.workstream || "").trim();
        const diagramToken = canonicalizeDiagramToken(raw.diagram || "");
        const next = {
          ...current,
          tab: "atlas",
          workstream: /^B-\d{3,}$/.test(workstreamToken) ? workstreamToken : "",
          diagram: diagramToken,
        };
        applyTab(next, { pushHistory: false, syncFrames: false });
        return;
      }

      if (data.type === "odylith-registry-navigate") {
        if (!event || event.source !== panes.registry.contentWindow) return;
        if (current.tab !== "registry") return;
        const componentToken = String(raw.component || "").trim().toLowerCase();
        const next = {
          ...current,
          tab: "registry",
          component: componentToken,
        };
        applyTab(next, { pushHistory: false, syncFrames: false });
        return;
      }

      if (data.type === "odylith-casebook-navigate") {
        if (!event || event.source !== panes.casebook.contentWindow) return;
        if (current.tab !== "casebook") return;
        const bugToken = String(raw.bug || "").trim();
        const severityToken = String(raw.severity || "").trim().toLowerCase();
        const statusToken = String(raw.status || "").trim().toLowerCase();
        const next = {
          ...current,
          tab: "casebook",
          bug: bugToken,
          severity: severityToken,
          status: statusToken,
        };
        applyTab(next, { pushHistory: false, syncFrames: false });
        return;
      }

    });

    window.addEventListener("popstate", () => {
      applyTab(readStateFromUrl(), { pushHistory: false });
    });

    window.addEventListener("resize", () => {
      scheduleRuntimeStatusLayoutSync();
      resizeOdylithCharts();
    });

    applyTab(readStateFromUrl(), { pushHistory: false });
    setBriefDrawer(false);
    setOdylithDrawer(false);
    window.requestAnimationFrame(() => {
      initializeOdylithCharts();
      resizeOdylithCharts();
    });

function initToolingShellQuickTooltips() {
  const QUICK_TOOLTIP_BIND_KEY = "odylithToolingQuickTooltipBound";
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

initToolingShellQuickTooltips();

(function initToolingShellCheatsheetDrawer() {
  const root = document.querySelector("[data-agent-cheatsheet]");
  if (!root || root.dataset.cheatsheetBound === "true") return;
  root.dataset.cheatsheetBound = "true";

  const drawer = document.getElementById("odylithDrawer");
  const toggle = document.getElementById("odylithToggle");
  const searchInput = root.querySelector("[data-cheatsheet-search]");
  const results = document.getElementById("agentCheatsheetResults");
  const copyStatus = document.getElementById("agentCheatsheetCopyStatus");
  const cards = Array.from(root.querySelectorAll("[data-cheatsheet-card]"));
  const filterButtons = Array.from(root.querySelectorAll("[data-cheatsheet-filter]"));
  const copyButtons = Array.from(root.querySelectorAll("[data-cheatsheet-copy-button]"));
  const totalCards = cards.length;
  let activeCategory = "all";

  function setCopyStatus(message) {
    if (!copyStatus) return;
    copyStatus.textContent = String(message || "").trim();
  }

  function visibleLabel(count, query) {
    const filterButton = filterButtons.find((button) => (button.dataset.cheatsheetFilter || "all") === activeCategory);
    const categoryLabel = filterButton ? String(filterButton.dataset.cheatsheetFilterLabel || "").trim() : "";
    const parts = [`${count} workflow${count === 1 ? "" : "s"} visible`];
    if (activeCategory !== "all" && categoryLabel) {
      parts.push(categoryLabel);
    }
    if (query) {
      parts.push(`matching "${query}"`);
    } else {
      parts.push(`of ${totalCards}`);
    }
    return parts.join(" · ");
  }

  function applyFilters() {
    const query = String(searchInput && searchInput.value ? searchInput.value : "").trim().toLowerCase();
    let visibleCount = 0;
    cards.forEach((card) => {
      const category = String(card.dataset.cheatsheetCategory || "all").trim();
      const haystack = String(card.dataset.searchText || "").toLowerCase();
      const categoryMatch = activeCategory === "all" || activeCategory === category;
      const queryMatch = !query || haystack.includes(query);
      const visible = categoryMatch && queryMatch;
      card.hidden = !visible;
      card.setAttribute("aria-hidden", String(!visible));
      if (visible) visibleCount += 1;
    });
    filterButtons.forEach((button) => {
      const isActive = (button.dataset.cheatsheetFilter || "all") === activeCategory;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
    if (results) {
      results.textContent = visibleLabel(visibleCount, query);
    }
  }

  async function handleCopyClick(event) {
    const button = event.currentTarget;
    const text = String(button.dataset.copyText || "").trim();
    if (!text) return;
    const successMessage = String(button.dataset.copySuccess || "Copied.").trim();
    const copied = typeof copyText === "function"
      ? await copyText(text)
      : false;
    setCopyStatus(copied ? successMessage : "Copy failed. Copy the text manually.");
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      applyFilters();
    });
  }

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activeCategory = String(button.dataset.cheatsheetFilter || "all").trim() || "all";
      applyFilters();
    });
  });

  copyButtons.forEach((button) => {
    button.addEventListener("click", handleCopyClick);
  });

  if (toggle && drawer && searchInput) {
    toggle.addEventListener("click", () => {
      window.requestAnimationFrame(() => {
        if (drawer.classList.contains("open")) {
          searchInput.focus();
          searchInput.select();
        }
      });
    });
  }

  applyFilters();
})();
