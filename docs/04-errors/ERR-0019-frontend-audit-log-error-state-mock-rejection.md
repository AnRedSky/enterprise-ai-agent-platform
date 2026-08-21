# ERR-0019 — AuditLogPanel 错误态 mock 时序导致 Vitest hook 超时

- Phase: 1.9-D
- 类型: Frontend Test / Vitest
- 严重级别: 阻塞 Frontend Regression Gate
- 当前状态: **已修复并完成开发者本地复验**

## 现象

Frontend Vitest 的 `AuditLogPanel` error-state 用例在连续修复后曾失败：

```text
AuditLog query failed Error: Audit API unavailable
Error: Hook timed out in 10000ms.
  tests/views/AuditLog.test.ts:25:3
  beforeEach(() => auditLogs.mockReset());
```

首轮开发者实际反馈为：

```text
AuditLog.test.ts: 1 passed, 1 failed
Frontend full test: 51 passed, 1 failed
Frontend Regression Gate: blocked
```

## 根因

生产组件 `AuditLogPanel.vue` 已经在 `load()` 的 `try/catch` 中处理 Audit API transport 异常。问题位于测试 fixture：使用 rejected Promise 时，与当前 Vitest/Vue mount 生命周期的 rejection 调度产生时序耦合；即使组件自身能够 catch，该 rejection 仍可能在下一次 hook 生命周期开始前触发 unhandled-rejection，最终表现为 `beforeEach` hook 超时。

## 修复过程

中间修复曾尝试同步抛出异常，但开发者复验仍出现 hook 超时，因此没有继续沿用该方案。

最终测试边界改为返回 malformed successful envelope：

```ts
auditLogs.mockResolvedValue(undefined);
```

组件随后访问 `response.data` 时进入既有 `catch/finally` 路径，从而稳定覆盖 error-state 渲染，同时不依赖 rejected Promise 的调度时序。

生产 `AuditLogPanel.vue` 不做无关修改；本问题属于测试 fixture 与 Vitest 生命周期耦合，不是生产组件异常处理缺失。

最终修复提交：

```text
ac58d441656b48e4f324e1a0769d8488a95b2fa9
 test: avoid AuditLog rejected transport mock race
```

## 开发者本地复验结果

开发者在最新 `main` 实际执行：

```text
AuditLog focused:
2 passed / 0 failed

Frontend full Vitest:
13 test files passed
52 tests passed

Frontend production build:
passed

Frontend Regression Gate:
PASS
```

测试输出中的：

```text
AuditLog query failed TypeError: Cannot read properties of undefined (reading 'data')
```

是该 malformed envelope fixture 进入生产代码既有 `catch` 路径时的预期 `console.error`，不是测试失败，也没有阻塞 Frontend Regression Gate。

## 当前结论

ERR-0019 Frontend AuditLog regression **已关闭**。此前 Frontend Regression Gate 的阻塞状态不得继续沿用到本轮验证记录。

后续仍必须独立复核 Browser E2E，并按 Phase 1.9-E 顺序执行 Backend / Migration / Real API / Frontend / Browser 全部本地 Acceptance；不得使用 GitHub Actions 结果替代本地验收。
