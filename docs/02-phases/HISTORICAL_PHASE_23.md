# Historical Phase 23 — 历史规划与任务记录

> 仅保存旧连续编号体系的历史事实，不代表当前项目 Phase。当前状态以 `PROJECT_STATUS.md` 为准。

## 1. 原始范围

Phase 23 围绕 Runtime Management、RBAC、Filter、Audit、Pagination、Frontend Vitest/Build、HTTP RBAC 和 CI 恢复展开。

## 2. 任务演进

- Task 01：Runtime API Client 类型化、统一 `Page<T>`、Execution/Audit 类型边界。
- Task 02：Vitest/Vue Test Utils 基础、Runtime/Audit Loading/Success/Empty/Error、Filter/Pagination。
- Task 03：Vitest 工具链、API Client 分页/filter/events/audit 测试。
- Task 04：Vue Test Utils/jsdom、Runtime/Audit 组件状态测试；当时本地 npm 环境不稳定，未预填通过。
- Task 05：Frontend test/build 真实执行与质量治理计划。
- Task 06：HTTP Runtime RBAC 测试：401、Owner 200/404、Admin 200、Filter/Pagination/Audit scope。
- Task 07：质量门禁验证；随后拆成 07-A/07-B/07-C，逐步修复 Frontend build/test。
- Task 08：验证 Task 07 mock 修复，继续 Frontend build 与 Backend RBAC。
- Task 09：把 Frontend `npm test` + `npm run build` 纳入 Windows 本地手工验收脚本。

## 3. 手工测试反馈规范

`39-manual-test-execution-guide.md` 定义了当时唯一反馈入口：测试必须以实际命令输出为依据；Frontend 执行 `npm test` / `npm run build`；Backend 执行 `pytest -q`；专项验证 HTTP RBAC；测试后检查 `git status --short` / `git diff --stat`；反馈中禁止提交密码、API Key、JWT 完整 Token 等秘密。

## 4. Task 07-A/B/C 历史修复

### 07-A

Frontend build 首次暴露 44 个第三方 TypeScript declaration errors，涉及 VueUse Web Bluetooth、Element Plus GlobalComponents/JSX/h 等。修复 `frontend/tsconfig.app.json`：显式 `types=[vite/client, element-plus/global]`，`skipLibCheck=true`，不修改 node_modules、不降低 strict。Commit `8afe568e738b7caee0f1d450c76e0715efd088ea`。当时仍要求本地实际 build 后才算 PASS。

### 07-B

Build 错误由 44 降至 1 个；剩余 `Agents.vue` Element Plus `DefaultRow` 与 `Agent` 不兼容。修复为模板只传 `row.id`，组件内部从 agents 查找完整 Agent，不做类型断言、不降低 strict。

### Task 08

用户 Windows 本地首次 `npm test`：6 files 中 5 failed、1 passed；8 tests 中 4 failed、4 passed。原因包括重复 `.test.js` 与 `.test.ts`、AuditLog 缺少 `mount`、Element Plus 组件/v-loading 未统一 stub。修复保留 TS 测试源、删除重复 JS 测试、补 `mount` / `vi.hoisted`、统一组件/directive stub；生产 `AuditLog.vue` / `Runtime.vue` 不改。

### 07-C

后续人工反馈明确：`npm run build：PASS`、`npm test：PASS`。该结果属于当时开发者实际反馈。

## 5. Task 09 / 验收脚本

新增 `frontend/scripts/run_manual_frontend_suite.ps1`，检查目录/package、npm、执行 test/build，任一步骤失败即非 0；扩展 `backend/scripts/run_manual_test_suite.ps1` 增加 `-Mode frontend` 与 `-Mode all`。记录明确脚本提交不等于用户环境测试通过。

## 6. 历史整体进展

`36-project-progress-assessment.md` 当时判断 Runtime/Audit API、Vue 管理页面、Owner/Admin scope 已形成，但 Frontend test/build、HTTP RBAC 实测和 CI 恢复仍待真实反馈。后续 Task 07-C 的真实反馈完成了 Frontend 验证；Phase 23 的历史记录仍不能替代当前 1.x 状态。

## 7. 历史来源完整清单

已核对：

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
- `39-manual-test-execution-guide.md`
- `40-phase-23-completion-and-phase-24-plan.md`
- `41-phase-23-task-07a-frontend-build-fix.md`
- `42-phase-23-task-07b-frontend-test-plan.md`
- `42-phase-23-task-08-plan.md`
- `43-phase-23-task-07b-build-fix.md`
- `43-phase-23-task-08-completion.md`
- `44-phase-23-task-07c-frontend-test-plan.md`
- `44-phase-23-task-09-plan.md`
- `45-phase-23-task-09-frontend-runner.md`

旧矩阵中曾出现但当前 main 未找到正文的 33/34 等路径不补造内容。