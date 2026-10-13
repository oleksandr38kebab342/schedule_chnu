from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.core import permissions as perm


def _entry_payload(ref, **over):
    payload = {
        "semester_id": ref["semester"],
        "subject_id": ref["subject"],
        "lesson_type_id": ref["lesson_type"],
        "pair_time_id": ref["pair1"],
        "day_of_week": 1,
        "week_parity": "ODD",
        "teacher_ids": [ref["teacher"]],
        "room_ids": [ref["room"]],
        "group_ids": [ref["group1"]],
    }
    payload.update(over)
    return payload


def test_create_entry_without_conflict(client: TestClient, auth_headers, reference):
    r = client.post("/api/v1/schedule", json=_entry_payload(reference), headers=auth_headers(perm.DISPATCHER))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["saved"] is True
    assert body["conflicts"] == []
    assert body["entry"]["group_ids"] == [reference["group1"]]


def test_entry_requires_audience(client: TestClient, auth_headers, reference):
    payload = _entry_payload(reference, group_ids=[], subgroup_ids=[], stream_ids=[])
    r = client.post("/api/v1/schedule", json=payload, headers=auth_headers(perm.DISPATCHER))
    assert r.status_code == 422


def test_student_cannot_create_entry(client: TestClient, auth_headers, reference):
    r = client.post("/api/v1/schedule", json=_entry_payload(reference), headers=auth_headers(perm.STUDENT))
    assert r.status_code == 403


def test_room_conflict_blocks_without_override(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.DISPATCHER)
    first = client.post("/api/v1/schedule", json=_entry_payload(reference), headers=headers)
    assert first.json()["saved"] is True

    # Інша група, та сама аудиторія/день/пара/парність -> ERROR-конфлікт.
    payload = _entry_payload(reference, group_ids=[reference["group2"]])
    second = client.post("/api/v1/schedule", json=payload, headers=headers)
    body = second.json()
    assert body["saved"] is False
    assert body["entry"] is None
    assert any(c["kind"] == "ROOM" and c["severity"] == "ERROR" for c in body["conflicts"])


def test_dispatcher_can_override_with_reason(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.DISPATCHER)
    client.post("/api/v1/schedule", json=_entry_payload(reference), headers=headers)

    payload = _entry_payload(reference, group_ids=[reference["group2"]],
                             override_reason="Погоджено завідувачем кафедри")
    r = client.post("/api/v1/schedule", json=payload, headers=headers)
    body = r.json()
    assert body["saved"] is True
    assert body["overridden"] is True


def test_override_without_permission_is_forbidden(client: TestClient, auth_headers, make_user, reference):
    # teacher має schedule.view, але не create — спершу дамо право create окремій ролі.
    headers = auth_headers(perm.DISPATCHER)
    client.post("/api/v1/schedule", json=_entry_payload(reference), headers=headers)

    # department_admin має schedule.view/export, але не override і не create -> перевіряємо create-гейт.
    dep_headers = auth_headers(perm.DEPARTMENT_ADMIN)
    payload = _entry_payload(reference, group_ids=[reference["group2"]], override_reason="спроба")
    r = client.post("/api/v1/schedule", json=payload, headers=dep_headers)
    assert r.status_code == 403  # немає навіть schedule.create


def test_odd_even_in_same_room_coexist(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.DISPATCHER)
    client.post("/api/v1/schedule", json=_entry_payload(reference, week_parity="ODD"), headers=headers)
    r = client.post(
        "/api/v1/schedule",
        json=_entry_payload(reference, week_parity="EVEN", group_ids=[reference["group2"]]),
        headers=headers,
    )
    assert r.json()["saved"] is True
    assert r.json()["conflicts"] == []


def test_schedule_for_group_lists_entries(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.DISPATCHER)
    client.post("/api/v1/schedule", json=_entry_payload(reference), headers=headers)
    r = client.get(
        f"/api/v1/schedule/group/{reference['group1']}",
        params={"semester_id": reference["semester"]},
        headers=headers,
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_export_returns_valid_xlsx(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.DISPATCHER)
    client.post("/api/v1/schedule", json=_entry_payload(reference), headers=headers)

    r = client.post(
        "/api/v1/export",
        json={"semester_id": reference["semester"], "group_ids": [reference["group1"]]},
        headers=auth_headers(perm.SUPER_ADMIN),
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxml")
    wb = load_workbook(BytesIO(r.content))
    assert "121" in wb.sheetnames


def test_export_rejects_unknown_groups(client: TestClient, auth_headers, reference):
    r = client.post(
        "/api/v1/export",
        json={"semester_id": reference["semester"], "group_ids": [999999]},
        headers=auth_headers(perm.SUPER_ADMIN),
    )
    assert r.status_code == 422
