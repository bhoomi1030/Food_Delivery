"""API tests: coupon listing and validation."""


def test_lists_only_active_coupons(client):
    codes = [c["code"] for c in client.get("/api/coupons").json()]
    assert codes == ["FLAT75", "TENOFF", "WELCOME50"]
    assert "EXPIRED20" not in codes


def test_validate_percent_coupon(client):
    r = client.post("/api/coupons/validate", json={"code": "welcome50", "subtotal": 300})
    assert r.status_code == 200
    body = r.json()
    assert body["coupon_code"] == "WELCOME50"
    assert body["discount"] == 100  # 50% of 300 = 150, capped at 100
    assert body["total"] == body["subtotal"] - 100 + body["delivery_fee"] + body["tax"]


def test_validate_flat_coupon(client):
    body = client.post("/api/coupons/validate", json={"code": "FLAT75", "subtotal": 500}).json()
    assert body["discount"] == 75 and body["delivery_fee"] == 0


def test_below_minimum_is_a_business_rule_error(client):
    r = client.post("/api/coupons/validate", json={"code": "WELCOME50", "subtotal": 100})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "business_rule_violation"
    assert "199" in r.json()["error"]["message"]


def test_expired_coupon_is_rejected(client):
    r = client.post("/api/coupons/validate", json={"code": "EXPIRED20", "subtotal": 500})
    assert r.status_code == 422 and "not active" in r.json()["error"]["message"]


def test_unknown_coupon_is_404(client):
    r = client.post("/api/coupons/validate", json={"code": "NOPE", "subtotal": 500})
    assert r.status_code == 404


def test_blank_coupon_is_rejected(client):
    r = client.post("/api/coupons/validate", json={"code": "   ", "subtotal": 500})
    assert r.status_code == 422


def test_negative_subtotal_is_a_validation_error(client):
    r = client.post("/api/coupons/validate", json={"code": "TENOFF", "subtotal": -5})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
