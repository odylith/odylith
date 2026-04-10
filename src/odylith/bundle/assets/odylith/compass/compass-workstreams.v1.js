    function joinWithAnd(items) {
      const rows = Array.isArray(items) ? items.map((item) => String(item || "").trim()).filter(Boolean) : [];
      if (!rows.length) return "";
      if (rows.length === 1) return rows[0];
      if (rows.length === 2) return `${rows[0]} and ${rows[1]}`;
      return `${rows.slice(0, -1).join(", ")}, and ${rows[rows.length - 1]}`;
    }

    function normalizeIdList(values) {
      if (!Array.isArray(values)) return [];
      const intentionalEmptyTokens = new Set(["none", "n/a", "na", "null", "nil", "-"]);
      return values
        .map((value) => String(value || "").trim())
        .filter((token) => token && !intentionalEmptyTokens.has(token.toLowerCase()));
    }

    function normalizeDiagramIdList(values) {
      return normalizeIdList(values)
        .map((value) => String(value || "").trim().toUpperCase())
        .filter((token) => /^D-\d{3,}$/.test(token));
    }

    function compassWorkstreamReleaseLabel(release) {
      const row = release && typeof release === "object" ? release : {};
      const nameLabel = String(row.name || row.version || row.tag || row.display_label || row.effective_name || "").trim();
      if (nameLabel) return nameLabel;
      return String(row.release_id || "").trim();
    }

    function numericProgressOrNull(value) {
      if (value === null || value === undefined || value === "") return null;
      const ratio = Number(value);
      return Number.isFinite(ratio) ? ratio : null;
    }

    function focusAreaSummary(files) {
      const rows = Array.isArray(files) ? files.map((file) => String(file || "").trim()).filter(Boolean) : [];
      const buckets = [
        ["src/odylith/runtime/", "runtime modules"],
        ["tests/", "targeted tests"],
        ["odylith/compass/", "Compass UI shell"],
        ["odylith/radar/source/", "Radar source"],
        ["odylith/radar/", "Radar dashboard"],
        ["agents-guidelines/", "workflow docs"],
        ["skills/", "skill guidance"],
        ["docs/", "developer docs"],
        ["odylith/technical-plans/", "plan tracking"],
        ["odylith/atlas/source/", "Mermaid source"],
        ["odylith/atlas/", "Mermaid catalog"],
        ["odylith/atlas/source/", "Atlas source assets"],
      ];
      const labels = [];
      for (const [prefix, label] of buckets) {
        if (rows.some((file) => file.startsWith(prefix))) {
          labels.push(label);
        }
      }
      if (!labels.length && rows.length) {
        labels.push("implementation files");
      }
      return labels.slice(0, 3);
    }

    function summarizeFileList(files, maxItems = 4) {
      const rows = Array.isArray(files) ? files.map((file) => String(file || "").trim()).filter(Boolean) : [];
      if (!rows.length) return "";
      const shown = rows.slice(0, maxItems);
      const suffix = rows.length > shown.length ? ` (+${rows.length - shown.length} more)` : "";
      return `${shown.join(", ")}${suffix}`;
    }

    function clipFocusText(value, maxChars = 160) {
      const text = String(value || "").replace(/\s+/g, " ").trim();
      if (!text) return "";
      if (text.length <= maxChars) return text;
      const hardLimit = Math.max(8, maxChars - 1);
      const boundary = text.lastIndexOf(" ", hardLimit);
      const cutAt = boundary >= Math.floor(maxChars * 0.6) ? boundary : hardLimit;
      return `${text.slice(0, cutAt).trimEnd()}…`;
    }

    function toSentence(text) {
      const token = String(text || "").trim();
      if (!token) return "";
      if (token.endsWith("…")) return token;
      if (/[.!?]$/.test(token)) return token;
      return `${token}.`;
    }

    function isGeneratedNarrativeFile(file) {
      const token = String(file || "").trim();
      if (!token) return true;
      if (token.startsWith("odylith/radar/source/") && !token.startsWith("odylith/radar/source/ui/")) {
        return false;
      }
      if (token.startsWith("odylith/atlas/source/")) {
        if (token.startsWith("odylith/atlas/source/catalog/")) return true;
        return token.endsWith(".svg") || token.endsWith(".png");
      }
      return token.startsWith("odylith/radar/source/ui/")
        || token === "odylith/radar/radar.html"
        || token === "odylith/radar/backlog-payload.v1.js"
        || token === "odylith/radar/backlog-app.v1.js"
        || token === "odylith/radar/standalone-pages.v1.js"
        || /^odylith\/radar\/backlog-(detail|document)-shard-\d+\.v1\.js$/.test(token)
        || token === "odylith/radar/traceability-graph.v1.json"
        || token === "odylith/radar/traceability-autofix-report.v1.json"
        || token === "odylith/casebook/casebook-payload.v1.js"
        || token === "odylith/registry/registry.html"
        || token === "odylith/registry/registry-app.v1.js"
        || token === "odylith/registry/registry-payload.v1.js"
        || /^odylith\/registry\/registry-detail-shard-\d+\.v1\.js$/.test(token)
        || token === "odylith/runtime/delivery_intelligence.v4.json"
        || token.startsWith("odylith/compass/runtime/")
        || token === "odylith/compass/compass-app.v1.js"
        || token === "odylith/compass/compass-shared.v1.js"
        || token === "odylith/compass/compass-state.v1.js"
        || token === "odylith/compass/compass-summary.v1.js"
        || token === "odylith/compass/compass-timeline.v1.js"
        || token === "odylith/compass/compass-waves.v1.js"
        || token === "odylith/compass/compass-releases.v1.js"
        || token === "odylith/compass/compass-workstreams.v1.js"
        || token === "odylith/compass/compass-ui-runtime.v1.js"
        || token === "odylith/compass/compass-style-base.v1.css"
        || token === "odylith/compass/compass-style-execution-waves.v1.css"
        || token === "odylith/compass/compass-style-surface.v1.css"
        || token === "odylith/compass/compass.html"
        || token === "odylith/index.html"
        || token === "odylith/atlas/atlas.html"
        || token === "odylith/atlas/mermaid-payload.v1.js"
        || token === "odylith/atlas/mermaid-app.v1.js";
    }

    function splitNarrativeFiles(files) {
      const rows = Array.isArray(files) ? files.map((file) => String(file || "").trim()).filter(Boolean) : [];
      const source = [];
      const generated = [];
      rows.forEach((file) => {
        if (isGeneratedNarrativeFile(file)) {
          generated.push(file);
        } else {
          source.push(file);
        }
      });
      return { source, generated };
    }

    function isGeneratedOnlyLocalEvent(eventRow) {
      const kind = String(eventRow && eventRow.kind ? eventRow.kind : "").trim();
      if (kind !== "local_change") return false;
      const files = Array.isArray(eventRow && eventRow.files) ? eventRow.files : [];
      const fileSplit = splitNarrativeFiles(files);
      return fileSplit.source.length === 0 && fileSplit.generated.length > 0;
    }

    function buildSignalSummary(kindCounts) {
      const counts = kindCounts && typeof kindCounts === "object" ? kindCounts : {};
      const lines = [];
      const impl = Number(counts.implementation || 0);
      const decision = Number(counts.decision || 0);
      const statement = Number(counts.statement || 0);
      const commit = Number(counts.commit || 0);
      const local = Number(counts.local_change || 0);
      const plan = Number(counts.plan_update || 0) + Number(counts.plan_completion || 0);
      const bugs = Number(counts.bug_watch || 0) + Number(counts.bug_update || 0) + Number(counts.bug_resolved || 0);
      if (impl > 0) lines.push(`${impl} implementation`);
      if (decision > 0) lines.push(`${decision} decision`);
      if (statement > 0) lines.push(`${statement} narrative`);
      if (commit > 0) lines.push(`${commit} commit`);
      if (local > 0) lines.push(`${local} local edit`);
      if (plan > 0) lines.push(`${plan} plan signal`);
      if (bugs > 0) lines.push(`${bugs} bug signal`);
      if (!lines.length) return "no classified execution signals";
      return lines.slice(0, 3).join(", ");
    }

    function wsCostBadge(ws, windowKey) {
      const cost = ws && ws.cost && ws.cost[windowKey] ? ws.cost[windowKey] : null;
      if (!cost) return "-";
      return `${Number(cost.index || 0)} (${String(cost.band || "").trim() || "N/A"})`;
    }

    function phaseChipClass(phaseValue) {
      const token = String(phaseValue || "").trim().toLowerCase();
      if (token === "planning") return "phase-planning";
      if (token === "implementation") return "phase-implementation";
      if (token === "finished") return "phase-finished";
      if (token === "queued") return "phase-queued";
      return "phase-other";
    }

    function phaseSortOrder(phaseValue) {
      const token = String(phaseValue || "").trim().toLowerCase();
      if (token === "implementation") return 0;
      if (token === "planning") return 1;
      if (token === "finished") return 2;
      if (token === "queued") return 3;
      return 4;
    }

    function proofRefHref(ref) {
      const row = ref && typeof ref === "object" ? ref : {};
      const surface = String(row.surface || "").trim().toLowerCase();
      const value = String(row.value || "").trim();
      if (!value) return "../index.html?tab=compass";
      if (surface === "casebook") return `../index.html?tab=casebook&bug=${encodeURIComponent(value)}`;
      if (surface === "registry") return `../index.html?tab=registry&component=${encodeURIComponent(value.replace(/^component:/, ""))}`;
      if (surface === "atlas") return `../index.html?tab=atlas&diagram=${encodeURIComponent(value)}`;
      if (surface === "radar") return radarWorkstreamHref(value);
      if (surface === "compass") return `../index.html?tab=compass&scope=${encodeURIComponent(value)}&date=live`;
      return `../index.html?tab=compass&scope=${encodeURIComponent(value)}&date=live`;
    }

    function workstreamProofDetailRows(selected) {
      const proofState = selected && selected.proof_state && typeof selected.proof_state === "object"
        ? selected.proof_state
        : {};
      const claimGuard = selected && selected.claim_guard && typeof selected.claim_guard === "object"
        ? selected.claim_guard
        : {};
      const proofResolution = selected && selected.proof_state_resolution && typeof selected.proof_state_resolution === "object"
        ? selected.proof_state_resolution
        : {};
      const proofSummaryLines = Array.isArray(selected && selected.proof_summary_lines)
        ? selected.proof_summary_lines.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const proofRefs = Array.isArray(selected && selected.proof_refs)
        ? selected.proof_refs.filter((item) => item && typeof item === "object")
        : [];
      const deploymentTruth = proofState && proofState.deployment_truth && typeof proofState.deployment_truth === "object"
        ? proofState.deployment_truth
        : {};
      const allowedNextWork = Array.isArray(proofState.allowed_next_work)
        ? proofState.allowed_next_work.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const deprioritized = Array.isArray(proofState.deprioritized_until_cleared)
        ? proofState.deprioritized_until_cleared.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const lastFalsification = proofState && proofState.last_falsification && typeof proofState.last_falsification === "object"
        ? proofState.last_falsification
        : {};
      const resolutionState = String(proofResolution.state || "").trim().toLowerCase();
      const resolutionLaneIds = Array.isArray(proofResolution.lane_ids)
        ? proofResolution.lane_ids.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
      const detailRows = [];
      const pushRow = (label, value) => {
        const token = String(value || "").trim();
        if (!token) return;
        detailRows.push(`<div><strong>${escapeHtml(label)}:</strong> ${escapeHtml(token)}</div>`);
      };
      pushRow("Current blocker", proofState.current_blocker);
      pushRow("Failure fingerprint", proofState.failure_fingerprint);
      pushRow("Frontier", proofState.frontier_phase);
      pushRow("Evidence tier", String(proofState.evidence_tier || "").replace(/_/g, " "));
      pushRow("Clear only when", proofState.clearance_condition);
      pushRow("Last falsification", lastFalsification.recorded_at);
      pushRow("Highest truthful claim", claimGuard.highest_truthful_claim);
      if (!String(proofState.current_blocker || "").trim() && resolutionState === "ambiguous") {
        pushRow("Proof state", `Ambiguous across ${resolutionLaneIds.join(", ") || "multiple lanes"}`);
      }
      if (!String(proofState.current_blocker || "").trim() && resolutionState === "none") {
        pushRow("Proof state", "No dominant proof lane is resolved for this workstream yet.");
      }
      if (allowedNextWork.length) {
        pushRow("Allowed next work", allowedNextWork.join(", "));
      }
      if (deprioritized.length) {
        pushRow("Deprioritized", deprioritized.join(", "));
      }
      const deploymentParts = [
        `local ${String(deploymentTruth.local_head || "unknown").trim() || "unknown"}`,
        `pushed ${String(deploymentTruth.pushed_head || "unknown").trim() || "unknown"}`,
        `published ${String(deploymentTruth.published_source_commit || "unknown").trim() || "unknown"}`,
        `runner ${String(deploymentTruth.runner_fingerprint || "unknown").trim() || "unknown"}`,
        `last fail ${String(deploymentTruth.last_live_failing_commit || "unknown").trim() || "unknown"}`,
      ];
      pushRow("Deployment truth", deploymentParts.join(" · "));
      if (!detailRows.length && !proofSummaryLines.length && !proofRefs.length) {
        return "";
      }
      const refsHtml = proofRefs.length
        ? `<div class="chips">${
            proofRefs.slice(0, 4).map((ref) => {
              const label = String(ref.label || ref.value || "Proof").trim() || "Proof";
              return `<a class="chip chip-link" href="${escapeHtml(proofRefHref(ref))}" target="_top">${escapeHtml(label)}</a>`;
            }).join("")
          }</div>`
        : "";
      const summaryHtml = proofSummaryLines.length
        ? `<div>${proofSummaryLines.slice(0, 4).map((line) => `<div>${escapeHtml(line)}</div>`).join("")}</div>`
        : "";
      return `
        <div class="ws-inline-detail">
          <div class="ws-detail-kicker">Proof Control</div>
          <div class="ws-detail-grid">
            ${detailRows.join("")}
            ${summaryHtml}
            ${refsHtml ? `<div><strong>Proof links:</strong> ${refsHtml}</div>` : ""}
          </div>
        </div>
      `;
    }

    function renderCurrentWorkstreams(payload, state, events, transactions, navigationState) {
      const rows = scopeWorkstreams(payload, state);
      const target = document.getElementById("current-workstreams");
      const windowKey = state.window === "24h" ? "24h" : "48h";
      const planLookup = planHrefLookup(payload);
      const workstreamTitles = workstreamTitleLookup(payload);
      const txRows = Array.isArray(transactions) ? transactions : [];
      const eventRows = Array.isArray(events) ? events : [];
      const digestContextByWorkstream = digestWorkstreamContextLookup(payload, state);
      const focusPayload = payload && payload.execution_focus && typeof payload.execution_focus === "object"
        ? payload.execution_focus
        : {};
      const focusByWorkstream = focusPayload && focusPayload.by_workstream && typeof focusPayload.by_workstream === "object"
        ? focusPayload.by_workstream
        : {};
      const activeWindowMinutes = Number(focusPayload.active_window_minutes || 15);
      const navState = navigationState && typeof navigationState === "object" ? navigationState : state;
      const normalizeRegistryComponents = (rawValue) => {
        const rows = Array.isArray(rawValue) ? rawValue : [];
        const deduped = [];
        const seen = new Set();
        rows.forEach((row) => {
          const componentId = String(row && row.component_id ? row.component_id : "").trim().toLowerCase();
          if (!componentId || seen.has(componentId)) return;
          seen.add(componentId);
          const name = String(row && row.name ? row.name : componentId).trim() || componentId;
          deduped.push({ component_id: componentId, name });
        });
        return deduped;
      };

      if (!rows.length) {
        target.innerHTML = '<p class="empty">No active workstreams in this scope.</p>';
        return;
      }

      const records = rows.map((row) => {
        const ideaId = String(row.idea_id || "").trim();
        const plan = row.plan || {};
        const timeline = row.timeline || {};
        const why = row.why || {};
        const activity = row.activity && typeof row.activity === "object" ? (row.activity[windowKey] || {}) : {};
        const registryComponents = normalizeRegistryComponents(row.registry_components);
        const executionWaveProgramsForRow = Array.isArray(row.execution_wave_programs)
          ? row.execution_wave_programs
          : workstreamWavePrograms(payload, ideaId);
        const primaryWaveProgram = executionWaveProgramsForRow.length ? executionWaveProgramsForRow[0] : null;

        const phase = String(row.status || "").trim().toLowerCase();
        const phaseLabel = phase ? `${phase.charAt(0).toUpperCase()}${phase.slice(1)}` : "Unknown";
        const phaseClass = phaseChipClass(phase);
        const progressRatio = numericProgressOrNull(
          Object.prototype.hasOwnProperty.call(plan, "display_progress_ratio")
            ? plan.display_progress_ratio
            : (Object.prototype.hasOwnProperty.call(plan, "progress_ratio") ? plan.progress_ratio : null)
        );
        const progressLabel = String(plan && plan.display_progress_label ? plan.display_progress_label : "").trim();
        const progressKnown = progressRatio !== null;
        const progressPct = progressKnown ? Math.round(progressRatio * 100) : null;
        const progressCellLabel = progressKnown ? `${progressPct}%` : (progressLabel || "n/a");
        const doneTasks = Number(plan.done_tasks || 0);
        const totalTasks = Number(plan.total_tasks || 0);
        const eta = timeline.eta_days;
        const etaConfidence = String(timeline.eta_confidence || "").toUpperCase();
        const etaLabel = typeof eta === "number" ? `${eta}d (${etaConfidence || "LOW"})` : "N/A";
        const costLabel = wsCostBadge(row, windowKey);

        const whyText = String(why.why_now || why.opportunity || why.founder_pov || "").trim();
        const shortWhy = clipFocusText(whyText, 280);
        const nextTasks = Array.isArray(plan.next_tasks) ? plan.next_tasks.map((item) => String(item || "").trim()).filter(Boolean) : [];
        const nextCheckpoint = nextTasks.length
          ? clipFocusText(nextTasks[0], 180)
          : "No explicit next checkpoint captured in current plan checklist.";

        const strictScopedTransactions = txRows.filter((tx) => {
          const ws = Array.isArray(tx.workstreams) ? tx.workstreams.map((item) => String(item || "").trim()).filter(Boolean) : [];
          return ws.length === 1 && ws[0] === ideaId;
        });
        const strictScopedEvents = eventRows.filter((event) => {
          const ws = Array.isArray(event.workstreams) ? event.workstreams.map((item) => String(item || "").trim()).filter(Boolean) : [];
          return ws.length === 1 && ws[0] === ideaId;
        });
        const hasStrictScopeLink = strictScopedTransactions.length > 0 || strictScopedEvents.length > 0;
        const scopedKindCounts = {
          implementation: 0,
          decision: 0,
          statement: 0,
          commit: 0,
          local_change: 0,
          plan_update: 0,
          plan_completion: 0,
          bug_watch: 0,
          bug_update: 0,
          bug_resolved: 0,
        };
        const scopedFiles = [];
        strictScopedEvents.slice(0, 20).forEach((event) => {
          const kind = String(event && event.kind ? event.kind : "").trim();
          if (Object.prototype.hasOwnProperty.call(scopedKindCounts, kind)) {
            scopedKindCounts[kind] += 1;
          }
          const files = Array.isArray(event && event.files) ? event.files : [];
          if (files.length) scopedFiles.push(...files);
        });
        const prioritizedContextEvent = strictScopedEvents.find((event) => {
          const kind = String(event && event.kind ? event.kind : "").trim();
          if (["implementation", "decision", "statement", "plan_update", "plan_completion", "commit"].includes(kind)) {
            return true;
          }
          if (kind !== "local_change") return false;
          const fileSplit = splitNarrativeFiles(Array.isArray(event && event.files) ? event.files : []);
          return fileSplit.source.length > 0;
        }) || strictScopedEvents[0] || null;
        const txCount = strictScopedTransactions.length;
        const txEventCount = strictScopedTransactions.reduce((total, tx) => total + Number(tx.event_count || 0), 0);
        const txFileCount = strictScopedTransactions.reduce((total, tx) => total + Number(tx.files_count || 0), 0);
        const latestTx = strictScopedTransactions[0] || null;
        const latestTxTs = latestTx ? (latestTx.end_ts_iso || latestTx.start_ts_iso || "") : "";
        const latestTxId = String((latestTx && latestTx.transaction_id) || "").trim();
        const latestTxLabel = compactTimestamp(latestTxTs || timeline.last_activity_iso);
        const latestHeadlineRaw = latestTx ? String(latestTx.headline || "").trim() : "";
        const latestHeadline = clipFocusText(latestHeadlineRaw, 140);

        const liveFocus = focusByWorkstream && focusByWorkstream[ideaId] && typeof focusByWorkstream[ideaId] === "object"
          ? focusByWorkstream[ideaId]
          : {};
        const liveIsActive = hasStrictScopeLink && Boolean(liveFocus.is_active);
        const liveLabel = liveIsActive ? "Active" : "Quiet";
        const liveLast = compactTimestamp(liveFocus.last_event_iso || latestTxTs || timeline.last_activity_iso);
        const txFocusFiles = Array.isArray(latestTx && latestTx.files) ? latestTx.files : [];
        if (txFocusFiles.length) scopedFiles.push(...txFocusFiles);
        const scopedFileSplit = splitNarrativeFiles(scopedFiles);
        const scopedAreaFiles = scopedFileSplit.source.length ? scopedFileSplit.source : scopedFiles;
        const scopedAreas = focusAreaSummary(scopedAreaFiles);
        const scopedSignalSummary = buildSignalSummary(scopedKindCounts);
        const hasScopedImplementationSignal = Boolean(scopedKindCounts.implementation || scopedKindCounts.decision || scopedKindCounts.statement);
        const implementationFocusParts = [];
        if (hasStrictScopeLink && scopedAreas.length) {
          implementationFocusParts.push(`implementing ${joinWithAnd(scopedAreas)}`);
        }
        if (hasStrictScopeLink && scopedSignalSummary !== "no classified execution signals") {
          implementationFocusParts.push(`signals show ${scopedSignalSummary}`);
        }
        if (hasStrictScopeLink && liveIsActive) {
          implementationFocusParts.push("execution is currently active");
        }
        const implementationFocus = hasStrictScopeLink && hasScopedImplementationSignal && implementationFocusParts.length
          ? toSentence(clipFocusText(`Currently ${implementationFocusParts.join("; ")}`, 280))
          : "";

        const commitCount = Number(activity.commit_count || 0);
        const localChangeCount = Number(activity.local_change_count || 0);
        const fileTouchCount = Number(activity.file_touch_count || 0);
        const lineage = row && row.lineage && typeof row.lineage === "object" ? row.lineage : {};
        const lineageSummaryParts = [];
        const lineageRows = [
          ["Reopens", lineage.reopens],
          ["Reopened by", lineage.reopened_by],
          ["Split from", lineage.split_from],
          ["Split into", lineage.split_into],
          ["Merged into", lineage.merged_into],
          ["Merged from", lineage.merged_from],
        ];
        lineageRows.forEach(([label, rawIds]) => {
          const ids = normalizeIdList(rawIds);
          if (!ids.length) return;
          lineageSummaryParts.push(`${label} ${ids.join(", ")}`);
        });
        const lineageSummary = lineageSummaryParts.join("; ");
        const planHref = String(planLookup[ideaId] || "").trim();
        const tableTitle = String(row.title || "").trim();
        const focusContext = clipFocusText(
          String(liveFocus.context || liveFocus.headline || liveFocus.latest_event_summary || "").trim(),
          140,
        );
        const eventContext = prioritizedContextEvent
          ? clipFocusText(
              String(
                prioritizedContextEvent.context
                || prioritizedContextEvent.summary
                || "",
              ).trim(),
              140,
            )
          : "";
        const digestContext = clipFocusText(
          String(digestContextByWorkstream[ideaId] || "").trim(),
          140,
        );
        const latestContext = (hasStrictScopeLink ? latestHeadline : "")
          || (hasStrictScopeLink ? focusContext : "")
          || digestContext
          || eventContext
          || "No workstream-linked implementation context in selected window.";
        const txSignalCount = txCount + txEventCount + txFileCount;
        const relatedDiagramIds = normalizeDiagramIdList(row.related_diagram_ids);
        const waveSpanLabel = primaryWaveProgram ? String(primaryWaveProgram.wave_span_label || "").trim() : "";
        const waveRoleLabel = primaryWaveProgram ? String(primaryWaveProgram.role_label || "").trim() : "";
        const waveUmbrellaId = primaryWaveProgram ? String(primaryWaveProgram.umbrella_id || "").trim() : "";
        const waveProgramNext = primaryWaveProgram ? String(primaryWaveProgram.program_next_label || "").trim() : "";
        const waveActiveLabels = primaryWaveProgram && Array.isArray(primaryWaveProgram.active_wave_labels)
          ? primaryWaveProgram.active_wave_labels.map((item) => String(item || "").trim()).filter(Boolean)
          : [];
        const waveProgramSummary = primaryWaveProgram
          ? [waveActiveLabels.length ? `Active: ${waveActiveLabels.join(", ")}` : "", waveProgramNext ? `Next: ${waveProgramNext}` : ""]
              .filter(Boolean)
              .join(" · ")
          : "";
        const hasActiveWaveMembership = primaryWaveProgram ? Boolean(primaryWaveProgram.has_active_wave) : false;
        const release = row && row.release && typeof row.release === "object" ? row.release : {};
        const releaseLabel = compassWorkstreamReleaseLabel(release);
        const releaseHistorySummary = String(row.release_history_summary || "").trim();

        return {
          ideaId,
          title: String(row.title || "").trim(),
          tableTitle,
          phaseToken: phase,
          phaseLabel,
          phaseClass,
          liveLabel,
          liveIsActive,
          progressPct,
          progressKnown,
          progressLabel,
          progressCellLabel,
          doneTasks,
          totalTasks,
          etaLabel,
          costLabel,
          liveLast,
          txSignalCount,
          nextCheckpoint,
          whyText: shortWhy || "-",
          implementationFocus,
          latestContext: latestContext || "-",
          lineageSummary,
          latestTxLabel,
          latestTxId,
          commitCount,
          localChangeCount,
          fileTouchCount,
          txCount,
          txEventCount,
          txFileCount,
          timelineEventCount: strictScopedEvents.length,
          registryComponents,
          executionWavePrograms: executionWaveProgramsForRow,
          waveSpanLabel,
          waveRoleLabel,
          waveUmbrellaId,
          waveProgramNext,
          waveProgramSummary,
          hasActiveWaveMembership,
          releaseLabel,
          releaseHistorySummary,
          relatedDiagramIds,
          planHref,
          proof_state: row && row.proof_state && typeof row.proof_state === "object" ? row.proof_state : {},
          proof_state_resolution: row && row.proof_state_resolution && typeof row.proof_state_resolution === "object" ? row.proof_state_resolution : {},
          claim_guard: row && row.claim_guard && typeof row.claim_guard === "object" ? row.claim_guard : {},
          proof_refs: Array.isArray(row && row.proof_refs) ? row.proof_refs : [],
          proof_summary_lines: Array.isArray(row && row.proof_summary_lines) ? row.proof_summary_lines : [],
        };
      });

      if (!records.length) {
        target.innerHTML = '<p class="empty">No active workstreams in this scope.</p>';
        return;
      }

      records.sort((left, right) => {
        const phaseDelta = phaseSortOrder(left.phaseToken) - phaseSortOrder(right.phaseToken);
        if (phaseDelta !== 0) return phaseDelta;
        if (left.liveIsActive !== right.liveIsActive) return left.liveIsActive ? -1 : 1;
        const signalDelta = Number(right.txSignalCount || 0) - Number(left.txSignalCount || 0);
        if (signalDelta !== 0) return signalDelta;
        return String(left.ideaId || "").localeCompare(String(right.ideaId || ""));
      });

      const persistedSelection = String(target.dataset.selectedWorkstream || "").trim();
      const initiallyExpandedId = records.some((item) => item.ideaId === persistedSelection)
        ? persistedSelection
        : "";

      const detailMarkup = (selected) => {
        const primaryDiagramId = Array.isArray(selected.relatedDiagramIds) && selected.relatedDiagramIds.length
          ? String(selected.relatedDiagramIds[0] || "").trim()
          : "";
        const registryComponents = Array.isArray(selected.registryComponents) ? selected.registryComponents : [];
        const registryComponentLinks = registryComponents.length
          ? `<span class="chips">${
              registryComponents.map((item) => {
                const componentHref = `../index.html?tab=registry&component=${encodeURIComponent(item.component_id)}`;
                return `<a class="chip chip-link" href="${escapeHtml(componentHref)}" target="_top"${registryComponentTooltipAttrs(item, `Open registry for ${item.component_id}`)}>${escapeHtml(item.component_id)}</a>`;
              }).join("")
            }</span>`
          : "";
        const wavePrograms = Array.isArray(selected.executionWavePrograms) ? selected.executionWavePrograms : [];
        const waveChipRow = wavePrograms.length
          ? `<div class="ws-wave-chip-row">${
              wavePrograms.map((program) => {
                const spanLabel = String(program && program.wave_span_label ? program.wave_span_label : "").trim();
                const roleLabel = String(program && program.role_label ? program.role_label : "").trim();
                const umbrellaId = String(program && program.umbrella_id ? program.umbrella_id : "").trim();
                const chipParts = [
                  umbrellaId ? `<span class="label execution-wave-label wave-chip-program">${escapeHtml(umbrellaId)}</span>` : "",
                  spanLabel ? `<span class="label execution-wave-label ${program && program.has_active_wave ? "wave-status-active" : "wave-status-planned"}">${escapeHtml(spanLabel)}</span>` : "",
                  roleLabel ? `<span class="label execution-wave-label wave-role-chip">${escapeHtml(roleLabel)}</span>` : "",
                ].filter(Boolean);
                return chipParts.join("");
              }).join("")
            }</div>`
          : "";
        const liveWindowClause = `${selected.liveIsActive ? "active inside" : "outside"} ${Math.max(1, Math.round(activeWindowMinutes))}m live window`;
        const proofControlHtml = workstreamProofDetailRows(selected);
        return `
            <div class="ws-inline-detail">
              <div class="ws-detail-kicker">Selected Workstream Detail</div>
              <div class="ws-detail-title">${escapeHtml(selected.title || selected.ideaId)}</div>
              <div class="chips">
              <span class="chip"${workstreamTooltipAttrs(selected.ideaId, workstreamTitles, `Workstream ${selected.ideaId}`)}>${escapeHtml(selected.ideaId)}</span>
              <span class="chip ${selected.phaseClass}">Phase: ${escapeHtml(selected.phaseLabel)}</span>
              <span class="chip ${selected.liveIsActive ? "" : "subtle"}">Live: ${escapeHtml(selected.liveLabel)}</span>
              ${selected.releaseLabel ? `<span class="chip subtle">${escapeHtml(selected.releaseLabel)}</span>` : ""}
              ${selected.progressKnown
                ? `<span class="chip subtle">Progress: ${escapeHtml(`${selected.progressPct}% (${selected.doneTasks}/${selected.totalTasks})`)}</span>`
                : (selected.progressLabel
                  ? `<span class="chip subtle">Progress: ${escapeHtml(selected.progressLabel)}</span>`
                  : "")}
              <span class="chip subtle">Cost: ${escapeHtml(selected.costLabel)}</span>
              <span class="chip subtle">ETA: ${escapeHtml(selected.etaLabel)}</span>
            </div>
            ${waveChipRow}
            <div class="ws-detail-grid">
              <div><strong>Why now:</strong> ${escapeHtml(selected.whyText)}</div>
              <div><strong>Last update:</strong> ${escapeHtml(`${selected.liveLast} (${liveWindowClause})`)}</div>
              <div><strong>Latest context:</strong> ${escapeHtml(selected.latestContext)}</div>
              ${selected.waveProgramSummary ? `<div><strong>Wave posture:</strong> ${escapeHtml(selected.waveProgramSummary)}</div>` : ""}
              ${selected.releaseHistorySummary ? `<div><strong>Release history:</strong> ${escapeHtml(selected.releaseHistorySummary)}</div>` : ""}
              ${selected.lineageSummary ? `<div><strong>Lineage:</strong> ${escapeHtml(selected.lineageSummary)}</div>` : ""}
              ${selected.implementationFocus ? `<div><strong>Implementation focus:</strong> ${escapeHtml(selected.implementationFocus)}</div>` : ""}
              ${registryComponentLinks ? `<div><strong>Registry components:</strong> ${registryComponentLinks}</div>` : ""}
              ${primaryDiagramId ? `<div><strong>Atlas focus:</strong> ${escapeHtml(primaryDiagramId)}</div>` : ""}
              <div><strong>Next checkpoint:</strong> ${escapeHtml(selected.nextCheckpoint)}</div>
            </div>
          </div>
          ${proofControlHtml}
        `;
      };

      const renderWaveSummaryCell = (item) => {
        if (!item.waveSpanLabel) {
          return '<span class="muted">-</span>';
        }
        return `<div class="ws-wave-chip-row"><span class="label execution-wave-label ${item.hasActiveWaveMembership ? "wave-status-active" : "wave-status-planned"}">${escapeHtml(item.waveSpanLabel)}</span>${item.waveRoleLabel ? `<span class="label execution-wave-label wave-role-chip">${escapeHtml(item.waveRoleLabel)}</span>` : ""}</div>`;
      };

      const renderSummaryRowAttrs = (item, rowKind, isSelected) => (
        `class="ws-summary-row ${rowKind}${isSelected ? " is-selected" : ""}" data-ws-id="${escapeHtml(item.ideaId)}" tabindex="0" role="button" aria-expanded="${isSelected ? "true" : "false"}" aria-label="Open detail for ${escapeHtml(item.ideaId)}"`
      );

      const rowHtml = records.map((item) => {
        const isSelected = item.ideaId === initiallyExpandedId;
        const radarHref = radarWorkstreamHref(item.ideaId);
        return `
        <tr ${renderSummaryRowAttrs(item, "ws-row-title", isSelected)}>
          <td class="ws-title-cell ws-title-row-cell" colspan="5">
            ${escapeHtml(item.tableTitle || "-")}
          </td>
        </tr>
        <tr ${renderSummaryRowAttrs(item, "ws-row-meta", isSelected)}>
          <td class="ws-col-id"><div class="ws-id-stack"><a class="ws-id-btn" href="${escapeHtml(radarHref)}" target="_top" data-ws-id="${escapeHtml(item.ideaId)}"${workstreamTooltipAttrs(item.ideaId, workstreamTitles, `Open radar for ${item.ideaId}`)}>${escapeHtml(item.ideaId)}</a>${item.releaseLabel ? `<span class="chip subtle">${escapeHtml(item.releaseLabel)}</span>` : ""}</div></td>
          <td class="ws-col-wave">${renderWaveSummaryCell(item)}</td>
          <td class="ws-col-phase"><span class="chip ${item.phaseClass}">${escapeHtml(item.phaseLabel)}</span></td>
          <td class="ws-col-live"><span class="chip ${item.liveIsActive ? "" : "subtle"}">${escapeHtml(item.liveLabel)}</span></td>
          <td class="ws-col-progress">${escapeHtml(item.progressCellLabel)}</td>
        </tr>
        <tr class="ws-detail-row${isSelected ? " is-open" : ""}" data-ws-detail="${escapeHtml(item.ideaId)}">
          <td class="ws-detail-cell" colspan="5">${detailMarkup(item)}</td>
        </tr>
      `;
      }).join("");

      target.innerHTML = `
        <div class="ws-table-wrap">
          <table class="ws-table">
            <thead>
              <tr>
                <th class="ws-col-id">ID</th>
                <th class="ws-col-wave">Wave</th>
                <th class="ws-col-phase">Phase</th>
                <th class="ws-col-live">Live</th>
                <th class="ws-col-progress">Progress</th>
              </tr>
            </thead>
            <tbody data-role="ws-table-body">${rowHtml}</tbody>
          </table>
        </div>
      `;

      const tableBody = target.querySelector('[data-role="ws-table-body"]');
      if (!tableBody) {
        return;
      }

      const renderDetail = (workstreamId) => {
        const token = String(workstreamId || "").trim();
        const selected = token ? (records.find((item) => item.ideaId === token) || null) : null;
        target.dataset.selectedWorkstream = selected ? selected.ideaId : "";

        tableBody.querySelectorAll("tr.ws-summary-row").forEach((node) => {
          const rowWs = String(node.getAttribute("data-ws-id") || "").trim();
          const isSelected = Boolean(selected) && rowWs === selected.ideaId;
          node.classList.toggle("is-selected", isSelected);
          node.setAttribute("aria-expanded", isSelected ? "true" : "false");
        });
        tableBody.querySelectorAll("tr.ws-detail-row").forEach((node) => {
          const rowWs = String(node.getAttribute("data-ws-detail") || "").trim();
          node.classList.toggle("is-open", Boolean(selected) && rowWs === selected.ideaId);
        });
      };

      const selectRow = (workstreamId, options = {}) => {
        const token = String(workstreamId || "").trim();
        if (!token || !records.some((row) => row.ideaId === token)) return;
        const isAlreadyOpen = String(target.dataset.selectedWorkstream || "").trim() === token;
        if (isAlreadyOpen && !(options && options.setScope)) {
          renderDetail("");
          return;
        }
        renderDetail(token);
        const shouldSetScope = Boolean(options && options.setScope);
        if (!shouldSetScope || state.workstream === token) return;
        const next = new URLSearchParams(stateToQuery(state));
        next.set("scope", token);
        navigateCompass(next);
      };

      tableBody.querySelectorAll("tr.ws-summary-row").forEach((rowNode) => {
        const wsId = String(rowNode.getAttribute("data-ws-id") || "").trim();
        rowNode.addEventListener("click", () => {
          selectRow(wsId);
        });
        rowNode.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            selectRow(wsId);
          }
        });
      });
      if (initiallyExpandedId) {
        renderDetail(initiallyExpandedId);
      }
    }

    function renderTimeline(payload, state, events, transactions) {
      const target = document.getElementById("timeline");
      const linkContext = briefLinkContext(payload, state);
      const planLookup = planHrefLookup(payload);
      const planFileLookup = planFileHrefLookup(payload);
      const workstreamTitles = workstreamTitleLookup(payload);
      const workstreamNarratives = workstreamNarrativeLookup(payload);
      const historyDates = knownHistoryDateTokens(payload);
      const missingSnapshot = state.date !== "live" && DATE_RE.test(state.date) && !historyDates.includes(state.date);

      const renderTimelineWorkstreamChips = (workstreams, maxItems) => {
        const rows = Array.isArray(workstreams) ? workstreams : [];
        const chips = rows
          .map((id) => String(id || "").trim())
          .filter(Boolean)
          .slice(0, Math.max(0, Number(maxItems || 0)))
          .map((id) => {
            const tooltipAttrs = workstreamTooltipAttrs(id, workstreamTitles, `Open radar for ${id}`);
            return `<a class="chip chip-link workstream-id-chip" href="${escapeHtml(radarWorkstreamHref(id))}" target="_top"${tooltipAttrs}>${escapeHtml(id)}</a>`;
          });
        return chips.length ? `<div class="chips">${chips.join("")}</div>` : "";
      };

      if (missingSnapshot) {
        target.innerHTML = '<div class="empty">No snapshot available for this day. Showing live payload context; timeline events may be empty.</div>';
        return;
      }
      const dayTokens = timelineDayTokens(state, payload);
      if (!dayTokens.length) {
        target.innerHTML = '<div class="empty">No audit day available for this scope.</div>';
        return;
      }

      const selectedAuditDay = DATE_RE.test(String(state.audit_day || "").trim())
        ? String(state.audit_day || "").trim()
        : "";
      const renderDays = selectedAuditDay ? [selectedAuditDay] : dayTokens.slice().reverse();
      const rows = [];
      const txRows = Array.isArray(transactions) ? transactions : [];
      const eventRows = Array.isArray(events) ? events : [];
      const renderDaySet = new Set(renderDays);
      const relevantTransactions = txRows.filter((row) => renderDaySet.has(toLocalDateToken(row.end_ts_iso || row.start_ts_iso)));
      const relevantEvents = eventRows.filter((row) => renderDaySet.has(toLocalDateToken(row.ts_iso)));
      if (!relevantTransactions.length && !relevantEvents.length) {
        target.innerHTML = state.workstream
          ? '<div class="empty">No audit events in this scope and window.</div>'
          : '<div class="empty">No audit events in this window.</div>';
        return;
      }

      const renderTimelineEventCard = (eventRow) => {
        const eventTime = toDate(eventRow.ts_iso);
        const timeLabelInner = eventTime
          ? formatTimeInCompassTimeZone(eventTime)
          : "--:--";
        const eventKind = timelineKindLabel(eventRow.kind);
        const eventMetaBase = `${timeLabelInner} • ${displayAuthorLabel(eventRow.author)}`;
        const eventWs = Array.isArray(eventRow.workstreams) ? eventRow.workstreams : [];
        const eventFiles = Array.isArray(eventRow.files) ? eventRow.files : [];
        const eventWsChips = renderTimelineWorkstreamChips(eventWs, 4);
        const eventPlanLinks = String(eventRow.kind || "").trim() === "plan_completion"
          ? Array.from(new Set(eventWs.map((id) => String(id || "").trim()).filter((id) => WORKSTREAM_RE.test(id))))
              .map((id) => {
                const href = String(planLookup[id] || "").trim();
                if (!href) return null;
                return { href, label: `plan ${id}` };
              })
              .filter(Boolean)
          : [];
        const filePlanLinks = Array.from(new Set(eventFiles.map((file) => normalizeRepoPath(file))))
          .map((fileToken) => {
            if (isPlanIndexPath(fileToken)) return null;
            const details = planFileLookup[fileToken];
            if (details && typeof details === "object") {
              const href = String(details.href || "").trim();
              if (href) {
                const ideaId = String(details.idea_id || "").trim();
                const label = ideaId ? `plan ${ideaId}` : "open plan";
                return { href, label };
              }
            }
            const fallbackHref = planMarkdownHref(fileToken);
            if (!fallbackHref) return null;
            return { href: fallbackHref, label: "open plan" };
          })
          .filter(Boolean);
        const planMetaLinks = [];
        const seenPlanHrefs = new Set();
        [...eventPlanLinks, ...filePlanLinks].forEach((linkRow) => {
          if (!linkRow || typeof linkRow !== "object") return;
          const href = String(linkRow.href || "").trim();
          if (!href || seenPlanHrefs.has(href)) return;
          seenPlanHrefs.add(href);
          const label = String(linkRow.label || "open plan").trim() || "open plan";
          planMetaLinks.push(`<a href="${escapeHtml(href)}" target="_top">${escapeHtml(label)}</a>`);
        });
        const eventMeta = planMetaLinks.length
          ? `${escapeHtml(eventMetaBase)} • ${planMetaLinks.join(" • ")}`
          : escapeHtml(eventMetaBase);
        const eventKindMarkup = eventKind
          ? `<div class="hour-event-kind">${escapeHtml(eventKind)}</div>`
          : "";
        return `
          <div class="hour-event">
            ${eventKindMarkup}
            <div class="hour-event-title">${escapeHtml(eventRow.summary || "")}</div>
            ${eventRow.context ? `<div class="tx-context">${escapeHtml(eventRow.context)}</div>` : ""}
            ${eventWsChips}
            <div class="hour-event-meta">${eventMeta}</div>
          </div>
        `;
      };

      for (const dayToken of renderDays) {
        const dayTransactions = txRows.filter((row) => {
          const token = toLocalDateToken(row.end_ts_iso || row.start_ts_iso);
          return token === dayToken;
        });
        const dayEvents = eventRows.filter((row) => {
          const token = toLocalDateToken(row.ts_iso);
          return token === dayToken;
        });
        const byHour = Array.from({ length: 24 }, () => []);
        const eventByHour = Array.from({ length: 24 }, () => []);
        for (const row of dayTransactions) {
          const ts = toDate(row.end_ts_iso || row.start_ts_iso);
          if (!ts) continue;
          byHour[hourInCompassTimeZone(ts)].push(row);
        }
        for (const row of dayEvents) {
          const ts = toDate(row.ts_iso);
          if (!ts) continue;
          eventByHour[hourInCompassTimeZone(ts)].push(row);
        }

        const hourRows = [];
        const hourBounds = visibleHourBoundsForDay(dayToken, state, payload);
        if (!hourBounds) {
          continue;
        }
        for (let hour = hourBounds.max; hour >= hourBounds.min; hour -= 1) {
          const items = byHour[hour];
          const hourEventItems = eventByHour[hour];
          const hourLabel = `${String(hour).padStart(2, "0")}:00`;
          if (!items.length && !hourEventItems.length) {
            hourRows.push(`
              <div class="hour-row">
                <div class="hour-label">${escapeHtml(hourLabel)}</div>
                <div class="hour-empty">No audit events.</div>
              </div>
            `);
            continue;
          }

          if (!items.length && hourEventItems.length) {
            const orderedEvents = [...hourEventItems].sort((left, right) => {
              const leftTs = toDate((left && left.ts_iso) || "");
              const rightTs = toDate((right && right.ts_iso) || "");
              const leftMs = leftTs ? leftTs.getTime() : 0;
              const rightMs = rightTs ? rightTs.getTime() : 0;
              if (rightMs !== leftMs) return rightMs - leftMs;
              const leftId = String(left && left.id ? left.id : "");
              const rightId = String(right && right.id ? right.id : "");
              return rightId.localeCompare(leftId);
            });
            const compactedGenerated = orderedEvents.filter((row) => isGeneratedOnlyLocalEvent(row)).length;
            const visibleStandalone = orderedEvents.filter((row) => !isGeneratedOnlyLocalEvent(row));
            const shownStandalone = visibleStandalone.slice(0, 24);
            const hiddenStandalone = Math.max(0, visibleStandalone.length - shownStandalone.length);
            const compactSummary = [];
            if (compactedGenerated > 0) {
              compactSummary.push(`<div class="tx-meta">Compacted ${compactedGenerated} generated events.</div>`);
            }
            if (hiddenStandalone > 0) {
              compactSummary.push(`<div class="tx-meta">Showing ${shownStandalone.length} of ${visibleStandalone.length} standalone events.</div>`);
            }
            const eventHtml = shownStandalone.length
              ? `${compactSummary.join("")}${shownStandalone.map((eventRow) => renderTimelineEventCard(eventRow)).join("")}`
              : `<div class="hour-event"><div class="hour-event-title">Compacted ${compactedGenerated} generated events.</div><div class="hour-event-meta">${escapeHtml(hourLabel)} • compacted</div></div>`;
            hourRows.push(`
              <div class="hour-row">
                <div class="hour-label">${escapeHtml(hourLabel)}</div>
                <div class="hour-events">${eventHtml}</div>
              </div>
            `);
            continue;
          }

          const orderedItems = [...items].sort((left, right) => {
            const leftTs = toDate((left && (left.end_ts_iso || left.start_ts_iso)) || "");
            const rightTs = toDate((right && (right.end_ts_iso || right.start_ts_iso)) || "");
            const leftMs = leftTs ? leftTs.getTime() : 0;
            const rightMs = rightTs ? rightTs.getTime() : 0;
            if (rightMs !== leftMs) return rightMs - leftMs;
            const leftId = String(left && left.id ? left.id : "");
            const rightId = String(right && right.id ? right.id : "");
            return rightId.localeCompare(leftId);
          });
          const eventHtml = orderedItems.map((row) => {
            const timeLabel = summarizeAnchorTime(row.start_ts_iso, row.end_ts_iso);
            const ws = Array.isArray(row.workstreams) ? row.workstreams : [];
            const chips = renderTimelineWorkstreamChips(ws, 5);
            const transactionId = String(row.transaction_id || row.id || "").trim();
            const sessionId = String(row.session_id || "").trim();
            const contextText = String(row.context || "").trim();
            const summary = String(row.headline || "").trim() || "Transaction";
            const narrativeHeadline = String(timelineSummaryNarrativeHeader(row, workstreamNarratives) || "").trim();
            const titleText = narrativeHeadline || summary;
            const inlineNarrative = renderTimelineTransactionNarrative(row, linkContext, workstreamNarratives);
            const eventsList = Array.isArray(row.events) ? row.events : [];
            const filesList = Array.isArray(row.files) ? row.files : [];
            const eventsMeta = `${Number(row.event_count || eventsList.length || 0)} events • ${Number(row.files_count || filesList.length || 0)} files`;
            const meta = `${timeLabel} • ${eventsMeta}${sessionId ? ` • session ${sessionId}` : ""}`;
            const fileSplit = splitNarrativeFiles(filesList);
            const sourceFiles = fileSplit.source;
            const generatedFiles = fileSplit.generated;
            const generatedStandaloneRadarFiles = generatedFiles.filter((file) => normalizeRepoPath(file) === "odylith/radar/standalone-pages.v1.js");
            const generatedOtherFiles = generatedFiles.filter((file) => normalizeRepoPath(file) !== "odylith/radar/standalone-pages.v1.js");
            const shownSourceFiles = sourceFiles.slice(0, 24);
            const shownGeneratedOther = generatedOtherFiles.slice(0, 6);
            const fileRows = [
              ...shownSourceFiles.map((item) => `<li>${escapeHtml(item)}</li>`),
              ...shownGeneratedOther.map((item) => `<li>${escapeHtml(item)} <span class="ws-cell-muted">(generated)</span></li>`),
            ];
            if (generatedStandaloneRadarFiles.length > 0) {
              fileRows.push(`<li>${escapeHtml(`${generatedStandaloneRadarFiles.length} generated Radar standalone route bundle${generatedStandaloneRadarFiles.length === 1 ? "" : "s"} (compacted)`)}</li>`);
            }
            if (sourceFiles.length > shownSourceFiles.length) {
              fileRows.push(`<li>${escapeHtml(`+${sourceFiles.length - shownSourceFiles.length} more source files`)}</li>`);
            }
            if (generatedOtherFiles.length > shownGeneratedOther.length) {
              fileRows.push(`<li>${escapeHtml(`+${generatedOtherFiles.length - shownGeneratedOther.length} more generated artifacts`)}</li>`);
            }
            const fileHtml = fileRows.length
              ? `<div><h3>Files</h3><ul class="tx-files">${fileRows.join("")}</ul></div>`
              : `<div><h3>Files</h3><p class="empty">No files captured for this transaction.</p></div>`;

            const compactedGeneratedEvents = eventsList.filter((eventRow) => isGeneratedOnlyLocalEvent(eventRow)).length;
            const visibleEvents = eventsList.filter((eventRow) => !isGeneratedOnlyLocalEvent(eventRow));
            const shownEvents = visibleEvents.slice(0, 24);
            const hiddenVisibleEvents = Math.max(0, visibleEvents.length - shownEvents.length);
            const eventCompactionRows = [];
            if (compactedGeneratedEvents > 0) {
              eventCompactionRows.push(`<div class="tx-meta">Compacted ${compactedGeneratedEvents} generated events.</div>`);
            }
            if (hiddenVisibleEvents > 0) {
              eventCompactionRows.push(`<div class="tx-meta">Showing ${shownEvents.length} of ${visibleEvents.length} non-generated events.</div>`);
            }
            const eventRowsHtml = shownEvents.length
              ? `<div class="tx-events">${shownEvents.map((eventRow) => renderTimelineEventCard(eventRow)).join("")}</div>`
              : `<p class="empty">No high-signal event details captured.</p>`;
            return `
              <details class="tx-card">
                <summary>
                  <div class="tx-headline">${escapeHtml(titleText)}</div>
                  ${!narrativeHeadline && contextText ? `<div class="tx-context">${escapeHtml(contextText)}</div>` : ""}
                  ${chips}
                  <div class="tx-meta">${escapeHtml(meta)}${transactionId ? ` • ${escapeHtml(transactionId)}` : ""}</div>
                </summary>
                <div class="tx-detail">
                  ${inlineNarrative}
                  ${fileHtml}
                  <div>
                    <h3>Events</h3>
                    ${eventCompactionRows.join("")}
                    ${eventRowsHtml}
                  </div>
                </div>
              </details>
            `;
          }).join("");

          hourRows.push(`
            <div class="hour-row">
              <div class="hour-label">${escapeHtml(hourLabel)}</div>
              <div class="hour-events">${eventHtml}</div>
            </div>
          `);
        }

        rows.push(`
          <section class="timeline-day">
            <div class="timeline-day-title">${escapeHtml(formatTimelineDayHeader(dayToken))}</div>
            ${hourRows.join("")}
          </section>
        `);
      }

      if (!rows.length) {
        target.innerHTML = '<div class="empty">No audit events in this scope and window.</div>';
        return;
      }
      target.innerHTML = rows.join("");
    }
