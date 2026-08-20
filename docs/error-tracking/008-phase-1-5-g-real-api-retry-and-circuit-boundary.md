# 008：Phase 1.5-G Real API Retry / Circuit Boundary 验收失败

## 1. 实际错误

2026-08-20 开发者本地执行 Phase 1.5-G 验收时发现：

1. `uv run pytest -q`：`test_run_exhausts_retry_budget_before_scheduling_retry` 失败。测试期望原始 `ConnectionError`，Runtime 在 Execution 已进入 `failed` 后又被外层异常处理包装为 `HTTPException(500)`。
2. Real API `test_node_retry_real_business_loop`：Audit 中缺少既有兼容动作 `workflow.node.retry`，当前仅记录 `workflow.node.retry_scheduled` 与 `workflow.node.retry_exhausted`。
3. Real API `test_circuit_breaker_opens_and_fast_fails_real_business_boundary`：第二次独立 Execution 的首个 `CIRCUIT_OPEN` 节点实际观测到 `attempt=2`，与 Fast-Fail 不应产生 retry 的验收要求不一致。
4. 因上述失败，Full Regression Gate 在 Backend regression 阶段被阻断。

## 2. 根因分析

### 2.1 Runtime 异常包装边界

`WorkflowExecutionService.run()` 的最外层 `except Exception` 无条件将异常包装为 `HTTPException(500)`。当内部已经完成 Execution → failed 的终态转换时，原始运行时异常仍应保持传播，避免单元测试和 Runtime 调用方丢失真实异常类型。

### 2.2 Retry Governance Audit 兼容动作缺失

Retry scheduling 的 Trace 使用 `node.retry.scheduled`，Audit 当前只写入 `workflow.node.retry_scheduled`。已有 Real API Contract 仍要求 `workflow.node.retry` 作为 retry 发生的治理动作，因此实现缺少兼容审计事件。

### 2.3 Circuit Fast-Fail attempt 边界

Real API 观察到独立 Execution 在 `CIRCUIT_OPEN` Fast-Fail 后的 node attempt 与预期不一致。实现已在 `WorkflowRuntime` 中明确排除 `CIRCUIT_OPEN` 的 retry eligibility，但验收仍暴露 attempt 边界问题，因此必须通过本地真实数据库场景重新验证 Node Execution 创建、状态转换与 attempt 初始化，而不能仅依赖静态代码判断。

## 3. 影响

- Backend default regression 失败，Full Regression 被阻断。
- Real API Gate 失败，因此 Phase 1.5-G 不得标记完成。
- Retry Governance 审计契约与历史验收不兼容。
- Circuit Breaker Fast-Fail 的 Node attempt 语义尚未完成真实数据库验收。

## 4. 已实施修复

提交 `e0fff63ca6fdd56cb40bd7bb03f28b779b34d7a3`：

- 新建 `WorkflowNodeExecution` 时显式设置 `attempt=1`，消除数据库默认值/ORM 默认值差异对首尝试计数的影响。
- Retry scheduling 同时记录 `workflow.node.retry` 与 `workflow.node.retry_scheduled`，保留既有治理契约并继续提供更细粒度动作。
- 当 Execution 已进入 terminal state 后，外层异常处理不再二次包装原始异常；只有非 terminal 异常才转换为 `HTTPException(500)`。

## 5. 预防措施

- 增加/保留 Unit Test：retry budget exhaustion 必须在终态转换后保持原始异常类型。
- Real API 必须验证 retry audit action、node attempt、Trace 顺序以及 Circuit Fast-Fail 不产生 `node.retry.scheduled`。
- Circuit Breaker 的 attempt 语义必须使用真实 PostgreSQL + HTTP API 场景验收，不以静态检查代替。
- 本错误未完成真实本地复测前，不得更新 Phase 1.5-G 为“已完成”。

## 6. 验证要求

开发者本地同步最新 `main` 后必须重新执行：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
cd ..\frontend
npm test
npm run build
cd ..\backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_full_regression_gate.ps1
```

同时必须实际执行 Migration head 验证。以上结果在本次记录创建时均未被本环境重新执行，因此不预填“通过”。
