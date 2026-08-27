# Durable Frontier Lease Fencing

## Status

Implemented in `main`.

## Problem

A Worker can outlive its lease. If another Worker reclaims the Frontier, the stale Worker must not be able to complete, fail, or release the newly owned work item.

## Contract

`WorkflowFrontier.attempt` is the fencing generation. A Worker operation is valid only when both `worker_owner` and `attempt` still match the persisted Frontier.

```text
Worker A / attempt 3
        ↓ lease expires
Recovery
        ↓
retry_wait / owner cleared
        ↓
Worker B claims
        ↓
attempt 4
        ↓
Worker A late completion → rejected
```

Expired `claimed` / `running` Frontiers are returned to `retry_wait` using `FOR UPDATE SKIP LOCKED`. Recovery and claim do not commit; the Scheduler/Worker caller owns the outer transaction.

## Validation boundary

The repository now exposes:

- `recover_expired_frontiers()` for lease-expiry recovery.
- `transition_owned_frontier()` for owner + fencing-generation protected transitions.

Unit-test contracts cover expiry recovery, fencing rejection, lock usage, and the no-commit repository boundary.
