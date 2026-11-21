// Order history with a status tracker, cancel and (demo) "advance" actions.
import { api } from "../api.js";
import { confirmDialog, toast } from "../components.js";
import { STATUS_LABELS, esc, inr, plural } from "../utils.js";

const TRACK = ["PLACED", "CONFIRMED", "PREPARING", "OUT_FOR_DELIVERY", "DELIVERED"];

function tracker(status) {
  if (status === "CANCELLED") return '<p class="muted">This order was cancelled.</p>';
  const reached = TRACK.indexOf(status);
  return `<div class="tracker" data-testid="tracker">${TRACK.map((s, i) =>
    `<div class="step ${i <= reached ? "done" : ""}"><div class="bar"></div>${STATUS_LABELS[s]}</div>`).join("")}</div>`;
}

function orderCard(o, highlightId) {
  const when = new Date(o.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  return `
    <article class="card order-card ${o.id === highlightId ? "highlight" : ""}" data-testid="order-card" data-id="${o.id}">
      <div class="order-head">
        <div><strong>${esc(o.restaurant_name)}</strong> <span class="muted">· Order #${o.id}</span></div>
        <span class="status ${o.status}" data-testid="order-status">${STATUS_LABELS[o.status] || o.status}</span>
      </div>
      <div class="muted">${esc(when)}</div>
      <div class="order-lines">${o.items.map((i) => `${i.quantity} × ${esc(i.name)}`).join(", ")}</div>
      ${tracker(o.status)}
      <div class="muted">📍 ${esc(o.delivery_address)}</div>
      <div class="order-head" style="margin-top:8px">
        <strong data-testid="order-total">Total ${inr(o.total)}</strong>
        <span class="muted">${o.coupon_code ? `Coupon ${esc(o.coupon_code)} · saved ${inr(o.discount)}` : ""}</span>
      </div>
      <div class="order-actions">
        ${o.next_status ? `<button class="btn secondary small" data-action="advance" data-id="${o.id}" data-testid="advance-order">Simulate: ${STATUS_LABELS[o.next_status]}</button>` : ""}
        ${o.can_cancel ? `<button class="btn danger small" data-action="cancel" data-id="${o.id}" data-testid="cancel-order">Cancel order</button>` : ""}
      </div>
    </article>`;
}

export async function ordersView(root, { params }) {
  const highlightId = Number(params.get("placed")) || null;
  let page = 1;

  async function load() {
    root.innerHTML = `<div class="skeleton"></div>`;
    try {
      const data = await api.orders(page);
      const pages = Math.max(1, Math.ceil(data.total / data.page_size));
      root.innerHTML = `
        <h1 class="page-title">My orders</h1>
        <p class="page-sub" data-testid="orders-count">${plural(data.total, "order")}</p>
        ${data.items.length === 0
          ? `<div class="empty" data-testid="no-orders"><div class="big">📦</div><p>No orders yet.</p><a class="btn" href="#/">Order now</a></div>`
          : data.items.map((o) => orderCard(o, highlightId)).join("")}
        ${pages > 1 ? `<div class="pager">
          <button class="btn secondary small" id="prev" ${page <= 1 ? "disabled" : ""}>← Newer</button>
          <span>Page ${page} of ${pages}</span>
          <button class="btn secondary small" id="next" ${page >= pages ? "disabled" : ""}>Older →</button></div>` : ""}`;
    } catch (err) {
      root.innerHTML = `<div class="empty"><div class="big">⚠️</div><p>${esc(err.message)}</p></div>`;
    }
  }

  root.onclick = async (e) => {
    if (e.target.closest("#prev")) { page -= 1; await load(); return; }
    if (e.target.closest("#next")) { page += 1; await load(); return; }
    const button = e.target.closest("[data-action]");
    if (!button) return;
    const id = Number(button.dataset.id);
    try {
      if (button.dataset.action === "cancel") {
        const ok = await confirmDialog({ title: "Cancel this order?", message: "This cannot be undone.", confirmText: "Yes, cancel" });
        if (!ok) return;
        await api.cancelOrder(id);
        toast("Order cancelled", "success");
      } else {
        await api.advanceOrder(id);
      }
      await load();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  await load();
}
