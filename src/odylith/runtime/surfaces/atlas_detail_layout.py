"""Atlas detail-pane layout snippets used by the Mermaid catalog renderer."""

DETAIL_LAYOUT_CSS = r"""
    .hero {
      display: grid;
      gap: 10px;
      min-width: 0;
    }

    __ODYLITH_ATLAS_DISPLAY_TITLE__

    .hero-copy {
      display: grid;
      gap: 10px;
      min-width: 0;
      width: 100%;
    }

    .diagram-facts {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 10px;
      min-width: 0;
    }

    .diagram-fact {
      display: grid;
      gap: 4px;
      align-content: start;
      min-width: 0;
      padding: 10px 12px;
      border: 1px solid rgba(148, 163, 184, 0.22);
      border-radius: 12px;
      background: linear-gradient(180deg, #ffffff, #f8fbff);
      box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
    }

    .diagram-fact.ok {
      border-color: rgba(2, 122, 72, 0.22);
      background: linear-gradient(180deg, #ffffff, #f3fbf6);
    }

    .diagram-fact.warn {
      border-color: rgba(181, 71, 8, 0.24);
      background: linear-gradient(180deg, #ffffff, #fff7ed);
    }

    .diagram-fact-label,
    .diagram-fact-value {
      min-width: 0;
    }

    .diagram-fact-value {
      overflow-wrap: anywhere;
    }

    __ODYLITH_ATLAS_FACT_TYPOGRAPHY__

    .meta-pill {
      --label-bg: rgba(255, 255, 255, 0.9);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 0;
      border-radius: 0;
      background: var(--label-bg);
      padding: 4px 8px;
      white-space: nowrap;
      color: #334155;
    }
    __ODYLITH_ATLAS_LABEL_TYPOGRAPHY__

    .meta-pill.ok {
      --label-bg: #027a48;
      color: white;
    }

    .meta-pill.warn {
      --label-bg: #b54708;
      color: white;
    }

    .source-links {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: flex-start;
    }

    .source-link {
      text-decoration: none;
      --chip-link-border: rgba(3, 105, 161, 0.25);
      --chip-link-bg: rgba(255, 255, 255, 0.9);
      --chip-link-text: #0d4366;
      --chip-link-border-hover: rgba(14, 165, 163, 0.6);
      --chip-link-bg-hover: rgba(240, 253, 250, 0.98);
      --chip-link-text-hover: #0b645f;
    }

    .alert {
      border-radius: 12px;
      border: 1px solid rgba(181, 71, 8, 0.36);
      background: rgba(255, 244, 234, 0.95);
      padding: 10px 12px;
      display: none;
    }

    .alert.visible {
      display: block;
    }

    .viewer-shell {
      border-radius: 16px;
      border: 1px solid var(--border);
      background: #ffffff;
      overflow: hidden;
      display: grid;
      grid-template-rows: auto auto minmax(560px, 1fr);
      min-height: 660px;
    }

    .viewer-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      padding: 9px 10px;
      border-bottom: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.92);
    }

    .viewer-toolbar-left {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }

    .viewer-toolbar-right {
      display: inline-flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .tool-btn {
      --chip-link-border: rgba(3, 105, 161, 0.24);
      --chip-link-bg: white;
      --chip-link-text: #144261;
      --chip-link-border-hover: rgba(14, 165, 163, 0.65);
      --chip-link-bg-hover: rgba(240, 253, 250, 0.98);
      --chip-link-text-hover: #0b645f;
    }

    .viewer-shell .tool-btn:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    .viewer-stage {
      position: relative;
      overflow: hidden;
      min-height: 560px;
      touch-action: none;
      cursor: grab;
      background: #ffffff;
    }

    .viewer-stage.dragging {
      cursor: grabbing;
    }

    .viewer-stage:focus {
      outline: 3px solid #0369a1;
      outline-offset: -3px;
    }

    .viewer-instructions {
      margin: 0;
      padding: 8px 10px;
      border-bottom: 1px solid var(--border);
    }

    .viewer-image {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) scale(1);
      transform-origin: 50% 50%;
      max-width: none;
      max-height: none;
      pointer-events: none;
      user-select: none;
    }

    .diagram-heading {
      display: flex;
      align-items: start;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }

    .diagram-heading .hero-title { flex: 1 1 220px; }
    .hero .summary:empty { display: none; }
    .diagram-metadata > summary { cursor: pointer; }
    .diagram-metadata[open] > summary { margin-bottom: 12px; }
    .diagram-metadata .source-links { margin: 12px 0; }

    .details-grid {
      display: grid;
      align-content: start;
      gap: 12px;
      grid-template-columns: minmax(0, 1fr);
      min-width: 0;
    }

    .section {
      min-width: 0;
      max-width: 100%;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.9);
      padding: 16px;
    }

    .section h3 {
      margin: 0 0 12px;
    }

    .summary {
      margin: 0;
      color: #34475d;
      font-size: 1rem;
      line-height: 1.45;
    }

    .diagram-explanation-section {
      display: grid;
      align-content: start;
      gap: 14px;
    }

    .diagram-guide-panel:has(> .read-guide-body:empty) { display: none; }

    .diagram-guide-panel {
      display: grid;
      align-content: start;
      border: 1px solid rgba(3, 105, 161, 0.14);
      border-radius: 10px;
      background: rgba(248, 252, 255, 0.92);
      padding: 11px 12px;
      min-width: 0;
    }

    .diagram-guide-panel .artifact-label {
      margin-bottom: 5px;
    }

    .read-guide-body {
      margin: 0;
      color: #34475d;
      font-size: 1rem;
      line-height: 1.45;
    }

    .read-guide > summary {
      cursor: pointer;
    }

    .diagram-box-section,
    .ownership-section {
      display: grid;
      gap: 7px;
      min-width: 0;
    }

    .diagram-box-section[hidden] {
      display: none;
    }

    .diagram-box-list {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      min-width: 0;
      border: 1px solid rgba(3, 105, 161, 0.14);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.94);
      overflow: hidden;
    }

    .diagram-box-row {
      display: grid;
      grid-template-columns: 38px minmax(170px, 0.42fr) minmax(0, 1fr);
      gap: 11px;
      align-items: start;
      min-width: 0;
      padding: 9px 11px;
      border-bottom: 1px solid rgba(3, 105, 161, 0.12);
    }

    .diagram-box-row:last-child {
      border-bottom: 0;
    }

    .diagram-box-index {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 24px;
      border: 1px solid rgba(13, 68, 104, 0.2);
      border-radius: 999px;
      color: #294961;
      background: rgba(248, 252, 255, 0.96);
      font-weight: 700;
      font-size: 0.76rem;
    }

    .diagram-box-name {
      display: grid;
      gap: 3px;
      min-width: 0;
    }

    __ODYLITH_ATLAS_DIAGRAM_BOX_ROLE_LABEL__
    .diagram-box-name strong,
    .diagram-box-role,
    .diagram-box-description {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .diagram-box-role {
      width: fit-content;
      max-width: 100%;
      justify-content: flex-start;
    }

    .diagram-box-description {
      margin: 0;
      min-width: 0;
    }

    .diagram-box-content {
      display: grid;
      gap: 8px;
      min-width: 0;
    }

    .diagram-box-details {
      min-width: 0;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .diagram-box-details > summary {
      cursor: pointer;
      color: #36566f;
    }

    .diagram-box-details > summary:focus-visible {
      outline: 2px solid #0369a1;
      outline-offset: 2px;
    }

    .diagram-box-details dl {
      margin: 8px 0 0;
    }

    .diagram-box-details dt {
      font-weight: 600;
      white-space: pre-wrap;
    }

    .diagram-box-details dd {
      margin: 3px 0 10px;
      white-space: pre-wrap;
    }

    .component-list {
      margin-top: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 8px;
      min-width: 0;
      max-width: 100%;
      border: 0;
      background: transparent;
      overflow: visible;
    }

    .component-card {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 6px;
      align-items: start;
      min-width: 0;
      max-width: 100%;
      border: 1px solid rgba(3, 105, 161, 0.14);
      border-radius: 10px;
      padding: 10px 12px;
      background: rgba(255, 255, 255, 0.94);
    }

    .component-card strong {
      display: block;
    }

    .component-heading {
      display: flex;
      flex-wrap: wrap;
      gap: 5px 8px;
      align-items: baseline;
      min-width: 0;
    }

    .component-token {
      display: block;
      margin: 2px 0 0;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .component-card p {
      margin: 0;
      max-width: 72ch;
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

    .artifact-group:has(> #ownerWorkstreamLinks:empty),
    .artifact-group:has(> #activeWorkstreamLinks:empty),
    .workstream-context:has(> .artifact-group > #ownerWorkstreamLinks:empty):has(> .artifact-group > #activeWorkstreamLinks:empty):has(> #historicalWorkstreamGroup[hidden]) {
      display: none;
    }

    .artifact-label {
      margin: 0 0 6px 0;
    }
    __ODYLITH_ATLAS_ARTIFACT_LABEL_TYPOGRAPHY__

    .engineering-context-list {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      min-width: 0;
      border: 1px solid rgba(3, 105, 161, 0.14);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.94);
      overflow: hidden;
    }

    .linked-context-section .artifact-group {
      display: grid;
      grid-template-columns: minmax(150px, 210px) minmax(0, 1fr);
      gap: 12px;
      align-items: start;
      margin-bottom: 0;
      min-width: 0;
      padding: 10px 11px;
      border-bottom: 1px solid rgba(3, 105, 161, 0.12);
    }

    .linked-context-section .artifact-group:last-child {
      border-bottom: 0;
    }

    .linked-context-section .artifact-group:has(> .artifact-list:empty) {
      display: none;
    }

    .engineering-context-empty {
      margin: 0;
      padding: 10px 11px;
      color: #34475d;
      overflow-wrap: anywhere;
    }

    .engineering-context-list:has(> .artifact-group > .artifact-list:not(:empty)) > .engineering-context-empty {
      display: none;
    }

    .linked-context-section .artifact-label {
      margin: 0;
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
      max-height: none;
      overflow: visible;
      padding-right: 0;
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

    @media (max-width: 760px) {
      .diagram-facts { grid-template-columns: 1fr; }

      .diagram-box-row,
      .component-card,
      .linked-context-section .artifact-group {
        grid-template-columns: minmax(0, 1fr);
        gap: 6px;
      }
    }
"""

