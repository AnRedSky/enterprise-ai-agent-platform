# Durable Resume：Provider 503 被错误映射为 API 500

## 1. 发生时间

2026-08-26

## 2. 影响范围

Phase 2.6 Durable Execution / Durable Resume Real Worker Acceptance。

## 3. 实际现象

本地执行 `scripts/test/api-real/03_run_durable_resume_acceptance.ps1` 时，真实 HTTP Source Execution 首次调用临时 OpenAI-compatible Provider，Provider 按验收设计返回 `503 Service Unavailable`。

第一轮修复后，Provider HTTP 状态已经能够正确保留，`/workflows/executions/{execution_id}/run` 不再因为该异常直接错误映射为 500；但验收随后在 PostgreSQL Checkpoint 断言阶段失败。

实际错误为 Windows Python 3.12 ProactorEventLoop 与 asyncpg 连接池跨事件循环复用：

```text
RuntimeError: Event loop is closed
AttributeError: 'NoneType' object has no attribute 'send'
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
```

失败位置是同一个 Real API 测试函数先后多次调用 `asyncio.run(...)`，使 SQLAlchemy asyncpg 连接池中的连接在不同事件循环之间被复用。该问题同时产生 1 条 pytest RuntimeWarning。

在该问题修复后，验收继续暴露出 Checkpoint sequence 断言与既有持久化契约不一致：Real Worker Resume 验收断言首条 Checkpoint 为 `sequence == 1`，实际数据库值为 `0`。

## 4. 根因

OpenAI-compatible Provider 使用 `httpx.Response.raise_for_status()`，非 2xx 响应会产生 `httpx.HTTPStatusError`。Model Gateway 原先对 Provider 异常统一使用 `except Exception`，在配置了 Model Profile 的真实 Provider 场景直接重新抛出 `HTTPStatusError`。

WorkflowExecutionService 的 Runtime 异常边界只把 FastAPI `HTTPException` 映射为持久化失败状态并继续向 API 层抛出；未被识别的异常进入通用 `Exception` 分支并转换为 `500 Workflow Runtime 执行失败`。

因此 Provider 已经明确返回的 `503` 在 Gateway 与 Workflow Runtime 之间丢失了 HTTP 状态语义。

第一轮修复后，Real Worker 验收又暴露出测试自身的异步资源边界问题：`tests/api_real/test_workflow_resume_api.py` 在同一个测试中使用多个独立的 `asyncio.run(...)` 执行数据库操作，而项目使用 SQLAlchemy asyncpg 连接池。连接池连接绑定创建它的事件循环，前一次 `asyncio.run(...)` 结束后，后续事件循环继续复用旧连接，最终触发 Proactor socket 写入失败及未等待协程警告。

最后暴露的 sequence 问题不是生产代码异常：`WorkflowExecutionCheckpointService.append_next_in_transaction()` 明确定义第一个 Checkpoint 的 sequence 为 `0`，后续 Checkpoint 按 `max(sequence) + 1` 递增；现有 Real API Checkpoint 持久化验收也要求所有 Checkpoint sequence 等于 `range(len(checkpoints))`，即零基序列。Resume Assessment 使用实际 Checkpoint sequence 生成幂等键，因此 Resume 必须继续携带这个真实的零基 sequence。

## 5. 修复原则

- Provider 原始 HTTP 状态必须在 Runtime Gateway 边界保留。
- 已绑定 Model Profile 的真实 Provider 不允许把明确的 Provider HTTP 错误降级为本地 Mock。
- 未绑定 Model Profile 且允许本地 Mock fallback 的开发场景继续保持原 Mock fallback。
- `generate` 与 `stream` 两条 Gateway 路径必须保持一致的 Provider HTTP 状态映射。
- Real API 测试使用 asyncpg 时，数据库操作必须保持在同一事件循环内，禁止通过多个独立 `asyncio.run(...)` 跨循环复用 SQLAlchemy asyncpg 连接池。
- 测试警告必须与失败一起处理，不得通过屏蔽 warning 或修改 pytest warning 策略隐藏真实资源生命周期问题。
- Checkpoint sequence 是 Execution 内部零基、单调递增的持久化契约；验收不得擅自改成一基序列。

## 6. 修复内容

`ModelGateway` 对 `httpx.HTTPStatusError` 增加专门分支：

- 从 `exc.response.status_code` 提取原始 HTTP 状态码；
- 转换为 FastAPI `HTTPException`，使 WorkflowExecutionService 按现有 HTTP 异常状态机记录 `HTTP_503`；
- governed Model Profile 场景不执行 Mock fallback；
- 本地无 Profile fallback 场景保持既有 Mock fallback。

同时增加 Unit Test 覆盖：

- governed profile + `generate` 的 503 保留；
- governed profile + `stream` 的 503 保留；
- 无 Profile + fallback 的 503 仍降级到 Mock。

Real Worker 验收测试调整为 pytest async 测试函数，在单个测试事件循环内完成 Source 状态轮询、Checkpoint 查询、Resume 创建、Resume 状态轮询及最终结果查询，避免 asyncpg 连接池跨事件循环复用。

Real Worker Resume 验收的 Checkpoint 断言同步到既有零基契约：Source 首个完成节点 Checkpoint 为 `sequence == 0`，Resume Execution 自身首个完成节点 Checkpoint 也为 `sequence == 0`，而 `resume_checkpoint_sequence` 必须等于 Source Checkpoint 的实际 sequence。

## 7. 验收要求

代码提交后必须由开发者在本地重新启动受影响 API / Worker 进程，再执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_model_gateway.py
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\03_run_durable_resume_acceptance.ps1
```

本次错误记录只记录已经实际发生的失败；修复后的“通过”状态必须以开发者重新执行并反馈的本地结果为准，不在提交时预填。
