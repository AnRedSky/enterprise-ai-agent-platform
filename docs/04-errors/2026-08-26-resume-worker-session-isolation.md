# 2026-08-26 Durable Resume Worker Session 隔离问题

## 1. 现象

第一版 Resume Runtime 接入后，Worker 为了读取 Source Execution 与 Checkpoint，临时把当前数据库 Session 保存到 Worker 实例属性，再由 Resume helper 方法访问。

## 2. 风险

Worker 是并发消费器，同一个 `WorkflowWorker` 实例可以同时执行多个 Execution。如果把当前 SQLAlchemy `AsyncSession` 存在实例级属性中，多个并发 Execution 之间存在 Session 覆盖、交叉使用和事务边界混淆风险。

这会破坏 Worker 当前“每个 Execution 独立数据库事务”的设计，并可能把本来独立的 ownership / Runtime 操作错误关联到另一个 Execution。

## 3. 修复

将 Resume Runtime 准备链路改为显式传入当前 `execute_claimed()` 持有的 `db` Session：

```text
execute_claimed()
    ↓
_prepare_resume_runtime(db, execution, version)
    ↓
_source / checkpoint query 使用同一局部 db
    ↓
WorkflowExecutionService(db)
```

Worker 实例不再保存“当前 Execution Session”。

## 4. 设计约束

1. `WorkflowWorker` 可以并发执行多个 Execution。
2. Database Session 必须属于单个 Execution 调用上下文。
3. Resume Planner 本身是纯内存计算，不得持有 Session。
4. Resume Source / Checkpoint 必须在当前 Execution Session 中重新读取，不能相信创建 Resume 时缓存的业务数据。
5. 该错误属于实现阶段发现的并发隔离问题，已记录后才继续推进 Resume Runtime。

## 5. 验证要求

必须执行：

- Resume Planner targeted unit tests；
- Worker unit / fencing tests；
- 完整 `uv run pytest -q`；
- Backend Regression Gate；
- Tenant Safe Real API Gate；
- 有真实 Resume Execution 时再执行 Worker Resume acceptance。
