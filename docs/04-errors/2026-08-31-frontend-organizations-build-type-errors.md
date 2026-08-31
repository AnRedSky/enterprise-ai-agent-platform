# Frontend Organizations 构建类型错误

## 1. 现象

Frontend production build 在 `vue-tsc -b` 阶段失败，共 5 个 TypeScript 错误：组织详情页的 Element Plus 表格 `row` 被推断为 `DefaultRow`，无法传入 `Membership`；组织列表页 `statusLabel` 比较了 Contract 未声明的 `pending` 状态。

## 2. 根因

组织 API Contract 当前明确声明 `OrganizationStatus = "active" | "suspended"`，因此列表页继续判断 `pending` 会触发 TypeScript 不可达分支检查。组织详情页的 `el-table` 默认 slot 类型是通用 `DefaultRow`，虽然表格实际数据源为 `Membership[]`，但组件模板类型推断不会自动把 slot row 收窄到业务类型。

## 3. 修复

- 删除组织列表页不存在于正式 Contract 的 `pending` 分支，保留 `active`、`suspended` 和未知值兜底。
- 组织详情页在进入成员操作 Domain Service 前，将表格行显式收窄为正式 `Membership` 类型；不复制成员模型或生命周期逻辑。
- 不修改 Backend Contract，不增加第二套组织/成员状态定义。

## 4. 验证边界

本错误由本地 Frontend production build 反馈发现。代码提交后必须重新执行 targeted Vitest、`npm run build` 及 Frontend Release Gate；未收到新的本地执行结果前不得将构建标记为通过。
