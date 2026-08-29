# Phase 2.8-A Multi-Agent Collaboration Contract

> 本文件冻结 Phase 2.8 Multi-Agent Collaboration 的产品与 Backend Contract。
> Contract 已通过设计冻结，并已完成对应 Runtime Integration；后续变更不得重新定义已冻结的 tenant、版本、权限、幂等、预算、生命周期与 fencing 基础语义，除非另行形成正式 Contract 变更。

## 1. 目标

Phase 2.8 的目标不是简单增加“Agent 调 Agent”的调用能力，而是在现有 Agent / Workflow / Execution / RBAC / Audit / Trace / Model Governance / Durable Runtime 基础上，形成企业可治理的多 Agent 协作能力。

首版只解决一个明确场景：**一个主 Agent 在一次 Workflow Execution 内，将一个可审计、可限额、可回收的子任务委派给一个受治理的专职 Agent，并等待其结果继续主流程。**

不在首版引入 MQ/Kafka、通用 Agent Marketplace、跨租户 Agent 共享、开放式 Agent 自发现或无限递归 Agent spawning。

## 2. 核心术语

- **Orchestrator Agent**：当前 Execution 中负责推进业务流程的主 Agent。
- **Worker Agent**：被主 Agent 委派执行明确子任务的受治理 Agent。
- **Delegation**：一次有唯一身份、预算、超时、状态和 Trace 关联的子任务委派。
- **Collaboration Context**：传递给 Worker Agent 的最小必要输入，不默认复制主 Agent 全部上下文。
- **Collaboration Budget**：限制委派深度、并发子任务数量、模型调用预算与最长执行时间的约束集合。

## 3. 首版范围

### 3.1 必须支持

1. 一个 Orchestrator Execution 创建一个或多个受限 Delegation。
2. Delegation 必须绑定 tenant、source execution、source agent version、target agent version。
3. Target Agent 必须处于允许运行的发布状态，并通过现有 RBAC / tenant scope 校验。
4. Delegation 必须拥有稳定幂等身份；重复提交不得产生第二个相同业务 Delegation。
5. Worker Agent 的输入必须显式声明，禁止隐式复制全部父 Execution context。
6. Worker 结果必须持久化并关联父 Execution、Delegation、Trace / Audit。
7. Worker 成功、失败、超时、取消都必须形成明确状态。
8. Orchestrator 必须能依据 Worker 结果继续、失败或进入既有 retry / recovery 语义。
9. 必须阻止无限递归委派。
10. 必须限制同一 Orchestrator Execution 的活动 Delegation 数量。
11. Model Provider / Profile 选择继续遵循现有治理 Contract，不允许 Worker 绕过模型治理。
12. 所有跨 Agent 的权限、tenant、版本 lineage 必须 fail-closed。

### 3.2 首版明确不支持

- 跨 tenant Agent 调用；
- 任意 Agent 自发现与自动组网；
- 无上限动态 Agent spawning；
- 跨 Execution 共享未授权上下文；
- Agent Marketplace / 模板市场；
- MQ/Kafka/Event Bus；
- Saga / 分布式补偿框架；
- 独立于现有 Workflow Execution 的第二套可靠性状态机。

## 4. Backend Contract

### 4.1 Delegation Identity

Delegation 的业务幂等键至少由以下稳定字段组成：

```text
tenant_id
source_execution_id
source_agent_version_id
target_agent_version_id
delegation_key
```

`worker_owner`、lease token、进程 ID 等 ephemeral 字段不得进入业务幂等身份。

### 4.2 Tenant / Version / Permission Guard

创建 Delegation 时必须同时校验：

```text
source execution tenant == request tenant
source agent version tenant == request tenant
target agent version tenant == request tenant
target agent version == published / runnable
caller has existing workflow execution permission
```

任一 lineage 或权限条件不满足时直接拒绝，不通过“查不到再创建”形成隐式跨租户行为。

### 4.3 Delegation 状态

首版状态固定为：

```text
pending → running → completed
                 ↘ failed
                 ↘ timed_out
pending → cancelled
running → cancelled
```

终态：`completed / failed / timed_out / cancelled`。

终态 Delegation 不得再次进入 Worker Claim。

### 4.4 并发与预算

每个父 Execution 必须有显式 `max_active_delegations` 限制；达到限制时新 Delegation 必须 fail-closed，不得静默排队到无限集合。

首版必须同时具备：

- `max_delegation_depth`：限制递归委派层数；
- `max_active_delegations`：限制父 Execution 同时活动的子任务数量；
- `timeout_seconds`：限制单次 Delegation 生命周期；
- `model_budget`：复用现有 Model Provider / Profile 治理与成本/用量约束。

默认值必须由治理配置提供，业务代码不得硬编码企业级预算策略。

### 4.5 Context Isolation

Worker 只接收 Delegation 明确声明的输入：

```text
input_data
selected_context_refs
allowed_tools
model_profile / capability constraints
```

不得默认复制：

- 父 Agent 全部 memory；
- 父 Execution 全部 checkpoint state；
- 父 Agent 未授权的 tool credential；
- 其他 tenant 数据。