DETAIL_LAYOUT_HTML = r"""
      <section class="hero">
        <div class="hero-copy">
          <div class="diagram-heading">
            <h2 id="diagramTitle" class="hero-title"></h2>
            <button id="sidebarToggle" class="tool-btn" type="button" aria-controls="sidebarPanel" aria-expanded="true">Hide Panel</button>
          </div>
          <section id="staleAlert" class="alert" role="status"></section>
          <p id="diagramSummary" class="summary"></p>
        </div>
      </section>

      <section class="viewer-shell">
        <div class="viewer-toolbar">
          <div class="viewer-toolbar-left">
            <span id="zoomReadout" class="meta-pill">Zoom 100%</span>
            <span class="meta-pill">Pinch: zoom</span>
            <span class="meta-pill">Drag: pan</span>
            <span class="meta-pill">Shortcuts: + - 0 f</span>
          </div>
          <div class="viewer-toolbar-right">
            <button id="prevDiagram" class="tool-btn" type="button">Prev</button>
            <button id="nextDiagram" class="tool-btn" type="button">Next</button>
            <button id="zoomIn" class="tool-btn" type="button">Zoom +</button>
            <button id="zoomOut" class="tool-btn" type="button">Zoom -</button>
            <button id="fit" class="tool-btn" type="button">Fit</button>
            <button id="reset" class="tool-btn" type="button">Read at 100%</button>
          </div>
        </div>
        <p id="viewerInstructions" class="viewer-instructions">Tab to diagram: arrows pan; Shift pans farther. +/− zoom; 0 reads at 100%; F fits. Outside diagram, ↑/↓ select.</p>
        <div id="viewerStage" class="viewer-stage" tabindex="0" role="region" aria-labelledby="diagramTitle" aria-describedby="viewerInstructions">
          <img id="viewerImage" class="viewer-image" alt="diagram visualization" draggable="false" hidden />
        </div>
      </section>

      <section class="details-grid">
        <article class="section diagram-explanation-section">
          <details class="diagram-guide-panel read-guide">
              <summary class="artifact-label">How to read this diagram</summary>
              <p id="diagramReadGuide" class="read-guide-body"></p>
            </details>
          <div id="diagramBoxesSection" class="diagram-box-section" hidden>
            <p class="artifact-label">Boxes In This Diagram</p>
            <div id="diagramBoxList" class="diagram-box-list"></div>
          </div>
          <details class="ownership-section">
            <summary class="artifact-label">Owning components</summary>
            <div id="componentList" class="component-list"></div>
          </details>
        </article>

        <details class="section diagram-metadata">
          <summary class="artifact-label">Diagram details</summary>
          <div class="diagram-facts" role="list">
            <div class="diagram-fact" data-fact="diagram-id" role="listitem">
              <p class="diagram-fact-label">Diagram ID</p>
              <p id="diagramId" class="diagram-fact-value"></p>
            </div>
            <div class="diagram-fact" data-fact="kind" role="listitem">
              <p class="diagram-fact-label">Kind</p>
              <p id="diagramKind" class="diagram-fact-value"></p>
            </div>
            <div class="diagram-fact" data-fact="status" role="listitem">
              <p class="diagram-fact-label">Status</p>
              <p id="diagramStatus" class="diagram-fact-value"></p>
            </div>
            <div class="diagram-fact" data-fact="owner" role="listitem">
              <p class="diagram-fact-label">Owner</p>
              <p id="diagramOwner" class="diagram-fact-value"></p>
            </div>
            <div class="diagram-fact" data-fact="reviewed" role="listitem">
              <p class="diagram-fact-label">Reviewed</p>
              <p id="diagramReviewed" class="diagram-fact-value"></p>
            </div>
            <div id="diagramFreshnessCard" class="diagram-fact" data-fact="freshness" role="listitem">
              <p class="diagram-fact-label">Freshness</p>
              <p id="diagramFreshness" class="diagram-fact-value"></p>
            </div>
          </div>
          <div id="sourceLinks" class="source-links"></div>
          <section class="workstream-context">
            <h3>Connected Workstream Context</h3>
            <div class="artifact-group">
              <p class="artifact-label">Owners</p>
              <ul id="ownerWorkstreamLinks" class="artifact-list workstream-context-list"></ul>
            </div>
            <div class="artifact-group">
              <p class="artifact-label">Active Touches</p>
              <ul id="activeWorkstreamLinks" class="artifact-list workstream-context-list"></ul>
            </div>
            <div id="historicalWorkstreamGroup" class="artifact-group" hidden>
              <p class="artifact-label">Historical References</p>
              <details id="historicalWorkstreamDisclosure" class="atlas-context-disclosure">
                <summary id="historicalWorkstreamSummary"></summary>
                <ul id="historicalWorkstreamLinks" class="artifact-list workstream-context-list"></ul>
              </details>
            </div>
          </section>
        </details>

        <details class="section linked-context-section">
          <summary class="artifact-label">Linked records</summary>
          <div class="engineering-context-list">
            <p class="engineering-context-empty" role="status">No engineering context is linked to this diagram yet.</p>
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
        </details>
      </section>
"""

