"""Own Atlas viewer selection, empty-state presentation, and asset recovery."""

EMPTY_VIEW_CSS = r"""
    .main > [hidden], #atlasProjectLink[hidden] { display: none; }
    .main[data-selection-empty="true"] {
      min-height: 0;
      grid-template-rows: auto;
      align-content: start;
    }
"""

EMPTY_VIEW_HTML = r"""
      <section id="atlasEmptyState" class="section" aria-labelledby="atlasEmptyTitle" hidden>
        <h2 id="atlasEmptyTitle"></h2>
        <p id="atlasEmptyMessage"></p>
        <a id="atlasProjectLink" class="tool-btn" target="_top">Open Project</a>
      </section>
"""

VIEWER_RUNTIME_JS = r"""    function createAtlasViewer({ mainEl, stageEl, imageEl, listEl, viewport, catalogCount, projectHref }) {
      let loadedDiagram = null;
      const emptyEl = mainEl.querySelector("#atlasEmptyState");
      const emptyTitleEl = emptyEl.querySelector("#atlasEmptyTitle");
      const emptyMessageEl = emptyEl.querySelector("#atlasEmptyMessage");
      const projectLinkEl = emptyEl.querySelector("#atlasProjectLink");
      projectLinkEl.href = projectHref;
      const selectedSections = [...mainEl.children].filter((section) => section !== emptyEl);
      const listStatusEl = document.getElementById("diagramListStatus");
      const navigation = [document.getElementById("prevDiagram"), document.getElementById("nextDiagram")];
      const imageErrorEl = document.createElement("div");
      imageErrorEl.id = "viewerAssetError";
      imageErrorEl.className = "alert";
      imageErrorEl.setAttribute("role", "alert");
      imageErrorEl.setAttribute("aria-live", "assertive");
      imageErrorEl.hidden = true;
      stageEl.appendChild(imageErrorEl);

      const viewerShellEl = stageEl.closest(".viewer-shell");
      viewerShellEl.tabIndex = -1;
      viewerShellEl.setAttribute("aria-labelledby", "diagramTitle");
      // Explicit compact-layout catalog activation hands focus to the viewer controls.
      listEl.addEventListener("click", (event) => {
        if (!event.target.closest("button[data-diagram]")) return;
        if (!window.matchMedia("(max-width: 1180px)").matches) return;
        viewerShellEl.focus({ preventScroll: true });
        viewerShellEl.scrollIntoView({ block: "start", inline: "nearest", behavior: "instant" });
      });

      function setSelectionAvailable(available) {
        mainEl.dataset.selectionEmpty = String(!available);
        emptyEl.hidden = available;
        selectedSections.forEach((section) => { section.hidden = !available; });
        navigation.forEach((button) => { button.disabled = !available; });
      }

      function clearError() {
        imageErrorEl.hidden = true;
        imageErrorEl.classList.remove("visible");
        imageErrorEl.textContent = "";
      }

      return {
        clear() {
          loadedDiagram = null;
          setSelectionAvailable(false);
          emptyTitleEl.textContent = catalogCount ? "No matching diagrams" : "No diagrams yet";
          emptyMessageEl.textContent = catalogCount
            ? "Change or clear the filters to browse diagrams."
            : "Atlas will show the architecture diagrams created for your project. Open Project to define what you want to build.";
          projectLinkEl.hidden = catalogCount > 0;
          imageEl.onload = null;
          imageEl.onerror = null;
          imageEl.hidden = true;
          imageEl.removeAttribute("src");
          imageEl.dataset.fallbackApplied = "";
          clearError();
          viewport.clear();
        },
        show(diagram) {
          setSelectionAvailable(true);
          if (diagram === loadedDiagram && !imageEl.hidden) return;
          loadedDiagram = diagram;
          imageEl.onload = () => {
            imageEl.hidden = false;
            clearError();
            viewport.imageLoaded();
          };
          imageEl.onerror = () => {
            const fallback = String(diagram.source_png_href || "").trim();
            if (!fallback || imageEl.dataset.fallbackApplied === "1") {
              imageEl.hidden = true;
              viewport.clear();
              imageErrorEl.textContent = "Diagram preview unavailable. Use Prev or Next to open another diagram, or review the diagram summary and source links on this page.";
              imageErrorEl.hidden = false;
              imageErrorEl.classList.add("visible");
              return;
            }
            imageEl.dataset.fallbackApplied = "1";
            imageEl.src = fallback;
          };
          imageEl.hidden = true;
          clearError();
          imageEl.dataset.fallbackApplied = "";
          viewport.setDiagram(diagram);
          imageEl.src = diagram.source_svg_href;
        },
        setResults({ matches, hasSelection }) {
          listStatusEl.hidden = catalogCount === 0 || matches > 0;
          listStatusEl.textContent = hasSelection
            ? "No diagrams match these filters. The selected diagram is still shown."
            : "No diagrams match these filters. Change or clear the filters to browse diagrams.";
        },
      };
    }
"""
