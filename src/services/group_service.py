from typing import List

import asyncpg
from fastapi import HTTPException

from src.schemas.group import GroupCreate, GroupResponse


# Query 5 – All groups with employee count (JOIN + GROUP BY + COUNT)
async def list_groups_with_employee_count(conn: asyncpg.Connection) -> List[GroupResponse]:
    rows = await conn.fetch(
        """
        SELECT
            g.id,
            g.name,
            g.description,
            g.created_at,
            COUNT(eg.employee_id) AS employee_count
        FROM groups g
        LEFT JOIN employee_group eg ON g.id = eg.group_id
        GROUP BY g.id
        ORDER BY g.name
        """
    )
    return [GroupResponse(**dict(r)) for r in rows]


async def create_group(conn: asyncpg.Connection, payload: GroupCreate) -> dict:
    if await conn.fetchval("SELECT id FROM groups WHERE name = $1", payload.name):
        raise HTTPException(status_code=409, detail="Group name already exists")

    row = await conn.fetchrow(
        """
        INSERT INTO groups (name, description)
        VALUES ($1, $2)
        RETURNING id, name, description, created_at
        """,
        payload.name, payload.description,
    )
    return dict(row)

