# Banyan Cloud Employee Management Microservice

FastAPI + PostgreSQL + Redis microservice for managing employees and groups.

## Stack

- **FastAPI** – async REST framework
- **PostgreSQL 16** – relational store (via SQLAlchemy async + asyncpg)
- **Redis 7** – read-heavy caching with pattern-based invalidation
- **Alembic** – schema migrations
- **Pydantic v2** – request/response validation

## Project Structure

```
src/
  api/
    v1/
      employees.py   # /api/v1/employees routes
      groups.py      # /api/v1/groups routes
  core/
    config.py        # env-based settings
    database.py      # async SQLAlchemy engine & session
    redis.py         # Redis helpers (get/set/delete/pattern-delete)
  models/
    employee.py      # Employee, Group, association table, EmployeeStatus enum
  schemas/
    employee.py      # Pydantic schemas with validation
    group.py
  services/
    employee_service.py  # business logic & SQL queries
    group_service.py
  main.py            # FastAPI app, router inclusion
alembic/             # migrations
docker-compose.yml
```

## Quick Start (Docker)

```bash
cp .env.example .env   # already pre-filled for Docker
docker compose up --build
```

The API is available at **http://localhost:8000**.  
Interactive docs: **http://localhost:8000/docs**

## Local Development (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Update .env to point at your local Postgres & Redis
cp .env.example .env

# Run migrations
alembic upgrade head

# Start server
uvicorn src.main:app --reload
```

## API Reference

### Employees – `/api/v1/employees`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/employees` | Paginated, sortable, filterable employee list |
| GET | `/api/v1/employees/:id` | Single employee with groups (cached) |
| POST | `/api/v1/employees` | Create employee |
| PUT | `/api/v1/employees/:id` | Update employee |
| DELETE | `/api/v1/employees/:id` | Delete employee |
| POST | `/api/v1/employees/:id/groups/:groupId` | Assign employee to group |
| DELETE | `/api/v1/employees/:id/groups/:groupId` | Remove employee from group |
| GET | `/api/v1/employees/:id/groups` | List employee's groups |
| POST | `/api/v1/employees/create-and-assign-group` | Transactional create + assign |
| GET | `/api/v1/employees/department-counts` | Employees grouped by department |
| GET | `/api/v1/employees/joining-date-range?from=&to=` | Employees within date range |

### Groups – `/api/v1/groups`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/groups` | All groups with employee count (JOIN + GROUP BY) |
| POST | `/api/v1/groups` | Create group |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |

## Query Parameters – List Employees

| Param | Default | Values |
|-------|---------|--------|
| `page` | `1` | ≥ 1 |
| `limit` | `10` | 1–100 |
| `sortBy` | `created_at` | `first_name`, `last_name`, `joining_date`, `created_at` |
| `sortOrder` | `asc` | `asc`, `desc` |
| `status` | – | `ACTIVE`, `INACTIVE`, `ON_NOTICE`, `TERMINATED` |
| `department` | – | any string |

**Example:**
```
GET /api/v1/employees?page=1&limit=10&sortBy=joining_date&sortOrder=desc&status=ACTIVE&department=Engineering
```

## Transactional Workflow – `POST /api/v1/employees/create-and-assign-group`

```json
{
  "employee": {
    "employee_code": "EMP001",
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "designation": "Engineer",
    "department": "Engineering",
    "status": "ACTIVE",
    "joining_date": "2026-01-15"
  },
  "group_id": "<uuid-of-existing-group>"
}
```

Employee creation and group assignment happen inside a single DB transaction. If assignment fails the employee is rolled back.

## Validation Rules

- `employee_code` – required, unique, non-blank
- `email` – valid format, unique
- `first_name` / `last_name` – non-empty, non-blank
- `status` – one of `ACTIVE | INACTIVE | ON_NOTICE | TERMINATED`
- `joining_date` – valid ISO date
- `phone` – optional; if provided must be 7–15 digits (spaces/dashes/parens/+ allowed)

## Caching Strategy

- Individual employee lookups and paginated lists are cached in Redis (default TTL: 300 s).
- Any write operation (create, update, delete, group assignment) invalidates the affected employee key and all list/department-count keys via pattern delete.
- Cache TTL is configurable via `CACHE_TTL_SECONDS` in `.env`.

## Migrations

```bash
# Apply all migrations
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe change"

# Rollback one step
alembic downgrade -1
```
