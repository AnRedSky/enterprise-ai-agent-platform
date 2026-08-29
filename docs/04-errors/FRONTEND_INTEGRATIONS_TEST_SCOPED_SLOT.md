# Frontend Integrations Test scoped slot 回归记录

## 现象

`frontend/tests/views/Integrations.test.ts` 在未注册 Element Plus 的测试挂载环境中失败：

```text
TypeError: Cannot read properties of undefined (reading 'row')
```

同时出现 `el-table`、`el-table-column`、`el-tag`、`el-dialog` 等组件无法解析的 Vue warning。

## 根因

生产页面使用 Element Plus 的 scoped slot：

```vue
<template #default="scope">{{ scope.row... }}</template>
```

测试直接 `mount(Integrations)`，没有安装 Element Plus。`el-table-column` 因此无法提供生产组件实际的 slot scope，导致测试运行时访问不存在的 `scope.row`。

## 修复

测试挂载统一使用：

```ts
mount(Integrations, { global: { plugins: [ElementPlus] } })
```

并为新增 `DeliveryConsole` View 测试使用相同的插件安装方式。

## 边界

该问题属于 Frontend Test Environment 配置错误，不修改生产组件以迎合不完整的测试运行时。生产代码继续使用 Element Plus 正式组件和 scoped slot。

## 验证要求

必须在本地重新执行：

```powershell
cd frontend
npm test
npm run build
```

只有实际执行成功后，才能更新 Phase / Acceptance 文档中的通过状态。
