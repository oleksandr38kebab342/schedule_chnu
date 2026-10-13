from fastapi import APIRouter

from app.api.routes import (
    academic,
    auth,
    calendar,
    departments,
    export,
    facilities,
    faculties,
    schedule,
    teachers,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(faculties.router)
api_router.include_router(departments.router)
api_router.include_router(teachers.router)
api_router.include_router(academic.router)
api_router.include_router(facilities.router)
api_router.include_router(calendar.router)
api_router.include_router(schedule.router)
api_router.include_router(export.router)
