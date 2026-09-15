const payload = JSON.parse(document.getElementById("toolingDashboardData").textContent);
    const shellTitle = document.title || "Odylith";
    const shellBrandName = shellTitle.replace(/\s+Dashboard$/, "") || "Odylith";
    const payloadScript = document.getElementById("toolingDashboardData");
    const tabTitles = {
      project: "Project",
      radar: "Radar",
      atlas: "Atlas",
      compass: "Compass",
      registry: "Registry",
      casebook: "Casebook",
    };
    const tabs = {
      project: document.getElementById("tab-project"),
      radar: document.getElementById("tab-radar"),
      atlas: document.getElementById("tab-atlas"),
      compass: document.getElementById("tab-compass"),
      registry: document.getElementById("tab-registry"),
      casebook: document.getElementById("tab-casebook"),
    };
    const panes = {
      project: document.getElementById("pane-project"),
      radar: document.getElementById("frame-radar"),
      atlas: document.getElementById("frame-atlas"),
      compass: document.getElementById("frame-compass"),
      registry: document.getElementById("frame-registry"),
      casebook: document.getElementById("frame-casebook"),
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
    const upgradeSpotlightLinks = Array.from(document.querySelectorAll("#shellUpgradeSpotlight .upgrade-spotlight-link"));
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
    const UPGRADE_SPOTLIGHT_MAX_AGE_MS = 10 * 60 * 1000;

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
    const versionStateHref = String(payload.version_state_href || "").trim();
    const versionStateGlobalName = String(payload.version_state_global_name || "__ODYLITH_VERSION_STATE__").trim() || "__ODYLITH_VERSION_STATE__";
    const statusSnapshot = payload.status_snapshot || null;
    let latestVersionState = statusSnapshot ? statusSnapshot.version_state : window[versionStateGlobalName] || null;
    let versionStateProbeTimer = 0;
    let versionStateProbeInFlight = false;
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
        upgradeReopen.focus();
      }
    }

    function reopenUpgradeSpotlight() {
      if (!hasUpgradeSpotlight()) return;
      setUpgradeSpotlightDismissed(false);
      setUpgradeSpotlightHidden(false);
      if (upgradeSpotlightDismiss) {
        upgradeSpotlightDismiss.focus();
      }
    }

    function openUpgradeSpotlightLink(event) {
      const link = event.currentTarget;
      const href = link && link.href ? String(link.href).trim() : "";
      if (!href) return;
      const opened = window.open(href, "_blank");
      if (opened) {
        event.preventDefault();
        try {
          opened.opener = null;
        } catch (_error) {
          // Some browser contexts make opener read-only after noopener.
        }
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
      if (statusSnapshot) return;
      if (!payloadScript || !payloadScript.src || (!shellPayloadGeneratedUtc && !shellPayloadRefreshFingerprint)) return;
      if (shellRefreshTimer) {
        window.clearTimeout(shellRefreshTimer);
      }
      shellRefreshTimer = window.setTimeout(checkForShellRefresh, delayMs);
    }

    function reloadShellAfterPayloadRefresh() {
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.set("odylith-shell-refresh", String(Date.now()));
      window.location.replace(nextUrl.toString());
    }

    function checkForShellRefresh() {
      if (statusSnapshot) return;
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
          reloadShellAfterPayloadRefresh();
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
        !statusSnapshot && liveRefreshPayload
        && liveRefreshPayload.enabled
        && String(liveRefreshPayload.state_href || "").trim()
      );
    }

    function liveRefreshPollIntervalMs() {
      if (!liveRefreshPayload) return 20000;
      const parsed = Number.parseInt(String(liveRefreshPayload.poll_interval_ms || ""), 10);
      return Number.isFinite(parsed) && parsed >= 5000 ? parsed : 20000;
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
      if (statusSnapshot) return Boolean(panes[String(tab || "").trim().toLowerCase()]);
      if (!liveRefreshPayload || !Array.isArray(liveRefreshPayload.reloadable_tabs)) return false;
      return liveRefreshPayload.reloadable_tabs.includes(String(tab || "").trim().toLowerCase());
    }

    function normalizeVersionToken(value) {
      return String(value || "").trim().replace(/^v/i, "");
    }

    function formatVersionLabel(value) {
      const token = normalizeVersionToken(value);
      if (!token) return "";
      return /^[0-9]/.test(token) ? `v${token}` : token;
    }

    function renderedShellVersionToken() {
      const selfHost = payload && payload.self_host && typeof payload.self_host === "object"
        ? payload.self_host
        : {};
      return normalizeVersionToken(
        selfHost.active_version
        || selfHost.pinned_version
        || payload.shell_version_label
        || ""
      );
    }

    function buildShellVersionDriftPosture(versionState) {
      if (!versionState || typeof versionState !== "object") return null;
      const authoritativeToken = normalizeVersionToken(
        versionState.authoritative_version
        || versionState.active_version
        || versionState.pinned_version
        || ""
      );
      const renderedToken = renderedShellVersionToken();
      if (!authoritativeToken || !renderedToken || authoritativeToken === renderedToken) {
        return null;
      }
      const renderedLabel = formatVersionLabel(renderedToken);
      const authoritativeLabel = String(versionState.authoritative_label || "").trim() || formatVersionLabel(authoritativeToken);
      const generatedUtc = String(payload.generated_utc || "").trim() || "unknown";
      const stateGeneratedUtc = String(versionState.generated_utc || "").trim();
      const source = String(versionState.source || "odylith version").trim();
      const metaParts = [
        `Source: ${source}`,
        `Shell generated: ${generatedUtc}`,
        stateGeneratedUtc ? `Checked: ${stateGeneratedUtc}` : "",
        "Next: odylith dashboard refresh --repo-root . --force",
      ].filter(Boolean);
      return {
        visible: true,
        tone: "warning",
        kicker: "Dashboard stale",
        title: `Shell shows ${renderedLabel}, runtime is ${authoritativeLabel}`,
        body: "The generated dashboard shell is older than the authoritative Odylith runtime. Refresh only the dashboard shell before using this view as version evidence.",
        meta: metaParts.join(" · "),
        showReload: false,
        reloadLabel: "",
      };
    }

    function normalizeRuntimePosture(rawPosture, fallbackPosture) {
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
      const current = navigation.readState();
      const currentTab = current && typeof current === "object"
        ? String(current.tab || "").trim().toLowerCase()
        : "";
      if (!currentTab) return fallbackPosture;
      const surfaceRuntimeStatus = runtimeState && runtimeState.surface_runtime_status && typeof runtimeState.surface_runtime_status === "object"
        ? runtimeState.surface_runtime_status
        : initialSurfaceRuntimeStatus;
      const shellPosture = normalizeRuntimePosture(surfaceRuntimeStatus.shell, fallbackPosture);
      if (shellPosture.visible) {
        return shellPosture;
      }
      const rawPosture = surfaceRuntimeStatus[currentTab];
      return normalizeRuntimePosture(rawPosture, fallbackPosture);
    }

    function mergeRuntimeStatusState(runtimeState) {
      const baseState = runtimeState && typeof runtimeState === "object"
        ? { ...runtimeState }
        : {};
      if (!baseState.surface_runtime_status || typeof baseState.surface_runtime_status !== "object") {
        baseState.surface_runtime_status = initialSurfaceRuntimeStatus;
      }
      baseState.surface_runtime_status = { ...baseState.surface_runtime_status };
      const shellVersionDriftPosture = buildShellVersionDriftPosture(latestVersionState);
      if (shellVersionDriftPosture) {
        baseState.surface_runtime_status.shell = shellVersionDriftPosture;
      }
      return baseState;
    }

    function applyRuntimeStatus(runtimeState) {
      if (!runtimeStatus || !runtimeStatusTitle || !runtimeStatusBody || !runtimeStatusMeta || !runtimeStatusReload || !runtimeStatusDismiss) {
        return;
      }
      latestRuntimeStatusState = mergeRuntimeStatusState(runtimeState);
      const posture = buildRuntimeStatusPosture(latestRuntimeStatusState);
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

    function versionStateProbeEnabled() {
      return Boolean(!statusSnapshot && versionStateHref);
    }

    function scheduleVersionStateProbe(delayMs = 5000) {
      if (!versionStateProbeEnabled()) return;
      if (versionStateProbeTimer) {
        window.clearTimeout(versionStateProbeTimer);
      }
      versionStateProbeTimer = window.setTimeout(checkForVersionState, delayMs);
    }

    function checkForVersionState() {
      if (!versionStateProbeEnabled()) return;
      if (versionStateProbeInFlight) return;
      versionStateProbeInFlight = true;
      const previousPayload = window[versionStateGlobalName];
      const refreshProbe = document.createElement("script");
      const separator = versionStateHref.includes("?") ? "&" : "?";
      refreshProbe.async = true;
      refreshProbe.src = `${versionStateHref}${separator}refresh=${Date.now()}`;
      refreshProbe.onload = () => {
        versionStateProbeInFlight = false;
        const nextPayload = window[versionStateGlobalName];
        refreshProbe.remove();
        window[versionStateGlobalName] = previousPayload || {};
        if (nextPayload && typeof nextPayload === "object") {
          latestVersionState = nextPayload;
          applyRuntimeStatus(latestRuntimeStatusState || {});
        }
        scheduleVersionStateProbe(15000);
      };
      refreshProbe.onerror = () => {
        versionStateProbeInFlight = false;
        refreshProbe.remove();
        window[versionStateGlobalName] = previousPayload || {};
        scheduleVersionStateProbe(30000);
      };
      document.head.appendChild(refreshProbe);
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
          const current = navigation.readState();
          if (runtimeStateAffectsTab(current.tab, nextPayload) && runtimeAutoReloadReadyForTab(current.tab)) {
            runtimeAutoReloadAtByTab[String(current.tab || "").trim().toLowerCase()] = Date.now();
            if (runtimeReloadableForTab(current.tab)) navigation.reload();
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

    const navigation = createToolingShellNavigation({
      panes, payload, onState: renderSelectedTab, localStorageRead, localStorageWrite,
    });

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
    }

    function renderSelectedTab(next) {
      const tab = next.tab;
      tabs.project.setAttribute("aria-selected", String(tab === "project"));
      tabs.radar.setAttribute("aria-selected", String(tab === "radar"));
      tabs.atlas.setAttribute("aria-selected", String(tab === "atlas"));
      tabs.compass.setAttribute("aria-selected", String(tab === "compass"));
      tabs.registry.setAttribute("aria-selected", String(tab === "registry"));
      tabs.casebook.setAttribute("aria-selected", String(tab === "casebook"));
      panes.project.hidden = tab !== "project";
      panes.radar.hidden = tab !== "radar";
      panes.atlas.hidden = tab !== "atlas";
      panes.compass.hidden = tab !== "compass";
      panes.registry.hidden = tab !== "registry";
      panes.casebook.hidden = tab !== "casebook";
      document.title = `${tabTitles[tab] || shellTitle} | ${shellBrandName}`;

      applyRuntimeStatus(latestRuntimeStatusState || {});
    }

    tabs.project.addEventListener("click", () => {
      navigation.selectTab("project");
    });
    tabs.radar.addEventListener("click", () => {
      navigation.selectTab("radar");
    });
    tabs.atlas.addEventListener("click", () => {
      navigation.selectTab("atlas");
    });
    tabs.compass.addEventListener("click", () => {
      navigation.selectTab("compass");
    });
    tabs.registry.addEventListener("click", () => {
      navigation.selectTab("registry");
    });
    tabs.casebook.addEventListener("click", () => {
      navigation.selectTab("casebook");
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
          welcomeReopen.focus();
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
        const current = navigation.readState();
        navigation.activate({ ...current, tab }, { historyMode: "push" });
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
    upgradeSpotlightLinks.forEach((link) => {
      link.addEventListener("click", openUpgradeSpotlightLink);
    });
    if (upgradeSpotlightDismissed() || !hasUpgradeSpotlight()) {
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
    scheduleVersionStateProbe(15000);
    scheduleShellRefreshPoll(4000);
    scheduleRuntimeProbe(1200);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        scheduleVersionStateProbe(300);
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
      if (versionStateProbeTimer) {
        window.clearTimeout(versionStateProbeTimer);
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
        if (runtimeReloadableForTab(navigation.readState().tab)) navigation.reload();
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

    window.addEventListener("resize", () => {
      scheduleRuntimeStatusLayoutSync();
    });

    navigation.start();
    setBriefDrawer(false);
    setOdylithDrawer(false);
