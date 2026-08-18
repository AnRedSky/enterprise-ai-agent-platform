# 32 - Phase 23 Task 05 规划

## 1. 目标

完成前端测试与构建的实际可重复验证，修复 Runtime / Audit 测试中的环境、类型和组件问题。

## 2. 执行内容

1. 安装 frontend 依赖并生成/核查 lockfile（仅在项目原本采用该 lockfile 时提交）。
2. 执行 `npm test`。
3. 修复 Vitest / Vue Test Utils / Element Plus mock 问题。
4. 执行 `npm run build`。
5. 修复 TypeScript / vue-tsc 问题。
6. 再次执行 test + build，记录真实结果。
7. 核查 git diff，确保没有 node_modules、dist、coverage、日志等非项目文件。

## 3. 后续衔接

Task 05 完成后提交：

- `docs/33-phase-23-task-05-completion.md`
- `docs/34-phase-23-task-06-plan.md`

然后立即进入 Task 06：Backend HTTP API RBAC 真实接口测试，覆盖 401 / 403 / 404、Owner Scope、Admin Scope 和 Filter。
