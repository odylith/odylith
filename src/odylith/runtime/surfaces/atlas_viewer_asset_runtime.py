"""Atlas viewer image loading, fallback, and failure-state client templates."""

VIEWER_ASSET_INITIALIZATION_JS = r"""    const imageErrorEl = document.createElement("div");
    imageErrorEl.id = "viewerAssetError";
    imageErrorEl.className = "alert";
    imageErrorEl.setAttribute("role", "alert");
    imageErrorEl.setAttribute("aria-live", "assertive");
    imageErrorEl.hidden = true;
    stageEl.appendChild(imageErrorEl);"""

VIEWER_ASSET_CLEAR_JS = r"""      imageEl.removeAttribute("src");
      imageEl.dataset.fallbackApplied = "";"""

VIEWER_ASSET_LOAD_JS = r"""      imageEl.onload = () => {
        imageEl.hidden = false;
        imageErrorEl.hidden = true;
        imageErrorEl.classList.remove("visible");
        imageErrorEl.textContent = "";
        applyInitialView(diagram);
      };
      imageEl.onerror = () => {
        const fallback = String(diagram.source_png_href || "").trim();
        if (!fallback || imageEl.dataset.fallbackApplied === "1") {
          imageEl.hidden = true;
          imageErrorEl.textContent = "Diagram preview unavailable. Use Prev or Next above to open another diagram, or review the diagram summary and source links below.";
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
      applyImageBoxSizing(diagram);
      imageEl.src = diagram.source_svg_href;"""
