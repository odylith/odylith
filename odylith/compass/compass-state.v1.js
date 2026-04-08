    function params() {
      const qs = new URLSearchParams(window.location.search);
      const windowToken = (qs.get("window") || "").trim().toLowerCase();
      const dateToken = (qs.get("date") || "live").trim();
      const scopeToken = (qs.get("scope") || "").trim();
      const workstreamToken = (qs.get("workstream") || "").trim();
      const auditDayToken = (qs.get("audit_day") || "").trim();
      const activeScopeToken = WORKSTREAM_RE.test(scopeToken)
        ? scopeToken
        : (WORKSTREAM_RE.test(workstreamToken) ? workstreamToken : "");
      return {
        window: windowToken === "24h" ? "24h" : "48h",
        // Compass accepts legacy `workstream` links but normalizes to `scope`.
        workstream: activeScopeToken,
        date: dateToken || "live",
        audit_day: DATE_RE.test(auditDayToken) ? auditDayToken : "",
        audit_day_pinned: DATE_RE.test(auditDayToken) || ((dateToken || "live") !== "live" && DATE_RE.test(dateToken)),
      };
    }

    function toDate(value) {
      const ts = Date.parse(String(value || ""));
      if (Number.isNaN(ts)) return null;
      return new Date(ts);
    }

    function formatterPart(formatter, date, type) {
      if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
      const parts = formatter.formatToParts(date);
      const row = parts.find((item) => item.type === type);
      return row ? String(row.value || "") : "";
    }

    function localDateTokenFromDate(date) {
      if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
      const y = formatterPart(DATE_PARTS_FORMATTER, date, "year");
      const m = formatterPart(DATE_PARTS_FORMATTER, date, "month");
      const d = formatterPart(DATE_PARTS_FORMATTER, date, "day");
      if (!y || !m || !d) return "";
      return `${y}-${m}-${d}`;
    }

    function hourInCompassTimeZone(date) {
      const token = formatterPart(HOUR_PARTS_FORMATTER, date, "hour");
      const hour = Number(token);
      if (!Number.isFinite(hour)) return 0;
      if (hour < 0) return 0;
      if (hour > 23) return 23;
      return hour;
    }

    function formatTimeInCompassTimeZone(date) {
      if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "--:--";
      return TIME_FORMATTER.format(date);
    }

    function formatDateTimeInCompassTimeZone(date) {
      if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "Unknown";
      return DATETIME_FORMATTER.format(date);
    }

    function parseLocalDateToken(token) {
      const raw = String(token || "").trim();
      if (!DATE_RE.test(raw)) return null;
      const parts = raw.split("-").map((value) => Number(value));
      if (parts.length !== 3) return null;
      const [year, month, day] = parts;
      const parsed = new Date(Date.UTC(year, month - 1, day, 12, 0, 0, 0));
      if (Number.isNaN(parsed.getTime())) return null;
      return parsed;
    }

    function runtimeSnapshotDate(payload) {
      const runtime = payload && typeof payload === "object" ? payload : null;
      const candidates = runtime
        ? [runtime.now_local_iso, runtime.generated_utc]
        : [];
      for (const value of candidates) {
        const parsed = toDate(value);
        if (parsed) return parsed;
      }
      return null;
    }

    function runtimeSnapshotDayToken(payload) {
      const token = toLocalDateToken(runtimeSnapshotDate(payload));
      return DATE_RE.test(token) ? token : "";
    }

    function runtimeSnapshotMillis(payload) {
      const snapshot = runtimeSnapshotDate(payload);
      return snapshot instanceof Date && !Number.isNaN(snapshot.getTime())
        ? snapshot.getTime()
        : Number.NEGATIVE_INFINITY;
    }

    function normalizeHistoryDateTokens(values) {
      const rows = Array.isArray(values) ? values : [];
      const deduped = [];
      const seen = new Set();
      rows.forEach((value) => {
        const token = String(value || "").trim();
        if (!DATE_RE.test(token) || seen.has(token)) return;
        seen.add(token);
        deduped.push(token);
      });
      deduped.sort((left, right) => right.localeCompare(left));
      return deduped;
    }

    function historyMeta(payload) {
      return payload && typeof payload === "object" && payload.history && typeof payload.history === "object"
        ? payload.history
        : {};
    }

    function knownHistoryDateTokens(payload) {
      const history = historyMeta(payload);
      const archive = history && history.archive && typeof history.archive === "object"
        ? history.archive
        : {};
      return normalizeHistoryDateTokens([
        ...(Array.isArray(history.dates) ? history.dates : []),
        ...(Array.isArray(history.restored_dates) ? history.restored_dates : []),
        ...(Array.isArray(archive.dates) ? archive.dates : []),
      ]);
    }

    function choosePreferredLiveRuntimePayload(primaryPayload, secondaryPayload) {
      const primary = primaryPayload && typeof primaryPayload === "object"
        ? applyLiveHistoryMeta(primaryPayload)
        : null;
      const secondary = secondaryPayload && typeof secondaryPayload === "object"
        ? applyLiveHistoryMeta(secondaryPayload)
        : null;
      if (!primary && !secondary) return { payload: null, source: "none" };
      if (!primary) return { payload: secondary, source: "secondary" };
      if (!secondary) return { payload: primary, source: "primary" };
      const primaryMs = runtimeSnapshotMillis(primary);
      const secondaryMs = runtimeSnapshotMillis(secondary);
      if (Number.isFinite(secondaryMs) && (!Number.isFinite(primaryMs) || secondaryMs > primaryMs)) {
        return { payload: secondary, source: "secondary" };
      }
      return { payload: primary, source: "primary" };
    }

    function latestHistoryDateToken(payload) {
      const dates = knownHistoryDateTokens(payload);
      for (const value of dates) {
        const token = String(value || "").trim();
        if (DATE_RE.test(token)) return token;
      }
      return "";
    }

    function calendarMaxDateToken(payload) {
      const historyToken = latestHistoryDateToken(payload);
      if (DATE_RE.test(historyToken)) return historyToken;
      const snapshotToken = runtimeSnapshotDayToken(payload);
      if (DATE_RE.test(snapshotToken)) return snapshotToken;
      const browserToken = toLocalDateToken(new Date());
      return DATE_RE.test(browserToken) ? browserToken : "";
    }

    function shiftDateToken(token, daysDelta) {
      const base = parseLocalDateToken(token);
      if (!base) return "";
      const next = new Date(base.getTime());
      next.setUTCDate(next.getUTCDate() + Number(daysDelta || 0));
      return localDateTokenFromDate(next);
    }

    function resolveTimelineAnchorDay(state, payload) {
      if (DATE_RE.test(String(state.audit_day || ""))) return String(state.audit_day || "");
      if (state.date !== "live" && DATE_RE.test(String(state.date || ""))) return String(state.date || "");
      const runtimeDay = runtimeSnapshotDayToken(payload);
      if (DATE_RE.test(runtimeDay)) return runtimeDay;
      const browserDay = toLocalDateToken(new Date());
      return DATE_RE.test(browserDay) ? browserDay : "";
    }

    function timelineDayTokens(state, payload) {
      const bounds = windowBounds(state, payload);
      if (!bounds || !(bounds.start instanceof Date) || !(bounds.end instanceof Date)) {
        const anchor = resolveTimelineAnchorDay(state, payload);
        return DATE_RE.test(anchor) ? [anchor] : [];
      }
      const startToken = toLocalDateToken(bounds.start);
      const endToken = toLocalDateToken(bounds.end);
      if (!DATE_RE.test(startToken) || !DATE_RE.test(endToken)) {
        const anchor = resolveTimelineAnchorDay(state, payload);
        return DATE_RE.test(anchor) ? [anchor] : [];
      }
      const tokens = [];
      let cursor = startToken;
      let guard = 0;
      while (DATE_RE.test(cursor) && cursor <= endToken && guard < 40) {
        tokens.push(cursor);
        cursor = shiftDateToken(cursor, 1);
        guard += 1;
      }
      if (tokens.length) return tokens;
      const anchor = resolveTimelineAnchorDay(state, payload);
      return DATE_RE.test(anchor) ? [anchor] : [];
    }

    function formatTimelineDayHeader(token) {
      const date = parseLocalDateToken(token);
      if (!date) return String(token || "");
      const readable = DAY_HEADER_FORMATTER.format(date);
      return `${readable} (${token})`;
    }

    function maxVisibleHourForDay(dayToken, payload) {
      const token = String(dayToken || "").trim();
      const today = calendarMaxDateToken(payload) || toLocalDateToken(new Date());
      if (!DATE_RE.test(token)) return 23;
      if (!DATE_RE.test(today)) return 23;
      if (token < today) return 23;
      if (token > today) return -1;
      const snapshot = runtimeSnapshotDate(payload);
      return hourInCompassTimeZone(snapshot || new Date());
    }

    function rollingThirtyDayBounds(payload) {
      const maxDate = calendarMaxDateToken(payload) || toLocalDateToken(new Date());
      const historyDates = knownHistoryDateTokens(payload);
      const minDate = historyDates.length
        ? historyDates[historyDates.length - 1]
        : (DATE_RE.test(maxDate) ? shiftDateToken(maxDate, -29) : "");
      return {
        min: minDate,
        max: maxDate,
      };
    }

    function clampDateToken(token, minToken, maxToken) {
      const raw = String(token || "").trim();
      if (!DATE_RE.test(raw)) return "";
      if (DATE_RE.test(minToken) && raw < minToken) return minToken;
      if (DATE_RE.test(maxToken) && raw > maxToken) return maxToken;
      return raw;
    }

    function timelineKindLabel(kind) {
      const token = String(kind || "").trim();
      if (token === "local_change") return "";
      if (token === "commit") return "commit";
      if (token === "plan_update") return "plan update";
      if (token === "plan_completion") return "plan completed";
      if (token === "bug_watch") return "critical bug watch";
      if (token === "bug_resolved") return "critical bug resolved";
      if (token === "bug_update") return "bug update";
      if (token === "decision") return "decision";
      if (token === "implementation") return "implementation";
      if (token === "statement") return "statement";
      if (!token) return "event";
      return token.replace(/_/g, " ");
    }

    function timelineKindPriority(kind) {
      const token = String(kind || "").trim();
      if (token === "decision" || token === "implementation" || token === "statement" || token === "plan_completion" || token === "bug_watch" || token === "bug_resolved") {
        return 2;
      }
      return 1;
    }

    function displayAuthorLabel(value) {
      const token = String(value || "").trim();
      if (!token) return "assistant";
      if (token.toLowerCase() === "codex") return "assistant";
      return token;
    }

    function summarizeAnchorTime(startIso, endIso) {
      const start = toDate(startIso);
      const end = toDate(endIso);
      if (!start && !end) return "time unavailable";
      if (start) return formatTimeInCompassTimeZone(start);
      return formatTimeInCompassTimeZone(end);
    }

    function compactTimestamp(value) {
      const ts = toDate(value);
      if (!ts) return "Unknown";
      return formatDateTimeInCompassTimeZone(ts);
    }

    function prioritizeTimelineItems(items) {
      const rows = Array.isArray(items) ? [...items] : [];
      if (!rows.length) return [];
      rows.sort((left, right) => {
        const leftTs = toDate(left && left.ts_iso);
        const rightTs = toDate(right && right.ts_iso);
        const leftMs = leftTs ? leftTs.getTime() : 0;
        const rightMs = rightTs ? rightTs.getTime() : 0;
        if (rightMs !== leftMs) return rightMs - leftMs;
        const leftPriority = timelineKindPriority(left && left.kind);
        const rightPriority = timelineKindPriority(right && right.kind);
        if (rightPriority !== leftPriority) return rightPriority - leftPriority;
        const leftId = String(left && left.id ? left.id : "");
        const rightId = String(right && right.id ? right.id : "");
        return rightId.localeCompare(leftId);
      });
      return rows;
    }

    function hoursCutoff(hours) {
      const now = new Date();
      return new Date(now.getTime() - (hours * 60 * 60 * 1000));
    }

    function windowBounds(state, payload) {
      const windowHours = state.window === "24h" ? 24 : 48;
      if (state.date === "live") {
        const snapshotEnd = runtimeSnapshotDate(payload) || new Date();
        const end = new Date(snapshotEnd.getTime());
        const start = new Date(end.getTime() - (windowHours * 60 * 60 * 1000));
        return { start, end };
      }

      const anchorToken = resolveTimelineAnchorDay(state, payload);
      if (DATE_RE.test(anchorToken)) {
        const anchor = parseLocalDateToken(anchorToken);
        if (anchor) {
          const end = new Date(anchor.getTime() + (24 * 60 * 60 * 1000) - 1000);
          const start = new Date(end.getTime() - (windowHours * 60 * 60 * 1000) + 1000);
          return { start, end };
        }
      }
      const end = new Date();
      const start = hoursCutoff(windowHours);
      return { start, end };
    }

    function visibleHourBoundsForDay(dayToken, state, payload) {
      const token = String(dayToken || "").trim();
      if (!DATE_RE.test(token)) return null;
      const selectedAuditDay = String(state && state.audit_day ? state.audit_day : "").trim();
      if (DATE_RE.test(selectedAuditDay) && selectedAuditDay === token) {
        const maxHour = maxVisibleHourForDay(token, payload);
        if (maxHour < 0) return null;
        return { min: 0, max: maxHour };
      }
      const bounds = windowBounds(state, payload);
      if (!bounds || !(bounds.start instanceof Date) || !(bounds.end instanceof Date)) {
        return { min: 0, max: 23 };
      }
      const startDay = toLocalDateToken(bounds.start);
      const endDay = toLocalDateToken(bounds.end);
      if (!startDay || !endDay) return { min: 0, max: 23 };
      if (token < startDay || token > endDay) return null;

      let min = 0;
      let max = 23;
      if (token === startDay) {
        min = hourInCompassTimeZone(bounds.start);
      }
      if (token === endDay) {
        max = hourInCompassTimeZone(bounds.end);
      }
      if (max < min) return null;
      return { min, max };
    }

    function showStatus(message, tone = "info") {
      const banner = document.getElementById("status-banner");
      if (!banner) return;
      const text = String(message || "").trim();
      if (!text) {
        banner.classList.add("hidden");
        banner.classList.remove("warn");
        banner.textContent = "";
        banner.title = "";
        return;
      }
      banner.classList.remove("hidden");
      banner.classList.toggle("warn", tone === "warn");
      banner.textContent = text;
      banner.title = text;
    }

    function navigateCompass(nextQuery) {
      const query = nextQuery instanceof URLSearchParams
        ? nextQuery
        : new URLSearchParams(String(nextQuery || ""));
      query.delete("workstream");
      const localSearch = query.toString();

      try {
        if (window.parent && window.parent !== window) {
          const scope = String(query.get("scope") || "").trim();
          const windowToken = String(query.get("window") || "").trim().toLowerCase();
          const dateToken = String(query.get("date") || "").trim();
          const auditDayToken = String(query.get("audit_day") || "").trim();
          window.parent.postMessage(
            {
              type: "odylith-compass-navigate",
              state: {
                tab: "compass",
                scope: WORKSTREAM_RE.test(scope) ? scope : "",
                window: (windowToken === "24h" || windowToken === "48h") ? windowToken : "48h",
                date: (dateToken === "live" || DATE_RE.test(dateToken)) ? dateToken : "live",
                audit_day: DATE_RE.test(auditDayToken) ? auditDayToken : "",
              },
            },
            "*",
          );
        }
      } catch (_error) {
        // Fall through to local navigation when parent sync is unavailable.
      }

      window.location.search = localSearch;
    }

    function dedupeNoticeLines(lines) {
      const source = Array.isArray(lines) ? lines : [];
      const seen = new Set();
      const out = [];
      for (const line of source) {
        const text = String(line || "").trim();
        if (!text) continue;
        const key = text.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        out.push(text);
      }
      return out;
    }

    function isWarningNotice(line) {
      const token = String(line || "").toLowerCase();
      if (!token) return false;
      return (
        token.includes("no snapshot available") ||
        token.includes("live runtime is") ||
        token.includes("refresh with `odylith") ||
        token.includes("falling back") ||
        token.includes("runtime unavailable") ||
        token.includes("failed")
      );
    }

    function stateToQuery(state) {
      const query = new URLSearchParams();
      query.set("tab", "compass");
      query.set("window", state.window === "24h" ? "24h" : "48h");
      if (state.workstream && WORKSTREAM_RE.test(state.workstream)) query.set("scope", state.workstream);
      if (state.date && (state.date === "live" || DATE_RE.test(state.date))) query.set("date", state.date);
      if (
        state.audit_day_pinned
        && state.audit_day
        && DATE_RE.test(state.audit_day)
        && !(state.date !== "live" && state.audit_day === state.date)
      ) {
        query.set("audit_day", state.audit_day);
      }
      return query.toString();
    }

    function compassScopeHref(workstreamId, state) {
      const token = String(workstreamId || "").trim();
      const query = new URLSearchParams(stateToQuery(state));
      if (WORKSTREAM_RE.test(token)) query.set("scope", token);
      else query.delete("scope");
      const search = query.toString();
      return `../index.html${search ? `?${search}` : ""}`;
    }

    function cloneJsonPayload(value) {
      if (!value || typeof value !== "object") return null;
      try {
        return JSON.parse(JSON.stringify(value));
      } catch (_error) {
        return null;
      }
    }

    function liveHistoryMeta() {
      const runtime = window.__ODYLITH_COMPASS_RUNTIME__;
      if (!runtime || typeof runtime !== "object") return null;
      const history = runtime && typeof runtime === "object" && runtime.history && typeof runtime.history === "object"
        ? runtime.history
        : {};
      const archive = history && history.archive && typeof history.archive === "object"
        ? history.archive
        : {};
      const archiveDates = normalizeHistoryDateTokens(archive.dates);
      return {
        retention_days: Number(history.retention_days || 0),
        dates: normalizeHistoryDateTokens(history.dates),
        restored_dates: normalizeHistoryDateTokens(history.restored_dates),
        archive: {
          ...archive,
          dates: archiveDates,
          count: Math.max(Number(archive.count || 0), archiveDates.length),
        },
      };
    }

    function applyLiveHistoryMeta(payload) {
      if (!payload || typeof payload !== "object") return payload;
      const meta = liveHistoryMeta();
      if (!meta) return payload;
      const history = payload.history && typeof payload.history === "object"
        ? { ...payload.history }
        : {};
      if (meta.retention_days > 0) history.retention_days = meta.retention_days;
      history.dates = [...meta.dates];
      history.restored_dates = [...meta.restored_dates];
      history.archive = {
        ...meta.archive,
        dates: Array.isArray(meta.archive && meta.archive.dates) ? [...meta.archive.dates] : [],
      };
      payload.history = history;
      return payload;
    }

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
        script.onerror = () => {
          assetLoadCache.delete(resolvedHref);
          reject(new Error(`failed to load asset ${resolvedHref}`));
        };
        document.head.appendChild(script);
      });
      assetLoadCache.set(resolvedHref, promise);
      return promise;
    }

    async function ensureEmbeddedHistoryLoaded() {
      const store = window.__ODYLITH_COMPASS_HISTORY__;
      if (
        store
        && typeof store === "object"
        && store.snapshots
        && typeof store.snapshots === "object"
        && Object.keys(store.snapshots).length
      ) {
        return store;
      }
      const href = String(compassShell().runtime_history_js_href || "").trim();
      if (!href) return null;
      try {
        await loadScriptAsset(href);
      } catch (_error) {
        return null;
      }
      const resolved = window.__ODYLITH_COMPASS_HISTORY__;
      return resolved && typeof resolved === "object" ? resolved : null;
    }

    function embeddedHistorySnapshot(dayToken) {
      const token = String(dayToken || "").trim();
      if (!DATE_RE.test(token)) return null;
      const store = window.__ODYLITH_COMPASS_HISTORY__;
      const snapshots = store && typeof store === "object" && store.snapshots && typeof store.snapshots === "object"
        ? store.snapshots
        : {};
      const snapshot = cloneJsonPayload(snapshots[token]);
      if (!snapshot) return null;
      return applyLiveHistoryMeta(snapshot);
    }

    function shellRedirectInProgress() {
      return __ODYLITH_SHELL_REDIRECT_IN_PROGRESS__ === true || window.__ODYLITH_SHELL_REDIRECTING__ === true;
    }

    async function loadHistorySnapshot(dayToken, { warnOnFailure = false } = {}) {
      if (shellRedirectInProgress()) return { payload: null, warning: "" };
      const token = String(dayToken || "").trim();
      if (!DATE_RE.test(token)) return { payload: null, warning: "" };
      const isFileProtocol = String(window.location.protocol || "").toLowerCase() === "file:";
      if (!isFileProtocol) {
        const href = `${compassShell().runtime_history_base_href}/${token}.v1.json`;
        try {
          const response = await fetch(href, { cache: "no-store" });
          if (response.ok) {
            const payload = await response.json();
            if (payload && typeof payload === "object") {
              return { payload: applyLiveHistoryMeta(payload), warning: "" };
            }
          }
        } catch (_error) {}
      }
      await ensureEmbeddedHistoryLoaded();
      const embeddedPayload = embeddedHistorySnapshot(token);
      if (embeddedPayload) return { payload: embeddedPayload, warning: "" };
      return {
        payload: null,
        warning: warnOnFailure ? `No snapshot available for this day (${token}). Showing live runtime.` : "",
      };
    }

    async function loadRuntime(state) {
      if (shellRedirectInProgress()) {
        return { payload: null, source: "redirect", warning: "" };
      }
      let warning = "";
      if (state.date && state.date !== "live" && DATE_RE.test(state.date)) {
        const history = await loadHistorySnapshot(state.date, { warnOnFailure: true });
        if (history.payload) {
          return { payload: history.payload, source: `history:${state.date}`, warning };
        }
        warning = history.warning;
      }

      const embeddedRuntime = window.__ODYLITH_COMPASS_RUNTIME__ && typeof window.__ODYLITH_COMPASS_RUNTIME__ === "object"
        ? window.__ODYLITH_COMPASS_RUNTIME__
        : null;
      let fetchedRuntime = null;

      try {
        const response = await fetch(compassShell().runtime_json_href, { cache: "no-store" });
        if (response.ok) {
          const payload = await response.json();
          if (payload && typeof payload === "object") {
            fetchedRuntime = payload;
          }
        }
      } catch (_error) {}

      // Prefer the direct JSON snapshot when it is available so a stale
      // preloaded runtime JS global cannot pin Compass to an older render.
      const runtime = choosePreferredLiveRuntimePayload(fetchedRuntime, embeddedRuntime);
      if (runtime.payload) {
        return {
          payload: runtime.payload,
          source: runtime.source === "primary" && fetchedRuntime ? "runtime-json" : "runtime-js",
          warning,
        };
      }

      return { payload: null, source: "none", warning };
    }

    async function augmentLiveHistoryIntoPayload(payload, state) {
      if (shellRedirectInProgress()) return payload;
      if (!payload || typeof payload !== "object") return payload;
      if (state.date !== "live") return payload;
      const dayTokens = timelineDayTokens(state, payload);
      if (!dayTokens.length) return payload;

      const todayToken = calendarMaxDateToken(payload) || toLocalDateToken(new Date());
      const targetDays = dayTokens
        .map((token) => String(token || "").trim())
        .filter((token) => DATE_RE.test(token) && token !== todayToken);
      if (!targetDays.length) return payload;

      const mergedEvents = Array.isArray(payload.timeline_events) ? [...payload.timeline_events] : [];
      const mergedTransactions = Array.isArray(payload.timeline_transactions) ? [...payload.timeline_transactions] : [];
      const seenEventKeys = new Set(
        mergedEvents.map((row) => `${String(row && row.id ? row.id : "")}|${String(row && row.ts_iso ? row.ts_iso : "")}|${String(row && row.kind ? row.kind : "")}|${String(row && row.summary ? row.summary : "")}`)
      );
      const seenTransactionKeys = new Set(
        mergedTransactions.map((row) => `${String(row && row.id ? row.id : "")}|${String(row && row.transaction_id ? row.transaction_id : "")}|${String(row && (row.end_ts_iso || row.start_ts_iso) ? (row.end_ts_iso || row.start_ts_iso) : "")}`)
      );

      for (const dayToken of targetDays) {
        const history = await loadHistorySnapshot(dayToken);
        const historyPayload = history.payload;
        if (!historyPayload) continue;

        const historyEvents = Array.isArray(historyPayload && historyPayload.timeline_events)
          ? historyPayload.timeline_events
          : [];
        historyEvents.forEach((row) => {
          if (toLocalDateToken(row && row.ts_iso) !== dayToken) return;
          const key = `${String(row && row.id ? row.id : "")}|${String(row && row.ts_iso ? row.ts_iso : "")}|${String(row && row.kind ? row.kind : "")}|${String(row && row.summary ? row.summary : "")}`;
          if (seenEventKeys.has(key)) return;
          seenEventKeys.add(key);
          mergedEvents.push(row);
        });

        const historyTransactions = Array.isArray(historyPayload && historyPayload.timeline_transactions)
          ? historyPayload.timeline_transactions
          : [];
        historyTransactions.forEach((row) => {
          const tsIso = String(row && (row.end_ts_iso || row.start_ts_iso) ? (row.end_ts_iso || row.start_ts_iso) : "");
          if (toLocalDateToken(tsIso) !== dayToken) return;
          const key = `${String(row && row.id ? row.id : "")}|${String(row && row.transaction_id ? row.transaction_id : "")}|${tsIso}`;
          if (seenTransactionKeys.has(key)) return;
          seenTransactionKeys.add(key);
          mergedTransactions.push(row);
        });
      }

      payload.timeline_events = mergedEvents;
      payload.timeline_transactions = mergedTransactions;
      return payload;
    }

    function scopeWorkstreams(payload, state) {
      const rows = Array.isArray(payload.current_workstreams) ? payload.current_workstreams : [];
      const executionRows = rows.filter((row) => {
        const status = String(row && row.status ? row.status : "").trim();
        return status === "planning" || status === "implementation";
      });
      const scopedIds = collectScopedWorkstreamIds(payload, state);
      const scopedSet = new Set(scopedIds);
      const scopedRows = rows.filter((row) => scopedSet.has(String(row.idea_id || "").trim()));
      if (state.workstream) {
        const selectedRows = rows.filter((row) => String(row.idea_id || "").trim() === state.workstream);
        if (selectedRows.length) return selectedRows;
        const fallbackRow = selectedScopedWorkstreamFallback(payload, state.workstream);
        return fallbackRow ? [fallbackRow] : [];
      }
      if (scopedRows.length) return scopedRows;
      if (executionRows.length) return executionRows;
      return rows;
    }

    function selectedScopedWorkstreamFallback(payload, workstreamId) {
      const targetId = String(workstreamId || "").trim();
      if (!WORKSTREAM_RE.test(targetId)) return null;
      const rows = workstreamRowsForLookup(payload);
      const activeRow = rows.find((row) => {
        if (String(row && row.idea_id ? row.idea_id : "").trim() !== targetId) return false;
        const status = String(row && row.status ? row.status : "").trim();
        return status === "planning" || status === "implementation";
      }) || null;
      if (activeRow) return activeRow;
      return rows.find((row) => String(row && row.idea_id ? row.idea_id : "").trim() === targetId) || null;
    }

    function digestLinesForState(payload, state) {
      const brief = standupBriefForState(payload, state);
      if (String(brief && brief.status ? brief.status : "") === "ready") {
        return standupBriefToDigestLines(brief);
      }
      if (!hasStructuredStandupBriefPayload(payload)) {
        return legacyDigestLinesForState(payload, state);
      }
      return [];
    }

    function digestWorkstreamCounts(payload, state) {
      const rows = digestLinesForState(payload, state);
      const counts = new Map();
      rows.forEach((line) => {
        const tokens = String(line || "").match(/\bB-\d{3,}\b/g) || [];
        tokens.forEach((token) => {
          const ideaId = String(token || "").trim();
          if (!WORKSTREAM_RE.test(ideaId)) return;
          counts.set(ideaId, Number(counts.get(ideaId) || 0) + 1);
        });
      });
      return counts;
    }

    function digestWorkstreamContextLookup(payload, state) {
      const workstreamTitles = workstreamTitleLookup(payload);
      const lookup = Object.create(null);
      const rows = digestLinesForState(payload, state);
      rows.forEach((line) => {
        const compactLine = compactDigestWorkstreamLabels(line, workstreamTitles);
        const parts = splitDigestLine(compactLine);
        const candidates = [];
        const header = String(parts && parts.header ? parts.header : "").trim();
        if (header) candidates.push(header);
        const bullets = splitDigestBodyToBullets(parts && parts.body ? parts.body : "");
        bullets.forEach((bullet) => {
          const token = String(bullet || "").trim();
          if (token) candidates.push(token);
        });
        candidates.forEach((candidate) => {
          const wsTokens = candidate.match(/\bB-\d{3,}\b/g) || [];
          wsTokens.forEach((wsToken) => {
            const ideaId = String(wsToken || "").trim();
            if (!WORKSTREAM_RE.test(ideaId)) return;
            if (lookup[ideaId]) return;
            lookup[ideaId] = candidate;
          });
        });
      });
      return lookup;
    }

    function collectScopedWorkstreamIds(payload, state) {
      const summaryState = stateForSummary(state);
      const baseState = {
        window: summaryState.window === "24h" ? "24h" : "48h",
        workstream: "",
        date: summaryState.date === "live" || DATE_RE.test(String(summaryState.date || "")) ? String(summaryState.date || "live") : "live",
        audit_day: "",
      };
      const maxWorkstreamFanout = 4;

      const validIds = new Set(
        (Array.isArray(payload.current_workstreams) ? payload.current_workstreams : [])
          .map((row) => String(row && row.idea_id ? row.idea_id : "").trim())
          .filter((token) => WORKSTREAM_RE.test(token))
      );
      const strictCounts = new Map();
      const boundedFanoutCounts = new Map();
      const broadFanoutCounts = new Map();
      const bump = (map, token, amount = 1) => {
        const ws = String(token || "").trim();
        if (!WORKSTREAM_RE.test(ws)) return;
        if (validIds.size && !validIds.has(ws)) return;
        map.set(ws, Number(map.get(ws) || 0) + Number(amount || 0));
      };
      const consumeRows = (rows) => {
        rows.forEach((row) => {
          const ws = Array.isArray(row.workstreams)
            ? Array.from(new Set(row.workstreams.map((token) => String(token || "").trim()).filter((token) => WORKSTREAM_RE.test(token))))
            : [];
          if (!ws.length) return;
          const fanout = ws.length;
          if (fanout === 1) {
            bump(strictCounts, ws[0], 1);
            return;
          }
          if (maxWorkstreamFanout > 0 && fanout > maxWorkstreamFanout) {
            ws.forEach((token) => bump(broadFanoutCounts, token, 1));
            return;
          }
          ws.forEach((token) => bump(boundedFanoutCounts, token, 1));
        });
      };

      consumeRows(
        filterTransactionsByWindow(payload, baseState)
      );
      consumeRows(
        filterEventsByWindow(payload, baseState)
      );

      const digestCounts = digestWorkstreamCounts(payload, baseState);
      const scoreByWorkstream = new Map();
      const addScore = (token, amount) => {
        const ws = String(token || "").trim();
        if (!WORKSTREAM_RE.test(ws)) return;
        if (validIds.size && !validIds.has(ws)) return;
        scoreByWorkstream.set(ws, Number(scoreByWorkstream.get(ws) || 0) + Number(amount || 0));
      };
      strictCounts.forEach((count, ws) => addScore(ws, Number(count || 0) * 100));
      boundedFanoutCounts.forEach((count, ws) => addScore(ws, Number(count || 0) * 25));
      broadFanoutCounts.forEach((count, ws) => addScore(ws, Number(count || 0) * 5));
      digestCounts.forEach((count, ws) => addScore(ws, Number(count || 0) * 60));

      if (scoreByWorkstream.size) {
        return Array.from(scoreByWorkstream.entries())
          .sort((left, right) => {
            const delta = Number(right[1] || 0) - Number(left[1] || 0);
            if (delta !== 0) return delta;
            return String(left[0] || "").localeCompare(String(right[0] || ""));
          })
          .map(([ws]) => String(ws || ""));
      }

      const executionFallbackRows = Array.isArray(payload.current_workstreams)
        ? payload.current_workstreams.filter((row) => {
            const status = String(row && row.status ? row.status : "").trim();
            return status === "planning" || status === "implementation";
          })
        : [];
      return executionFallbackRows
        .map((row) => String(row && row.idea_id ? row.idea_id : "").trim())
        .filter((token) => WORKSTREAM_RE.test(token))
        .filter((token, index, list) => list.indexOf(token) === index)
        .sort((left, right) => String(left).localeCompare(String(right)));
    }

    function stateForSummary(state) {
      return {
        window: state.window === "24h" ? "24h" : "48h",
        workstream: WORKSTREAM_RE.test(String(state.workstream || "")) ? String(state.workstream || "") : "",
        date: state.date === "live" || DATE_RE.test(String(state.date || "")) ? String(state.date || "live") : "live",
        // Summary surfaces span the full selected 24h/48h window.
        // Audit-day filtering is timeline-specific and should not narrow standup/workstream context.
        audit_day: "",
        audit_day_pinned: false,
      };
    }

    function normalizeStateWithPayload(state, payload) {
      const next = {
        window: state.window === "24h" ? "24h" : "48h",
        workstream: WORKSTREAM_RE.test(String(state.workstream || "")) ? String(state.workstream || "") : "",
        date: state.date === "live" || DATE_RE.test(String(state.date || "")) ? String(state.date || "live") : "live",
        audit_day: DATE_RE.test(String(state.audit_day || "")) ? String(state.audit_day || "") : "",
        audit_day_pinned: Boolean(state && state.audit_day_pinned),
      };
      const warnings = [];
      const bounds = rollingThirtyDayBounds(payload);
      const todayToken = calendarMaxDateToken(payload) || toLocalDateToken(new Date());

      if (state.workstream && !next.workstream) {
        warnings.push("Invalid workstream token in URL. Falling back to global scope.");
      }
      if (state.date && state.date !== next.date) {
        warnings.push("Invalid date token in URL. Falling back to live runtime.");
      }
      if (state.audit_day && state.audit_day !== next.audit_day) {
        warnings.push("Invalid audit_day token in URL. Falling back to latest available day.");
      }

      if (next.date !== "live" && DATE_RE.test(next.date)) {
        const clampedDate = clampDateToken(next.date, bounds.min, bounds.max);
        if (clampedDate !== next.date) {
          warnings.push(`Selected date ${next.date} is outside calendar range. Using ${clampedDate}.`);
          next.date = clampedDate;
        }
        if (next.date === todayToken) {
          // "Today" should run in live mode so Global reflects trailing 24/48h telemetry.
          next.date = "live";
        }
      }
      if (DATE_RE.test(next.audit_day)) {
        const clampedAudit = clampDateToken(next.audit_day, bounds.min, bounds.max);
        if (clampedAudit !== next.audit_day) {
          warnings.push(`Selected audit day ${next.audit_day} is outside calendar range. Using ${clampedAudit}.`);
          next.audit_day = clampedAudit;
        }
      }

      const historyDates = knownHistoryDateTokens(payload);
      if (next.date !== "live" && !historyDates.includes(next.date)) {
        warnings.push(`No snapshot available for this day (${next.date}). Showing live payload for context.`);
      }

      if (!next.audit_day && next.date !== "live" && DATE_RE.test(next.date)) {
        next.audit_day = next.date;
      }
      const auditDays = collectTimelineAuditDays(
        filterEventsByWindow(payload, next),
        filterTransactionsByWindow(payload, next),
      );
      if (auditDays.length) {
        if (!next.audit_day) {
          next.audit_day = auditDays[0];
        } else if (!auditDays.includes(next.audit_day) && DATE_RE.test(next.audit_day)) {
          if (next.audit_day_pinned) {
            warnings.push(`No events were found for audit day ${next.audit_day} in the selected window.`);
          } else {
            next.audit_day = auditDays[0];
          }
        }
      } else {
        if (!DATE_RE.test(next.audit_day)) {
          next.audit_day = next.date !== "live" && DATE_RE.test(next.date)
            ? next.date
            : (clampDateToken(todayToken, bounds.min, bounds.max) || todayToken);
        }
      }

      const workstreamSet = new Set(collectScopedWorkstreamIds(payload, next));
      if (next.workstream && !workstreamSet.has(next.workstream)) {
        const allWorkstreamSet = new Set(
          workstreamRowsForLookup(payload)
            .map((row) => String(row && row.idea_id ? row.idea_id : "").trim())
            .filter((token) => WORKSTREAM_RE.test(token))
        );
        if (!allWorkstreamSet.has(next.workstream)) {
          warnings.push(`Unknown workstream ${next.workstream}. Showing global scope.`);
          next.workstream = "";
        }
      }

      const canonicalQuery = stateToQuery(next);
      const canonicalSearch = canonicalQuery ? `?${canonicalQuery}` : "";
      if (window.location.search !== canonicalSearch) {
        window.history.replaceState(null, "", `${window.location.pathname}${canonicalSearch}`);
      }
      return { state: next, warnings };
    }

    function filterEventsByWindow(payload, state) {
      const rows = Array.isArray(payload.timeline_events) ? payload.timeline_events : [];
      const selectedDays = new Set(timelineDayTokens(state, payload));
      const bounds = windowBounds(state, payload);
      const startMs = bounds && bounds.start instanceof Date ? bounds.start.getTime() : Number.NEGATIVE_INFINITY;
      const endMs = bounds && bounds.end instanceof Date ? bounds.end.getTime() : Number.POSITIVE_INFINITY;
      const filtered = rows.filter((row) => {
        const ts = toDate(row.ts_iso);
        if (!ts) return false;
        const ms = ts.getTime();
        if (ms < startMs || ms > endMs) return false;
        if (selectedDays.size && !selectedDays.has(toLocalDateToken(ts))) return false;
        if (!state.workstream) return true;
        const ws = Array.isArray(row.workstreams) ? row.workstreams.map((item) => String(item || "").trim()) : [];
        return ws.includes(state.workstream);
      });
      filtered.sort((left, right) => {
        const leftTs = toDate(left && left.ts_iso);
        const rightTs = toDate(right && right.ts_iso);
        const leftMs = leftTs ? leftTs.getTime() : 0;
        const rightMs = rightTs ? rightTs.getTime() : 0;
        if (rightMs !== leftMs) return rightMs - leftMs;
        const leftId = String(left && left.id ? left.id : "");
        const rightId = String(right && right.id ? right.id : "");
        return rightId.localeCompare(leftId);
      });
      return filtered;
    }

    function filterTransactionsByWindow(payload, state) {
      const rows = Array.isArray(payload.timeline_transactions) ? payload.timeline_transactions : [];
      const selectedDays = new Set(timelineDayTokens(state, payload));
      const bounds = windowBounds(state, payload);
      const startMs = bounds && bounds.start instanceof Date ? bounds.start.getTime() : Number.NEGATIVE_INFINITY;
      const endMs = bounds && bounds.end instanceof Date ? bounds.end.getTime() : Number.POSITIVE_INFINITY;
      const filtered = rows.filter((row) => {
        const ts = toDate(row.end_ts_iso || row.start_ts_iso);
        if (!ts) return false;
        const ms = ts.getTime();
        if (ms < startMs || ms > endMs) return false;
        if (selectedDays.size && !selectedDays.has(toLocalDateToken(ts))) return false;
        if (!state.workstream) return true;
        const ws = Array.isArray(row.workstreams) ? row.workstreams.map((item) => String(item || "").trim()) : [];
        return ws.includes(state.workstream);
      });
      filtered.sort((left, right) => {
        const leftTs = toDate((left && (left.end_ts_iso || left.start_ts_iso)) || "");
        const rightTs = toDate((right && (right.end_ts_iso || right.start_ts_iso)) || "");
        const leftMs = leftTs ? leftTs.getTime() : 0;
        const rightMs = rightTs ? rightTs.getTime() : 0;
        if (rightMs !== leftMs) return rightMs - leftMs;
        const leftId = String(left && left.id ? left.id : "");
        const rightId = String(right && right.id ? right.id : "");
        return rightId.localeCompare(leftId);
      });
      return filtered;
    }

    function toLocalDateToken(value) {
      const date = value instanceof Date ? value : toDate(value);
      return localDateTokenFromDate(date);
    }

    function collectAuditDays(events) {
      const tokens = new Set();
      for (const row of events) {
        const token = toLocalDateToken(row.ts_iso);
        if (token) tokens.add(token);
      }
      return Array.from(tokens).sort((a, b) => b.localeCompare(a));
    }

    function collectTimelineAuditDays(events, transactions) {
      const tokens = new Set();
      (Array.isArray(events) ? events : []).forEach((row) => {
        const token = toLocalDateToken(row && row.ts_iso);
        if (token) tokens.add(token);
      });
      (Array.isArray(transactions) ? transactions : []).forEach((row) => {
        const token = toLocalDateToken((row && (row.end_ts_iso || row.start_ts_iso)) || "");
        if (token) tokens.add(token);
      });
      return Array.from(tokens).sort((a, b) => b.localeCompare(a));
    }

    function filterEventsForAuditDay(events, auditDay) {
      if (!auditDay) return [];
      return events.filter((row) => toLocalDateToken(row.ts_iso) === auditDay);
    }

    function runtimeAgeMinutes(payload) {
      const snapshot = runtimeSnapshotDate(payload);
      if (!snapshot) return null;
      const ageMinutes = (Date.now() - snapshot.getTime()) / (60 * 1000);
      if (!Number.isFinite(ageMinutes)) return null;
      return ageMinutes < 0 ? 0 : ageMinutes;
    }

    function formatRuntimeAge(ageMinutes) {
      const minutes = Math.max(0, Math.round(Number(ageMinutes || 0)));
      if (minutes < 90) return `${minutes}m`;
      const hours = minutes / 60;
      if (hours < 36) return `${hours.toFixed(1)}h`;
      const days = hours / 24;
      return `${days.toFixed(1)}d`;
    }

    function staleRuntimeNotice(payload, state) {
      if (!payload || typeof payload !== "object") return "";
      if (String(state && state.date ? state.date : "live") !== "live") return "";
      const ageMinutes = runtimeAgeMinutes(payload);
      if (ageMinutes === null || ageMinutes < 90) return "";
      const snapshot = runtimeSnapshotDate(payload);
      const snapshotLabel = snapshot ? formatDateTimeInCompassTimeZone(snapshot) : "unknown time";
      return `Compass snapshot ${snapshotLabel} is ${formatRuntimeAge(ageMinutes)} old; timeline stays pinned there. Refresh: \`odylith dashboard refresh --repo-root .\` or ask agent \`Refresh Compass runtime for this repo.\``;
    }
