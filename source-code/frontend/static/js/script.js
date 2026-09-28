document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".nav-links");
  if (toggle && nav)
    toggle.addEventListener("click", () => nav.classList.toggle("is-open"));

  document.querySelectorAll(".password-toggle").forEach((button) => {
    button.addEventListener("click", () => {
      const input = button.parentElement.querySelector("input");
      input.type = input.type === "password" ? "text" : "password";
      button.textContent = input.type === "password" ? "Show" : "Hide";
    });
  });

  const bookingForm = document.querySelector("form[data-price]");
  if (bookingForm) {
    const checkIn = bookingForm.querySelector('[name="check_in"]');
    const checkOut = bookingForm.querySelector('[name="check_out"]');
    const total = document.querySelector("#total-price");
    const nights = document.querySelector("#night-count");
    const price = Number(bookingForm.dataset.price);
    const updateTotal = () => {
      if (!checkIn.value || !checkOut.value) {
        total.textContent = "INR 0";
        nights.textContent = "Choose dates to calculate";
        return;
      }
      const days = Math.round(
        (new Date(`${checkOut.value}T00:00:00`) -
          new Date(`${checkIn.value}T00:00:00`)) /
          86400000,
      );
      if (days > 0) {
        total.textContent = `INR ${(days * price).toLocaleString("en-IN")}`;
        nights.textContent = `${days} night${days === 1 ? "" : "s"}`;
      } else {
        total.textContent = "INR 0";
        nights.textContent = "Check-out must be later";
      }
    };
    checkIn.addEventListener("change", updateTotal);
    checkOut.addEventListener("change", updateTotal);
    updateTotal();
  }

  document.querySelectorAll(".alerts .alert").forEach((alert) => {
    window.setTimeout(() => alert.remove(), 5000);
  });
});
