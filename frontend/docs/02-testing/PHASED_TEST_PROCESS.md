# Frontend 分阶段测试流程

## 1. 固定流程

```powershell
cd frontend
npm ci
npm exec vitest run tests/views/AppShell.test.ts
npm run test:phase:p1
npm run test:phase:p2
npm run test:phase:p2.10
npm run test:phase:p3
npm run test:phase:p4
npm exec vitest run tests/views/FullSiteConsistencyGapAudit.test.ts tests/views/FullSiteConsistencyStaticAudit.test.ts
npm run test:unit
npm run build
npm run test:gate
```

Real API / Browser E2E 仅在依赖服务由开发者手动启动后执行；脚本不自动启动服务：

```powershell
npm run test:e2e
npm run test:final
```

一键本地前端回归：`npm run test:local:full`。

## 2. 阶段覆盖

- P1：Agent、Knowledge、Tool、Model Provider、Agent Workbench UI-05、Agent Debug UI-04。
- P2：Workflow、Workflow UI-03/UI-04/UI-05、Trigger、Runtime、Runtime Deep Link、Runtime Correlations。
- P2.10：Runtime Operations API/UI 与 build。
- P3：Organization、Audit、Integration、Dashboard。
- P4：AppShell 与共享平台体验。
- Full-site：raw UI primitive、数组位置实体推断、optimistic durable-fact mutation、关键 durable ID 导航。

## 3. 本轮失败根因

### Workflow Trigger

修复前 10 个失败都从 `api.triggers('w1')` 未调用开始。页面只加载 Workflow 列表，不自动选择第一项；Trigger 必须建立显式 Workflow 上下文。测试 fixture 已显式设置 `selectedWorkflowId` 并调用 `loadTriggers()`，同时将不存在的 `createTrigger()` 调整为真实页面方法 `saveTrigger()`。

### Workflows UI-04/UI-05

403 Permission、Trace Loading、Archived Read-only 测试未建立选中 Workflow 上下文，导致页面仍处于“请选择 Workflow”。测试现通过 `selectWorkflow(workflow)` 建立真实上下文，并断言页面实际权限/归档文案。

### Agent Debug UI-04

Loading 状态由 `onMounted(loadDebugContext)` 更新，不能用首次同步 render 断言。测试改为 `vi.waitFor()` 等待 mounted 后的 Loading 状态。

## 4. 基线与验证声明

用户提供的修复前基线：第一组 4 文件 / 33 测试 / 23 passed / 10 failed；第二组 5 文件 / 14 测试 / 10 passed / 4 failed。上述均为修复前结果。

本轮通过 GitHub 完成代码、测试脚本和文档修改，但未在用户 Windows 工作区执行 Vitest 或 Build，因此修复后的 PASS 状态必须以本地重新执行结果为准。

测试原则：测试假设错误则修 fixture/assertion；产品违反契约才修改产品；原始后端错误不得直接展示给用户。
