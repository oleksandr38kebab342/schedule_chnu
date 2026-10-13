from fastapi.testclient import TestClient

from app.core import permissions as perm
from app.models import natural_key, normalize_room_code


def test_natural_key_sorts_groups_numerically():
    names = ["КН-10", "КН-1", "КН-2"]
    assert sorted(names, key=natural_key) == ["КН-1", "КН-2", "КН-10"]


def test_normalize_room_code_collapses_separators():
    assert normalize_room_code("А.203А") == normalize_room_code("А203А")
    assert normalize_room_code("А.203А") == normalize_room_code("А-203А")
    # Різні кімнати лишаються різними.
    assert normalize_room_code("А.203А") != normalize_room_code("А.203Б")


def test_groups_listed_in_natural_order(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.SUPER_ADMIN)
    for name in ("КН-10", "КН-2", "КН-1"):
        r = client.post(
            "/api/v1/groups",
            json={"department_id": reference["department"], "name": name},
            headers=headers,
        )
        assert r.status_code == 201, r.text
    listed = [g["name"] for g in client.get("/api/v1/groups", headers=headers).json()]
    # 121, 122 з фікстури + нові; перевіряємо саме природний порядок КН-*.
    kn = [n for n in listed if n.startswith("КН")]
    assert kn == ["КН-1", "КН-2", "КН-10"]


def test_room_search_by_alias(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.SUPER_ADMIN)
    r = client.post(
        "/api/v1/rooms",
        json={
            "building_id": reference["building"],
            "number": "Б.101",
            "aliases": ["Б101", "Б-101"],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    # Пошук за іншим написанням знаходить ту саму аудиторію.
    found = client.get("/api/v1/rooms", params={"search": "б-101"}, headers=headers).json()
    assert any(room["number"] == "Б.101" for room in found)


def test_duplicate_room_in_building_rejected(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.SUPER_ADMIN)
    body = {"building_id": reference["building"], "number": "В.1"}
    assert client.post("/api/v1/rooms", json=body, headers=headers).status_code == 201
    # «В1» нормалізується так само -> конфлікт у межах корпусу.
    dup = client.post("/api/v1/rooms", json={**body, "number": "В1"}, headers=headers)
    assert dup.status_code == 409


def test_pair_time_rejects_reversed_interval(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.SUPER_ADMIN)
    r = client.post(
        "/api/v1/times",
        json={"number": 9, "starts_at": "11:00:00", "ends_at": "10:00:00"},
        headers=headers,
    )
    assert r.status_code == 422


def test_teacher_with_departments(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.SUPER_ADMIN)
    r = client.post(
        "/api/v1/teachers",
        json={
            "first_name": "Олена",
            "last_name": "Петренко",
            "department_ids": [reference["department"]],
            "primary_department_id": reference["department"],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["department_ids"] == [reference["department"]]


def test_teacher_rejects_unknown_department(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.SUPER_ADMIN)
    r = client.post(
        "/api/v1/teachers",
        json={"first_name": "X", "last_name": "Y", "department_ids": [999999]},
        headers=headers,
    )
    assert r.status_code == 422


def test_generate_weeks_endpoint(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.SUPER_ADMIN)
    r = client.post(
        f"/api/v1/semesters/{reference['semester']}/generate-weeks", headers=headers
    )
    assert r.status_code == 201, r.text
    weeks = r.json()
    assert weeks[0]["number"] == 1
    assert weeks[0]["parity"] == "ODD"
    assert weeks[1]["parity"] == "EVEN"


def test_week_for_date_endpoint(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.SUPER_ADMIN)
    r = client.get(
        f"/api/v1/semesters/{reference['semester']}/week-for-date",
        params={"day": "2025-09-01"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["number"] == 1
