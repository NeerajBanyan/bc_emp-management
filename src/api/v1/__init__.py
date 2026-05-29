from fastapi import APIRouter

from src.api.v1.employees import router as employees_router
from src.api.v1.groups import router as groups_router

v1_router = APIRouter(prefix="/api/v1") #adds /api/v1 to every URL
v1_router.include_router(employees_router) #plugs in /employees routes
v1_router.include_router(groups_router) #plugs in /groups routes
