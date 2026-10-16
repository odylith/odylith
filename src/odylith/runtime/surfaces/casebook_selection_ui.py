"""Own Casebook async detail selection, cancellation, and rendered outcomes."""


def runtime_js() -> str:
    return """
    function createCasebookSelection({ detail, loadDetail, renderDetail, onOutcome }) {
      let detailRenderToken = 0;
      return async function selectBug(row, emptyHtml = "") {
        const renderToken = ++detailRenderToken;
        detail.innerHTML = "";
        if (!row) {
          detail.innerHTML = emptyHtml;
          onOutcome({ id: "", outcome: "empty" });
          return;
        }
        onOutcome({ id: "", outcome: "loading" });
        const id = String(row.bug_route || row.bug_key || "").trim();
        let loaded;
        try { loaded = id ? await loadDetail(id) : null; } catch (_error) { loaded = null; }
        if (renderToken !== detailRenderToken) return;
        const complete = loaded && typeof loaded === "object";
        renderDetail(complete ? { ...row, ...loaded } : row);
        if (!complete) detail.innerHTML += '<p role="status">Bug detail unavailable. The available summary is shown.</p>';
        onOutcome({ id, outcome: complete ? "ready" : "degraded" });
      };
    }
    """.strip()
