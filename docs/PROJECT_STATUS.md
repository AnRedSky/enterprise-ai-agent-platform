# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-D Workflow Runtime Integration
- 当前角色：开发执行
- 开始时间：2026-08-19
- 基线：已同步远端 `main` 最新提交 `b4288f0f1957941e501c3b238679c47b93aefbfa`

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5-A | 已完成 | Workflow Definition Contract，本地 Backend 验收通过 |
| Phase 1.5-B | 已完成 | Publish Governance、Tenant Contract，本地 Backend 手工验收通过 |
| Phase 1.5-C | 已完成 | Workflow Execution State Machine；开发者反馈全量测试及 1.5-C 验收全部通过 |
| Phase 1.5-D | 开发中 | Workflow Runtime Integration |
| Phase 1.5-E | 待开始 | Governance / Audit / Trace |
| Phase 1.5-F | 待开始 | Vue Workflow / Governance 管理端 |

## 3. 1.5-C 验收结论

开发者已反馈：

```text
uv run pytest -q                         → 通过
uv run alembic upgrade head              → 通过
uv run alembic current                   → 0016_workflow_execution_state_machine (head)
1.5-C Workflow Execution contract       → 通过
```

因此允许进入 1.5-D。

## 4. 1.5-D 实施范围

### 已实现

1. `backend/app/runtime/workflow_runtime.py`
   - Workflow Definition 校验
   - `input / agent / output` 三类最小节点
   - 串行节点执行
   - Agent published version 校验
   - Agent owner/admin 权限校验
   - Model Gateway 调用

2. `backend/app/services/workflow_execution.py`
   - Execution → Runtime 编排
   - Node running / completed / failed 持久化
   - Runtime 成功收敛为 completed
   - Runtime 节点失败收敛为 failed

3. `backend/app/api/workflow_executions.py`
   - 新增 `POST /api/v1/workflows/executions/{execution_id}/run`

4. 测试
   - `tests/test_workflow_runtime.py`
   - `tests/test_api_workflow_runtime.py`

5. 本地验收脚本
   - `backend/scripts/run_phase_1_5_d_workflow_runtime_validation.ps1`

6. 阶段文档
   - `docs/phase-1.5-d-workflow-runtime-integration.md`

## 5. 1.5-D 明确边界

本阶段只实现稳定的最小串行 Runtime，不实现：

- MQ / Worker 异步调度
- Temporal
- 并行 DAG
- 条件分支 / 循环
- Tool Runtime 编排
- Human-in-the-loop
- Governance / Audit / Trace 扩展
- Vue Workflow UI

## 6. 当前验收门禁

必须由开发者本地实际执行并反馈：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
uv run alembic current
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_d_workflow_runtime_validation.ps1
```

前后端测试严格隔离；本阶段 Backend 验证脚本不得调用 frontend npm 测试。

## 7. 下一步

1. 开发者拉取 / 同步当前 `main`。
2. 执行 1.5-D Backend 全量 pytest 与 Runtime 验收脚本。
3. 若失败，先记录到 `docs/error-tracking/`，修复后重新验收。
4. 只有 1.5-D 本地验收全部通过后，进入 Phase 1.5-E Governance / Audit / Trace。
