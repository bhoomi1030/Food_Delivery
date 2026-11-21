# FoodDash 🍽️

A Swiggy/Zomato-style food delivery app: browse restaurants, build a cart, apply coupons, sign up, place an order and track it through its lifecycle.

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, SQLite, JWT auth
- **Frontend:** vanilla JavaScript (ES modules, hash router, no build step)
- **Tests:** pytest for unit and API tests, Playwright (driving Google Chrome) for browser tests

## Run it

```bash
make install        # creates .venv and installs dependencies
make run            # http://localhost:8000  (API docs: /docs)
```

No `make`? Use:

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/uvicorn backend.main:app --port 8000
```

Demo login: `demo@fooddash.dev` / `demo12345`. 8 restaurants and 4 coupons (`WELCOME50`, `FLAT75`, `TENOFF`, and the inactive `EXPIRED20`) are seeded on first start.

## Test it

```bash
make test        # everything
make test-api    # unit + API tests (fast, in-memory SQLite)
make test-e2e    # browser tests (needs Google Chrome installed)
```

The browser tests start a real uvicorn server on a temporary database and drive Chrome headlessly, so they exercise the full stack: UI → HTTP → API → database.

## Project layout

```
backend/
  main.py          app factory: wires settings, DB, routers, static UI
  config.py        settings + business-rule constants
  database.py      engine / session setup
  models.py        SQLAlchemy models
  schemas.py       Pydantic request/response contract
  security.py      PBKDF2 password hashing, JWT creation/verification
  exceptions.py    domain errors + one consistent error shape
  seed.py          demo restaurants, menus, coupons, demo user
  routers/         HTTP layer: auth, restaurants, coupons, orders
  services/
    pricing.py     pure pricing logic (coupons, delivery fee, tax)
    order_state.py order lifecycle state machine
    orders.py      order use-cases (quote, place, cancel, advance)
frontend/
  index.html       app shell
  css/styles.css
  js/              app (router), api client, store, cart, components, utils
  js/views/        home, restaurant, checkout, orders, auth
tests/
  backend/         pricing, state machine, auth, restaurants, coupons, orders
  e2e/             Playwright customer-journey tests
```

Layering is routers → services → models. Pricing and the order state machine are pure functions with no database access, which keeps them easy to unit test.

## Design decisions

- **Money is integer rupees.** Percentages use round-half-up integer maths, so totals never drift the way floats do.
- **Pricing is server-side.** The client sends item ids and quantities; the server prices them from the live menu. Order lines snapshot name and price at order time, so later menu changes do not alter past orders.
- **Idempotent order placement.** Send an `Idempotency-Key` header; a retry returns the original order (`200`) instead of creating a duplicate (`201`). Keys are scoped per user.
- **Explicit order state machine.** `PLACED → CONFIRMED → PREPARING → OUT_FOR_DELIVERY → DELIVERED`. Cancellation is only allowed from `PLACED` or `CONFIRMED`. Illegal moves return `422`.
- **Authorization.** Users can only read, cancel or advance their own orders (`403` otherwise).
- **One error shape:** `{"error": {"code", "message", "details?"}}` for every failure, including validation errors.
- **No user enumeration.** Unknown email and wrong password return the identical `401`.

### Pricing rules

| Rule | Value |
| --- | --- |
| Tax | 5% of (subtotal − discount) |
| Delivery fee | ₹40, free when subtotal ≥ ₹499 |
| `WELCOME50` | 50% off, max ₹100, min order ₹199 |
| `FLAT75` | ₹75 off, min order ₹399 |
| `TENOFF` | 10% off, max ₹60 |
| Limits | max 10 per item, one restaurant per cart |

## API

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/health` | – | Health check |
| POST | `/api/auth/register` | – | Create account, returns JWT |
| POST | `/api/auth/login` | – | Log in, returns JWT |
| GET | `/api/auth/me` | ✔ | Current user |
| GET | `/api/restaurants` | – | Search / filter / sort / paginate (`q`, `cuisine`, `veg`, `sort`, `page`, `page_size`) |
| GET | `/api/restaurants/{id}` | – | Restaurant with menu |
| GET | `/api/coupons` | – | Active coupons |
| POST | `/api/coupons/validate` | – | Price a subtotal with a coupon |
| POST | `/api/orders/quote` | – | Price a cart without creating an order |
| POST | `/api/orders` | ✔ | Place an order (`Idempotency-Key` header supported) |
| GET | `/api/orders` | ✔ | My orders, newest first, paginated |
| GET | `/api/orders/{id}` | ✔ | One of my orders |
| POST | `/api/orders/{id}/cancel` | ✔ | Cancel (only while `PLACED` / `CONFIRMED`) |
| POST | `/api/orders/{id}/advance` | ✔ | Demo helper: move to the next status |

Interactive docs are generated at `/docs`.

## Scope and known limitations

This is a portfolio project, not a production service.

- **No real payments.** Checkout does not take payment.
- **No real kitchen or rider apps.** The "Simulate" button on the orders page stands in for them by calling `/advance`. In production that endpoint would be restricted to restaurant/rider roles.
- **SQLite** is used for zero-setup; the SQLAlchemy layer would allow PostgreSQL by changing `FOODDASH_DATABASE_URL` (not tested against PostgreSQL).
- Set `FOODDASH_SECRET_KEY` to a strong random value outside local development.
- Auth tokens are kept in `localStorage`, which is simple but exposed to XSS; the frontend escapes user-provided text before rendering it.
