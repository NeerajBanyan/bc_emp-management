from datetime import date
from typing import List, Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query, status

from src.core.database import get_db
from src.core.redis import cache_delete_pattern, cache_get, cache_set
from src.schemas.employee import (
    CreateAndAssignGroupRequest,
    DepartmentCount,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeStatus,
    EmployeeUpdate,
    GroupSummary,
    PaginatedEmployees,
)
from src.services import employee_service

router = APIRouter(prefix="/employees", tags=["Employees"])

EMPLOYEE_CACHE_KEY = "employee:{id}"
EMPLOYEES_LIST_PATTERN = "employees:list:*"
DEPT_COUNT_KEY = "employees:department_counts"


def _list_cache_key(page, limit, sort_by, sort_order, status, department) -> str:
    return f"employees:list:{page}:{limit}:{sort_by}:{sort_order}:{status}:{department}"


async def _invalidate_caches(employee_id: Optional[UUID] = None) -> None:
    if employee_id:
        await cache_delete_pattern(EMPLOYEE_CACHE_KEY.format(id=employee_id))
    await cache_delete_pattern(EMPLOYEES_LIST_PATTERN)
    await cache_delete_pattern(DEPT_COUNT_KEY)


# ---------- List employees ----------

@router.get("", response_model=PaginatedEmployees)
async def list_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at", pattern="^(first_name|last_name|joining_date|created_at)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    status: Optional[EmployeeStatus] = Query(None),
    department: Optional[str] = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
):
    cache_key = _list_cache_key(page, limit, sort_by, sort_order, status, department)
    cached = await cache_get(cache_key)
    if cached:
        return cached

    total, employees = await employee_service.list_employees(
        conn, page, limit, sort_by, sort_order,
        status.value if status else None, department,
    )
    response = PaginatedEmployees(
        total=total, page=page, limit=limit,
        items=[EmployeeResponse(**e) for e in employees],
    )
    await cache_set(cache_key, response.model_dump())
    return response


# ---------- Department counts (Query 3) ----------

@router.get("/department-counts", response_model=List[DepartmentCount])
async def department_counts(conn: asyncpg.Connection = Depends(get_db)):
    cached = await cache_get(DEPT_COUNT_KEY)
    if cached:
        return cached

    counts = await employee_service.get_department_counts(conn)
    await cache_set(DEPT_COUNT_KEY, [c.model_dump() for c in counts])
    return counts


# ---------- Joining date range (Query 4) ----------

@router.get("/joining-date-range", response_model=List[EmployeeResponse])
async def employees_by_joining_date_range(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    conn: asyncpg.Connection = Depends(get_db),
):
    employees = await employee_service.get_employees_by_joining_date_range(conn, from_date, to_date)
    return [EmployeeResponse(**e) for e in employees]


# ---------- Transactional create + assign ----------

@router.post("/create-and-assign-group", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_and_assign_group(
    payload: CreateAndAssignGroupRequest,
    conn: asyncpg.Connection = Depends(get_db),
):
    employee = await employee_service.create_and_assign_group(conn, payload)
    await _invalidate_caches()
    return EmployeeResponse(**employee)


# ---------- Get single employee (Query 2 – JOIN with groups) ----------

@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: UUID, conn: asyncpg.Connection = Depends(get_db)):
    cache_key = EMPLOYEE_CACHE_KEY.format(id=employee_id)
    cached = await cache_get(cache_key)
    if cached:
        return cached

    employee = await employee_service.get_employee(conn, employee_id)
    response = EmployeeResponse(**employee)
    await cache_set(cache_key, response.model_dump())
    return response


# ---------- Create employee ----------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_employee(payload: EmployeeCreate, conn: asyncpg.Connection = Depends(get_db)):
    employee = await employee_service.create_employee(conn, payload)
    await _invalidate_caches()
    name = f"{employee['first_name']} {employee['last_name']}"
    return {"message": "Employee created successfully", "name": name}


# ---------- Update employee ----------

@router.put("/{employee_id}")
async def update_employee(
    employee_id: UUID, payload: EmployeeUpdate,
    conn: asyncpg.Connection = Depends(get_db),
):
    employee = await employee_service.update_employee(conn, employee_id, payload)
    await _invalidate_caches(employee_id)
    name = f"{employee['first_name']} {employee['last_name']}"
    return {"message": "Employee updated successfully", "name": name}


# ---------- Delete employee ----------

@router.delete("/{employee_id}")
async def delete_employee(employee_id: UUID, conn: asyncpg.Connection = Depends(get_db)):
    name = await employee_service.delete_employee(conn, employee_id)
    await _invalidate_caches(employee_id)
    return {"message": "Employee deleted successfully", "name": name}


# ---------- Group assignment sub-routes ----------

@router.post("/{employee_id}/groups/{group_id}", response_model=EmployeeResponse)
async def assign_group(
    employee_id: UUID, group_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
):
    employee = await employee_service.assign_group(conn, employee_id, group_id)
    await _invalidate_caches(employee_id)
    return EmployeeResponse(**employee)


@router.delete("/{employee_id}/groups/{group_id}", response_model=EmployeeResponse)
async def remove_group(
    employee_id: UUID, group_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
):
    employee = await employee_service.remove_group(conn, employee_id, group_id)
    await _invalidate_caches(employee_id)
    return EmployeeResponse(**employee)


@router.get("/{employee_id}/groups", response_model=List[GroupSummary])
async def get_employee_groups(employee_id: UUID, conn: asyncpg.Connection = Depends(get_db)):
    groups = await employee_service.get_employee_groups(conn, employee_id)
    return [GroupSummary(**g) for g in groups]

