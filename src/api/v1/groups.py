from typing import List

import asyncpg
from fastapi import APIRouter, Depends, status

from src.core.database import get_db
from src.schemas.group import GroupCreate, GroupResponse
from src.services import group_service

router = APIRouter(prefix="/groups", tags=["Groups"])


# Query 5 – groups with employee count
@router.get("", response_model=List[GroupResponse])
async def list_groups(conn: asyncpg.Connection = Depends(get_db)):
    return await group_service.list_groups_with_employee_count(conn)


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(payload: GroupCreate, conn: asyncpg.Connection = Depends(get_db)):
    group = await group_service.create_group(conn, payload)
    return GroupResponse(**group)

