# Phase 1.7 — Workflow Trigger Expansion / Scheduling

## 1. 阶段目标

在 Phase 1.6 Trigger Contract 基础上扩展可配置触发入口，建立可审计、可持久化、可测试的 Scheduling Contract，再进入实际 Scheduler / Execution integration。

## 2. 任务拆解

| ID | 内容 | 状态 |
|---|---|---|
| 1.7-A | Scheduled Trigger Backend Contract | 已完成 |
| 1.7-B | Scheduler execution / persistence integration | 已完成 |
| 1.7-C | Frontend Schedule Governance UI | 已完成 |
| 1.7-D | Real HTTP + Browser E2E | 已完成 |

## 3. Backend Contract

Trigger 类型扩展为 `manual` / `scheduled`。Scheduled Trigger 必须提供明确的 schedule config；保存配置不自动产生 Execution；Tenant / Workflow / Published Version / enabled lifecycle 与 Phase 1.6 保持一致。

初始 schedule contract 支持明确、可测试的周期表达，例如：

```json
{
  "timezone": "Asia/Shanghai",
  "interval_seconds": 300
}
```

不直接接受任意 Cron DSL；若未来增加 Cron，应新增独立 Contract 与验收。

## 4. Scheduler / Persistence

Scheduler 与 Workflow Execution 共用 Trigger Service、Execution State Machine、Idempotency / Reliability / Audit / Trace 边界。调度器的引入不得改变已有 Trigger Contract。

## 5. Frontend

Schedule Governance UI 必须通过 Backend API Types 工作，提供 Trigger inventory、schedule 配置、生命周期控制和错误状态。前端不自行判断 Execution / Idempotency 规则。

## 6. Browser E2E

```text
Browser
 ↓
Vue Trigger Governance
 ↓
Real Backend HTTP
 ↓
Scheduled Trigger
 ↓
Scheduler
 ↓
Workflow Execution
 ↓
Execution Observation
```

覆盖 governance、runtime convergence、lifecycle security，并作为第三层独立 Gate。

## 7. 完成记录

Phase 1.7 已正式关闭。历史 1.7-A/B/C/D 文档统一并入本 Phase；实际结果进入 `03-acceptance/PHASE_1_7_ACCEPTANCE.md`。