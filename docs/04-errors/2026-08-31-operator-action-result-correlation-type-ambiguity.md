# Operator Action Result Correlation Type Ambiguity

- Date: 2026-08-31
- Area: Phase 2.10-II Runtime Operator Governance / Audit Trace Correlation
- Severity: High
- Status: Fixed

## Symptom

`OperatorActionIdempotency.result_resource_id` was interpreted as a `WorkflowExecution.id` by the runtime correlation service without storing the result resource type.

The same field was also populated with the original trigger/execution resource ID when an idempotent action failed, creating a false result correlation.

## Root cause

The persistence model contained only `result_resource_id`, while Operator Action resources can be `workflow_execution` or `workflow_trigger`. Result resource type was therefore an implicit convention instead of an explicit domain contract.

## Fix

1. Added nullable `result_resource_type` to `operator_action_idempotencies`.
2. Added tenant-scoped result correlation index.
3. Backfilled successful historical results as `workflow_execution`.
4. Cleared result resource fields from historical non-successful records because they were not actual results.
5. Operator governance now persists `workflow_execution` as the result type for successful retry/invoke actions.
6. Failed idempotent actions no longer persist a pseudo result resource.
7. Runtime correlation only follows result IDs when `result_resource_type == workflow_execution`.
8. Added unit and real PostgreSQL acceptance coverage.

## Regression boundary

The hardening gate never starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis, and all test identifiers are generated automatically.
