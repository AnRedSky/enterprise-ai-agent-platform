# Phase 2.8 B6 stale Frontier Runtime Entry 根因与修复

## 1. 发生时间

2026-08-29

## 2. 现象

基于 `5464ef31` 执行 B6 Multi-Worker Runtime Gate 时，Backend default regression 出现：

```text
test_runtime_entry_rejects_stale_frontier_before_node_execution
```

失败表现为测试在验证 stale Frontier ownership 前进入 `_is_delegation_frontier()`，该方法访问 PostgreSQL；测试进程中的 asyncio event loop 已关闭，最终出现 asyncpg `AttributeError: 'NoneType' object has no attribute 'send'`，并伴随：

```text
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
```

## 3. 根因

`PlannerDrivenDurableFrontierWorkflowWorker.execute_frontier()` 的执行顺序为：

1. 先查询 Frontier 是否属于 Delegation；
2. 再验证 Frontier / Execution ownership、attempt、状态和双层 lease；
3. ownership 失效时才拒绝执行。

这违反了 Runtime Entry 的安全边界：一个已经失去 Worker ownership 的 Frontier 不应为了确定业务类型再次访问数据库，更不能在 stale Runtime 上触发 Delegation Runtime 路由判断。

因此 stale Frontier 测试本应在 ownership guard 处立即返回，却先触发了 PostgreSQL 连接操作。Windows Proactor event loop 在测试退出阶段关闭后，asyncpg 仍尝试写 socket，于是产生连接异常和未 await 警告。

## 4. 修复

将 `execute_frontier()` 的入口顺序调整为：

```text
Frontier ownership / attempt / status / lease verification
        ↓ 失败 → 立即返回
Delegation Frontier classification
        ↓ 是
canonical Durable Frontier Runtime Entry
        ↓ 否
Planner-driven Workflow execution
```

即：

```python
if not await self._verify_frontier_consumption_ownership(frontier):
    return
if await self._is_delegation_frontier(frontier):
    await super().execute_frontier(frontier)
    return
```

该修复不新增 Runtime、Provider、Queue、Retry 或 Recovery 实现，也不改变 Delegation 与普通 Workflow 的正式执行入口，只收紧 Runtime Entry 的 ownership fencing 顺序。

## 5. 测试要求

必须实际重新执行 B6 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

重点确认：

1. stale Frontier ownership regression 通过；
2. Backend default regression 无 asyncpg event-loop warning；
3. B6 Real HTTP + PostgreSQL Multi-Worker Runtime 仍通过；
4. Delegation 继续进入 canonical Runtime Entry；
5. 普通 Workflow 继续进入 Planner-driven Runtime；
6. 未取得 ownership 的 Frontier 不再触发 Delegation 分类查询。

## 6. 状态

**代码修复已提交到 `main`，等待开发者本地重新执行 B6 Gate 后确认实际验收结果。**
