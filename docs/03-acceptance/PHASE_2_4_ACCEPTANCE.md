# Phase 2.4 Durable Scheduler Acceptance

> 当前状态：**Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire integration 已完成开发；Frontend / Browser E2E 仍在本地验收。**
> 验收基线：`main`
> 评估日期：2026-08-25

## 1. 当前 Gate

| 项目 | 状态 |
|---|---|
| Contract / timezone / DST | 本地 Gate 已通过：13 passed |
| Scheduler 持久化模型 | 本地 Migration Gate 已通过 |
| Alembic `0028_durable_scheduler_persistence` | 本地 `current` 为 head |
| 原子 lease claim / release | PostgreSQL Repository integration 已通过：2 passed |
| schedule slot 幂等 claim | PostgreSQL Repository integration 已通过 |
| WorkflowExecution 绑定 | Runtime Gate 已覆盖并通过 |
| Tenant / Organization scope | Repository lease/slot 与状态查询 tenant isolation 已覆盖 |
| Scheduler Runtime persistence 闭环 | 本地 Gate 已通过：4 passed |
| Scheduler API Contract / 状态可观测性 | 本地 Gate 已通过：6 passed |
| Misfire policy Runtime integration | 已完成开发，待最终汇总验收 |
| Frontend Regression Gate | 开发者本地实际通过：79 passed，production build 通过 |
| Workflow Trigger Browser E2E | **当前待重新执行：正式路由已修复，现已补齐真实登录 Session，但尚无新的本地实际通过结果** |
| Tenant Safe Real API acceptance | 待完成 |

## 2. 最新 Workflow Trigger Browser E2E 失败与修复

开发者在 `c7c2a58` 基线本地执行 Workflow Trigger Browser Gate 时，测试已经访问正式路由 `/workflows/triggers`，但仍未看到 `Workflow Trigger Governance`。

根因是 E2E 使用 `APIRequestContext` 完成真实登录后，只保存了 API Authorization Header，没有将真实登录返回的 `access_token`、`roles`、`user_id` 写入浏览器正式 Session localStorage。Frontend Router 的认证守卫因此将 Browser 导向登录页。

本轮修复在 `frontend/tests/e2e/workflow-trigger-governance.spec.ts` 中从真实 `/auth/login` 响应建立：

```text
enterprise_agent_access_token
enterprise_agent_roles
enterprise_agent_user_id
```

修复不修改生产 Router、Backend Auth Contract、Scheduler Runtime 或持久化逻辑，也不创建旧路径兼容入口。

## 3. 本轮重新验收入口

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Browser Gate 依赖本地真实 Frontend `http://127.0.0.1:5173` 与 Backend HTTP `http://127.0.0.1:8000/api/v1`，并由脚本负责隔离 Browser E2E 数据库状态。

## 4. 后续 Acceptance 目标

至少覆盖：

- 多实例 lease 竞争；
- lease 过期抢占；
- 重复 schedule slot claim；
- misfire：skip / fire_once / bounded_catch_up；
- enabled / paused / disabled；
- WorkflowExecution 关联；
- Tenant Safe organization scope；
- Audit / Trace 关联；
- 服务重启后的 next_run_at / lease 恢复语义；
- Scheduler 状态 API 的 tenant isolation 与错误边界；
- Workflow Trigger 真实浏览器创建、状态查看、禁用、启用及持久化回读。

**当前不记录 Phase 2.4 Passed。**
