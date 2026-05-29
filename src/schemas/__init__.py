# just marks this as a Python package

from src.schemas.employee import (
    EmployeeStatus,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    PaginatedEmployees,
    DepartmentCount,
    CreateAndAssignGroupRequest,
    GroupSummary,
)
from src.schemas.group import GroupCreate, GroupResponse

#__all__ — defines what's "public"
__all__ = [
    "EmployeeStatus",
    "EmployeeCreate",
    "EmployeeUpdate",
    "EmployeeResponse",
    "PaginatedEmployees",
    "DepartmentCount",
    "CreateAndAssignGroupRequest",
    "GroupSummary",
    "GroupCreate",
    "GroupResponse",
]
