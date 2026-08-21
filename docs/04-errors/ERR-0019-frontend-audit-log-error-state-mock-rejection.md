# ERR-0019 — AuditLogPanel 错误态 rejected mock 在 Vitest 中形成未处理 rejection

- Phase: 1.9-D
- 类型: Frontend Test / Vitest
- 严重级别: 阻塞 Frontend Regression Gate

## 现象

Frontend Vitest 的 `AuditLogPanel` error-state 用例使用 `auditLogs.mockRejectedValue(...)` 模拟 Audit API 失败时，测试进程将该 rejection 报告为失败；生产组件本身已经在 `load()` 的 `try/catch` 中处理 API 异常。

## 根因

该用例的目标只是验证组件进入错误态，但 rejected Promise 的调度与 Vitest 当前运行时的 unhandled-rejection 检测存在时序耦合，导致测试失败位置落在 mock rejection，而不是组件的错误态断言。

## 修复

将测试边界改为同步抛出异常的 mock：仍然覆盖 `load()` 的 `catch` 路径，但不依赖 Promise rejection 的调度时序。生产 `AuditLogPanel.vue` 不做无关修改。

## 预防 / 验证

必须从 `frontend` 目录执行：

```powershell
npm test -- tests/views/AuditLog.test.ts
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

只有实际执行并通过后，才能更新 Phase 1.9-D / 1.9-E 的验收状态。
