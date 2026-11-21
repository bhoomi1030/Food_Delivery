// Small, dependency-free helpers shared by all modules.

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/** Escape text before putting it inside an HTML template (prevents XSS). */
export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);
}

/** Format whole rupees as ₹1,234. */
export function inr(amount) {
  return "₹" + Number(amount).toLocaleString("en-IN");
}

export function debounce(fn, wait = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

export function uuid() {
  if (globalThis.crypto && crypto.randomUUID) return crypto.randomUUID();
  return Date.now().toString(36) + Math.random().toString(16).slice(2);
}

export function plural(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

/** Split "#/login?next=%23%2Fcheckout" into { path, params }. */
export function parseHash(hash) {
  const raw = hash && hash.length > 1 ? hash : "#/";
  const [path, query = ""] = raw.split("?");
  return { path, params: new URLSearchParams(query) };
}

export const STATUS_LABELS = {
  PLACED: "Order placed",
  CONFIRMED: "Confirmed",
  PREPARING: "Preparing",
  OUT_FOR_DELIVERY: "Out for delivery",
  DELIVERED: "Delivered",
  CANCELLED: "Cancelled",
};
