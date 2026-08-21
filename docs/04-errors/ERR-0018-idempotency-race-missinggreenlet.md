# ERR-0018 — Real API Idempotency Race 500 / Async Session Rollback

## 1. 发现阶段

Phase 1.9-C — Real API Reliability Scenarios。

## 2. 现象

开发者本地执行完整 Real API Gate：

```text
1 failed, 22 passed in 39.35s
```

失败场景：

```text
POST /workflows/{workflow_id}/executions
两个并发 HTTP 请求使用相同 Idempotency-Key
```

预期：两个请求均返回 `201`，并收敛到同一个 Execution。

实际：其中一个并发请求返回 HTTP `500 Internal Server Error`。原测试随后尝试 `response.json()`，因为 500 body 是纯文本 `Internal Server Error`，进一步产生 `JSONDecodeError`，掩盖了最初的 HTTP 500。

## 3. 根因判断

`WorkflowExecutionService.create()` 原实现捕获 `IntegrityError` 后直接执行 `await self.db.rollback()`，再使用原来的 `workflow` / `version` ORM 实例继续访问字段。

在 SQLAlchemy AsyncSession 中，完整 rollback 会使相关 ORM 状态过期；并发 idempotency 唯一约束竞争路径随后访问过期对象可能触发异步上下文之外的数据库加载，从而形成 `MissingGreenlet` / HTTP 500 风险。

## 4. 修复

改为：

- 在带 Idempotency-Key 的创建路径使用 `AsyncSession.begin_nested()` 建立 SAVEPOINT。
- 唯一约束竞争只回滚 SAVEPOINT，不回滚整个业务事务。
- 在 flush 前保存 `tenant_id`、`workflow_id`、`workflow_version_id` 标量值。
- IntegrityError 后使用保存的标量值查询已经提交的 Execution。
- 非 idempotency 创建保持原有事务行为。
- Real API 测试在解析响应时保留非 JSON body，避免 JSONDecodeError 掩盖 HTTP 状态码和原始错误响应。

代码提交：

```text
bdecd76b7c186c48fc3b7afdd23cc5d7dff1ecb6
fix: make idempotency race recovery transaction safe
```

测试诊断改进提交：

```text
7d7ff84d3c0449dd52c98882fbdb61ce8524d1d7
 test: improve Phase 1.9-C real API diagnostics
```

## 5. 验证边界

截至记录创建时，修复代码尚未由开发者重新执行本地 Gate，因此不能标记为验证 PASS。

此前实际失败证据：

```text
Focused direct pytest:
3 failed because WORKFLOW_ID was not prepared.

Full Real API Gate:
22 passed, 1 failed.
Failure:
test_execution_idempotency_is_race_safe_over_real_http
HTTP 500 Internal Server Error
```

## 6. 后续验证要求

必须重新执行：

```powershell
uv run pytest -q `
  tests/api_real/test_phase_1_9c_reliability_api.py `
  -m real_api
```

直接执行前应先准备 Real API context；推荐使用完整 Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

通过条件：

- 1.9-C 新增 3 个场景全部 PASS；
- 并发相同 Idempotency-Key 不产生 HTTP 500；
- 两个请求返回同一个 Execution ID；
- Ownership isolation 返回 404；
- 完整 Real API Gate 全部 PASS。
