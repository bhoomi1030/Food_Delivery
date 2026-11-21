// Cart rules. A cart belongs to exactly one restaurant at a time.
import { getState, setCart, emptyCart } from "./store.js";

export const MAX_QTY = 10;

export function cartCount() {
  return getState().cart.items.reduce((sum, line) => sum + line.quantity, 0);
}

export function cartSubtotal() {
  return getState().cart.items.reduce((sum, line) => sum + line.price * line.quantity, 0);
}

export function quantityOf(menuItemId) {
  const line = getState().cart.items.find((l) => l.id === menuItemId);
  return line ? line.quantity : 0;
}

export function belongsToOtherRestaurant(restaurantId) {
  const { cart } = getState();
  return cart.items.length > 0 && cart.restaurantId !== restaurantId;
}

/** Add one unit. The caller must confirm first if belongsToOtherRestaurant() is true. */
export function addItem(restaurant, item) {
  let { cart } = getState();
  if (cart.restaurantId !== restaurant.id) {
    cart = { restaurantId: restaurant.id, restaurantName: restaurant.name, items: [] };
  }
  const items = cart.items.map((l) => ({ ...l }));
  const existing = items.find((l) => l.id === item.id);
  if (existing) {
    existing.quantity = Math.min(MAX_QTY, existing.quantity + 1);
  } else {
    items.push({ id: item.id, name: item.name, price: item.price, is_veg: item.is_veg, quantity: 1 });
  }
  setCart({ ...cart, items });
}

export function changeQuantity(menuItemId, delta) {
  const { cart } = getState();
  const items = cart.items
    .map((l) => (l.id === menuItemId ? { ...l, quantity: Math.min(MAX_QTY, l.quantity + delta) } : l))
    .filter((l) => l.quantity > 0);
  setCart(items.length ? { ...cart, items } : emptyCart());
}

export function clearCart() {
  setCart(emptyCart());
}

/** Payload shape expected by POST /api/orders/quote and POST /api/orders. */
export function cartPayload(couponCode) {
  const { cart } = getState();
  return {
    restaurant_id: cart.restaurantId,
    items: cart.items.map((l) => ({ menu_item_id: l.id, quantity: l.quantity })),
    coupon_code: couponCode || null,
  };
}
