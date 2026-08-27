# Workflow Transaction Ownership Primitives

## Problem

Workflow recovery already supports caller-owned transactions for Resume creation, but Runtime NodeExecution and Checkpoint writes still require an explicit ownership boundary before Phase 2.7-A can be closed.

## Decision

Introduce small, reusable transaction primitives:

- `nested_write(db)` — contention-prone durable writes execute inside `begin_nested()` so an integrity conflict rolls back only the SAVEPOINT.
- `commit_owned(db, owned=...)` — a service commits only when it explicitly owns the transaction.

These primitives do not silently change existing callers. Runtime integration remains a separate production-code change and must not be declared complete until `transition_node()` and the Runtime execution path use the same boundary.

## Invariant

```text
Caller-owned transaction
  -> domain durable writes
  -> nested contention handling
  -> single caller commit
```

A lower-level domain operation must not call `rollback()` on the caller's outer transaction after a nested integrity conflict.
