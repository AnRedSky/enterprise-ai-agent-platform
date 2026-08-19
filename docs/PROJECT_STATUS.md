# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-E Governance / Audit / Trace
- 当前角色：开发执行
- 开始时间：2026-08-20
- 基线：远端 `main` 最新基线 `9ad4ad6abb53dbeb758f3686fe60bbd21c21b108`

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5-A | 已完成 | Workflow Definition Contract，本地 Backend 验收通过 |
| Phase 1.5-B | 已完成 | Publish Governance、Tenant Contract，本地 Backend 手工验收通过 |
| Phase 1.5-C | 已完成 | Workflow Execution State Machine，本地 Backend 验收通过 |
| Phase 1.5-D | 已完成 | Workflow Runtime Integration；开发者反馈本地验收无异常 |
| Phase 1.5-E | 开发中 / 修复后待验收 | Governance / Audit / Trace；Migration 已升级至 0017，Governance contract 2 passed；full regression 曾因测试夹具缺少 `created_by` 失败，已修复，等待开发者重新执行全量验收 |
| Phase 1.5-F | 待开始 | Vue Workflow / Governance 管理端 |

## 3. 1.5-D 验收结论

开发者已反馈：

```text
1.5-D Workflow Runtime Backend 本地验收 → 无异常
```

因此允许进入 1.5-E。

## 4. 1.5-E 实施范围

### 已实现

1. `backend/app/models/core.py`
   - AuditLog 增加 tenant / workflow / workflow version / workflow execution 关联字段

2. `backend/app/models/workflow_trace.py`
   - 新增 WorkflowTraceEvent 持久化模型

3. `backend/app/services/workflow_governance.py`
   - Workflow Audit 持久化
   - Workflow Trace 持久化

4. `backend/app/services/workflow_execution.py`
   - Workflow 创建产生 Audit / Trace
   - Execution 状态变化产生 Trace
   - Node 状态变化产生 Trace
   - Terminal Execution 产生 Audit

5. `backend/app/services/runtime_query.py`
   - Workflow Audit owner/admin scope
   - Workflow Trace owner/admin scope
   - Workflow Audit filters

6. `backend/app/api/runtime.py`
   - `GET /api/v1/runtime/executions/{execution_id}/trace`
   - Audit 查询支持 `workflow_id` / `workflow_execution_id`

7. `backend/app/schemas/runtime.py`
   - WorkflowTrace API contract
   - Workflow Audit governance fields

8. `backend/alembic/versions/0017_workflow_governance_audit_trace.py`
   - Audit governance fields
   - workflow_trace_events

9. `backend/tests/test_workflow_governance.py`
   - Audit / Trace persistence
   - owner isolation

10. `backend/scripts/run_phase_1_5_e_workflow_governance_validation.ps1`
   - Backend-only local validation

11. `docs/phase-1.5-e-governance-audit-trace.md`
   - Phase 1.5-E 实施与验收计划

12. `backend/tests/test_workflow_execution_state_machine.py`
   - 补齐 `created_by` 测试夹具，保持测试对象与 WorkflowExecution Domain Contract 一致

13. `docs/error-tracking/003-workflow-execution-governance-test-fixture-created-by.md`
   - 记录 1.5-E Governance 接入后测试夹具不一致错误

## 5. 已记录问题与修复

### 003：Workflow Execution Governance 接入后测试夹具缺少 `created_by`

开发者本地 `uv run pytest -q` 曾得到：

```text
178 passed, 2 failed
AttributeError: 'types.SimpleNamespace' object has no attribute 'created_by'
```

根因是旧状态机单元测试夹具没有同步 Phase 1.5-E 引入的 Governance actor contract。修复方式为补齐测试夹具 `created_by=uuid4()`，不在生产代码中增加针对测试对象的降级逻辑。

详细记录见：

```text
docs/error-tracking/003-workflow-execution-governance-test-fixture-created-by.md
```

## 6. 当前验收门禁

开发者尚未反馈修复后的 1.5-E 全量验收结果，因此当前不得标记为已完成。

待执行：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
uv run alembic current
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_e_workflow_governance_validation.ps1
```

预期 head：

```text
0017_workflow_governance_audit_trace
```

Backend 验证脚本只能执行 Backend migration / pytest，不得调用 Frontend 测试。Frontend 测试必须独立执行。

只有开发者实际反馈上述门禁全部通过后，才能进入 1.5-F。

## 7. 下一步

1. 开发者同步最新 `main`。
2. 执行 1.5-E Backend migration / contract / full regression。
3. 若继续失败，先记录到 `docs/error-tracking/`，再修复。
4. 验收全部通过后更新本文件为 1.5-E 已完成。
5. 然后进入 Phase 1.5-F Vue Workflow / Governance 管理端。
