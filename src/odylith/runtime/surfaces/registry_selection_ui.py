"""Own Registry selection loading and absent-versus-filtered presentation."""


def runtime_js() -> str:
    return """
    function createRegistrySelection({ detail, timeline, timelineCount, sourceCount, loadDetail, renderDetail, renderTimeline, onOutcome }) {
      let revision = 0;
      return async function selectComponent(selectedId, filtered) {
        const currentRevision = ++revision;
        const expectedId = String(selectedId || "").trim().toLowerCase();
        const summary = filtered.find(row => String(row.component_id || "").trim().toLowerCase() === expectedId);
        detail.dataset.selectedComponent = summary ? expectedId : "";
        if (!summary) {
          renderTimeline(null);
          detail.innerHTML = sourceCount === 0
            ? `<section class="empty" role="status"><h2>No components yet</h2><p>Registry will show the components defined for this project.</p><p><a href="../index.html?tab=project" target="_top">Open Project</a> to start from your project intent.</p></section>`
            : `<section class="empty" role="status"><h2>No matching components</h2><p>Change your search or reset the filters to see components already in Registry.</p></section>`;
          onOutcome({ id: "", outcome: "empty" });
          return;
        }
        detail.innerHTML = "";
        timelineCount.textContent = "";
        timeline.innerHTML = "";
        onOutcome({ id: "", outcome: "loading" });
        let loaded;
        try { loaded = await loadDetail(selectedId); } catch (_error) { loaded = null; }
        if (currentRevision !== revision) return;
        const complete = loaded && typeof loaded === "object";
        const selected = complete ? { ...summary, ...loaded } : summary;
        renderDetail(selected);
        renderTimeline(selected);
        if (!complete) detail.innerHTML += '<p role="status">Component detail unavailable. The available summary is shown.</p>';
        onOutcome({ id: expectedId, outcome: complete ? "ready" : "degraded" });
      };
    }
    """.strip()
