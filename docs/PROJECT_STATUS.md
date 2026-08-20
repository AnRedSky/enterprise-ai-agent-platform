# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT_GUIDELINES.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-F Vue Workflow / Governance 管理端验收及测试基础设施治理
- 当前角色：开发执行
- 基线：2026-08-20 远端 `main` 已完成 tests / scripts 职责整改，并通过 Backend regression 与 migration 验收

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
| Phase 1.5-D | 已完成 | Workflow Runtime Integration；本地验收无异常 |
| Phase 1.5-E | 已完成 | Governance / Audit / Trace；全量测试通过，warning 已修复并验收通过 |
| Phase 1.5-F | 开发中 / Backend 回归与 Frontend build 已通过 | Vue Workflow / Governance 管理端；Execution 状态 / Node 状态、API/View tests 已补齐；Real API Gate 当前发现 bootstrap fixture 与 Workflow Runtime definition contract 不一致，已修复，待本地复测后关闭 |
| 测试基础设施治理 | 整改中 | 已建立 Unit / Integration / API Contract / Real API 四层规范，并迁移 API Contract、Real API 与联调入口；历史遗留测试/评估脚本继续按职责迁移，不允许新增根目录文件 |

## 3. 本轮测试体系整改

已完成：

1. `backend/tests/` 明确划分 `unit/`、`integration/`、`api_contract/`、`api_real/`。
2. 已将原根目录 API endpoint 测试迁移至 `tests/api_contract/`，并删除旧重复文件。
3. 已将 Real API bootstrap / runner 迁移至 `scripts/test/api-real/`。
4. 已将 Frontend / Backend Integration Gate 迁移至 `scripts/test/integration/`。
5. 新增 `scripts/test/regression/`、`scripts/evaluation/knowledge/`、`scripts/evaluation/embedding/` 职责边界。
6. 更新 `backend/tests/README.md`、`backend/scripts/README.md`、`docs/DEVELOPMENT_GUIDELINES.md`，明确测试实现与脚本编排分离。
7. 已修复迁移后评估脚本导入、集成迁移测试路径与 Workflow migration test path 问题。

## 4. 强制测试链

```text
Unit → Integration → API Contract → Real API → Frontend Test/Build → Browser 联调
```

Real API Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

统一联调 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_frontend_backend_gate.ps1
```

禁止手工填写 `ACCESS_TOKEN`、`WORKFLOW_ID`、`WORKFLOW_EXECUTION_ID` 作为 Real API 测试前置条件。

## 5. 当前验收结果

### Backend regression

开发者已反馈通过：

```text
171 passed, 5 deselected
```

### Migration

开发者已反馈通过：

```text
0017_workflow_governance_audit_trace (head)
```

### Frontend production build

开发者已反馈 `npm run build` 成功，当前构建无之前的 vendor 循环 warning / chunk > 500KB warning。

### Phase 1.5-F 本轮实现

已完成：

1. Workflow Registry / Version / Publish 管理界面。
2. Workflow Definition JSON 编辑与新 Version 创建。
3. Workflow Audit 查询展示。
4. Workflow Trace 查询展示。
5. 新增 Workflow Execution / Node API types 与查询封装。
6. Governance 页面新增 Execution 状态、当前节点、时间、错误及 Node 状态展示。
7. 新增 Workflow API contract tests。
8. 新增 Workflow Governance view tests。

### Real API Gate 当前问题与修复

开发者本地 Real API Gate 曾在执行 bootstrap fixture 时失败：

```text
POST /workflows/{workflow_id}/executions -> 422
Workflow definition 必须包含非空 nodes
```

根因是 bootstrap 创建的 fallback Workflow 使用了空 `nodes`，并且会复用 definition 不可执行的已发布 Workflow。已在 `backend/scripts/test/api-real/00_bootstrap_real_api.py` 修复：

1. 新建 fixture 使用 `input` + `output` 最小可执行节点定义。
2. 复用已有 Workflow 前检查其已发布 Version definition 是否包含非空 `nodes`。
3. 没有可执行已发布 Workflow 时自动创建有效 fixture。
4. 保持 Token / Workflow ID / Execution ID 全自动生成。

错误记录：`docs/error-tracking/007-real-api-bootstrap-empty-workflow-definition.md`。

修复提交：`2aab1dc8f619e604d76a7d97845e7669857f147c`。

## 6. Phase 1.5-F 最终关闭条件

仍待开发者本地执行并反馈：

1. `cd frontend && npm test`
2. `cd frontend && npm run build`
3. `cd backend && uv run pytest -q`
4. `cd backend && uv run alembic upgrade head && uv run alembic current`
5. 修复后的 Real API Gate
6. Workflow Registry → Version → Publish → Execution Status / Node Status → Audit → Trace 浏览器级联调

## 7. 下一步

1. 开发者同步最新 `main`。
2. 重新执行 Backend regression 与 migration，确认 bootstrap 修复没有引入回归。
3. 执行 Real API Gate，重点验证自动创建/发现可执行 Workflow、Execution、Audit、Trace 全链路。
4. Real API 全部通过后，再进行 Frontend Test/Build 与浏览器级 Workflow 联调。
5. 记录真实执行结果后关闭 Phase 1.5-F。
6. Phase 1.5-F 关闭后，再进入 Workflow Execution Reliability Hardening，不提前虚构下一阶段任务。
