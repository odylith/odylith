"""Own Registry selection loading and absent-versus-filtered presentation."""


def runtime_js() -> str:
    return """
    function createRegistrySelection({ detail, timeline, timelineCount, sourceCount, loadDetail, renderDetail, renderTimeline }) {
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
          return;
        }
        detail.innerHTML = "";
        timelineCount.textContent = "";
        timeline.innerHTML = "";
        const loaded = await loadDetail(selectedId);
        if (currentRevision !== revision) return;
        const selected = loaded && typeof loaded === "object" ? { ...summary, ...loaded } : summary;
        renderDetail(selected);
        renderTimeline(selected);
      };
    }
    """.strip()
