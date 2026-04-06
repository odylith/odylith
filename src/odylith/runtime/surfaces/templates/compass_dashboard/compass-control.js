const SHELL = JSON.parse(document.getElementById("compassShellData").textContent);
window.__ODYLITH_COMPASS_SHELL__ = SHELL && typeof SHELL === "object" ? SHELL : {};
init();
