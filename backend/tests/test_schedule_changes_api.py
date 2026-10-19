"""Редагування занять, точкові зміни (заміна/перенесення/скасування) і аудит."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import permissions as perm
from app.models import AuditLog, Teacher

MONDAY_ODD = date(2025, 9, 1)
WEDNESDAY_ODD = date(2025, 9, 3)


def _entry_payload(ref, **over):
    payload = {
        "semester_id": ref["semester"],
        "subject_id": ref["subject"],
        "lesson_type_id": ref["lesson_type"],
        "pair_time_id": ref["pair1"],
        "day_of_week": 1,
        "week_parity": "BOTH",
        "teacher_ids": [ref["teacher"]],
        "room_ids": [ref["room"]],
        "group_ids": [ref["group1"]],
    }
    payload.update(over)
    return payload


def _create(client: TestClient, ref, headers, **over) -> int:
    response = client.post("/api/v1/schedule", json=_entry_payload(ref, **over), headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["entry"]["id"]


def test_dispatcher_edits_entry(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.DISPATCHER)
    entry_id = _create(client, reference, headers)

    response = client.put(
        f"/api/v1/schedule/{entry_id}",
        json=_entry_payload(reference, pair_time_id=reference["pair2"], day_of_week=2),
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["saved"] is True
    assert body["entry"]["pair_time_id"] == reference["pair2"]
    assert body["entry"]["day_of_week"] == 2


def test_edit_into_conflict_is_blocked_then_overridden(
    client: TestClient, auth_headers, reference
):
    headers = auth_headers(perm.DISPATCHER)
    _create(client, reference, headers)  # пара 1, понеділок, та сама аудиторія
    movable = _create(client, reference, headers, pair_time_id=reference["pair2"],
                      group_ids=[reference["group2"]])

    clash = _entry_payload(
        reference, pair_time_id=reference["pair1"], group_ids=[reference["group2"]]
    )
    blocked = client.put(f"/api/v1/schedule/{movable}", json=clash, headers=headers)
    assert blocked.status_code == 200
    assert blocked.json()["saved"] is False
    assert any(c["kind"] == "ROOM" for c in blocked.json()["conflicts"])

    # Правка не застосувалася: заняття лишилось на парі 2.
    unchanged = client.get(f"/api/v1/schedule/{movable}", headers=headers).json()
    assert unchanged["pair_time_id"] == reference["pair2"]

    forced = client.put(
        f"/api/v1/schedule/{movable}",
        json={**clash, "override_reason": "Дозвіл декана, аудиторія ділиться"},
        headers=headers,
    )
    assert forced.json()["saved"] is True
    assert forced.json()["overridden"] is True


def test_student_cannot_edit_entry(client: TestClient, auth_headers, reference):
    entry_id = _create(client, reference, auth_headers(perm.DISPATCHER))
    response = client.put(
        f"/api/v1/schedule/{entry_id}",
        json=_entry_payload(reference),
        headers=auth_headers(perm.STUDENT),
    )
    assert response.status_code == 403


def test_cancel_shows_in_public_view(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.DISPATCHER)
    entry_id = _create(client, reference, headers)

    created = client.post(
        f"/api/v1/schedule/{entry_id}/exceptions",
        json={"action": "CANCEL", "on_date": MONDAY_ODD.isoformat(), "reason": "Карантин"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    day = client.get(
        f"/api/v1/public/schedule/group/{reference['group1']}/day",
        params={"date": MONDAY_ODD.isoformat()},
    ).json()
    assert day["lessons"][0]["status"] == "CANCELLED"
    assert day["lessons"][0]["change_reason"] == "Карантин"


def test_replacement_requires_target_and_shows_substitute(
    client: TestClient, db: Session, auth_headers, reference
):
    headers = auth_headers(perm.DISPATCHER)
    entry_id = _create(client, reference, headers)

    empty = client.post(
        f"/api/v1/schedule/{entry_id}/exceptions",
        json={"action": "REPLACE", "on_date": MONDAY_ODD.isoformat()},
        headers=headers,
    )
    assert empty.status_code == 422

    substitute = Teacher(first_name="Олена", last_name="Петренко", short_name="Петренко О.")
    db.add(substitute)
    db.commit()

    created = client.post(
        f"/api/v1/schedule/{entry_id}/exceptions",
        json={
            "action": "REPLACE",
            "on_date": MONDAY_ODD.isoformat(),
            "new_teacher_id": substitute.id,
            "reason": "Лікарняний",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    day = client.get(
        f"/api/v1/public/schedule/group/{reference['group1']}/day",
        params={"date": MONDAY_ODD.isoformat()},
    ).json()
    lesson = day["lessons"][0]
    assert lesson["status"] == "REPLACED"
    assert lesson["teachers"][0]["short_name"] == "Петренко О."
    assert lesson["teachers"][0]["is_substitute"] is True


def test_move_requires_new_slot(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.DISPATCHER)
    entry_id = _create(client, reference, headers)

    response = client.post(
        f"/api/v1/schedule/{entry_id}/exceptions",
        json={"action": "MOVE", "on_date": MONDAY_ODD.isoformat()},
        headers=headers,
    )
    assert response.status_code == 422


def test_teacher_cannot_cancel_lesson(client: TestClient, auth_headers, reference):
    entry_id = _create(client, reference, auth_headers(perm.DISPATCHER))
    response = client.post(
        f"/api/v1/schedule/{entry_id}/exceptions",
        json={"action": "CANCEL", "on_date": MONDAY_ODD.isoformat()},
        headers=auth_headers(perm.TEACHER),
    )
    assert response.status_code == 403
    assert "schedule.cancel" in response.json()["detail"]


def test_deleting_exception_restores_lesson(client: TestClient, auth_headers, reference):
    headers = auth_headers(perm.DISPATCHER)
    entry_id = _create(client, reference, headers)
    exception_id = client.post(
        f"/api/v1/schedule/{entry_id}/exceptions",
        json={"action": "CANCEL", "on_date": MONDAY_ODD.isoformat()},
        headers=headers,
    ).json()["id"]

    listed = client.get(f"/api/v1/schedule/{entry_id}/exceptions", headers=headers).json()
    assert [e["id"] for e in listed] == [exception_id]

    deleted = client.delete(f"/api/v1/schedule/exceptions/{exception_id}", headers=headers)
    assert deleted.status_code == 204

    day = client.get(
        f"/api/v1/public/schedule/group/{reference['group1']}/day",
        params={"date": MONDAY_ODD.isoformat()},
    ).json()
    assert day["lessons"][0]["status"] == "NORMAL"


def test_changes_are_written_to_audit_log(
    client: TestClient, db: Session, auth_headers, reference
):
    headers = auth_headers(perm.DISPATCHER)
    entry_id = _create(client, reference, headers)
    client.post(
        f"/api/v1/schedule/{entry_id}/exceptions",
        json={"action": "CANCEL", "on_date": MONDAY_ODD.isoformat(), "reason": "Карантин"},
        headers=headers,
    )

    actions = [log.action for log in db.scalars(select(AuditLog))]
    assert "schedule.create" in actions
    assert "schedule.exception.cancel" in actions


def test_audit_endpoint_needs_permission(client: TestClient, auth_headers, reference):
    dispatcher = auth_headers(perm.DISPATCHER)
    _create(client, reference, dispatcher)

    assert client.get("/api/v1/audit", headers=dispatcher).status_code == 403

    admin = client.get("/api/v1/audit", headers=auth_headers(perm.SUPER_ADMIN))
    assert admin.status_code == 200
    body = admin.json()
    assert body[0]["action"] == "schedule.create"
    assert body[0]["user_email"] == "dispatcher@chnu.edu.ua"
