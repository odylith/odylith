"""Own Radar selection loading, cancellation and useful empty-state recovery."""


def runtime_js() -> str:
    return """
    function createBacklogSelection({ detail, empty, sourceCount, loadDetail, renderDetail, onOutcome }) {
      let revision = 0;
      empty.setAttribute("role", "status");
      return async function selectWorkstream(selectedId, filtered) {
        const currentRevision = ++revision;
        const summary = filtered.find(row => row.idea_id === selectedId);
        detail.innerHTML = "";
        detail.hidden = !summary;
        empty.hidden = Boolean(summary);
        if (!summary) {
          empty.innerHTML = sourceCount === 0
            ? `<h2>No workstreams yet</h2><p>Radar will show the work planned for this project.</p><p><a href="../index.html?tab=project" target="_top">Open Project</a> to start from your project intent.</p>`
            : `<h2>No matching workstreams</h2><p>Change your search or filters to see workstreams already in Radar.</p>`;
          onOutcome({ id: "", outcome: "empty" });
          return;
        }
        onOutcome({ id: "", outcome: "loading" });
        let loaded;
        try { loaded = await loadDetail(summary.idea_id); } catch (_error) { loaded = null; }
        if (currentRevision !== revision) return;
        const complete = loaded && typeof loaded === "object";
        renderDetail(complete ? { ...summary, ...loaded } : summary);
        if (!complete) detail.innerHTML += '<p role="status">Workstream detail unavailable. The available summary is shown.</p>';
        onOutcome({ id: summary.idea_id, outcome: complete ? "ready" : "degraded" });
      };
    }
    """.strip()
