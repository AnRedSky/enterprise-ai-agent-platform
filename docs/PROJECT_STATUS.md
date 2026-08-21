# 项目开发进度

> 本文只记录当前项目基线、阶段状态、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/01-governance/DEVELOPMENT.md`；文档治理统一维护在 `docs/01-governance/DOCUMENTATION.md`；阶段计划位于 `docs/02-phases/`；阶段验收位于 `docs/03-acceptance/`；工程错误位于 `docs/04-errors/`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- Phase 1.7：**已完成并正式关闭**
- 当前阶段：**Phase 1.8 Event / Webhook Trigger Expansion 已正式关闭**
- 当前任务：**Docs Governance Refactor：文档迁移矩阵已建立，新目录与正式入口已开始迁移**
- 当前角色：开发执行
- 测试 Gate 治理：Backend、Frontend、Browser/E2E 三层独立；不使用 GitHub Actions workflow run

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5 | **已完成** | Workflow / Governance A～G 全部完成；Circuit Breaker 最终验收通过 |
| Phase 1.6 | **已正式关闭** | Trigger CRUD、Governance、Real HTTP、Browser E2E 全部完成 |
| Phase 1.7 | **已正式关闭** | Scheduled Trigger A～D 全部完成；Backend、Frontend、Browser 三层 Gate 通过 |
| Phase 1.8 | **已正式关闭** | Webhook Trigger A～F 全部完成；Backend、Frontend、Browser 三层 Gate 通过 |

## 3. Phase 1.8 最终验收结果

### Backend

开发者最新实际反馈：

```text
uv run pytest -q
→ 257 passed, 20 deselected in 4.95s

scripts/test/api-real/01_run_real_api_tests.ps1
→ 20 passed in 37.94s
→ [PASS] Real API gate completed. Frontend/backend integration may proceed.
```

Phase 1.8-B 已实际执行 `uv run alembic upgrade head` 并通过；Phase 1.8 无新增数据库 Migration。

### Frontend

开发者实际反馈：

```text
npm test
→ 13 test files passed
→ 52 tests passed

npm run build
→ production build succeeded
→ 1709 modules transformed

scripts/test/release/01_frontend_regression_gate.ps1
→ Frontend automated regression passed
→ Frontend production build passed
→ [PASS] Frontend regression gate completed.
```

### Browser E2E

开发者最新实际反馈：

```text
npx playwright test --list --project="Desktop Chrome"
→ 3 tests listed

scripts/test/e2e/01_run_workflow_trigger_e2e.ps1
→ scheduled Trigger governance: passed
→ webhook Trigger governance: passed
→ webhook runtime convergence / lifecycle security: passed
→ 3 passed
```

## 4. Docs Governance Refactor

### 已完成

1. 从最新 `main` 盘点 `docs/` 根目录及现有子目录。
2. 建立 `docs/DOCS_MIGRATION_MATRIX.md`，先定义旧文档 → 新文档映射。
3. 创建统一入口 `docs/README.md`。
4. 创建 `docs/00-architecture/`、`docs/01-governance/`、`docs/02-phases/`、`docs/03-acceptance/`、`docs/04-errors/` 的正式文档入口。
5. 新增 `01-governance/DOCUMENTATION.md`，废止新的连续 `00/01/02/...` 文档命名方式。
6. 将工程规则迁移到 `01-governance/DEVELOPMENT.md`，并以当前 `DEVELOPMENT.md` 的规则为准解决旧 `DEVELOPMENT_GUIDELINES.md` 冲突。
7. 建立 Phase 1.2～1.8 的统一 Phase 目录入口及 Phase Acceptance 入口。
8. 建立历史 Phase 23 / 24 的明确历史入口，避免旧阶段状态覆盖当前状态。
9. 建立 `04-errors/README.md`，准备迁移旧 `error-tracking/`。

### 尚未完成

- 旧根级文档尚未全部删除。
- 旧 `docs/error-tracking/` 尚未全部迁移并重新编号。
- 旧 `docs/phase-1-5-f/` 尚未全部合并。
- 全仓旧路径引用尚未最终清理。
- 新旧文档内容的逐项一致性校验尚未完成。

因此当前 Docs Governance Refactor **尚未宣称完成**。

## 5. 当前下一步

继续严格按照 `docs/DOCS_MIGRATION_MATRIX.md`：

1. 逐份完成剩余历史文档内容迁移。
2. 迁移并重新编号 `error-tracking/`。
3. 合并 `phase-1-5-f/`。
4. 全仓搜索旧 `docs/` 路径并修正引用。
5. 删除旧根级入口，完成目录收口。
6. 做文档静态结构 / 引用 / 命名检查。
7. 再次更新本文件，确认 Docs Governance Refactor 完成后，恢复下一 Phase 开发。

## 6. 开发治理

1. 不提交、不触发、不依赖 GitHub Actions workflow run。
2. 所有测试由开发者本地执行。
3. 实际测试结果只能在开发者反馈后写入状态文档。
4. Backend、Frontend、Browser/E2E 三层 Gate 独立。
5. 不提交 secret、Real API context、Playwright trace/screenshot 等本地运行产物。
6. 所有开发工作以最新 `main` 为唯一基线，禁止创建开发分支、临时分支或任务分支。
