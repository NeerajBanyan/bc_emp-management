from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class GroupResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    employee_count: Optional[int] = None
