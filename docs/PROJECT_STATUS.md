# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-F Vue Workflow / Governance 管理端
- 当前角色：开发执行
- 开始时间：2026-08-20
- 基线：远端 `main` 最新基线持续同步

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
| Phase 1.5-E | 已完成 | Governance / Audit / Trace；开发者反馈全量测试通过，warning 已修复并验收通过 |
| Phase 1.5-F | 开发中 / Frontend build 已通过 | Vue Workflow / Governance 管理端；production build 成功，但存在第三方 Rollup PURE annotation 与 bundle size warning，已记录并不阻塞当前 build |

## 3. 1.5-E 最终验收

开发者已反馈：

```text
测试通过
```

Phase 1.5-E 已关闭，允许进入 Phase 1.5-F。

## 4. Phase 1.5-F 已实施范围

1. `frontend/src/api/workflows.ts`
   - Workflow / Version / Trace API Types
   - Workflow Registry API
   - Version Create / Publish
   - Audit / Trace 查询

2. `frontend/src/views/workflows/index.vue`
   - Workflow Registry 列表
   - Workflow 创建
   - Version 管理
   - JSON Definition 编辑
   - Version Publish
   - Audit 查询
   - Execution Trace 查询

3. `frontend/src/router/index.ts`
   - 新增 `/workflows` 管理端路由

4. `docs/phase-1.5-f-vue-workflow-governance.md`
   - Phase 1.5-F 范围、Contract、验收门禁与手工场景

## 5. 当前验收结果

### Frontend production build

开发者已反馈：

```text
vite v6.4.3 building for production...
✓ 1704 modules transformed.
✓ built in 10.34s
```

结论：`npm run build` **通过**。

同时发现并记录以下非阻断 warning：

1. `@vueuse/core` 构建产物中的 `/* #__PURE__ */` annotation 位置无法被当前 Rollup 完整解析，Rollup 自动移除该 annotation。
2. production bundle 中存在超过 500 kB 的 chunk。

详细记录：

```text
docs/error-tracking/006-frontend-vite-rollup-third-party-pure-annotation-warning.md
```

当前不直接修改 `node_modules`，也不简单通过提高 `chunkSizeWarningLimit` 掩盖问题；后续性能优化阶段评估依赖升级、route-level dynamic import 与 manualChunks。

### 尚未完成的验收门禁

Phase 1.5-F 尚不能标记完成，仍待开发者实际反馈：

```powershell
cd frontend
npm test
```

Backend full regression + migration head：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
uv run alembic current
```

随后执行前后端联调：

```powershell
cd ..\frontend
npm test
npm run build
```

手工联调：

1. 登录进入 `/workflows`。
2. 创建 Workflow。
3. 查看 Version。
4. 创建新 Definition Version。
5. 发布 Version。
6. 查询 Workflow Audit。
7. 输入真实 Workflow Execution ID 查询 Trace。
8. 验证普通用户的 tenant / owner 隔离。
9. 验证管理员治理查询范围。

## 6. 下一步

1. 开发者在最新 `main` 基线执行 `frontend/npm test`。
2. 执行 Backend full regression + migration head verification。
3. 执行 Phase 1.5-F Workflow / Governance 本地手工联调。
4. 若出现错误，先记录到 `docs/error-tracking/`，再修复。
5. 只有 Frontend、Backend、Migration、手工联调全部通过后，才能关闭 Phase 1.5-F。
6. Phase 1.5-F 关闭后重新规划下一阶段，不提前虚构新的 Phase 任务。
