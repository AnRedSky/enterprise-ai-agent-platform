# Phase 2.8 B2/B3 Delegation 终态持久化事务边界

## 1. 现象

开发者在远端 `main` 的 `099ee1b6` 本地执行 B2 Worker Execution Bridge Gate 时，Unit、Backend Regression 与 Migration/head 均通过，但 Real HTTP + PostgreSQL + Runtime 仍出现：

```text
AssertionError: assert 'running' == 'completed'
```

失败发生在独立 `SessionLocal()` 查询 `AgentDelegation.status` 时；同一条 Worker Execution 已经成功进入 `completed`，Target Agent Runtime 与 Worker Execution terminalization 均正常。

此前已经连续尝试 PostgreSQL `UPDATE ... RETURNING`、ORM `synchronize_session="fetch"`、`populate_existing=True` 以及直接修改已锁定 ORM identity，均未使该 Real Gate 稳定通过。因此不能继续把问题归结为单一 ORM identity synchronization 选项。

## 2. 根因收敛

当前 B2 Worker Runtime 在一个长生命周期 `AsyncSession` 中同时承担：

1. Workflow Runtime 执行；
2. Worker Execution 状态 terminalization；
3. Delegation completion/failure；
4. AuditLog / WorkflowTraceEvent 写入。

Workflow Runtime / Execution lifecycle 本身会多次执行 commit / refresh。虽然 Worker generation 的 UUID 已经提前快照，Delegation terminal write 仍然与 Runtime Session 的 identity、事务提交和 refresh 生命周期耦合。Real Gate 的实际结果表明，单纯调整 Delegation DML 的 ORM 同步策略无法消除该边界问题。

因此本轮将问题进一步收敛为**Runtime terminalization 与 Delegation terminalization 的事务边界设计问题**：两者属于不同 Durable Entity 的终态提交，应通过稳定的 Worker generation identity 关联，而不应依赖同一 ORM Session 的生命周期。

## 3. 修复

`67e8379f` 将 Delegation finalization 调整为独立事务：

- Runtime 开始前快照 `tenant_id`、`worker_execution_id` 与 Delegation identity；
- Workflow Execution terminalization 继续由既有 Runtime Session 负责；
- Delegation completion/failure 在 `finally` 中创建新的 `SessionLocal()`；
- 新 Session 重新读取 Worker Execution，并验证 `tenant_id`；
- `complete_delegation()` / `fail_delegation()` 继续通过 `SELECT ... FOR UPDATE`、tenant boundary 与 `worker_execution_id` generation fencing 收敛状态；
- Delegation terminal state、AuditLog、WorkflowTraceEvent 在独立事务中原子提交；
- 不恢复 ORM bulk DML，不复制 Worker、Lease、Retry、Recovery 或 Provider。

该设计同时避免了之前 `MissingGreenlet` 类问题：finalization 不再访问 Runtime Session 中已被 commit/refresh 后可能 expired 的 ORM execution 属性，只使用进入 Runtime 前保存的 UUID。

## 4. 自动化测试约束

B2/B3 Gate 必须保持**只校验、不启动服务**：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

Gate 自动生成测试用户、Token、tenant、organization、Agent、Workflow、Delegation fixture 与测试数据；禁止开发者手工填写测试信息。

Gate 只检查 PostgreSQL、Redis 与 Backend API 是否已运行，不执行 `docker compose up`、`uvicorn` 或其他服务启动命令。服务必须由本地开发环境预先提供。

## 5. 验证要求

本轮代码提交后必须由开发者本地实际执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

B2/B3 Real Gate 在开发者实际复跑前不得标记为通过。若 Real Gate 继续失败，应以新的实际堆栈与数据库终态事实继续定位，不得重复声明旧修复已通过。