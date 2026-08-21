# Phase 1.7 — Acceptance

## 1. 范围

Scheduled Trigger Backend Contract、Scheduler execution / persistence、Schedule Governance UI、Real HTTP 与 Browser E2E。

## 2. 历史任务归并

- 1.7-A-01：Scheduled Trigger Backend Contract，来源为 Phase 1.7 规划基线。
- 1.7-A-02：Scheduler background runtime、interval slot、deterministic idempotency、FastAPI lifespan。
- 1.7-A-03：dispatch failure isolation、workflow/trigger governance、same-slot recovery、restart boundary。
- 1.7-B：workflow_executions persistence boundary、status/input/idempotency、recovery metadata、multi-worker convergence。
- 1.7-C：Schedule Governance Frontend Integration。
- 1.7-D：Real HTTP + Browser E2E scheduling contract。

当前 Git tree 未发现独立 A-01/A-04 文档，因此不补造缺失记录。

## 3. Gate

Backend、Frontend、Browser 三层独立执行。

## 4. 历史实际验收结论

当前 `PROJECT_STATUS.md` 记录 Phase 1.7 已正式关闭，Browser / Frontend / Backend 三层 Gate 均已通过。迁移仅整理记录，不重新推断历史测试结果。

## 5. 历史实现边界

Scheduler 使用 deterministic slot idempotency，Execution persistence 使用 `workflow_executions`，不增加独立 scheduler state。Frontend 不自行实现 scheduler runtime。Browser E2E 只验证 Browser + real HTTP + application runtime，不复制其他 Gate。

## 6. 迁移来源

- `18-phase-1.7-workflow-trigger-scheduling-contract.md`
- `12-phase-1.7-a-02-scheduled-trigger-runtime.md`
- `13-phase-1.7-a-03-scheduled-trigger-governance-recovery.md`
- `13-phase-1.7-b-scheduler-execution-persistence.md`
- `19-phase-1.7-c-schedule-governance-frontend-integration.md`
- `20-phase-1.7-d-browser-frontend-backend-e2e.md`
