# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B5 Audit / Trace closure**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- B1 Atomic Claim 已完成并通过本地真实 HTTP + PostgreSQL 双 Worker 并发 Gate；
- B2 Worker Execution Bridge 已完成，复用既有 Workflow Worker / WorkflowRuntime；
- B3 Delegation completion/failure generation fencing 已完成；
- B4 timeout / cancel / parent semantics 已完成并由开发者本地 Real Gate 验收通过；
- Runtime Session / Execution terminalization / Model Profile Snapshot / Frontier heartbeat 锁序问题已完成修复；
- Scheduler 对单节点顺序 Workflow 的空 `edges` 语义已与 DAG Runtime 对齐；
- B5 Delegation Audit / Trace 基础闭环已实现，创建与取消事件已写入 AuditLog / WorkflowTraceEvent。

## 3. 最新本地验收证据

开发者在 `d5fd0639` 基线完成 B4：

```text
B4 timeout Unit            25 passed
Backend regression         858 passed, 3 skipped, 48 deselected
Migration/head             0039_workflow_node_execution_tenant_trigger (head)
B4 Real Gate               5 passed
```

B5 当前首次执行发现 Worker shutdown 单元测试阻塞：

```text
25 passed, 1 failed, 1 teardown error
```

失败原因为测试直接 monkeypatch `AsyncEngine.dispose` 实例属性，而 `AsyncEngine.dispose` 为只读属性；同时实际运行 Worker 时观察到 asyncpg connection close 阶段 `CancelledError`。

该问题已完成根因分析并在 `b789b4538f2a3e1b38dcb5ab40e22723bcd5e6cc` / `91972538cf87e70e496ef306d2294406056d7ce2` 修复：Worker 关闭路径增加 cancellation-safe engine disposal，测试改为替换正式关闭边界并覆盖取消后的二次 dispose。

**以上修复尚未由本环境实际执行验证，因此不得标记 B5 Passed。**

## 4. B5 目标

B5 要求形成完整的父子审计与 Trace 闭环：

```text
source execution
  └── delegation
        └── worker execution
              └── trace
```

必须覆盖：

1. created / running 生命周期事实；
2. completed / failed / timed_out / cancelled 全终态 Audit / Trace；
3. `trace_id`、父 Execution、Delegation、Worker Execution 的身份链路一致；
4. generation fencing 后的迟到 completion/failure 不得覆盖终态；
5. Audit/Trace metadata 不得写入 Secret / credential 原文；
6. parent Execution 不被 Delegation 子任务终态直接终止。

## 5. B5 自动化验收

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\05_delegation_audit_trace_gate.ps1
```

Gate 只验证本地前置服务，不启动、重启或停止服务；测试用户、Token、tenant、ID 与测试数据由 Gate 自动生成。

验收顺序：

```text
[0] prerequisite service verification
    ↓
[1] Worker shutdown + Delegation lifecycle Unit
    ↓
[2] Backend default regression
    ↓
[3] Alembic upgrade/head
    ↓
[4] Real HTTP + PostgreSQL Delegation Audit/Trace closure
```

修复后的本地执行必须实际证明 Gate 全部通过后，才允许继续 Phase 2.8 closure。

## 6. 下一主线任务

```text
B5 Audit / Trace closure
    ↓
Delegation 多 Worker + PostgreSQL + Runtime acceptance
    ↓
Phase 2.8 closure
    ↓
Phase 2.9 Enterprise Integration / Event Infrastructure Contract
```
