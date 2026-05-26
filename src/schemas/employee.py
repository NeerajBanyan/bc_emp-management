import enum
import re
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- Employee status enum ----------

class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_NOTICE = "ON_NOTICE"
    TERMINATED = "TERMINATED"


# ---------- Group sub-schema (used inside employee responses) ----------

class GroupSummary(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None


# ---------- Employee request schemas ----------

class EmployeeCreate(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    designation: str = Field(..., min_length=1, max_length=100)
    department: str = Field(..., min_length=1, max_length=100)
    status: EmployeeStatus
    joining_date: date

    @field_validator("first_name", "last_name", "employee_code")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank or whitespace")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = re.sub(r"[\s\-\(\)\+]", "", v)
        if not cleaned.isdigit() or not (7 <= len(cleaned) <= 15):
            raise ValueError("phone must be 7–15 digits (spaces, dashes, +, parens allowed)")
        return v


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    designation: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[EmployeeStatus] = None
    joining_date: Optional[date] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("must not be blank or whitespace")
        return v.strip() if v else v

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = re.sub(r"[\s\-\(\)\+]", "", v)
        if not cleaned.isdigit() or not (7 <= len(cleaned) <= 15):
            raise ValueError("phone must be 7–15 digits (spaces, dashes, +, parens allowed)")
        return v


# ---------- Employee response schema ----------

class EmployeeResponse(BaseModel):
    id: UUID
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    designation: str
    department: str
    status: EmployeeStatus
    joining_date: date
    created_at: datetime
    updated_at: datetime
    groups: List[GroupSummary] = []


# ---------- Other response shapes ----------

class PaginatedEmployees(BaseModel):
    total: int
    page: int
    limit: int
    items: List[EmployeeResponse]


class DepartmentCount(BaseModel):
    department: str
    employee_count: int


# ---------- Multi-step workflow ----------

class CreateAndAssignGroupRequest(BaseModel):
    employee: EmployeeCreate
    group_id: UUID
