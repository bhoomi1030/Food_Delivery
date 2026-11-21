"""API tests: registration, login, token handling and the error shape."""
import jwt

from backend.seed import DEMO_EMAIL, DEMO_PASSWORD


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "service": "fooddash"}


def test_register_returns_token_and_user(client):
    r = client.post("/api/auth/register", json={"name": "Asha Rao", "email": "Asha@Example.com", "password": "secret123"})
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["user"]["email"] == "asha@example.com"  # normalised
    assert "password" not in str(body).lower()


def test_register_duplicate_email_conflicts(client, auth):
    r = client.post("/api/auth/register", json={"name": "Dup", "email": "TEST@example.com", "password": "password123"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_register_validation_errors_use_standard_shape(client):
    r = client.post("/api/auth/register", json={"name": "A", "email": "nope", "password": "short"})
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "validation_error"
    assert {d["field"] for d in error["details"]} == {"name", "email", "password"}


def test_login_success_and_me(client):
    r = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == DEMO_EMAIL


def test_login_is_case_insensitive_on_email(client):
    r = client.post("/api/auth/login", json={"email": "  DEMO@fooddash.dev ", "password": DEMO_PASSWORD})
    assert r.status_code == 200


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_login_unknown_user_gives_same_message_as_wrong_password(client):
    unknown = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever123"})
    wrong = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": "whatever123"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()  # no user enumeration


def test_me_requires_a_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_garbage_token(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_me_rejects_token_signed_with_another_secret(client):
    forged = jwt.encode({"sub": "1"}, "a-different-secret-key-0123456789abcdef", algorithm="HS256")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_me_rejects_non_bearer_scheme(client, auth):
    token = auth["Authorization"].split()[1]
    assert client.get("/api/auth/me", headers={"Authorization": f"Basic {token}"}).status_code == 401


def test_passwords_are_stored_hashed(client):
    from backend.models import User

    session = client.app.state.session_factory()
    try:
        user = session.query(User).filter_by(email=DEMO_EMAIL).one()
        assert user.password_hash.startswith("pbkdf2_sha256$")
        assert DEMO_PASSWORD not in user.password_hash
    finally:
        session.close()
