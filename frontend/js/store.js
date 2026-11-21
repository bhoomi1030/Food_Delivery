// Tiny observable store persisted in localStorage (auth session + cart).

const AUTH_KEY = "fooddash.auth";
const CART_KEY = "fooddash.cart";

const listeners = new Set();

function load(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function save(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable (private mode) – keep working in memory */
  }
}

export const emptyCart = () => ({ restaurantId: null, restaurantName: "", items: [] });

let state = {
  auth: load(AUTH_KEY, null),
  cart: load(CART_KEY, emptyCart()),
};

function emit() {
  listeners.forEach((fn) => fn(state));
}

export function getState() {
  return state;
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function setAuth(auth) {
  state = { ...state, auth };
  save(AUTH_KEY, auth);
  emit();
}

export function setCart(cart) {
  state = { ...state, cart };
  save(CART_KEY, cart.items.length ? cart : null);
  emit();
}
