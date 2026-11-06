/* =====================================================================
   SkillTrack AI - main.js
   Small, dependency-free helpers. No inline handlers in templates.
   ===================================================================== */

(function () {
  "use strict";

  /* ---------------------------------------------------------- sidebar */
  const body = document.body;

  function closeSidebar() {
    body.classList.remove("sidebar-open");
  }

  document.querySelectorAll("[data-sidebar-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      body.classList.toggle("sidebar-open");
    });
  });

  document.querySelectorAll("[data-sidebar-close]").forEach(function (element) {
    element.addEventListener("click", closeSidebar);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeSidebar();
    }
  });

  /* ------------------------------------------------------ flash messages */
  document.querySelectorAll(".flash-item").forEach(function (element) {
    window.setTimeout(function () {
      if (typeof bootstrap === "undefined") {
        element.remove();
        return;
      }
      bootstrap.Alert.getOrCreateInstance(element).close();
    }, 6000);
  });

  /* ------------------------------------------------------ password fields */
  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    button.addEventListener("click", function () {
      const input = document.getElementById(button.getAttribute("data-toggle-password"));
      if (!input) {
        return;
      }
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.textContent = showing ? "Show" : "Hide";
      button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  });

  /* ----------------------------------------------------- range sliders */
  document.querySelectorAll("[data-range]").forEach(function (range) {
    const row = range.closest(".skill-row");
    const output = row ? row.querySelector("[data-range-output]") : null;

    function sync() {
      if (output) {
        output.textContent = Number(range.value).toFixed(1);
      }
    }

    range.addEventListener("input", sync);
    sync();
  });

  /* ------------------------------------------------- submit loading state */
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      const button = form.querySelector("[data-loading]");
      if (!button || button.disabled) {
        return;
      }

      const label = button.getAttribute("data-loading") || "Please wait...";
      button.dataset.previousHtml = button.innerHTML;
      button.disabled = true;
      button.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' +
        label;

      // Safety net: if navigation is blocked by the browser, restore the button
      window.setTimeout(function () {
        if (button.dataset.previousHtml) {
          button.disabled = false;
          button.innerHTML = button.dataset.previousHtml;
        }
      }, 15000);
    });
  });

  /* -------------------------------------------------- resume file picker */
  const fileInput = document.querySelector("[data-file-input]");
  const fileNameLabel = document.querySelector("[data-file-name]");
  const dropZone = document.querySelector("[data-drop-zone]");

  if (fileInput && fileNameLabel) {
    fileInput.addEventListener("change", function () {
      fileNameLabel.textContent = fileInput.files.length
        ? fileInput.files[0].name
        : "No file selected";
    });
  }

  if (dropZone && fileInput) {
    ["dragenter", "dragover"].forEach(function (name) {
      dropZone.addEventListener(name, function (event) {
        event.preventDefault();
        dropZone.classList.add("is-dragover");
      });
    });
    ["dragleave", "drop"].forEach(function (name) {
      dropZone.addEventListener(name, function (event) {
        event.preventDefault();
        dropZone.classList.remove("is-dragover");
      });
    });
    dropZone.addEventListener("drop", function (event) {
      if (event.dataTransfer && event.dataTransfer.files.length) {
        fileInput.files = event.dataTransfer.files;
        fileInput.dispatchEvent(new Event("change"));
      }
    });
  }

  /* ------------------------------------------- auto-submit filter selects */
  document.querySelectorAll("[data-autosubmit]").forEach(function (field) {
    field.addEventListener("change", function () {
      const form = field.closest("form");
      if (form) {
        form.submit();
      }
    });
  });

  /* ------------------------------------------- mark unsaved profile state */
  const profileForm = document.getElementById("profile-form");
  if (profileForm) {
    let dirty = false;

    profileForm.addEventListener("input", function () {
      dirty = true;
    });

    window.addEventListener("beforeunload", function (event) {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    });

    profileForm.addEventListener("submit", function () {
      dirty = false;
    });
  }
})();