### 4.6 Failure / Retry / Timeout

Worker Failure 不得直接修改父 Execution 的 terminal 状态。父流程必须根据既有 Workflow / Execution Contract 决定：继续、retry、失败或恢复。

Delegation timeout 只结束 Delegation 自身；父 Execution 是否 retry / recover 必须由既有 Durable Execution Contract 决定。

不得为 Multi-Agent 单独创建第二套 Retry / Recovery 状态机。

### 4.7 Idempotency

同一 `tenant + source_execution + delegation_key` 的重复创建必须返回已有 Delegation 或明确的幂等命中结果。

Worker completion 必须具备 fencing / ownership 校验；stale Worker 不得覆盖已完成、已取消或新一代 Worker 的结果。

### 4.8 Audit / Trace

至少形成：

```text
source execution
  └── delegation
        └── worker execution / trace
```

必须能够从任一 Worker 结果反查父 Execution，并从父 Execution 定位所有 Delegation。

Audit / Trace 中只记录允许暴露的 metadata；Secret、credential 原文和未授权上下文不得进入记录。

## 5. API Contract 原则

首版 API 只暴露明确的 Delegation 生命周期能力：

```text
POST   /executions/{execution_id}/delegations
GET    /executions/{execution_id}/delegations
GET    /executions/{execution_id}/delegations/{delegation_id}
POST   /executions/{execution_id}/delegations/{delegation_id}/cancel
```

API 不直接暴露 Worker 内部 lease、进程 owner 或数据库状态字段作为业务 Contract。

Request 必须显式包含 `target_agent_version_id`、`delegation_key`、`input_data`，以及可选的受治理 budget / timeout / context refs。

Response 至少包含 `id`、`status`、`source_execution_id`、`target_agent_version_id`、`created_at`、`updated_at` 与可追踪的 trace identity。

## 6. 数据模型方向

预计新增单一 `agent_delegations` Durable Entity；不复制 Workflow Execution 的完整状态模型。

至少需要：

```text
tenant_id
source_execution_id
source_agent_version_id
target_agent_version_id
delegation_key
status
input_data / context refs
budget / timeout
depth
worker_execution_id (nullable)
trace_id
created_at / started_at / ended_at
error_code / error_message
```

Migration 必须在 Contract 通过后独立设计，并补充 tenant、幂等、状态与 lineage 约束。

## 7. 测试与验收 Contract

必须覆盖：

### Unit

- delegation identity；
- tenant / version / permission guard；
- depth / active-count budget；
- context isolation；
- lifecycle transition；
- duplicate creation；
- stale completion fencing；
- timeout / cancellation；
- parent Execution failure semantics。

### Integration

- PostgreSQL persistence；
- unique constraint / concurrent duplicate convergence；
- parent Execution 与 Delegation lineage；
- Worker completion transaction boundary。

### Real API

必须证明真实 HTTP + PostgreSQL：

1. 创建合法 Delegation；
2. 重复 delegation key 幂等收敛；
3. 跨 tenant / 未发布 target Agent 被拒绝；
4. Worker 结果持久化；
5. timeout / cancel 状态真实落库；
6. Audit / Trace 可反查父子关系；
7. 2+ Worker 对多个 Delegation 的 durable ownership / drain 能够正确收敛。

### Browser E2E

仅在实际增加前端 Delegation UI 后加入，不复制 Backend Gate。

## 8. 开发顺序

```text
Phase 2.8-A Contract 冻结
        ↓
Backend Domain + API Contract        ✅ 已实现
        ↓
Alembic Migration                    ✅ 已实现
        ↓
Unit / Integration / API Contract   ✅ 已实现并通过当前 targeted / regression 范围
        ↓
Runtime Integration                  ✅ 已完成
        ↓
Real API Gate                        ✅ B6 已通过
        ↓
Backend Regression                  ✅ B6 Gate 已通过
        ↓
Frontend API Types / UI（如需要）   本 Phase 未新增专用 Delegation UI
        ↓
Browser E2E（如需要）               不作为本 Phase 必选门槛
```

## 9. 当前决策

Phase 2.8-A Contract 已冻结并完成生产实现。当前不再重复讨论基础 Delegation 数据模型或 API 边界；Runtime Integration 已由 B1-B6 完成并获得真实 HTTP + PostgreSQL + 多 Worker 验收证据。

当前实现状态：

- Delegation Durable Entity / Repository / Service：已实现；
- create/list/get/cancel API：已实现；
- tenant/version/permission/idempotency/budget：已实现；
- lifecycle / Worker completion fencing 纯规则：已实现；
- Atomic Worker Claim：已实现并验收；
- Worker Execution bridge：已实现并验收；
- generation-fenced completion persistence：已实现并验收；
- timeout/cancel runtime：已实现并验收；
- Audit / Trace runtime closure：已实现并验收；
- Multi-worker Durable Frontier runtime：已实现并通过 B6 Real Gate；
- PostgreSQL Integration / Real API Runtime acceptance：已完成当前 Phase 范围验收。

后续实现必须继续复用既有 Workflow Worker / lease / fencing / retry / recovery 能力，不创建第二套可靠性状态机。
