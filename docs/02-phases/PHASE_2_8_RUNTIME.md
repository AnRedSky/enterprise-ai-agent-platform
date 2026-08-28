# Phase 2.8 Delegation Runtime Integration — Worker 生命周期与执行闭环

## 1. 当前状态

Phase 2.8-A Multi-Agent Collaboration Contract 已冻结，Delegation Domain + API Contract 已实现。当前进入 Runtime Integration：把已有 `AgentDelegation` 接入现有 Workflow Worker / lease / fencing 体系，不创建第二套 Worker、Retry 或 Recovery 状态机。

最新 `main`：`37061abb99fefbf753c088f6644f24d289814c39`。

## 2. 已完成

### Domain / API

- `AgentDelegation` Durable Entity；
- tenant / source execution / source agent version / target agent version lineage；
- stable delegation identity 与并发幂等；
- depth / active-count / timeout / model budget；
- create/list/get/cancel API；
- Audit / Trace 基础事件；
- active budget creation 的父 Execution 行锁序列化。

### Lifecycle Contract

`37061ab` 新增 `backend/app/services/agent_delegation/lifecycle.py`，统一定义：

```text
pending → running / cancelled
running → completed / failed / timed_out / cancelled
terminal → closed
Worker completion → running + worker_execution_id generation 必须一致
timeout → now >= timeout_at
```

对应 Unit 覆盖状态转换、终态封闭、stale generation、缺失 owner 与 timeout 边界。

**注意：该提交后的 Unit/Regression 尚未获得新的开发者本地实际结果，因此本文件不标记其为 PASS。**

## 3. 当前核查结论

当前 Delegation 已经具备“可治理的任务实体”，但还不具备“可由 Worker 实际执行的运行时闭环”。核心缺口集中在 ownership，而不是 API：

```text
API create
    ↓
pending Delegation
    ↓  ← 当前缺口：Atomic Claim
running + worker_execution_id
    ↓  ← 当前缺口：Worker Execution bridge
Agent Runtime
    ↓
completion / failure / timeout / cancel
    ↓  ← 当前缺口：generation-fenced persistence
Audit / Trace / parent workflow semantics
```

## 4. 当前执行任务拆解

### B1 — Atomic Delegation Claim

建立 tenant-scoped 原子 Claim：

1. 仅 `pending` 可 Claim；
2. PostgreSQL 条件更新或行锁保证单一 ownership；
3. Claim 时生成唯一 `worker_execution_id`；
4. 并发 Worker 只有一个 generation 成功；
5. timeout / cancelled / terminal Delegation fail-closed；
6. 不引入独立 Worker lease 模型。

### B2 — Workflow Worker Execution Bridge

复用现有 Worker execution 体系，把以下信息显式传递：

- target Agent version；
- model profile；
- `input_data`；
- `selected_context_refs`；
- `allowed_tools`；
- delegation trace identity。

不得默认复制父 Execution checkpoint、memory 或未授权 credential。

### B3 — Generation-fenced Completion

Worker 完成、失败、timeout、cancel 必须经过统一 lifecycle rule，并在事务中重新确认当前 `worker_execution_id`。旧 generation 即使晚到，也不得覆盖新 generation 或终态事实。

### B4 — Parent Workflow Semantics

Delegation failure/timeout/cancel 不直接终止父 Execution。父 Workflow 根据既有 Execution / Retry / Recovery Contract 决定后续行为。

### B5 — Audit / Trace Closure

完成：

```text
source execution
  └── delegation
        └── worker execution / trace
```

要求可双向追溯，且 metadata 中不得包含 Secret / credential 原文。

## 5. 验收矩阵

| 场景 | 必须证明 |
|---|---|
| 合法 Claim | pending → running，产生唯一 worker generation |
| 并发 Claim | 2+ Worker 竞争时仅一个成功 |
| stale completion | 旧 generation 不得覆盖当前状态 |
| completed fencing | 完成后再次 completion 必须拒绝 |
| cancel fencing | cancel 后迟到 Worker 不得写回 |
| timeout fencing | timeout 后迟到 Worker 不得写回 |
| Worker execution | target Agent version 按治理配置真实执行 |
| Context isolation | 只传显式 input/context/tool refs |
| Failure semantics | Worker failure 不绕过父 Workflow terminalization |
| Audit / Trace | 子任务可反查父 Execution |
| PostgreSQL | 状态与 generation 在真实数据库中一致 |

## 6. 本地测试入口

### Unit

```powershell
cd backend
uv run pytest tests/unit/test_agent_delegation_lifecycle.py -q
```

### Backend regression

```powershell
cd backend
uv run pytest -q
```

### Migration

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

### Real API

Real API / Runtime 需要开发者预先启动 PostgreSQL、Redis、API、Worker、Scheduler；Gate 不自动管理服务进程。

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

后续 B1-B5 应增加独立 targeted Real API 入口，覆盖多 Worker 竞争、stale completion、timeout/cancel 与真实 PostgreSQL 持久化。

## 7. 开发边界

- 不新增 MQ/Kafka；
- 不新增独立 Delegation Worker 进程；
- 不复制 Workflow Retry / Recovery；
- 不改变既有 Durable Frontier 的 checkpoint Contract；
- 不允许跨 tenant / 未发布 Agent version；
- 不把 ephemeral worker owner / process ID 纳入业务幂等身份；
- 所有 runtime ownership 与 completion 都必须可追溯到 `worker_execution_id` generation。

## 8. 下一交付单元

下一次代码交付应以 **B1 Atomic Delegation Claim + Integration/Unit** 为最小完整交付单元；随后再进入 B2/B3。完成 B1 前不要扩展前端 UI，也不要创建与 Worker runtime 无关的平行抽象。
