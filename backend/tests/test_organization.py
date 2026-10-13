from fastapi.testclient import TestClient

from app.core import permissions as perm
from tests.conftest import TEST_PASSWORD

FACULTY = {"name": "Факультет математики та інформатики", "code": "FMI", "short_name": "ФМІ"}


def _create_faculty(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    payload = {**FACULTY, **overrides}
    response = client.post("/api/v1/faculties", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_dispatcher_cannot_manage_faculties(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/faculties", json=FACULTY, headers=auth_headers(perm.DISPATCHER)
    )
    assert response.status_code == 403
    assert perm.FACULTY_MANAGE in response.json()["detail"]


def test_faculty_write_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/v1/faculties", json=FACULTY).status_code == 401


def test_faculty_crud_cycle(client: TestClient, auth_headers) -> None:
    headers = auth_headers(perm.SUPER_ADMIN)
    created = _create_faculty(client, headers)
    assert created["is_active"] is True

    listed = client.get("/api/v1/faculties", headers=headers).json()
    assert [f["code"] for f in listed] == ["FMI"]

    patched = client.patch(
        f"/api/v1/faculties/{created['id']}", json={"is_active": False}, headers=headers
    )
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False

    assert client.delete(f"/api/v1/faculties/{created['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/faculties/{created['id']}", headers=headers).status_code == 404


def test_faculty_code_must_be_unique(client: TestClient, auth_headers) -> None:
    headers = auth_headers(perm.SUPER_ADMIN)
    _create_faculty(client, headers)
    duplicate = client.post("/api/v1/faculties", json=FACULTY, headers=headers)
    assert duplicate.status_code == 409


def test_any_authenticated_user_can_read_faculties(
    client: TestClient, auth_headers, make_user
) -> None:
    _create_faculty(client, auth_headers(perm.SUPER_ADMIN))
    student = make_user(perm.STUDENT)
    login = client.post(
        "/api/v1/auth/login", json={"email": student.email, "password": TEST_PASSWORD}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/faculties", headers=headers).status_code == 200


def test_department_requires_existing_faculty(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/departments",
        json={"faculty_id": 999, "name": "Кафедра ПЗ", "code": "PZ"},
        headers=auth_headers(perm.SUPER_ADMIN),
    )
    assert response.status_code == 422


def test_departments_filtered_by_faculty(client: TestClient, auth_headers) -> None:
    headers = auth_headers(perm.SUPER_ADMIN)
    first = _create_faculty(client, headers)
    second = _create_faculty(client, headers, code="FIZ", name="Фізичний факультет")

    for faculty_id, code in ((first["id"], "PZ"), (first["id"], "MAT"), (second["id"], "FIZ-1")):
        created = client.post(
            "/api/v1/departments",
            json={"faculty_id": faculty_id, "name": f"Кафедра {code}", "code": code},
            headers=headers,
        )
        assert created.status_code == 201, created.text

    filtered = client.get(
        "/api/v1/departments", params={"faculty_id": first["id"]}, headers=headers
    ).json()
    assert sorted(d["code"] for d in filtered) == ["MAT", "PZ"]


def test_department_cannot_be_its_own_parent(client: TestClient, auth_headers) -> None:
    headers = auth_headers(perm.SUPER_ADMIN)
    faculty = _create_faculty(client, headers)
    department = client.post(
        "/api/v1/departments",
        json={"faculty_id": faculty["id"], "name": "Кафедра ПЗ", "code": "PZ"},
        headers=headers,
    ).json()

    response = client.patch(
        f"/api/v1/departments/{department['id']}",
        json={"parent_id": department["id"]},
        headers=headers,
    )
    assert response.status_code == 422


def test_department_admin_cannot_manage_faculties(client: TestClient, auth_headers) -> None:
    headers = auth_headers(perm.DEPARTMENT_ADMIN)
    assert client.post("/api/v1/faculties", json=FACULTY, headers=headers).status_code == 403
