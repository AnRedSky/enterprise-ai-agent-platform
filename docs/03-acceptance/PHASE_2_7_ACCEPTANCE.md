# Phase 2.7 Acceptance — Terminalization / Replay Closure

## 1. 验收范围

本文件记录 Phase 2.7 的**生产主线代码验收结论**。它不把尚未执行的本地测试、Regression、Real API 或 E2E 标记为通过。

范围：

- Durable Frontier Claim / overlap fencing；
- Runtime consumption ownership；
- Checkpoint Durable write boundary；
- Success / Failure terminalization；
- Retry exhaustion；
- Recovery / Replay convergence；
- stale Worker / lease-loss fencing；
- completion fact uniqueness；
- Execution terminalization 通用入口旁路。

## 2. 代码级验收结论

### Durable ownership

- Execution worker epoch 与 Frontier attempt 分离；
- Frontier / Execution lease 在最终 transition 前重新验证；
- lease loss 不进入普通业务 failure convergence；
- stale Worker 不得产生新的 terminal durable fact。

### Terminalization

- Success 使用 Frontier → Execution 统一锁序；
- Failure / retry exhaustion 收口到统一 Failure lifecycle；
- sibling Frontier 在 terminalization 时关闭；
- 通用 `WorkflowExecutionService.transition()` 的 `completed/failed` 入口禁止绕过活动 Frontier guard；
- terminal Execution 不满足 Claim / Recovery 的可消费条件。

### Replay

- completion fact 绑定 source Frontier；
- Execution / Version / fingerprint / Node-set / payload / lifecycle / Next Frontier identity 必须一致；
- 多 completion fact fail-closed；
- lifecycle / payload drift fail-closed；
- Replay 不依赖历史 Worker owner。

### Checkpoint writer

- legacy `append()` 已进入统一 Durable boundary；
- `frontier_completed` 必须使用 `append_next_in_transaction()`；
- sequence uniqueness 已有数据库约束；
- 不重复创建 migration。

## 3. 验收状态

```text
生产主线代码：完成
Unit Test 实现：完成
Unit Test 执行：未执行
Backend Regression：未执行
Migration verification：未执行
Real API：未执行
Frontend Gate：未执行
Browser E2E：未执行
本地手动测试：未执行
```

因此本文件的“完成”仅表示**主线生产实现已经收口**，不表示运行时质量验收已经通过。

## 4. 下一阶段

按 `docs/01-governance/DEVELOPMENT.md` 进入本地测试与验收阶段：

1. 环境与依赖检查；
2. Unit / Backend default regression；
3. Database migration/head verification；
4. Real HTTP API Gate；
5. Frontend Gate；
6. Browser / Frontend-Backend E2E（如范围需要）；
7. 本地手动场景；
8. 根据真实失败结果形成新的修复提交；
9. 更新本 Acceptance 与 `PROJECT_STATUS.md`。
