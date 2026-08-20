# Phase 1.5-G：Circuit Breaker 实施与验收计划

> 本文维护 Phase 1.5-G 的领域范围、实现边界、验收门禁和实际推进状态。长期工程规则以 `docs/DEVELOPMENT.md` 为准；所有开发直接基于 `main`。

## 1. 目标

在 Workflow Runtime 已具备 Timeout + Retry + Failure Recovery 的基础上，补齐数据库持久化的 Circuit Breaker，形成：

```text
CLOSED
  ↓ transient failure threshold
OPEN
  ↓ recovery timeout
HALF_OPEN
  ↓ probe success
CLOSED
```

核心目标：

- Runtime worker 无状态，Circuit State 由 PostgreSQL 共享。
- Circuit State 严格按 `tenant_id + circuit_key` 隔离。
- OPEN 状态 Fast-Fail，返回 503 / `CIRCUIT_OPEN` 语义。
- 只有 transient failure 才计入熔断阈值。
- HALF_OPEN 探活并发受 `half_open_max_calls` 限制。
- Circuit Breaker 不应错误吞掉业务/权限/参数类失败。
- Circuit Breaker 与既有 Retry / Workflow Deadline 保持边界清晰。

## 2. 当前 main 基线

当前已落地：

1. `WorkflowCircuitState` 持久化模型。
2. `0020_workflow_circuit_breaker` Alembic migration。
3. `CircuitBreakerService` CLOSED / OPEN / HALF_OPEN 状态机。
4. Tenant + circuit key 隔离。
5. 数据库行锁保护状态读取与更新。
6. Workflow Runtime Circuit Breaker 集成。
7. Circuit 配置校验。
8. transient failure 分类，避免 404 / 403 / 422 等业务错误错误触发熔断。
9. Circuit Breaker Unit Test 与 Runtime Contract Test。

## 3. 测试 Gate 结构调整

此前的 `backend/scripts/test/integration/01_frontend_backend_gate.ps1` 只是重复编排 Backend regression、Migration、Real API 和 Frontend test/build，不提供独立的 Frontend/Backend E2E 测试能力，已从 `main` 删除。

当前全套质量门统一由：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_full_regression_gate.ps1
```

负责编排：

```text
Backend regression
    ↓
Migration/head verification
    ↓
Real HTTP API Gate
    ↓
Frontend test + production build
```

`backend/scripts/test/integration/` 当前仅保留未来真正 Browser / Frontend-Backend E2E 编排职责，不得重新复制已有测试 Gate。

## 4. 本轮强制验收

必须由开发者本地实际执行：

```powershell
cd backend
uv run pytest -q

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migration\01_migrate.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1

cd ..\frontend
npm test
npm run build

cd ..\backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_full_regression_gate.ps1
```

不得以未实际执行的结果标记 Phase 1.5-G 通过。

## 5. Real API 边界验收

Real API 必须覆盖至少以下场景：

1. Circuit disabled：行为与未启用 Circuit Breaker 时一致。
2. transient failure 连续达到 `failure_threshold`：状态由 CLOSED → OPEN。
3. OPEN 状态请求立即 Fast-Fail，不再次调用 Model Provider。
4. 404 / 403 / 422 等 non-transient failure 不增加 Circuit failure count。
5. recovery timeout 到期：OPEN → HALF_OPEN。
6. HALF_OPEN 探活数量不超过 `half_open_max_calls`。
7. 探活成功：HALF_OPEN → CLOSED，并清零失败计数。
8. 探活失败：HALF_OPEN → OPEN，并重新开始 recovery timeout。
9. Tenant A 的失败不得影响 Tenant B 的同名 circuit key。
10. Circuit OPEN 不应消耗 Retry budget。
11. Retry delay 与 Workflow deadline 的既有治理规则不得被 Circuit Breaker 绕过。
12. Execution / Node / Trace / Audit 最终状态保持一致。

## 6. 当前状态

- 测试基础设施治理：已完成，重复 Frontend/Backend 全套 Gate 已删除并迁移到 Release / Full Regression Gate。
- 实现：已提交到 `main`。
- Migration：已创建 0020，待开发者本地执行 head 验证。
- Unit / Contract：已存在，待开发者本地全量回归确认。
- Real API：待完成 Circuit Breaker 真实边界验收。
- Frontend：Circuit Breaker 当前无独立 UI 需求，仍需执行既有前端测试与生产构建作为阶段门禁。

## 7. 下一步

优先完成 Circuit Breaker Real API 边界验收；若全部通过，则更新 `docs/PROJECT_STATUS.md` 收口 Phase 1.5-G，再进入 Workflow Execution 查询/历史治理，并最终进入异步 Worker / 调度能力。
