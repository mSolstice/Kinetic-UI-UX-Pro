const form = document.querySelector("#checkout-form");
const steps = Array.from(document.querySelectorAll(".form-step"));
const stepTabs = Array.from(document.querySelectorAll("[data-step-target]"));
const backButton = document.querySelector("#back-button");
const nextButton = document.querySelector("#next-button");
const errorSummary = document.querySelector("#error-summary");
const statusMessage = document.querySelector("#status-message");
const successPanel = document.querySelector("#success-panel");
const successEmail = document.querySelector("#success-email");

const shippingReview = document.querySelector("#shipping-review");
const paymentReview = document.querySelector("#payment-review");
const lineItems = document.querySelector("#line-items");
const totals = document.querySelector("#totals");
const orderTotal = document.querySelector("[data-order-total]");

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD"
});

const order = {
  items: [
    { name: "Studio carry kit", detail: "1 item", price: 149 },
    { name: "Protected shipping", detail: "Included", price: 0 }
  ],
  tax: 12.67
};

const model = {
  fullName: "",
  email: "",
  phone: "",
  address: "",
  city: "",
  region: "",
  postalCode: "",
  delivery: "standard",
  cardName: "",
  cardNumber: "",
  expiry: "",
  cvc: "",
  billingSame: true
};

const stepFields = [
  ["fullName", "email", "phone", "address", "city", "region", "postalCode", "delivery"],
  ["cardName", "cardNumber", "expiry", "cvc"],
  []
];

const labels = {
  fullName: "Full name",
  email: "Email",
  phone: "Phone",
  address: "Street address",
  city: "City",
  region: "State",
  postalCode: "ZIP code",
  delivery: "Delivery speed",
  cardName: "Name on card",
  cardNumber: "Card number",
  expiry: "Expiration",
  cvc: "Security code"
};

let currentStep = 0;
let maxUnlockedStep = 0;
let status = { name: "editing" };

function total() {
  return order.items.reduce((sum, item) => sum + item.price, 0) + order.tax;
}

function hydrateFromStorage() {
  try {
    const saved = JSON.parse(localStorage.getItem("kinetic-checkout") || "{}");
    Object.keys(model).forEach((key) => {
      if (Object.prototype.hasOwnProperty.call(saved, key)) {
        model[key] = saved[key];
      }
    });
  } catch {
    localStorage.removeItem("kinetic-checkout");
  }
}

function saveModel() {
  localStorage.setItem("kinetic-checkout", JSON.stringify(model));
}

function populateFields() {
  Object.entries(model).forEach(([name, value]) => {
    const field = form.elements[name];
    if (!field) return;
    if (field.type === "checkbox") {
      field.checked = Boolean(value);
    } else {
      field.value = value;
    }
  });
}

function updateModelFromForm() {
  Object.keys(model).forEach((name) => {
    const field = form.elements[name];
    if (!field) return;
    model[name] = field.type === "checkbox" ? field.checked : field.value.trim();
  });
  saveModel();
}

function clearErrors() {
  errorSummary.hidden = true;
  errorSummary.innerHTML = "";
  stepFields.flat().forEach((name) => {
    const field = form.elements[name];
    const error = document.querySelector(`#${name}-error`);
    if (field) {
      field.removeAttribute("aria-invalid");
      field.removeAttribute("aria-describedby");
    }
    if (error) error.textContent = "";
  });
}

function setFieldError(name, message) {
  const field = form.elements[name];
  const error = document.querySelector(`#${name}-error`);
  if (!field || !error) return;
  field.setAttribute("aria-invalid", "true");
  field.setAttribute("aria-describedby", `${name}-error`);
  error.textContent = message;
}

function validateField(name) {
  const value = String(model[name] ?? "").trim();

  if (!value) return `${labels[name]} is required.`;
  if (name === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
    return "Enter an email address in the format name@example.com.";
  }
  if (name === "phone" && value.replace(/\D/g, "").length < 10) {
    return "Enter a phone number with at least 10 digits.";
  }
  if (name === "postalCode" && !/^[0-9]{5}(-[0-9]{4})?$/.test(value)) {
    return "Enter a 5-digit ZIP code or ZIP+4.";
  }
  if (name === "cardNumber" && value.replace(/\D/g, "").length < 13) {
    return "Enter a card number with at least 13 digits.";
  }
  if (name === "expiry" && !isValidExpiry(value)) {
    return "Enter a future expiration date as MM/YY.";
  }
  if (name === "cvc" && !/^[0-9]{3,4}$/.test(value)) {
    return "Enter the 3 or 4 digit security code.";
  }
  return "";
}

function isValidExpiry(value) {
  const match = value.match(/^(0[1-9]|1[0-2])\/?([0-9]{2})$/);
  if (!match) return false;
  const month = Number(match[1]);
  const year = 2000 + Number(match[2]);
  const expiry = new Date(year, month, 0, 23, 59, 59);
  return expiry >= new Date();
}

