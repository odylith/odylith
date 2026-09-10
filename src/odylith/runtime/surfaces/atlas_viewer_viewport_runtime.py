"""Own Atlas diagram sizing, reading controls, and pointer or keyboard navigation."""

VIEWPORT_RUNTIME_JS = r"""    function createAtlasViewport({ stageEl, imageEl, zoomReadoutEl, controls }) {
      let diagram = null;
      let ready = false;
      let scale = 1;
      let offsetX = 0;
      let offsetY = 0;
      let dragging = false;
      let dragStartX = 0;
      let dragStartY = 0;
      let panPointerId = null;
      let pinchState = null;
      const activePointers = new Map();
      const MIN_SCALE = 0.05;
      const MAX_SCALE = 5;

      function clamp(value, low, high) {
        return Math.min(high, Math.max(low, value));
      }

      function applyTransform() {
        imageEl.style.transform = `translate(calc(-50% + ${offsetX}px), calc(-50% + ${offsetY}px)) scale(${scale})`;
        zoomReadoutEl.textContent = `Zoom ${Math.round(scale * 100)}%`;
      }

      function resetView() {
        scale = 1;
        offsetX = 0;
        offsetY = 0;
        applyTransform();
      }

      function diagramDimensions() {
        const vbw = Number(diagram && diagram.svg_viewbox_width ? diagram.svg_viewbox_width : 0);
        const vbh = Number(diagram && diagram.svg_viewbox_height ? diagram.svg_viewbox_height : 0);
        if (Number.isFinite(vbw) && Number.isFinite(vbh) && vbw > 0 && vbh > 0) {
          return { width: vbw, height: vbh };
        }
        const iw = imageEl.naturalWidth || 0;
        const ih = imageEl.naturalHeight || 0;
        return iw && ih ? { width: iw, height: ih } : null;
      }

      function applyImageBoxSizing() {
        const dims = diagramDimensions();
        // Percentage-sized SVGs need their viewBox size, not tiny intrinsic img dimensions.
        imageEl.style.width = dims ? `${dims.width}px` : "";
        imageEl.style.height = dims ? `${dims.height}px` : "";
      }

      function stageFitPadding() {
        const shortSide = Math.min(stageEl.clientWidth || 0, stageEl.clientHeight || 0);
        return shortSide ? clamp(shortSide * 0.045, 18, 54) : 18;
      }

      function computedFitScale() {
        const dims = diagramDimensions();
        if (!dims) return null;
        const padding = stageFitPadding();
        const sw = Math.max(1, (stageEl.clientWidth || 1) - padding * 2);
        const sh = Math.max(1, (stageEl.clientHeight || 1) - padding * 2);
        return Math.min(sw / dims.width, sh / dims.height);
      }

      function applyInitialView() {
        const rawFitScale = computedFitScale();
        if (rawFitScale === null) {
          resetView();
          return;
        }
        let initialFactor = 1.0;
        const MIN_INITIAL_FIT_FACTOR = 0.94;
        const rawOverrideFactor = Number(diagram && diagram.initial_view_fit_factor ? diagram.initial_view_fit_factor : 0);
        if (Number.isFinite(rawOverrideFactor) && rawOverrideFactor > 0) {
          initialFactor = clamp(rawOverrideFactor, MIN_INITIAL_FIT_FACTOR, initialFactor);
        }
        const target = rawFitScale * initialFactor;
        scale = clamp(target, MIN_SCALE, 1);
        offsetX = 0;
        offsetY = 0;
        applyTransform();
      }

      function fitView() {
        if (!ready) return;
        const rawFitScale = computedFitScale();
        if (rawFitScale === null) {
          resetView();
          return;
        }
        scale = clamp(rawFitScale, MIN_SCALE, MAX_SCALE);
        offsetX = 0;
        offsetY = 0;
        applyTransform();
      }

      function readAtFullSize() {
        if (!ready) return;
        resetView();
        stageEl.focus({ preventScroll: true });
        stageEl.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "instant" });
      }

      function zoomTo(targetScale, centerX, centerY) {
        if (!ready) return;
        const oldScale = scale;
        const newScale = clamp(targetScale, MIN_SCALE, MAX_SCALE);
        if (newScale === oldScale) return;
        const px = centerX - stageEl.clientWidth / 2;
        const py = centerY - stageEl.clientHeight / 2;
        offsetX = px - ((px - offsetX) / oldScale) * newScale;
        offsetY = py - ((py - offsetY) / oldScale) * newScale;
        scale = newScale;
        applyTransform();
      }

      function zoomBy(factor, centerX = stageEl.clientWidth / 2, centerY = stageEl.clientHeight / 2) {
        zoomTo(scale * factor, centerX, centerY);
      }

      function pointerRecord(event) {
        return { x: event.clientX, y: event.clientY, type: event.pointerType };
      }

      function touchPointers() {
        return [...activePointers.values()].filter((item) => item.type === "touch");
      }

      function distance(a, b) {
        return Math.hypot(a.x - b.x, a.y - b.y);
      }

      function endPan() {
        dragging = false;
        panPointerId = null;
        stageEl.classList.remove("dragging");
      }

      function setReady(value) {
        ready = value;
        Object.values(controls).forEach((button) => { button.disabled = !ready; });
        stageEl.tabIndex = ready ? 0 : -1;
        stageEl.setAttribute("aria-disabled", String(!ready));
        if (!ready) {
          endPan();
          activePointers.clear();
          pinchState = null;
        }
      }

      controls.zoomIn.addEventListener("click", () => zoomBy(1.14));
      controls.zoomOut.addEventListener("click", () => zoomBy(0.88));
      controls.fit.addEventListener("click", fitView);
      controls.reset.addEventListener("click", readAtFullSize);

      stageEl.addEventListener("pointerdown", (event) => {
        if (!ready) return;
        activePointers.set(event.pointerId, pointerRecord(event));
        stageEl.setPointerCapture(event.pointerId);
        const touches = touchPointers();
        if (touches.length >= 2) {
          endPan();
          pinchState = {
            startDistance: Math.max(1, distance(touches[0], touches[1])),
            startScale: scale,
          };
          return;
        }
        if (!pinchState) {
          dragging = true;
          panPointerId = event.pointerId;
          dragStartX = event.clientX - offsetX;
          dragStartY = event.clientY - offsetY;
          stageEl.classList.add("dragging");
        }
      });

      stageEl.addEventListener("pointermove", (event) => {
        if (!ready) return;
        if (activePointers.has(event.pointerId)) {
          activePointers.set(event.pointerId, pointerRecord(event));
        }
        const touches = touchPointers();
        if (touches.length >= 2) {
          const [a, b] = touches;
          if (!pinchState) {
            pinchState = { startDistance: Math.max(1, distance(a, b)), startScale: scale };
          }
          const rect = stageEl.getBoundingClientRect();
          const ratio = distance(a, b) / Math.max(1, pinchState.startDistance);
          zoomTo(pinchState.startScale * ratio, (a.x + b.x) / 2 - rect.left, (a.y + b.y) / 2 - rect.top);
          return;
        }
        pinchState = null;
        if (dragging && event.pointerId === panPointerId) {
          offsetX = event.clientX - dragStartX;
          offsetY = event.clientY - dragStartY;
          applyTransform();
        }
      });

      function stopPointer(event) {
        activePointers.delete(event.pointerId);
        if (event.pointerId === panPointerId) endPan();
        if (touchPointers().length < 2) pinchState = null;
        if (stageEl.hasPointerCapture(event.pointerId)) stageEl.releasePointerCapture(event.pointerId);
      }

      stageEl.addEventListener("pointerup", stopPointer);
      stageEl.addEventListener("pointercancel", stopPointer);
      // Trackpad pinch arrives as wheel+ctrlKey; ordinary page scrolling must not zoom.
      stageEl.addEventListener("wheel", (event) => {
        if (!ready || !event.ctrlKey) return;
        event.preventDefault();
        const rect = stageEl.getBoundingClientRect();
        zoomBy(event.deltaY < 0 ? 1.08 : 0.92, event.clientX - rect.left, event.clientY - rect.top);
      }, { passive: false });

      stageEl.addEventListener("keydown", (event) => {
        if (!ready || document.activeElement !== stageEl || event.ctrlKey || event.metaKey || event.altKey) return;
        const step = event.shiftKey ? 240 : 80;
        if (event.key === "ArrowLeft") offsetX += step;
        else if (event.key === "ArrowRight") offsetX -= step;
        else if (event.key === "ArrowUp") offsetY += step;
        else if (event.key === "ArrowDown") offsetY -= step;
        else return;
        event.preventDefault();
        event.stopPropagation();
        applyTransform();
      });

      window.addEventListener("keydown", (event) => {
        if (!ready || event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
        const target = event.target;
        if (target instanceof Element && (target.closest("input, textarea, select") || target.isContentEditable)) return;
        const key = event.key;
        if (key === "+" || key === "=") zoomBy(1.14);
        else if (key === "-") zoomBy(0.88);
        else if (key === "0") readAtFullSize();
        else if (key.toLowerCase() === "f") fitView();
        else return;
        event.preventDefault();
      });
      window.addEventListener("resize", fitView);
      setReady(false);

      return {
        setDiagram(nextDiagram) {
          if (diagram === nextDiagram && ready) return;
          setReady(false);
          diagram = nextDiagram;
          applyImageBoxSizing();
        },
        imageLoaded() {
          if (!diagram || ready) return;
          setReady(true);
          applyImageBoxSizing();
          applyInitialView();
        },
        clear() {
          setReady(false);
          diagram = null;
          resetView();
        },
      };
    }
"""
