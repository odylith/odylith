    const WORKSTREAM_RE = /^B-\d{3,}$/;
    const DIAGRAM_RE = /^D-\d{3,}$/;
    const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
    const COMPASS_TIME_ZONE = "America/Los_Angeles";
    const DATE_PARTS_FORMATTER = new Intl.DateTimeFormat("en-US", {
      timeZone: COMPASS_TIME_ZONE,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    const HOUR_PARTS_FORMATTER = new Intl.DateTimeFormat("en-US", {
      timeZone: COMPASS_TIME_ZONE,
      hour: "2-digit",
      hour12: false,
    });
    const TIME_FORMATTER = new Intl.DateTimeFormat("en-US", {
      timeZone: COMPASS_TIME_ZONE,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
    const DAY_HEADER_FORMATTER = new Intl.DateTimeFormat("en-US", {
      timeZone: COMPASS_TIME_ZONE,
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "2-digit",
    });
    const DATETIME_FORMATTER = new Intl.DateTimeFormat("en-US", {
      timeZone: COMPASS_TIME_ZONE,
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
    const STANDUP_BRIEF_SECTION_SPECS = [
      { key: "completed", label: "Completed in this window" },
      { key: "current_execution", label: "Current execution" },
      { key: "next_planned", label: "Next planned" },
      { key: "risks_to_watch", label: "Risks to watch" },
    ];
    let CURRENT_STANDUP_BRIEF = null;
function compassShell() {
  const shell = window.__ODYLITH_COMPASS_SHELL__;
  return shell && typeof shell === "object" ? shell : {};
}
    function initQuickTooltips() {
  const QUICK_TOOLTIP_BIND_KEY = "compassQuickTooltipBound";
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

initQuickTooltips();

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function splitDigestLine(line) {
      const token = String(line || "").trim();
      const idx = token.indexOf(":");
      if (idx <= 0) {
        return { header: token, body: "" };
      }
      return {
        header: token.slice(0, idx + 1).trim(),
        body: token.slice(idx + 1).trim(),
      };
    }

    function splitDigestBodyToBullets(body) {
      const source = String(body || "").replace(/\s+/g, " ").trim();
      if (!source) return [];

      const pipeSplit = source
        .split(/\s+\|\s+/)
        .map((token) => token.trim())
        .filter(Boolean);
      const chunks = pipeSplit.length ? pipeSplit : [source];

      const bullets = [];
      for (const chunk of chunks) {
        const parts = chunk
          .split(/;\s+(?=[A-Z0-9`])/)
          .map((token) => token.trim())
          .filter(Boolean);
        if (parts.length) {
          bullets.push(...parts);
        } else if (chunk) {
          bullets.push(chunk);
        }
      }
      return bullets.length ? bullets : [source];
    }

    function hasStructuredStandupBriefPayload(payload) {
      if (!payload || typeof payload !== "object") return false;
      const globalBrief = payload.standup_brief && typeof payload.standup_brief === "object";
      const scopedBrief = payload.standup_brief_scoped && typeof payload.standup_brief_scoped === "object";
      return Boolean(globalBrief || scopedBrief);
    }

    function standupBriefToDigestLines(brief) {
      if (!brief || typeof brief !== "object" || String(brief.status || "") !== "ready") return [];
      const sections = Array.isArray(brief.sections) ? brief.sections : [];
      return STANDUP_BRIEF_SECTION_SPECS.map((spec) => {
        const section = sections.find((row) => row && String(row.key || "").trim() === spec.key) || {};
        const bullets = Array.isArray(section.bullets) ? section.bullets : [];
        const bulletTexts = bullets
          .map((bullet) => {
            const text = String(bullet && bullet.text ? bullet.text : "").trim();
            if (!text) return "";
            return text;
          })
          .filter(Boolean);
        return bulletTexts.length ? `${spec.label}: ${bulletTexts.join(" | ")}` : `${spec.label}:`;
      });
    }

    function unavailableStandupBrief(message, diagnostics = {}) {
      return {
        status: "unavailable",
        source: "unavailable",
        fingerprint: "",
        generated_utc: "",
        diagnostics: {
          reason: String(diagnostics.reason || "missing_brief").trim() || "missing_brief",
          message: String(message || diagnostics.message || "No standup brief is available for this view.").trim(),
          provider: String(diagnostics.provider || "").trim(),
          config_source: String(diagnostics.config_source || "").trim(),
          config_path: String(diagnostics.config_path || "").trim(),
          attempted_utc: String(diagnostics.attempted_utc || "").trim(),
          provider_failure_code: String(diagnostics.provider_failure_code || "").trim(),
          provider_failure_detail: String(diagnostics.provider_failure_detail || "").trim(),
          validation_errors: Array.isArray(diagnostics.validation_errors) ? diagnostics.validation_errors : [],
        },
        sections: [],
      };
    }

    function scopedWorkstreamRow(payload, workstreamId) {
      const target = String(workstreamId || "").trim();
      if (!target) return null;
      const rows = workstreamRowsForLookup(payload);
      return rows.find((row) => row && String(row.idea_id || "").trim() === target) || null;
    }

    function scopedWindowActivity(row, windowKey) {
      const activity = row && row.activity && typeof row.activity === "object" ? row.activity : {};
      const windowActivity = activity && activity[windowKey] && typeof activity[windowKey] === "object"
        ? activity[windowKey]
        : {};
      return {
        commitCount: Number(windowActivity.commit_count || 0),
        localChangeCount: Number(windowActivity.local_change_count || 0),
        fileTouchCount: Number(windowActivity.file_touch_count || 0),
      };
    }

    function quietWindowStandupBrief(workstreamId, windowKey) {
      const hourLabel = windowKey === "48h" ? "48" : "24";
      return unavailableStandupBrief(
        `${String(workstreamId || "This scope").trim()} was quiet in the last ${hourLabel} hours, so Compass has nothing new to brief for that scope.`,
        {
          reason: "scoped_window_inactive",
          title: "Nothing moved in this window",
        },
      );
    }

    function cloneStructuredBrief(brief) {
      return JSON.parse(JSON.stringify(brief && typeof brief === "object" ? brief : {}));
    }

    function scopedFallbackToGlobalBrief(globalBrief, workstreamId, message, reason) {
      const cloned = cloneStructuredBrief(globalBrief);
      cloned.notice = {
        title: "Showing the global live brief",
        message: String(message || "").trim(),
        reason: String(reason || "scoped_brief_showing_global").trim(),
      };
      cloned.scope_fallback = {
        workstream: String(workstreamId || "").trim(),
        mode: "global_brief",
      };
      return cloned;
    }

    function scopedLiveBriefFallbackMessage(workstreamId, diagnostics) {
      const scopedWorkstream = String(workstreamId || "This scope").trim() || "This scope";
      const safeDiagnostics = diagnostics && typeof diagnostics === "object" ? diagnostics : {};
      const reason = String(safeDiagnostics.reason || "").trim().toLowerCase();
      if (reason === "provider_deferred") {
        return `${scopedWorkstream} still needs its own brief. Compass is showing the global live brief for now.`;
      }
      if (reason === "rate_limited") {
        return `${scopedWorkstream} is waiting on narration provider capacity. Compass is showing the global live brief for now.`;
      }
      if (reason === "credits_exhausted") {
        return `${scopedWorkstream} is waiting on narration provider budget. Compass is showing the global live brief for now.`;
      }
      if (reason === "timeout") {
        return `${scopedWorkstream} asked the narration provider for a scoped brief, but the reply took too long. Compass is showing the global live brief while it retries in the background.`;
      }
      if (reason === "invalid_batch") {
        return `${scopedWorkstream} got a scoped provider reply, but the brief was not usable yet. Compass is showing the global live brief while it retries in the background.`;
      }
      if (reason === "provider_unavailable" || reason === "transport_error" || reason === "auth_error" || reason === "provider_error") {
        return `${scopedWorkstream} ran into a narration provider problem. That may be capacity, budget, access, or provider health, so Compass is showing the global live brief for now.`;
      }
      return `Compass could not load a scoped live brief for ${scopedWorkstream}, so it is showing the global live brief for now.`;
    }

    function standupBriefForState(payload, state) {
      const key = state.window === "24h" ? "24h" : "48h";
      if (hasStructuredStandupBriefPayload(payload)) {
        const scopedWorkstream = WORKSTREAM_RE.test(String(state && state.workstream ? state.workstream : "").trim())
          ? String(state.workstream || "").trim()
          : "";
        const hasScopedSelection = Boolean(scopedWorkstream);
        const globalBrief = payload.standup_brief && payload.standup_brief[key] && typeof payload.standup_brief[key] === "object"
          ? payload.standup_brief[key]
          : null;
        const scopedMap = payload.standup_brief_scoped && payload.standup_brief_scoped[key] && typeof payload.standup_brief_scoped[key] === "object"
          ? payload.standup_brief_scoped[key]
          : {};
        const scopedBrief = scopedWorkstream && scopedMap[scopedWorkstream] && typeof scopedMap[scopedWorkstream] === "object"
          ? scopedMap[scopedWorkstream]
          : null;
        const scopedReady = scopedBrief && String(scopedBrief.status || "").trim() === "ready" ? scopedBrief : null;
        const globalReady = globalBrief && String(globalBrief.status || "").trim() === "ready" ? globalBrief : null;
        const scopedReadySource = String(scopedReady && scopedReady.source ? scopedReady.source : "").trim();
        const globalReadySource = String(globalReady && globalReady.source ? globalReady.source : "").trim();
        if (hasScopedSelection && scopedReady) return scopedReady;
        if (hasScopedSelection && scopedBrief) {
          const diagnostics = scopedBrief.diagnostics && typeof scopedBrief.diagnostics === "object" ? scopedBrief.diagnostics : {};
          const reason = String(diagnostics.reason || "").trim().toLowerCase();
          if (reason === "scoped_window_inactive") {
            return scopedBrief;
          }
          if (globalReady) {
            const fallbackReason = reason || "scoped_brief_unavailable";
            const message = scopedLiveBriefFallbackMessage(scopedWorkstream, diagnostics);
            return scopedFallbackToGlobalBrief(globalReady, scopedWorkstream, message, `scoped_${fallbackReason}_showing_global`);
          }
          return scopedBrief;
        }
        if (hasScopedSelection) {
          const scopedRow = scopedWorkstreamRow(payload, scopedWorkstream);
          const activity = scopedWindowActivity(scopedRow, key);
          if (scopedRow && activity.commitCount <= 0 && activity.localChangeCount <= 0 && activity.fileTouchCount <= 0) {
            if (globalReady) {
              return scopedFallbackToGlobalBrief(
                globalReady,
                scopedWorkstream,
                `${scopedWorkstream} was quiet in this window, so Compass is showing the global live brief instead.`,
                "scoped_window_quiet_showing_global",
              );
            }
            return quietWindowStandupBrief(scopedWorkstream, key);
          }
          if (globalReady) {
            return scopedFallbackToGlobalBrief(
              globalReady,
              scopedWorkstream,
              `Compass does not have a scoped live brief for ${scopedWorkstream} yet, so it is showing the global live brief for now.`,
              "scoped_brief_missing_showing_global",
            );
          }
          return unavailableStandupBrief(
            `No scoped standup brief is available for ${scopedWorkstream}.`,
            { reason: "scoped_brief_missing" },
          );
        }
        if (globalReady && (globalReadySource === "provider" || globalReadySource === "cache")) return globalReady;
        if (globalReady) return globalReady;
        if (scopedReady && (scopedReadySource === "provider" || scopedReadySource === "cache")) return scopedReady;
        if (scopedReady) return scopedReady;
        if (globalBrief) return globalBrief;
        return unavailableStandupBrief("No structured standup brief is available for this view.");
      }
      return unavailableStandupBrief("No structured standup brief is available for this view.");
    }

    function radarWorkstreamHref(workstreamId, { view = "" } = {}) {
      const code = String(workstreamId || "").trim();
      if (!WORKSTREAM_RE.test(code)) return "";
      const query = new URLSearchParams();
      query.set("tab", "radar");
      query.set("workstream", code);
      if (String(view || "").trim()) {
        query.set("view", String(view || "").trim());
      }
      return `../index.html?${query.toString()}`;
    }

    function atlasDiagramHref(diagramId, state, preferredWorkstream = "") {
      const code = String(diagramId || "").trim();
      if (!DIAGRAM_RE.test(code)) return "";
      const query = new URLSearchParams();
      query.set("tab", "atlas");
      query.set("diagram", code);
      const scopedWorkstream = WORKSTREAM_RE.test(String(preferredWorkstream || "").trim())
        ? String(preferredWorkstream || "").trim()
        : (state.workstream && WORKSTREAM_RE.test(state.workstream) ? state.workstream : "");
      if (scopedWorkstream) {
        query.set("workstream", scopedWorkstream);
      }
      return `../index.html?${query.toString()}`;
    }

    function briefLinkContext(payload, state) {
      return {
        state,
        workstreamTitles: workstreamTitleLookup(payload),
        planLookup: planHrefLookup(payload),
      };
    }

    function digestTokenHref(token, context) {
      const code = String(token || "").trim();
      if (WORKSTREAM_RE.test(code)) {
        return radarWorkstreamHref(code);
      }
      if (DIAGRAM_RE.test(code)) {
        return atlasDiagramHref(code, context && context.state ? context.state : { workstream: "" });
      }
      return "";
    }

    function linkTokenTooltipAttrs(token, context) {
      const code = String(token || "").trim();
      if (!code) return "";
      const workstreamTitles = context && context.workstreamTitles && typeof context.workstreamTitles === "object"
        ? context.workstreamTitles
        : {};
      if (WORKSTREAM_RE.test(code)) {
        const baseText = workstreamTooltipText(code, workstreamTitles, `Workstream ${code}`);
        const actionText = "Open workstream in Radar";
        return ` data-tooltip="${escapeHtml(`${baseText} · ${actionText}`)}" aria-label="${escapeHtml(`${code}: ${baseText}. ${actionText}.`)}"`;
      }
      if (DIAGRAM_RE.test(code)) {
        const actionText = `Open Atlas diagram ${code}`;
        return ` data-tooltip="${escapeHtml(actionText)}" aria-label="${escapeHtml(actionText)}"`;
      }
      return "";
    }

    function linkifyNarrativeText(text, context) {
      const source = String(text || "");
      if (!source) return "";
      const tokenRe = /\b(B-\d{3,}|D-\d{3,})\b/g;
      const chunks = [];
      let cursor = 0;
      let match = tokenRe.exec(source);
      while (match !== null) {
        const start = Number(match.index || 0);
        const token = String(match[1] || "");
        if (start > cursor) chunks.push(escapeHtml(source.slice(cursor, start)));
        const href = digestTokenHref(token, context);
        if (href) {
          const tooltipAttrs = linkTokenTooltipAttrs(token, context);
          chunks.push(
            `<a class="digest-link" href="${escapeHtml(href)}" target="_top"${tooltipAttrs}>${escapeHtml(token)}</a>`
          );
        } else {
          chunks.push(escapeHtml(token));
        }
        cursor = start + token.length;
        match = tokenRe.exec(source);
      }
      if (cursor < source.length) {
        chunks.push(escapeHtml(source.slice(cursor)));
      }
      return chunks.join("");
    }

    function workstreamSlug(value) {
      const token = String(value || "").trim().toLowerCase();
      if (!token) return "";
      return token
        .replace(/[^a-z0-9-]+/g, "-")
        .replace(/^-+/, "")
        .replace(/-+$/, "");
    }

    function normalizeRepoPath(value) {
      const token = String(value || "").trim();
      if (!token) return "";
      return token.startsWith("./") ? token.slice(2) : token;
    }

    function workstreamRowsForLookup(payload) {
      const catalog = Array.isArray(payload && payload.workstream_catalog) ? payload.workstream_catalog : [];
      const current = Array.isArray(payload && payload.current_workstreams) ? payload.current_workstreams : [];
      const merged = new Map();
      catalog.forEach((row) => {
        const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
        if (!ideaId) return;
        merged.set(ideaId, row);
      });
      current.forEach((row) => {
        const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
        if (!ideaId) return;
        merged.set(ideaId, row);
      });
      return merged.size ? Array.from(merged.values()) : [];
    }

    function planLinkLookup(payload) {
      const rows = workstreamRowsForLookup(payload);
      const byWorkstream = Object.create(null);
      const byPlanFile = Object.create(null);
      rows.forEach((row) => {
        const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
        if (!WORKSTREAM_RE.test(ideaId)) return;
        const links = row && row.links && typeof row.links === "object" ? row.links : {};
        const planFile = normalizeRepoPath(String(links.plan_file || "").trim());
        if (!planFile) return;
        const href = radarWorkstreamHref(ideaId, { view: "plan" });
        byWorkstream[ideaId] = href;
        byPlanFile[planFile] = { href, idea_id: ideaId };
      });
      return { byWorkstream, byPlanFile };
    }

    function radarWorkstreamHref(workstreamId, options = {}) {
      const token = String(workstreamId || "").trim();
      const params = new URLSearchParams();
      params.set("tab", "radar");
      if (WORKSTREAM_RE.test(token)) params.set("workstream", token);
      const view = String(options && options.view ? options.view : "").trim().toLowerCase();
      if (view) params.set("view", view);
      return `../index.html?${params.toString()}`;
    }

    function planHrefLookup(payload) {
      return planLinkLookup(payload).byWorkstream;
    }

    function workstreamTitleLookup(payload) {
      const rows = workstreamRowsForLookup(payload);
      const lookup = Object.create(null);
      rows.forEach((row) => {
        const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
        if (!WORKSTREAM_RE.test(ideaId)) return;
        const title = String(row && row.title ? row.title : "").trim();
        if (!title) return;
        lookup[ideaId] = title;
      });
      return lookup;
    }

    function workstreamNarrativeLookup(payload) {
      const rows = workstreamRowsForLookup(payload);
      const lookup = Object.create(null);
      rows.forEach((row) => {
        const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
        if (!WORKSTREAM_RE.test(ideaId)) return;
        const why = row && row.why && typeof row.why === "object" ? row.why : {};
        const plan = row && row.plan && typeof row.plan === "object" ? row.plan : {};
        lookup[ideaId] = {
          title: String(row && row.title ? row.title : "").trim(),
          status: String(row && row.status ? row.status : "").trim(),
          implemented_summary: String(row && row.implemented_summary ? row.implemented_summary : "").trim(),
          problem: String(why && why.problem ? why.problem : "").trim(),
          proposed_solution: String(why && why.proposed_solution ? why.proposed_solution : "").trim(),
          opportunity: String(why && why.opportunity ? why.opportunity : "").trim(),
          why_now: String(why && why.why_now ? why.why_now : "").trim(),
          founder_pov: String(why && why.founder_pov ? why.founder_pov : "").trim(),
          next_tasks: Array.isArray(plan && plan.next_tasks) ? plan.next_tasks.map((item) => String(item || "").trim()).filter(Boolean) : [],
        };
      });
      return lookup;
    }

    function executionWavePayload(payload) {
      const source = payload && payload.execution_waves && typeof payload.execution_waves === "object"
        ? payload.execution_waves
        : {};
      const summary = source && source.summary && typeof source.summary === "object" ? source.summary : {};
      const programs = Array.isArray(source.programs) ? source.programs : [];
      const programCatalog = Array.isArray(source.program_catalog) ? source.program_catalog : programs;
      const workstreams = source && source.workstreams && typeof source.workstreams === "object"
        ? source.workstreams
        : {};
      return { summary, programs, programCatalog, workstreams };
    }

    function executionWavePrograms(payload) {
      return executionWavePayload(payload).programs;
    }

    function executionWaveProgramCatalog(payload) {
      return executionWavePayload(payload).programCatalog;
    }

    function executionWaveProgramByUmbrella(payload, umbrellaId) {
      const token = String(umbrellaId || "").trim();
      if (!token) return null;
      const liveProgram = executionWavePrograms(payload).find((row) => String(row && row.umbrella_id ? row.umbrella_id : "").trim() === token) || null;
      if (liveProgram) return liveProgram;
      return executionWaveProgramCatalog(payload).find((row) => String(row && row.umbrella_id ? row.umbrella_id : "").trim() === token) || null;
    }

    function workstreamWavePrograms(payload, workstreamId) {
      const token = String(workstreamId || "").trim();
      if (!token) return [];
      const byWorkstream = executionWavePayload(payload).workstreams;
      return Array.isArray(byWorkstream[token]) ? byWorkstream[token] : [];
    }

    function executionWaveEntriesForScope(payload, scopedWorkstream) {
      const programs = executionWavePrograms(payload);
      const token = String(scopedWorkstream || "").trim();
      if (!token) {
        return {
          entries: programs.map((program) => ({ program, context: null })),
          scopedContexts: [],
          scopedUmbrellaProgram: null,
          hasRelevantScope: false,
        };
      }

      const scopedContexts = workstreamWavePrograms(payload, token).filter((row) => row && typeof row === "object");
      const scopedUmbrellaProgram = executionWaveProgramByUmbrella(payload, token);
      if (scopedUmbrellaProgram) {
        return {
          entries: [{ program: scopedUmbrellaProgram, context: null }],
          scopedContexts,
          scopedUmbrellaProgram,
          hasRelevantScope: true,
        };
      }

      if (scopedContexts.length) {
        const entries = scopedContexts
          .map((context) => {
            const umbrellaId = String(context && context.umbrella_id ? context.umbrella_id : "").trim();
            if (!umbrellaId) return null;
            const program = executionWaveProgramByUmbrella(payload, umbrellaId);
            return program ? { program, context } : null;
          })
          .filter(Boolean);
        return {
          entries,
          scopedContexts,
          scopedUmbrellaProgram: null,
          hasRelevantScope: entries.length > 0,
        };
      }

      return {
        entries: [],
        scopedContexts: [],
        scopedUmbrellaProgram: null,
        hasRelevantScope: false,
      };
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
          <div class="execution-wave-card-shell execution-wave-card-shell-full-copy">
            <div class="execution-wave-title-row">
              <div class="execution-wave-title">${escapeHtml(waveLabel)}</div>
              <span class="label execution-wave-label wave-chip-program">${escapeHtml(sequenceChip)}</span>
              ${progressChip ? `<span class="label execution-wave-label wave-progress-chip">${escapeHtml(progressChip)}</span>` : ""}
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
            <div class="execution-wave-sub">${escapeHtml(summary || "No wave summary recorded.")}</div>
            ${compactSummaryLine ? `<div class="execution-wave-compact"><div class="execution-wave-compact-line execution-wave-compact-line-strong">${escapeHtml(compactSummaryLine)}</div></div>` : ""}
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
          ${contextChips.length ? `<div class="execution-wave-focus-stat-rail">${contextChips.join("")}</div>` : ""}
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

    function workstreamTooltipText(workstreamId, workstreamTitles, fallbackText) {
      const id = String(workstreamId || "").trim();
      if (!id) return "";
      const title = workstreamTitles && typeof workstreamTitles[id] === "string"
        ? String(workstreamTitles[id] || "").trim()
        : "";
      if (title) return title;
      const fallback = String(fallbackText || "").trim();
      return fallback || `Workstream ${id}`;
    }

    function workstreamTooltipAttrs(workstreamId, workstreamTitles, fallbackText) {
      const id = String(workstreamId || "").trim();
      if (!id) return "";
      const tooltip = workstreamTooltipText(id, workstreamTitles, fallbackText);
      if (!tooltip) return "";
      return ` data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(`${id}: ${tooltip}`)}"`;
    }

    function registryComponentTooltipText(componentRow) {
      const componentId = String(componentRow && componentRow.component_id ? componentRow.component_id : "").trim().toLowerCase();
      if (!componentId) return "";
      const name = String(componentRow && componentRow.name ? componentRow.name : "").trim();
      return name || `Registry component ${componentId}`;
    }

    function registryComponentTooltipAttrs(componentRow, fallbackText) {
      const componentId = String(componentRow && componentRow.component_id ? componentRow.component_id : "").trim().toLowerCase();
      if (!componentId) return "";
      const tooltip = registryComponentTooltipText(componentRow) || String(fallbackText || "").trim();
      if (!tooltip) return "";
      return ` data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(`${componentId}: ${tooltip}`)}"`;
    }

    function compactDigestWorkstreamLabels(text, workstreamTitles) {
      const source = String(text || "");
      if (!source) return "";
      const rows = workstreamTitles && typeof workstreamTitles === "object"
        ? Object.entries(workstreamTitles)
            .map(([ideaId, title]) => [String(ideaId || "").trim(), String(title || "").trim()])
            .filter(([ideaId, title]) => WORKSTREAM_RE.test(ideaId) && title.length > 0)
            .sort((left, right) => right[1].length - left[1].length)
        : [];
      if (!rows.length) return source;
      let out = source;
      rows.forEach(([ideaId, title]) => {
        const label = `${title} (${ideaId})`;
        if (!label) return;
        out = out.split(label).join(ideaId);
      });
      return out;
    }

    function planFileHrefLookup(payload) {
      return planLinkLookup(payload).byPlanFile;
    }

    function isPlanIndexPath(value) {
      const token = normalizeRepoPath(value).toLowerCase();
      return token === "odylith/technical-plans/index.md";
    }

    function isPlanMarkdownPath(value) {
      const token = normalizeRepoPath(value);
      if (!token) return false;
      if (isPlanIndexPath(token)) return false;
      return token.startsWith("odylith/technical-plans/") && token.toLowerCase().endsWith(".md");
    }

    function planMarkdownHref(value) {
      const token = normalizeRepoPath(value);
      if (!isPlanMarkdownPath(token)) return "";
      const encodedPath = token
        .split("/")
        .filter(Boolean)
        .map((segment) => encodeURIComponent(segment))
        .join("/");
      if (!encodedPath) return "";
      return `../../${encodedPath}`;
    }
