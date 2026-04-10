    function normalizeCompassSourceTruthPayload(sourcePayload) {
      const payload = sourcePayload && typeof sourcePayload === "object" ? sourcePayload : {};
      const exactReleaseSummary = payload.release_summary && typeof payload.release_summary === "object"
        ? payload.release_summary
        : null;
      const exactCurrentWorkstreams = Array.isArray(payload.current_workstreams)
        ? payload.current_workstreams.filter((row) => row && typeof row === "object")
        : null;
      const exactWorkstreamCatalog = Array.isArray(payload.workstream_catalog)
        ? payload.workstream_catalog.filter((row) => row && typeof row === "object")
        : null;
      if (exactCurrentWorkstreams !== null || exactWorkstreamCatalog !== null) {
        return {
          kind: "source_truth",
          generated_utc: String(payload.generated_utc || "").trim(),
          release_summary: {
            catalog: Array.isArray(exactReleaseSummary && exactReleaseSummary.catalog)
              ? exactReleaseSummary.catalog.filter((row) => row && typeof row === "object")
              : [],
            current_release: exactReleaseSummary && typeof exactReleaseSummary.current_release === "object"
              ? exactReleaseSummary.current_release
              : {},
            next_release: exactReleaseSummary && typeof exactReleaseSummary.next_release === "object"
              ? exactReleaseSummary.next_release
              : {},
            summary: exactReleaseSummary && typeof exactReleaseSummary.summary === "object"
              ? exactReleaseSummary.summary
              : {},
          },
          current_workstreams: exactCurrentWorkstreams || [],
          workstream_catalog: exactWorkstreamCatalog || [],
          verified_scoped_workstreams: payload.verified_scoped_workstreams && typeof payload.verified_scoped_workstreams === "object"
            ? payload.verified_scoped_workstreams
            : {},
          promoted_scoped_workstreams: payload.promoted_scoped_workstreams && typeof payload.promoted_scoped_workstreams === "object"
            ? payload.promoted_scoped_workstreams
            : {},
          window_scope_signals: payload.window_scope_signals && typeof payload.window_scope_signals === "object"
            ? payload.window_scope_signals
            : {},
          workstreams: [],
        };
      }
      return {
        kind: "traceability_graph",
        generated_utc: String(payload.generated_utc || "").trim(),
        release_summary: {
          catalog: Array.isArray(payload.releases) ? payload.releases.filter((row) => row && typeof row === "object") : [],
          current_release: payload.current_release && typeof payload.current_release === "object" ? payload.current_release : {},
          next_release: payload.next_release && typeof payload.next_release === "object" ? payload.next_release : {},
          summary: payload.release_summary && typeof payload.release_summary === "object" ? payload.release_summary : {},
        },
        current_workstreams: [],
        workstream_catalog: [],
        verified_scoped_workstreams: {},
        promoted_scoped_workstreams: {},
        window_scope_signals: {},
        workstreams: Array.isArray(payload.workstreams) ? payload.workstreams.filter((row) => row && typeof row === "object") : [],
        execution_programs: Array.isArray(payload.execution_programs) ? payload.execution_programs.filter((row) => row && typeof row === "object") : [],
      };
    }

    function sourceTruthWorkstreamLookup(sourceTruth) {
      const payload = sourceTruth && typeof sourceTruth === "object" ? sourceTruth : {};
      const rows = [
        ...(Array.isArray(payload.workstream_catalog) ? payload.workstream_catalog : []),
        ...(Array.isArray(payload.current_workstreams) ? payload.current_workstreams : []),
        ...(Array.isArray(payload.workstreams) ? payload.workstreams : []),
      ];
      const lookup = new Map();
      rows.forEach((row) => {
        const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
        if (!WORKSTREAM_RE.test(ideaId)) return;
        lookup.set(ideaId, row);
      });
      return lookup;
    }

    function normalizedWorkstreamIdList(items) {
      if (!Array.isArray(items)) return [];
      return Array.from(
        new Set(
          items
            .map((item) => String(item || "").trim())
            .filter((token) => WORKSTREAM_RE.test(token))
        )
      ).sort((left, right) => left.localeCompare(right));
    }

    function runtimeCurrentWorkstreamIds(payload) {
      const rows = Array.isArray(payload && payload.current_workstreams) ? payload.current_workstreams : [];
      return normalizedWorkstreamIdList(rows.map((row) => String(row && row.idea_id ? row.idea_id : "").trim()));
    }

    function sourceTruthCurrentWorkstreamIds(sourceTruth) {
      const payload = sourceTruth && typeof sourceTruth === "object" ? sourceTruth : {};
      const exactRows = Array.isArray(payload.current_workstreams) ? payload.current_workstreams : [];
      if (exactRows.length) {
        return normalizedWorkstreamIdList(exactRows.map((row) => String(row && row.idea_id ? row.idea_id : "").trim()));
      }
      const currentRelease = payload.release_summary && typeof payload.release_summary.current_release === "object"
        ? payload.release_summary.current_release
        : {};
      const activeReleaseIds = normalizedWorkstreamIdList(currentRelease.active_workstreams);
      const activeWaveIds = [];
      const seen = new Set();
      const pushId = (value) => {
        const token = String(value || "").trim();
        if (!WORKSTREAM_RE.test(token) || seen.has(token)) return;
        seen.add(token);
        activeWaveIds.push(token);
      };
      (Array.isArray(payload.execution_programs) ? payload.execution_programs : []).forEach((program) => {
        const activeWaves = Array.isArray(program && program.active_waves) ? program.active_waves : [];
        activeWaves.forEach((wave) => {
          pushId(program && program.umbrella_id);
          ["primary_workstreams", "carried_workstreams", "in_band_workstreams", "all_workstreams"].forEach((field) => {
            const items = Array.isArray(wave && wave[field]) ? wave[field] : [];
            items.forEach((item) => {
              if (item && typeof item === "object") {
                pushId(item.idea_id);
              } else {
                pushId(item);
              }
            });
          });
        });
      });
      const prioritized = normalizedWorkstreamIdList([...activeReleaseIds, ...activeWaveIds]);
      if (prioritized.length) {
        return prioritized;
      }
      const rows = Array.isArray(payload.workstreams) ? payload.workstreams : [];
      return normalizedWorkstreamIdList(
        rows
          .filter((row) => {
            const status = String(row && row.status ? row.status : "").trim().toLowerCase();
            return status === "planning" || status === "implementation";
          })
          .map((row) => String(row && row.idea_id ? row.idea_id : "").trim())
      );
    }

    function identicalWorkstreamLists(left, right) {
      const leftIds = normalizedWorkstreamIdList(left);
      const rightIds = normalizedWorkstreamIdList(right);
      if (leftIds.length !== rightIds.length) return false;
      for (let index = 0; index < leftIds.length; index += 1) {
        if (leftIds[index] !== rightIds[index]) return false;
      }
      return true;
    }

    function formatWorkstreamList(items) {
      const ids = normalizedWorkstreamIdList(items);
      return ids.length ? ids.join(", ") : "none";
    }

    function _parseUtcMillis(value) {
      const token = String(value || "").trim();
      if (!token) return null;
      const millis = Date.parse(token);
      return Number.isFinite(millis) ? millis : null;
    }

    function sourceTruthPayloadIsUsable(sourceTruth) {
      const payload = sourceTruth && typeof sourceTruth === "object" ? sourceTruth : {};
      if (payload.kind === "source_truth") {
        return Array.isArray(payload.current_workstreams) || Array.isArray(payload.workstream_catalog);
      }
      const releaseSummary = payload.release_summary && typeof payload.release_summary === "object"
        ? payload.release_summary
        : {};
      const currentRelease = releaseSummary.current_release && typeof releaseSummary.current_release === "object"
        ? releaseSummary.current_release
        : {};
      return Boolean(
        (Array.isArray(payload.workstreams) && payload.workstreams.length)
        || (Array.isArray(payload.execution_programs) && payload.execution_programs.length)
        || (Array.isArray(releaseSummary.catalog) && releaseSummary.catalog.length)
        || String(currentRelease.release_id || "").trim()
      );
    }

    function buildCompassRuntimeTruthDrift(payload, sourceTruth) {
      const normalizedSourceTruth = normalizeCompassSourceTruthPayload(sourceTruth);
      const sourceReleaseSummary = normalizedSourceTruth.release_summary;
      const runtimeReleaseSummary = payload && payload.release_summary && typeof payload.release_summary === "object"
        ? payload.release_summary
        : {};
      const sourceCurrentRelease = sourceReleaseSummary.current_release && typeof sourceReleaseSummary.current_release === "object"
        ? sourceReleaseSummary.current_release
        : {};
      const runtimeCurrentRelease = runtimeReleaseSummary.current_release && typeof runtimeReleaseSummary.current_release === "object"
        ? runtimeReleaseSummary.current_release
        : {};
      const sourceActiveMembers = normalizedWorkstreamIdList(sourceCurrentRelease.active_workstreams);
      const runtimeActiveMembers = normalizedWorkstreamIdList(runtimeCurrentRelease.active_workstreams);
      const sourceCompletedMembers = normalizedWorkstreamIdList(sourceCurrentRelease.completed_workstreams);
      const runtimeCompletedMembers = normalizedWorkstreamIdList(runtimeCurrentRelease.completed_workstreams);
      const sourceCurrentWorkstreams = sourceTruthCurrentWorkstreamIds(normalizedSourceTruth);
      const runtimeCurrentWorkstreams = runtimeCurrentWorkstreamIds(payload);
      const reasonCodes = [];
      if (String(sourceCurrentRelease.release_id || "").trim() !== String(runtimeCurrentRelease.release_id || "").trim()) {
        reasonCodes.push("current_release_id");
      }
      if (!identicalWorkstreamLists(sourceActiveMembers, runtimeActiveMembers)) {
        reasonCodes.push("active_release_membership");
      }
      if (!identicalWorkstreamLists(sourceCompletedMembers, runtimeCompletedMembers)) {
        reasonCodes.push("completed_release_membership");
      }
      if (!identicalWorkstreamLists(sourceCurrentWorkstreams, runtimeCurrentWorkstreams)) {
        reasonCodes.push("current_workstreams");
      }
      if (!reasonCodes.length) {
        return { has_drift: false, warning: "" };
      }
      const releaseLabel = String(
        sourceCurrentRelease.display_label
        || sourceCurrentRelease.effective_name
        || sourceCurrentRelease.version
        || sourceCurrentRelease.release_id
        || runtimeCurrentRelease.display_label
        || runtimeCurrentRelease.effective_name
        || runtimeCurrentRelease.version
        || runtimeCurrentRelease.release_id
        || "the current release"
      ).trim();
      const warningParts = [];
      const sourceLabel = normalizedSourceTruth.kind === "source_truth" ? "the governed source-truth snapshot" : "the traceability-graph fallback";
      if (reasonCodes.includes("current_release_id") || reasonCodes.includes("active_release_membership") || reasonCodes.includes("completed_release_membership")) {
        warningParts.push(
          `Release truth for ${releaseLabel} now targets ${formatWorkstreamList(sourceActiveMembers)} and completes ${formatWorkstreamList(sourceCompletedMembers)}, while the visible Compass snapshot targets ${formatWorkstreamList(runtimeActiveMembers)} and completes ${formatWorkstreamList(runtimeCompletedMembers)}.`
        );
      }
      if (reasonCodes.includes("current_workstreams")) {
        warningParts.push(
          `Source truth current workstreams are ${formatWorkstreamList(sourceCurrentWorkstreams)}, while the visible snapshot lists ${formatWorkstreamList(runtimeCurrentWorkstreams)}.`
        );
      }
      warningParts.push(`Compass reconciled this view from ${sourceLabel}. Run \`odylith compass refresh --repo-root .\` to refresh the full runtime snapshot.`);
      return {
        has_drift: true,
        kind: normalizedSourceTruth.kind,
        generated_utc: normalizedSourceTruth.generated_utc,
        reason_codes: reasonCodes,
        source_active_members: sourceActiveMembers,
        source_completed_members: sourceCompletedMembers,
        source_current_workstreams: sourceCurrentWorkstreams,
        source_current_workstream_rows: Array.isArray(normalizedSourceTruth.current_workstreams) ? normalizedSourceTruth.current_workstreams.slice() : [],
        source_workstream_catalog: Array.isArray(normalizedSourceTruth.workstream_catalog) ? normalizedSourceTruth.workstream_catalog.slice() : [],
        warning: warningParts.join(" "),
      };
    }

    function minimalCompassWorkstreamRowFromSource(sourceRow) {
      const row = sourceRow && typeof sourceRow === "object" ? sourceRow : {};
      const status = String(row.status || "").trim().toLowerCase();
      const progressRatio = status === "finished" ? 1 : null;
      return {
        idea_id: String(row.idea_id || "").trim(),
        title: String(row.title || row.idea_id || "").trim(),
        status,
        release: row.release && typeof row.release === "object"
          ? { ...row.release }
          : (row.active_release && typeof row.active_release === "object" ? { ...row.active_release } : {}),
        release_history_summary: String(row.release_history_summary || "").trim(),
        plan: progressRatio === null ? {} : { progress_ratio: progressRatio, display_progress_ratio: progressRatio, display_progress_label: "100% progress" },
        activity: {},
        links: {},
        why: {},
        registry_components: Array.isArray(row.registry_components) ? row.registry_components.slice() : [],
        execution_wave_programs: Array.isArray(row.execution_wave_programs) ? row.execution_wave_programs.slice() : [],
        claim_guard: row.claim_guard && typeof row.claim_guard === "object" ? { ...row.claim_guard } : {},
        proof_state: row.proof_state && typeof row.proof_state === "object" ? { ...row.proof_state } : {},
        proof_state_resolution: row.proof_state_resolution && typeof row.proof_state_resolution === "object" ? { ...row.proof_state_resolution } : {},
        proof_summary_lines: Array.isArray(row.proof_summary_lines) ? row.proof_summary_lines.slice() : [],
        proof_refs: row.proof_refs && typeof row.proof_refs === "object" ? { ...row.proof_refs } : {},
      };
    }

    function mergeCompassWorkstreamRowFromSource(existingRow, sourceRow) {
      const source = sourceRow && typeof sourceRow === "object" ? sourceRow : {};
      const base = existingRow && typeof existingRow === "object"
        ? { ...existingRow }
        : minimalCompassWorkstreamRowFromSource(source);
      const status = String(source.status || base.status || "").trim().toLowerCase();
      const plan = base.plan && typeof base.plan === "object" ? { ...base.plan } : {};
      if (status === "finished") {
        plan.progress_ratio = 1;
        plan.display_progress_ratio = 1;
        plan.display_progress_label = "100% progress";
      }
      return {
        ...base,
        ...source,
        idea_id: String(source.idea_id || base.idea_id || "").trim(),
        title: String(source.title || base.title || source.idea_id || base.idea_id || "").trim(),
        status,
        release: source.release && typeof source.release === "object"
          ? { ...source.release }
          : (source.active_release && typeof source.active_release === "object"
            ? { ...source.active_release }
            : (base.release && typeof base.release === "object" ? { ...base.release } : {})),
        release_history_summary: String(source.release_history_summary || base.release_history_summary || "").trim(),
        execution_wave_programs: Array.isArray(source.execution_wave_programs)
          ? source.execution_wave_programs.slice()
          : (Array.isArray(base.execution_wave_programs) ? base.execution_wave_programs.slice() : []),
        plan,
      };
    }

    function applyCompassRuntimeTruthPatch(payload, sourceTruthPayload, drift) {
      const normalizedSourceTruth = normalizeCompassSourceTruthPayload(sourceTruthPayload);
      const sourceReleaseSummary = normalizedSourceTruth.release_summary;
      const sourceRows = sourceTruthWorkstreamLookup(normalizedSourceTruth);
      const runtimeRows = Array.isArray(payload && payload.current_workstreams) ? payload.current_workstreams : [];
      const catalogRows = Array.isArray(payload && payload.workstream_catalog) ? payload.workstream_catalog : [];
      const existingRows = new Map();
      [...catalogRows, ...runtimeRows].forEach((row) => {
        const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
        if (!WORKSTREAM_RE.test(ideaId) || existingRows.has(ideaId)) return;
        existingRows.set(ideaId, row);
      });
      const exactCurrentRows = Array.isArray(drift.source_current_workstream_rows) ? drift.source_current_workstream_rows : [];
      const exactCatalogRows = Array.isArray(drift.source_workstream_catalog) ? drift.source_workstream_catalog : [];
      const currentWorkstreamRows = exactCurrentRows.length
        ? exactCurrentRows.map((row) => mergeCompassWorkstreamRowFromSource(existingRows.get(String(row.idea_id || "").trim()), row))
        : drift.source_current_workstreams
          .map((ideaId) => {
            const sourceRow = sourceRows.get(ideaId);
            if (sourceRow) return mergeCompassWorkstreamRowFromSource(existingRows.get(ideaId), sourceRow);
            return existingRows.get(ideaId) || null;
          })
          .filter(Boolean);
      const workstreamCatalog = exactCatalogRows.length
        ? exactCatalogRows.map((row) => mergeCompassWorkstreamRowFromSource(existingRows.get(String(row.idea_id || "").trim()), row))
        : Array.from(
            new Set([
              ...drift.source_current_workstreams,
              ...drift.source_active_members,
              ...drift.source_completed_members,
              ...runtimeCurrentWorkstreamIds(payload),
            ])
          )
            .map((ideaId) => {
              const sourceRow = sourceRows.get(ideaId);
              if (sourceRow) return mergeCompassWorkstreamRowFromSource(existingRows.get(ideaId), sourceRow);
              return existingRows.get(ideaId) || null;
            })
            .filter(Boolean);

      return {
        ...payload,
        release_summary: sourceReleaseSummary,
        current_workstreams: currentWorkstreamRows,
        workstream_catalog: workstreamCatalog,
        verified_scoped_workstreams: normalizedSourceTruth.kind === "source_truth"
          ? (normalizedSourceTruth.verified_scoped_workstreams && typeof normalizedSourceTruth.verified_scoped_workstreams === "object"
            ? { ...normalizedSourceTruth.verified_scoped_workstreams }
            : {})
          : { "24h": [], "48h": [] },
        promoted_scoped_workstreams: normalizedSourceTruth.kind === "source_truth"
          ? (normalizedSourceTruth.promoted_scoped_workstreams && typeof normalizedSourceTruth.promoted_scoped_workstreams === "object"
            ? { ...normalizedSourceTruth.promoted_scoped_workstreams }
            : {})
          : { "24h": [], "48h": [] },
        window_scope_signals: normalizedSourceTruth.kind === "source_truth"
          ? (normalizedSourceTruth.window_scope_signals && typeof normalizedSourceTruth.window_scope_signals === "object"
            ? { ...normalizedSourceTruth.window_scope_signals }
            : {})
          : { "24h": {}, "48h": {} },
        runtime_truth_guard: {
          source: normalizedSourceTruth.kind,
          source_generated_utc: normalizedSourceTruth.generated_utc,
          reason_codes: Array.isArray(drift.reason_codes) ? drift.reason_codes.slice() : [],
          reconciled: true,
        },
      };
    }

    async function reconcileRuntimePayloadWithSourceTruth(payload) {
      if (!payload || typeof payload !== "object") return { payload, warning: "" };
      if (String(window.location.protocol || "").toLowerCase() === "file:") {
        return { payload, warning: "" };
      }
      const sourceTruthHref = String(compassShell().source_truth_href || "").trim();
      const traceabilityHref = String(compassShell().traceability_graph_href || "").trim();
      const hrefs = Array.from(new Set([sourceTruthHref, traceabilityHref].filter(Boolean)));
      if (!hrefs.length) return { payload, warning: "" };
      try {
        for (const href of hrefs) {
          const response = await fetch(href, { cache: "no-store" });
          if (!response.ok) continue;
          const sourceTruthPayload = await response.json();
          if (!sourceTruthPayload || typeof sourceTruthPayload !== "object") continue;
          const normalizedSourceTruth = normalizeCompassSourceTruthPayload(sourceTruthPayload);
          if (!sourceTruthPayloadIsUsable(normalizedSourceTruth)) continue;
          const sourceMillis = _parseUtcMillis(normalizedSourceTruth.generated_utc);
          const runtimeMillis = _parseUtcMillis(payload.generated_utc);
          if (sourceMillis !== null && runtimeMillis !== null && sourceMillis < runtimeMillis) {
            continue;
          }
          const drift = buildCompassRuntimeTruthDrift(payload, sourceTruthPayload);
          if (!drift.has_drift) return { payload, warning: "" };
          return {
            payload: applyCompassRuntimeTruthPatch(payload, sourceTruthPayload, drift),
            warning: drift.warning,
          };
        }
        return { payload, warning: "" };
      } catch (_error) {
        return { payload, warning: "" };
      }
    }
