# Phase 1.9 Acceptance — Runtime Reliability / Production Hardening

> 状态：进行中
> 基线：最新 `main`

## 1. Acceptance 原则

本文件只记录开发者本地实际执行的验收结果，不预填 PASS，不使用 GitHub Actions 替代本地验收。

## 2. 1.9-A Acceptance

### Circuit Breaker HALF_OPEN Concurrent Recovery

| Gate | 实际结果 | 状态 |
|---|---:|---|
| Circuit Breaker targeted tests | 16 passed / 0.68s | PASS |
| Alembic upgrade head | PostgreSQL upgrade completed | PASS |
| Migration head | `0022_workflow_trigger` | PASS |
| Backend Regression | 262 passed, 20 deselected / 3.64s | PASS |
| Mandatory Real API | 20 passed / 32.99s | PASS |
| Standalone Real API | 20 passed / 33.26s | PASS |

结论：**1.9-A 已通过本地实际验证。**

## 3. 1.9-B Acceptance

### 当前实现

已完成 Runtime Failure / Retry / Circuit Boundary 的 stale Probe completion 修复：

- HALF_OPEN Probe reservation 继续受 PostgreSQL 行锁保护。
- Probe completion 绑定当前 Recovery Window。
- 使用现有 `half_opened_at` 作为 Recovery Window generation boundary。
- stale Probe success 不得关闭新的 Recovery Window。
- stale Probe failure 不得重新 OPEN 新的 Recovery Window。
- 未经过 `before_call()` 的直接 service-level success/failure 调用保持兼容。

对应代码提交：

```text
8085e5c7c6009a97a7d3a1d73094f7812c9f9258
fix: isolate stale circuit probe completions
```

对应专项测试提交：

```text
f7ef0c55810171cb70e5873a99cba82a01a64047
 test: cover stale half-open probe completion
```

### 本地实际验证

开发者在最新 `main` 实际执行：

| Gate | 实际结果 | 状态 |
|---|---:|---|
| Focused 1.9-B runtime tests | 35 passed / 0.97s | PASS |
| Backend Regression | 264 passed, 20 deselected / 4.79s | PASS |
| Alembic upgrade/head | `0022_workflow_trigger` | PASS |
| Mandatory Real API | 20 passed / 40.74s | PASS |
| Standalone Real API | 20 passed / 31.38s | PASS |

结论：**1.9-B 当前 focused scope 已通过本地 Backend / PostgreSQL / Real API 验证。**

## 4. 1.9-C Acceptance — Real API Reliability Scenarios

状态：**阻塞，尚未 Acceptance。**

### 新增测试

```text
backend/tests/api_real/test_phase_1_9c_reliability_api.py
```

覆盖：

- Workflow Execution `Idempotency-Key` 顺序重放返回同一 Execution。
- 两个并发真实 HTTP 请求使用相同 `Idempotency-Key` 时收敛到同一个 Execution。
- 同一 Tenant 下其他用户不能读取目标用户创建的 Execution（ownership isolation）。

### 首轮实际结果

直接运行专项文件时未准备 `WORKFLOW_ID` context：

```text
3 failed in 0.10s
WORKFLOW_ID is required for 1.9-C reliability validation
```

随后正式 Real API Gate 自动 bootstrap context 后，Idempotency race 场景首先暴露 HTTP 500：

```text
22 passed, 1 failed in 39.35s
```

随后开发者重新执行 Gate 时，bootstrap 在准备 Retry boundary fixture 阶段即失败：

```text
POST /workflows/executions/{execution_id}/run
expected HTTP 404, got 500
{"detail":"Workflow Runtime 执行失败"}
```

后端日志明确给出：

```text
AttributeError: 'WorkflowRuntime' object has no attribute 'execute'
```

该错误同时影响 Scheduled Trigger dispatch。

### ERR-0018：Idempotency race

原实现的 idempotency `IntegrityError` 路径存在完整 `AsyncSession.rollback()` 后 ORM 对象过期风险。

已提交修复：

```text
bdecd76b7c186c48fc3b7afdd23cc5d7dff1ecb6
fix: make idempotency race recovery transaction safe
```

对应错误：

```text
docs/04-errors/ERR-0018-idempotency-race-missinggreenlet.md
```

该修复**尚未取得新的本地验证结果**，因此 ERR-0018 不能关闭。

### ERR-0019：WorkflowRuntime orchestration regression

发现根因：`WorkflowExecutionService.run()` 调用 `WorkflowRuntime.execute()`，但当前 `WorkflowRuntime` 仅存在 `execute_node()`，缺少 Runtime orchestration 方法。

已提交修复：

```text
0cb983f979962d182a519a380511284cc11e2cda
fix: restore workflow runtime execution orchestration
```

对应错误：

```text
docs/04-errors/ERR-0019-workflow-runtime-execute-missing.md
```

修复范围包括：

- sequential node orchestration；
- node timeout；
- workflow deadline；
- retry policy；
- workflow retry budget；
- node state transition；
- retry backoff deadline boundary；
- `CIRCUIT_OPEN` / `WORKFLOW_TIMEOUT` 不进入 retry。

**ERR-0019 当前仍为 Open：代码已修复，尚无新的开发者本地验证证据。**

### 当前 Acceptance 判断

**不能标记 PASS。** 当前存在至少一个明确的 Real API bootstrap blocking issue（ERR-0019），同时 ERR-0018 也尚未获得修复后的本地验证证据。

### 下一步

必须先重新执行 Workflow Runtime / Retry / Timeout 相关专项测试，然后执行完整 Real API Gate：

```powershell
uv run pytest -q `
  tests/unit/test_workflow_runtime_timeout.py `
  tests/unit/test_workflow_execution_retry_transition.py `
  tests/unit/test_workflow_retry_budget.py `
  tests/unit/test_workflow_retry_policy.py

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

只有 bootstrap 成功并完成全量 Real API 后，才能继续剩余 1.9-C 场景。

当前注册接口仍将新用户绑定到 canonical `DEFAULT_TENANT_ID`，因此 ownership isolation 不等价于跨 Tenant isolation。

## 5. 下一验收顺序

1. 验证 ERR-0019 WorkflowRuntime orchestration 修复。
2. 同时重新验证 ERR-0018 Idempotency race 修复。
3. 完成 1.9-C 剩余 Real API Reliability 场景。
4. 完成 Frontend / Browser Reliability Convergence。
5. 最终执行 Phase 1.9 Acceptance。

## 6. Phase 1.9 关闭条件

必须同时满足：

- 1.9-A Acceptance PASS；
- 1.9-B Runtime Failure / Retry / Circuit Boundary PASS；
- 1.9-C Real API Reliability PASS；
- 1.9-D Frontend / Browser Reliability PASS；
- Backend / Frontend / Browser 独立 Gate 均来自本地实际执行；
- Migration head 正确；
- PROJECT_STATUS 与 Phase 文档同步；
- 无未记录的阻塞错误。
