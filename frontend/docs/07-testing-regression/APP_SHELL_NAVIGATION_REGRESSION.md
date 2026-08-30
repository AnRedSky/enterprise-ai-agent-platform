# AppShell 导航回归修复记录

## 1. 本地反馈

2026-08-29 开发者在 Windows 本地执行 `frontend/npm test`：20 个测试文件中 19 个通过、1 个失败；89 个测试中 87 个通过、2 个失败。失败均集中在 `tests/views/AppShell.test.ts`。

## 2. 根因

### 导航文案

测试仍断言上一版信息架构名称 `Agent 中心`、`知识中心`、`组织与模型`，但当前 AppShell 的正式导航为 `Agent 管理`、`知识库`、`组织管理`。这是测试契约滞后，不是生产页面功能缺失。

### 路由切换

AppShell 原先依赖 Element Plus `el-menu` 的 `router` 属性隐式驱动 Vue Router。Vitest + Vue Test Utils 的 memory history 环境中，直接触发 `el-menu-item` 点击没有稳定完成路由切换，导致断言仍停留在 `/dashboard`。

## 3. 修复设计

主导航属于平台基础设施，路由切换应由 AppShell 明确拥有：

1. 移除 `el-menu` 的隐式 `router` 行为。
2. 监听 `el-menu` 的 `select` 事件。
3. 将菜单 `index` 作为目标路径交给统一 `navigate()`。
4. 继续以当前 Vue Router 路由作为 `default-active`，保证刷新、深链和浏览器导航后的菜单状态一致。
5. 更新测试，使其验证当前正式信息架构与真实 Vue Router memory history 导航契约。

## 4. 验收要求

开发者本地必须重新执行：

```powershell
cd frontend
npm test -- tests/views/AppShell.test.ts
npm test
npm run build
npm run test:gate
```

只有新的本地命令输出明确成功后，才能记录为通过。当前提交不预填测试通过结论。
