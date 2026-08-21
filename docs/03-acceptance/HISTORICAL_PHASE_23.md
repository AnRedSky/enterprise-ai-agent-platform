# Historical Phase 23 — Acceptance / Historical Evidence

> 历史验收记录。不得作为当前项目状态源。

## 1. 历史结论

`40-phase-23-completion-and-phase-24-plan.md` 明确记录：Phase 23 当时不能标记为全部完成，必须等待本地手工测试反馈后形成最终质量门禁。

## 2. 已确认形成的能力

- Runtime Execution 管理 API
- Runtime Timeline API
- Audit Log 查询
- Owner / Admin 数据范围
- Runtime Filter / Pagination
- Runtime API Client 测试
- Runtime.vue / AuditLog.vue 测试基础
- HTTP Runtime RBAC 测试代码

## 3. 当时未确认的质量证据

- Frontend `npm test`
- Frontend `npm run build`
- Backend `pytest -q`
- HTTP RBAC 测试实际执行
- CI 恢复后的绿色执行

## 4. 关键历史失败

Windows 本地 Vitest 运行曾出现 3 个测试文件全部 failed、0 tests。根因是 `vi.mock()` factory 直接引用顶层初始化 mock 变量，被 Vitest 提升后触发 TDZ。修复采用 `vi.hoisted()`，涉及 runtime、AuditLog、Runtime 三组 mock。原记录要求修复后重新执行 test/build，不把修复代码本身当成通过证据。

## 5. 来源

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
