# Historical Phase 23 — 历史规划与任务记录

> 本文仅保存旧连续编号体系中的历史事实，不代表当前项目 Phase。当前状态以 `PROJECT_STATUS.md` 为准。

## 1. 原始范围

原 Phase 23 围绕 Runtime Management、RBAC、Filter、Audit、Pagination、Frontend Vitest、Build、HTTP RBAC 和 CI 恢复评估展开。

## 2. 历史任务与已读取内容

### Task 01

Runtime 前端 API Client 类型化与管理页面类型收敛：Execution / Event / AuditLog TypeScript 类型、统一 `Page<T>`、Runtime Execution Detail API、Audit API response 类型、AuditLog 移除 `any[]`。当时仅完成静态类型边界，实际 build 待后续任务。

### Task 02

目标是建立 Vue Runtime / Audit 自动化测试基础：Vitest / Vue Test Utils 配置、Runtime List 与 Audit List 的 Loading / Success / Empty / Error、Filter / Pagination。历史完成记录明确说明当时 npm registry / 本地前端测试运行受环境阻断，因此不得把未执行结果标为通过。

### Task 03

落地 Vitest 工具链、`test` / `test:watch`、`vitest.config.ts`，并覆盖 Runtime API Client 的分页、status filter、Execution Events、Audit Logs filter。历史记录仍明确没有可信的真实 `npm test` 结果。

### Task 04

引入 `@vue/test-utils`、`jsdom`，Runtime/Audit 组件覆盖 Empty / Error 等状态，API 使用 mock 隔离。历史记录再次明确当时没有成功执行 npm install / npm test，因此不宣称通过。

### Task 05

计划将 frontend test/build 转为真实可重复执行，并修复 Vitest / Vue Test Utils / Element Plus mock、TypeScript / Vite build 问题；同时核查不提交 node_modules/dist/coverage。

### Task 06

HTTP Runtime RBAC 测试实现：未带 Bearer Token → 401；普通用户访问不可见 Execution → 404；Admin 查询跨 Owner Execution → 200；Runtime Execution Filter 参数透传。实现记录明确没有真实 pytest 执行证据，因此只表示测试代码完成。

### Task 07

质量门禁计划要求真实执行 frontend `npm test` / `npm run build` 与 backend pytest、HTTP RBAC、API Contract，并在失败后修复。历史 Windows 本地反馈后来发现 Vitest `vi.mock()` factory 引用顶层 mock 变量导致 TDZ，三个测试文件分别出现 `Cannot access 'get' / 'auditLogs' / 'executions' before initialization`；修复统一使用 `vi.hoisted()`，保持业务代码和断言语义不变。修复后仍要求重新执行 test/build，旧记录没有预填通过。

## 3. 历史整体进展评估

`36-project-progress-assessment.md` 当时基于 main 判断：Runtime Execution / Timeline / Audit API、Vue 管理页面、Owner/Admin scope、Runtime API Client / Runtime.vue / AuditLog.vue 测试基础已形成；但 frontend test/build、HTTP RBAC 实际执行和 CI 恢复仍被列为未完成，Tool Runtime / Memory / Observability 也仍被列为后续能力。

随后 `40-phase-23-completion-and-phase-24-plan.md` 仍明确：Phase 23 不能在没有 `docs/39` 本地手工反馈前标记全部完成；因此这些记录必须保留为历史状态，不能覆盖当前 1.x 项目状态。

## 4. 历史来源

已核对并归并：

- `24-phase-23-plan.md`
- `25-phase-23-task-01-completion.md`
- `26-phase-23-task-02-plan.md`
- `27-phase-23-task-02-completion.md`
- `28-phase-23-task-03-plan.md`
- `29-phase-23-task-03-completion.md`
- `30-phase-23-task-04-plan.md`
- `31-phase-23-task-04-completion.md`
- `32-phase-23-task-05-plan.md`
- `36-project-progress-assessment.md`
- `37-phase-23-task-06-http-rbac-implementation.md`
- `38-phase-23-task-07-validation-plan.md`
- `40-phase-23-completion-and-phase-24-plan.md`
- `41-phase-23-task-07-test-failure-fix.md`

部分矩阵中曾出现但当前 main 已不存在的 `33/34/39` 路径不凭空补造正文；其存在性差异记录在迁移矩阵中。