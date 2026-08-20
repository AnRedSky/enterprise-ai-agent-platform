# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT_GUIDELINES.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-F Vue Workflow / Governance 管理端验收及测试基础设施治理
- 当前角色：开发执行
- 基线：2026-08-20 远端 `main` 已同步到最新整改提交

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
| Phase 1.5-F | 开发中 / Frontend build 已通过 | Vue Workflow / Governance 管理端；待 Frontend test、Backend regression、Real API Gate 和浏览器联调最终关闭 |
| 测试基础设施治理 | 整改中 | 已建立 Unit / Integration / API Contract / Real API 四层规范，并迁移 API Contract、Real API 与联调入口；历史遗留测试/评估脚本继续按职责迁移，不允许新增根目录文件 |

## 3. 本轮测试体系整改

已完成：

1. `backend/tests/` 明确划分 `unit/`、`integration/`、`api_contract/`、`api_real/`。
2. 已将原根目录 API endpoint 测试迁移至 `tests/api_contract/`，并删除旧重复文件。
3. 已将 Real API bootstrap / runner 迁移至 `scripts/test/api-real/`。
4. 已将 Frontend / Backend Integration Gate 迁移至 `scripts/test/integration/`。
5. 新增 `scripts/test/regression/`、`scripts/evaluation/knowledge/`、`scripts/evaluation/embedding/` 职责边界。
6. 更新 `backend/tests/README.md`、`backend/scripts/README.md`、`docs/DEVELOPMENT_GUIDELINES.md`，明确测试实现与脚本编排分离。

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

### Frontend production build

开发者已反馈 `npm run build` 成功：

```text
✓ 1704 modules transformed.
✓ built in 10.34s
```

存在第三方 `@vueuse/core` PURE annotation 与 bundle chunk size warning，已记录为非阻断项。

### Phase 1.5-F 最终关闭条件

仍待开发者本地执行并反馈：

1. `cd frontend && npm test`
2. `cd backend && uv run pytest -q`
3. `cd backend && uv run alembic upgrade head && uv run alembic current`
4. Real API Gate
5. Frontend / Backend 浏览器级联调

## 6. 下一步

1. 开发者拉取最新 `main`，执行测试基础设施整改后的完整回归。
2. 首先验证 Backend full regression 与 migration head。
3. 再执行 Real API Gate；通过后才能进行前后端联调。
4. 完成 Phase 1.5-F 浏览器级验收并关闭 Phase 1.5-F。
5. 测试基础设施治理的剩余历史文件继续按实际职责迁移，迁移后必须通过完整回归才能删除旧入口。
6. Phase 1.5-F 关闭后，再根据实际完成情况规划下一阶段，不提前虚构 Phase 任务。
