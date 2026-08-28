# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前代码提交：`2daeeb62` — `docs(errors): record B2 real gate provider coupling`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B2 Worker Execution Bridge Real Gate 修复与本地验收**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力已完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施已完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- lifecycle / Worker fencing 纯规则入口已建立；
- B1 Atomic Claim 已完成生产实现：PostgreSQL Delegation 行锁、真实 `WorkflowExecution`、Worker owner/lease、`worker_execution_id` 与同事务持久化；
- B1 Real HTTP + PostgreSQL 双 Worker 并发 Gate 已由开发者本地实际执行并通过；
- ORM metadata registry 已修复跨模块 ForeignKey 运行时注册问题；
- B2 Worker Execution Bridge 已进入生产代码：已 Claim Execution 通过正式 Delegation Runtime Bridge 显式装配 target Agent version、model profile、input、selected context refs、allowed tools 与 trace identity，并复用现有 Workflow Worker / WorkflowRuntime；
- B2 synthetic Runtime 已修复与 DAG validator 的 Contract 冲突；
- B3 Delegation completion/failure 已进入生产代码：以 `worker_execution_id` 作为 Worker generation fencing identity，在当前 generation 仍有效且 Worker Execution 已进入对应终态时收敛 Delegation；
- 注册用户现在在同一事务中绑定默认 Tenant 对应的 active Organization，保证后续 Governance membership 边界成立。

## 3. 最新本地验收反馈

开发者在当前 `main`（`2daeeb62`）实际执行：

```text
B2 bridge Unit             3 passed
B2 Backend regression      850 passed, 3 skipped, 46 deselected
B2 Migration/head          0039_workflow_node_execution_tenant_trigger (head)
B2 Real Gate               1 failed, 2 passed
```

失败发生在 `test_b2_worker_execution_bridge_runs_target_agent_version` 的 Real PostgreSQL Fixture 阶段：

```text
assert delegation.model_profile_id is not None
E assert None is not None
```

根因是此前为隔离外部 Provider 增加的测试 Fixture 仍假设 Delegation 在创建后已经带有 `model_profile_id`。当前 Real Gate 创建的 Target Agent 使用 `model_id=mock-model` 但没有显式 Model Profile，因此 Delegation 合法地继承了 `NULL` profile，测试辅助函数却无法从不存在的 profile 推导 Organization。

本次修复改为直接从 Delegation 的 Target Agent version 与 Delegation tenant 查询对应 Organization，再自动创建独立 `provider_type=mock` / `model_name=mock-model` Profile 并绑定 Delegation。该修复仍保持真实 HTTP + PostgreSQL + Worker Runtime 链路，不修改生产 Provider fallback 语义。

## 4. B2 当前实现边界

```text
B1 Claim
    ↓
WorkflowExecution.worker_execution_id
    ↓
AgentDelegationRuntimeBridge
    ├── target_agent_version_id
    ├── target_agent_id
    ├── model_profile_id
    ├── input_data
    ├── selected_context_refs
    ├── allowed_tools
    └── trace_id
    ↓
单 Node 内存 Runtime Version
    ↓
既有 DurableResumeWorkflowRuntime
    ↓
既有 WorkflowRuntime
    ↓
Target Agent published version
    ↓
既有 ModelGateway / Governance / Provider
```

B2 不创建第二套 Worker、Lease、Retry、Recovery 或 Provider；不修改父 Workflow Version 数据库记录，不复制父 Execution checkpoint、memory 或 credential。

B2 synthetic Runtime 是单 Node 执行对象，不属于持久化 DAG，因此 Definition 不声明 `edges`。

Real Gate 的 Model Provider Fixture 必须由测试自动建立并绑定，不得依赖开发数据库中的默认 Provider/Profile。

## 5. B3 当前实现

```text
Worker Runtime
    │
    ├── completed ────────┐
    │                      ▼
    │              complete_delegation()
    │                      │
    └── failed ───────────► fail_delegation()
                           │
                           ▼
                 SELECT Delegation FOR UPDATE
                           │
                           ▼
                 validate_worker_fence()
                           │
                           ├── status == running
                           ├── worker_execution_id 存在
                           └── generation == 当前 Worker Execution
                           │
                           ▼
                 Delegation terminal state
                           │
                           ├── AuditLog
                           └── WorkflowTraceEvent
```

B3 明确不允许旧 Worker generation 修改新 generation 的 Delegation 状态。Worker lease 丢失时不提前收敛 Delegation，保留后续有效 generation 接管的空间。

B3 completion/failure 不改变父 Workflow Execution；Target Worker Execution 的生命周期仍由既有 WorkflowExecutionService 管理。

## 6. 自动化验收

B2 正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
```

B3 正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

Gate 自动完成 PostgreSQL / Redis 启动、Backend 健康检查与必要时自动启动、临时用户注册登录、Token 注入、Real HTTP fixture、数据库 migration/head 验证及 Real API 测试；开发者不需要手工填写 Token、用户名、密码、tenant、organization、ID、Provider endpoint 或测试数据，也不需要手工启动服务。

## 7. 当前未完成

| 能力 | 状态 |
|---|---|
| B1 Atomic Claim | ✅ 本地真实验收通过 |
| B2 Worker Execution Bridge 生产实现 | ✅ |
| B2 Bridge Unit | ✅ 本地 3 passed |
| B2 Backend regression | ✅ 本地 850 passed, 3 skipped, 46 deselected |
| B2 Real HTTP + PostgreSQL + Runtime | 🔧 Fixture 修复后待本地复跑 |
| B3 completion/failure + generation fencing 生产实现 | ✅ |
| B3 Unit / Real Gate | 🔧 B2 修复后待本地复跑 |
| B4 timeout/cancel/parent semantics | ⏳ 尚未进入生产实现 |
| B5 Audit/Trace 完整闭环 | ⏳ |
| Delegation Runtime multi-worker acceptance | ⏳ |

## 8. 下一开发顺序

```text
同步最新 main
    ↓
修复 B2 Real Gate Model Profile Fixture
    ↓
B2 Bridge Unit + Backend Regression + Migration
    ↓
B2 Real HTTP + PostgreSQL + Runtime
    ↓
B3 Delegation completion/failure Gate
    ↓
若 Real Gate 有问题 → 立即修复并记录 docs/04-errors/
    ↓
B3 本地验收闭环
    ↓
B4 timeout / cancel / parent semantics
    ↓
B5 Audit / Trace
    ↓
Delegation 多 Worker + PostgreSQL + Runtime acceptance
```

## 9. 测试规则

开发者本地实际执行结果为唯一测试依据；GitHub Actions 不作为验收依据。

B1 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\01_delegation_contract_gate.ps1
```

B2 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
```

B3 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

Real API Gate 自动生成临时身份与 Token，不要求开发者手工输入任何信息。

## 10. 当前结论

**B1 已本地真实 PostgreSQL 双 Worker Gate 验收通过。B2/B3 生产实现及此前已知回归均已修复；当前最新本地反馈暴露的是 B2 Real Gate 测试 Fixture 对可选 `model_profile_id` 的错误前置假设。本次提交修复该测试隔离问题后，必须重新由开发者本地实际执行 B2 Gate，再执行 B3 Gate；在新的实际结果产生前，不得标记 B2/B3 Real Gate 通过。B2 Real Gate 通过后立即进入 B3 本地验收闭环，再进入 B4 timeout / cancel / parent semantics。**
