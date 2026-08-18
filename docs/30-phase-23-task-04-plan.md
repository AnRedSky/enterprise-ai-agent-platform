# 30 - Phase 23 Task 04 规划

## 1. 目标

完成 Runtime / Audit Vue 组件自动化测试，并验证核心状态与用户交互。

## 2. 执行顺序

1. 引入 Vue Test Utils 与 jsdom；若当前 Vitest 环境限制无法引入，则调整为兼容的组件测试环境。
2. Runtime.vue：Loading、Success、Empty、Error。
3. Runtime.vue：status filter、pagination、Execution Timeline 打开与 API 失败。
4. AuditLog.vue：Loading、Success、Empty、Error。
5. AuditLog.vue：status filter、pagination。
6. 执行 frontend test 与 build。
7. 修复测试暴露的类型或组件问题。

## 3. 完成标准

- Runtime / Audit 核心组件具备自动化测试。
- API 请求通过 mock 隔离。
- Empty / Loading / Error 状态有明确断言。
- test 与 build 可重复执行；若环境阻断，必须在完成记录中明确说明，不得虚报通过。
- 完成后提交 `docs/31` 完成记录和 `docs/32` 下一任务规划，并立即进入 Task 05。
