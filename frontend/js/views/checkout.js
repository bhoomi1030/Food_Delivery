// Checkout: cart editing, coupon, live server-side pricing, address and place order.
import { api } from "../api.js";
import { cartPayload, cartSubtotal, changeQuantity, clearCart } from "../cart.js";
import { billRows, stepper, toast, vegDot } from "../components.js";
import { getState } from "../store.js";
import { esc, inr, uuid } from "../utils.js";

export async function checkoutView(root) {
  const { auth, cart } = getState();

  if (cart.items.length === 0) {
    root.innerHTML = `
      <div class="empty" data-testid="empty-cart"><div class="big">🛒</div>
        <h2>Your cart is empty</h2><p>Add something tasty from a restaurant.</p>
        <a class="btn" href="#/">Browse restaurants</a></div>`;
    return;
  }

  let couponCode = "";
  let bill = null;
  let busy = false;
  let idempotencyKey = uuid(); // one key per checkout attempt -> safe retries

  async function refreshBill(showCouponError = true) {
    try {
      bill = await api.quote(cartPayload(couponCode));
    } catch (err) {
      if (couponCode) {
        if (showCouponError) toast(err.message, "error");
        couponCode = "";
        bill = await api.quote(cartPayload("")).catch(() => null);
      } else {
        toast(err.message, "error");
        bill = null;
      }
    }
  }

  const coupons = await api.coupons().catch(() => []);
  await refreshBill();

  function render() {
    const current = getState().cart;
    if (current.items.length === 0) { checkoutView(root); return; }
    const addressValue = root.querySelector("#address") ? root.querySelector("#address").value : "";
    root.innerHTML = `
      <h1 class="page-title">Checkout</h1>
      <p class="page-sub">From <strong data-testid="cart-restaurant">${esc(current.restaurantName)}</strong></p>
      <div class="checkout">
        <section class="card card-pad">
          <h3>Your items</h3>
          <div data-testid="cart-lines">
            ${current.items.map((l) => `
              <div class="cart-row" data-testid="cart-line">
                <div><div class="item-name">${vegDot(l.is_veg)} ${esc(l.name)}</div>
                  <div class="muted">${inr(l.price)} each</div></div>
                <div style="display:flex;gap:12px;align-items:center">
                  ${stepper(l.id, l.quantity)}
                  <strong>${inr(l.price * l.quantity)}</strong>
                </div>
              </div>`).join("")}
          </div>
          <h3 style="margin-top:20px">Delivery address</h3>
          <div class="field">
            <textarea id="address" rows="3" placeholder="House no., street, area, city" data-testid="address">${esc(addressValue)}</textarea>
          </div>
        </section>
        <aside class="card card-pad">
          <h3>Offers</h3>
          ${bill && bill.coupon_code
            ? `<div class="applied" data-testid="coupon-applied"><span>${esc(bill.coupon_code)} applied</span>
                 <button class="btn secondary small" id="remove-coupon" data-testid="remove-coupon">Remove</button></div>`
            : `<div class="coupon-row">
                 <input class="input" id="coupon" placeholder="Coupon code" data-testid="coupon-input" aria-label="Coupon code">
                 <button class="btn secondary" id="apply-coupon" data-testid="apply-coupon">Apply</button>
               </div>
               <div class="coupon-chips">${coupons.map((c) => `<button class="chip" data-code="${esc(c.code)}" title="${esc(c.description)}">${esc(c.code)}</button>`).join("")}</div>`}
          <h3 style="margin-top:20px">Bill details</h3>
          <div data-testid="bill">${bill ? billRows(bill) : '<p class="muted">Could not calculate the bill.</p>'}</div>
          <div class="form-error" id="form-error" data-testid="checkout-error"></div>
          <button class="btn block" id="place" data-testid="place-order" ${busy || !bill ? "disabled" : ""}>
            ${auth ? (busy ? "Placing order…" : `Place order · ${bill ? inr(bill.total) : ""}`) : "Login to place order"}
          </button>
        </aside>
      </div>`;
  }

  async function applyCoupon(code) {
    if (!code.trim()) { toast("Enter a coupon code", "error"); return; }
    couponCode = code.trim().toUpperCase();
    await refreshBill();
    if (bill && bill.coupon_code) toast(`${bill.coupon_code} applied – you saved ${inr(bill.discount)}`, "success");
    render();
  }

  async function place() {
    if (!getState().auth) { location.hash = "#/login?next=%23%2Fcheckout"; return; }
    const address = root.querySelector("#address").value.trim();
    const errorEl = root.querySelector("#form-error");
    if (address.length < 8) { errorEl.textContent = "Please enter a complete delivery address (min 8 characters)."; return; }
    busy = true;
    render();
    root.querySelector("#address").value = address;
    try {
      const order = await api.placeOrder({ ...cartPayload(couponCode), delivery_address: address }, idempotencyKey);
      clearCart();
      toast("Order placed! 🎉", "success");
      location.hash = `#/orders?placed=${order.id}`;
    } catch (err) {
      busy = false;
      idempotencyKey = uuid();
      await refreshBill(false);
      render();
      root.querySelector("#address").value = address;
      root.querySelector("#form-error").textContent = err.message;
    }
  }

  root.onclick = async (e) => {
    const stepButton = e.target.closest("[data-action]");
    if (stepButton) {
      changeQuantity(Number(stepButton.dataset.id), stepButton.dataset.action === "inc" ? 1 : -1);
      if (getState().cart.items.length) await refreshBill(false);
      render();
      return;
    }
    const chip = e.target.closest("[data-code]");
    if (chip) { await applyCoupon(chip.dataset.code); return; }
    if (e.target.closest("#apply-coupon")) { await applyCoupon(root.querySelector("#coupon").value); return; }
    if (e.target.closest("#remove-coupon")) { couponCode = ""; await refreshBill(false); render(); return; }
    if (e.target.closest("#place")) { await place(); }
  };

  render();
  void cartSubtotal;
}
