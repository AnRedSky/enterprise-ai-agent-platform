# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前基线：`67e8379f` — `fix(worker): isolate delegation finalization transaction boundary`
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
- Delegation terminal write 已增加 tenant + running + worker generation fencing，并完成 ORM bulk DML 同步边界整改；
- B2/B3 Real Gate 当前采用**只校验、不启动服务**的本地前置检查，测试用户、Token、fixture 与测试数据均由 Gate 自动生成。

## 3. 最新本地验收反馈

开发者在 `099ee1b6` 本地实际执行 B2 Gate：

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

该结果确认 Target Agent Runtime、Worker Execution terminalization 与 generation context 均已正常工作；此前多轮 terminal DML identity 修复仍未消除独立 Real Gate 查询看到 `running` 的问题，因此本轮进一步收敛事务边界，而不是继续堆叠 ORM identity synchronization 选项。

## 4. 本轮修复

`67e8379f` 将 Delegation finalization 从 Worker Runtime 的长生命周期 AsyncSession 中隔离：

- 在 Runtime 开始前快照 `tenant_id`、`worker_execution_id` 等不可变 generation identity；
- Workflow Runtime / Worker Execution terminalization 继续使用既有 Runtime Session；
- Delegation completion/failure 改为创建独立 `SessionLocal()`；
- 独立 Session 重新读取并校验 Worker Execution tenant boundary；
- `complete_delegation()` / `fail_delegation()` 继续复用既有 generation fencing、AuditLog、WorkflowTraceEvent 与原子事务；
- 不再在 Runtime Session 的 commit/refresh 生命周期内耦合 Delegation terminal write；
- 不恢复 ORM bulk DML，也不增加第二套 Worker、Lease、Retry、Recovery 或 Provider。

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
Worker Execution terminalization（Runtime Session）
    ↓
快照 tenant + worker generation identity
    ↓
独立 Delegation finalization Session
    ↓
tenant + running + worker_execution_id fencing
    ↓
Delegation completed / failed + AuditLog + WorkflowTraceEvent
```

B2 不创建第二套 Worker、Lease、Retry、Recovery 或 Provider；不修改父 Workflow Version 数据库记录，不复制父 Execution checkpoint、memory 或 credential。

## 6. B3 当前实现

```text
Worker Runtime
    │
    ├── completed ────────┐
    │                      ▼
    │              独立 finalization Session
    │                      │
    └── failed ───────────► complete/fail_delegation()
                           │
                           ▼
                 SELECT Delegation FOR UPDATE
                           │
                           ▼
                 validate_worker_fence()
                           │
                           ▼
                 fenced terminal write
                           │
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

Gate 只负责验证本地前置服务，不自动启动任何服务：

- PostgreSQL：必须已运行；
- Redis：必须已运行；
- Backend API：必须已运行并通过 `/health`；
- Gate 不调用 `docker compose up`；
- Gate 不调用 `uvicorn` / `Start-Process`；
- 测试用户、Token、tenant、organization、Agent、Workflow、Delegation fixture 与测试数据均由脚本自动生成，不需要手工填写。

## 8. 当前未完成

| 能力 | 状态 |
|---|---|
| B1 Atomic Claim | ✅ 本地真实验收通过 |
| B2 Worker Execution Bridge 生产实现 | ✅ |
| B2 Bridge Unit | ✅ 本地 3 passed |
| B2 Backend regression | ✅ 本地 850 passed, 3 skipped, 46 deselected |
| B2 Real HTTP + PostgreSQL + Runtime | 🔧 独立 finalization transaction boundary 修复，待本地复跑 |
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
隔离 Delegation finalization transaction boundary
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