# Phase 2.6 — Durable Execution Checkpoint Acceptance

## 1. 验收目标

验证 Workflow Execution 已具备独立、不可变的 Checkpoint 持久化基础，但尚未把 Checkpoint 错误地扩展为自动 Resume。

## 2. 代码边界

```text
WorkflowExecution
      ↓
Checkpoint Service
      ↓
workflow_execution_checkpoints
```

必须满足：

- `execution_id + sequence` 唯一；
- Checkpoint 只追加，不覆盖历史记录；
- Checkpoint 可以保存 Execution / Node 状态快照；
- Checkpoint 可以保存可恢复业务 state；
- Checkpoint 保存当时 Worker owner 事实；
- `latest()` 通过最高 sequence 读取最新快照；
- 不改变现有 Execution / Node 状态机；
- 不自动 Resume 已中断的 running Execution。

## 3. 开发者本地前置服务

当前 targeted unit test 不需要启动 API / Scheduler / Worker。

真实 PostgreSQL migration / persistence Gate 需要开发者预先运行 PostgreSQL，服务进程本身由测试 Gate 管理规则决定；不得在测试脚本内私自启动、停止或重启本地业务服务。

## 4. Targeted Test

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_execution_checkpoint.py
```

## 5. Migration

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

预期 head：

```text
0032_workflow_execution_checkpoint
```

## 6. 下一阶段验收

Checkpoint 代码通过 targeted unit 与 migration 后，再增加真实 PostgreSQL persistence Gate；只有真实持久化链路通过后，才进入 Runtime completion boundary 接入。

当前不应记录自动 Resume / checkpoint recovery 已完成。
