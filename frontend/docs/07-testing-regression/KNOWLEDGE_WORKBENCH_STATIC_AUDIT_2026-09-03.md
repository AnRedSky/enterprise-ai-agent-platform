# Knowledge Workbench Static Audit Remediation — 2026-09-03

## 1. Scope

本记录对应 `frontend` 分支在 Full-site UI consistency audit 中暴露的知识库工作台问题。

目标是修复页面层历史 Element Plus 状态实现，同时保持现有知识库 API Contract、数据结构、业务流程和响应式布局不变。

## 2. Failure

用户本地 targeted regression：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

结果为 `1 failed | 4 passed`，唯一失败为 `FullSiteConsistencyStaticAudit.test.ts`。

失败文件：

- `frontend/src/views/knowledge/components/KnowledgeWorkbench.vue`

失败规则：页面仍包含 `v-loading`，并同时存在历史 `<el-empty>` 状态实现。

## 3. Root Cause

`KnowledgeWorkbench.vue` 已经引入 `SurfaceCard` / `StatePanel`，但迁移不完整：

- 知识库表格仍通过 `v-loading` 表达加载状态；
- 文档、版本、分块及检索区域仍通过 `el-empty` 表达空状态。

这属于 UI governance primitive 迁移遗漏，不属于后端 API Contract 问题，也不需要新增业务逻辑。

## 4. Implementation

提交：

- `3f8a13987fb6ef391885c51f52aad7a6d8fd4ee6` — `fix: migrate knowledge workbench to shared state primitives`

调整：

1. 移除 Knowledge Workbench 页面中的 `v-loading`；
2. 文档、版本、分块空状态统一改为 `StatePanel state="empty"`；
3. 检索加载、无结果和初始等待状态统一使用 `StatePanel`；
4. 保留 `SurfaceCard` 作为业务区块容器；
5. 保留知识库、文档、版本、分块、检索的既有 API 调用和数据结构；
6. 不增加前端对后端状态或实体关系的重复推导。

## 5. Validation

GitHub source-level verification after the fix：

- `v-loading` search：无匹配；
- `el-empty` search：无匹配；
- `frontend` 相对 `main`：`ahead_by=1`、`behind_by=0`；
- 当前 `frontend` 最新提交为本修复提交 `3f8a13987fb6ef391885c51f52aad7a6d8fd4ee6`。

由于当前执行环境不能运行用户 Windows 工作树中的 npm/Vitest，因此不能伪造本地测试通过结果。应由本地工作树同步最新 `frontend` 后重新执行 targeted regression。

## 6. Local Test Procedure

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend
git rev-parse HEAD

npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

预期：上述 5 个测试文件全部通过。

通过后再执行完整门禁：

```powershell
npm test
npm run build
npm run test:gate
npm run test:e2e
```

测试过程不自动启动服务；如 E2E 需要依赖服务，应由既有开发环境按项目文档预先提供运行中的服务。
