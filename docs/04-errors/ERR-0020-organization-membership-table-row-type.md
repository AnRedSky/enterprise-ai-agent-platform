# ERR-0020 — Organization Membership table row type

## 问题

Phase 2.1-D Frontend Regression / production build 在 `frontend/src/views/organizations/detail.vue` 失败。

`el-table-column` 默认 slot 的 `row` 被 Element Plus 类型声明为 `DefaultRow`，而页面操作函数要求 `Membership`，导致 `vue-tsc` 报告 5 个 TS2345/TS2739 错误。

典型错误：

```text
Argument of type 'DefaultRow' is not assignable to parameter of type 'Membership'.
```

## 根因

`members` ref 的运行时数据类型虽然是 `Membership[]`，但 Element Plus `el-table` / `el-table-column` slot 类型没有从该模板上下文自动收窄到 `Membership`。模板中的 `row` 因此保持为通用 `DefaultRow`。

## 修复

在 `detail.vue` 增加集中式 `asMembership(row: unknown): Membership` 类型边界，并在成员操作入口统一转换：

- `openEdit`
- `toggleMember`
- `transfer`
- `remove`

该转换只处理 UI table slot 的静态类型边界，不改变后端 API Contract、数据结构或授权逻辑。

同时为 Organization 列表测试补充 `el-tag` stub，消除已有测试中的组件解析 warning。

## 验证边界

代码修复已直接提交 `main`。本次不能将本地 Frontend Gate 标记为通过，因为修复后的 `npm test` / production build 尚未由开发者重新执行。

下一步必须重新执行：

```powershell
cd frontend
npm test -- tests/api/organizations.test.ts tests/views/Organizations.test.ts tests/views/OrganizationDetail.test.ts
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

只有上述 Gate 实际通过后，才能继续 Phase 2.1-E Real API / Browser E2E acceptance。
