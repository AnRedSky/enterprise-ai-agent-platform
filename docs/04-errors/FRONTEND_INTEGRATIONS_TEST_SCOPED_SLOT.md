# Frontend Integrations Test scoped slot 回归记录

## 现象

`frontend/tests/views/Integrations.test.ts` 在用户最新本地反馈中仍失败：

```text
TypeError: Cannot read properties of undefined (reading 'row')
```

同时出现 `el-table`、`el-table-column`、`el-tag`、`el-dialog` 等组件无法解析的 Vue warning。

## 根因

生产页面使用 Element Plus scoped slot：

```vue
<template #default="scope">{{ scope.row... }}</template>
```

当前测试通过 `mount(Integrations)` 单独创建 Vue Test Utils 应用。虽然已有 `plugins: [ElementPlus]`，但用户实际执行结果表明该插件安装没有形成可靠的组件解析边界，`el-table-column` 仍按未解析组件处理，slot context 中不存在生产表格组件提供的 `scope`，最终触发 `scope.row` 访问异常。

因此不能继续把“安装 ElementPlus 插件”当作已经完成的修复；必须让测试装配显式、可验证地注册页面依赖。

## 本次修复

`Integrations.test.ts` 增加 `mountIntegrations()` 测试装配函数，并显式注册：

```text
ElAlert
ElButton
ElCard
ElDialog
ElForm
ElFormItem
ElInput
ElInputNumber
ElOption
ElSelect
ElTabPane
ElTable
ElTableColumn
ElTabs
ElTag
```

同时提供 `v-loading` 测试 directive。两个用例统一使用该入口，避免测试之间出现不同组件装配状态。

## 边界

该问题仍属于 Frontend Test Environment 配置问题，不修改生产组件以迎合不完整的测试运行时。生产页面继续使用 Element Plus 正式组件和 scoped slot。

## 防回归

必须在用户本地实际执行：

```powershell
cd frontend
npm test
npm run build
npm run test:gate
```

只有实际执行成功后，才能更新 Phase / Acceptance 文档中的通过状态。