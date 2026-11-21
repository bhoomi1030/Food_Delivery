// Restaurant page: grouped menu with add / remove steppers bound to the cart.
import { api } from "../api.js";
import { addItem, belongsToOtherRestaurant, changeQuantity, clearCart, quantityOf } from "../cart.js";
import { confirmDialog, stepper, toast, vegDot } from "../components.js";
import { esc, inr } from "../utils.js";

export async function restaurantView(root, { id }) {
  root.innerHTML = `<a class="back" href="#/">← All restaurants</a><div class="skeleton"></div>`;

  let restaurant;
  try {
    restaurant = await api.restaurant(id);
  } catch (err) {
    root.innerHTML = `<a class="back" href="#/">← All restaurants</a>
      <div class="empty" data-testid="not-found"><div class="big">😕</div><p>${esc(err.message)}</p></div>`;
    return;
  }

  const categories = [...new Set(restaurant.menu.map((m) => m.category))];

  function render() {
    root.innerHTML = `
      <a class="back" href="#/">← All restaurants</a>
      <div class="card r-header">
        <div class="r-emoji" aria-hidden="true">${esc(restaurant.emoji)}</div>
        <div>
          <h1 class="page-title" data-testid="restaurant-name">${esc(restaurant.name)}</h1>
          <div class="muted">${esc(restaurant.cuisine)} · ${esc(restaurant.description)}</div>
          <div class="r-meta" style="margin-top:8px">
            <span class="rating">★ ${restaurant.rating.toFixed(1)}</span>
            <span>${restaurant.delivery_minutes} mins</span>
            ${restaurant.is_open ? "" : '<span class="badge closed">Closed</span>'}
          </div>
        </div>
      </div>
      ${categories.map((category) => `
        <h2 class="menu-cat">${esc(category)}</h2>
        <div class="card menu-list">
          ${restaurant.menu.filter((m) => m.category === category).map((item) => {
            const qty = quantityOf(item.id);
            return `
              <div class="menu-item" data-testid="menu-item" data-id="${item.id}">
                <div>
                  <div class="item-name">${vegDot(item.is_veg)} <span data-testid="item-name">${esc(item.name)}</span></div>
                  <div class="item-desc">${esc(item.description)}</div>
                  <div class="item-price">${inr(item.price)}</div>
                </div>
                <div>
                  ${!restaurant.is_open || !item.is_available
                    ? '<span class="badge closed">Unavailable</span>'
                    : qty > 0 ? stepper(item.id, qty)
                    : `<button class="btn small" data-action="add" data-id="${item.id}" data-testid="add-${item.id}">ADD</button>`}
                </div>
              </div>`;
          }).join("")}
        </div>`).join("")}`;
  }

  async function addToCart(item) {
    if (belongsToOtherRestaurant(restaurant.id)) {
      const ok = await confirmDialog({
        title: "Start a new cart?",
        message: "Your cart has items from another restaurant. Adding this will clear it.",
        confirmText: "Yes, start new cart",
      });
      if (!ok) return;
      clearCart();
    }
    addItem(restaurant, item);
  }

  root.addEventListener("click", async (e) => {
    const button = e.target.closest("[data-action]");
    if (!button) return;
    const item = restaurant.menu.find((m) => m.id === Number(button.dataset.id));
    if (!item) return;
    const action = button.dataset.action;
    if (action === "add" || action === "inc") {
      const before = quantityOf(item.id);
      await addToCart(item);
      if (quantityOf(item.id) === before && before >= 10) toast("Maximum 10 per item", "error");
    } else if (action === "dec") {
      changeQuantity(item.id, -1);
    }
    render();
  });

  render();
}
