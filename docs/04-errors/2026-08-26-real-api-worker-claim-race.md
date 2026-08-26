# 2026-08-26 — Real API Execution Worker 抢占导致断言不稳定

## 1. 问题

`tests/api_real/test_runtime_model_governance_api.py` 在 Tenant Safe Real API Gate 中偶发收到：

```text
POST /workflows/executions/{execution_id}/run
→ HTTP 409
→ {"detail":"只有 pending Execution 可以 Run"}
```

同一批测试在没有 Worker 抢占时可以直接得到业务期望的 `200` 或 `500`。

## 2. 根因

Real API Gate 使用独立 PostgreSQL Worker。创建 `pending WorkflowExecution` 后，Worker 可以在 HTTP `/run` 到达前先完成 claim，将 `worker_owner` 写入 Execution 并进入 Runtime。

HTTP `/run` 此时再次进入生产 ownership fencing，必须拒绝重复执行并返回 `409`。该行为属于生产并发控制的正确结果，不是 Runtime 业务失败。

已有 `tests/api_real/execution_helpers.py::run_or_observe_execution` 已统一定义这一合法竞态：收到准确的 pending-run `409` 后只观察真实 Execution，等待 Worker 把状态推进到 terminal，再基于持久化结果继续业务断言。

## 3. 修复

将 Runtime Model Governance Real API 测试接入现有 `run_or_observe_execution`，禁止在测试文件内复制 Worker race 判断逻辑。

- fallback-success 测试接受直接 `200` 或合法 Worker 抢占 `409`，最终必须验证真实 Execution 为 `completed`；
- published-model-profile failure 测试接受直接 `500` 或合法 Worker 抢占 `409`，最终必须验证真实 Execution 为 `failed` 且 `error_code == HTTP_500`；
- 不修改生产 Execution 状态机；
- 不允许把 `running → running` 变成合法转换；
- 不允许测试自动停止、重启 Worker。

## 4. 验证方式

正确入口仍为 Tenant Safe Real API Gate，因为它负责准备 `ACCESS_TOKEN`、`ORGANIZATION_ID` 等真实测试上下文：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

直接执行 `tests/api_real/test_runtime_model_governance_api.py` 时必须先提供真实 API 测试上下文；仅使用 `uv run pytest -q tests/api_real/...` 会因 `real_api` marker 被 deselect，不能作为通过依据。

## 5. 结论

该问题属于测试对合法 Worker ownership race 的处理不完整，不属于生产 Runtime 状态机错误。修复后测试必须同时覆盖：HTTP 直接执行路径与 Worker 先 claim 路径。