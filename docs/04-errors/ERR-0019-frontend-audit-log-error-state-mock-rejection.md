# ERR-0019 — AuditLogPanel 错误态 mock 时序导致 Vitest hook 超时

- Phase: 1.9-D
- 类型: Frontend Test / Vitest
- 严重级别: 阻塞 Frontend Regression Gate

## 现象

Frontend Vitest 的 `AuditLogPanel` error-state 用例在连续修复后仍失败：

```text
AuditLog query failed Error: Audit API unavailable
Error: Hook timed out in 10000ms.
  tests/views/AuditLog.test.ts:25:3
  beforeEach(() => auditLogs.mockReset());
```

开发者实际反馈为：

```text
AuditLog.test.ts: 1 passed, 1 failed
Frontend full test: 51 passed, 1 failed
Frontend Regression Gate: blocked
```

## 根因

生产组件 `AuditLogPanel.vue` 已经在 `load()` 的 `try/catch` 中处理 Audit API 异常。问题位于测试 fixture：先使用 `mockRejectedValue(...)`，后改为 deferred Promise + `vi.waitFor(...)` 等待 transport 调用，再 reject deferred Promise；在当前 Vitest/Vue mount 调度下，该测试仍与异步 rejection / hook 生命周期产生时序耦合，最终表现为 hook 超时，而不是稳定地完成组件错误态断言。

## 修复

测试 transport 改为**同步抛出异常**：

```ts
auditLogs.mockImplementation(() => {
  throw new Error("Audit API unavailable");
});
```

组件的 `load()` 对 transport 调用使用 `await`，因此同步异常仍然进入组件真实的 `catch` 路径；测试随后只等待 Vue promise flush，并断言 transport 调用一次及错误态渲染。

生产 `AuditLogPanel.vue` 不做无关修改。

修复提交：

```text
dc3d9ebc7dd5dd5ecd34260e7040795ecaebe6db
 test: remove AuditLog rejection timing race
```

## 验证要求

必须从 `frontend` 目录由开发者本地实际执行：

```powershell
npm test -- tests/views/AuditLog.test.ts
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

只有实际执行并通过后，才能更新 Phase 1.9-D / 1.9-E 的验收状态。此前失败结果不得用新的提交预先标记为通过。
