// Thin fetch wrapper. All server errors become ApiError with a readable message.
import { getState, setAuth } from "./store.js";

export class ApiError extends Error {
  constructor(message, status = 0, code = "error") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(path, { method = "GET", body, headers = {}, auth = false } = {}) {
  const finalHeaders = { Accept: "application/json", ...headers };
  if (body !== undefined) finalHeaders["Content-Type"] = "application/json";
  const session = getState().auth;
  if (auth && session) finalHeaders.Authorization = `Bearer ${session.token}`;

  let response;
  try {
    response = await fetch(path, {
      method,
      headers: finalHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the server. Please check your connection.", 0, "network");
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && auth) setAuth(null); // expired session
    const err = data && data.error;
    throw new ApiError(err ? err.message : `Request failed (${response.status})`, response.status, err ? err.code : "error");
  }
  return data;
}

const qs = (params) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== false) search.set(k, v);
  });
  const text = search.toString();
  return text ? `?${text}` : "";
};

export const api = {
  register: (payload) => request("/api/auth/register", { method: "POST", body: payload }),
  login: (payload) => request("/api/auth/login", { method: "POST", body: payload }),
  restaurants: (params) => request(`/api/restaurants${qs(params)}`),
  restaurant: (id) => request(`/api/restaurants/${id}`),
  coupons: () => request("/api/coupons"),
  quote: (payload) => request("/api/orders/quote", { method: "POST", body: payload }),
  placeOrder: (payload, idempotencyKey) =>
    request("/api/orders", { method: "POST", body: payload, auth: true, headers: { "Idempotency-Key": idempotencyKey } }),
  orders: (page = 1) => request(`/api/orders?page=${page}&page_size=5`, { auth: true }),
  cancelOrder: (id) => request(`/api/orders/${id}/cancel`, { method: "POST", auth: true }),
  advanceOrder: (id) => request(`/api/orders/${id}/advance`, { method: "POST", auth: true }),
};
