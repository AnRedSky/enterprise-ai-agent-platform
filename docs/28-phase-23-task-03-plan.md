# 28 - Phase 23 Task 03 计划

## 1. 目标

落地 Vue 测试工具链，并让 Runtime / Audit 管理页面具备可重复执行的自动化测试。

## 2. 执行顺序

1. 增加 Vitest、Vue Test Utils、jsdom 及必要类型依赖。
2. 增加 Vitest 配置与测试脚本。
3. 为 Runtime.vue 建立 API mock，验证列表、筛选、分页、Empty、Error、Timeline。
4. 为 AuditLog.vue 建立 API mock，验证查询、分页、Empty、Error。
5. 执行 `npm test`、`npm run build`。
6. 发现失败立即修复并重新执行。

## 3. 质量门禁

- 禁止提交 `node_modules`、`coverage`、`dist` 等生成物。
- 测试失败不得写成通过。
- 依赖变更必须同步 lockfile。
- Task 03 完成时提交 `docs/29` 完成记录，并同步提交 Task 04 规划文档。

## 4. 后续任务

Task 04：HTTP API 层真实 RBAC 测试，重点验证 401 / 403 / 404、Owner Scope、Admin Scope 与资源不存在性保护。
