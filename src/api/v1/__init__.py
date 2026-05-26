from fastapi import APIRouter

from src.api.v1.employees import router as employees_router
from src.api.v1.groups import router as groups_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(employees_router)
v1_router.include_router(groups_router)
