(() => {
      const initialStep = Number(window.registrationWizardConfig?.initialStep || 1);
      const titles = {
        1: "Paso 1 de 5",
        2: "Paso 2 de 5",
        3: "Paso 3 de 5",
        4: "Paso 4 de 5",
        5: "Paso 5 de 5"
      };
      const statusCopy = {
        1: "Comienza con tus datos básicos.",
        2: "Ubicamos tu nivel y momento profesional.",
        3: "Ahora traduce tu experiencia a skills concretas.",
        4: "Definamos la dirección que quieres seguir.",
        5: "Último paso: objetivo y disponibilidad."
      };
      const wizard = document.getElementById("registrationWizard");
      const panels = Array.from(document.querySelectorAll(".wizard-panel"));
      const tracks = Array.from(document.querySelectorAll("[data-track-step]"));
      const progressTitle = document.getElementById("progressTitle");
      const stepStatus = document.getElementById("stepStatus");
      const backButton = document.getElementById("backButton");
      const nextButton = document.getElementById("nextButton");
      const submitButton = document.getElementById("submitButton");
      let currentStep = Math.min(5, Math.max(1, initialStep || 1));

      const parseTags = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);
      const formatTags = (items) => Array.from(new Set(items.map((item) => item.trim()).filter(Boolean))).join(", ");

      document.querySelectorAll("[data-picker]").forEach((picker) => {
        const hiddenInput = picker.querySelector('input[type="hidden"]');
        const selectedWrap = picker.querySelector(".tag-picker__selected");
        const searchInput = picker.querySelector(".tag-input");
        const suggestionsWrap = picker.querySelector(".suggestions");
        const options = JSON.parse(picker.dataset.options || "[]");
        let selected = parseTags(hiddenInput.value);

        const updateHidden = () => {
          hiddenInput.value = formatTags(selected);
        };

        const renderSelected = () => {
          selectedWrap.innerHTML = "";
          selected.forEach((label) => {
            const chip = document.createElement("span");
            chip.className = "tag";
            chip.innerHTML = `<span>${label}</span><button type="button" aria-label="Quitar ${label}">×</button>`;
            chip.querySelector("button").addEventListener("click", () => {
              selected = selected.filter((item) => item !== label);
              updateHidden();
              renderSelected();
              renderSuggestions(searchInput.value);
            });
            selectedWrap.appendChild(chip);
          });
        };

        const addTag = (label) => {
          const clean = label.trim();
          if (!clean) return;
          if (!selected.includes(clean)) {
            selected.push(clean);
            updateHidden();
            renderSelected();
          }
          searchInput.value = "";
          renderSuggestions("");
        };

        const renderSuggestions = (query) => {
          const normalized = (query || "").toLowerCase().trim();
          suggestionsWrap.innerHTML = "";
          options
            .filter((label) => !selected.includes(label))
            .filter((label) => !normalized || label.toLowerCase().includes(normalized))
            .slice(0, 8)
            .forEach((label) => {
              const button = document.createElement("button");
              button.type = "button";
              button.className = "suggestion";
              button.textContent = label;
              button.addEventListener("click", () => addTag(label));
              suggestionsWrap.appendChild(button);
            });
        };

        searchInput.addEventListener("input", (event) => renderSuggestions(event.target.value));
        searchInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && searchInput.value.trim()) {
            event.preventDefault();
            addTag(searchInput.value);
          }
        });

        updateHidden();
        renderSelected();
        renderSuggestions("");
      });

      const getStepFields = (step) => {
        const panel = panels.find((item) => Number(item.dataset.step) === step);
        return panel ? Array.from(panel.querySelectorAll("[data-required='1']")) : [];
      };

      const isFieldValid = (field) => {
        const type = (field.type || "").toLowerCase();
        if (type === "radio") {
          const group = wizard.querySelectorAll(`[name="${field.name}"]`);
          return Array.from(group).some((item) => item.checked);
        }
        return Boolean((field.value || "").trim());
      };

      const focusFirstInvalidField = (step) => {
        const fields = getStepFields(step);
        const invalid = fields.find((field) => !isFieldValid(field));
        if (invalid) {
          if (invalid.type === "hidden") {
            const picker = invalid.closest("[data-picker]");
            const input = picker ? picker.querySelector(".tag-input") : null;
            if (input) input.focus();
          } else {
            invalid.focus();
          }
        }
      };

      const validateStep = (step) => {
        const fields = getStepFields(step);
        return fields.every((field) => isFieldValid(field));
      };

      const paint = () => {
        panels.forEach((panel) => {
          panel.classList.toggle("is-active", Number(panel.dataset.step) === currentStep);
        });
        tracks.forEach((track) => {
          const step = Number(track.dataset.trackStep);
          track.classList.toggle("is-active", step === currentStep);
          track.classList.toggle("is-complete", step < currentStep);
        });
        progressTitle.textContent = titles[currentStep] || "Paso";
        stepStatus.textContent = statusCopy[currentStep] || "";
        backButton.style.display = currentStep === 1 ? "none" : "inline-flex";
        nextButton.style.display = currentStep === 5 ? "none" : "inline-flex";
        submitButton.style.display = currentStep === 5 ? "inline-flex" : "none";
      };

      nextButton.addEventListener("click", () => {
        if (!validateStep(currentStep)) {
          focusFirstInvalidField(currentStep);
          return;
        }
        currentStep = Math.min(5, currentStep + 1);
        paint();
      });

      backButton.addEventListener("click", () => {
        currentStep = Math.max(1, currentStep - 1);
        paint();
      });

      wizard.addEventListener("submit", (event) => {
        if (!validateStep(currentStep)) {
          event.preventDefault();
          focusFirstInvalidField(currentStep);
          return;
        }
        for (let step = 1; step <= 5; step += 1) {
          if (!validateStep(step)) {
            event.preventDefault();
            currentStep = step;
            paint();
            focusFirstInvalidField(step);
            return;
          }
        }
      });

      paint();
    })();
