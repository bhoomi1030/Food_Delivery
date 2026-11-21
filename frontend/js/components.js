// Reusable UI pieces: toasts, confirm dialog, restaurant card, quantity stepper.
import { esc, inr } from "./utils.js";

export function toast(message, type = "info") {
  const root = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.dataset.testid = "toast";
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3600);
}

/** Promise-based confirm dialog. Resolves true/false. */
export function confirmDialog({ title, message, confirmText = "Confirm", cancelText = "Cancel" }) {
  return new Promise((resolve) => {
    const root = document.getElementById("modal-root");
    root.innerHTML = `
      <div class="modal-backdrop" data-testid="modal">
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <h3 id="modal-title">${esc(title)}</h3>
          <p class="muted">${esc(message)}</p>
          <div class="modal-actions">
            <button class="btn secondary" data-testid="modal-cancel">${esc(cancelText)}</button>
            <button class="btn" data-testid="modal-confirm">${esc(confirmText)}</button>
          </div>
        </div>
      </div>`;
    const close = (result) => {
      root.innerHTML = "";
      resolve(result);
    };
    root.querySelector("[data-testid=modal-cancel]").onclick = () => close(false);
    root.querySelector("[data-testid=modal-confirm]").onclick = () => close(true);
    root.querySelector(".modal-backdrop").onclick = (e) => {
      if (e.target.classList.contains("modal-backdrop")) close(false);
    };
  });
}

export function restaurantCard(r) {
  return `
    <article class="card r-card" data-testid="restaurant-card" data-id="${r.id}" tabindex="0" role="link"
             aria-label="${esc(r.name)}">
      <div class="r-emoji" aria-hidden="true">${esc(r.emoji)}</div>
      <div class="r-name">${esc(r.name)}</div>
      <div class="muted">${esc(r.cuisine)}</div>
      <div class="r-meta">
        <span class="rating">★ ${r.rating.toFixed(1)}</span>
        <span>${r.delivery_minutes} mins</span>
        ${r.is_veg ? '<span class="badge veg">Pure veg</span>' : ""}
        ${r.is_open ? "" : '<span class="badge closed">Closed</span>'}
      </div>
    </article>`;
}

export function vegDot(isVeg) {
  return `<span class="veg-dot ${isVeg ? "" : "nonveg"}" title="${isVeg ? "Vegetarian" : "Non-vegetarian"}"></span>`;
}

export function stepper(id, quantity) {
  return `
    <div class="stepper" data-testid="stepper-${id}">
      <button data-action="dec" data-id="${id}" aria-label="Remove one">−</button>
      <span class="qty" data-testid="qty-${id}">${quantity}</span>
      <button data-action="inc" data-id="${id}" aria-label="Add one">+</button>
    </div>`;
}

export function billRows(bill) {
  return `
    <div class="bill-row"><span>Item total</span><span data-testid="bill-subtotal">${inr(bill.subtotal)}</span></div>
    ${bill.discount > 0 ? `<div class="bill-row"><span>Discount${bill.coupon_code ? ` (${esc(bill.coupon_code)})` : ""}</span><span class="discount" data-testid="bill-discount">−${inr(bill.discount)}</span></div>` : ""}
    <div class="bill-row"><span>Delivery fee</span><span data-testid="bill-delivery">${bill.delivery_fee === 0 ? "FREE" : inr(bill.delivery_fee)}</span></div>
    <div class="bill-row"><span>Taxes (5%)</span><span data-testid="bill-tax">${inr(bill.tax)}</span></div>
    <div class="bill-row total"><span>To pay</span><span data-testid="bill-total">${inr(bill.total)}</span></div>`;
}
