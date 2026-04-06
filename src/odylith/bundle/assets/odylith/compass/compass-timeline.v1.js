    function timelineSummaryNaturalJoin(values) {
      const rows = Array.from(new Set(
        (Array.isArray(values) ? values : [])
          .map((item) => String(item || "").trim())
          .filter(Boolean)
      ));
      if (!rows.length) return "";
      if (rows.length === 1) return rows[0];
      if (rows.length === 2) return `${rows[0]} and ${rows[1]}`;
      return `${rows.slice(0, -1).join(", ")}, and ${rows[rows.length - 1]}`;
    }

    function timelineSummaryTokenRefList(values, maxItems = 3) {
      const rows = Array.from(new Set(
        (Array.isArray(values) ? values : [])
          .map((item) => String(item || "").trim())
          .filter(Boolean)
      ));
      if (!rows.length) return "";
      if (rows.length <= Math.max(1, Number(maxItems || 0))) {
        return timelineSummaryNaturalJoin(rows);
      }
      const shown = rows.slice(0, Math.max(1, Number(maxItems || 0)));
      return `${shown.join(", ")}, and ${rows.length - shown.length} more`;
    }

    function timelineSummaryTransactionFiles(transaction) {
      return (Array.isArray(transaction && transaction.files) ? transaction.files : [])
        .map((file) => normalizeRepoPath(file))
        .filter(Boolean);
    }

    function consumerTruthRoots() {
      const shell = compassShell();
      return shell.consumer_truth_roots && typeof shell.consumer_truth_roots === "object"
        ? shell.consumer_truth_roots
        : {};
    }

    function truthRootToken(value) {
      return normalizeRepoPath(String(value || "").trim());
    }

    function timelineSummaryFileAreaLabel(file) {
      const token = normalizeRepoPath(file);
      const componentSpecsRoot = truthRootToken(consumerTruthRoots().component_specs);
      const runbooksRoot = truthRootToken(consumerTruthRoots().runbooks);
      if (!token) return "";
      if (runbooksRoot && runbooksRoot !== "odylith" && token.startsWith(`${runbooksRoot}/`)) return runbooksRoot;
      if (componentSpecsRoot && componentSpecsRoot !== "odylith" && token.startsWith(`${componentSpecsRoot}/`)) return componentSpecsRoot;
      if (token.startsWith("odylith/registry/source/components/") && token.endsWith("/CURRENT_SPEC.md")) return "registry component specs";
      if (token.startsWith("docs/")) return "docs";
      if (token.startsWith("tests/")) return "tests";
      if (token.startsWith("odylith/radar/source/")) return "odylith/radar/source";
      if (token.startsWith("odylith/radar/")) return "odylith/radar";
      if (token.startsWith("odylith/compass/")) return "odylith/compass";
      if (token.startsWith("agents-guidelines/")) return "agents-guidelines";
      const slash = token.indexOf("/");
      return slash === -1 ? token : token.slice(0, slash);
    }

    function timelineSummaryFileAreaSummary(files, maxItems = 4) {
      const rows = Array.isArray(files) ? files : [];
      const counts = new Map();
      rows.forEach((file) => {
        const label = timelineSummaryFileAreaLabel(file);
        if (!label) return;
        counts.set(label, Number(counts.get(label) || 0) + 1);
      });
      if (!counts.size) return "";
      const entries = Array.from(counts.entries())
        .sort((left, right) => {
          if (right[1] !== left[1]) return right[1] - left[1];
          return String(left[0] || "").localeCompare(String(right[0] || ""));
        });
      const shown = entries.slice(0, Math.max(1, Number(maxItems || 0)));
      const text = shown.map(([label, count]) => `${label} (${count})`).join(", ");
      const hidden = Math.max(0, entries.length - shown.length);
      return hidden > 0 ? `${text} (+${hidden} more)` : text;
    }

    function timelineSummaryPlanCompletionIds(transaction) {
      const ids = new Set();
      const eventRows = Array.isArray(transaction && transaction.events) ? transaction.events : [];
      eventRows.forEach((row) => {
        if (String(row && row.kind ? row.kind : "").trim() !== "plan_completion") return;
        const workstreams = Array.isArray(row && row.workstreams) ? row.workstreams : [];
        workstreams.forEach((workstreamId) => {
          const token = String(workstreamId || "").trim();
          if (WORKSTREAM_RE.test(token)) ids.add(token);
        });
        const summary = String(row && row.summary ? row.summary : "").trim();
        const matches = summary.match(/B-\d{3,}/g) || [];
        matches.forEach((token) => ids.add(String(token || "").trim()));
      });
      return Array.from(ids);
    }

    function timelineSummaryPriorityWorkstreamIds(transaction) {
      const eventRows = Array.isArray(transaction && transaction.events) ? transaction.events : [];
      const priorities = ["implementation", "decision", "statement", "plan_update", "plan_completion"];
      for (const kind of priorities) {
        const match = eventRows.find((row) => String(row && row.kind ? row.kind : "").trim() === kind) || null;
        if (!match) continue;
        const ids = new Set();
        const workstreams = Array.isArray(match && match.workstreams) ? match.workstreams : [];
        workstreams.forEach((workstreamId) => {
          const token = String(workstreamId || "").trim();
          if (WORKSTREAM_RE.test(token)) ids.add(token);
        });
        const sourceText = String(match && (match.summary || match.context) ? (match.summary || match.context) : "").trim();
        const matches = sourceText.match(/B-\d{3,}/g) || [];
        matches.forEach((token) => ids.add(String(token || "").trim()));
        if (ids.size) return Array.from(ids);
      }
      return [];
    }

    function timelineSummaryPrimaryWorkstreamContext(transaction, workstreamLookup = {}) {
      const normalizedLookup = workstreamLookup && typeof workstreamLookup === "object" ? workstreamLookup : {};
      const directIds = timelineSummaryPlanCompletionIds(transaction);
      const priorityIds = timelineSummaryPriorityWorkstreamIds(transaction);
      const fallbackIds = Array.from(new Set(
        (Array.isArray(transaction && transaction.workstreams) ? transaction.workstreams : [])
          .map((item) => String(item || "").trim())
          .filter((item) => WORKSTREAM_RE.test(item))
      ));
      const eventRows = Array.isArray(transaction && transaction.events) ? transaction.events : [];
      const broadLocalOnlyBatch = (
        !directIds.length
        && !priorityIds.length
        && fallbackIds.length > 12
        && eventRows.length > 0
        && eventRows.every((row) => String(row && row.kind ? row.kind : "").trim() === "local_change")
      );
      const candidateIds = (broadLocalOnlyBatch || timelineSummaryCompassMixedAuditBatch(transaction))
        ? []
        : (directIds.length ? directIds : (priorityIds.length ? priorityIds : fallbackIds));
      for (const ideaId of candidateIds) {
        const source = normalizedLookup[ideaId];
        const row = source && typeof source === "object" ? source : {};
        const title = typeof source === "string" ? String(source || "").trim() : String(row.title || "").trim();
        const status = String(row.status || "").trim();
        const implementedSummary = String(row.implemented_summary || "").trim();
        const problem = String(row.problem || "").trim();
        const proposedSolution = String(row.proposed_solution || "").trim();
        const opportunity = String(row.opportunity || "").trim();
        const whyNow = String(row.why_now || "").trim();
        const founderPov = String(row.founder_pov || "").trim();
        const nextTasks = Array.isArray(row.next_tasks) ? row.next_tasks : [];
        if (ideaId || title || implementedSummary || problem || proposedSolution) {
          return { ideaId, title, status, implementedSummary, problem, proposedSolution, opportunity, whyNow, founderPov, nextTasks };
        }
      }
      return {
        ideaId: "",
        title: "",
        status: "",
        implementedSummary: "",
        problem: "",
        proposedSolution: "",
        opportunity: "",
        whyNow: "",
        founderPov: "",
        nextTasks: [],
      };
    }

    function timelineSummaryDerivedTitleContext(transaction, workstreamLookup = {}) {
      const primary = timelineSummaryPrimaryWorkstreamContext(transaction, workstreamLookup);
      let title = String(primary.title || "").trim();
      if (!title) {
        const eventRows = Array.isArray(transaction && transaction.events) ? transaction.events : [];
        const planEvent = eventRows.find((row) => String(row && row.kind ? row.kind : "").trim() === "plan_completion") || null;
        const sourceText = String(planEvent && (planEvent.summary || planEvent.context) ? (planEvent.summary || planEvent.context) : "").trim();
        if (sourceText) {
          title = sourceText
            .replace(/^Plan milestone completed:\s*/i, "")
            .replace(/\s+closed\s+for\s+B-\d{3,}\.?$/i, "")
            .replace(/\.$/, "")
            .trim();
        }
      }
      return {
        ideaId: String(primary.ideaId || "").trim(),
        title,
        status: String(primary.status || "").trim(),
        implementedSummary: String(primary.implementedSummary || "").trim(),
        problem: String(primary.problem || "").trim(),
        proposedSolution: String(primary.proposedSolution || "").trim(),
        opportunity: String(primary.opportunity || "").trim(),
        whyNow: String(primary.whyNow || "").trim(),
        founderPov: String(primary.founderPov || "").trim(),
        nextTasks: Array.isArray(primary.nextTasks) ? primary.nextTasks : [],
      };
    }

    function timelineSummaryDisplayTitle(title) {
      const text = String(title || "").trim();
      if (!text) return "";
      return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
    }

    function timelineSummaryNarrativeKey(text) {
      const token = String(text || "").trim();
      if (!token) return "";
      return token
        .toLowerCase()
        .replace(/[`*_]/g, "")
        .replace(/(captured|recorded|implemented|updated|closed)\s+(b-\d{3,}(?:,\s*b-\d{3,})*(?:,\s*and\s*\d+\s+more)?)\s+(checkpoint|plan state):\s*/g, "")
        .replace(/(current-state checkpoint|target end state|target outcome|why this matters|why now|next tracked step|gap being tracked|problem being solved|scope note)\s*:\s*/g, "")
        .replace(/[^\w\s]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    }

    function timelineSummaryDedupNarrativeItems(items, maxItems = 3) {
      const seen = new Set();
      const rows = [];
      (Array.isArray(items) ? items : []).forEach((item) => {
        const text = String(item || "").trim();
        if (!text) return;
        const key = timelineSummaryNarrativeKey(text);
        if (!key || seen.has(key)) return;
        seen.add(key);
        rows.push(text);
      });
      return rows.slice(0, Math.max(1, Number(maxItems || 0)));
    }

    function timelineSummaryPrimaryWorkstreamTopic(primary, maxWords = 4) {
      const row = primary && typeof primary === "object" ? primary : {};
      const ideaId = String(row.ideaId || "").trim();
      const title = timelineSummaryDisplayTitle(row.title || "");
      if (!title) return ideaId;
      const words = title.split(/\s+/).filter(Boolean);
      const shown = words.slice(0, Math.max(1, Number(maxWords || 0))).join(" ");
      return ideaId ? `${ideaId} ${shown}` : shown;
    }

    function timelineSummaryPrimaryWorkstreamLabel(primary, maxChars = 88) {
      const row = primary && typeof primary === "object" ? primary : {};
      const ideaId = String(row.ideaId || "").trim();
      const title = timelineSummaryDisplayTitle(row.title || "");
      const label = ideaId && title ? `${ideaId} ${title}` : (ideaId || title);
      return clipFocusText(label, maxChars);
    }

    function timelineSummaryCleanPriorityEventText(eventRow) {
      const row = eventRow && typeof eventRow === "object" ? eventRow : {};
      const kind = String(row.kind || "").trim();
      const sourceText = String(row.summary || row.context || "").trim();
      if (!sourceText) return "";
      if (kind === "implementation") {
        return sourceText
          .replace(/^Implementation checkpoint in [^:]+:\s*/i, "")
          .replace(/\.\.+$/g, ".")
          .trim();
      }
      if (kind === "plan_update") {
        return sourceText.replace(/^Plan updated:\s*/i, "").trim();
      }
      if (kind === "plan_completion") {
        return sourceText
          .replace(/^Plan milestone completed:\s*/i, "")
          .replace(/\s+closed\s+for\s+B-\d{3,}\.?$/i, "")
          .trim();
      }
      return sourceText;
    }

    function timelineSummaryEvidenceCaptureOnly(transaction) {
      const files = timelineSummaryTransactionFiles(transaction);
      if (!files.length) return false;
      const hasPlan = files.some((file) => file.startsWith("odylith/technical-plans/"));
      if (!hasPlan) return false;
      return files.every((file) => {
        if (file.startsWith("odylith/technical-plans/")) return true;
        if (file.startsWith("odylith/radar/source/")) return false;
        return isGeneratedNarrativeFile(file)
          || file.startsWith("odylith/runtime/");
      });
    }

    function timelineSummaryCompassMixedAuditBatch(transaction) {
      if (!timelineSummaryTouchesCompass(transaction)) return false;
      const files = timelineSummaryTransactionFiles(transaction);
      const touchesCompassSource = files.includes("src/odylith/runtime/surfaces/compass_dashboard_shell.py")
        || files.includes("odylith/registry/source/components/compass/CURRENT_SPEC.md")
        || files.some((file) => file.startsWith("tests/") && file.toLowerCase().includes("compass"));
      if (!touchesCompassSource) return false;
      const eventRows = Array.isArray(transaction && transaction.events) ? transaction.events : [];
      const hasImportedExecutionSignal = eventRows.some((row) => {
        const kind = String(row && row.kind ? row.kind : "").trim();
        if (!["implementation", "plan_update", "plan_completion"].includes(kind)) return false;
        const workstreams = Array.isArray(row && row.workstreams) ? row.workstreams : [];
        return workstreams.some((item) => WORKSTREAM_RE.test(String(item || "").trim()));
      });
      const workstreamCount = new Set(
        (Array.isArray(transaction && transaction.workstreams) ? transaction.workstreams : [])
          .map((item) => String(item || "").trim())
          .filter((item) => WORKSTREAM_RE.test(item))
      ).size;
      return hasImportedExecutionSignal && (files.length > 12 || workstreamCount > 4);
    }

    function timelineSummarySupportingSurfaceNarrative(transaction) {
      const files = timelineSummaryTransactionFiles(transaction);
      const surfaces = [];
      if (files.some((file) => file.startsWith("odylith/technical-plans/"))) surfaces.push("the active plan");
      if (files.some((file) => file.startsWith("docs/"))) surfaces.push("the matching docs");
      if (files.some((file) => file.startsWith("tests/"))) surfaces.push("the matching tests");
      if (files.some((file) => file.startsWith("odylith/radar/"))) surfaces.push("generated backlog surfaces");
      if (files.some((file) => file.startsWith("odylith/registry/"))) surfaces.push("generated Registry surfaces");
      if (files.some((file) => file.startsWith("odylith/casebook/"))) surfaces.push("generated Casebook surfaces");
      if (files.some((file) => file.startsWith("odylith/runtime/"))) surfaces.push("delivery-intelligence outputs");
      if (files.some((file) => file.startsWith("odylith/compass/"))) surfaces.push("generated Compass surfaces");
      if (files.some((file) => file === "odylith/index.html" || file === "odylith/tooling-payload.v1.js")) {
        surfaces.push("tooling shell surfaces");
      }
      if (!surfaces.length) return "";
      if (timelineSummaryEvidenceCaptureOnly(transaction)) {
        return `Refreshed ${timelineSummaryNaturalJoin(surfaces)} so the checkpoint is visible across the linked planning and governance surfaces.`;
      }
      return `Updated ${timelineSummaryNaturalJoin(surfaces)} so the surrounding surfaces stay aligned with the direct change.`;
    }

    function timelineSummaryWhyNowNarrative(transaction, workstreamLookup = {}) {
      const primary = timelineSummaryDerivedTitleContext(transaction, workstreamLookup);
      const title = String(primary.title || "").trim();
      const whyText = String(primary.whyNow || primary.opportunity || primary.founderPov || "").trim();
      if (whyText) {
        return `Why now: ${toSentence(clipFocusText(whyText, 220))}`;
      }
      const key = timelineSummaryTitlePatternKey(title);
      if (key === "compass_work_type_intent_clarity") {
        return "Why now: the current Timeline Audit card still makes readers reconstruct the change from lifecycle bookkeeping and surrounding churn.";
      }
      if (key === "compass_closeout_summary_quality") {
        return "Why now: a finished workstream should close with a clear shipped-change summary, not raw milestone phrasing.";
      }
      if (key === "compass_inline_timeline_audit") {
        return "Why now: the explanation should live beside the transaction evidence instead of forcing the reader to jump to a detached summary.";
      }
      const loweredTitle = title.toLowerCase();
      if (timelineSummaryTouchesCompass(transaction) && /(latest audit|audit narrative|audit summary|timeline audit)/.test(loweredTitle)) {
        return "Why now: the audit surface should explain the change on first read instead of making the operator infer it from the ledger.";
      }
      return "";
    }

    function timelineSummaryNextStepNarrative(transaction, workstreamLookup = {}) {
      const primary = timelineSummaryDerivedTitleContext(transaction, workstreamLookup);
      const nextTasks = Array.isArray(primary.nextTasks) ? primary.nextTasks : [];
      if (!nextTasks.length) return "";
      return `Next tracked step: ${toSentence(clipFocusText(nextTasks[0], 220))}`;
    }

    function timelineSummaryTransactionRoleNarrative(transaction) {
      if (timelineSummaryEvidenceCaptureOnly(transaction)) {
        return "Scope note: this transaction captures the checkpoint and propagates evidence; it is not the runtime cutover itself.";
      }
      if (timelineSummaryTouchesCompass(transaction)) {
        return "Scope note: this transaction changes the Compass audit experience itself, not just surrounding bookkeeping.";
      }
      return "";
    }

    function timelineSummaryActionSubject(title) {
      const text = timelineSummaryDisplayTitle(title);
      if (!text) return "";
      const stripped = text
        .replace(/(productization|hardening|clarity|quality|alignment|summary|narrative|repair|closeout|cleanup|tightening)$/i, "")
        .replace(/fix(?:es)?$/i, "")
        .replace(/\s+(and|for|of|with)$/i, "")
        .replace(/[\s,:;-]+$/g, "")
        .trim();
      return stripped || text;
    }

    function timelineSummaryTitlePatternKey(title) {
      const value = String(title || "").trim().toLowerCase();
      if (!value) return "";
      if (/scroll lock/.test(value) && /selector/.test(value)) return "dashboard_scroll_lock";
      if (/closeout summary quality/.test(value)) return "compass_closeout_summary_quality";
      if (/work type and intent clarity/.test(value)) return "compass_work_type_intent_clarity";
      if (/inline timeline audit narrative/.test(value)) return "compass_inline_timeline_audit";
      if (/transaction local summary/.test(value)) return "compass_transaction_local_summary";
      if (/summary card and timeline narrative/.test(value)) return "compass_summary_card";
      if (/narrative header and sections/.test(value)) return "compass_header_sections";
      return "";
    }

    function timelineSummaryGenericTitleAction(title, action) {
      const raw = String(title || "").trim();
      const normalized = String(action || "").trim();
      if (!raw || !normalized) return "";
      const subject = timelineSummaryActionSubject(raw);
      if (!subject) return "";
      return `${normalized} ${subject}.`;
    }

    function timelineSummaryTitleDrivenImplementationNarrative(title) {
      const raw = String(title || "").trim();
      if (!raw) return "";
      const lower = raw.toLowerCase();
      if (/productization/.test(lower)) return timelineSummaryGenericTitleAction(raw, "Productized");
      if (/hardening/.test(lower)) return timelineSummaryGenericTitleAction(raw, "Hardened");
      if (/(repair|fix|fixes)/.test(lower)) return timelineSummaryGenericTitleAction(raw, "Fixed");
      if (/(clarity|quality|alignment)/.test(lower)) return timelineSummaryGenericTitleAction(raw, "Clarified");
      if (/(summary|narrative|header|sections)/.test(lower)) return timelineSummaryGenericTitleAction(raw, "Reworked");
      if (/bootstrap/.test(lower)) return timelineSummaryGenericTitleAction(raw, "Bootstrapped");
      if (/migration/.test(lower)) return timelineSummaryGenericTitleAction(raw, "Migrated");
      return "";
    }

    function timelineSummaryCloseoutHeaderNarrative(transaction, workstreamLookup = {}) {
      const primary = timelineSummaryDerivedTitleContext(transaction, workstreamLookup);
      const closedIds = timelineSummaryPlanCompletionIds(transaction);
      const runtimeImplementedSummary = String(primary.implementedSummary || "").trim();
      if (runtimeImplementedSummary && closedIds.includes(String(primary.ideaId || "").trim())) {
        return toSentence(clipFocusText(runtimeImplementedSummary, 220));
      }
      const title = String(primary.title || "").trim();
      const key = timelineSummaryTitlePatternKey(title);
      if (key === "dashboard_scroll_lock") {
        return "Fixed dashboard selector scrolling after virtualization made the list snap back.";
      }
      if (key === "compass_closeout_summary_quality") {
        return "Tightened Compass closeout summaries so finished audits describe the actual change.";
      }
      if (key === "compass_work_type_intent_clarity") {
        return "Reordered Compass audit narrative so the implementation story lands before lifecycle noise.";
      }
      if (key === "compass_inline_timeline_audit") {
        return "Moved Compass audit narrative into each timeline transaction.";
      }
      if (key === "compass_transaction_local_summary") {
        return "Bound Compass audit summaries to the actual top timeline transaction.";
      }
      if (key === "compass_summary_card") {
        return "Added a Compass latest-audit summary above the timeline.";
      }
      if (key === "compass_header_sections") {
        return "Reshaped Compass audit summaries into clearer narrative sections.";
      }
      const eventRows = Array.isArray(transaction && transaction.events) ? transaction.events : [];
      const hasPlanCompletion = eventRows.some((row) => String(row && row.kind ? row.kind : "").trim() === "plan_completion");
      if (!hasPlanCompletion || !title) return "";
      const lower = title.toLowerCase();
      if (/\bhardening\b/.test(lower)) return timelineSummaryGenericTitleAction(title, "Hardened");
      if (/\bclarity\b/.test(lower)) return timelineSummaryGenericTitleAction(title, "Clarified");
      if (/\bquality\b/.test(lower)) return timelineSummaryGenericTitleAction(title, "Improved");
      if (/\b(summary|narrative|header|sections)\b/.test(lower)) return timelineSummaryGenericTitleAction(title, "Reworked");
      return toSentence(timelineSummaryDisplayTitle(title));
    }

    function timelineSummaryImplementationHeaderNarrative(transaction, workstreamLookup = {}) {
      const priorityKind = String((timelineSummaryPriorityEvent(transaction) || {}).kind || "").trim();
      if (!priorityKind || priorityKind === "plan_completion") return "";
      const primary = timelineSummaryDerivedTitleContext(transaction, workstreamLookup);
      const runtimeImplementedSummary = String(primary.implementedSummary || "").trim();
      if (runtimeImplementedSummary) {
        return toSentence(clipFocusText(runtimeImplementedSummary, 180));
      }
      if (priorityKind === "implementation") {
        const topic = timelineSummaryPrimaryWorkstreamTopic(primary, 4);
        const problem = String(primary.problem || "").trim()
          .replace(/^Service\s+/i, "")
          .replace(/flows\s+/i, "")
          .replace(/\s*,\s*creating.*$/i, "")
          .trim();
        if (topic && timelineSummaryEvidenceCaptureOnly(transaction) && problem) {
          return `${topic} checkpoint: ${toSentence(clipFocusText(problem, 118))}`;
        }
        const cleaned = timelineSummaryCleanPriorityEventText(timelineSummaryPriorityEvent(transaction))
          .replace(/^completed\s+/i, "")
          .trim();
        if (topic && cleaned) {
          return `${topic}: ${toSentence(clipFocusText(cleaned, 150))}`;
        }
      }
      return timelineSummaryTitleDrivenImplementationNarrative(primary.title);
    }

    function timelineSummaryTouchesCompass(transaction) {
      const files = timelineSummaryTransactionFiles(transaction);
      return files.includes("src/odylith/runtime/surfaces/compass_dashboard_shell.py")
        || files.includes("src/odylith/runtime/surfaces/compass_dashboard_frontend_contract.py")
        || files.includes("src/odylith/runtime/surfaces/compass_dashboard_runtime.py")
        || files.includes("src/odylith/runtime/surfaces/render_compass_dashboard.py")
        || files.some((file) => file.startsWith("src/odylith/runtime/surfaces/templates/compass_dashboard/"))
        || files.includes("odylith/compass/compass-app.v1.js")
        || files.includes("odylith/compass/compass-shared.v1.js")
        || files.includes("odylith/compass/compass-state.v1.js")
        || files.includes("odylith/compass/compass-summary.v1.js")
        || files.includes("odylith/compass/compass-timeline.v1.js")
        || files.includes("odylith/compass/compass-waves.v1.js")
        || files.includes("odylith/compass/compass-workstreams.v1.js")
        || files.includes("odylith/compass/compass-ui-runtime.v1.js")
        || files.includes("odylith/compass/compass-style-base.v1.css")
        || files.includes("odylith/compass/compass-style-execution-waves.v1.css")
        || files.includes("odylith/compass/compass-style-surface.v1.css")
        || files.includes("odylith/compass/compass.html")
        || files.includes("odylith/registry/source/components/compass/CURRENT_SPEC.md")
        || files.some((file) => file.startsWith("tests/") && file.toLowerCase().includes("compass"));
    }

    function timelineSummaryWorkTypeNarrative(transaction, workstreamLookup = {}) {
      const primary = timelineSummaryDerivedTitleContext(transaction, workstreamLookup);
      if (String(primary.implementedSummary || "").trim() && timelineSummaryPlanCompletionIds(transaction).includes(String(primary.ideaId || "").trim())) {
        return "";
      }
      if (timelineSummaryCompassMixedAuditBatch(transaction)) {
        return "Compass timeline-audit surface refinement with imported execution-checkpoint carry-through across the linked governance surfaces.";
      }
      const priorityKind = String((timelineSummaryPriorityEvent(transaction) || {}).kind || "").trim();
      const workstreamLabel = timelineSummaryPrimaryWorkstreamLabel(primary, 92);
      if (workstreamLabel && (String(primary.proposedSolution || "").trim() || String(primary.problem || "").trim())) {
        if (priorityKind === "implementation" && timelineSummaryEvidenceCaptureOnly(transaction)) {
          return `Current-state checkpoint for ${workstreamLabel}.`;
        }
        if (priorityKind === "implementation") {
          return `Active implementation slice for ${workstreamLabel}.`;
        }
        if (priorityKind === "plan_update") {
          return `Execution-state refresh for ${workstreamLabel}.`;
        }
        if (priorityKind === "plan_completion") {
          return `Closeout of ${workstreamLabel}.`;
        }
        return `Change slice for ${workstreamLabel}.`;
      }
      const title = String(primary.title || "").trim().toLowerCase();
      const key = timelineSummaryTitlePatternKey(title);
      if (key === "dashboard_scroll_lock") {
        return "Selector scrolling usability fix after virtualization made the active row snap back.";
      }
      if (key === "compass_closeout_summary_quality") {
        return "Compass timeline-audit refinement for finished-workstream closeouts.";
      }
      if (key === "compass_work_type_intent_clarity") {
        return "Compass timeline-audit narrative refinement so the card leads with the change itself.";
      }
      if (key === "compass_inline_timeline_audit") {
        return "Compass audit-card refinement so each transaction explains itself in place.";
      }
      if (timelineSummaryTouchesCompass(transaction)) {
        if (/(inline timeline audit narrative|latest audit|audit narrative|audit summary|timeline audit)/.test(title)) {
          return "Compass timeline-audit UX refinement rather than service/runtime feature delivery.";
        }
        return "";
      }
      if (timelineSummaryInfraNarrative(transaction)) {
        return "Shared infra/config change.";
      }
      if (timelineSummaryGovernanceNarrative(transaction)) {
        return timelineSummaryPlanCompletionIds(transaction).length
          ? "Finished-workstream closeout plus matching odylith/technical-plans/Radar/Odylith surface sync."
          : "Planning and rendered-surface sync around the active slice.";
      }
      return "";
    }

    function timelineSummaryIntentNarrative(transaction, workstreamLookup = {}) {
      const primary = timelineSummaryDerivedTitleContext(transaction, workstreamLookup);
      const title = String(primary.title || "").trim();
      if (timelineSummaryCompassMixedAuditBatch(transaction)) {
        return "Target outcome: make each expanded Compass audit lead with the real code or UX change, while keeping lifecycle proof and regenerated-surface sync in supporting positions.";
      }
      const proposedSolution = String(primary.proposedSolution || "").trim();
      if (proposedSolution) {
        return `Target outcome: ${toSentence(clipFocusText(proposedSolution, 230))}`;
      }
      const problem = String(primary.problem || "").trim();
      if (timelineSummaryEvidenceCaptureOnly(transaction) && problem) {
        return `Problem being solved: ${toSentence(clipFocusText(problem, 220))}`;
      }
      const loweredTitle = title.toLowerCase();
      const key = timelineSummaryTitlePatternKey(title);
      if (key === "dashboard_scroll_lock") {
        return "Target outcome: let operators scroll the dashboard naturally without the active row snapping back into view.";
      }
      if (key === "compass_closeout_summary_quality") {
        return "Target outcome: make finished audits close with the shipped change and proof, not milestone bookkeeping.";
      }
      if (key === "compass_work_type_intent_clarity") {
        return "Target outcome: make the expanded Timeline Audit card explain intent, the change summary, and implementation evidence in a stable order.";
      }
      if (key === "compass_inline_timeline_audit") {
        return "Target outcome: make each expanded timeline transaction self-explanatory where the evidence already lives.";
      }
      if (key === "compass_transaction_local_summary") {
        return "Target outcome: tie the newest Compass summary to the actual top timeline transaction, not a broader digest.";
      }
      if (key === "compass_summary_card") {
        return "Target outcome: give the newest timeline transaction a clear at-a-glance summary surface.";
      }
      if (key === "compass_header_sections") {
        return "Target outcome: break the expanded audit into a small set of sections that read clearly from intent through proof.";
      }
      if (timelineSummaryTouchesCompass(transaction)) {
        if (/inline timeline audit narrative/.test(loweredTitle)) {
          return "Target outcome: move the explanation into each audit card so the operator understands the change without leaving the transaction.";
        }
        if (/(latest audit|audit narrative|audit summary|timeline audit)/.test(loweredTitle)) {
          return "Target outcome: make the transaction read like a direct explanation of the work instead of a detached ledger.";
        }
        return "";
      }
      if (timelineSummaryInfraNarrative(transaction)) {
        return "Target outcome: land the infra/config change with enough surrounding proof to make rollout and ownership obvious.";
      }
      return "";
    }

    function timelineSummarySummaryOfChangeNarrative(transaction, workstreamLookup = {}) {
      const primary = timelineSummaryDerivedTitleContext(transaction, workstreamLookup);
      const title = String(primary.title || "").trim();
      const key = timelineSummaryTitlePatternKey(title);
      if (key === "dashboard_scroll_lock") {
        return "Adjusted selector recentering rules so manual scroll position survives rerenders unless navigation intentionally changes the active row.";
      }
      if (key === "compass_closeout_summary_quality") {
        return "Reframed finished-workstream audit copy so the card opens with the shipped change instead of closeout boilerplate.";
      }
      if (key === "compass_work_type_intent_clarity") {
        return "Reordered and relabeled the expanded audit card so it opens with Intent, then Summary of Change, then Implemented.";
      }
      if (key === "compass_inline_timeline_audit") {
        return "Moved the explanatory summary into each expanded timeline card instead of keeping it in a detached latest-audit panel.";
      }
      if (key === "compass_transaction_local_summary") {
        return "Bound the newest Compass summary to the actual top timeline transaction instead of the broader standup brief.";
      }
      if (key === "compass_summary_card") {
        return "Added a dedicated latest-audit summary surface above the timeline so the freshest transaction can be understood at a glance.";
      }
      if (key === "compass_header_sections") {
        return "Split the expanded audit into clearer sections so the transaction reads like an explanation instead of a raw ledger.";
      }
      const closeoutHeader = timelineSummaryCloseoutHeaderNarrative(transaction, workstreamLookup);
      if (closeoutHeader) return closeoutHeader;
      const implementationHeader = timelineSummaryImplementationHeaderNarrative(transaction, workstreamLookup);
      if (implementationHeader) return implementationHeader;
      const workType = timelineSummaryWorkTypeNarrative(transaction, workstreamLookup);
      if (workType) return workType;
      const compass = timelineSummaryCompassNarrative(transaction, workstreamLookup);
      if (compass) return compass;
      const infra = timelineSummaryInfraNarrative(transaction);
      if (infra) return toSentence(clipFocusText(infra, 220));
      const generic = timelineSummaryGenericNarrative(transaction);
      if (generic) return generic;
      return "";
    }

    function timelineSummaryImplementedNarrative(transaction, workstreamLookup = {}) {
      const primary = timelineSummaryDerivedTitleContext(transaction, workstreamLookup);
      const title = String(primary.title || "").trim();
      const key = timelineSummaryTitlePatternKey(title);
      if (key === "dashboard_scroll_lock") {
        return "Guarded selector recentering so scroll-driven rerenders preserve manual position, while selection, filter, and route changes still reveal the active row when needed.";
      }
      if (key === "compass_closeout_summary_quality") {
        return "Rewrote closeout headers and bullets so finished timeline audits summarize the implemented change instead of echoing raw `closed for B-###` copy.";
      }
      if (key === "compass_work_type_intent_clarity") {
        return "Reordered and relabeled the expanded audit card so it now reads Intent, Summary of Change, Implemented, and then Files.";
      }
      if (key === "compass_inline_timeline_audit") {
        return "Removed the standalone latest-audit summary card and moved the narrative into each expanded timeline audit.";
      }
      if (key === "compass_transaction_local_summary") {
        return "Changed Compass to summarize the first filtered timeline transaction directly instead of replaying the broader standup brief.";
      }
      if (key === "compass_summary_card") {
        return "Added a latest-audit summary card above Timeline Audit so the newest transaction had a dedicated narrative surface.";
      }
      if (key === "compass_header_sections") {
        return "Split the audit summary into clearer narrative sections so the transaction reads like a short recap instead of a raw ledger.";
      }
      const runtimeImplementedSummary = String(primary.implementedSummary || "").trim();
      if (runtimeImplementedSummary) return toSentence(clipFocusText(runtimeImplementedSummary, 260));
      const priorityEvent = timelineSummaryPriorityEvent(transaction);
      const priorityKind = String((priorityEvent || {}).kind || "").trim();
      if (priorityKind === "implementation") {
        const cleaned = timelineSummaryCleanPriorityEventText(priorityEvent);
        if (cleaned && timelineSummaryEvidenceCaptureOnly(transaction)) {
          return `Recorded the current-state checkpoint: ${toSentence(clipFocusText(cleaned, 240))}`;
        }
      }
      const titleDrivenNarrative = timelineSummaryTitleDrivenImplementationNarrative(title);
      if (titleDrivenNarrative) return titleDrivenNarrative;
      const compass = timelineSummaryCompassNarrative(transaction, workstreamLookup);
      if (compass) return compass;
      const infra = timelineSummaryInfraNarrative(transaction);
      if (infra) return infra;
      const docNarrative = timelineSummaryDocumentationNarrative(transaction);
      if (docNarrative) return docNarrative;
      const priorityNarrative = timelineSummaryPriorityEventNarrative(transaction);
      if (priorityNarrative) return priorityNarrative;
      return "";
    }

    function timelineSummaryPriorityEvent(transaction) {
      const eventRows = Array.isArray(transaction && transaction.events) ? transaction.events : [];
      const priorities = ["implementation", "decision", "plan_update", "plan_completion", "bug_resolved", "bug_update"];
      for (const kind of priorities) {
        const match = eventRows.find((row) => {
          if (String(row && row.kind ? row.kind : "").trim() !== kind) return false;
          return Boolean(String(row && (row.summary || row.context) ? (row.summary || row.context) : "").trim());
        }) || null;
        if (match) return match;
      }
      return null;
    }

    function timelineSummaryPriorityEventNarrative(transaction) {
      const eventRow = timelineSummaryPriorityEvent(transaction);
      if (!eventRow) return "";
      const kind = String(eventRow.kind || "").trim();
      const refs = timelineSummaryTokenRefList(
        (Array.isArray(eventRow.workstreams) ? eventRow.workstreams : []).filter((item) => WORKSTREAM_RE.test(String(item || "").trim())),
        2,
      );
      const sourceText = timelineSummaryCleanPriorityEventText(eventRow);
      if (!sourceText) return "";
      if (kind === "implementation") {
        return `${refs ? `Captured ${refs} checkpoint: ` : ""}${toSentence(clipFocusText(sourceText, 220))}`;
      }
      if (kind === "plan_update") {
        return `${refs ? `Updated ${refs} plan state: ` : ""}${toSentence(clipFocusText(sourceText, 220))}`;
      }
      if (kind === "plan_completion") {
        return `${refs ? `Closed ${refs}: ` : ""}${toSentence(clipFocusText(sourceText, 220))}`;
      }
      return `${refs ? `${refs}: ` : ""}${toSentence(clipFocusText(sourceText, 220))}`;
    }

    function timelineSummaryDocumentationNarrative(transaction) {
      const files = timelineSummaryTransactionFiles(transaction);
      const componentSpecsRoot = truthRootToken(consumerTruthRoots().component_specs);
      const runbooksRoot = truthRootToken(consumerTruthRoots().runbooks);
      const docFiles = files.filter((file) =>
        file.startsWith("docs/")
        || (file.startsWith("odylith/registry/source/components/") && file.endsWith("/CURRENT_SPEC.md"))
      );
      if (docFiles.length < 3) return "";
      const themes = [];
      if (
        docFiles.some((file) =>
          (runbooksRoot && file.startsWith(`${runbooksRoot}/`))
          || file.startsWith("docs/runbooks/")
        )
      ) themes.push("runbooks");
      if (
        docFiles.some((file) =>
          (componentSpecsRoot && file.startsWith(`${componentSpecsRoot}/`))
        )
        || docFiles.some((file) => file.startsWith("odylith/registry/source/components/") && file.endsWith("/CURRENT_SPEC.md"))
      ) themes.push("component specs");
      if (docFiles.some((file) => file.includes("guide") || file.includes("bootstrap"))) themes.push("maintainer and developer guides");
      if (docFiles.some((file) => file.includes("architecture"))) themes.push("architecture guidance");
      if (!themes.length) {
        return `Rolled the same audit through ${timelineSummaryFileAreaSummary(docFiles, 3)} so the docs stay aligned.`;
      }
      return `Rolled the same checkpoint through ${timelineSummaryNaturalJoin(themes)} so the operator docs and architecture guidance stay aligned.`;
    }

    function timelineSummaryCompassNarrative(transaction, workstreamLookup = {}) {
      const files = timelineSummaryTransactionFiles(transaction);
      const primary = timelineSummaryPrimaryWorkstreamContext(transaction, workstreamLookup);
      const title = String(primary.title || "").trim().toLowerCase();
      const hasSummarySource = files.includes("src/odylith/runtime/surfaces/compass_dashboard_shell.py");
      const hasTemplateSource = files.some((file) => file.startsWith("src/odylith/runtime/surfaces/templates/compass_dashboard/"));
      const hasSummarySpec = files.includes("odylith/registry/source/components/compass/CURRENT_SPEC.md");
      const hasSummaryTest = files.some((file) => file.startsWith("tests/") && file.toLowerCase().includes("compass"));
      const hasCompassGenerated = files.some((file) => file.startsWith("odylith/compass/")) || files.includes("odylith/index.html");
      if (!(hasSummarySource || hasTemplateSource || hasSummarySpec || hasSummaryTest || hasCompassGenerated)) return "";
      const refreshed = [];
      if (hasSummarySpec) refreshed.push("spec");
      if (hasSummaryTest) refreshed.push("test");
      if (hasCompassGenerated) refreshed.push("generated Compass surfaces");
      const refreshText = refreshed.length ? ` and refreshed the matching ${timelineSummaryNaturalJoin(refreshed)}` : "";
      if (/inline timeline audit narrative/.test(title)) {
        return `Removed the standalone latest-audit summary card and made each transaction card carry its own narrative header and bullet summary${refreshText}.`;
      }
      if (/(latest audit|audit narrative|audit summary|timeline audit)/.test(title)) {
        return `Reworked how Compass explains timeline audits so the story comes from the transaction itself${refreshText}.`;
      }
      return "";
    }

    function timelineSummaryInfraMoves(transaction) {
      const files = timelineSummaryTransactionFiles(transaction);
      const moves = [];
      const hasEnvManifest = files.some((file) => file.startsWith("configs/") && file.includes("env_manifest"));
      const hasSharedIngressStack = files.some((file) => file.startsWith("infra/stacks/") && file.includes("shared_ingress"));
      const hasSharedIngressMake = files.some((file) => (file.startsWith("mk/") || file.startsWith("tests/")) && file.toLowerCase().includes("sharedingress"));
      const hasPulumiToolbox = files.some((file) => file.endsWith("pulumi_toolbox.py"));
      if (hasEnvManifest) moves.push("env-manifest wiring");
      if (hasSharedIngressStack) moves.push("shared ingress stack support");
      if (hasSharedIngressMake) moves.push("shared ingress make-target wiring");
      if (hasPulumiToolbox) moves.push("the service-deploy Pulumi toolbox path");
      return moves;
    }

    function timelineSummaryInfraNarrative(transaction) {
      const files = timelineSummaryTransactionFiles(transaction);
      const moves = timelineSummaryInfraMoves(transaction);
      if (!moves.length) {
        const infraAreas = timelineSummaryFileAreaSummary(
          files.filter((file) => {
            if (file.startsWith("infra/") || file.startsWith("configs/") || file.startsWith("mk/")) {
              return true;
            }
            if (!file.startsWith("tests/")) return false;
            const lower = file.toLowerCase();
            return lower.includes("infra")
              || lower.includes("env_manifest")
              || lower.includes("env-manifest")
              || lower.includes("sharedingress");
          }),
          3,
        );
        if (!infraAreas) return "";
        return `Bundled shared infra work across ${infraAreas}.`;
      }
      return `Bundled shared infra work across ${timelineSummaryNaturalJoin(moves)}.`;
    }

    function timelineSummaryGovernanceNarrative(transaction) {
      const files = timelineSummaryTransactionFiles(transaction);
      const closedIds = timelineSummaryPlanCompletionIds(transaction);
      const hasGovernanceSync = files.some((file) =>
        file.startsWith("odylith/technical-plans/")
        || file.startsWith("odylith/radar/")
        || file === "odylith/index.html"
        || file === "odylith/tooling-payload.v1.js"
      );
      if (closedIds.length) {
        const tokenList = timelineSummaryTokenRefList(closedIds, 3);
        if (hasGovernanceSync) {
          return `Closed the loop on ${tokenList} by syncing odylith/technical-plans, Radar, and Odylith shell state with the shipped change.`;
        }
        return `Closed ${tokenList} in the same audit block.`;
      }
      if (timelineSummaryEvidenceCaptureOnly(transaction)) {
        return "";
      }
      if (hasGovernanceSync) {
        return "Closed the loop between plan state and rendered dashboards so the visible lifecycle state matches the source change.";
      }
      return "";
    }

    function timelineSummaryBreadthNarrative(transaction) {
      const workstreamCount = new Set(
        (Array.isArray(transaction && transaction.workstreams) ? transaction.workstreams : [])
          .map((item) => String(item || "").trim())
          .filter((item) => WORKSTREAM_RE.test(item))
      ).size;
      if (workstreamCount < 12) return "";
      const files = timelineSummaryTransactionFiles(transaction);
      const hasCompassShared = files.includes("src/odylith/runtime/surfaces/compass_dashboard_shell.py")
        || files.includes("odylith/registry/source/components/compass/CURRENT_SPEC.md")
        || files.some((file) => file.startsWith("tests/") && file.toLowerCase().includes("compass"));
      const closedIds = timelineSummaryPlanCompletionIds(transaction);
      if (hasCompassShared && closedIds.length) {
        return `The ${workstreamCount}-workstream fan-out mostly comes from shared Compass/Radar/Odylith surfaces and generated bundles, not ${workstreamCount} separate feature changes; the direct slice here is ${timelineSummaryTokenRefList(closedIds, 2)}.`;
      }
      if (hasCompassShared) {
        return `The ${workstreamCount}-workstream fan-out mostly comes from shared Compass docs, tests, and dashboard surfaces rather than ${workstreamCount} separate direct changes.`;
      }
      return "";
    }

    function timelineSummaryGenericNarrative(transaction) {
      const files = timelineSummaryTransactionFiles(transaction);
      const split = splitNarrativeFiles(files);
      const sample = summarizeFileList(split.source.length ? split.source : files, 3);
      if (sample) {
        return `Latest audit concentrated on ${sample}.`;
      }
      const areaSummary = timelineSummaryFileAreaSummary(files, 3);
      if (areaSummary) {
        return `Latest audit centered on ${areaSummary}.`;
      }
      return "";
    }

    function timelineSummaryNarrativeHeader(transaction, workstreamLookup = {}) {
      const closeoutHeader = timelineSummaryCloseoutHeaderNarrative(transaction, workstreamLookup);
      if (closeoutHeader) return closeoutHeader;
      if (timelineSummaryCompassMixedAuditBatch(transaction)) {
        const compassNarrative = timelineSummaryCompassNarrative(transaction, workstreamLookup);
        if (compassNarrative) return compassNarrative;
      }
      const implementationHeader = timelineSummaryImplementationHeaderNarrative(transaction, workstreamLookup);
      if (implementationHeader) return implementationHeader;
      const priorityNarrative = timelineSummaryPriorityEventNarrative(transaction);
      const workType = timelineSummaryWorkTypeNarrative(transaction, workstreamLookup);
      const intent = timelineSummaryIntentNarrative(transaction, workstreamLookup);
      const primary = timelineSummaryPrimaryWorkstreamContext(transaction, workstreamLookup);
      const titleKey = timelineSummaryTitlePatternKey(primary.title || "");
      if (workType && intent && titleKey && timelineSummaryTouchesCompass(transaction)) {
        return `Compass audit refinement: leading each expanded transaction with intent, summary of change, and implementation detail${primary.ideaId ? ` for ${primary.ideaId}` : ""}.`;
      }
      if (priorityNarrative) return priorityNarrative;
      const compassNarrative = timelineSummaryCompassNarrative(transaction, workstreamLookup);
      const compass = Boolean(compassNarrative);
      const infraNarrative = timelineSummaryInfraNarrative(transaction);
      const infra = Boolean(infraNarrative);
      const governance = Boolean(timelineSummaryGovernanceNarrative(transaction));
      const closedIds = timelineSummaryPlanCompletionIds(transaction);
      const infraLabel = timelineSummaryNaturalJoin(timelineSummaryInfraMoves(transaction));
      if (compass && infra) {
        return `Retooled Compass's latest-audit narrative while folding in ${infraLabel || "shared infra work"}.`;
      }
      if (compass && closedIds.length) {
        return `Retooled Compass's latest-audit narrative and closed ${timelineSummaryTokenRefList(closedIds, 2)} in the same audit.`;
      }
      if (compass) {
        return compassNarrative;
      }
      if (infra && governance) {
        return "Advanced shared infra wiring and synced the matching governance surfaces in the same audit.";
      }
      if (infra) {
        return toSentence(clipFocusText(infraNarrative, 220));
      }
      if (governance) {
        return `Closed ${timelineSummaryTokenRefList(closedIds, 2) || "the active slice"} and synced the governance surfaces in the latest audit.`;
      }
      return "";
    }

    function timelineSummaryNarrativeSections(transaction, workstreamLookup = {}) {
      const priorityNarrative = timelineSummaryPriorityEventNarrative(transaction);
      const priorityKind = String((timelineSummaryPriorityEvent(transaction) || {}).kind || "").trim();
      const intent = timelineSummaryIntentNarrative(transaction, workstreamLookup);
      const whyNow = timelineSummaryWhyNowNarrative(transaction, workstreamLookup);
      const summaryOfChange = timelineSummarySummaryOfChangeNarrative(transaction, workstreamLookup);
      const implemented = timelineSummaryImplementedNarrative(transaction, workstreamLookup);
      const supportingSurface = timelineSummarySupportingSurfaceNarrative(transaction);
      const docNarrative = timelineSummaryDocumentationNarrative(transaction);
      const governance = timelineSummaryGovernanceNarrative(transaction);
      const roleNarrative = timelineSummaryTransactionRoleNarrative(transaction);
      const breadth = timelineSummaryBreadthNarrative(transaction);
      const summaryKey = timelineSummaryNarrativeKey(summaryOfChange);
      const summaryItems = [];
      if (summaryOfChange) summaryItems.push(summaryOfChange);
      if (roleNarrative && (timelineSummaryEvidenceCaptureOnly(transaction) || !summaryOfChange)) {
        summaryItems.push(roleNarrative);
      }
      const implementedInputs = [];
      if (implemented && timelineSummaryNarrativeKey(implemented) !== summaryKey) {
        implementedInputs.push(implemented);
      }
      if (supportingSurface) implementedInputs.push(supportingSurface);
      if (docNarrative) implementedInputs.push(docNarrative);
      if (governance) implementedInputs.push(governance);
      if (priorityNarrative && priorityKind && priorityKind !== "plan_completion" && priorityKind !== "plan_update") {
        implementedInputs.push(priorityNarrative);
      }
      if (!implementedInputs.length && priorityNarrative) {
        implementedInputs.push(priorityNarrative);
      }
      if (breadth) {
        implementedInputs.push(breadth);
      }
      if (!implementedInputs.length) {
        const generic = timelineSummaryGenericNarrative(transaction);
        if (generic && timelineSummaryNarrativeKey(generic) !== summaryKey) {
          implementedInputs.push(generic);
        }
      }
      const sections = [];
      const intentItems = timelineSummaryDedupNarrativeItems([intent, whyNow], 3);
      if (intentItems.length) {
        sections.push({ title: "Intent", items: intentItems });
      }
      const summarySectionItems = timelineSummaryDedupNarrativeItems(summaryItems, 3);
      if (summarySectionItems.length) {
        sections.push({ title: "Summary of Change", items: summarySectionItems });
      }
      const implementedItems = timelineSummaryDedupNarrativeItems(implementedInputs, 4);
      if (implementedItems.length) {
        sections.push({ title: "Implemented", items: implementedItems });
      }
      return sections;
    }

    function renderTimelineNarrativeItem(text, linkContext) {
      const normalizedText = String(text || "").trim();
      if (!normalizedText) return "";
      return `
        <li class="tx-narrative-item">
          <span>${linkifyNarrativeText(normalizedText, linkContext)}</span>
        </li>
      `;
    }

    function renderTimelineNarrativeSection(title, items, linkContext) {
      const normalizedTitle = String(title || "").trim();
      const rows = (Array.isArray(items) ? items : [])
        .map((item) => renderTimelineNarrativeItem(item, linkContext))
        .filter(Boolean);
      if (!normalizedTitle || !rows.length) return "";
      return `
        <section class="tx-narrative-section">
          <div class="tx-narrative-section-title">${escapeHtml(normalizedTitle)}</div>
          <ul class="tx-narrative-list">${rows.join("")}</ul>
        </section>
      `;
    }

    function renderTimelineTransactionNarrative(transaction, linkContext, workstreamLookup = {}) {
      const sections = timelineSummaryNarrativeSections(transaction, workstreamLookup);
      const sectionsHtml = sections
        .map((section) => renderTimelineNarrativeSection(section.title, section.items, linkContext))
        .filter(Boolean)
        .join("");
      if (sectionsHtml) {
        return `
          <div class="tx-narrative">
            <h3>Audit Narrative</h3>
            ${sectionsHtml}
          </div>
        `;
      }
      const fallbackHeading = String(timelineSummaryNarrativeHeader(transaction, workstreamLookup) || "").trim();
      if (!fallbackHeading) return "";
      return `
        <div class="tx-narrative">
          <h3>Audit Narrative</h3>
          <ul class="tx-narrative-list">${renderTimelineNarrativeItem(fallbackHeading, linkContext)}</ul>
        </div>
      `;
    }
