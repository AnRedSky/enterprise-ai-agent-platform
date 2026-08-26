# Durable Resume：Provider 503 被错误映射为 API 500

## 1. 发生时间

2026-08-26

## 2. 影响范围

Phase 2.6 Durable Execution / Durable Resume Real Worker Acceptance。

## 3. 实际现象

本地执行 `scripts/test/api-real/03_run_durable_resume_acceptance.ps1` 时，真实 HTTP Source Execution 首次调用临时 OpenAI-compatible Provider，Provider 按验收设计返回 `503 Service Unavailable`。

实际 API `/workflows/executions/{execution_id}/run` 返回 `500 Internal Server Error`，导致验收在 Source failure 断言处失败：

```text
AssertionError: {"detail":"Server error '503 Service Unavailable' ..."}
assert 500 in (409, 503)
```

## 4. 根因

OpenAI-compatible Provider 使用 `httpx.Response.raise_for_status()`，非 2xx 响应会产生 `httpx.HTTPStatusError`。Model Gateway 原先对 Provider 异常统一使用 `except Exception`，在配置了 Model Profile 的真实 Provider 场景直接重新抛出 `HTTPStatusError`。

WorkflowExecutionService 的 Runtime 异常边界只把 FastAPI `HTTPException` 映射为持久化失败状态并继续向 API 层抛出；未被识别的异常进入通用 `Exception` 分支并转换为 `500 Workflow Runtime 执行失败`。

因此 Provider 已经明确返回的 `503` 在 Gateway 与 Workflow Runtime 之间丢失了 HTTP 状态语义。

## 5. 修复原则

- Provider 原始 HTTP 状态必须在 Runtime Gateway 边界保留。
- 已绑定 Model Profile 的真实 Provider 不允许把明确的 Provider HTTP 错误降级为本地 Mock。
- 未绑定 Model Profile 且允许本地 Mock fallback 的开发场景继续保持原 fallback 行为。
- `generate` 与 `stream` 两条 Gateway 路径必须保持一致的 Provider HTTP 状态映射。

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
