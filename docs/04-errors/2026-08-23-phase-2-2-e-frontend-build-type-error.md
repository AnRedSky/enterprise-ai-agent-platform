# 2026-08-23 Phase 2.2-E Frontend production build type error

## 现象

E-3 Frontend targeted Vitest 在修复 vue-router test injection 后已通过，但 Frontend Regression Gate 的 production build 在 `vue-tsc -b` 阶段失败：

```text
src/views/organizations/model-providers.vue
TS2345: Argument of type 'DefaultRow' is not assignable to parameter of type 'ModelProfile'.
```

错误发生在 Element Plus `el-table` 的 `row` 模板参数传入 `openEditProfile(row)` 与 `removeProfile(row)` 的位置。Element Plus 模板类型推断将 row 识别为通用 `DefaultRow`，而业务 handler 直接要求 `ModelProfile`，导致测试可以通过但生产类型检查失败。

## 根因

这是 UI 组件模板类型边界问题，不是 Model Provider/Profile API contract 或领域模型错误。业务 handler 的参数类型正确表达了领域约束，但没有在 UI 组件的弱类型 row 边界建立显式转换。

## 修复

保持 `openEditProfile(profile: ModelProfile)` 与 `removeProfile(profile: ModelProfile)` 的领域 handler 不变，在表格事件入口新增：

```text
editProfileFromTableRow(row: unknown)
removeProfileFromTableRow(row: unknown)
```

入口负责将组件 row 边界转换为 `ModelProfile`，模板不再直接把 Element Plus `DefaultRow` 传给领域 handler。

## 验证要求

本修复提交时尚未由开发者本地重新执行 Frontend Regression Gate，因此本记录只确认代码修复，不记录 production build 为 Passed。

必须由开发者执行：

```powershell
cd frontend
npm test -- --run tests/api/modelProviders.test.ts tests/views/ModelProviders.test.ts
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

若 Frontend Gate 通过，再按需要执行独立 Browser E2E；不得将 Browser E2E 结果替代 Frontend Gate。
