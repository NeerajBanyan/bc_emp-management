from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

import asyncpg
from fastapi import HTTPException

from src.schemas.employee import CreateAndAssignGroupRequest, DepartmentCount, EmployeeCreate, EmployeeUpdate

# Only these column names are allowed for sorting (prevents SQL injection)
ALLOWED_SORT_FIELDS = {"first_name", "last_name", "joining_date", "created_at"}


# -----------------------------------------------------------------------
# Helper: fetch one employee row + all its groups using a JOIN
# This satisfies Query 2: Employee with Group Details Using JOIN
# -----------------------------------------------------------------------
async def _get_employee_with_groups(conn: asyncpg.Connection, employee_id: UUID) -> dict:
    rows = await conn.fetch(
        """
        SELECT
            e.id, e.employee_code, e.first_name, e.last_name, e.email, e.phone,
            e.designation, e.department, e.status, e.joining_date,
            e.created_at, e.updated_at,
            g.id          AS group_id,
            g.name        AS group_name,
            g.description AS group_description
        FROM employees e
        LEFT JOIN employee_group eg ON e.id = eg.employee_id
        LEFT JOIN groups g          ON eg.group_id = g.id
        WHERE e.id = $1
        """,
        employee_id,
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Employee not found")

    first = rows[0]
    employee = {
        "id":            first["id"],
        "employee_code": first["employee_code"],
        "first_name":    first["first_name"],
        "last_name":     first["last_name"],
        "email":         first["email"],
        "phone":         first["phone"],
        "designation":   first["designation"],
        "department":    first["department"],
        "status":        first["status"],
        "joining_date":  first["joining_date"],
        "created_at":    first["created_at"],
        "updated_at":    first["updated_at"],
        "groups": [
            {
                "id":          r["group_id"],
                "name":        r["group_name"],
                "description": r["group_description"],
            }
            for r in rows if r["group_id"] is not None
        ],
    }
    return employee


# -----------------------------------------------------------------------
# Query 1 – List employees with pagination, sorting, and filtering
# -----------------------------------------------------------------------
async def list_employees(
    conn: asyncpg.Connection,
    page: int,
    limit: int,
    sort_by: str,
    sort_order: str,
    status: Optional[str],
    department: Optional[str],
) -> Tuple[int, List[dict]]:
    # Whitelist sort column to prevent SQL injection
    if sort_by not in ALLOWED_SORT_FIELDS:
        sort_by = "created_at"
    order = "DESC" if sort_order.lower() == "desc" else "ASC"

    # Build WHERE clause dynamically
    conditions: list = []
    params: list = []

    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")
    if department:
        params.append(department)
        conditions.append(f"department = ${len(params)}")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Total count for pagination
    total = await conn.fetchval(f"SELECT COUNT(*) FROM employees {where}", *params)

    # Fetch the page
    params.append(limit)
    params.append((page - 1) * limit)
    rows = await conn.fetch(
        f"""
        SELECT id, employee_code, first_name, last_name, email, phone,
               designation, department, status, joining_date, created_at, updated_at
        FROM employees
        {where}
        ORDER BY {sort_by} {order}
        LIMIT ${len(params) - 1} OFFSET ${len(params)}
        """,
        *params,
    )

    return total, [dict(r) | {"groups": []} for r in rows]


# -----------------------------------------------------------------------
# Get single employee (uses JOIN – Query 2)
# -----------------------------------------------------------------------
async def get_employee(conn: asyncpg.Connection, employee_id: UUID) -> dict:
    return await _get_employee_with_groups(conn, employee_id)


# -----------------------------------------------------------------------
# Create employee
# -----------------------------------------------------------------------
async def create_employee(conn: asyncpg.Connection, payload: EmployeeCreate) -> dict:
    # Uniqueness checks
    if await conn.fetchval("SELECT id FROM employees WHERE employee_code = $1", payload.employee_code):
        raise HTTPException(status_code=409, detail="employee_code already exists")
    if await conn.fetchval("SELECT id FROM employees WHERE email = $1", payload.email):
        raise HTTPException(status_code=409, detail="email already exists")

    row = await conn.fetchrow(
        """
        INSERT INTO employees
            (employee_code, first_name, last_name, email, phone,
             designation, department, status, joining_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, employee_code, first_name, last_name, email, phone,
                  designation, department, status, joining_date, created_at, updated_at
        """,
        payload.employee_code, payload.first_name, payload.last_name,
        payload.email, payload.phone, payload.designation,
        payload.department, payload.status.value, payload.joining_date,
    )
    return dict(row) | {"groups": []}


# -----------------------------------------------------------------------
# Update employee
# -----------------------------------------------------------------------
async def update_employee(conn: asyncpg.Connection, employee_id: UUID, payload: EmployeeUpdate) -> dict:
    if not await conn.fetchval("SELECT id FROM employees WHERE id = $1", employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return await _get_employee_with_groups(conn, employee_id)

    # Check email uniqueness if being changed
    if "email" in updates:
        dup = await conn.fetchval(
            "SELECT id FROM employees WHERE email = $1 AND id != $2",
            updates["email"], employee_id,
        )
        if dup:
            raise HTTPException(status_code=409, detail="email already exists")

    # Build SET clause dynamically
    set_parts: list = []
    params: list = []
    for key, value in updates.items():
        # Convert enum to its string value for DB storage
        params.append(value.value if hasattr(value, "value") else value)
        set_parts.append(f"{key} = ${len(params)}")

    set_parts.append("updated_at = NOW()")
    params.append(employee_id)

    await conn.execute(
        f"UPDATE employees SET {', '.join(set_parts)} WHERE id = ${len(params)}",
        *params,
    )
    return await _get_employee_with_groups(conn, employee_id)


# -----------------------------------------------------------------------
# Delete employee
# -----------------------------------------------------------------------
async def delete_employee(conn: asyncpg.Connection, employee_id: UUID) -> str:
    row = await conn.fetchrow(
        "SELECT first_name, last_name FROM employees WHERE id = $1", employee_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    await conn.execute("DELETE FROM employees WHERE id = $1", employee_id)
    return f"{row['first_name']} {row['last_name']}"


# -----------------------------------------------------------------------
# Group assignment
# -----------------------------------------------------------------------
async def assign_group(conn: asyncpg.Connection, employee_id: UUID, group_id: UUID) -> dict:
    if not await conn.fetchval("SELECT id FROM employees WHERE id = $1", employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    if not await conn.fetchval("SELECT id FROM groups WHERE id = $1", group_id):
        raise HTTPException(status_code=404, detail="Group not found")

    # ON CONFLICT DO NOTHING avoids error if already assigned
    await conn.execute(
        "INSERT INTO employee_group (employee_id, group_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        employee_id, group_id,
    )
    return await _get_employee_with_groups(conn, employee_id)


async def remove_group(conn: asyncpg.Connection, employee_id: UUID, group_id: UUID) -> dict:
    if not await conn.fetchval("SELECT id FROM employees WHERE id = $1", employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")

    await conn.execute(
        "DELETE FROM employee_group WHERE employee_id = $1 AND group_id = $2",
        employee_id, group_id,
    )
    return await _get_employee_with_groups(conn, employee_id)


async def get_employee_groups(conn: asyncpg.Connection, employee_id: UUID) -> List[dict]:
    if not await conn.fetchval("SELECT id FROM employees WHERE id = $1", employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")

    rows = await conn.fetch(
        """
        SELECT g.id, g.name, g.description
        FROM groups g
        JOIN employee_group eg ON g.id = eg.group_id
        WHERE eg.employee_id = $1
        """,
        employee_id,
    )
    return [dict(r) for r in rows]


# -----------------------------------------------------------------------
# Query 3 – Department-wise employee count
# -----------------------------------------------------------------------
async def get_department_counts(conn: asyncpg.Connection) -> List[DepartmentCount]:
    rows = await conn.fetch(
        """
        SELECT department, COUNT(*) AS employee_count
        FROM employees
        GROUP BY department
        ORDER BY department
        """
    )
    return [DepartmentCount(department=r["department"], employee_count=r["employee_count"]) for r in rows]


# -----------------------------------------------------------------------
# Query 4 – Employees who joined within a date range
# -----------------------------------------------------------------------
async def get_employees_by_joining_date_range(
    conn: asyncpg.Connection, from_date: date, to_date: date
) -> List[dict]:
    rows = await conn.fetch(
        """
        SELECT id, employee_code, first_name, last_name, email, phone,
               designation, department, status, joining_date, created_at, updated_at
        FROM employees
        WHERE joining_date BETWEEN $1 AND $2
        ORDER BY joining_date
        """,
        from_date, to_date,
    )
    return [dict(r) | {"groups": []} for r in rows]


# -----------------------------------------------------------------------
# Multi-step transactional workflow: create employee + assign group
# -----------------------------------------------------------------------
async def create_and_assign_group(conn: asyncpg.Connection, payload: CreateAndAssignGroupRequest) -> dict:
    # Validate group exists before starting
    if not await conn.fetchval("SELECT id FROM groups WHERE id = $1", payload.group_id):
        raise HTTPException(status_code=404, detail="Group not found")

    # Uniqueness checks before the transaction
    if await conn.fetchval("SELECT id FROM employees WHERE employee_code = $1", payload.employee.employee_code):
        raise HTTPException(status_code=409, detail="employee_code already exists")
    if await conn.fetchval("SELECT id FROM employees WHERE email = $1", payload.employee.email):
        raise HTTPException(status_code=409, detail="email already exists")

    # Wrap both inserts in one transaction – if either fails, both roll back
    async with conn.transaction():
        row = await conn.fetchrow(
            """
            INSERT INTO employees
                (employee_code, first_name, last_name, email, phone,
                 designation, department, status, joining_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """,
            payload.employee.employee_code, payload.employee.first_name,
            payload.employee.last_name, payload.employee.email,
            payload.employee.phone, payload.employee.designation,
            payload.employee.department, payload.employee.status.value,
            payload.employee.joining_date,
        )
        await conn.execute(
            "INSERT INTO employee_group (employee_id, group_id) VALUES ($1, $2)",
            row["id"], payload.group_id,
        )

    return await _get_employee_with_groups(conn, row["id"])

