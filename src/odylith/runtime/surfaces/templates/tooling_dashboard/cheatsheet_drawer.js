(function initToolingShellCheatsheetDrawer() {
  const root = document.querySelector("[data-agent-cheatsheet]");
  if (!root || root.dataset.cheatsheetBound === "true") return;
  root.dataset.cheatsheetBound = "true";

  const drawer = document.getElementById("odylithDrawer");
  const toggle = document.getElementById("odylithToggle");
  const searchInput = root.querySelector("[data-cheatsheet-search]");
  const results = document.getElementById("agentCheatsheetResults");
  const copyStatus = document.getElementById("agentCheatsheetCopyStatus");
  const emptyState = document.getElementById("agentCheatsheetEmpty");
  const cards = Array.from(root.querySelectorAll("[data-cheatsheet-card]"));
  const filterButtons = Array.from(root.querySelectorAll("[data-cheatsheet-filter]"));
  const copyButtons = Array.from(root.querySelectorAll("[data-cheatsheet-copy-button]"));
  const totalCards = cards.length;
  let activeCategory = "all";

  function setCopyStatus(message) {
    if (!copyStatus) return;
    copyStatus.textContent = String(message || "").trim();
  }

  function visibleLabel(count, query) {
    const filterButton = filterButtons.find((button) => (button.dataset.cheatsheetFilter || "all") === activeCategory);
    const categoryLabel = filterButton ? String(filterButton.dataset.cheatsheetFilterLabel || "").trim() : "";
    const parts = [`${count} workflow${count === 1 ? "" : "s"} visible`];
    if (activeCategory !== "all" && categoryLabel) {
      parts.push(categoryLabel);
    }
    if (query) {
      parts.push(`matching "${query}"`);
    } else {
      parts.push(`of ${totalCards}`);
    }
    return parts.join(" · ");
  }

  function applyFilters() {
    const query = String(searchInput && searchInput.value ? searchInput.value : "").trim().toLowerCase();
    let visibleCount = 0;
    cards.forEach((card) => {
      const category = String(card.dataset.cheatsheetCategory || "all").trim();
      const haystack = String(card.dataset.searchText || "").toLowerCase();
      const categoryMatch = activeCategory === "all" || activeCategory === category;
      const queryMatch = !query || haystack.includes(query);
      const visible = categoryMatch && queryMatch;
      card.hidden = !visible;
      card.setAttribute("aria-hidden", String(!visible));
      if (visible) visibleCount += 1;
    });
    filterButtons.forEach((button) => {
      const isActive = (button.dataset.cheatsheetFilter || "all") === activeCategory;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
    if (results) {
      results.textContent = visibleLabel(visibleCount, query);
    }
    if (emptyState) {
      emptyState.hidden = visibleCount !== 0;
    }
  }

  async function handleCopyClick(event) {
    const button = event.currentTarget;
    const text = String(button.dataset.copyText || "").trim();
    if (!text) return;
    const successMessage = String(button.dataset.copySuccess || "Copied.").trim();
    const copied = typeof copyText === "function"
      ? await copyText(text)
      : false;
    setCopyStatus(copied ? successMessage : "Copy failed. Copy the text manually.");
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      applyFilters();
    });
  }

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activeCategory = String(button.dataset.cheatsheetFilter || "all").trim() || "all";
      applyFilters();
    });
  });

  copyButtons.forEach((button) => {
    button.addEventListener("click", handleCopyClick);
  });

  if (toggle && drawer && searchInput) {
    toggle.addEventListener("click", () => {
      window.requestAnimationFrame(() => {
        if (drawer.classList.contains("open")) {
          searchInput.focus();
          searchInput.select();
        }
      });
    });
  }

  applyFilters();
})();
