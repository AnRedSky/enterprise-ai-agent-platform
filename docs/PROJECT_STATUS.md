# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前基线：`18c54b14` — `fix(delegation): synchronize terminal DML identity`
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
- B1 Atomic Claim 已完成生产实现，并已通过本地真实 HTTP + PostgreSQL 双 Worker 并发 Gate；
- B2 Worker Execution Bridge 已进入生产代码，复用现有 Workflow Worker / WorkflowRuntime 执行目标 Agent version；
- B3 Delegation completion/failure 已进入生产代码，以 `worker_execution_id` 作为 Worker generation fencing identity；
- B2 Runtime Session / Execution terminalization / Model Profile Snapshot 等前置问题已经完成修复；
- Delegation terminal write 已增加 tenant + running + worker generation fencing，并使用 PostgreSQL `UPDATE ... RETURNING`。

## 3. 最新本地验收反馈

开发者在 `d8e89757` 本地实际执行 B2 Gate：

```text
B2 bridge Unit             3 passed
Backend regression         850 passed, 3 skipped, 46 deselected
Migration/head             0039_workflow_node_execution_tenant_trigger (head)
B2 Real Gate               1 failed, 2 passed
```

失败为：

```text
assert persisted.status == "completed"
E AssertionError: assert 'running' == 'completed'
```

该结果确认 Target Agent Runtime、Worker Execution terminalization 与 generation context 均已正常工作，问题进一步收敛到 Delegation terminal DML 与当前 SQLAlchemy identity map 的同步边界。

## 4. 本轮修复

completion/failure 的终态 UPDATE 现在同时使用：

- tenant + `running` + `worker_execution_id` 三重数据库 fencing；
- PostgreSQL `UPDATE ... RETURNING AgentDelegation`；
- `synchronize_session="fetch"`；
- `populate_existing=True`；
- completion/failure、AuditLog、WorkflowTraceEvent 同一事务提交。

该修复只调整 Delegation terminal persistence 的 ORM synchronization 边界，不新增 Worker、Lease、Retry、Recovery 或 Provider 实现。

对应错误记录：`docs/04-errors/2026-08-28-phase-2-8-b2-b3-delegation-terminal-dml-session-sync.md`。

## 5. B2 当前实现边界

```text
B1 Claim
    ↓
WorkflowExecution.worker_execution_id
    ↓
AgentDelegationRuntimeBridge
    ↓
单 Node 内存 Runtime Version
    ↓
既有 DurableResumeWorkflowRuntime
    ↓
既有 WorkflowRuntime
    ↓
Target Agent published version
    ↓
Worker Execution terminalization
    ↓
当前 Worker AsyncSession 中 Delegation completion/failure
    ↓
tenant + running + worker_execution_id fencing
    ↓
UPDATE ... RETURNING + Session fetch/populate_existing
```

B2 不创建第二套 Worker、Lease、Retry、Recovery 或 Provider；不修改父 Workflow Version 数据库记录，不复制父 Execution checkpoint、memory 或 credential。

## 6. B3 当前实现

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
                           ▼
                 fenced UPDATE ... RETURNING
                           │
                           ├── Session synchronization
                           ├── AuditLog
                           └── WorkflowTraceEvent
```

B3 不允许旧 Worker generation 修改新 generation 的 Delegation 状态；Worker lease 丢失时不提前收敛 Delegation。

## 7. 自动化验收

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

## 8. 当前未完成

| 能力 | 状态 |
|---|---|
| B1 Atomic Claim | ✅ 本地真实验收通过 |
| B2 Worker Execution Bridge 生产实现 | ✅ |
| B2 Bridge Unit | ✅ 本地 3 passed |
| B2 Backend regression | ✅ 本地 850 passed, 3 skipped, 46 deselected |
| B2 Real HTTP + PostgreSQL + Runtime | 🔧 Session synchronization 修复，待本地复跑 |
| B3 completion/failure + generation fencing 生产实现 | ✅ |
| B3 Unit / Backend regression | ✅ 本地 30 passed / 850 passed |
| B3 Real HTTP + PostgreSQL completion/fencing | 🔧 B2 修复后待本地复跑 |
| B4 timeout/cancel/parent semantics | ⏳ 尚未进入生产实现 |
| B5 Audit/Trace 完整闭环 | ⏳ |
| Delegation Runtime multi-worker acceptance | ⏳ |

## 9. 下一开发顺序

```text
同步最新 main
    ↓
修复 Delegation terminal DML Session synchronization 边界
    ↓
B2 Bridge Unit + Backend Regression + Migration
    ↓
B2 Real HTTP + PostgreSQL + Runtime 本地复验
    ↓
B3 Delegation completion/failure Gate 本地复验
    ↓
若 Real Gate 有问题 → 立即修复并记录 docs/04-errors/
    ↓
B2/B3 本地验收闭环
    ↓
B4 timeout / cancel / parent semantics
    ↓
B5 Audit / Trace
    ↓
Delegation 多 Worker + PostgreSQL + Runtime acceptance
```

## 10. 测试规则

开发者本地实际执行结果为唯一测试依据；GitHub Actions 不作为验收依据。当前修复在开发者本地重新执行 B2/B3 Real Gate 前，不标记为通过。