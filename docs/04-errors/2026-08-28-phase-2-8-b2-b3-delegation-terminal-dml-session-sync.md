# Phase 2.8 B2/B3 Delegation 终态持久化事务边界

## 1. 现象

开发者在远端 `main` 的 `612dbf55` 本地执行 B2 Worker Execution Bridge Gate 时，Unit、Backend Regression 与 Migration/head 均通过，但 Real HTTP + PostgreSQL + Runtime 仍出现：

```text
AssertionError: assert 'running' == 'completed'
```

失败发生在 Worker Runtime 返回后重新建立的 `SessionLocal()` 查询 `AgentDelegation.status` 时；同一条 Worker Execution 已经成功进入 `completed`，Target Agent Runtime 与 Worker Execution terminalization 均正常。

此前已经连续尝试 PostgreSQL `UPDATE ... RETURNING`、ORM `synchronize_session="fetch"`、`populate_existing=True`、直接修改已锁定 ORM identity，以及把 Delegation finalization 放入独立 Session；Real Gate 均仍未稳定通过。因此此前把问题单纯归结为 ORM identity synchronization 或“已经独立事务”是不完整的。

## 2. 根因最终收敛

`67e8379f` 虽然创建了新的 `SessionLocal()` 执行 Delegation finalization，但调用位置仍位于 `execute_claimed_execution()` 的 Runtime `async with SessionLocal()` 生命周期内部。也就是说：

1. Runtime Session 仍然存活；
2. Runtime Session 可能仍持有当前事务、锁或数据库连接状态；
3. Delegation finalization Session 在此期间并发访问同一 Worker generation；
4. 两个 Session 的提交/关闭边界并没有真正完成物理隔离。

因此“独立 Session”并不等于“独立 Session 生命周期”。反复修改 terminal DML 而没有关闭 Runtime Session，导致同一个 `running -> completed` 现象持续出现。

## 3. 本轮真实修复

`989d87d8` 将终态提交边界进一步收紧：

- Runtime 开始前继续快照 `tenant_id`、`worker_execution_id` 与 Delegation identity；
- Workflow Runtime / Worker Execution terminalization 继续由既有 Runtime Session 负责；
- Runtime `finally` 中首先关闭当前 Runtime Session，主动释放未结束事务、连接与锁；
- 只有 Runtime Session 完全关闭后，才创建独立 `SessionLocal()` 执行 Delegation completion/failure；
- finalization Session 重新读取 Worker Execution，并验证 tenant boundary；
- `complete_delegation()` / `fail_delegation()` 继续通过 `SELECT ... FOR UPDATE`、tenant boundary 与 `worker_execution_id` generation fencing 收敛状态；
- Delegation terminal state、AuditLog、WorkflowTraceEvent 在独立事务中原子提交；
- 不恢复 ORM bulk DML，不复制 Worker、Lease、Retry、Recovery 或 Provider。

关键设计原则：**Runtime Session 必须先结束，Delegation terminalization Session 才能开始。**

## 4. 自动化测试约束

B2/B3 Gate 必须保持只校验、不启动服务：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

Gate 自动生成测试用户、Token、tenant、organization、Agent、Workflow、Delegation fixture 与测试数据；禁止开发者手工填写测试信息。

Gate 只检查 PostgreSQL、Redis 与 Backend API 是否已运行，不执行 `docker compose up`、`uvicorn` 或其他服务启动命令。

## 5. 验证要求

本轮修复后必须由开发者本地实际执行 B2/B3 Real Gate。当前代码提交不等同于验收通过；只有本地实际结果确认 `AgentDelegation.status == completed` 后，才允许将 B2/B3 Real Gate 标记为通过。