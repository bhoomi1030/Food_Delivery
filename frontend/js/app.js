// App shell: hash router, header (auth + cart badge) and floating cart bar.
import { cartCount, cartSubtotal } from "./cart.js";
import { authView } from "./views/auth.js";
import { checkoutView } from "./views/checkout.js";
import { homeView } from "./views/home.js";
import { ordersView } from "./views/orders.js";
import { restaurantView } from "./views/restaurant.js";
import { getState, setAuth, subscribe } from "./store.js";
import { toast } from "./components.js";
import { esc, inr, parseHash, plural } from "./utils.js";

const PROTECTED = new Set(["/orders"]);

// Each view receives a fresh root element, so listeners never pile up between pages.
const routes = [
  { pattern: /^\/$/, nav: "home", view: (root) => homeView(root) },
  { pattern: /^\/restaurant\/(\d+)$/, nav: "home", view: (root, ctx, m) => restaurantView(root, { id: m[1] }) },
  { pattern: /^\/checkout$/, nav: "", view: (root) => checkoutView(root) },
  { pattern: /^\/orders$/, nav: "orders", view: (root, ctx) => ordersView(root, { params: ctx.params }) },
  { pattern: /^\/login$/, nav: "", view: (root, ctx) => authView(root, { mode: "login", params: ctx.params }) },
  { pattern: /^\/register$/, nav: "", view: (root, ctx) => authView(root, { mode: "register", params: ctx.params }) },
];

let navigation = 0;

function freshRoot() {
  const old = document.getElementById("app");
  const clone = old.cloneNode(false);
  old.replaceWith(clone);
  return clone;
}

async function router() {
  const current = ++navigation;
  const { path, params } = parseHash(location.hash);
  const route = path.startsWith("#") ? path.slice(1) : path;
  const clean = route === "" ? "/" : route;

  if (PROTECTED.has(clean) && !getState().auth) {
    location.hash = `#/login?next=${encodeURIComponent(location.hash || "#/")}`;
    return;
  }

  const root = freshRoot();
  const match = routes.map((r) => ({ r, m: clean.match(r.pattern) })).find((x) => x.m);
  if (!match) {
    markNav("");
    root.innerHTML = `<div class="empty" data-testid="not-found-page"><div class="big">🧭</div><h2>Page not found</h2><a class="btn" href="#/">Go home</a></div>`;
    return;
  }

  markNav(match.r.nav);
  window.scrollTo({ top: 0 });
  try {
    await match.r.view(root, { params }, match.m);
  } catch (err) {
    if (current === navigation) {
      root.innerHTML = `<div class="empty"><div class="big">⚠️</div><p>${esc(err.message)}</p></div>`;
    }
  }
}

function markNav(name) {
  document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === name));
}

function renderChrome() {
  const { auth } = getState();
  const count = cartCount();

  const badge = document.querySelector("[data-testid=cart-count]");
  badge.textContent = count;
  badge.hidden = count === 0;

  document.getElementById("auth-area").innerHTML = auth
    ? `<span class="user-chip" data-testid="user-name">Hi, ${esc(auth.user.name.split(" ")[0])}</span>
       <button class="btn secondary small" id="logout" data-testid="logout">Log out</button>`
    : `<a class="btn secondary small" href="#/login" data-testid="login-link">Log in</a>
       <a class="btn small" href="#/register" data-testid="signup-link">Sign up</a>`;

  const bar = document.getElementById("cart-bar");
  const onCheckout = location.hash.startsWith("#/checkout");
  if (count > 0 && !onCheckout) {
    bar.hidden = false;
    bar.dataset.testid = "cart-bar";
    bar.innerHTML = `<span>${plural(count, "item")} · ${inr(cartSubtotal())}</span><span>View cart →</span>`;
  } else {
    bar.hidden = true;
  }
}

document.getElementById("cart-bar").addEventListener("click", () => {
  location.hash = "#/checkout";
});
document.getElementById("auth-area").addEventListener("click", (e) => {
  if (e.target.closest("#logout")) {
    setAuth(null);
    toast("Logged out");
    location.hash = "#/";
  }
});

subscribe(renderChrome);
window.addEventListener("hashchange", () => {
  renderChrome();
  router();
});
renderChrome();
router();
