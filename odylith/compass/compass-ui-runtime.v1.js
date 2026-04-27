    function markCompassSurfaceReady(isReady) {
      if (!document.body || !document.body.dataset) return;
      document.body.dataset.surfaceReady = isReady ? "ready" : "loading";
    }

    function syncControls(state, events, payload) {
      const persistAuditDay = Boolean(state && state.audit_day_pinned && DATE_RE.test(state.audit_day));
      document.querySelectorAll('[data-window]').forEach((btn) => {
        btn.classList.toggle('active', String(btn.getAttribute('data-window')) === state.window);
        btn.addEventListener('click', () => {
          const next = new URLSearchParams(window.location.search);
          next.delete('workstream');
          next.set('tab', 'compass');
          next.set('window', String(btn.getAttribute('data-window')));
          if (state.workstream) next.set('scope', state.workstream);
          else next.delete('scope');
          if (state.date) next.set('date', state.date);
          if (persistAuditDay) next.set('audit_day', state.audit_day);
          else next.delete('audit_day');
          navigateCompass(next);
        });
      });
      const scopeSelect = document.getElementById('scope-select');
      if (scopeSelect) {
        const ids = collectScopedWorkstreamIds(payload, stateForSummary(state));
        const validIdSet = new Set(
          workstreamRowsForLookup(payload)
            .map((row) => String(row && row.idea_id ? row.idea_id : "").trim())
            .filter((token) => WORKSTREAM_RE.test(token))
        );
        const selectedScope = WORKSTREAM_RE.test(String(state.workstream || ""))
          ? String(state.workstream || "")
          : "";
        // Preserve a valid deep-linked scope even when the current Compass
        // window has no local signal for it yet, so the selector never
        // contradicts the visible scoped state/pill.
        const optionIds = selectedScope && validIdSet.has(selectedScope) && !ids.includes(selectedScope)
          ? [selectedScope, ...ids]
          : ids;
        const windowKey = state.window === "24h" ? "24h" : "48h";
        const scopedBriefMap = payload.standup_brief_scoped && payload.standup_brief_scoped[windowKey] && typeof payload.standup_brief_scoped[windowKey] === "object"
          ? payload.standup_brief_scoped[windowKey]
          : {};
        const originalOrder = new Map(optionIds.map((id, index) => [id, index]));
        const briefSourceRank = (id) => {
          const brief = scopedBriefMap[id] && typeof scopedBriefMap[id] === "object" ? scopedBriefMap[id] : null;
          const status = String(brief && brief.status ? brief.status : "").trim().toLowerCase();
          if (status !== "ready") return 3;
          const source = String(brief && brief.source ? brief.source : "").trim().toLowerCase();
          if (source === "provider") return 0;
          if (source === "cache") return 1;
          return 2;
        };
        const sortedOptionIds = optionIds.slice().sort((left, right) => {
          const leftId = String(left || "").trim();
          const rightId = String(right || "").trim();
          if (selectedScope && leftId === selectedScope) return -1;
          if (selectedScope && rightId === selectedScope) return 1;
          const rankDelta = briefSourceRank(leftId) - briefSourceRank(rightId);
          if (rankDelta !== 0) return rankDelta;
          return Number(originalOrder.get(leftId) || 0) - Number(originalOrder.get(rightId) || 0);
        });
        scopeSelect.innerHTML = [
          '<option value="">Global</option>',
          ...sortedOptionIds.map((id) => `<option value="${escapeHtml(id)}">${escapeHtml(id)}</option>`),
        ].join("");
        scopeSelect.value = sortedOptionIds.includes(selectedScope) ? selectedScope : "";
        if (!scopeSelect.dataset.bound) {
          scopeSelect.dataset.bound = "1";
          scopeSelect.addEventListener('change', () => {
            const next = new URLSearchParams(window.location.search);
            next.delete('workstream');
            next.set('tab', 'compass');
            next.set('window', state.window);
            if (state.date) next.set('date', state.date);
            if (persistAuditDay) next.set('audit_day', state.audit_day);
            else next.delete('audit_day');
            const selected = String(scopeSelect.value || "").trim();
            if (WORKSTREAM_RE.test(selected)) {
              next.set('scope', selected);
            } else {
              next.delete('scope');
            }
            navigateCompass(next);
          });
        }
      }
      const globalButton = document.getElementById('scope-global');
      if (globalButton) {
        globalButton.classList.toggle('active', !state.workstream);
        globalButton.setAttribute('aria-pressed', String(!state.workstream));
        if (!globalButton.dataset.bound) {
          globalButton.dataset.bound = "1";
          globalButton.addEventListener('click', () => {
            if (!state.workstream) return;
            const next = new URLSearchParams(window.location.search);
            next.delete('workstream');
            next.set('tab', 'compass');
            next.set('window', state.window);
            if (state.date) next.set('date', state.date);
            if (persistAuditDay) next.set('audit_day', state.audit_day);
            else next.delete('audit_day');
            next.delete('scope');
            navigateCompass(next);
          });
        }
      }
      const auditDayInput = document.getElementById('audit-day-input');
      const bounds = rollingThirtyDayBounds(payload);
      const todayToken = calendarMaxDateToken(payload) || toLocalDateToken(new Date());
      if (auditDayInput) {
        const fallbackDay = todayToken || bounds.max;
        const preferredDay = DATE_RE.test(state.audit_day)
          ? state.audit_day
          : (state.date !== "live" && DATE_RE.test(state.date) ? state.date : fallbackDay);
        const selectedDay = clampDateToken(preferredDay, bounds.min, bounds.max) || fallbackDay;
        auditDayInput.disabled = false;
        auditDayInput.min = bounds.min;
        auditDayInput.max = bounds.max;
        auditDayInput.value = selectedDay;
        if (!auditDayInput.dataset.bound) {
          auditDayInput.dataset.bound = "1";
          auditDayInput.addEventListener('change', () => {
            const next = new URLSearchParams(window.location.search);
            next.delete('workstream');
            next.set('tab', 'compass');
            next.set('window', state.window);
            if (state.workstream) next.set('scope', state.workstream);
            else next.delete('scope');
            const selected = clampDateToken(
              String(auditDayInput.value || "").trim(),
              bounds.min,
              bounds.max
            );
            if (selected && DATE_RE.test(selected)) {
              next.set('audit_day', selected);
              next.set('date', selected === todayToken ? 'live' : selected);
            } else {
              next.set('date', 'live');
              next.delete('audit_day');
            }
            navigateCompass(next);
          });
        }
      }
      const scopePill = document.getElementById('scope-pill');
      const touchedIds = collectScopedWorkstreamIds(payload, state);
      const workstreamTitles = workstreamTitleLookup(payload);
      scopePill.textContent = state.workstream
        ? `Scope: ${state.workstream}`
        : `Scope: Global (${touchedIds.length} touched)`;
      if (state.workstream && WORKSTREAM_RE.test(state.workstream)) {
        const tooltip = workstreamTooltipText(
          state.workstream,
          workstreamTitles,
          `Scoped to ${state.workstream}`,
        );
        scopePill.setAttribute("data-tooltip", tooltip);
        scopePill.setAttribute("aria-label", `${state.workstream}: ${tooltip}`);
      } else {
        scopePill.removeAttribute("data-tooltip");
        scopePill.removeAttribute("aria-label");
      }
      const auditDayPill = document.getElementById('audit-day-pill');
      if (auditDayPill) {
        auditDayPill.textContent = `Audit Day: ${state.audit_day || "-"}`;
      }
    }

    function showFallback(message) {
      const target = document.getElementById("kpi-grid");
      target.innerHTML = `<article class="stat"><p class="kpi-label">Runtime Unavailable</p><p class="muted">${message}</p></article>`;
      CURRENT_STANDUP_BRIEF = null;
      const briefCard = document.getElementById("standup-brief-card");
      if (briefCard) {
        briefCard.classList.add("standup-brief-card--compact");
        if (briefCard.dataset) briefCard.dataset.briefMode = "status";
      }
      const copyButton = document.getElementById("copy-brief");
      if (copyButton) {
        copyButton.classList.add("hidden");
        copyButton.disabled = true;
        copyButton.setAttribute("aria-hidden", "true");
        copyButton.setAttribute("tabindex", "-1");
      }
      showBriefCopyStatus("");
      document.getElementById("digest-list").innerHTML = '<div class="empty">Runtime data unavailable.</div>';
      const executionWavesHost = document.getElementById("execution-waves-host");
      if (executionWavesHost) executionWavesHost.innerHTML = "";
      const releaseGroupsHost = document.getElementById("release-groups-host");
      if (releaseGroupsHost) releaseGroupsHost.innerHTML = "";
      document.getElementById("current-workstreams").innerHTML = '<p class="empty">Run sync to regenerate Compass runtime snapshots.</p>';
      document.getElementById("timeline").innerHTML = '<div class="empty">No timeline data available.</div>';
      document.getElementById("risk-list").innerHTML = '<p class="empty">No risk payload available.</p>';
      markCompassSurfaceReady(true);
    }

    let briefCopyStatusTimer = null;

    function showBriefCopyStatus(message, tone = "info") {
      const notice = document.getElementById("brief-copy-status");
      if (!notice) return;
      const text = String(message || "").trim();
      if (briefCopyStatusTimer) {
        window.clearTimeout(briefCopyStatusTimer);
        briefCopyStatusTimer = null;
      }
      if (!text) {
        notice.classList.add("hidden");
        notice.classList.remove("warn");
        notice.textContent = "";
        notice.title = "";
        return;
      }
      notice.classList.remove("hidden");
      notice.classList.toggle("warn", tone === "warn");
      notice.textContent = text;
      notice.title = text;
      briefCopyStatusTimer = window.setTimeout(() => {
        notice.classList.add("hidden");
        notice.classList.remove("warn");
        notice.textContent = "";
        notice.title = "";
        briefCopyStatusTimer = null;
      }, 3200);
    }

    let liveBriefWarmPollTimer = null;
    const LIVE_BRIEF_WARM_POLL_INTERVAL_MS = 1500;
    const LIVE_BRIEF_WARM_POLL_MAX_ATTEMPTS = 8;
    const LIVE_BRIEF_WARM_POLL_RETRY_REASONS = new Set([
      "provider_deferred",
      "rate_limited",
      "timeout",
      "transport_error",
    ]);

    function clearLiveBriefWarmPoll() {
      if (!liveBriefWarmPollTimer) return;
      window.clearTimeout(liveBriefWarmPollTimer);
      liveBriefWarmPollTimer = null;
    }

    function shouldPollForWarmBrief(brief, state) {
      const safeBrief = brief && typeof brief === "object" ? brief : {};
      const safeState = state && typeof state === "object" ? state : {};
      if (String(safeState.date || "live").trim() !== "live") return false;
      if (String(safeBrief.status || "").trim() !== "ready") {
        const diagnostics = safeBrief.diagnostics && typeof safeBrief.diagnostics === "object" ? safeBrief.diagnostics : {};
        const reason = String(diagnostics.reason || "").trim().toLowerCase();
        return LIVE_BRIEF_WARM_POLL_RETRY_REASONS.has(reason);
      }
      const notice = safeBrief.notice && typeof safeBrief.notice === "object" ? safeBrief.notice : {};
      const noticeReason = String(notice.reason || "").trim().toLowerCase();
      return noticeReason === "scoped_provider_deferred_showing_global"
        || noticeReason === "scoped_provider_deferred_showing_wider_global";
    }

    async function resolveCompassRuntimeView(rawState, runtime) {
      let payload = runtime.payload;
      let normalized = normalizeStateWithPayload(rawState, payload);
      payload = await augmentLiveHistoryIntoPayload(payload, normalized.state);
      normalized = normalizeStateWithPayload(rawState, payload);
      const state = normalized.state;
      const summaryState = stateForSummary(state);
      const summaryEvents = filterEventsByWindow(payload, summaryState);
      return { payload, normalized, state, summaryState, summaryEvents };
    }

    async function renderCompassWarmBriefOnly(rawState, runtime) {
      if (!runtime.payload) {
        return { brief: null, state: rawState };
      }
      const resolved = await resolveCompassRuntimeView(rawState, runtime);
      renderDigest(resolved.payload, resolved.summaryState, resolved.summaryEvents);
      return { brief: CURRENT_STANDUP_BRIEF, state: resolved.state };
    }

    async function renderCompassRuntime(rawState, runtime) {
      if (!runtime.payload) {
        showFallback("Compass runtime files were not found. Run `odylith sync --repo-root . --force`.");
        return { brief: null, state: rawState };
      }
      const resolved = await resolveCompassRuntimeView(rawState, runtime);
      const { payload, normalized, state, summaryState, summaryEvents } = resolved;
      const summaryTransactions = filterTransactionsByWindow(payload, summaryState);
      const timelineEvents = filterEventsByWindow(payload, state);
      const timelineTransactions = filterTransactionsByWindow(payload, state);
      syncControls(state, summaryEvents, payload);

      const notices = [];
      const freshnessNotice = staleRuntimeNotice(payload, state);
      if (freshnessNotice) notices.push(freshnessNotice);
      if (runtime.warning) notices.push(runtime.warning);
      if (normalized.warnings.length) notices.push(...normalized.warnings);
      if (runtime.source.startsWith("history:")) {
        notices.push(`Loaded historical snapshot ${runtime.source.replace("history:", "")}.`);
      }
      const uniqueNotices = dedupeNoticeLines(notices);
      if (uniqueNotices.length) {
        const hasWarn = uniqueNotices.some((line) => isWarningNotice(line));
        showStatus(uniqueNotices.join(" "), hasWarn ? "warn" : "info");
      } else {
        showStatus("");
      }

      renderKpis(payload, summaryState, summaryEvents);
      renderDigest(payload, summaryState, summaryEvents);
      renderExecutionWaves(payload, summaryState);
      renderReleaseGroups(payload, summaryState);
      renderCurrentWorkstreams(payload, summaryState, summaryEvents, summaryTransactions, state);
      renderTimeline(payload, state, timelineEvents, timelineTransactions);
      renderRisks(payload, summaryState);
      markCompassSurfaceReady(true);
      return { brief: CURRENT_STANDUP_BRIEF, state };
    }

    function scheduleLiveBriefWarmPoll(rawState, rendered, attempt = 0) {
      clearLiveBriefWarmPoll();
      const renderedState = rendered && rendered.state && typeof rendered.state === "object" ? rendered.state : rawState;
      const renderedBrief = rendered && rendered.brief && typeof rendered.brief === "object" ? rendered.brief : null;
      if (!shouldPollForWarmBrief(renderedBrief, renderedState)) return;
      if (attempt >= LIVE_BRIEF_WARM_POLL_MAX_ATTEMPTS) return;
      liveBriefWarmPollTimer = window.setTimeout(async () => {
        liveBriefWarmPollTimer = null;
        if (shellRedirectInProgress()) return;
        const nextRawState = params();
        const runtime = await loadRuntime(nextRawState);
        if (!runtime.payload) return;
        const rerendered = await renderCompassWarmBriefOnly(nextRawState, runtime);
        if (!shouldPollForWarmBrief(rerendered.brief, rerendered.state)) return;
        scheduleLiveBriefWarmPoll(nextRawState, rerendered, attempt + 1);
      }, LIVE_BRIEF_WARM_POLL_INTERVAL_MS);
    }

    function bindCopyBrief() {
      const button = document.getElementById("copy-brief");
      if (!button) return;
      button.addEventListener("click", async () => {
        const lines = [];
        const brief = CURRENT_STANDUP_BRIEF && typeof CURRENT_STANDUP_BRIEF === "object" ? CURRENT_STANDUP_BRIEF : null;
        if (brief && String(brief.status || "").trim() === "ready") {
          const notice = brief.notice && typeof brief.notice === "object" ? brief.notice : {};
          const noticeTitle = String(notice.title || "").trim();
          const noticeMessage = String(notice.message || "").trim();
          if (noticeTitle && noticeMessage) {
            lines.push(`${noticeTitle}: ${noticeMessage}`);
          } else if (noticeTitle) {
            lines.push(noticeTitle);
          } else if (noticeMessage) {
            lines.push(noticeMessage);
          }
          const sections = Array.isArray(brief.sections) ? brief.sections : [];
          STANDUP_BRIEF_SECTION_SPECS.forEach((spec) => {
            const section = sections.find((row) => row && String(row.key || "").trim() === spec.key);
            const bullets = Array.isArray(section && section.bullets) ? section.bullets : [];
            lines.push(`${spec.label}:`);
            bullets.forEach((bullet) => {
              const text = String(bullet && bullet.text ? bullet.text : "").trim();
              if (!text) return;
              lines.push(`- ${text}`);
            });
          });
        } else if (brief) {
          const diagnostics = brief.diagnostics && typeof brief.diagnostics === "object" ? brief.diagnostics : {};
          lines.push(String(diagnostics.title || "AI standup brief unavailable").trim() || "AI standup brief unavailable");
          if (String(diagnostics.message || "").trim()) {
            lines.push(String(diagnostics.message || "").trim());
          }
          if (String(diagnostics.reason || "").trim()) {
            lines.push(`Reason: ${String(diagnostics.reason || "").trim()}`);
          }
        }
        if (!lines.length) {
          const fallback = Array.from(document.querySelectorAll("#digest-list .empty, #digest-list .brief-status-copy"))
            .map((node) => String(node.textContent || "").trim())
            .filter(Boolean);
          lines.push(...fallback);
        }
        if (!lines.length) return;
        const payload = lines.join("\n");
        try {
          await navigator.clipboard.writeText(payload);
          showBriefCopyStatus("Standup brief copied to clipboard.", "info");
        } catch (error) {
          console.warn("clipboard write failed", error);
          showBriefCopyStatus("Clipboard write failed. You can still copy from the Standup Brief panel.", "warn");
        }
      });
    }

    async function init() {
      markCompassSurfaceReady(false);
      clearLiveBriefWarmPoll();
      if (shellRedirectInProgress()) {
        return;
      }
      showBriefCopyStatus("");
      bindCopyBrief();
      const rawState = params();

      const runtime = await loadRuntime(rawState);
      const rendered = await renderCompassRuntime(rawState, runtime);
      scheduleLiveBriefWarmPoll(rawState, rendered);
    }
