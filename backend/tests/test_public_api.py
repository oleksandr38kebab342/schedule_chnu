"""Публічний перегляд розкладу: без входу, але тільки читання."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Group, Parity, RoomAlias, ScheduleEntry, ScheduleGroup, ScheduleRoom

MONDAY_ODD = date(2025, 9, 1)


@pytest.fixture
def lesson(db: Session, reference) -> ScheduleEntry:
    entry = ScheduleEntry(
        semester_id=reference["semester"],
        subject_id=reference["subject"],
        lesson_type_id=reference["lesson_type"],
        pair_time_id=reference["pair1"],
        day_of_week=1,
        week_parity=Parity.BOTH,
    )
    entry.groups = [ScheduleGroup(group_id=reference["group1"])]
    entry.rooms = [ScheduleRoom(room_id=reference["room"])]
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def test_schedule_is_readable_without_login(client: TestClient, reference, lesson):
    response = client.get(
        f"/api/v1/public/schedule/group/{reference['group1']}/day",
        params={"date": MONDAY_ODD.isoformat()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["week_number"] == 1
    assert body["parity"] == "ODD"
    assert len(body["lessons"]) == 1
    assert body["lessons"][0]["subject_name"] == "Математичний аналіз"


def test_week_endpoint_returns_workdays(client: TestClient, reference, lesson):
    body = client.get(
        f"/api/v1/public/schedule/group/{reference['group1']}/week",
        params={"date": MONDAY_ODD.isoformat()},
    ).json()
    assert [d["day_of_week"] for d in body["days"]] == [1, 2, 3, 4, 5]
    assert sum(len(d["lessons"]) for d in body["days"]) == 1


def test_groups_are_sorted_naturally(client: TestClient, db: Session, reference):
    department_id = reference["department"]
    db.add_all(
        [
            Group(department_id=department_id, name="КН-10"),
            Group(department_id=department_id, name="КН-2"),
            Group(department_id=department_id, name="КН-1"),
        ]
    )
    db.commit()

    names = [g["name"] for g in client.get("/api/v1/public/groups").json()]
    assert names.index("КН-1") < names.index("КН-2") < names.index("КН-10")


def test_group_search_and_faculty_name(client: TestClient, reference):
    body = client.get("/api/v1/public/groups", params={"search": "121"}).json()
    assert [g["name"] for g in body] == ["121"]
    assert body[0]["faculty_name"] == "ФМІ"
    assert body[0]["department_name"] == "ПЗ"


def test_room_search_ignores_separators(client: TestClient, db: Session, reference):
    db.add(RoomAlias(room_id=reference["room"], alias="А203", normalized="а203"))
    db.commit()

    for query in ("А.203", "а203", "А-203"):
        found = client.get("/api/v1/public/rooms", params={"search": query}).json()
        assert [r["number"] for r in found] == ["А.203"], query


def test_calendar_reports_week_and_parity(client: TestClient, reference):
    body = client.get("/api/v1/public/calendar", params={"date": "2025-09-08"}).json()
    assert body["week_number"] == 2
    assert body["parity"] == "EVEN"
    assert body["semester_name"] == "I семестр"
    assert body["week_starts_on"] == "2025-09-08"


def test_unknown_group_gives_404(client: TestClient, reference):
    response = client.get("/api/v1/public/schedule/group/9999/day")
    assert response.status_code == 404


def test_public_access_can_be_switched_off(client: TestClient, reference, monkeypatch):
    monkeypatch.setattr(settings, "public_schedule_enabled", False)
    response = client.get(f"/api/v1/public/schedule/group/{reference['group1']}/day")
    assert response.status_code == 403
    assert "вимкнено" in response.json()["detail"]


def test_public_router_is_read_only(client: TestClient, reference):
    # Публічний роутер не має жодного методу запису.
    from app.main import app

    public_paths = {p: m for p, m in app.openapi()["paths"].items() if "/public/" in p}
    assert public_paths
    for path, methods in public_paths.items():
        assert set(methods) == {"get"}, path
