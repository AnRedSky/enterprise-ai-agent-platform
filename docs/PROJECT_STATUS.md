# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-C Workflow Execution State Machine
- 当前角色：开发执行
- 开始时间：2026-08-19

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5-A | 已完成 | Workflow Definition Contract，本地 Backend 验收通过 |
| Phase 1.5-B | 已完成 | Publish Governance、Tenant Contract，本地 Backend 手工验收通过 |
| Phase 1.5-C | 修复待验收 | Workflow Execution State Machine；0016 migration metadata 兼容问题已修复代码并提交 main，等待开发者本地验证 |
| Phase 1.5-D | 待开始 | Workflow Runtime Integration |
| Phase 1.5-E | 待开始 | Governance / Audit / Trace |
| Phase 1.5-F | 待开始 | Vue Workflow / Governance 管理端 |

## 3. 1.5-C 当前任务拆解

1. WorkflowExecution / WorkflowNodeExecution Domain
2. Execution / Node 状态机
3. Alembic 0016
4. Execution API Contract
5. Tenant-scoped Execution 查询
6. Backend pytest
7. Backend API Scenario
8. 本地手工验收
9. 文档更新
10. 直接提交 `main`

### 已发现并修复的问题

`0016_workflow_execution_state_machine` revision id 长度为 37，而历史 `alembic_version.version_num` 为 `VARCHAR(32)`，导致 PostgreSQL 在记录 migration head 时失败。

错误记录：

`docs/error-tracking/001-alembic-version-column-too-short.md`

当前修复：

- `backend/alembic/env.py` 增加 Alembic version metadata preflight。
- 已存在且长度不足的 `alembic_version.version_num` 自动扩展至 `VARCHAR(64)`。
- preflight 与 migration 保持同一事务。
- 增加 `backend/tests/test_alembic_env.py` 覆盖扩展、缺表 no-op、已满足长度 no-op。

## 4. 修复后的验收门禁

必须由开发者实际执行并反馈结果：

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_c_workflow_execution_validation.ps1
```

1.5-C 未完成本地验收前，不进入 1.5-D Runtime Integration。

## 5. 测试结果记录

### 最近已确认结果

- Backend 全量回归：`152 passed in 2.71s`，无 warnings（用户于 2026-08-19 提供的实际结果）。
- 1.5-B Tenant Contract：用户反馈手动测试无异常。

### 当前待验证

- 0016 migration 修复后的 `uv run alembic upgrade head`
- 0016 migration 修复后的 `uv run alembic current`
- 1.5-C Backend pytest
- 1.5-C Backend 手工验证脚本

## 6. 下一步

1. 开发者本地验证 main 最新提交。
2. 根据实际结果更新本文件与错误记录。
3. 1.5-C 验收通过后继续 1.5-D Runtime Integration。
