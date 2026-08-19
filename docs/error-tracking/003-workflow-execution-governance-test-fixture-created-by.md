# 003：Workflow Execution Governance 接入后测试夹具缺少 `created_by`

## 1. 基本信息

- 阶段：Phase 1.5-E Governance / Audit / Trace
- 日期：2026-08-20
- 类型：Backend Test / Governance Integration
- 严重级别：阻塞
- 影响范围：`uv run pytest -q`、1.5-E Backend full regression

## 2. 实际错误

开发者本地执行：

```powershell
cd backend
uv run pytest -q
```

结果：178 passed、2 failed。失败均位于：

```text
tests/test_workflow_execution_state_machine.py::test_pending_execution_can_start_and_complete
tests/test_workflow_execution_state_machine.py::test_pending_execution_can_be_cancelled_but_running_cannot_complete_twice
```

实际异常：

```text
AttributeError: 'types.SimpleNamespace' object has no attribute 'created_by'
```

异常发生在 `WorkflowExecutionService.transition()` 调用 Governance Trace 时：

```python
await self.governance.trace(
    execution,
    execution.created_by,
    ...,
)
```

## 3. 根因

Phase 1.5-E 为 Workflow Execution 状态转换增加了 Audit / Trace 持久化。真实 `WorkflowExecution` domain 本身具有必需的 `created_by` 字段，但 Phase 1.5-C 的状态机单元测试使用 `SimpleNamespace` 构造轻量测试对象时没有同步补齐该 domain contract。

因此这是**测试夹具与已升级 Domain Contract 不一致**，不是数据库 migration 或 Runtime 状态机规则错误。

## 4. 修复方案

更新 `backend/tests/test_workflow_execution_state_machine.py` 的所有 `SimpleNamespace` Execution 夹具，补齐：

```python
created_by=uuid4()
```

不通过在生产代码中使用 `getattr(execution, "created_by", None)` 等方式掩盖 Domain Contract 缺失，避免测试对象与真实 ORM 模型产生不一致。

## 5. 预防措施

- Workflow Execution 测试夹具必须覆盖当前 `WorkflowExecution` Domain Contract 中被 Service 使用的必需字段。
- 当 Service 新增 Audit / Trace / Tenant / Owner 等横切约束时，必须同步检查已有 Unit Test fixtures。
- 测试修复应优先补齐真实 Domain Contract，而不是在生产代码中加入仅为测试对象服务的降级逻辑。
- Backend 测试继续严格与 Frontend 测试隔离。
- 新发生的工程错误继续独立记录在 `docs/error-tracking/`。

## 6. 验证要求

修复提交后由开发者本地实际执行：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
uv run alembic current
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_e_workflow_governance_validation.ps1
```

在收到实际执行结果前，不得将 Phase 1.5-E 标记为验收通过。

## 7. 状态

代码与测试夹具已修复并提交 `main` 后，等待开发者本地重新验证；当前不能预填“测试通过”。
