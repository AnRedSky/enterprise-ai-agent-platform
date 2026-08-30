# Element Plus Loading 指令注册回归记录

## 1. 背景

`WorkflowLifecycle.vue` 使用 Element Plus `v-loading` 为版本/发布与触发调度区域提供稳定的详情加载反馈。页面测试已通过 `global.directives.loading` 提供测试桩，但生产入口此前没有注册该指令，运行时可能出现 `Failed to resolve directive: loading`，导致 UI Loading 语义与实际应用入口不一致。

## 2. 实现

在 `frontend/src/main.ts` 中直接从 `element-plus` 导入官方 `vLoading` 指令，并通过 `app.directive("loading", vLoading)` 注册为全局指令。

这样页面继续使用标准 Element Plus `v-loading`，无需在业务页面复制 loading 实现，也不会增加第二套状态管理。

## 3. Contract / 兼容性

- 不改变任何 Backend API、API Type 或业务状态枚举。
- 不改变现有组件 Props / Emits。
- 继续兼容已有业务页面中的 `v-loading` 用法。
- 只在应用启动层增加 Element Plus 官方指令注册，避免业务组件各自注册造成不一致。

## 4. 测试

新增 `frontend/tests/main.test.ts`，验证应用启动时调用 `app.directive("loading", vLoading)`。

按照前端开发准则，必须在本地依赖完整后执行：

```powershell
cd frontend
npm ci
npm test -- tests/main.test.ts
npm test
npm run build
npm run test:gate
npm run test:e2e
```

当前工具环境无法访问用户 Windows 本地 Node 工作区，因此以上命令尚未在本地执行，不能记录为“通过”。

## 5. 验收状态

- 代码实现：已完成
- 回归测试：已补充
- 本地 targeted Vitest：待执行
- 全量 Vitest：待执行
- build：待执行
- test gate：待执行
- Browser E2E：待执行

在本地验证全部完成前，本任务保持“进行中”。