function validateStep(stepIndex) {
  updateModelFromForm();
  clearErrors();
  const errors = stepFields[stepIndex]
    .map((name) => ({ name, message: validateField(name) }))
    .filter((error) => error.message);

  errors.forEach((error) => setFieldError(error.name, error.message));

  if (errors.length > 0) {
    const list = errors
      .map((error) => `<li><a href="#${error.name}">${error.message}</a></li>`)
      .join("");
    errorSummary.innerHTML = `<p>We need a few details before continuing.</p><ul>${list}</ul>`;
    errorSummary.hidden = false;
    errorSummary.focus({ preventScroll: false });
    return false;
  }

  statusMessage.textContent = `${stepTabs[stepIndex].textContent.trim()} complete.`;
  return true;
}

function showStep(stepIndex) {
  currentStep = stepIndex;
  clearErrors();
  successPanel.hidden = true;
  status = { name: "editing" };

  steps.forEach((step, index) => {
    const active = index === currentStep;
    step.hidden = !active;
    step.classList.toggle("is-active", active);
  });

  stepTabs.forEach((tab, index) => {
    const unlocked = index <= maxUnlockedStep;
    tab.classList.toggle("is-active", index === currentStep);
    tab.classList.toggle("is-complete", index < maxUnlockedStep);
    tab.setAttribute("aria-disabled", String(!unlocked));
    tab.removeAttribute("aria-current");
    if (index === currentStep) tab.setAttribute("aria-current", "step");
  });

  backButton.textContent = currentStep === 0 ? "Back to cart" : "Back";
  backButton.setAttribute("aria-disabled", String(currentStep === 0));
  nextButton.textContent = currentStep === 0
    ? "Continue to payment"
    : currentStep === 1
      ? "Review order"
      : "Place order";

  if (currentStep === 2) renderReview();
}

function renderReview() {
  const shippingRows = [
    ["Name", model.fullName],
    ["Email", model.email],
    ["Phone", model.phone],
    ["Address", `${model.address}, ${model.city}, ${model.region} ${model.postalCode}`],
    ["Delivery", model.delivery === "express" ? "Express, 1 to 2 business days" : "Standard, 3 to 5 business days"]
  ];

  const digits = model.cardNumber.replace(/\D/g, "");
  const paymentRows = [
    ["Card", `Ending in ${digits.slice(-4) || "----"}`],
    ["Billing", model.billingSame ? "Same as shipping" : "Different billing address"]
  ];

  shippingReview.innerHTML = rowsToDefinitionList(shippingRows);
  paymentReview.innerHTML = rowsToDefinitionList(paymentRows);
  lineItems.innerHTML = order.items.map((item) => (
    `<li><span><strong>${item.name}</strong><small>${item.detail}</small></span><span>${money.format(item.price)}</span></li>`
  )).join("");
  totals.innerHTML = rowsToDefinitionList([
    ["Tax", money.format(order.tax)],
    ["Total", money.format(total())]
  ], "total-row");
}

function rowsToDefinitionList(rows, className = "review-row") {
  return rows.map(([term, value]) => (
    `<div class="${className}"><dt>${term}</dt><dd>${value}</dd></div>`
  )).join("");
}

function placeOrder() {
  if (status.name === "loading") return;
  updateModelFromForm();
  status = { name: "loading" };
  form.setAttribute("aria-busy", "true");
  nextButton.textContent = "Placing order...";
  nextButton.setAttribute("aria-disabled", "true");

  window.setTimeout(() => {
    status = { name: "success" };
    form.removeAttribute("aria-busy");
    nextButton.removeAttribute("aria-disabled");
    nextButton.textContent = "Place order";
    successEmail.textContent = model.email;
    successPanel.hidden = false;
    successPanel.focus({ preventScroll: false });
    statusMessage.textContent = "Order placed. Receipt details are shown on the page.";
  }, 650);
}

form.addEventListener("input", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement)) return;

  if (target.name === "cardNumber") {
    target.value = target.value.replace(/\D/g, "").replace(/(.{4})/g, "$1 ").trim();
  }
  if (target.name === "expiry") {
    target.value = target.value.replace(/\D/g, "").replace(/^([0-9]{2})([0-9])/, "$1/$2").slice(0, 5);
  }

  updateModelFromForm();
});

form.addEventListener("blur", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement)) return;
  updateModelFromForm();
  const message = validateField(target.name);
  const fieldIsInCurrentStep = stepFields[currentStep].includes(target.name);
  if (fieldIsInCurrentStep && message) setFieldError(target.name, message);
}, true);

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (status.name === "loading") return;
  if (currentStep < 2) {
    if (!validateStep(currentStep)) return;
    maxUnlockedStep = Math.max(maxUnlockedStep, currentStep + 1);
    showStep(currentStep + 1);
    return;
  }
  placeOrder();
});

backButton.addEventListener("click", () => {
  if (currentStep === 0) return;
  updateModelFromForm();
  showStep(currentStep - 1);
});

stepTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const targetStep = Number(tab.dataset.stepTarget);
    if (targetStep > maxUnlockedStep) return;
    updateModelFromForm();
    showStep(targetStep);
  });
});

errorSummary.addEventListener("click", (event) => {
  const link = event.target.closest("a");
  if (!link) return;
  const field = document.querySelector(link.getAttribute("href"));
  if (field) field.focus();
});

hydrateFromStorage();
populateFields();
orderTotal.textContent = money.format(total());
showStep(0);