DETAIL_RUNTIME_HELPERS_JS = r"""
    function renderDiagramBoxes(diagram, sectionEl, listEl) {
      listEl.replaceChildren();
      const boxes = Array.isArray(diagram.diagram_boxes)
        ? diagram.diagram_boxes.filter((box) => box && typeof box === "object" && typeof box.description === "string"
          && (box.description.trim() || (box.description === "" && typeof box.node_id === "string" && box.node_id)))
        : [];
      sectionEl.hidden = !boxes.length;
      boxes.forEach((box, index) => {
        const row = document.createElement("article");
        row.className = "diagram-box-row";

        const number = document.createElement("span");
        number.className = "diagram-box-index";
        number.textContent = String(index + 1);

        const name = document.createElement("div");
        name.className = "diagram-box-name";
        const heading = document.createElement("strong");
        heading.textContent = String(box.label ?? "");
        name.appendChild(heading);
        const roleText = String(box.role ?? "");

        const content = document.createElement("div");
        content.className = "diagram-box-content";
        if (box.description) {
          const description = document.createElement("p");
          description.className = "diagram-box-description";
          description.textContent = String(box.description ?? "");
          content.appendChild(description);
        }
        const detailRows = Array.isArray(box.details) && box.details.length ? [
          ...(roleText.trim() ? [{label: "Role", text: roleText}] : []),
          ...box.details,
        ] : [];
        if (detailRows.length) {
          const disclosure = document.createElement("details");
          disclosure.className = "diagram-box-details";
          const summary = document.createElement("summary");
          summary.textContent = "Supporting details";
          const entries = document.createElement("dl");
          detailRows.forEach((detail) => {
            const label = document.createElement("dt");
            label.textContent = String(detail.label ?? "");
            const text = document.createElement("dd");
            text.textContent = String(detail.text ?? "");
            entries.appendChild(label);
            entries.appendChild(text);
          });
          disclosure.appendChild(summary);
          disclosure.appendChild(entries);
          content.appendChild(disclosure);
        }

        row.appendChild(number);
        row.appendChild(name);
        row.appendChild(content);
        listEl.appendChild(row);
      });
    }

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
      const catalogGuide = String(diagram && diagram.read_guide ? diagram.read_guide : "").trim();
      return catalogGuide;
    }
"""
