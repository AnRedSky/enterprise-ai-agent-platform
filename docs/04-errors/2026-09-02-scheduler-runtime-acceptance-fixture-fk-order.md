# Scheduler Runtime PostgreSQL 验收夹具 FK 插入顺序错误

## 1. 发生现象

本地执行 Scheduler Runtime PostgreSQL Acceptance Gate 时，`tests/integration/test_workflow_scheduler_runtime.py` 在创建 `WorkflowSchedule` 时失败：

```text
ForeignKeyViolationError: insert or update on table "workflow_schedules" violates foreign key constraint "workflow_schedules_trigger_id_fkey"
DETAIL: Key (trigger_id)=(...) is not present in table "workflow_triggers".
```

## 2. 根因

验收测试在同一个 SQLAlchemy transaction 中同时 `add()` `WorkflowTrigger` 与 `WorkflowSchedule`，但两个 ORM 模型之间没有声明 SQLAlchemy relationship。SQLAlchemy 因此不能根据 ORM relationship 推导这两个 INSERT 的数据库依赖顺序，实际 flush 时可能先插入 `workflow_schedules`，而数据库中的 `workflow_triggers` 尚不存在，触发 PostgreSQL 外键约束。

这不是 Scheduler Runtime 生产代码的业务逻辑错误，而是 PostgreSQL Acceptance Fixture 没有显式建立 FK 前置事实。

## 3. 修复

在创建 `WorkflowSchedule` 前显式执行：

```python
await setup_session.flush()
```

使 `WorkflowTrigger` 先持久化，再插入引用其 `id` 的 `WorkflowSchedule`。

同时调整 `datetime` 导入顺序，保持标准库导入稳定性。

## 4. 防回归要求

Scheduler Runtime PostgreSQL 验收夹具必须遵循真实数据库 FK 顺序：

```text
Tenant/User
  ↓
Workflow/WorkflowVersion
  ↓
WorkflowTrigger
  ↓
WorkflowSchedule
  ↓
Scheduler Runtime tick
  ↓
ScheduleSlot / WorkflowExecution / Frontier / Audit / Trace
```

新增没有 ORM relationship 的跨表 FK fixture 时，不得依赖 SQLAlchemy 的隐式 INSERT 排序；应通过 `flush()` 或明确的持久化边界建立前置事实。

## 5. 验证

修复后重新执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.4\22_scheduler_runtime_gate.ps1
```

本次修复后的通过状态必须以开发者本地实际执行输出为准，不能以 GitHub Actions 或静态代码检查代替。

## 6. 关联变更

- `backend/tests/integration/test_workflow_scheduler_runtime.py`
- `backend/scripts/test/phase-2.4/22_scheduler_runtime_gate.ps1`
- `docs/03-acceptance/PHASE_2_4_ACCEPTANCE.md`
