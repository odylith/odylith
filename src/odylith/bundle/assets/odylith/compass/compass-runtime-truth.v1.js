    function normalizeTraceabilityReleaseSummary(traceabilityPayload) {
      const payload = traceabilityPayload && typeof traceabilityPayload === "object" ? traceabilityPayload : {};
      return {
        catalog: Array.isArray(payload.releases) ? payload.releases.filter((row) => row && typeof row === "object") : [],
        current_release: payload.current_release && typeof payload.current_release === "object" ? payload.current_release : {},
        next_release: payload.next_release && typeof payload.next_release === "object" ? payload.next_release : {},
        summary: payload.release_summary && typeof payload.release_summary === "object" ? payload.release_summary : {},
      };
    }

    function traceabilityWorkstreamLookup(traceabilityPayload) {
      const rows = Array.isArray(traceabilityPayload && traceabilityPayload.workstreams)
        ? traceabilityPayload.workstreams
        : [];
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

    function traceabilityCurrentWorkstreamIds(traceabilityPayload) {
      const rows = Array.isArray(traceabilityPayload && traceabilityPayload.workstreams)
        ? traceabilityPayload.workstreams
        : [];
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

    function buildCompassRuntimeTruthDrift(payload, traceabilityPayload) {
      const sourceReleaseSummary = normalizeTraceabilityReleaseSummary(traceabilityPayload);
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
      const sourceCurrentWorkstreams = traceabilityCurrentWorkstreamIds(traceabilityPayload);
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
      warningParts.push("Compass reconciled this view from the live traceability graph. Run `odylith compass refresh --repo-root .` to refresh the full runtime snapshot.");
      return {
        has_drift: true,
        reason_codes: reasonCodes,
        source_active_members: sourceActiveMembers,
        source_completed_members: sourceCompletedMembers,
        source_current_workstreams: sourceCurrentWorkstreams,
        warning: warningParts.join(" "),
      };
    }

    function minimalCompassWorkstreamRowFromTraceability(traceRow) {
      const row = traceRow && typeof traceRow === "object" ? traceRow : {};
      const status = String(row.status || "").trim().toLowerCase();
      const progressRatio = status === "finished" ? 1 : null;
      return {
        idea_id: String(row.idea_id || "").trim(),
        title: String(row.title || row.idea_id || "").trim(),
        status,
        release: row.active_release && typeof row.active_release === "object" ? { ...row.active_release } : {},
        release_history_summary: String(row.release_history_summary || "").trim(),
        plan: progressRatio === null ? {} : { progress_ratio: progressRatio, display_progress_ratio: progressRatio, display_progress_label: "100% progress" },
        activity: {},
        links: {},
        why: {},
        registry_components: [],
        execution_wave_programs: [],
        claim_guard: {},
        proof_state: {},
        proof_state_resolution: {},
        proof_summary_lines: [],
        proof_refs: {},
      };
    }

    function mergeCompassWorkstreamRowFromTraceability(existingRow, traceRow) {
      const traceSource = traceRow && typeof traceRow === "object" ? traceRow : {};
      const base = existingRow && typeof existingRow === "object"
        ? { ...existingRow }
        : minimalCompassWorkstreamRowFromTraceability(traceSource);
      const status = String(traceSource.status || base.status || "").trim().toLowerCase();
      const plan = base.plan && typeof base.plan === "object" ? { ...base.plan } : {};
      if (status === "finished") {
        plan.progress_ratio = 1;
        plan.display_progress_ratio = 1;
        plan.display_progress_label = "100% progress";
      }
      return {
        ...base,
        idea_id: String(traceSource.idea_id || base.idea_id || "").trim(),
        title: String(traceSource.title || base.title || traceSource.idea_id || base.idea_id || "").trim(),
        status,
        release: traceSource.active_release && typeof traceSource.active_release === "object"
          ? { ...traceSource.active_release }
          : (base.release && typeof base.release === "object" ? { ...base.release } : {}),
        release_history_summary: String(traceSource.release_history_summary || base.release_history_summary || "").trim(),
        plan,
      };
    }

    function applyCompassRuntimeTruthPatch(payload, traceabilityPayload, drift) {
      const sourceReleaseSummary = normalizeTraceabilityReleaseSummary(traceabilityPayload);
      const traceabilityRows = traceabilityWorkstreamLookup(traceabilityPayload);
      const runtimeRows = Array.isArray(payload && payload.current_workstreams) ? payload.current_workstreams : [];
      const catalogRows = Array.isArray(payload && payload.workstream_catalog) ? payload.workstream_catalog : [];
      const existingRows = new Map();
      [...catalogRows, ...runtimeRows].forEach((row) => {
        const ideaId = String(row && row.idea_id ? row.idea_id : "").trim();
        if (!WORKSTREAM_RE.test(ideaId) || existingRows.has(ideaId)) return;
        existingRows.set(ideaId, row);
      });

      const currentWorkstreamRows = drift.source_current_workstreams
        .map((ideaId) => {
          const traceRow = traceabilityRows.get(ideaId);
          if (traceRow) return mergeCompassWorkstreamRowFromTraceability(existingRows.get(ideaId), traceRow);
          return existingRows.get(ideaId) || null;
        })
        .filter(Boolean);

      const catalogIds = Array.from(
        new Set([
          ...drift.source_current_workstreams,
          ...drift.source_active_members,
          ...drift.source_completed_members,
          ...runtimeCurrentWorkstreamIds(payload),
        ])
      );
      const workstreamCatalog = catalogIds
        .map((ideaId) => {
          const traceRow = traceabilityRows.get(ideaId);
          if (traceRow) return mergeCompassWorkstreamRowFromTraceability(existingRows.get(ideaId), traceRow);
          return existingRows.get(ideaId) || null;
        })
        .filter(Boolean);

      return {
        ...payload,
        release_summary: sourceReleaseSummary,
        current_workstreams: currentWorkstreamRows,
        workstream_catalog: workstreamCatalog,
        runtime_truth_guard: {
          source: "traceability_graph",
          traceability_generated_utc: String(traceabilityPayload && traceabilityPayload.generated_utc ? traceabilityPayload.generated_utc : "").trim(),
          reason_codes: Array.isArray(drift.reason_codes) ? drift.reason_codes.slice() : [],
          reconciled: true,
        },
      };
    }

    async function reconcileRuntimePayloadWithSourceTruth(payload) {
      if (!payload || typeof payload !== "object") return { payload, warning: "" };
      const href = String(compassShell().traceability_graph_href || "").trim();
      if (!href) return { payload, warning: "" };
      if (String(window.location.protocol || "").toLowerCase() === "file:") {
        return { payload, warning: "" };
      }
      try {
        const response = await fetch(href, { cache: "no-store" });
        if (!response.ok) return { payload, warning: "" };
        const traceabilityPayload = await response.json();
        if (!traceabilityPayload || typeof traceabilityPayload !== "object") return { payload, warning: "" };
        const drift = buildCompassRuntimeTruthDrift(payload, traceabilityPayload);
        if (!drift.has_drift) return { payload, warning: "" };
        return {
          payload: applyCompassRuntimeTruthPatch(payload, traceabilityPayload, drift),
          warning: drift.warning,
        };
      } catch (_error) {
        return { payload, warning: "" };
      }
    }
