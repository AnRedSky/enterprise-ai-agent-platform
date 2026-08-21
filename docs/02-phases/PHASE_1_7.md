# Phase 1.7 — Workflow Trigger Expansion / Scheduling

## 1. 阶段目标

在 Phase 1.6 Trigger Contract 基础上扩展可配置触发入口，建立可审计、可持久化、可测试的 Scheduling Contract，再进入实际 Scheduler / Execution integration。

## 2. 任务拆解与历史内容归并

| ID | 内容 | 状态 | 历史来源 |
|---|---|---|---|
| 1.7-A | Scheduled Trigger Backend Contract / Scheduler runtime / governance recovery | 已完成 | A-01/A-02/A-03 历史记录 |
| 1.7-B | Scheduler execution / persistence integration | 已完成 | `13-phase-1.7-b-scheduler-execution-persistence.md` |
| 1.7-C | Frontend Schedule Governance UI | 已完成 | `19-phase-1.7-c-schedule-governance-frontend-integration.md` |
| 1.7-D | Real HTTP + Browser E2E | 已完成 | `20-phase-1.7-d-browser-frontend-backend-e2e.md` |

当前 Git tree 未发现独立 A-01 或 A-04 文档，因此不凭文件名补造缺失内容；A-01 的 contract 边界来自 `18-phase-1.7-workflow-trigger-scheduling-contract.md`，A-02/A-03 的具体内容来自对应历史文档。

## 3. Backend Contract

Trigger 类型扩展为 `manual` / `scheduled`。Scheduled Trigger 必须提供明确 schedule config；保存配置不自动产生 Execution；Tenant / Workflow / Published Version / enabled lifecycle 与 Phase 1.6 保持一致。

初始 schedule contract：`timezone` + `interval_seconds`。不直接接受任意 Cron DSL；未来增加 Cron 必须新增独立 Contract 与验收。

## 4. Scheduler Runtime / Idempotency

FastAPI lifespan 启动 Scheduler background task，周期扫描 enabled + scheduled + published Workflow，通过现有 Workflow Execution Runtime 执行。

Interval slot 与 deterministic Idempotency-Key：`scheduled:{trigger_id}:{interval_slot}`，其中 interval_slot 基于 UTC epoch 与 interval_seconds 计算。多 worker 重复 dispatch 依赖现有 PostgreSQL 唯一约束收敛到单个 Execution。

Scheduler 停止随 FastAPI lifespan 取消；当前不持久化 next_run_at、scheduler lease、misfire policy 或独立 scheduler state。

## 5. Governance / Recovery

Scheduler candidate 必须满足 scheduled、enabled、published Workflow、非空 published_version_id。单个 dispatch failure 不得终止 scheduler loop。相同 Trigger + slot 即使重复 tick、worker restart 或 multi-worker dispatch，也不得产生第二 Execution。已存在 failed Execution 的 slot 仍视为已消费，不自动复制；恢复进入后续 slot 或显式 operator retry。

Workflow unpublish/archive、Trigger disable/delete 后不再 dispatch；重新 publish 后下一有效 slot 可恢复。

## 6. Persistence Boundary

Scheduled Trigger 不建立独立 scheduler state 表。Execution persistence boundary 为 `workflow_executions`，保存 tenant/workflow/version、idempotency key、status、input_data；调度来源通过 scheduled_slot / recovery metadata 解释。

数据库唯一约束 `(tenant_id, idempotency_key)` 是最终去重边界，scheduler pre-check 不是唯一正确性依据。

历史 B 文档记录过 SQLAlchemy `MissingGreenlet` 并发错误，已在 scheduler slot claim 收口过程中处理，不建立旁路并发方案。

## 7. Frontend Schedule Governance

Frontend 只消费既有 Trigger HTTP Contract，不重新实现 Scheduler。支持 manual/scheduled 类型、Schedule config 展示与创建、enabled/disabled/delete；scheduled Trigger 不显示 manual Invoke。Frontend 不计算 next-run、slot、recovery、lease、worker 状态。

## 8. Browser E2E

真实链路：Browser → Vue Trigger Governance → Real Backend HTTP → Scheduled Trigger → Scheduler → Workflow Execution → Execution Observation。

覆盖 Schedule 创建、生命周期、真实 persistence、scheduler 产生 Execution，并保持 Browser Gate 与 Backend/Frontend Gate 独立。

## 9. 验收门禁

Backend、Frontend、Browser 三层独立执行：Backend regression → migration/head → Real API；Frontend Vitest → production build；Browser → real Frontend → real Backend HTTP。

## 10. 迁移来源

- `18-phase-1.7-workflow-trigger-scheduling-contract.md`
- `12-phase-1.7-a-02-scheduled-trigger-runtime.md`
- `13-phase-1.7-a-03-scheduled-trigger-governance-recovery.md`
- `13-phase-1.7-b-scheduler-execution-persistence.md`
- `19-phase-1.7-c-schedule-governance-frontend-integration.md`
- `20-phase-1.7-d-browser-frontend-backend-e2e.md`
- `03-acceptance/PHASE_1_7_ACCEPTANCE.md`

## 11. 当前状态

**Phase 1.7 已正式关闭。** 历史计划、实现边界、失败/恢复约束和测试层职责已归并；实际测试结论只在 Acceptance / Project Status 中维护。