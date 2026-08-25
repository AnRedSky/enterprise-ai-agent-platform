# 2026-08-25：Worker ownership fencing 后测试契约漂移

## 1. 现象

开发者基于远端 `main@9493252` 执行本地验收后，发现两类回归失败：

### 1.1 Backend Regression 的 Unit Fixture 失败

```text
403 passed, 3 skipped, 36 deselected
8 failed
```

8 个失败均在 `WorkflowExecutionService.run()` 进入 `_validate_run_owner()` 时触发：

```text
AttributeError: 'types.SimpleNamespace' object has no attribute 'worker_owner'
```

这些测试使用 `SimpleNamespace` 模拟 `WorkflowExecution`，但在 Worker ownership fencing 引入后没有同步补齐 `worker_owner` 字段，因此尚未进入原有 retry / timeout 断言。

### 1.2 Tenant Safe Real API 的 Circuit Breaker Half-Open 测试失败

```text
34 passed, 1 failed
```

失败请求为：

```text
POST /workflows/executions/<id>/run
-> 503 {"detail":"Circuit Breaker is open"}
```

该 `503` 本身是 Half-Open Probe Quota 的合法业务边界结果。当前两个并发 Probe 的预期业务结果本来就是：

```text
[200, 503]
```

但 `run_or_observe_execution()` 默认只接受 `200`，因此把合法的 `503` 错误地当成测试辅助层失败。

## 2. 根因

本轮生产修复把 Execution ownership 正式提升为 Runtime 入口 Contract：

```text
WorkflowExecution
    └── worker_owner

HTTP /run
    └── worker_owner=None

Worker Runtime
    └── worker_owner=<claim owner>
```

因此测试中的伪造 Execution 必须显式表达“未被 Worker claim”：

```text
worker_owner=None
```

同时，Real API 测试辅助函数不能假设所有业务场景都只有 `200` 一个直接成功状态。Circuit Breaker Half-Open 并发场景明确存在一个合法 `503 CIRCUIT_OPEN` Probe，测试必须显式声明该允许状态，而不是吞掉异常。

## 3. 修复原则

### 3.1 不修改生产 ownership 校验以迁就旧 Fixture

不采用：

```python
getattr(execution, "worker_owner", None)
```

作为生产兼容垫片。

原因是这会把遗漏 Execution Contract 字段的测试模型继续隐藏起来，并弱化 ownership fencing 的结构约束。正确做法是同步测试 Fixture，使其与生产领域对象 Contract 一致。

### 3.2 Real API Helper 显式支持多个合法 HTTP 结果

`run_or_observe_execution()` 的 `expected_http_status` 扩展为：

```python
int | tuple[int, ...]
```

默认行为保持 `200` 不变；只有业务边界明确允许多个结果时，测试调用方才传入例如：

```python
expected_http_status=(200, 503)
```

这样既保留真实 HTTP 状态，又不会把未知 `4xx/5xx` 自动吞掉。

## 4. 变更范围

- `backend/tests/api_real/execution_helpers.py`
- `backend/tests/api_real/test_workflow_governance_api.py`
- `backend/tests/unit/test_workflow_execution_retry_transition.py`
- `backend/tests/unit/test_workflow_retry_transition.py`
- `backend/tests/unit/test_workflow_retry_budget.py`
- `backend/tests/unit/test_workflow_runtime_timeout.py`

生产 `WorkflowExecutionService`、Execution 状态机、Circuit Breaker 业务逻辑不因本测试问题放宽。

## 5. 本地重新验收顺序

修复提交后必须由开发者在本地实际执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend

uv run pytest -q tests/unit/test_workflow_execution_worker_fencing.py tests/unit/test_workflow_worker.py

uv run pytest -q tests/unit/test_workflow_execution_retry_transition.py tests/unit/test_workflow_retry_transition.py tests/unit/test_workflow_retry_budget.py tests/unit/test_workflow_runtime_timeout.py

uv run pytest -q tests/api_real/test_usage_accounting_api.py tests/api_real/test_workflow_governance_api.py

uv run alembic upgrade head

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Gate 继续遵守：API / Scheduler / Worker 必须由开发者预先运行，测试脚本不得启动、停止或重启服务。

## 6. 状态

本文件只记录本次实际失败及修复边界。修复提交后未收到新的本地执行结果前，不标记任何 Gate 为 Passed。
