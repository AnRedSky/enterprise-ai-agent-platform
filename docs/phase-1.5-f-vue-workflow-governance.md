# Phase 1.5-F Vue Workflow / Governance 管理端

## 1. 目标

在 Phase 1.5-E Governance / Audit / Trace Backend Contract 已验收的基础上，建设 Vue 3 管理端 Workflow / Governance 闭环。

本阶段遵循固定开发顺序：Backend Contract 已稳定后，先完成 Frontend API Types / Vitest，再完成 UI，最后由开发者本地执行前后端联调与全量回归。

## 2. 范围

### P0

- Workflow Registry 列表
- Workflow 创建
- Workflow Version 列表
- Workflow Definition JSON 编辑与创建新 Version
- Version Publish
- Workflow Audit 查询
- Workflow Execution Trace 查询
- RBAC / tenant isolation 继续由 Backend Contract 强制保证

### 非本阶段

- 可视化 DAG / Canvas 编排器
- Workflow 节点拖拽
- Workflow 在线运行控制台
- 多 Agent Workflow Designer

Definition 编辑器暂使用 JSON contract，为后续可视化编排器保留接口边界。

## 3. Backend Contract

- `GET /api/v1/workflows`
- `POST /api/v1/workflows`
- `GET /api/v1/workflows/{workflow_id}`
- `PATCH /api/v1/workflows/{workflow_id}`
- `GET /api/v1/workflows/{workflow_id}/versions`
- `POST /api/v1/workflows/{workflow_id}/versions`
- `POST /api/v1/workflows/{workflow_id}/versions/{version_id}/publish`
- `GET /api/v1/runtime/executions/{execution_id}/trace`
- `GET /api/v1/runtime/audit-logs?workflow_id=...`

后端 Contract 来源为现有 Workflow Registry、Runtime Query、Workflow Governance 实现，不在前端重新定义业务语义。

## 4. 前端实现

- `frontend/src/api/workflows.ts`
  - Workflow / Version / Trace 类型
  - Workflow Registry API
  - Governance Audit / Trace API
- `frontend/src/views/workflows/index.vue`
  - Registry
  - Version Governance
  - Definition
  - Audit
  - Trace
- `frontend/src/router/index.ts`
  - 新增 `/workflows`

### 4.1 前端构建优化整改

Phase 1.5-F 的构建优化继续保持 `tests / scripts` 职责隔离，不新增测试入口，也不把开发脚本改造成测试脚本。

本轮整改：

- 移除 `main.ts` 的 `app.use(ElementPlus)` 全量组件注册。
- 根据当前 `src/views` 实际使用情况，在 `main.ts` 手工注册已使用的 Element Plus 组件。
- 保留 Element Plus 全局 CSS；组件 JavaScript 通过 ES Module 按需引用，使 Rollup 可以执行 tree-shaking。
- 保留既有 route-level lazy loading 与 `manualChunks` 拆包策略，不通过提高 `chunkSizeWarningLimit` 掩盖 bundle 体积问题。
- 既有 `@vueuse/core` `INVALID_ANNOTATION` 精准 warning 过滤保持不变，不修改 `node_modules`。
- Node `localStorage` ExperimentalWarning 的测试环境处理保持现状，由 `frontend/tests/setup.ts` 提供确定性的测试 storage。

Element Plus 官方文档明确支持基于 ES Module 的手动 Tree Shaking；当前采用手工按需注册方案，避免为本轮优化额外引入自动导入插件依赖。

## 5. 验收门禁

开发者本地执行：

```powershell
cd frontend
npm test
npm run build
```

前后端联调：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
uv run alembic current

cd ..\frontend
npm test
npm run build
```

手工场景：

1. 登录后进入 `/workflows`。
2. 创建 Workflow。
3. 选择 Workflow，查看 Version。
4. 编辑合法 JSON Definition 并创建新 Version。
5. 发布 Version，确认 Published Version 更新。
6. Audit 页查询当前 Workflow 的治理记录。
7. Trace 页输入真实 Workflow Execution ID，确认 Trace 时间线可读取。
8. 使用非管理员账号验证只能访问自身租户 / 权限范围内数据。
9. 使用管理员账号验证治理查询范围符合 Backend RBAC Contract。
10. 检查 `npm run build` 不再出现 `@vueuse/core` PURE annotation warning，且不依赖提高 `chunkSizeWarningLimit` 消除 chunk warning。

## 6. 完成标准

- Frontend Vitest 通过且无未解释 warning。
- Frontend production build 通过。
- Element Plus 不再通过 `app.use(ElementPlus)` 全量注册。
- Frontend bundle 拆分策略保持可解释，不能以调高 warning 阈值代替优化。
- Backend regression 保持通过。
- Backend migration 保持 head。
- Workflow CRUD / Version / Publish / Audit / Trace 手工联调无异常。
- 不绕过 Backend RBAC / tenant isolation。
- 实际验收结果由开发者反馈后才能更新为已完成。

## 7. 下一步

前端构建优化完成并通过本地验收后，更新 `docs/PROJECT_STATUS.md`，再根据实际产品优先级决定继续增强 Workflow Designer，或进入更高阶 Runtime / Multi-Agent 能力。
