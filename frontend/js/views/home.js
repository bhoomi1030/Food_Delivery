// Home: search, cuisine filters, sort and paginated restaurant grid.
import { api } from "../api.js";
import { restaurantCard } from "../components.js";
import { debounce, esc, plural } from "../utils.js";

export async function homeView(root) {
  const filters = { q: "", cuisine: "", veg: false, sort: "rating", page: 1 };

  root.innerHTML = `
    <section class="hero">
      <h1>Hungry? Get it delivered in minutes.</h1>
      <p class="muted">Search restaurants or dishes, build your cart and track your order.</p>
      <div class="search-row">
        <input class="input" id="search" type="search" placeholder="Search restaurants, cuisines or dishes"
               aria-label="Search" data-testid="search-input">
        <select id="sort" aria-label="Sort by" data-testid="sort-select">
          <option value="rating">Top rated</option>
          <option value="delivery">Fastest delivery</option>
          <option value="name">Name A–Z</option>
        </select>
      </div>
    </section>
    <div class="filters" id="filters" data-testid="filters"></div>
    <div id="results"><div class="grid"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div></div>`;

  const resultsEl = root.querySelector("#results");
  const filtersEl = root.querySelector("#filters");
  let cuisines = [];
  let requestId = 0;

  function renderFilters() {
    filtersEl.innerHTML = `
      <button class="chip ${filters.cuisine === "" ? "active" : ""}" data-cuisine="">All</button>
      ${cuisines.map((c) => `<button class="chip ${filters.cuisine === c ? "active" : ""}" data-cuisine="${esc(c)}" data-testid="cuisine-chip">${esc(c)}</button>`).join("")}
      <button class="chip ${filters.veg ? "active" : ""}" id="veg-toggle" data-testid="veg-toggle">🌱 Pure veg</button>`;
  }

  async function load() {
    const current = ++requestId; // ignore out-of-order responses
    try {
      const data = await api.restaurants({ ...filters, page_size: 6 });
      if (current !== requestId) return;
      cuisines = data.cuisines;
      renderFilters();
      if (data.items.length === 0) {
        resultsEl.innerHTML = `<div class="empty" data-testid="empty"><div class="big">🔍</div><p>No restaurants match your search.</p></div>`;
        return;
      }
      const pages = Math.max(1, Math.ceil(data.total / data.page_size));
      resultsEl.innerHTML = `
        <p class="muted" data-testid="result-count">${plural(data.total, "restaurant")} found</p>
        <div class="grid" data-testid="restaurant-grid">${data.items.map(restaurantCard).join("")}</div>
        ${pages > 1 ? `<div class="pager">
          <button class="btn secondary small" id="prev" data-testid="prev-page" ${filters.page <= 1 ? "disabled" : ""}>← Prev</button>
          <span data-testid="page-info">Page ${data.page} of ${pages}</span>
          <button class="btn secondary small" id="next" data-testid="next-page" ${filters.page >= pages ? "disabled" : ""}>Next →</button>
        </div>` : ""}`;
    } catch (err) {
      if (current !== requestId) return;
      resultsEl.innerHTML = `<div class="empty"><div class="big">⚠️</div><p>${esc(err.message)}</p><button class="btn small" id="retry">Retry</button></div>`;
    }
  }

  root.querySelector("#search").addEventListener("input", debounce((e) => {
    filters.q = e.target.value;
    filters.page = 1;
    load();
  }, 250));
  root.querySelector("#sort").addEventListener("change", (e) => {
    filters.sort = e.target.value;
    filters.page = 1;
    load();
  });
  filtersEl.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-cuisine]");
    if (chip) filters.cuisine = chip.dataset.cuisine;
    else if (e.target.closest("#veg-toggle")) filters.veg = !filters.veg;
    else return;
    filters.page = 1;
    load();
  });
  resultsEl.addEventListener("click", (e) => {
    if (e.target.closest("#prev")) { filters.page -= 1; load(); return; }
    if (e.target.closest("#next")) { filters.page += 1; load(); return; }
    if (e.target.closest("#retry")) { load(); return; }
    const card = e.target.closest("[data-testid=restaurant-card]");
    if (card) location.hash = `#/restaurant/${card.dataset.id}`;
  });
  resultsEl.addEventListener("keydown", (e) => {
    const card = e.target.closest("[data-testid=restaurant-card]");
    if (card && e.key === "Enter") location.hash = `#/restaurant/${card.dataset.id}`;
  });

  await load();
}
