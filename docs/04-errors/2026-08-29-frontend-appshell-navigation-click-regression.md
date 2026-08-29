# AppShell 导航点击回归修复

## 1. 本地证据

2026-08-29 开发者在最新 `main` 上执行前端回归：

- `AppShell.test.ts`：2 个测试中 1 个失败；
- 完整 `npm test`：20 个测试文件中 19 个通过，89 个测试中 88 个通过；
- `npm run build`：通过；
- `npm run test:gate`：因 Frontend test 失败而阻塞。

失败固定为点击 `Agent 管理` 后路由仍为 `/dashboard`。

## 2. 根因

上一轮将导航从 Element Plus `el-menu` 的隐式 `router` 行为改为 `@select` + `router.push()`，方向正确，但在当前 Vue Test Utils/jsdom 环境中，真实点击叶子 `el-menu-item` 没有稳定产生可观察的 `select` 事件。因此生产导航仍依赖组件内部事件链，测试无法验证用户实际点击路径。

## 3. 修复

AppShell 将叶子导航和工作流子导航的路由行为直接绑定到 `el-menu-item` 的 `click`：

```text
用户点击菜单项
      ↓
ElMenuItem click
      ↓
AppShell.navigate(path)
      ↓
Vue Router.push(path)
```

同时移除 `el-menu` 层面的 `@select` 处理，避免同一次点击同时触发两套路由入口。

菜单高亮仍由 `route.path` → `default-active` 驱动，因此路由状态仍是导航视觉状态的唯一来源。

## 4. 为什么不修改生产代码绕过测试

本次失败不是单纯测试桩问题，而是暴露了主导航把关键行为委托给第三方组件事件协议的可测试性问题。主导航属于应用壳层核心能力，应由 `AppShell` 明确拥有导航动作，因此直接绑定 `el-menu-item` click 更符合职责边界，也让浏览器真实点击与单元测试拥有同一业务入口。

## 5. 测试验收

修复后必须在开发者本地重新执行：

```powershell
cd frontend
npm test -- tests/views/AppShell.test.ts
npm test
npm run build
npm run test:gate
```

在新的本地输出出现前，不将 Gate 状态记录为通过。

## 6. 原子提交

代码、回归测试和本错误记录属于同一修复交付单元，应一次性提交到 `main`，不拆分中间提交。
