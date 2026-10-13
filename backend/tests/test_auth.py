from fastapi.testclient import TestClient

from app.core import permissions as perm
from tests.conftest import TEST_PASSWORD


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_login_returns_token(client: TestClient, make_user) -> None:
    user = make_user(perm.DISPATCHER)
    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_rejects_wrong_password(client: TestClient, make_user) -> None:
    user = make_user(perm.DISPATCHER)
    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_rejects_short_password_with_401(client: TestClient, make_user) -> None:
    """Короткий пароль — це 401, а не 422: політика паролів не має просочуватись."""
    user = make_user(perm.DISPATCHER)
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": "x"})
    assert response.status_code == 401


def test_login_rejects_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": "nobody@chnu.edu.ua", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401


def test_login_rejects_inactive_user(client: TestClient, make_user) -> None:
    user = make_user(perm.DISPATCHER, is_active=False)
    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 403


def test_me_exposes_roles_and_permissions(client: TestClient, auth_headers) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers(perm.DISPATCHER))
    assert response.status_code == 200
    body = response.json()
    assert body["roles"] == [perm.DISPATCHER]
    assert perm.SCHEDULE_OVERRIDE_CONFLICT in body["permissions"]
    assert perm.USERS_MANAGE not in body["permissions"]


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_garbage_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_super_admin_has_every_permission(client: TestClient, auth_headers) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers(perm.SUPER_ADMIN))
    assert set(response.json()["permissions"]) == set(perm.ALL_PERMISSIONS)
