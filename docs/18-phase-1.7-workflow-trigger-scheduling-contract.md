# Phase 1.7：Workflow Trigger Expansion / Scheduling Contract

> 本文是 Phase 1.6 收口后的下一阶段规划基线。Phase 1.7 是在现有 Trigger Contract 之上扩展业务入口能力的阶段；本阶段先建立可审计、可持久化、可测试的 Scheduling Contract，再决定是否引入实际 Scheduler / Worker 基础设施。

## 1. 阶段目标

将 Phase 1.6 已验证的 manual Trigger Contract 向“可配置触发入口”扩展，同时保持当前 FastAPI + PostgreSQL 单体边界，不在第一项任务中直接引入 MQ、Worker、Event Bus 或第三方 Workflow Engine。

目标链路：

```text
Published Workflow
      ↓
Trigger Contract
      ↓
Schedule Contract
      ↓
Tenant / RBAC / Lifecycle validation
      ↓
Execution / Idempotency / Reliability Governance
      ↓
Audit / Trace
```

## 2. Phase 1.7 分解

| 子阶段 | 内容 | 状态 |
|---|---|---|
| 1.7-A | Scheduled Trigger Backend Contract | **开发中** |
| 1.7-B | Scheduler execution / persistence integration | 待 1.7-A 验收 |
| 1.7-C | Frontend Schedule Governance UI Contract | 待 1.7-B |
| 1.7-D | Real HTTP + Browser E2E scheduling contract | 待 1.7-C |

## 3. 1.7-A 当前任务边界

第一项只实现 Backend Contract，不实现后台调度器：

1. Trigger 类型扩展为 `manual` / `scheduled` 的稳定契约。
2. Scheduled Trigger 的 schedule config schema 与校验。
3. Tenant / Workflow / Published Version 绑定规则保持与 Phase 1.6 一致。
4. enabled / disabled 生命周期保持一致。
5. Schedule 配置变更必须可审计。
6. 不因保存 Schedule 自动创建执行。
7. 不引入 MQ、Worker、Event Bus、Cron daemon 或外部调度引擎。
8. Backend pytest / contract scenario 先行，随后再进入 Frontend。

## 4. Schedule Contract 初始边界

初版只支持明确、可测试的周期表达，不直接接受任意 Cron DSL。建议契约字段：

```json
{
  "timezone": "Asia/Shanghai",
  "interval_seconds": 300
}
```

约束：

- `timezone` 必须为有效 IANA timezone。
- `interval_seconds` 必须为正整数，并设置明确上下限。
- `scheduled` Trigger 必须提供 schedule config。
- `manual` Trigger 不允许依赖 schedule config 执行。
- 保存配置不产生 Workflow Execution。

> 上述限制是 Phase 1.7-A 的工程设计基线，后续若需要 Cron 表达式，应先新增独立 Contract 与验收，不直接扩大本任务范围。

## 5. 固定开发顺序

```text
规划基线
  ↓
Backend Domain + Schema Contract
  ↓
Migration（如持久化结构需要）
  ↓
Backend pytest / API Contract
  ↓
Backend Real API
  ↓
Frontend API Type + UI
  ↓
Frontend Vitest + production build
  ↓
真实联调
  ↓
Browser E2E
  ↓
文档
  ↓
main
```

## 6. Gate

Backend、Frontend、Browser/E2E 三层继续保持完全独立：

```text
Backend Gate
→ regression
→ migration/head
→ Real API

Frontend Gate
→ Vitest
→ production build

E2E Gate
→ Browser
→ real Frontend
→ real Backend HTTP
```

## 7. 当前立即执行任务

**Phase 1.7-A-01：Scheduled Trigger Backend Contract**。

验收要求：先完成 domain/schema contract 与测试，再决定 migration 与 API 扩展；禁止跳过 Backend Contract 直接开发前端调度 UI。
