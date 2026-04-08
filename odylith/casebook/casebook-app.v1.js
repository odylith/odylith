const __ODYLITH_SHELL_REDIRECT_IN_PROGRESS__ = (function enforceShellOwnedSurfaceAccess() {
  try {
    const expectedFrameId = "frame-casebook";
    const frameElement = window.frameElement;
    const actualFrameId = frameElement && typeof frameElement.id === "string" ? frameElement.id : "";
    if (window.parent && window.parent !== window && actualFrameId === expectedFrameId) {
      return false;
    }
    const shellUrl = new URL("../index.html", window.location.href);
    const currentParams = new URLSearchParams(window.location.search || "");
    const nextParams = new URLSearchParams();
    nextParams.set("tab", "casebook");
    const passthroughRules = [{"target":"bug","sources":["bug"]},{"target":"severity","sources":["severity"]},{"target":"status","sources":["status"]}];
    for (const rule of passthroughRules) {
      if (!rule || !rule.target) continue;
      const sources = Array.isArray(rule.sources) && rule.sources.length ? rule.sources : [rule.target];
      let selected = "";
      for (const sourceKey of sources) {
        const token = String(currentParams.get(sourceKey) || "").trim();
        if (token) {
          selected = token;
          break;
        }
      }
      if (selected) {
        nextParams.set(rule.target, selected);
      }
    }
    shellUrl.search = nextParams.toString() ? `?${nextParams.toString()}` : "";
    shellUrl.hash = "";
    if (window.__ODYLITH_SHELL_REDIRECTING__ === true && window.__ODYLITH_SHELL_REDIRECT_TARGET__ === shellUrl.toString()) {
      return true;
    }
    const targetWindow = window.top && window.top !== window ? window.top : window;
    if (targetWindow.location && targetWindow.location.href === shellUrl.toString()) {
      return false;
    }
    window.__ODYLITH_SHELL_REDIRECTING__ = true;
    window.__ODYLITH_SHELL_REDIRECT_TARGET__ = shellUrl.toString();
    if (typeof window.stop === "function") {
      window.stop();
    }
    targetWindow.location.replace(shellUrl.toString());
    return true;
  } catch (_error) {
    // Fail open so renderer-local logic can still surface diagnostics if the shell route cannot be resolved.
    return false;
  }
})();

