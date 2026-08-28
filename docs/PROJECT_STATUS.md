# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前代码基线：`989d87d8` — `fix(worker): close runtime session before delegation finalization`
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
- Delegation terminal write 已完成 tenant + running + worker generation fencing 与 ORM bulk DML 边界整改；
- 当前进一步修复 Runtime Session 与 Delegation finalization Session 的实际生命周期边界。

## 3. 最新本地验收反馈

开发者在 `612dbf55` 本地实际执行 B2 Gate：

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

该结果再次确认 Target Agent Runtime、Worker Execution terminalization 与 generation context 均已正常工作；此前多轮 terminal DML 与独立 Session 修复仍未消除问题，因此不能继续把问题描述为单纯 ORM identity synchronization。

## 4. 本轮真实修复

`989d87d8` 将 Delegation finalization 的生命周期边界继续前移：

- Runtime 开始前快照不可变的 tenant / Worker generation identity；
- Runtime 与 Worker Execution terminalization 使用既有 Runtime Session；
- Runtime `finally` 中先关闭 Runtime Session，释放事务、连接与锁；
- Runtime Session 完全关闭后，才进入 Delegation 独立 finalization Session；
- finalization Session 重新读取 Worker Execution 并执行 tenant + running + worker generation fencing；
- Delegation terminal state、AuditLog、WorkflowTraceEvent 继续原子提交；
- 不增加第二套 Worker、Lease、Retry、Recovery 或 Provider。

这次修复针对的是此前“独立 Session 但生命周期仍重叠”的真实边界缺陷，而不是继续调整同一条 DML 语句。

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
Worker Execution terminalization（Runtime Session）
    ↓
关闭 Runtime Session
    ↓
独立 Delegation finalization Session
    ↓
tenant + running + worker_execution_id fencing
    ↓
Delegation completed / failed + AuditLog + WorkflowTraceEvent
```

## 6. B3 当前实现

B3 不允许旧 Worker generation 修改新 generation 的 Delegation 状态；Worker lease 丢失时不提前收敛 Delegation。completion/failure 必须在 Runtime Session 关闭后执行独立终态事务。

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

Gate 只负责验证本地前置服务，不自动启动任何服务：PostgreSQL、Redis、Backend API 必须已经运行并满足健康检查。测试用户、Token、tenant、organization、Agent、Workflow、Delegation fixture 与测试数据均由脚本自动生成，不需要手工填写。

## 8. 当前未完成

| 能力 | 状态 |
|---|---|
| B1 Atomic Claim | ✅ 本地真实验收通过 |
| B2 Worker Execution Bridge 生产实现 | ✅ |
| B2 Bridge Unit | ✅ 本地 3 passed |
| B2 Backend regression | ✅ 本地 850 passed, 3 skipped, 46 deselected |
| B2 Real HTTP + PostgreSQL + Runtime | 🔧 `989d87d8` 生命周期边界修复，待本地复跑 |
| B3 completion/failure + generation fencing 生产实现 | ✅ |
| B3 Unit / Backend regression | ✅ |
| B3 Real HTTP + PostgreSQL completion/fencing | 🔧 B2 修复后待本地复跑 |
| B4 timeout/cancel/parent semantics | ⏳ 尚未进入生产实现 |
| B5 Audit/Trace 完整闭环 | ⏳ |
| Delegation Runtime multi-worker acceptance | ⏳ |

## 9. 下一开发顺序

```text
同步最新 main
    ↓
验证 Runtime Session 完全关闭后的 Delegation finalization
    ↓
B2 Real HTTP + PostgreSQL + Runtime 本地复验
    ↓
B3 Delegation completion/failure Gate 本地复验
    ↓
若 Real Gate 有问题 → 依据新的实际堆栈与数据库终态继续修复
    ↓
B2/B3 本地验收闭环
    ↓
B4 timeout / cancel / parent semantics
    ↓
B5 Audit / Trace
    ↓
继续 Phase 2.8 主线任务
```