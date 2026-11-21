"""API tests: quoting, placing, idempotency, authorization and the order lifecycle."""
import pytest


def place(client, auth, payload, key=None):
    headers = dict(auth)
    if key:
        headers["Idempotency-Key"] = key
    return client.post("/api/orders", json=payload, headers=headers)


# ---------- quote ----------
def test_quote_is_public_and_matches_pricing_rules(client, order_payload):
    payload = {k: order_payload[k] for k in ("restaurant_id", "items")}
    r = client.post("/api/orders/quote", json=payload)
    assert r.status_code == 200
    # 2 x 49 = 98 -> +40 delivery, 5 tax (4.9 rounded)
    assert r.json() == {"subtotal": 98, "discount": 0, "delivery_fee": 40, "tax": 5, "total": 143, "coupon_code": None}


def test_quote_with_coupon(client, menu):
    payload = {
        "restaurant_id": menu["restaurant_id"], "coupon_code": "WELCOME50",
        "items": [{"menu_item_id": menu["items"]["Butter Chicken"]["id"], "quantity": 1}],
    }
    body = client.post("/api/orders/quote", json=payload).json()
    assert body["subtotal"] == 329 and body["discount"] == 100 and body["coupon_code"] == "WELCOME50"


def test_quote_merges_duplicate_lines(client, menu):
    naan = menu["items"]["Butter Naan"]["id"]
    payload = {"restaurant_id": 1, "items": [{"menu_item_id": naan, "quantity": 2}, {"menu_item_id": naan, "quantity": 3}]}
    assert client.post("/api/orders/quote", json=payload).json()["subtotal"] == 245


def test_quote_rejects_coupon_below_minimum(client, order_payload):
    payload = {"restaurant_id": 1, "items": order_payload["items"], "coupon_code": "WELCOME50"}
    assert client.post("/api/orders/quote", json=payload).status_code == 422


def test_quote_rejects_item_from_another_restaurant(client, menu):
    pizza = client.get("/api/restaurants/2").json()["menu"][0]["id"]
    payload = {"restaurant_id": 1, "items": [{"menu_item_id": pizza, "quantity": 1}]}
    r = client.post("/api/orders/quote", json=payload)
    assert r.status_code == 422 and "does not belong" in r.json()["error"]["message"]


def test_quote_unknown_restaurant(client):
    payload = {"restaurant_id": 999, "items": [{"menu_item_id": 1, "quantity": 1}]}
    assert client.post("/api/orders/quote", json=payload).status_code == 404


@pytest.mark.parametrize("items", [[], [{"menu_item_id": 1, "quantity": 0}], [{"menu_item_id": 1, "quantity": 11}]])
def test_quote_validates_items(client, items):
    r = client.post("/api/orders/quote", json={"restaurant_id": 1, "items": items})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_quote_caps_merged_quantity_at_ten(client, menu):
    naan = menu["items"]["Butter Naan"]["id"]
    items = [{"menu_item_id": naan, "quantity": 6}, {"menu_item_id": naan, "quantity": 6}]
    r = client.post("/api/orders/quote", json={"restaurant_id": 1, "items": items})
    assert r.status_code == 422 and "at most 10" in r.json()["error"]["message"]


def test_closed_restaurant_cannot_be_ordered_from(client, order_payload):
    from backend.models import Restaurant

    session = client.app.state.session_factory()
    session.get(Restaurant, 1).is_open = False
    session.commit()
    session.close()
    r = client.post("/api/orders/quote", json={"restaurant_id": 1, "items": order_payload["items"]})
    assert r.status_code == 422 and "closed" in r.json()["error"]["message"]


def test_unavailable_item_cannot_be_ordered(client, order_payload):
    from backend.models import MenuItem

    session = client.app.state.session_factory()
    session.get(MenuItem, order_payload["items"][0]["menu_item_id"]).is_available = False
    session.commit()
    session.close()
    r = client.post("/api/orders/quote", json={"restaurant_id": 1, "items": order_payload["items"]})
    assert r.status_code == 422 and "unavailable" in r.json()["error"]["message"]


# ---------- placing ----------
def test_place_order_requires_authentication(client, order_payload):
    assert client.post("/api/orders", json=order_payload).status_code == 401


def test_place_order_snapshots_prices_and_starts_placed(client, auth, order_payload):
    r = place(client, auth, order_payload)
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "PLACED" and order["total"] == 143
    assert order["restaurant_name"] == "Spice Route"
    assert order["items"] == [{"menu_item_id": order_payload["items"][0]["menu_item_id"], "name": "Butter Naan", "unit_price": 49, "quantity": 2}]
    assert order["can_cancel"] is True and order["next_status"] == "CONFIRMED"


def test_place_order_with_coupon_records_discount(client, auth, menu):
    payload = {
        "restaurant_id": 1, "coupon_code": "tenoff", "delivery_address": "12 MG Road, Bengaluru",
        "items": [{"menu_item_id": menu["items"]["Dal Makhani"]["id"], "quantity": 2}],
    }
    order = place(client, auth, payload).json()
    assert order["coupon_code"] == "TENOFF" and order["discount"] == 44  # 10% of 438


def test_place_order_validates_address(client, auth, order_payload):
    order_payload["delivery_address"] = "short"
    r = place(client, auth, order_payload)
    assert r.status_code == 422 and "delivery_address" in r.json()["error"]["message"]


