    function releaseHeroLabel(release) {
      const releaseRow = release && typeof release === "object" ? release : {};
      const nameLabel = String(releaseRow.name || "").trim();
      if (nameLabel) return nameLabel;
      const versionLabel = String(releaseRow.version || "").trim();
      if (versionLabel) return versionLabel;
      const effectiveLabel = String(
        releaseRow.effective_name || releaseRow.display_label || ""
      ).trim();
      if (effectiveLabel) return effectiveLabel;
      const tagLabel = String(releaseRow.tag || "").trim();
      if (tagLabel) return /^v\d/.test(tagLabel) ? tagLabel.slice(1) : tagLabel;
      return String(release && (release.release_id || "") || "").trim();
    }

    function heroKpiRows(base, state, touchedIds, riskRows, scopedTouch, commitCount, localCount) {
      const releaseSummary = payloadReleaseSummary(base.__payload);
      const currentRelease = releaseSummary.current_release || {};
      const rows = [
        ["Commits", state.workstream ? commitCount : Number(base.commits || 0)],
        ["Local Changes", state.workstream ? localCount : Number(base.local_changes || 0)],
        ["Touched Workstreams", state.workstream ? scopedTouch.size : touchedIds.length],
        ["Active Workstreams", Number(base.active_workstreams || 0)],
        ["Critical Risks", riskRows.bugs.length + riskRows.selfHost.length + riskRows.traceCritical.length + riskRows.stale.length],
        ["Completed Plans", Number(base.recent_completed_plans || 0)],
      ];
      const currentReleaseLabel = releaseHeroLabel(currentRelease);
      if (currentReleaseLabel) {
        rows.push(["Target Release", currentReleaseLabel, "stat-release-only"]);
      }
      return rows;
    }

    function payloadReleaseSummary(payload) {
      return payload && payload.release_summary && typeof payload.release_summary === "object"
        ? payload.release_summary
        : {};
    }

    function renderKpis(payload, state, events) {
      const key = state.window === "24h" ? "24h" : "48h";
      const base = { ...((payload.kpis && payload.kpis[key]) || {}), __payload: payload };
      const touchedIds = collectScopedWorkstreamIds(payload, state);
      const riskRows = resolveScopedRiskRows(payload, state);
      const scopedTouch = new Set();
      let commitCount = 0;
      let localCount = 0;
      for (const row of events) {
        if (row.kind === "commit") commitCount += 1;
        if (row.kind === "local_change") localCount += 1;
        const ws = Array.isArray(row.workstreams) ? row.workstreams : [];
        for (const item of ws) scopedTouch.add(String(item || "").trim());
      }

      const kpis = heroKpiRows(base, state, touchedIds, riskRows, scopedTouch, commitCount, localCount);
      const target = document.getElementById("kpi-grid");
      target.innerHTML = kpis.map(([label, value, cardClass]) => `
        <article class="stat${cardClass ? ` ${cardClass}` : ""}">
          ${label ? `<p class="kpi-label">${escapeHtml(label)}</p>` : ""}
          <p class="kpi-value">${escapeHtml(value)}</p>
        </article>
      `).join("");
    }

    function resolveScopedRiskRows(payload, state) {
      const risks = payload.risks || {};
      const bugs = Array.isArray(risks.bugs) ? risks.bugs.filter((row) => row.is_open_critical) : [];
      const selfHost = Array.isArray(risks.self_host) ? risks.self_host : [];
      const traceCritical = Array.isArray(risks.traceability_critical)
        ? risks.traceability_critical
        : (Array.isArray(risks.traceability) ? risks.traceability.filter((row) => String(row && row.severity ? row.severity : "").trim().toLowerCase() === "error") : []);
      const stale = Array.isArray(risks.stale_diagrams) ? risks.stale_diagrams : [];
      const scopedIds = new Set(collectScopedWorkstreamIds(payload, stateForSummary(state)));
      const isScopedView = WORKSTREAM_RE.test(String(state && state.workstream ? state.workstream : ""));
      const selectedScope = isScopedView ? String(state.workstream || "").trim() : "";
      const bounds = windowBounds(state, payload);

      const inWindow = (row) => {
        const dateToken = String(row && row.date ? row.date : "").trim();
        if (!DATE_RE.test(dateToken)) return true;
        if (!bounds || !(bounds.start instanceof Date) || !(bounds.end instanceof Date)) return true;
        const parsedDate = parseLocalDateToken(dateToken);
        if (!(parsedDate instanceof Date) || Number.isNaN(parsedDate.getTime())) return true;
        return parsedDate >= bounds.start && parsedDate <= bounds.end;
      };

      const keepByScope = (row) => {
        const ws = Array.isArray(row && row.workstreams)
          ? row.workstreams.map((token) => String(token || "").trim()).filter((token) => WORKSTREAM_RE.test(token))
          : [];
        if (selectedScope) {
          if (!ws.length && String(row && row.idea_id ? row.idea_id : "").trim()) {
            return String(row.idea_id || "").trim() === selectedScope;
          }
          return ws.includes(selectedScope);
        }
        if (!ws.length) {
          const ideaToken = String(row && row.idea_id ? row.idea_id : "").trim();
          if (!ideaToken) return true;
          return scopedIds.has(ideaToken);
        }
        return ws.some((token) => scopedIds.has(token));
      };

      return {
        bugs: bugs.filter((item) => inWindow(item) && keepByScope(item)),
        selfHost: selfHost.filter((item) => inWindow(item)),
        traceCritical: traceCritical.filter((item) => keepByScope(item)),
        stale: stale.filter((item) => keepByScope(item)),
      };
    }

    function renderRisks(payload, state) {
      const scoped = resolveScopedRiskRows(payload, state);
      const target = document.getElementById("risk-list");
      const blocks = [];

      for (const row of scoped.bugs.slice(0, 6)) {
        blocks.push(`<div class="risk"><strong>${escapeHtml(row.severity)}</strong> ${escapeHtml(row.title)} (${escapeHtml(row.status)})</div>`);
      }
      for (const row of scoped.selfHost.slice(0, 3)) {
        blocks.push(`<div class="risk"><strong>${escapeHtml(row.severity || "warning")}</strong> ${escapeHtml(row.message || "Self-host posture needs attention.")}</div>`);
      }
      for (const row of scoped.traceCritical.slice(0, 6)) {
        blocks.push(`<div class="risk"><strong>${escapeHtml(row.severity)}</strong> ${escapeHtml(row.message || row.category)}</div>`);
      }
      for (const row of scoped.stale.slice(0, 4)) {
        blocks.push(`<div class="risk"><strong>stale diagram</strong> ${escapeHtml(row.diagram_id)} ${escapeHtml(row.title)} (${escapeHtml(`${row.age_days}d`)})</div>`);
      }

      if (!blocks.length) {
        target.innerHTML = '<p class="empty">No critical risks in this window.</p>';
        return;
      }
      target.innerHTML = blocks.join("");
    }

    function briefEvidenceLookup(brief) {
      return brief && brief.evidence_lookup && typeof brief.evidence_lookup === "object"
        ? brief.evidence_lookup
        : {};
    }

    function evidenceEntriesForBullet(bullet, brief) {
      const lookup = briefEvidenceLookup(brief);
      const factIds = Array.isArray(bullet && bullet.fact_ids)
        ? bullet.fact_ids.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      return factIds
        .map((factId) => {
          const entry = lookup[factId];
          if (!entry || typeof entry !== "object") return null;
          const text = String(entry.text || "").trim();
          if (!text) return null;
          return text;
        })
        .filter(Boolean);
    }

    function renderBriefEvidence(bullet, brief, linkContext) {
      const entries = evidenceEntriesForBullet(bullet, brief);
      if (!entries.length) return "";
      const label = entries.length === 1 ? "Evidence" : `Evidence (${entries.length})`;
      const tooltip = entries.length === 1
        ? "Inspect the cited fact behind this bullet"
        : "Inspect the cited facts behind this bullet";
      const items = entries.map((text) => `
        <li class="brief-evidence-item">${linkifyNarrativeText(text, linkContext)}</li>
      `).join("");
      return `
        <details class="brief-evidence">
          <summary class="brief-evidence-toggle" data-tooltip="${escapeHtml(tooltip)}">${escapeHtml(label)}</summary>
          <div class="brief-evidence-panel">
            <ul class="brief-evidence-list">${items}</ul>
          </div>
        </details>
      `;
    }

    function renderBriefBullet(bullet, brief, linkContext) {
      const text = String(bullet && bullet.text ? bullet.text : "").trim();
      if (!text) return "";
      const evidenceHtml = renderBriefEvidence(bullet, brief, linkContext);
      return `
        <li class="brief-bullet">
          <span class="brief-bullet-copy">${linkifyNarrativeText(text, linkContext)}</span>
          ${evidenceHtml ? `<div class="brief-bullet-support">${evidenceHtml}</div>` : ""}
        </li>
      `;
    }

    function renderBriefMeta(brief) {
      if (!brief || typeof brief !== "object") return "";
      const source = String(brief.source || "").trim().toLowerCase();
      if (source === "provider" || source === "cache") {
        const generated = compactTimestamp(brief.generated_utc);
        return `
          <div class="standup-brief-meta">
            <span class="standup-brief-generated">Generated ${escapeHtml(generated)}</span>
          </div>
        `;
      }
      return "";
    }

    function briefHasRenderableNarrative(brief) {
      if (!brief || typeof brief !== "object") return false;
      if (String(brief.status || "").trim() !== "ready") return false;
      const source = String(brief.source || "").trim().toLowerCase();
      return source === "provider" || source === "cache";
    }

    function syncBriefPresentationChrome(brief) {
      const card = document.getElementById("standup-brief-card");
      const copyButton = document.getElementById("copy-brief");
      const copyStatus = document.getElementById("brief-copy-status");
      const hasNarrative = briefHasRenderableNarrative(brief);

      if (card) {
        card.classList.toggle("standup-brief-card--compact", !hasNarrative);
        if (card.dataset) {
          card.dataset.briefMode = hasNarrative ? "narrative" : "status";
        }
      }

      if (copyButton) {
        copyButton.classList.toggle("hidden", !hasNarrative);
        copyButton.disabled = !hasNarrative;
        if (hasNarrative) {
          copyButton.removeAttribute("aria-hidden");
          copyButton.removeAttribute("tabindex");
        } else {
          copyButton.setAttribute("aria-hidden", "true");
          copyButton.setAttribute("tabindex", "-1");
        }
      }

      if (!hasNarrative && copyStatus) {
        copyStatus.classList.add("hidden");
        copyStatus.classList.remove("warn");
        copyStatus.textContent = "";
        copyStatus.title = "";
      }
    }

    function visibleBriefNotice(brief) {
      const notice = brief && brief.notice && typeof brief.notice === "object" ? brief.notice : {};
      return notice;
    }

    function renderBriefNotice(brief) {
      const notice = visibleBriefNotice(brief);
      const title = String(notice.title || "").trim();
      const message = String(notice.message || "").trim();
      if (!title && !message) return "";
      return `
        <div class="brief-status-card brief-status-card--info">
          ${title ? `<div class="brief-status-title">${escapeHtml(title)}</div>` : ""}
          ${message ? `<div class="brief-status-copy">${escapeHtml(message)}</div>` : ""}
        </div>
      `;
    }

    function renderUnavailableBrief(brief) {
      const diagnostics = brief && brief.diagnostics && typeof brief.diagnostics === "object" ? brief.diagnostics : {};
      const title = String(diagnostics.title || "").trim() || "Standup brief unavailable";
      const message = String(diagnostics.message || "").trim() || "No standup brief is available for this view.";
      const retryUtc = String(diagnostics.next_retry_utc || "").trim();
      const retryCopy = retryUtc ? `Next retry ${compactTimestamp(retryUtc)}.` : "";
      return `
        <div class="brief-status-card brief-status-card--warn brief-status-card--compact" role="status" aria-live="polite">
          <div class="brief-status-title">${escapeHtml(title)}</div>
          <div class="brief-status-copy">${escapeHtml(message)}</div>
          ${retryCopy ? `<div class="brief-status-meta">${escapeHtml(retryCopy)}</div>` : ""}
        </div>
      `;
    }

    function renderReadyBrief(brief, linkContext) {
      const sections = Array.isArray(brief && brief.sections) ? brief.sections : [];
      const sectionHtml = STANDUP_BRIEF_SECTION_SPECS.map((spec) => {
        const section = sections.find((row) => row && String(row.key || "").trim() === spec.key) || { bullets: [] };
        const bullets = Array.isArray(section.bullets) ? section.bullets : [];
        const items = bullets
          .map((bullet) => renderBriefBullet(bullet, brief, linkContext))
          .filter(Boolean)
          .join("");
        return `
          <section class="brief-section">
            <div class="brief-section-title">${escapeHtml(spec.label)}</div>
            <div class="brief-section-body">${items ? `<ul class="brief-bullet-list">${items}</ul>` : ""}</div>
          </section>
        `;
      }).join("");
      return `
        <div class="standup-brief-sheet">
          ${renderBriefMeta(brief)}
          ${renderBriefNotice(brief)}
          <div class="standup-brief-sections">${sectionHtml}</div>
        </div>
      `;
    }

    function applyBriefDataset(target, brief, state) {
      if (!target || !target.dataset) return;
      const safeBrief = brief && typeof brief === "object" ? brief : {};
      const safeState = state && typeof state === "object" ? state : {};
      const scopedWorkstream = WORKSTREAM_RE.test(String(safeState.workstream || "").trim())
        ? String(safeState.workstream || "").trim()
        : "";
      const notice = visibleBriefNotice(safeBrief);
      const hasNotice = Boolean(String(notice.title || "").trim() || String(notice.message || "").trim());
      const dataset = {
        briefStatus: String(safeBrief.status || "").trim(),
        briefSource: String(safeBrief.source || "").trim().toLowerCase(),
        briefFingerprint: String(safeBrief.fingerprint || "").trim(),
        briefGeneratedUtc: String(safeBrief.generated_utc || "").trim(),
        briefCacheMode: String(safeBrief.cache_mode || "").trim().toLowerCase(),
        briefWindow: String(safeState.window || "").trim() === "48h" ? "48h" : "24h",
        briefScope: scopedWorkstream || "Global",
        briefHasNotice: hasNotice ? "true" : "false",
        briefNoticeReason: String(notice.reason || "").trim(),
      };
      Object.entries(dataset).forEach(([key, value]) => {
        target.dataset[key] = String(value || "");
      });
    }

    function renderDigest(payload, state, events) {  // eslint-disable-line no-unused-vars
      const target = document.getElementById("digest-list");
      const brief = standupBriefForState(payload, state);
      const linkContext = briefLinkContext(payload, state);
      CURRENT_STANDUP_BRIEF = brief;
      applyBriefDataset(target, brief, state);
      syncBriefPresentationChrome(brief);

      if (!brief || typeof brief !== "object") {
        target.innerHTML = "";
        return;
      }
      if (!briefHasRenderableNarrative(brief)) {
        target.innerHTML = renderUnavailableBrief(brief);
        return;
      }
      target.innerHTML = renderReadyBrief(brief, linkContext);
    }
