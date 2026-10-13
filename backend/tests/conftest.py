from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import permissions as perm
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import Base, Permission, Role, User, UserRole

TEST_PASSWORD = "test-password-123"
# bcrypt навмисно повільний, тому хеш рахуємо один раз на весь прогін.
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()

    perms = {code: Permission(code=code, description=text) for code, text in perm.ALL_PERMISSIONS.items()}
    session.add_all(perms.values())
    session.flush()
    for code, spec in perm.ROLES.items():
        session.add(
            Role(
                code=code,
                name=str(spec["name"]),
                permissions=[perms[c] for c in spec["permissions"]],  # type: ignore[union-attr]
            )
        )
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def make_user(db: Session):
    def factory(role_code: str, email: str | None = None, is_active: bool = True) -> User:
        user = User(
            email=email or f"{role_code}@chnu.edu.ua",
            full_name=f"Тест {role_code}",
            password_hash=TEST_PASSWORD_HASH,
            is_active=is_active,
        )
        db.add(user)
        db.flush()
        role = db.scalar(select(Role).where(Role.code == role_code))
        assert role is not None
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        return user

    return factory


@pytest.fixture
def auth_headers(client: TestClient, make_user):
    def factory(role_code: str) -> dict[str, str]:
        user = make_user(role_code)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": TEST_PASSWORD},
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return factory


@pytest.fixture
def reference(db: Session):
    """Мінімальний довідковий набір для тестів розкладу й експорту."""
    from datetime import time

    from app.models import (
        Building,
        Department,
        Faculty,
        Group,
        LessonType,
        PairTime,
        Room,
        Semester,
        Subject,
        Teacher,
        AcademicYear,
    )

    faculty = Faculty(name="ФМІ", code="FMI")
    db.add(faculty)
    db.flush()
    dept = Department(faculty_id=faculty.id, name="ПЗ", code="PZ")
    db.add(dept)
    db.flush()

    year = AcademicYear(name="2025/2026", starts_on=__import__("datetime").date(2025, 9, 1),
                        ends_on=__import__("datetime").date(2026, 6, 30))
    db.add(year)
    db.flush()
    sem = Semester(academic_year_id=year.id, ordinal=1, name="I семестр",
                   start_date=__import__("datetime").date(2025, 9, 1),
                   end_date=__import__("datetime").date(2025, 12, 28))
    db.add(sem)

    g1 = Group(department_id=dept.id, name="121")
    g2 = Group(department_id=dept.id, name="122")
    subj = Subject(name="Математичний аналіз", code="MA")
    lt = LessonType(code="LEC", name="Лекція", short_name="Лк")
    building = Building(name="Головний", code="A")
    db.add_all([g1, g2, subj, lt, building])
    db.flush()
    room = Room(building_id=building.id, number="А.203", normalized="а203")
    t1 = Teacher(first_name="Іван", last_name="Іваненко", short_name="Іваненко І.")
    p1 = PairTime(number=1, starts_at=time(8, 20), ends_at=time(9, 40))
    p2 = PairTime(number=2, starts_at=time(9, 50), ends_at=time(11, 10))
    db.add_all([room, t1, p1, p2])
    db.commit()

    return {
        "faculty": faculty.id, "department": dept.id, "semester": sem.id,
        "group1": g1.id, "group2": g2.id, "subject": subj.id, "lesson_type": lt.id,
        "building": building.id, "room": room.id, "teacher": t1.id,
        "pair1": p1.id, "pair2": p2.id,
    }
