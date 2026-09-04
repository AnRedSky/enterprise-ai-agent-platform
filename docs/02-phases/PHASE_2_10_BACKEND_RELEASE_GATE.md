# Phase 2.10 Backend Release Gate

## Purpose

Provide a repeatable backend-only release acceptance boundary after Operator Governance II-08 Canonical Audit Query Performance and II-09 Result Lineage are locally verified.

## Scope

The gate verifies:

1. Backend default regression with warnings treated as errors.
2. Existing PostgreSQL readiness without starting protected services.
3. Alembic migration upgrade to head and exactly one migration head.
4. Operator Action idempotency and cross-session Retry/Resume concurrency.
5. Retry/Resume Result Resource lineage and transaction rollback.
6. Protected-service startup boundary.

## Service boundary

The gate must never create, start, restart, or stop API, Scheduler, Worker, PostgreSQL, or Redis. PostgreSQL is only probed and used when already reachable.

## Test data

Acceptance tests generate their own identities, tenants, workflows, execution records, and idempotency keys. No manual business IDs or credentials are required.

## Execution

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\27_backend_release_gate.ps1
```

A PostgreSQL-unreachable environment returns `[NOT EXECUTED]` with exit code `2`; it does not attempt service startup.
