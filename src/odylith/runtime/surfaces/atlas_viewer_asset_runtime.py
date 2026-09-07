"""Atlas viewer asset loading, recovery, and explicit activation feedback."""

VIEWER_ASSET_INITIALIZATION_JS = r"""    const imageErrorEl = document.createElement("div");
    imageErrorEl.id = "viewerAssetError";
    imageErrorEl.className = "alert";
    imageErrorEl.setAttribute("role", "alert");
    imageErrorEl.setAttribute("aria-live", "assertive");
    imageErrorEl.hidden = true;
    stageEl.appendChild(imageErrorEl);

    const viewerShellEl = stageEl.closest(".viewer-shell");
    viewerShellEl.tabIndex = -1;
    viewerShellEl.setAttribute("aria-labelledby", "diagramTitle");
    // Only explicit catalog activation hands off from the stacked list to its viewer.
    // Focusing the shell keeps Prev/Next first in the subsequent keyboard tab order.
    listEl.addEventListener("click", (event) => {
      if (!event.target.closest("button[data-diagram]")) return;
      if (!window.matchMedia("(max-width: 1180px)").matches) return;
      viewerShellEl.focus({ preventScroll: true });
      viewerShellEl.scrollIntoView({ block: "start", inline: "nearest", behavior: "instant" });
    });"""

VIEWER_ASSET_CLEAR_JS = r"""      imageEl.removeAttribute("src");
      viewport.clear();
      imageEl.dataset.fallbackApplied = "";"""

VIEWER_ASSET_LOAD_JS = r"""      imageEl.onload = () => {
        imageEl.hidden = false;
        imageErrorEl.hidden = true;
        imageErrorEl.classList.remove("visible");
        imageErrorEl.textContent = "";
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
      imageEl.hidden = false;
      imageErrorEl.hidden = true;
      imageErrorEl.classList.remove("visible");
      imageErrorEl.textContent = "";
      imageEl.dataset.fallbackApplied = "";
      viewport.setDiagram(diagram);
      imageEl.src = diagram.source_svg_href;"""
