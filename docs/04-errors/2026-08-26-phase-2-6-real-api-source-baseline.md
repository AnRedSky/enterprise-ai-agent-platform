# Phase 2.6 Real API 源码基线与弃用警告纠偏

## 1. 发现时间

2026-08-26

## 2. 问题

本地开发者在 `main` 基线执行 Real API Gate 时观察到两类异常：

1. Resume Candidate 单元测试产生 `datetime.utcnow()` 弃用警告。
2. `test_runtime_model_governance_api.py` 的本地执行仍直接调用 `/workflows/executions/{execution_id}/run`，在独立 Worker 抢先 claim 时收到 `409 只有 pending Execution 可以 Run`，而远端 `main` 已经统一通过 `run_or_observe_execution()` 处理该合法竞态。

同时，直接执行 `tests/api_real/test_runtime_model_governance_api.py` 在没有 Tenant Safe Context 环境变量时只能得到 Context 缺失失败，不能作为 Real API Gate 结果。

## 3. 根因

远端 `main` 中 Runtime Model Governance Real API 测试已经使用统一的 Worker claim race helper，Resume Candidate 测试也已经使用 timezone-aware UTC 时间构造；本地实际执行源码与远端基线不一致，说明仅检查 `git log` 不足以证明测试源码实际一致。

## 4. 纠正措施

本次新增 `backend/scripts/dev/verify_real_api_source_baseline.ps1`，在 Tenant Safe Real API Gate 的测试执行前强制验证：

```text
HEAD == origin/main
        ↓
关键 Real API / Checkpoint 测试文件无未提交修改
        ↓
Runtime Model Governance 测试使用统一 run_or_observe_execution
        ↓
Execution helper 支持显式多 HTTP 结果契约
        ↓
才允许进入真实 HTTP 测试
```

Resume Candidate 测试统一使用 `datetime.now(UTC).replace(tzinfo=None)`，消除 Python `datetime.utcnow()` 弃用警告。

## 5. 预防措施

- Real API Gate 不再仅依赖 `git log` 判断源码版本；
- 关键测试文件出现本地修改时直接阻断 Gate，避免旧测试代码产生误导性业务失败；
- 直接运行 Real API 测试文件不作为正式验收入口；必须通过 Tenant Safe Real API Gate 准备 Context；
- Worker claim race 只保留 `run_or_observe_execution()` 一个正式测试处理入口；
- 不通过放宽业务断言掩盖 Worker ownership 竞态。
