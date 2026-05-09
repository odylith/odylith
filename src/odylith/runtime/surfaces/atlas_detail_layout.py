"""Atlas detail-pane layout snippets used by the Mermaid catalog renderer."""

DETAIL_LAYOUT_CSS = r"""
    .details-grid {
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(0, 1fr);
      min-width: 0;
    }

    .section {
      min-width: 0;
      max-width: 100%;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.88);
      padding: 12px;
    }

    .section h3 {
    }

    .summary {
      margin: 0;
    }

    .read-guide {
      margin-top: 12px;
      border: 1px solid rgba(3, 105, 161, 0.14);
      border-radius: 12px;
      background: rgba(248, 252, 255, 0.92);
      padding: 10px 11px;
      min-width: 0;
    }

    .read-guide .artifact-label {
      margin-bottom: 5px;
    }

    .read-guide-body {
      margin: 0;
    }

    .component-list-label {
      margin-top: 13px;
      margin-bottom: 7px;
    }

    .component-list {
      margin-top: 0;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
      gap: 10px;
      min-width: 0;
      max-width: 100%;
    }

    .component-card {
      min-width: 0;
      max-width: 100%;
      border: 1px solid rgba(3, 105, 161, 0.17);
      border-radius: 10px;
      padding: 9px 10px;
      background: rgba(255, 255, 255, 0.95);
    }

    .component-card strong {
      display: block;
    }

    .component-token {
      display: block;
      margin: -1px 0 6px;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .component-card p {
      margin: 0;
    }
    __ODYLITH_ATLAS_READABLE_COPY__

    __ODYLITH_ATLAS_OPERATOR_READOUT_LAYOUT__
    __ODYLITH_ATLAS_OPERATOR_READOUT_LABEL__
    __ODYLITH_ATLAS_OPERATOR_READOUT_COPY__
    __ODYLITH_ATLAS_OPERATOR_READOUT_META__

    .artifact-group {
      margin-bottom: 10px;
    }

    .artifact-group:last-child {
      margin-bottom: 0;
    }

    .artifact-label {
      margin: 0 0 6px 0;
    }
    __ODYLITH_ATLAS_ARTIFACT_LABEL_TYPOGRAPHY__

    .engineering-context-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 10px;
      min-width: 0;
    }

    .linked-context-section .artifact-group {
      margin-bottom: 0;
      min-width: 0;
      border: 1px solid rgba(3, 105, 161, 0.14);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.94);
      padding: 10px 11px;
    }

    .artifact-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 0;
      max-width: 100%;
    }

    .linked-context-section .artifact-list {
      max-height: 210px;
      overflow: auto;
      padding-right: 2px;
    }

    .workstream-context-list {
      flex-direction: row;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }

    .atlas-context-disclosure {
      border: 1px solid rgba(3, 105, 161, 0.16);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.94);
      overflow: hidden;
    }

    .atlas-context-disclosure > summary {
      cursor: pointer;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.96);
    }

    .atlas-context-disclosure > summary::-webkit-details-marker {
      display: none;
    }

    .atlas-context-disclosure > summary::before {
      content: "\\25B8";
      color: #5d7389;
    }

    .atlas-context-disclosure[open] > summary::before {
      content: "\\25BE";
    }

    .atlas-context-disclosure[open] > summary {
      border-bottom: 1px solid rgba(3, 105, 161, 0.16);
    }

    .atlas-context-disclosure .artifact-list {
      padding: 10px;
    }

    .context-link-item {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }

    .context-tags {
      display: inline-flex;
      flex-wrap: wrap;
      gap: 5px;
    }

    .context-tag {
      display: inline-flex;
      align-items: center;
      --label-bg: rgba(255, 255, 255, 0.92);
      border: 0;
      background: var(--label-bg);
      color: #36566f;
      border-radius: 0;
      padding: 2px 7px;
    }

    .artifact-list a {
      text-decoration: none;
      border-bottom: 1px dotted rgba(13, 68, 104, 0.38);
      width: fit-content;
      max-width: 100%;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .artifact-list a:hover {
      color: #0a8a84;
      border-bottom-color: rgba(10, 138, 132, 0.62);
    }

    .artifact-list a.workstream-pill-link {
      border-bottom: 0;
      width: auto;
    }
    __ODYLITH_ATLAS_WORKSTREAM_PILL_TYPOGRAPHY__

    .artifact-list a.workstream-pill-link:hover {
      border-bottom: 0;
    }
"""

DETAIL_LAYOUT_HTML = r"""
      <section class="details-grid">
        <article class="section diagram-explanation-section">
          <h3>What This Diagram Shows</h3>
          <p id="diagramSummary" class="summary"></p>
          <div class="read-guide">
            <p class="artifact-label">How To Read This View</p>
            <p id="diagramReadGuide" class="read-guide-body"></p>
          </div>
          <p class="artifact-label component-list-label">Components In This Diagram</p>
          <div id="componentList" class="component-list"></div>
        </article>

        <article class="section linked-context-section">
          <h3>Linked Engineering Context</h3>
          <div class="engineering-context-grid">
            <div class="artifact-group">
              <p class="artifact-label">Backlog</p>
              <ul id="backlogLinks" class="artifact-list"></ul>
            </div>
            <div class="artifact-group">
              <p class="artifact-label">Plans</p>
              <ul id="planLinks" class="artifact-list"></ul>
            </div>
            <div class="artifact-group">
              <p class="artifact-label">Developer Docs</p>
              <ul id="docLinks" class="artifact-list"></ul>
            </div>
            <div class="artifact-group">
              <p class="artifact-label">Implementation Code</p>
              <ul id="codeLinks" class="artifact-list"></ul>
            </div>
            <div class="artifact-group">
              <p class="artifact-label">Registry Components</p>
              <ul id="registryLinks" class="artifact-list"></ul>
            </div>
            <div class="artifact-group">
              <p class="artifact-label">Operator Surfaces</p>
              <ul id="surfaceLinks" class="artifact-list"></ul>
            </div>
          </div>
        </article>
      </section>
"""

DETAIL_RUNTIME_HELPERS_JS = r"""
    function componentLookupKey(value) {
      return String(value || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    }

    function componentDisplayName(value) {
      const token = String(value || "").trim();
      if (!token) return "";
      const exact = String(componentTitleLookup[token] || "").trim();
      if (exact) return exact;
      const normalized = componentLookupKey(token);
      return String(componentTitleLookup[normalized] || "").trim() || token;
    }

    function diagramReadGuide(diagram) {
      const kind = String(diagram && diagram.kind ? diagram.kind : "").trim().toLowerCase();
      if (kind.includes("sequence")) {
        return "Read from top to bottom. Each lane is an actor or component; arrows are calls, handoffs, or proof events; notes and failure branches show where the workflow can block or recover.";
      }
      if (kind.includes("state")) {
        return "Read states as allowed product or system conditions. Arrows are the only allowed transitions; blocked or rejected states mark conditions that must not advance without proof.";
      }
      if (kind.includes("timeline")) {
        return "Read left to right as release or execution order. Each segment is a phase, wave, or proof checkpoint that should line up with the linked workstreams below.";
      }
      return "Read from named entrypoints through the arrows. Boxes are components, states, decisions, or proof obligations; grouped regions show ownership boundaries; dashed or labeled edges usually mark review, dependency, or blocked movement.";
    }
"""
