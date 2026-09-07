"""Present Casebook list cards and distinguish absent records from filtered results."""

LIST_PRESENTATION_JS = r"""    function casebookListPresentation({ rows, totalCount, selectedRoute, escapeHtml, displayTokenLabel }) {
      if (!rows.length) {
        const noCases = totalCount === 0;
        const listMessage = noCases
          ? "No Casebook cases have been recorded yet."
          : "No Casebook entries match the current filters.";
        const detailMessage = noCases
          ? "When you find a defect, ask Odylith to capture it with the expected behavior, actual behavior, and reproduction steps."
          : "Select a different filter or search term to inspect Casebook detail.";
        return {
          listHtml: `<div class="empty-state" role="status">${listMessage}</div>`,
          detailHtml: `<div class="empty-state" role="status">${detailMessage}</div>`,
          meta: "0 visible",
        };
      }
      const listHtml = rows.map((row) => {
        const coverage = row.intelligence_coverage && typeof row.intelligence_coverage === "object" ? row.intelligence_coverage : {};
        const capturedCount = Number(coverage.captured_count || 0);
        const totalFields = Number(coverage.total_fields || 0);
        const requiredMissingFields = Array.isArray(coverage.required_missing_fields)
          ? coverage.required_missing_fields.map((item) => String(item || "").trim()).filter(Boolean)
          : [];
        const active = row.bug_route === selectedRoute;
        const chips = [
          row.severity ? `<span class="list-chip ${/^p[01]$/i.test(String(row.severity || "")) ? "critical-chip" : ""}">${escapeHtml(row.severity)}</span>` : "",
          row.status ? `<span class="list-chip">${escapeHtml(displayTokenLabel(row.status))}</span>` : "",
          row.archive_bucket ? `<span class="list-chip archive-chip">${escapeHtml(row.archive_bucket)}</span>` : "",
          totalFields ? `<span class="list-chip ${requiredMissingFields.length ? "warn-chip" : ""}" data-tooltip="${escapeHtml(`${capturedCount}/${totalFields} recommended fields captured`)}">Intel</span>` : "",
        ].filter(Boolean).join("");
        return `
          <button type="button" class="bug-row${active ? " active" : ""}" data-bug="${escapeHtml(row.bug_route || "")}">
            <div class="bug-row-head">
              <div>
                ${row.bug_id ? `<p class="bug-row-kicker">${escapeHtml(row.bug_id)}</p>` : ""}
                <p class="bug-row-title">${escapeHtml(row.title || row.bug_key || "Bug")}</p>
              </div>
              <span class="bug-row-date">${escapeHtml(row.date || "-")}</span>
            </div>
            <p class="bug-row-summary">${escapeHtml(row.summary || row.components || "No summary available.")}</p>
            <div class="bug-row-meta">${chips}</div>
          </button>
        `;
      }).join("");
      return { listHtml, detailHtml: null, meta: `${rows.length} visible` };
    }
"""
