# 41 - Phase 23 Task 07 测试失败修复记录

## 1. 本次测试反馈

用户在 Windows 本地执行 `frontend\npm test`，Vitest 4.1.10 结果为 3 个测试文件全部 failed、0 tests。

## 2. 根因

三个测试文件均在 `vi.mock()` factory 中直接引用了文件顶层初始化的 mock 变量。Vitest 会提升 `vi.mock()` 调用，导致 factory 执行时这些变量尚未初始化，触发 TDZ：

- `runtime.test.ts`: `Cannot access 'get' before initialization`
- `AuditLog.test.ts`: `Cannot access 'auditLogs' before initialization`
- `Runtime.test.ts`: `Cannot access 'executions' before initialization`

## 3. 修复

统一改用 `vi.hoisted(() => ({ ... }))` 创建 mock，再在 `vi.mock()` factory 中引用；同时保持测试断言和业务代码不变。

## 4. 当前状态

修复代码已经提交 `main`：

- `243510d` - axios runtime API mock
- `0894e30` - AuditLog mock
- `a95dc3f` - Runtime mock

## 5. 验证要求

修复后必须由本地环境重新执行：

```bash
cd frontend
npm test
npm run build
```

本记录只记录代码根因与修复，不宣称修复后的测试已经通过。
