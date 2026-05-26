-- ============================================================
-- Banyan Cloud Employee Management – Database Schema
-- Run this file in pgAdmin Query Tool on the banyan_employees DB
-- ============================================================

-- 1. Groups table
CREATE TABLE groups (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(500),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Employees table
CREATE TABLE employees (
    id            UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_code VARCHAR(50)   NOT NULL UNIQUE,
    first_name    VARCHAR(100)  NOT NULL,
    last_name     VARCHAR(100)  NOT NULL,
    email         VARCHAR(255)  NOT NULL UNIQUE,
    phone         VARCHAR(20),
    designation   VARCHAR(100)  NOT NULL,
    department    VARCHAR(100)  NOT NULL,
    status        VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'ON_NOTICE', 'TERMINATED')),
    joining_date  DATE          NOT NULL,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Indexes for filtering and sorting
CREATE INDEX idx_employees_status     ON employees(status);
CREATE INDEX idx_employees_department ON employees(department);
CREATE INDEX idx_employees_joining    ON employees(joining_date);

-- 4. Employee ↔ Group many-to-many join table
CREATE TABLE employee_group (
    employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
    group_id    UUID REFERENCES groups(id)    ON DELETE CASCADE,
    PRIMARY KEY (employee_id, group_id)
);
