# 前端 Vitest 失败根因：异步竞态与 Element Plus 测试桩丢失业务文本

- 日期：2026-08-30
- 领域：Frontend / Test Infrastructure
- 基线：`main` / `1965e769cac8657564e3cc31781ce3b71293570e`

## 现象

Runtime、Workflow、Agent、Organization、Model Provider、Dashboard 的部分 Vitest 用例失败，但生产源码已经包含对应中文空状态、错误提示、生命周期文案和状态映射。

## 根因

### 1. 异步断言竞态

多个测试仅等待 API mock 被调用，例如 `expect(api.list).toHaveBeenCalled()`。API 调用发生在异步函数进入 await 前，但 Vue 响应式状态要等 Promise resolve 后才更新，因此断言可能发生在加载完成之前。

### 2. 表格测试桩没有模拟业务渲染

`el-table-column` 测试桩直接返回空节点，完全丢弃 `label` 和 scoped slot。生产代码通过列的 scoped slot 渲染状态、操作和技术标识时，测试 DOM 自然看不到这些文本。

### 3. 部分组件测试桩没有渲染属性

`el-alert` 没有渲染 `title`、`el-dialog` 没有渲染 `title`，导致错误提示和弹窗标题无法进行用户可见文本断言。Runtime 测试还缺少 `el-date-picker` 测试桩，造成 unresolved component warning。

## 修复

新增 `frontend/tests/support/element-table-stubs.ts`，统一保留表头、普通字段和 scoped slot；受影响测试改为等待页面 loading 状态结束或业务状态发生变化；错误和弹窗测试桩开始渲染用户可见属性；Runtime 增加日期选择器测试桩。

## 设计约束

不修改生产代码以迎合错误测试桩，不在生产页面增加仅用于测试的隐藏文案，不复制后端状态机逻辑。测试应验证真实 ViewModel 与用户可见 UI，而不是 Element Plus 内部实现细节。

## 验证

本修复提交后必须在开发者本地执行：

```powershell
cd frontend
npx vitest run tests/views/Runtime.test.ts
npx vitest run tests/views/Workflows.test.ts
npx vitest run tests/views/Agents.test.ts
npx vitest run tests/views/Organizations.test.ts tests/views/OrganizationDetail.test.ts
npx vitest run tests/views/ModelProviders.test.ts
npx vitest run tests/views/Dashboard.test.ts
npm test
npm run build
```

真实执行结果以本地终端为准；当前 ChatGPT 工作环境无法访问用户 Windows 工作区，因此不会伪造本地通过结果。
