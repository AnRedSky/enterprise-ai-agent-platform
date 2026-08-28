# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前代码提交：`61c1a482` — `fix(test): align auth contract with default organization binding`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B3 Delegation completion / failure + generation fencing**

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

开发者最新实际反馈基线为 `0f9bdc7f`：

```text
B2 Bridge Unit             3 passed
B2 Backend regression      848 passed, 3 skipped, 46 deselected
B2 Real Gate               2 failed, 1 passed
B3 Backend regression      848 passed, 3 skipped, 46 deselected
B3 Real Gate               2 failed, 1 passed
```

B2/B3 Real Gate 的两个业务/测试问题已经分别完成修复：

1. `d5d3129a`：注册用户绑定默认 Organization，消除真实 Worker Runtime 的 `403 当前用户没有有效的 Organization membership`；
2. `2198ef4c`：B3 fencing rollback 后使用独立 UUID，消除 `MissingGreenlet`；
3. `61c1a482`：同步修复 Backend Contract 测试 FakeDB，使其反映新的默认 Organization 注册契约，并增加 Organization 缺失的 409 Contract 覆盖。

**注意：`61c1a482` 之后的 B2/B3 Gate 尚未由开发者本地重新执行，因此当前不能宣称 B2/B3 Real Gate 通过。**

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

## 6. B3 自动化验收

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

Gate 自动完成：

1. Delegation lifecycle Unit；
2. Backend default regression；
3. Alembic upgrade/head；
4. 自动启动 PostgreSQL / Redis；
5. 自动启动 Backend（未运行时）；
6. 自动注册临时用户并登录取得 Token；
7. 真实 HTTP 创建 Orchestrator / Target Agent / Workflow / Delegation；
8. 真实 PostgreSQL Claim；
9. 通过现有 Worker Runtime 执行 Target Agent；
10. 验证 Worker Execution completed 后 Delegation 自动 completed；
11. 使用随机旧 Worker generation 调用 completion，验证被 fencing 拒绝且 Delegation 保持 running；
12. 验证 Worker Execution failed 后当前 generation 能将 Delegation 收敛为 failed，并持久化 error code/message。

禁止手工填写 Token、用户名、密码、tenant、ID 或测试数据。

## 7. 当前未完成

| 能力 | 状态 |
|---|---|
| B1 Atomic Claim | ✅ 本地真实验收通过 |
| B2 Worker Execution Bridge 生产实现 | ✅ |
| B2 Bridge Unit | 🔧 修复后待本地复跑 |
| B2 Real HTTP + PostgreSQL + Runtime | 🔧 修复后待本地复跑 |
| B3 completion/failure + generation fencing 生产实现 | ✅ |
| B3 Unit / Real Gate | 🔧 修复后待本地复跑 |
| B4 timeout/cancel/parent semantics | ⏳ 尚未进入生产实现 |
| B5 Audit/Trace 完整闭环 | ⏳ |
| Delegation Runtime multi-worker acceptance | ⏳ |

## 8. 下一开发顺序

```text
同步最新 main
    ↓
Backend Contract regression
    ↓
B2 Worker Execution Bridge Gate
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

**B1 已本地真实 PostgreSQL 双 Worker Gate 验收通过。B2/B3 生产实现及其已知回归问题均已修复；最新修复提交为 `61c1a482`。但修复后的 B2/B3 Real Gate 尚未产生新的开发者本地实际结果，因此当前仍处于“修复后待验收”状态。通过后立即进入 B4 timeout / cancel / parent semantics。**
