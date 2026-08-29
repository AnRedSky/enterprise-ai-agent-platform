# Phase 2.9 前端回归测试修复：AppShell 导航契约

## 1. 背景

本地 `frontend` 回归测试在 2026-08-29 发现 `AppShell` 的两个测试失败：

- 导航文案断言仍使用上一版信息架构名称（例如 `Agent 中心`、`知识中心`、`组织与模型`），而当前生产壳层已经统一为 `Agent 管理`、`知识库`、`组织管理`。
- 在 Vitest + Vue Test Utils 环境中直接点击 `el-menu-item` 后，`el-menu` 的 `router` 集成没有可靠地完成 memory router 导航，测试仍停留在 `/dashboard`。

## 2. 根因

第一项属于测试契约滞后：测试断言没有跟随已提交的 AppShell 信息架构同步更新。

第二项属于组件集成边界不明确：AppShell 同时依赖 Element Plus `el-menu` 的隐式 router 行为和 Vue Router，导致浏览器组件行为与轻量测试环境之间存在差异。平台主导航属于核心基础设施，不应依赖隐式事件链完成关键路由切换。

## 3. 修复

`frontend/src/components/AppShell.vue`：

1. 移除 `el-menu` 的隐式 `router` 依赖。
2. 增加 `@select` 显式处理。
3. 将菜单 index 作为目标路径交给统一 `navigate()`。
4. 保留 `default-active` 与当前路由同步，确保刷新及深链页面仍能正确高亮。

`frontend/tests/views/AppShell.test.ts`：

1. 断言当前实际生产导航文案。
2. 保留用户身份、角色、核心导航及路由切换验证。
3. 测试通过真实的 Vue Router memory history 验证 AppShell 的导航契约。

## 4. 验证

开发者本地已提供如下执行入口：

```powershell
cd frontend
npm test -- tests/views/AppShell.test.ts
npm test
npm run build
```

提交前应以开发者本地实际执行输出记录最终结果。未实际执行的命令不得标记为通过。
