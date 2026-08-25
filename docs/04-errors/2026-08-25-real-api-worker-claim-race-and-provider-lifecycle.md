# 2026-08-25：Real API Worker claim 竞态与 Provider 生命周期阻塞

## 1. 发生现象

开发者执行 Tenant Safe Real API bootstrap 时出现：

```text
POST /workflows/executions/e3f30ab1-7658-4809-b3a1-047dfce24110/run
-> expected HTTP 404, got 409
只有 pending Execution 可以 Run
```

随后 Backend Regression Gate 的 Real API Governance 出现两个 cleanup 失败：

```text
DELETE /model-providers/<provider_id>
-> 500 Internal Server Error
```

## 2. 根因分析

### 2.1 `/run` 的 409 是 Worker 合法竞争

Phase 2.5 已将 Scheduled / Manual Execution 统一落库为 `pending`，独立 Worker 使用 PostgreSQL `FOR UPDATE SKIP LOCKED` 认领 pending Execution。

因此以下时序是合法的：

```text
API bootstrap
    │
    ├── POST create Execution(status=pending)
    │
    └───────────────┐
                    │
             Worker claim
                    │
             worker_owner = current worker
                    │
             Worker 执行并完成
                    │
bootstrap POST /run
                    │
                    └── 409：只有 pending Execution 可以 Run
```

生产 Execution 状态机不应因此放宽为 `running → running` 或允许重复执行。

### 2.2 Provider 删除仍被历史 Usage Record 阻塞

`model_usage_records.profile_id` 已在 `0030_usage_profile_lifecycle` 中改为：

```text
nullable
ON DELETE SET NULL
```

但 `model_usage_records.provider_id` 仍为：

```text
NOT NULL
ON DELETE RESTRICT
```

Real API Governance 测试在删除 Profile 后继续删除 Provider，因此历史 Usage Record 阻止 Provider 删除并导致 500。

Usage Record 已保存：

```text
model_type
model_name
pricing_source
pricing_version
input/output/request/total cost
```

这些字段构成历史用量快照，因此 Provider / Profile 配置对象删除后不应反向阻塞历史审计数据。

## 3. 修复方案

### 3.1 Real API bootstrap

不修改生产 `/run` Contract。

bootstrap 增加统一执行辅助逻辑：

1. 首先正常调用真实 HTTP `/run`；
2. 如果返回预期业务状态，立即检查 PostgreSQL 持久化结果；
3. 如果返回明确的 `只有 pending Execution 可以 Run`，视为 Worker 已合法抢占；
4. 轮询真实 HTTP Execution 查询直到 `completed / failed / cancelled`；
5. 校验最终状态与 Fixture 期望错误码；
6. 超时、其他 409、其他 HTTP 错误全部失败。

这样既保留真实 Worker 消费链，又消除测试脚本依赖瞬时调度顺序的问题。

### 3.2 ModelUsageRecord Provider FK

新增 Alembic：

```text
0031_usage_provider_lifecycle
```

调整：

```text
provider_id: UUID | None
ON DELETE SET NULL
```

降级时若存在 `provider_id IS NULL` 历史记录则主动拒绝降级，避免静默丢失历史关联语义。

## 4. 不采用的错误修复

以下方案均不采用：

- 不把 `WorkflowExecutionService.run()` 改成允许非 pending 状态重复执行；
- 不把 `running → running` 加入 Node 状态机；
- 不让 Real API Gate 自动停止 Worker；
- 不通过降低 Worker polling 频率规避竞态；
- 不删除历史 Usage Record；
- 不把 Provider 删除改成级联删除 Usage Record；
- 不增加第二套 Runtime / Execution Service。

## 5. 验证要求

本次修复必须在开发者本地真实环境重新执行：

```powershell
cd backend
uv run alembic upgrade head
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

其中 API / Scheduler / Worker 必须由开发者按项目服务前置条件手工保持运行；测试 Gate 不启动、停止或重启服务。

## 6. 预期结果

修复后的目标不是“忽略错误”，而是：

```text
Real API bootstrap
    → Worker 竞争属于合法路径
    → 最终 Execution 状态仍必须符合 Fixture Contract

Profile delete
    → profile_id = NULL
    → 历史 Usage Record 保留

Provider delete
    → provider_id = NULL
    → 历史 Usage Record 保留

Backend Gate
    → 不再因 Provider cleanup FK 失败阻塞
```
