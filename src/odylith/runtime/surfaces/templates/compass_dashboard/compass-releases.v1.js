    function compassReleaseSummaryPayload(payload) {
      return payload && payload.release_summary && typeof payload.release_summary === "object"
        ? payload.release_summary
        : {};
    }

    function compassReleaseDisplayName(release) {
      const row = release && typeof release === "object" ? release : {};
      const nameLabel = String(row.name || row.version || row.tag || row.display_label || row.effective_name || "").trim();
      if (nameLabel) return nameLabel;
      return String(row.release_id || "").trim();
    }

    function compassReleaseStatusChipClass(status) {
      const token = String(status || "").trim().toLowerCase();
      if (token === "active") return "wave-status-active";
      if (token === "planned" || token === "draft") return "wave-status-planned";
      if (token === "closed" || token === "shipped" || token === "terminal") return "wave-status-complete";
      return "wave-chip-program";
    }

    function compassReleaseStatusLabel(status) {
      const token = String(status || "").trim().toLowerCase();
      if (!token) return "";
      return `${token.charAt(0).toUpperCase()}${token.slice(1)}`;
    }

    function compassReleaseMemberStatusClass(status) {
      const token = String(status || "").trim().toLowerCase();
      if (token === "implementation") return "wave-status-active";
      if (token === "planning" || token === "queued") return "wave-status-planned";
      if (token === "finished" || token === "parked" || token === "superseded") return "wave-status-complete";
      return "wave-chip-program";
    }

    function compassReleaseWorkstreamIds(release, workstreamRows) {
      const explicit = Array.isArray(release && release.active_workstreams)
        ? release.active_workstreams.map((item) => String(item || "").trim()).filter((item) => WORKSTREAM_RE.test(item))
        : [];
      if (explicit.length) return explicit;
      const releaseId = String(release && release.release_id ? release.release_id : "").trim();
      if (!releaseId) return [];
      return workstreamRows
        .map((row) => {
          const activeRelease = row && row.release && typeof row.release === "object" ? row.release : {};
          const activeReleaseId = String(activeRelease.release_id || "").trim();
          const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
          return activeReleaseId === releaseId && WORKSTREAM_RE.test(ideaId) ? ideaId : "";
        })
        .filter(Boolean);
    }

    function compassReleaseCompletedWorkstreamIds(release, workstreamRows) {
      if (release && typeof release === "object" && Object.prototype.hasOwnProperty.call(release, "completed_workstreams")) {
        return Array.isArray(release && release.completed_workstreams)
          ? release.completed_workstreams.map((item) => String(item || "").trim()).filter((item) => WORKSTREAM_RE.test(item))
          : [];
      }
      const removedSummary = `Removed from ${compassReleaseDisplayName(release)}`;
      return workstreamRows
        .map((row) => {
          const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
          const status = String(row && row.status ? row.status : "").trim().toLowerCase();
          const releaseHistorySummary = String(row && row.release_history_summary ? row.release_history_summary : "").trim();
          return WORKSTREAM_RE.test(ideaId) && status === "finished" && releaseHistorySummary === removedSummary ? ideaId : "";
        })
        .filter(Boolean);
    }

    function numericProgressOrNull(value) {
      if (value === null || value === undefined || value === "") return null;
      const ratio = Number(value);
      return Number.isFinite(ratio) ? ratio : null;
    }

    function compassReleaseGroups(payload, state) {
      const summary = compassReleaseSummaryPayload(payload);
      const catalog = Array.isArray(summary.catalog) ? summary.catalog.filter((row) => row && typeof row === "object") : [];
      const currentReleaseId = String(summary && summary.current_release && summary.current_release.release_id ? summary.current_release.release_id : "").trim();
      const nextReleaseId = String(summary && summary.next_release && summary.next_release.release_id ? summary.next_release.release_id : "").trim();
      const scopedWorkstream = WORKSTREAM_RE.test(String(state && state.workstream ? state.workstream : "").trim())
        ? String(state.workstream || "").trim()
        : "";
      const workstreamRows = workstreamRowsForLookup(payload);
      const workstreamTitles = workstreamTitleLookup(payload);
      const workstreamById = new Map(
        workstreamRows
          .map((row) => {
            const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
            return WORKSTREAM_RE.test(ideaId) ? [ideaId, row] : null;
          })
          .filter(Boolean)
      );

      const groups = catalog
        .map((release) => {
          const releaseId = String(release.release_id || "").trim();
          const memberIds = compassReleaseWorkstreamIds(release, workstreamRows);
          const completedMemberIds = [...new Set(
            compassReleaseCompletedWorkstreamIds(release, workstreamRows).filter((ideaId) => !memberIds.includes(ideaId))
          )];
          const members = memberIds.map((ideaId) => {
            const row = workstreamById.get(ideaId) || {};
            const plan = row && row.plan && typeof row.plan === "object" ? row.plan : {};
            const progressRatio = numericProgressOrNull(
              Object.prototype.hasOwnProperty.call(plan, "display_progress_ratio")
                ? plan.display_progress_ratio
                : (Object.prototype.hasOwnProperty.call(plan, "progress_ratio") ? plan.progress_ratio : null)
            );
            const progressLabel = String(plan && plan.display_progress_label ? plan.display_progress_label : "").trim();
            return {
              idea_id: ideaId,
              title: String(row && row.title ? row.title : workstreamTitles[ideaId] || "").trim() || ideaId,
              status: String(row && row.status ? row.status : "").trim().toLowerCase(),
              progress_ratio: progressRatio,
              progress_label: progressLabel,
            };
          });
          const completedMembers = completedMemberIds.map((ideaId) => {
            const row = workstreamById.get(ideaId) || {};
            const plan = row && row.plan && typeof row.plan === "object" ? row.plan : {};
            const progressRatio = numericProgressOrNull(
              Object.prototype.hasOwnProperty.call(plan, "display_progress_ratio")
                ? plan.display_progress_ratio
                : (Object.prototype.hasOwnProperty.call(plan, "progress_ratio") ? plan.progress_ratio : null)
            );
            const progressLabel = String(plan && plan.display_progress_label ? plan.display_progress_label : "").trim();
            return {
              idea_id: ideaId,
              title: String(row && row.title ? row.title : workstreamTitles[ideaId] || "").trim() || ideaId,
              status: String(row && row.status ? row.status : "").trim().toLowerCase(),
              progress_ratio: progressRatio,
              progress_label: progressLabel,
            };
          });
          return {
            release_id: releaseId,
            display_label: compassReleaseDisplayName(release) || releaseId,
            status: String(release.status || "").trim().toLowerCase(),
            version: String(release.version || "").trim(),
            tag: String(release.tag || "").trim(),
            notes: String(release.notes || "").trim(),
            aliases: Array.isArray(release.aliases) ? release.aliases.map((item) => String(item || "").trim()).filter(Boolean) : [],
            is_current: releaseId === currentReleaseId,
            is_next: releaseId === nextReleaseId,
            members,
            member_ids: memberIds,
            completed_members: completedMembers,
            completed_member_ids: completedMemberIds,
          };
        })
        .filter((group) => {
          if (scopedWorkstream) return group.member_ids.includes(scopedWorkstream) || group.completed_member_ids.includes(scopedWorkstream);
          return (
            group.is_current
            || group.is_next
            || group.status === "active"
            || group.status === "planned"
            || group.status === "draft"
            || group.members.length > 0
            || group.completed_members.length > 0
          );
        });

      groups.sort((left, right) => {
        const leftVisibleCount = Number(left.members.length || 0) + Number(left.completed_members.length || 0);
        const rightVisibleCount = Number(right.members.length || 0) + Number(right.completed_members.length || 0);
        const leftRank = left.is_current ? 0 : (left.is_next ? 1 : (leftVisibleCount > 0 ? 2 : 3));
        const rightRank = right.is_current ? 0 : (right.is_next ? 1 : (rightVisibleCount > 0 ? 2 : 3));
        if (leftRank !== rightRank) return leftRank - rightRank;
        const leftCount = leftVisibleCount;
        const rightCount = rightVisibleCount;
        if (rightCount !== leftCount) return rightCount - leftCount;
        return String(left.display_label || left.release_id || "").localeCompare(String(right.display_label || right.release_id || ""));
      });
      return groups;
    }

    function renderReleaseGroups(payload, state) {
      const host = document.getElementById("release-groups-host");
      if (!host) return;
      const clearHost = () => {
        host.innerHTML = "";
      };
      const ensureTarget = () => {
        host.innerHTML = '<article class="card release-groups-card"><h2>Release Targets</h2><div id="release-groups" class="muted"></div></article>';
        return host.querySelector("#release-groups");
      };
      const scopedWorkstream = WORKSTREAM_RE.test(String(state && state.workstream ? state.workstream : "").trim())
        ? String(state.workstream || "").trim()
        : "";
      const workstreamTitles = workstreamTitleLookup(payload);
      const groups = compassReleaseGroups(payload, state);
      if (!groups.length) {
        clearHost();
        return;
      }
      const target = ensureTarget();
      if (!target) {
        clearHost();
        return;
      }
      const renderMemberChip = (ideaId, options = {}) => {
        const token = String(ideaId || "").trim();
        if (!WORKSTREAM_RE.test(token)) return "";
        const tooltip = workstreamTooltipText(token, workstreamTitles, `Open radar for ${token}`);
        const tone = options && options.selected ? " wave-member-selected" : "";
        return `<a class="chip chip-link execution-wave-chip-link${tone}" href="${escapeHtml(radarWorkstreamHref(token))}" target="_top" data-tooltip="${escapeHtml(tooltip)}" aria-label="${escapeHtml(`${token}: ${tooltip}`)}">${escapeHtml(token)}</a>`;
      };
      const formatMemberProgress = (member) => {
        const explicitLabel = String(member && member.progress_label ? member.progress_label : "").trim();
        if (explicitLabel) return explicitLabel;
        const ratio = numericProgressOrNull(member && Object.prototype.hasOwnProperty.call(member, "progress_ratio") ? member.progress_ratio : null);
        if (ratio === null) return "";
        return `${Math.round(Math.min(Math.max(ratio, 0), 1) * 100)}% progress`;
      };
      const renderMemberRow = (member) => {
        const ideaId = String(member && member.idea_id ? member.idea_id : "").trim();
        if (!WORKSTREAM_RE.test(ideaId)) return "";
        const title = String(member && member.title ? member.title : "").trim() || ideaId;
        const status = String(member && member.status ? member.status : "").trim().toLowerCase();
        const statusLabel = compassReleaseStatusLabel(status);
        const progressLabel = formatMemberProgress(member);
        const cardClassNames = ["execution-wave-card", compassReleaseMemberStatusClass(status)];
        if (ideaId === scopedWorkstream) cardClassNames.push("is-member");
        const titleChips = [
          statusLabel ? `<span class="label execution-wave-label ${compassReleaseMemberStatusClass(status)}">${escapeHtml(statusLabel)}</span>` : "",
        ].filter(Boolean);
        const metaChips = [
          progressLabel ? `<span class="label execution-wave-label wave-progress-chip">${escapeHtml(progressLabel)}</span>` : "",
          ideaId === scopedWorkstream ? '<span class="label execution-wave-label wave-current-chip">Selected</span>' : "",
        ].filter(Boolean);
        return `
          <article class="${cardClassNames.join(" ")}">
            <div class="execution-wave-card-summary">
              <div class="execution-wave-card-shell">
                <div class="execution-wave-card-copy">
                  <div class="execution-wave-member-head">
                    <div class="execution-wave-member-title-chips">
                      ${renderMemberChip(ideaId, { selected: ideaId === scopedWorkstream })}
                      ${titleChips.join("")}
                    </div>
                    <div class="execution-wave-title">${escapeHtml(title)}</div>
                  </div>
                </div>
                ${metaChips.length ? `<div class="execution-wave-card-meta"><div class="execution-wave-card-stat-rail">${metaChips.join("")}</div></div>` : ""}
              </div>
            </div>
          </article>
        `;
      };
      const renderReleaseSection = (group) => {
        const memberCount = Number(group.members.length || 0);
        const completedCount = Number(group.completed_members.length || 0);
        const visibleMembers = [...group.members, ...group.completed_members];
        const memberLabel = `${memberCount} targeted workstream${memberCount === 1 ? "" : "s"}`;
        const completedLabel = `${completedCount} completed workstream${completedCount === 1 ? "" : "s"}`;
        const releaseProgress = executionWaveWorkstreamProgress(visibleMembers, {
          resolveWorkstreamProgress: (row) => row && Object.prototype.hasOwnProperty.call(row, "progress_ratio") ? row.progress_ratio : null,
        });
        const releaseCompletion = executionWaveWorkstreamCompletion(visibleMembers, {
          resolveWorkstreamStatus: (row) => row && row.status ? row.status : "",
        });
        const contextLine = scopedWorkstream
          ? `${scopedWorkstream} currently targets this release.`
          : (group.is_current && !group.members.length && group.completed_members.length
            ? "Current release remains visible until maintainers explicitly ship or close it."
            : (group.is_current
            ? "Current release target across active workstreams."
            : (group.is_next ? "Next release target across active workstreams." : "Explicit release target from the release registry.")));
        const lifecycleBits = [
          compassReleaseStatusLabel(group.status) ? `${compassReleaseStatusLabel(group.status)} release` : "",
          group.aliases.length ? `Aliases: ${group.aliases.join(", ")}` : "",
          memberLabel,
          completedCount ? completedLabel : "",
          releaseCompletion.totalCount > 0
            ? `${releaseCompletion.completeCount}/${releaseCompletion.totalCount} complete`
            : "",
        ].filter(Boolean);
        const titleChips = [
          group.is_current ? '<span class="label execution-wave-label wave-current-chip">Target Release</span>' : "",
        ].filter(Boolean);
        const sectionChips = [
          group.is_next ? '<span class="label execution-wave-label wave-status-planned">Next</span>' : "",
          compassReleaseStatusLabel(group.status)
            ? `<span class="label execution-wave-label ${compassReleaseStatusChipClass(group.status)}">${escapeHtml(compassReleaseStatusLabel(group.status))}</span>`
            : "",
          `<span class="label execution-wave-label wave-chip-program">${escapeHtml(memberLabel)}</span>`,
          completedCount ? `<span class="label execution-wave-label wave-status-complete">${escapeHtml(completedLabel)}</span>` : "",
          releaseProgress.percent ? `<span class="label execution-wave-label wave-progress-chip">${escapeHtml(`Overall ${releaseProgress.percent} progress`)}</span>` : "",
        ].filter(Boolean);
        const openAttr = scopedWorkstream ? " open" : "";
        const panels = [];
        if (group.members.length || !group.completed_members.length) {
          panels.push(`
                <div class="execution-wave-panel">
                  <div class="execution-wave-group-label">Targeted Workstreams</div>
                  <div class="execution-wave-sequence">
                    ${group.members.length
                      ? group.members.map(renderMemberRow).filter(Boolean).join("")
                      : '<span class="execution-wave-empty">No targeted workstreams.</span>'}
                  </div>
                </div>
          `);
        }
        if (group.completed_members.length) {
          panels.push(`
                <div class="execution-wave-panel">
                  <div class="execution-wave-group-label">Completed Workstreams</div>
                  <div class="execution-wave-sequence">
                    ${group.completed_members.map(renderMemberRow).filter(Boolean).join("")}
                  </div>
                </div>
          `);
        }
        return `
          <details class="execution-wave-section"${openAttr}>
            <summary class="execution-wave-section-summary execution-wave-section-summary-compass">
              <div class="execution-wave-section-copy">
                <div class="execution-wave-section-title-row">
                  <div class="execution-wave-section-title">${escapeHtml(group.display_label)}</div>
                  ${titleChips.length ? `<div class="execution-wave-section-title-meta">${titleChips.join("")}</div>` : ""}
                </div>
                <div class="execution-wave-section-line">${escapeHtml(contextLine)}</div>
                <div class="execution-wave-section-line execution-wave-section-line-muted">${escapeHtml(lifecycleBits.join(" · "))}</div>
              </div>
              <span class="execution-wave-section-toggle execution-wave-section-toggle-triangle" aria-hidden="true"></span>
              ${sectionChips.length ? `<div class="execution-wave-section-meta execution-wave-section-meta-bottom">${sectionChips.join("")}</div>` : ""}
            </summary>
            <div class="execution-wave-section-body">
              <div class="execution-wave-board">
                ${panels.join("")}
              </div>
            </div>
          </details>
        `;
      };

      target.innerHTML = `<div class="execution-wave-program-stack execution-wave-program-stack-release">${groups.map(renderReleaseSection).join("")}</div>`;
    }
