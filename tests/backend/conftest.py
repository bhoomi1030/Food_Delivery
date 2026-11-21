"""Shared fixtures: every test gets a fresh in-memory app with seeded data."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from backend.seed import DEMO_EMAIL, DEMO_PASSWORD


@pytest.fixture()
def client():
    settings = Settings(database_url="sqlite:///:memory:", password_iterations=1000)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _register(client, name="Test User", email="test@example.com", password="password123"):
    response = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    """Authorization headers for a freshly registered user."""
    return _register(client)


@pytest.fixture()
def other_auth(client):
    """Authorization headers for a second, different user."""
    return _register(client, name="Other User", email="other@example.com")


@pytest.fixture()
def demo_auth(client):
    response = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def menu(client):
    """Restaurant 1 (Spice Route) with its menu keyed by item name."""
    detail = client.get("/api/restaurants/1").json()
    return {"restaurant_id": detail["id"], "items": {i["name"]: i for i in detail["menu"]}}


@pytest.fixture()
def order_payload(menu):
    """A valid order: 2 x Butter Naan (₹98 subtotal)."""
    return {
        "restaurant_id": menu["restaurant_id"],
        "items": [{"menu_item_id": menu["items"]["Butter Naan"]["id"], "quantity": 2}],
        "delivery_address": "12 MG Road, Bengaluru",
    }
