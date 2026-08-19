# 004：Workflow Execution Governance 测试夹具缺少租户与工作流上下文

## 1. 基本信息

- 阶段：Phase 1.5-E Governance / Audit / Trace
- 日期：2026-08-20
- 类型：Backend Test / Governance Contract
- 严重级别：阻塞
- 影响范围：`uv run pytest -q`、Phase 1.5-E Backend full regression

## 2. 实际错误

开发者本地执行 `uv run pytest -q`：

```text
178 passed, 2 failed
AttributeError: 'types.SimpleNamespace' object has no attribute 'tenant_id'
```

失败测试：

```text
tests/test_workflow_execution_state_machine.py::test_pending_execution_can_start_and_complete
tests/test_workflow_execution_state_machine.py::test_pending_execution_can_be_cancelled_but_running_cannot_complete_twice
```

错误发生在：

```text
app/services/workflow_governance.py
WorkflowGovernanceService.trace()
```

具体为 Governance Trace 创建时访问：

```python
execution.tenant_id
execution.workflow_id
execution.workflow_version_id
```

而状态机测试夹具此前只补齐了 `created_by`，没有同步补齐完整的 WorkflowExecution Governance Domain Contract。

## 3. 根因

Phase 1.5-E 将 Execution Governance / Audit / Trace 接入状态机后，`WorkflowExecution` 的最小可用上下文已经不只是 `id + created_by`。

Trace 和 Audit 都需要以下关联字段：

- `tenant_id`
- `workflow_id`
- `workflow_version_id`
- `created_by`
- `id`

测试仍沿用了 Phase 1.5-C 的简化 `SimpleNamespace`，导致测试夹具与生产 Domain Contract 漂移。

## 4. 修复方案

不在生产代码中使用 `getattr()`、默认 UUID 或其他降级逻辑绕过缺失字段。

直接修复测试夹具：

```python

def _execution(*, status: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_version_id=uuid4(),
        created_by=uuid4(),
        ...,
    )
```

同时将重复夹具集中为 `_execution()`，避免后续测试继续遗漏 Governance 所需上下文。

## 5. 预防措施

- Workflow Execution 相关单元测试夹具必须满足当前 `WorkflowExecution` Domain Contract。
- 新增 Audit / Trace / Tenant / RBAC 关联字段后，必须同步检查已有测试夹具。
- 禁止为了让旧测试通过而降低生产服务的领域约束。
- Governance Contract 变化必须同时覆盖状态机、Runtime、Audit、Trace 测试。
- 新发生的工程错误继续独立记录在 `docs/error-tracking/`，不得混入开发准则或项目进度文档。

## 6. 验证要求

开发者同步最新 `main` 后执行：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
uv run alembic current
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_e_workflow_governance_validation.ps1
```

预期：

- Backend full regression 全部通过；
- Alembic head 为 `0017_workflow_governance_audit_trace`；
- Phase 1.5-E validation script 全部通过。

未收到开发者实际执行结果前，不得将 Phase 1.5-E 标记为完成。

## 7. 状态

代码修复已直接提交 `main`，等待开发者本地重新执行完整验收。
