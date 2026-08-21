# Phase 1.5 — Acceptance

## 1. 范围

Workflow Definition / Version / Publish、Tenant Governance、Execution State Machine、Runtime Integration、Governance / Audit / Trace、Retry / Timeout / Idempotency / Concurrency / Deadline、Circuit Breaker。

## 2. Final Acceptance — 1.5-G

开发者实际结果（来源于原 Phase 1.5 计划的最终验收记录）：

```text
uv run alembic upgrade head
→ 0020_workflow_circuit_breaker -> 0021_workflow_circuit_policy 成功

uv run pytest -q
→ 209 passed, 11 deselected in 3.44s

backend/scripts/test/api-real/01_run_real_api_tests.ps1
→ 11 passed in 17.62s
→ [PASS] Real API gate completed.
```

## 3. Circuit Breaker Contract

- CLOSED → OPEN → HALF_OPEN → CLOSED
- policy 按 `tenant_id + circuit_key` 隔离
- policy drift `409`
- OPEN `CIRCUIT_OPEN` fast-fail
- HALF_OPEN probe quota
- success → CLOSED
- failure → OPEN

## 4. 验收结论

原 Phase 1.5 文档记录 1.5-A～G 全部完成，Phase 1.5 正式关闭。后续阶段的状态以新的 `PROJECT_STATUS.md` 为准。