def test_later_price_changes_do_not_alter_existing_orders(client, auth, order_payload):
    from backend.models import MenuItem

    order_id = place(client, auth, order_payload).json()["id"]
    session = client.app.state.session_factory()
    session.get(MenuItem, order_payload["items"][0]["menu_item_id"]).price = 999
    session.commit()
    session.close()
    stored = client.get(f"/api/orders/{order_id}", headers=auth).json()
    assert stored["items"][0]["unit_price"] == 49 and stored["total"] == 143


# ---------- idempotency ----------
def test_same_idempotency_key_replays_the_original_order(client, auth, order_payload):
    first = place(client, auth, order_payload, key="abc-123")
    second = place(client, auth, order_payload, key="abc-123")
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert client.get("/api/orders", headers=auth).json()["total"] == 1


def test_different_keys_create_different_orders(client, auth, order_payload):
    a = place(client, auth, order_payload, key="k1").json()["id"]
    b = place(client, auth, order_payload, key="k2").json()["id"]
    assert a != b


def test_idempotency_keys_are_scoped_per_user(client, auth, other_auth, order_payload):
    a = place(client, auth, order_payload, key="shared")
    b = place(client, other_auth, order_payload, key="shared")
    assert a.status_code == b.status_code == 201 and a.json()["id"] != b.json()["id"]


def test_without_a_key_every_request_creates_an_order(client, auth, order_payload):
    place(client, auth, order_payload)
    place(client, auth, order_payload)
    assert client.get("/api/orders", headers=auth).json()["total"] == 2


# ---------- reading & authorization ----------
def test_orders_list_requires_authentication(client):
    assert client.get("/api/orders").status_code == 401


def test_list_is_newest_first_and_paginated(client, auth, order_payload):
    ids = [place(client, auth, order_payload).json()["id"] for _ in range(3)]
    body = client.get("/api/orders?page_size=2", headers=auth).json()
    assert body["total"] == 3 and [o["id"] for o in body["items"]] == [ids[2], ids[1]]
    page2 = client.get("/api/orders?page_size=2&page=2", headers=auth).json()
    assert [o["id"] for o in page2["items"]] == [ids[0]]


def test_users_only_see_their_own_orders(client, auth, other_auth, order_payload):
    place(client, auth, order_payload)
    assert client.get("/api/orders", headers=other_auth).json()["total"] == 0


def test_cannot_read_someone_elses_order(client, auth, other_auth, order_payload):
    order_id = place(client, auth, order_payload).json()["id"]
    r = client.get(f"/api/orders/{order_id}", headers=other_auth)
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"


def test_cannot_cancel_or_advance_someone_elses_order(client, auth, other_auth, order_payload):
    order_id = place(client, auth, order_payload).json()["id"]
    assert client.post(f"/api/orders/{order_id}/cancel", headers=other_auth).status_code == 403
    assert client.post(f"/api/orders/{order_id}/advance", headers=other_auth).status_code == 403
    assert client.get(f"/api/orders/{order_id}", headers=auth).json()["status"] == "PLACED"


def test_unknown_order_is_404(client, auth):
    assert client.get("/api/orders/9999", headers=auth).status_code == 404


# ---------- lifecycle ----------
def test_cancel_a_placed_order(client, auth, order_payload):
    order_id = place(client, auth, order_payload).json()["id"]
    r = client.post(f"/api/orders/{order_id}/cancel", headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED" and r.json()["can_cancel"] is False and r.json()["next_status"] is None


def test_cancelling_twice_fails(client, auth, order_payload):
    order_id = place(client, auth, order_payload).json()["id"]
    client.post(f"/api/orders/{order_id}/cancel", headers=auth)
    assert client.post(f"/api/orders/{order_id}/cancel", headers=auth).status_code == 422


def test_advance_walks_the_order_to_delivered(client, auth, order_payload):
    order_id = place(client, auth, order_payload).json()["id"]
    statuses = [client.post(f"/api/orders/{order_id}/advance", headers=auth).json()["status"] for _ in range(4)]
    assert statuses == ["CONFIRMED", "PREPARING", "OUT_FOR_DELIVERY", "DELIVERED"]
    r = client.post(f"/api/orders/{order_id}/advance", headers=auth)
    assert r.status_code == 422 and "cannot move further" in r.json()["error"]["message"]


def test_cannot_cancel_once_preparing(client, auth, order_payload):
    order_id = place(client, auth, order_payload).json()["id"]
    client.post(f"/api/orders/{order_id}/advance", headers=auth)  # CONFIRMED is still cancellable
    assert client.get(f"/api/orders/{order_id}", headers=auth).json()["can_cancel"] is True
    client.post(f"/api/orders/{order_id}/advance", headers=auth)  # -> PREPARING
    r = client.post(f"/api/orders/{order_id}/cancel", headers=auth)
    assert r.status_code == 422 and "Cannot move" in r.json()["error"]["message"]


def test_cannot_advance_a_cancelled_order(client, auth, order_payload):
    order_id = place(client, auth, order_payload).json()["id"]
    client.post(f"/api/orders/{order_id}/cancel", headers=auth)
    assert client.post(f"/api/orders/{order_id}/advance", headers=auth).status_code == 422


def test_demo_user_can_order_end_to_end(client, demo_auth, order_payload):
    assert place(client, demo_auth, order_payload).status_code == 201