const DATA = window["__ODYLITH_CASEBOOK_DATA__"] || {};
    const bugSummaries = Array.isArray(DATA.bugs) ? DATA.bugs : [];
    const assetLoadCache = new Map();
    const searchInput = document.getElementById("searchInput");
    const severityFilter = document.getElementById("severityFilter");
    const statusFilter = document.getElementById("statusFilter");
    const bugList = document.getElementById("bugList");
    const detailPane = document.getElementById("detailPane");
    const listMeta = document.getElementById("listMeta");
    const kpiOpenCritical = document.getElementById("kpiOpenCritical");
    const kpiOpenTotal = document.getElementById("kpiOpenTotal");
    const kpiTotalCases = document.getElementById("kpiTotalCases");
    const kpiLatestCase = document.getElementById("kpiLatestCase");
    let detailRenderToken = 0;
    const BUG_ID_COMPACT_RE = /^(?:CB)?-?(\d{1,})$/i;
    const HUMAN_SIGNAL_FIELDS = [
      "Failure Signature",
      "Trigger Path",
      "Detected By",
      "Timeline",
    ];
    const HUMAN_IMPACT_FIELDS = [
      "Impact",
      "Blast Radius",
      "Ownership",
      "Invariant Violated",
      "SLO/SLA Impact",
    ];
    const HUMAN_RESPONSE_FIELDS = [
      "Root Cause",
      "Solution",
      "Workaround",
      "Rollback/Forward Fix",
      "Verification",
    ];

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
        script.onerror = () => reject(new Error(`Failed to load Casebook detail shard: ${resolvedHref}`));
        document.head.appendChild(script);
      });
      assetLoadCache.set(resolvedHref, promise);
      return promise;
    }

    function detailManifest() {
      const manifest = DATA.detail_manifest;
      return manifest && typeof manifest === "object" ? manifest : {};
    }

    async function loadDetailEntry(detailId) {
      const token = String(detailId || "").trim();
      if (!token) return null;
      const loaded = window.__ODYLITH_CASEBOOK_DETAIL_SHARDS__ || {};
      if (loaded[token] && typeof loaded[token] === "object") {
        return loaded[token];
      }
      const shardHref = String(detailManifest()[token] || "").trim();
      if (!shardHref) return null;
      await loadScriptAsset(shardHref);
      const resolved = window.__ODYLITH_CASEBOOK_DETAIL_SHARDS__ || {};
      return resolved[token] && typeof resolved[token] === "object" ? resolved[token] : null;
    }

    const casebookDataSource = {
      async loadDetail(id) {
        return loadDetailEntry(id);
      },
      prefetch(id) {
        void loadDetailEntry(id);
      },
    };

    function escapeHtml(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function inlineCodeHtml(value) {
      return escapeHtml(value).replace(/`([^`]+)`/g, "<code>$1</code>");
    }

    function canonicalizeBugToken(value) {
      const token = String(value || "").trim().replace(/^\.\//, "");
      if (!token) return "";
      if (token.includes("://")) return "";
      if (/^(?:[A-Za-z]:[\\/]|\/)/.test(token)) return "";
      return token;
    }

    function canonicalizeFilterToken(value) {
      return String(value || "").trim().toLowerCase();
    }

    function normalizeSearchToken(value) {
      return String(value || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "");
    }

    function canonicalizeBugIdToken(value) {
      const raw = canonicalizeBugToken(value || "");
      if (!raw) return "";
      const token = raw.toUpperCase();
      if (/^CB-\d{3,}$/.test(token)) return token;
      const compact = token.match(BUG_ID_COMPACT_RE);
      if (!compact) return "";
      return `CB-${compact[1].padStart(3, "0")}`;
    }

    function bugAliasTokens(row) {
      const aliases = Array.isArray(row && row.bug_aliases) ? row.bug_aliases : [];
      const fallback = [row && row.bug_route, row && row.bug_id, row && row.bug_key, row && row.source_path];
      return [...aliases, ...fallback]
        .map((item) => canonicalizeBugToken(item || ""))
        .filter(Boolean);
    }

    function bugSearchText(row) {
      return [
        row && row.bug_id,
        row && row.title,
        row && row.summary,
        row && row.components,
        row && row.bug_key,
        row && row.source_path,
        row && row.search_text,
        ...(Array.isArray(row && row.component_tokens) ? row.component_tokens : []),
      ].join(" ").toLowerCase();
    }

    function bugExactMatch(row, term) {
      const lowered = canonicalizeBugToken(term || "").toLowerCase();
      const aliases = bugAliasTokens(row);
      if (lowered && aliases.some((alias) => alias.toLowerCase() === lowered)) return true;
      const canonicalBugId = canonicalizeBugIdToken(term || "");
      if (!canonicalBugId) return false;
      return aliases.some((alias) => canonicalizeBugIdToken(alias) === canonicalBugId);
    }

    function resolveBugRoute(rows, token) {
      const normalized = canonicalizeBugToken(token || "");
      if (!normalized) return "";
      const lowered = normalized.toLowerCase();
      const match = rows.find((row) => bugAliasTokens(row).some((alias) => alias.toLowerCase() === lowered));
      return match ? String(match.bug_route || "").trim() : "";
    }

    function readState() {
      const params = new URLSearchParams(window.location.search || "");
      return {
        bug: canonicalizeBugToken(params.get("bug") || ""),
        severity: canonicalizeFilterToken(params.get("severity") || ""),
        status: canonicalizeFilterToken(params.get("status") || ""),
      };
    }

    function writeState(state) {
      const query = new URLSearchParams();
      if (state.bug) query.set("bug", state.bug);
      if (state.severity) query.set("severity", state.severity);
      if (state.status) query.set("status", state.status);
      const suffix = query.toString() ? `?${query.toString()}` : "";
      const next = `${window.location.pathname}${suffix}`;
      if (next !== `${window.location.pathname}${window.location.search}`) {
        window.history.replaceState(null, "", next);
      }
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({
          type: "odylith-casebook-navigate",
          state: {
            bug: state.bug || "",
            severity: state.severity || "",
            status: state.status || "",
          },
        }, "*");
      }
    }

    function fillSelect(selectEl, values, current, allLabel) {
      const rows = [`<option value="">${escapeHtml(allLabel)}</option>`];
      for (const token of values) {
        rows.push(
          `<option value="${escapeHtml(token)}"${token === current ? " selected" : ""}>${escapeHtml(token.toUpperCase())}</option>`
        );
      }
      selectEl.innerHTML = rows.join("");
    }

    function renderRichText(text) {
      const raw = String(text || "").trim();
      if (!raw) return "<p>Not captured in this bug entry.</p>";
      const blocks = raw.split(/\n\s*\n+/).map((item) => item.trim()).filter(Boolean);
      return blocks.map((block) => {
        const lines = block.split(/\n/).map((item) => item.replace(/\s+$/g, "")).filter((item) => item.trim());
        if (!lines.length) return "";
        if (lines.every((line) => /^\s*[-*]\s+/.test(line))) {
          const items = lines.map((line) => `<li>${inlineCodeHtml(line.replace(/^\s*[-*]\s+/, ""))}</li>`).join("");
          return `<ul>${items}</ul>`;
        }
        return `<p>${inlineCodeHtml(lines.join(" "))}</p>`;
      }).join("");
    }

    function renderDelimitedList(text) {
      const raw = String(text || "").trim();
      if (!raw || raw === "-") return "<p>Not captured in this bug entry.</p>";
      const tokens = raw.split(/\s\/\s/).map((item) => item.trim()).filter(Boolean);
      if (tokens.length <= 1) {
        return `<p>${inlineCodeHtml(raw)}</p>`;
      }
      return `<ul class="detail-list">${tokens.map((token) => `<li>${inlineCodeHtml(token)}</li>`).join("")}</ul>`;
    }

    function renderNarrativeFieldRows(fieldNames, fields, formatterMap = {}) {
      const rows = fieldNames
        .map((field) => {
          const value = String(fields[field] || "").trim();
          if (!value) return "";
          const formatter = typeof formatterMap[field] === "function" ? formatterMap[field] : renderRichText;
          return `
            <div class="narrative-row">
              <p class="signal-label narrative-label">${escapeHtml(field)}</p>
              <div class="detail-copy">${formatter(value)}</div>
            </div>
          `;
        })
        .filter(Boolean)
        .join("");
      return rows ? `<div class="narrative-list">${rows}</div>` : "";
    }

    function renderLabeledNarratives(items) {
      if (!Array.isArray(items) || !items.length) return "";
      const rows = items
        .map((item) => {
          const label = String(item && item.label || "").trim();
          const value = String(item && item.value || "").trim();
          if (!label || !value) return "";
          return `
            <div class="narrative-row">
              <p class="signal-label narrative-label">${escapeHtml(label)}</p>
              <div class="detail-copy">${renderRichText(value)}</div>
            </div>
          `;
        })
        .filter(Boolean)
        .join("");
      return rows ? `<div class="narrative-list">${rows}</div>` : "";
    }

    function actionChipHtml(label, href, tooltip = "") {
      const text = String(label || "").trim();
      const target = String(href || "").trim();
      if (!text || !target) return "";
      const note = String(tooltip || "").trim();
      const tooltipAttrs = note
        ? ` data-tooltip="${escapeHtml(note)}" aria-label="${escapeHtml(note)}"`
        : "";
      return `<a class="action-chip" href="${escapeHtml(target)}" target="_top" rel="noreferrer"${tooltipAttrs}>${escapeHtml(text)}</a>`;
    }

    function renderActionChips(items) {
      if (!Array.isArray(items) || !items.length) return "";
      const seen = new Set();
      const chips = [];
      for (const item of items) {
        const label = String(item && item.label || "").trim();
        const href = String(item && item.href || "").trim();
        if (!label || !href) continue;
        const key = `${label}::${href}`;
        if (seen.has(key)) continue;
        seen.add(key);
        chips.push(actionChipHtml(label, href, item && item.tooltip));
      }
      return chips.join("");
    }

    function renderActionChipGroup(items) {
      const chips = renderActionChips(items);
      return chips ? `<div class="link-group">${chips}</div>` : "";
    }

    function renderLinkRow(label, items) {
      const chips = renderActionChipGroup(items);
      if (!chips) return "";
      return `
        <div class="link-row">
          <p class="signal-label link-row-label">${escapeHtml(label)}</p>
          ${chips}
        </div>
      `;
    }

    function dedupeByField(items) {
      if (!Array.isArray(items)) return [];
      const seen = new Set();
      const rows = [];
      for (const item of items) {
        if (!item || typeof item !== "object") continue;
        const field = String(item.field || "").trim();
        if (!field) continue;
        const key = field.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        rows.push(item);
      }
      return rows;
    }

    function renderPathLinkList(items) {
      if (!Array.isArray(items) || !items.length) return "";
      const rows = items
        .map((item) => {
          const label = String(item.path || "").trim();
          if (!label) return "";
          const href = String(item.href || "").trim();
          const body = href
            ? `<a class="ref-link" href="${escapeHtml(href)}" target="_top" rel="noreferrer">${inlineCodeHtml(label)}</a>`
            : `<span>${inlineCodeHtml(label)}</span>`;
          return `<li>${body}</li>`;
        })
        .filter(Boolean)
        .join("");
      return rows ? `<ul class="detail-list reference-list">${rows}</ul>` : "";
    }

    function renderComponentNarratives(items) {
      if (!Array.isArray(items) || !items.length) return "";
      const options = arguments.length > 1 && arguments[1] && typeof arguments[1] === "object" ? arguments[1] : {};
      const maxItems = Number.isFinite(Number(options.maxItems)) && Number(options.maxItems) > 0
        ? Number(options.maxItems)
        : Number.MAX_SAFE_INTEGER;
      const includeWorkstreams = Boolean(options.includeWorkstreams);
      const visibleItems = items.slice(0, maxItems);
      const rows = visibleItems
        .map((item) => {
          const componentId = String(item && item.component_id || "").trim();
          if (!componentId) return "";
          const name = String(item && item.name || componentId).trim();
          const registryHref = String(item && item.registry_href || item && item.href || "").trim();
          const specHref = String(item && item.spec_href || "").trim();
          const specRef = String(item && item.spec_ref || "").trim();
          const registryChip = actionChipHtml("Registry", registryHref);
          const specChip = specHref ? actionChipHtml("Spec", specHref) : "";
          const radarChips = includeWorkstreams ? renderActionChips(
            Array.isArray(item && item.workstream_links)
              ? item.workstream_links.map((row) => ({
                  label: `Radar ${String(row && row.workstream || "").trim()}`,
                  href: String(row && row.href || "").trim(),
                }))
              : []
          ) : "";
          return `
            <div class="component-block">
              <div class="component-title-block">
                <p class="component-context-name">${escapeHtml(name)}</p>
                <p class="component-subtitle">${escapeHtml(componentId)}</p>
              </div>
              <div class="link-group">
                ${registryChip}
                ${specChip}
                ${radarChips}
              </div>
              ${specRef && !specHref ? `<p class="component-note"><span class="inline-note-label">Spec ref:</span> ${inlineCodeHtml(specRef)}</p>` : ""}
            </div>
          `;
        })
        .filter(Boolean)
        .join("");
      if (!rows) return "";
      const overflowCount = Math.max(0, items.length - visibleItems.length);
      const overflowNote = overflowCount
        ? `<p class="component-note">${overflowCount} more linked component${overflowCount === 1 ? "" : "s"} retained in Registry context.</p>`
        : "";
      return `<div class="component-listing">${rows}</div>${overflowNote}`;
    }

    function renderComponentLinkList(items) {
      if (!Array.isArray(items) || !items.length) return "";
      const rows = items
        .map((item) => {
          const componentId = String(item.component_id || "").trim();
          if (!componentId) return "";
          const name = String(item.name || componentId).trim();
          const href = String(item.href || "").trim();
          const body = href
            ? `<a class="ref-link" href="${escapeHtml(href)}" target="_top" rel="noreferrer">${escapeHtml(name)}</a>`
            : `<span>${escapeHtml(name)}</span>`;
          return `
            <li>
              ${body}
              <span class="ref-meta">${escapeHtml(componentId)}</span>
            </li>
          `;
        })
        .filter(Boolean)
        .join("");
      return rows ? `<ul class="detail-list reference-list">${rows}</ul>` : "";
    }

    function renderRelatedBugLinkList(items) {
      if (!Array.isArray(items) || !items.length) return "";
      const rows = items
        .map((item) => {
          const bugKey = String(item.bug_key || "").trim();
          if (!bugKey) return "";
          const title = String(item.title || bugKey).trim();
          const href = String(item.href || "").trim();
          const meta = [item.bug_id, item.date, item.severity, item.status]
            .map((value) => String(value || "").trim())
            .filter(Boolean)
            .join(" · ");
          const body = href
            ? `<a class="ref-link" href="${escapeHtml(href)}" target="_top" rel="noreferrer">${escapeHtml(title)}</a>`
            : `<span>${escapeHtml(title)}</span>`;
          return `
            <li>
              ${body}
              ${meta ? `<span class="ref-meta">${escapeHtml(meta)}</span>` : ""}
            </li>
          `;
        })
        .filter(Boolean)
        .join("");
      return rows ? `<ul class="detail-list reference-list">${rows}</ul>` : "";
    }

    function renderPlainList(items) {
      if (!Array.isArray(items) || !items.length) return "";
      return `<ul class="detail-list">${items.map((item) => `<li>${escapeHtml(String(item || "").trim())}</li>`).join("")}</ul>`;
    }

    function renderLimitedActionRow(label, items, maxItems, overflowLabel) {
      if (!Array.isArray(items) || !items.length) return "";
      const limit = Number.isFinite(Number(maxItems)) && Number(maxItems) > 0 ? Number(maxItems) : items.length;
      const visibleItems = items.slice(0, limit);
      const chips = renderActionChipGroup(visibleItems);
      if (!chips) return "";
      const overflowCount = Math.max(0, items.length - visibleItems.length);
      const overflowNote = overflowCount
        ? `<p class="component-note">${overflowCount} more ${escapeHtml(String(overflowLabel || "links"))} retained in source context.</p>`
        : "";
      return `
        <div class="narrative-row">
          <p class="signal-label narrative-label">${escapeHtml(label)}</p>
          <div class="detail-copy">${chips}${overflowNote}</div>
        </div>
      `;
    }

    function matchesSearch(row, term) {
      if (!term) return true;
      if (bugExactMatch(row, term)) return true;
      const searchText = bugSearchText(row);
      if (searchText.includes(term)) return true;
      const normalizedNeedle = normalizeSearchToken(term);
      if (!normalizedNeedle) return false;
      return normalizeSearchToken(searchText).includes(normalizedNeedle);
    }

    function matchesFilters(row, state) {
      if (state.severity && String(row.severity_token || "") !== state.severity) return false;
      if (state.status && String(row.status_token || "") !== state.status) return false;
      return true;
    }

    function visibleRows(state, searchTerm) {
      return bugSummaries.filter((row) => matchesFilters(row, state) && matchesSearch(row, searchTerm));
    }

    function renderKpis() {
      const counts = DATA.counts || {};
      kpiOpenCritical.textContent = String(Number(counts.open_critical || 0));
      kpiOpenTotal.textContent = String(Number(counts.open_total || 0));
      kpiTotalCases.textContent = String(Number(counts.total_cases || 0));
      kpiLatestCase.textContent = String(counts.latest_case_date || "-");
      kpiLatestCase.title = String(counts.latest_case_title || "").trim();
    }

    function detailCoreRows(row) {
      const fields = row.fields && typeof row.fields === "object" ? row.fields : {};
      return [
        ["Bug ID", row.bug_id || "-"],
        ["Date", row.date || "-"],
        ["Severity", row.severity || "-"],
        ["Status", row.status || "-"],
        ["Fixed", fields["Fixed"] || "-"],
      ].filter(([, value]) => String(value || "").trim() && String(value || "").trim() !== "-");
    }

    function detailSupportingRows(row) {
      const fields = row.fields && typeof row.fields === "object" ? row.fields : {};
      return [
        ["Type", fields["Type"] || "-"],
        ["Reproducibility", fields["Reproducibility"] || "-"],
      ].filter(([, value]) => String(value || "").trim() && String(value || "").trim() !== "-");
    }

    async function renderDetail(row) {
      if (!row) {
        detailRenderToken += 1;
        detailPane.innerHTML = ``;
        return;
      }
      const renderToken = ++detailRenderToken;
      detailPane.innerHTML = ``;
      const detailKey = String(row.bug_route || row.bug_key || "").trim();
      const loadedDetail = detailKey ? await casebookDataSource.loadDetail(detailKey) : null;
      if (renderToken !== detailRenderToken) {
        return;
      }
      const detail = loadedDetail && typeof loadedDetail === "object"
        ? { ...row, ...loadedDetail }
        : row;
      const fields = detail.fields && typeof detail.fields === "object" ? detail.fields : {};
      const coverage = detail.intelligence_coverage && typeof detail.intelligence_coverage === "object" ? detail.intelligence_coverage : {};
      const capturedCount = Number(coverage.captured_count || 0);
      const totalFields = Number(coverage.total_fields || 0);
      const missingFields = Array.isArray(coverage.missing_fields) ? coverage.missing_fields.map((item) => String(item || "").trim()).filter(Boolean) : [];
      const requiredMissingFields = Array.isArray(coverage.required_missing_fields)
        ? coverage.required_missing_fields.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const workstreamLinks = Array.isArray(detail.workstream_links)
        ? detail.workstream_links
            .map((item) => ({
              label: "Radar " + String(item && item.workstream || "").trim(),
              href: String(item && item.href || "").trim(),
            }))
            .filter((item) => item.label.trim() && item.href)
        : [];
      const atlasLinks = Array.isArray(detail.diagram_links)
        ? detail.diagram_links
            .map((item) => ({
              label: String(item && item.diagram_id || "").trim().toUpperCase(),
              href: String(item && item.href || "").trim(),
              tooltip: `${String(item && item.title || item && item.diagram_id || "").trim()}. Open Atlas context.`,
            }))
            .filter((item) => item.label.trim() && item.href)
        : [];
      const relatedBugLinks = Array.isArray(detail.related_bug_links)
        ? detail.related_bug_links
            .map((item) => ({
              label: String(item && item.bug_id || item && item.title || item && item.bug_key || "").trim(),
              href: String(item && item.href || "").trim(),
            }))
            .filter((item) => item.label.trim() && item.href)
        : [];
      const detailSectionRows = dedupeByField(Array.isArray(detail.detail_sections) ? detail.detail_sections : []);
      const detailSectionMap = new Map(
        detailSectionRows
          .map((section) => {
            const field = String(section && section.field || "").trim();
            const value = String(section && section.value || "").trim();
            return [field.toLowerCase(), value];
          })
          .filter(([field, value]) => field && value)
      );
      function detailFieldValue(fieldName) {
        const token = String(fieldName || "").trim();
        if (!token) return "";
        const sectionValue = String(detailSectionMap.get(token.toLowerCase()) || "").trim();
        if (sectionValue) return sectionValue;
        return String(fields[token] || "").trim();
      }
      function renderFocusedFieldRows(fieldNames, formatterMap = {}) {
        const rows = fieldNames
          .map((fieldName) => {
            const value = detailFieldValue(fieldName);
            if (!value) return "";
            const formatter = typeof formatterMap[fieldName] === "function" ? formatterMap[fieldName] : renderRichText;
            return `
              <div class="narrative-row">
                <p class="signal-label narrative-label">${escapeHtml(fieldName)}</p>
                <div class="detail-copy">${formatter(value)}</div>
              </div>
            `;
          })
          .filter(Boolean)
          .join("");
        return rows ? `<div class="narrative-list">${rows}</div>` : "";
      }
      function renderBriefCard(title, note, body) {
        const cardTitle = String(title || "").trim();
        const cardBody = String(body || "").trim();
        if (!cardTitle || !cardBody) return "";
        const cardNote = String(note || "").trim();
        return `
          <article class="brief-card">
            <div class="brief-card-head">
              <p class="brief-card-title">${escapeHtml(cardTitle)}</p>
              ${cardNote ? `<p class="brief-card-note">${escapeHtml(cardNote)}</p>` : ""}
            </div>
            ${cardBody}
          </article>
        `;
      }
      const chips = [];
      if (detail.severity) {
        chips.push(`<span class="meta-chip ${/^p[01]$/i.test(String(detail.severity || "")) ? "critical-chip" : ""}">${escapeHtml(detail.severity)}</span>`);
      }
      if (detail.status) {
        chips.push(`<span class="meta-chip ${String(detail.is_open) === "true" || detail.is_open ? "warn-chip" : ""}">${escapeHtml(detail.status)}</span>`);
      }
      if (detail.archive_bucket) {
        chips.push(`<span class="meta-chip archive-chip">Archive: ${escapeHtml(detail.archive_bucket)}</span>`);
      }
      if (totalFields) {
        chips.push(`<span class="meta-chip ${requiredMissingFields.length ? "warn-chip" : ""}">Intel ${capturedCount}/${totalFields}</span>`);
      }
      const sourceLink = detail.source_href
        ? actionChipHtml("Source markdown", detail.source_href)
        : `<span class="meta-chip muted">Source markdown missing</span>`;
      const summaryText = String(detail.summary || detailFieldValue("Description") || detailFieldValue("Impact") || "").trim();
      const summary = summaryText ? `<p class="detail-summary">${escapeHtml(summaryText)}</p>` : "";
      const summaryFacts = [...detailCoreRows(detail), ...detailSupportingRows(detail)]
        .map(([label, value]) => `
          <div class="summary-fact" data-summary-field="${escapeHtml(label)}" role="listitem">
            <p class="summary-fact-label">${escapeHtml(label)}</p>
            <p class="summary-fact-value">${escapeHtml(value)}</p>
          </div>
        `)
        .join("");
      const componentNarrative = detail.components && String(detail.components).trim() && String(detail.components).trim() !== "-"
        ? `
          <div class="narrative-row">
            <p class="signal-label narrative-label">Reported components</p>
            <div class="detail-copy">${renderDelimitedList(detail.components)}</div>
          </div>
        `
        : "";
      const humanSignalBody = renderFocusedFieldRows(HUMAN_SIGNAL_FIELDS);
      const humanImpactBody = [renderFocusedFieldRows(HUMAN_IMPACT_FIELDS), componentNarrative].filter(Boolean).join("");
      const humanResponseBody = renderFocusedFieldRows(HUMAN_RESPONSE_FIELDS);
      const humanCards = [
        renderBriefCard("Signal", "How the bug showed up.", humanSignalBody),
        renderBriefCard("Impact", "Why the bug mattered.", humanImpactBody),
        renderBriefCard("Response", "What changed or should happen now.", humanResponseBody),
      ].filter(Boolean).join("");
      const humanSection = humanCards
        ? `
          <article class="detail-section detail-section-human" aria-label="Bug brief">
            <div class="brief-stack">${humanCards}</div>
          </article>
        `
        : "";
      const intelligenceSection = totalFields && (requiredMissingFields.length || missingFields.length)
        ? `
          <details class="detail-disclosure agent-disclosure">
            <summary class="disclosure-title">Capture Gaps</summary>
            <div class="detail-disclosure-body detail-copy">
              <div class="coverage-strip">
                <span class="meta-chip">${capturedCount} of ${totalFields} recommended fields captured</span>
                ${requiredMissingFields.length ? `<span class="meta-chip warn-chip">Missing critical signals: ${requiredMissingFields.length}</span>` : ""}
              </div>
              <p class="coverage-note">Casebook still renders this bug, but the record is missing some of the surrounding context that makes nearby implementation work easier and safer.</p>
              ${requiredMissingFields.length ? `
                <div class="detail-copy">
                  <p class="signal-label">Missing critical signals</p>
                  ${renderPlainList(requiredMissingFields)}
                </div>
              ` : ""}
              ${missingFields.length ? `
                <div class="detail-copy">
                  <p class="signal-label">Missing intelligence fields</p>
                  ${renderPlainList(missingFields)}
                </div>
              ` : ""}
            </div>
          </details>
        `
        : "";
      const agentGuidance = detail.agent_guidance && typeof detail.agent_guidance === "object" ? detail.agent_guidance : {};
      const agentChecks = Array.isArray(agentGuidance.preflight_checks)
        ? agentGuidance.preflight_checks.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const agentProofLinks = renderPathLinkList(Array.isArray(agentGuidance.proof_links) ? agentGuidance.proof_links : []);
      const guidanceSignals = renderFocusedFieldRows(agentChecks.length ? ["Agent Guardrails"] : ["Agent Guardrails", "Preflight Checks"]);
      const codeRefs = renderPathLinkList(detail.code_ref_links);
      const docRefs = renderPathLinkList(detail.doc_ref_links);
      const testRefs = renderPathLinkList(detail.test_ref_links);
      const contractRefs = renderPathLinkList(detail.contract_ref_links);
      const relatedBugPreview = Array.isArray(detail.related_bug_links) ? detail.related_bug_links.slice(0, 4) : [];
      const relatedBugList = renderRelatedBugLinkList(relatedBugPreview);
      const relatedBugOverflowCount = Array.isArray(detail.related_bug_links)
        ? Math.max(0, detail.related_bug_links.length - relatedBugPreview.length)
        : 0;
      const evidenceRows = [
        codeRefs ? `<div class="narrative-row"><p class="signal-label narrative-label">Code references</p><div class="detail-copy">${codeRefs}</div></div>` : "",
        docRefs ? `<div class="narrative-row"><p class="signal-label narrative-label">Runbooks and docs</p><div class="detail-copy">${docRefs}</div></div>` : "",
        testRefs ? `<div class="narrative-row"><p class="signal-label narrative-label">Regression tests</p><div class="detail-copy">${testRefs}</div></div>` : "",
        contractRefs ? `<div class="narrative-row"><p class="signal-label narrative-label">Contracts and schemas</p><div class="detail-copy">${contractRefs}</div></div>` : "",
        relatedBugList
          ? `<div class="narrative-row"><p class="signal-label narrative-label">Related bug records</p><div class="detail-copy">${relatedBugList}${relatedBugOverflowCount ? `<p class="component-note">${relatedBugOverflowCount} more related bug record${relatedBugOverflowCount === 1 ? "" : "s"} retained in source context.</p>` : ""}</div></div>`
          : "",
      ].filter(Boolean).join("");
      const relatedContextRows = [
        detail.component_links && Array.isArray(detail.component_links) && detail.component_links.length
          ? `<div class="narrative-row"><p class="signal-label narrative-label">Linked components</p><div class="detail-copy">${renderComponentNarratives(detail.component_links, { maxItems: 3, includeWorkstreams: false })}</div></div>`
          : "",
        renderLimitedActionRow("Atlas diagrams", atlasLinks, 4, "Atlas diagram links"),
      ].filter(Boolean).join("");
      const consumedFieldKeys = new Set(
        [...HUMAN_SIGNAL_FIELDS, ...HUMAN_IMPACT_FIELDS, ...HUMAN_RESPONSE_FIELDS, "Description", "Agent Guardrails", "Preflight Checks"]
          .map((fieldName) => String(fieldName || "").trim().toLowerCase())
          .filter(Boolean)
      );
      const remainingDetailRows = detailSectionRows
        .filter((section) => !consumedFieldKeys.has(String(section && section.field || "").trim().toLowerCase()))
        .map((section) => `
          <div class="narrative-row">
            <p class="signal-label narrative-label">${escapeHtml(section.field || "")}</p>
            <div class="detail-copy">${renderRichText(section.value || "")}</div>
          </div>
        `)
        .join("");
      const remainingDetailSections = remainingDetailRows
        ? `
          <details class="detail-disclosure agent-disclosure">
            <summary class="disclosure-title">Additional Captured Detail</summary>
            <div class="detail-disclosure-body narrative-list">${remainingDetailRows}</div>
          </details>
        `
        : "";
      const agentBlocks = [
        guidanceSignals
          ? `<div class="agent-band-block"><p class="agent-band-title">Guardrails</p>${guidanceSignals}</div>`
          : "",
        agentChecks.length
          ? `
            <div class="agent-band-block">
              <p class="agent-band-title">Before coding nearby</p>
              <div class="detail-copy agent-checks">
                ${renderPlainList(agentChecks)}
              </div>
            </div>
          `
          : "",
        agentProofLinks
          ? `
            <div class="agent-band-block">
              <p class="agent-band-title">Direct proof links</p>
              <div class="detail-copy">${agentProofLinks}</div>
            </div>
          `
          : "",
        evidenceRows
          ? `
            <div class="agent-band-block">
              <p class="agent-band-title">Evidence and references</p>
              <div class="narrative-list">${evidenceRows}</div>
            </div>
          `
          : "",
        relatedContextRows
          ? `
            <div class="agent-band-block">
              <p class="agent-band-title">Related context</p>
              <div class="narrative-list">${relatedContextRows}</div>
            </div>
          `
          : "",
      ].filter(Boolean).join("");
      const agentSection = agentBlocks || remainingDetailSections || intelligenceSection
        ? `
          <article class="detail-section detail-section-agent">
            <h2 class="section-heading">Odylith Agent Learnings</h2>
            <p class="section-lede">Deeper guardrails, evidence, and nearby context for future Odylith-assisted changes.</p>
            ${agentBlocks ? `<div class="agent-band">${agentBlocks}</div>` : ""}
            ${remainingDetailSections}
            ${intelligenceSection}
          </article>
        `
        : "";
      const sectionBlocks = [
        humanSection,
        agentSection,
      ].filter(Boolean).join("");
      detailPane.innerHTML = `
        <section class="detail-head">
          <div class="detail-headline">
            ${detail.bug_id ? `<p class="detail-kicker">${escapeHtml(detail.bug_id)}</p>` : ""}
            <h1 class="detail-title">${escapeHtml(detail.title || detail.bug_key || "Bug detail")}</h1>
          </div>
          ${summaryFacts ? `<div class="summary-facts" role="list">${summaryFacts}</div>` : ""}
          ${summary}
          <div class="detail-meta">${chips.join("")}</div>
          <div class="detail-links">
            ${sourceLink}
            ${workstreamLinks.length ? renderActionChipGroup(workstreamLinks) : ""}
          </div>
        </section>
        <section class="section-stack">
          ${sectionBlocks}
        </section>
      `;
    }

    function renderList(state, rows) {
      if (!rows.length) {
        bugList.innerHTML = ``;
        listMeta.textContent = "Visible: 0";
        renderDetail(null);
        return;
      }
      const selectedRoute = resolveBugRoute(rows, state.bug) || String(rows[0].bug_route || "");
      const selected = rows.find((row) => row.bug_route === selectedRoute) || rows[0];
      bugList.innerHTML = rows.map((row) => {
        const coverage = row.intelligence_coverage && typeof row.intelligence_coverage === "object" ? row.intelligence_coverage : {};
        const capturedCount = Number(coverage.captured_count || 0);
        const totalFields = Number(coverage.total_fields || 0);
        const requiredMissingFields = Array.isArray(coverage.required_missing_fields)
          ? coverage.required_missing_fields.map((item) => String(item || "").trim()).filter(Boolean)
          : [];
        const active = row.bug_route === selectedRoute;
        const chips = [
          row.severity ? `<span class="list-chip ${/^p[01]$/i.test(String(row.severity || "")) ? "critical-chip" : ""}">${escapeHtml(row.severity)}</span>` : "",
          row.status ? `<span class="list-chip">${escapeHtml(row.status)}</span>` : "",
          row.archive_bucket ? `<span class="list-chip archive-chip">${escapeHtml(row.archive_bucket)}</span>` : "",
          totalFields ? `<span class="list-chip ${requiredMissingFields.length ? "warn-chip" : ""}">Intel ${capturedCount}/${totalFields}</span>` : "",
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
      listMeta.textContent = `Visible: ${rows.length}`;
      for (const button of bugList.querySelectorAll(".bug-row")) {
        button.addEventListener("click", () => {
          const bug = canonicalizeBugToken(button.getAttribute("data-bug") || "");
          const next = { ...readState(), bug };
          writeState(next);
          render();
        });
        const bug = canonicalizeBugToken(button.getAttribute("data-bug") || "");
        if (bug) {
          button.addEventListener("mouseenter", () => {
            casebookDataSource.prefetch(bug);
          });
          button.addEventListener("focus", () => {
            casebookDataSource.prefetch(bug);
          });
        }
      }
      if (selectedRoute !== state.bug) {
        writeState({ ...state, bug: selectedRoute });
      }
      rows.slice(0, Math.min(6, rows.length)).forEach((row) => {
        const bug = String(row.bug_route || row.bug_key || "").trim();
        if (bug) {
          casebookDataSource.prefetch(bug);
        }
      });
      void renderDetail(selected);
    }

    function render() {
      const state = readState();
      const searchTerm = String(searchInput.value || "").trim().toLowerCase();
      const rows = visibleRows(state, searchTerm);
      renderList(state, rows);
    }

    fillSelect(
      severityFilter,
      Array.isArray(DATA.filters && DATA.filters.severity_tokens) ? DATA.filters.severity_tokens : [],
      readState().severity,
      "All severities"
    );
    fillSelect(
      statusFilter,
      Array.isArray(DATA.filters && DATA.filters.status_tokens) ? DATA.filters.status_tokens : [],
      readState().status,
      "All statuses"
    );
    renderKpis();
    searchInput.addEventListener("input", () => render());
    severityFilter.addEventListener("change", () => {
      writeState({ ...readState(), severity: canonicalizeFilterToken(severityFilter.value || ""), bug: readState().bug });
      render();
    });
    statusFilter.addEventListener("change", () => {
      writeState({ ...readState(), status: canonicalizeFilterToken(statusFilter.value || ""), bug: readState().bug });
      render();
    });
    window.addEventListener("popstate", () => {
      fillSelect(
        severityFilter,
        Array.isArray(DATA.filters && DATA.filters.severity_tokens) ? DATA.filters.severity_tokens : [],
        readState().severity,
        "All severities"
      );
      fillSelect(
        statusFilter,
        Array.isArray(DATA.filters && DATA.filters.status_tokens) ? DATA.filters.status_tokens : [],
        readState().status,
        "All statuses"
      );
      render();
    });
    render();
    function initCasebookQuickTooltips() {
  const QUICK_TOOLTIP_BIND_KEY = "odylithCasebookTooltipBound";
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

initCasebookQuickTooltips();
