    function numericProgressOrNull(value) {
      if (value === null || value === undefined || value === "") return null;
      const numericValue = Number(value);
      return Number.isFinite(numericValue) ? numericValue : null;
    }

    function renderExecutionWaves(payload, state) {
      const host = document.getElementById("execution-waves-host");
      if (!host) return;
      const clearHost = () => {
        host.innerHTML = "";
      };
      const ensureTarget = () => {
        host.innerHTML = '<article class="card execution-waves-card"><h2>Programs</h2><div id="execution-waves" class="muted"></div></article>';
        return host.querySelector("#execution-waves");
      };
      const programs = executionWavePrograms(payload);
      if (!programs.length) {
        clearHost();
        return;
      }
      const scopedWorkstream = WORKSTREAM_RE.test(String(state && state.workstream ? state.workstream : ""))
        ? String(state.workstream || "")
        : "";
      const disclosureGroup = "programs";
      const scopedWaveView = executionWaveEntriesForScope(payload, scopedWorkstream);
      if (scopedWorkstream && !scopedWaveView.hasRelevantScope) {
        clearHost();
        return;
      }
      const target = ensureTarget();
      if (!target) {
        clearHost();
        return;
      }
      const waveSummary = executionWavePayload(payload).summary || {};
      const workstreamRows = workstreamRowsForLookup(payload);
      const workstreamTitles = workstreamTitleLookup(payload);
      const workstreamNarratives = workstreamNarrativeLookup(payload);
      const planFileLookup = planFileHrefLookup(payload);
      const workstreamStatusById = new Map(
        workstreamRows
          .map((row) => {
            const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
            const status = String(row && row.status ? row.status : "").trim().toLowerCase();
            return [ideaId, status || ""];
          })
          .filter(([ideaId]) => ideaId)
      );
      const workstreamProgressById = new Map(
        workstreamRows
          .map((row) => {
            const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
            const plan = row && typeof row.plan === "object" ? row.plan : {};
            const progressRatio = numericProgressOrNull(
              Object.prototype.hasOwnProperty.call(plan, "display_progress_ratio")
                ? plan.display_progress_ratio
                : (Object.prototype.hasOwnProperty.call(plan, "progress_ratio") ? plan.progress_ratio : null)
            );
            return [ideaId, progressRatio];
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
      const renderMemberChip = (ideaId, options = {}) => {
        const token = String(ideaId || "").trim();
        if (!WORKSTREAM_RE.test(token)) return "";
        const tooltip = workstreamTooltipText(token, workstreamTitles, `Open radar for ${token}`);
        const tone = options && options.selected ? " wave-member-selected" : "";
        return `<a class="chip chip-link execution-wave-chip-link${tone}" href="${escapeHtml(radarWorkstreamHref(token))}" target="_top" data-execution-wave-scope="${escapeHtml(token)}" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(`${token}: ${tooltip}`)}">${escapeHtml(token)}</a>`;
      };
      const planHrefForPath = (value) => {
        const token = normalizeRepoPath(value);
        if (!token) return "";
        const details = planFileLookup[token];
        if (details && typeof details === "object") {
          const href = String(details.href || "").trim();
          if (href) return href;
        }
        return planMarkdownHref(token);
      };

      const entries = scopedWaveView.entries;
      const scopedContexts = scopedWaveView.scopedContexts;
      const primaryScopedContext = scopedContexts[0] && typeof scopedContexts[0] === "object" ? scopedContexts[0] : null;
      const primaryProgram = scopedWaveView.scopedUmbrellaProgram
        || (primaryScopedContext
          ? executionWaveProgramByUmbrella(payload, primaryScopedContext.umbrella_id)
          : (entries[0] && entries[0].program ? entries[0].program : null));
      const relevantProgramCount = entries.length;
      const relevantActiveCount = entries.reduce((count, entry) => count + Number(entry && entry.program && entry.program.active_wave_count ? entry.program.active_wave_count : 0), 0);
      const relevantWaveCount = entries.reduce((count, entry) => count + Number(entry && entry.program && entry.program.wave_count ? entry.program.wave_count : 0), 0);
      const sectionProgramCount = scopedWorkstream ? relevantProgramCount : Number(waveSummary.program_count || programs.length || 0);
      const sectionActiveCount = scopedWorkstream ? relevantActiveCount : Number(waveSummary.active_wave_count || 0);
      const sectionWaveCount = scopedWorkstream ? relevantWaveCount : Number(waveSummary.wave_count || 0);
      const renderOptions = {
        escapeHtml,
        emptyStateClass: "execution-wave-empty",
        renderMemberChip,
        planHrefForPath,
        resolveWorkstreamStatus,
        resolveWorkstreamProgress,
        selectedBadgeLabel: "Selected",
        selectedCardClass: "is-member",
        sectionHeaderVariant: "compass",
      };
      const formatExecutionWaveProgramTitle = (program) => {
        const umbrellaTitle = String(program && program.umbrella_title ? program.umbrella_title : "").trim();
        const umbrellaId = String(program && program.umbrella_id ? program.umbrella_id : "").trim();
        return umbrellaTitle && umbrellaId
          ? `${umbrellaTitle} (${umbrellaId})`
          : (umbrellaTitle || umbrellaId);
      };
      const disclosureKeyForProgram = (program) => {
        const umbrellaId = String(program && program.umbrella_id ? program.umbrella_id : "").trim();
        if (umbrellaId) return `program:${umbrellaId}`;
        const label = formatExecutionWaveProgramTitle(program);
        return label ? `program:${label}` : "program:execution-waves";
      };
      const executionWaveCompletionChip = (program) => {
        const completionLabel = String(program && program.completion_label || "").trim();
        if (!completionLabel) return "";
        return `<span class="label execution-wave-label wave-status-complete">${escapeHtml(completionLabel)}</span>`;
      };
      const renderProgramSection = (entry) => {
        const program = entry && entry.program ? entry.program : null;
        if (!program) return "";
        const persistenceKey = disclosureKeyForProgram(program);
        const sectionChips = [];
        const programWaveCount = Number(program && program.wave_count || 0);
        if (programWaveCount > 0) {
          sectionChips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${programWaveCount}-wave program`)}</span>`);
        }
        const completionChip = executionWaveCompletionChip(program);
        if (completionChip) sectionChips.push(completionChip);
        const programProgress = executionWaveProgramProgress(program, { resolveWorkstreamStatus, resolveWorkstreamProgress });
        if (programProgress.percent) {
          sectionChips.push(`<span class="label execution-wave-label wave-progress-chip">${escapeHtml(`Overall ${programProgress.percent} progress`)}</span>`);
        }
        const programSummaryLine = executionWaveSummaryLine(program, { resolveWorkstreamStatus });
        return renderExecutionWaveSection(
          {
            title: formatExecutionWaveProgramTitle(program),
            entries: [entry],
            selectedWorkstreamId: scopedWorkstream,
            persistenceKey,
            contextLine: "",
            summaryLine: programSummaryLine,
            sectionChips,
            openByDefault: resolveCompassDisclosureOpen(disclosureGroup, state, persistenceKey, false),
          },
        {
          ...renderOptions,
          hideProgramFocusTitle: true,
          hideProgramFocusPanel: true,
          boardWrapperClass: "",
          sectionClassName: "execution-wave-section-flat",
        },
      );
      };

      if (entries.length > 1) {
        target.innerHTML = `<div class="execution-wave-program-stack">${entries.map(renderProgramSection).filter(Boolean).join("")}</div>`;
        bindCompassDisclosurePersistence(target, disclosureGroup, state);
        return;
      }

      const sectionLabel = sectionProgramCount === 1 && primaryProgram
        ? `${String(primaryProgram.umbrella_title || primaryProgram.umbrella_id || "").trim()} (${String(primaryProgram.umbrella_id || "").trim()})`
        : `${sectionProgramCount} relevant umbrella programs`;
      const sectionContextLine = scopedWaveView.scopedUmbrellaProgram
        ? "Umbrella-owned execution waves for this program."
        : primaryScopedContext
        ? `${scopedWorkstream} participates across ${String(primaryScopedContext.wave_span_label || "").trim() || "the program"} as ${String(primaryScopedContext.role_label || "").trim() || "a member"}.`
        : (scopedWorkstream ? "" : "Umbrella-owned execution waves for active programs.");
      const sectionSummaryLine = sectionProgramCount === 1 && primaryProgram
        ? executionWaveSummaryLine(primaryProgram, { resolveWorkstreamStatus })
        : `${sectionProgramCount} programs · ${sectionActiveCount} active waves · ${sectionWaveCount} total waves`;
      const sectionChips = [];
      if (sectionProgramCount > 1) {
        sectionChips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${sectionProgramCount} programs`)}</span>`);
      } else if (primaryProgram && Number(primaryProgram.wave_count || 0) > 0) {
        sectionChips.push(`<span class="label execution-wave-label wave-chip-program">${escapeHtml(`${Number(primaryProgram.wave_count || 0)}-wave program`)}</span>`);
        const completionChip = executionWaveCompletionChip(primaryProgram);
        if (completionChip) sectionChips.push(completionChip);
        const programProgress = executionWaveProgramProgress(primaryProgram, { resolveWorkstreamStatus, resolveWorkstreamProgress });
        if (programProgress.percent) {
          sectionChips.push(`<span class="label execution-wave-label wave-progress-chip">${escapeHtml(`Overall ${programProgress.percent} progress`)}</span>`);
        }
      }
      if (sectionActiveCount > 0) {
        sectionChips.push(`<span class="label execution-wave-label wave-status-active">${escapeHtml(`${sectionActiveCount} active`)}</span>`);
      }
      if (primaryScopedContext) {
        const waveSpan = String(primaryScopedContext.wave_span_label || "").trim();
        const roleLabel = String(primaryScopedContext.role_label || "").trim();
        if (waveSpan) sectionChips.push(`<span class="label execution-wave-label wave-status-planned">${escapeHtml(waveSpan)}</span>`);
        if (roleLabel) sectionChips.push(`<span class="label execution-wave-label wave-role-chip">${escapeHtml(roleLabel)}</span>`);
      }
      const sectionPersistenceKey = disclosureKeyForProgram(primaryProgram);

      target.innerHTML = renderExecutionWaveSection(
        {
          title: primaryProgram
            ? formatExecutionWaveProgramTitle(primaryProgram)
            : "Execution Waves",
          entries,
          selectedWorkstreamId: scopedWorkstream,
          persistenceKey: sectionPersistenceKey,
          programLabel: sectionLabel,
          contextLine: sectionContextLine,
          summaryLine: sectionSummaryLine,
          sectionChips,
          openByDefault: resolveCompassDisclosureOpen(disclosureGroup, state, sectionPersistenceKey, false),
        },
        {
          ...renderOptions,
          hideProgramFocusPanel: true,
          boardWrapperClass: "",
          sectionClassName: "execution-wave-section-flat",
        },
      );
      bindCompassDisclosurePersistence(target, disclosureGroup, state);

      Array.from(target.querySelectorAll("[data-execution-wave-scope]")).forEach((node) => {
        if (String(node.tagName || "").toLowerCase() === "a") {
          return;
        }
        node.addEventListener("click", (event) => {
          event.preventDefault();
          const token = String(node.getAttribute("data-execution-wave-scope") || "").trim();
          if (!WORKSTREAM_RE.test(token) || token === scopedWorkstream) return;
          const next = new URLSearchParams(stateToQuery(state));
          next.set("scope", token);
          navigateCompass(next);
        });
      });
    }
