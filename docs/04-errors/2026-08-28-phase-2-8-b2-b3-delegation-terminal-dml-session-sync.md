# Phase 2.8 B2/B3 Delegation 终态 DML Session 同步边界

## 1. 现象

开发者在远端 `main` 的 `d8e89757` 本地执行 B2 Worker Execution Bridge Gate 时，Unit、Backend Regression 与 Migration/head 均通过，但 Real HTTP + PostgreSQL + Runtime 仍出现：

```text
AssertionError: assert 'running' == 'completed'
```

失败发生在独立 `SessionLocal()` 查询 `AgentDelegation.status` 时；同一条 Worker Execution 已经成功进入 `completed`，Target Agent Runtime 与 Worker Execution terminalization 均正常。

## 2. 根因

Delegation completion/failure 使用 ORM-enabled `UPDATE ... RETURNING AgentDelegation`。当前 Worker Session 在此前的 Runtime Bridge / Claim 链路中已经持有同一 `AgentDelegation` identity；仅使用 `RETURNING` 并不能明确要求 SQLAlchemy 对 identity map 中已有对象执行终态刷新。

因此终态 DML 的数据库 fencing 条件虽然正确，但 ORM Session 的 identity 同步边界仍不够明确，容易让旧的 `running` identity 与本次 terminal write 的返回实体产生不一致。

SQLAlchemy 2.x 对 ORM-enabled UPDATE 支持 `synchronize_session="fetch"`，并允许与显式 `RETURNING` 组合；对已有 identity 使用 `populate_existing` 可以强制用数据库返回值刷新对象。

## 3. 修复

completion/failure 的终态 UPDATE 统一使用：

- tenant + `running` + `worker_execution_id` 三重 fencing；
- PostgreSQL `RETURNING AgentDelegation`；
- `synchronize_session="fetch"`；
- `populate_existing=True`；
- AuditLog、WorkflowTraceEvent 与 terminal write 同一事务提交。

不改变 Worker、Lease、Retry、Recovery、Provider 或父 Workflow Execution 的职责边界。

## 4. 验证要求

必须由开发者本地实际执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

Gate 自动启动 PostgreSQL、Redis，并在 API 未运行时自动启动本地 uvicorn；测试用户、Token、fixture、Provider/Profile 与测试数据均由脚本自动生成，不需要手工输入。

在开发者实际复跑前，不得把 B2/B3 Real Gate 标记为通过。