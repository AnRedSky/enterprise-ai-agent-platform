# Durable Frontier Retry Terminal Diagnostics

## 日期

2026-08-27

## 问题

在 Success / Failure terminalization final audit 中检查 `FrontierRetryPolicy` 与 `schedule_frontier_retry()` 时发现：当当前 Frontier 已达到 `max_attempts` 时，代码直接调用 `transition_owned_frontier(..., target_status="failed")`，但没有在 transition 前写入本次 failure 的 `error_code` / `error_message`。

结果是 Frontier 可以进入 Durable `failed` 状态，但自身可能丢失导致终态失败的诊断信息。Execution failure convergence 虽然仍保存 Execution-level error，但 Frontier durable fact 不完整。

## 修复

`backend/app/services/workflow/frontier_retry.py` 现在在 retry / terminal failure 两条路径进入 `transition_owned_frontier()` 前统一写入：

- `frontier.error_code`
- `frontier.error_message`

因此：

```text
retryable + budget remaining
    -> retry_wait + failure diagnostics

retryable + budget exhausted
    -> failed + failure diagnostics

non-retryable
    -> failed + failure diagnostics
```

仍保持：

- 不创建新的 Execution；
- 不创建新的 Frontier；
- commit 仍由调用方事务负责；
- 最终状态推进继续通过 owner + attempt + active lease fencing。

## Unit Test

更新 `backend/tests/unit/test_frontier_retry.py`，增加 retry budget exhausted 后 `failed` Frontier 必须保留 `error_code` / `error_message` 的断言。

## 测试状态

本轮只实现 Unit Test，未执行 pytest、集成测试、E2E、Real API 或本地手动测试。不得记录 PASS。

## 后续

继续执行 Phase 2.7 Success / Failure terminalization final audit 与 Replay convergence final audit；若发现新的生产生命周期缺口，优先修复生产代码后再补 Unit Test。
