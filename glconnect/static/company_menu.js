(function () {
  if (window.__companyMenuInit) return;
  window.__companyMenuInit = true;

  function closeMenu(menu) {
    var dropdown = menu.querySelector("[data-company-dropdown]");
    var toggle = menu.querySelector("[data-company-toggle]");
    if (!dropdown || !toggle) return;
    dropdown.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  }

  function bindMenu(menu) {
    if (menu.dataset.companyBound === "true") return;
    menu.dataset.companyBound = "true";

    var toggle = menu.querySelector("[data-company-toggle]");
    var dropdown = menu.querySelector("[data-company-dropdown]");
    if (!toggle || !dropdown) return;

    toggle.addEventListener("click", function (e) {
      e.stopPropagation();
      document.querySelectorAll("[data-company-menu]").forEach(function (other) {
        if (other !== menu) closeMenu(other);
      });
      var open = dropdown.hidden;
      dropdown.hidden = !open;
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  function init() {
    document.querySelectorAll("[data-company-menu]").forEach(bindMenu);

    document.addEventListener("click", function (e) {
      document.querySelectorAll("[data-company-menu]").forEach(function (menu) {
        var dropdown = menu.querySelector("[data-company-dropdown]");
        var toggle = menu.querySelector("[data-company-toggle]");
        if (!dropdown || dropdown.hidden) return;
        if (!menu.contains(e.target)) closeMenu(menu);
      });
    });

    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      document.querySelectorAll("[data-company-menu]").forEach(function (menu) {
        var dropdown = menu.querySelector("[data-company-dropdown]");
        if (dropdown && !dropdown.hidden) closeMenu(menu);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
