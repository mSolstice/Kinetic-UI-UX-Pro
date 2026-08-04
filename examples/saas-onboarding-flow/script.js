(function () {
  const form = document.querySelector("[data-onboarding-form]");
  const steps = Array.from(document.querySelectorAll("[data-step]"));
  const navSteps = Array.from(document.querySelectorAll("[data-nav-step]"));
  const progress = document.querySelector("[data-progress]");
  const readiness = document.querySelector("[data-readiness]");
  const live = document.querySelector("[data-live-region]");
  const nextButton = document.querySelector("[data-next]");
  const backButton = document.querySelector("[data-back]");
  const skipButton = document.querySelector("[data-skip]");
  const emailInput = document.querySelector("[data-email]");
  const roleSelect = document.querySelector("[data-role]");
  const addInviteButton = document.querySelector("[data-add-invite]");
  const sampleButton = document.querySelector("[data-load-sample]");
  const inviteList = document.querySelector("[data-invite-list]");
  const emptyInvites = document.querySelector("[data-empty-invites]");
  const inviteError = document.querySelector("[data-invite-error]");
  const connectorError = document.querySelector("[data-connector-error]");
  const connectorStatus = document.querySelector("[data-connector-status]");
  const reviewInvites = document.querySelector("[data-review-invites]");
  const reviewConnector = document.querySelector("[data-review-connector]");

  const state = {
    step: 0,
    invites: [],
    connector: "",
    connectorStatus: "idle",
    inviteStatus: "idle"
  };

  const nextLabels = ["Start setup", "Continue to data", "Connect source", "Open dashboard"];

  function announce(message) {
    live.textContent = "";
    window.setTimeout(() => {
      live.textContent = message;
    }, 20);
  }

  function setBusy(stepIndex, value) {
    const step = steps[stepIndex];
    if (step) {
      step.setAttribute("aria-busy", String(value));
    }
  }

  function setButtonBusy(button, busyLabel, idleLabel, busy) {
    button.textContent = busy ? busyLabel : idleLabel;
    button.setAttribute("aria-disabled", String(busy));
  }

  function validEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
  }

  function showError(node, message) {
    node.textContent = message;
    node.hidden = false;
  }

  function clearError(node) {
    node.textContent = "";
    node.hidden = true;
  }

  function updateProgress() {
    const invitePoints = state.invites.length > 0 ? 34 : 0;
    const connectorPoints = state.connectorStatus === "success" ? 33 : 0;
    const stepPoints = state.step > 0 ? 33 : 0;
    const value = Math.min(100, stepPoints + invitePoints + connectorPoints);
    progress.value = value;
    readiness.textContent = `${value}%`;
  }

  function renderSteps() {
    steps.forEach((step, index) => {
      step.classList.toggle("is-current", index === state.step);
    });

    navSteps.forEach((step, index) => {
      step.classList.toggle("is-active", index === state.step);
      step.classList.toggle("is-done", index < state.step);
    });

    backButton.hidden = state.step === 0;
    skipButton.hidden = state.step === 3;
    nextButton.textContent = nextLabels[state.step];
    updateProgress();

    const currentHeading = steps[state.step].querySelector("h2");
    if (currentHeading) {
      currentHeading.setAttribute("tabindex", "-1");
      currentHeading.focus({ preventScroll: true });
    }
  }

  function renderInvites() {
    inviteList.innerHTML = "";
    emptyInvites.hidden = state.invites.length > 0;

    state.invites.forEach((invite, index) => {
      const item = document.createElement("li");
      const content = document.createElement("span");
      const email = document.createElement("strong");
      const role = document.createElement("small");
      const remove = document.createElement("button");

      email.textContent = invite.email;
      role.textContent = invite.role;
      content.append(email, role);

      remove.type = "button";
      remove.className = "button button-ghost";
      remove.textContent = "Remove";
      remove.addEventListener("click", () => {
        state.invites.splice(index, 1);
        renderInvites();
        renderReview();
        updateProgress();
        announce("Invite removed.");
      });

      item.append(content, remove);
      inviteList.append(item);
    });
  }

  function renderReview() {
    reviewInvites.textContent = state.invites.length
      ? `${state.invites.length} pending invite${state.invites.length === 1 ? "" : "s"}`
      : "No teammates invited yet";
    reviewConnector.textContent = state.connectorStatus === "success"
      ? `${state.connector} connected`
      : "No source connected yet";
  }

  async function addInvite() {
    if (state.inviteStatus === "loading") return;
    clearError(inviteError);

    const email = emailInput.value.trim();
    const role = roleSelect.value;

    if (!validEmail(email)) {
      showError(inviteError, "We could not add that invite because the email address is incomplete. Enter a work email like alex@company.com.");
      announce("Invite email needs attention.");
      emailInput.focus();
      return;
    }

    if (state.invites.some((invite) => invite.email.toLowerCase() === email.toLowerCase())) {
      showError(inviteError, "That teammate is already on the invite list. Choose another email or remove the existing invite first.");
      announce("Duplicate invite was not added.");
      emailInput.focus();
      return;
    }

    state.inviteStatus = "loading";
    setBusy(1, true);
    setButtonBusy(addInviteButton, "Adding", "Add teammate", true);

    await delay(520);
    state.invites.push({ email, role });
    state.inviteStatus = "success";
    emailInput.value = "";
    renderInvites();
    renderReview();
    updateProgress();
    announce(`${email} added as ${role}.`);

    state.inviteStatus = "idle";
    setBusy(1, false);
    setButtonBusy(addInviteButton, "Adding", "Add teammate", false);
  }

  function loadSampleTeam() {
    clearError(inviteError);
    state.invites = [
      { email: "alex.chen@example.com", role: "Admin" },
      { email: "mira.patel@example.com", role: "Analyst" }
    ];
    renderInvites();
    renderReview();
    updateProgress();
    announce("Sample team added.");
  }

  async function connectSource() {
    if (state.connectorStatus === "loading") return false;
    clearError(connectorError);
    connectorStatus.hidden = true;

    const selected = form.querySelector("[data-connector]:checked");
    if (!selected) {
      showError(connectorError, "Choose one data source to continue, or skip this step and connect it later from settings.");
      announce("Choose a data source before connecting.");
      form.querySelector("[data-connector]").focus();
      return false;
    }

    state.connector = selected.value;
    state.connectorStatus = "loading";
    setBusy(2, true);
    setButtonBusy(nextButton, "Connecting", "Connect source", true);
    announce(`Connecting ${state.connector}.`);

    await delay(900);

    const shouldFail = state.connector === "Billing" && !connectSource.retrySucceeded;
    if (shouldFail) {
      connectSource.retrySucceeded = true;
      state.connectorStatus = "error";
      setBusy(2, false);
      setButtonBusy(nextButton, "Connecting", "Connect source", false);
      showError(connectorError, "We could not reach the billing provider. Check that popups are allowed, then try again.");
      announce("Billing connection failed. Try again.");
      return false;
    }

    state.connectorStatus = "success";
    setBusy(2, false);
    setButtonBusy(nextButton, "Connecting", "Connect source", false);
    connectorStatus.hidden = false;
    connectorStatus.textContent = `${state.connector} connected with read-only access.`;
    renderReview();
    updateProgress();
    announce(`${state.connector} connected.`);
    return true;
  }

  function goToStep(nextStep) {
    state.step = Math.max(0, Math.min(3, nextStep));
    renderSteps();
    renderReview();
  }

  async function handleNext() {
    if (state.step === 1 && state.invites.length === 0) {
      showError(inviteError, "Add a teammate, use the sample team, or skip this step for now.");
      announce("Invite step needs attention.");
      emailInput.focus();
      return;
    }

    if (state.step === 2) {
      const connected = await connectSource();
      if (!connected) return;
    }

    if (state.step === 3) {
      announce("Workspace setup complete. Opening dashboard.");
      nextButton.textContent = "Dashboard ready";
      nextButton.setAttribute("aria-disabled", "true");
      return;
    }

    goToStep(state.step + 1);
  }

  function handleSkip() {
    clearError(inviteError);
    clearError(connectorError);
    if (state.step < 3) {
      announce("Step skipped. You can resume setup from workspace settings.");
      goToStep(state.step + 1);
    }
  }

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  addInviteButton.addEventListener("click", addInvite);
  sampleButton.addEventListener("click", loadSampleTeam);
  nextButton.addEventListener("click", handleNext);
  backButton.addEventListener("click", () => goToStep(state.step - 1));
  skipButton.addEventListener("click", handleSkip);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    handleNext();
  });

  renderSteps();
  renderInvites();
  renderReview();
})();
