# Phase 2.7 Acceptance — Terminalization / Replay Closure

## 1. 验收范围

本文件记录 Phase 2.7 的生产主线代码与当前已获得的本地验收证据。未实际执行的 Gate 保持未验收，不使用 GitHub Actions 替代本地证据。

范围：Durable Frontier Claim / overlap fencing、Runtime ownership、Checkpoint durable write boundary、Success / Failure terminalization、Retry exhaustion、Recovery / Replay、stale Worker / lease-loss fencing、completion fact uniqueness、Execution terminalization 旁路防护。

## 2. 代码级验收结论

- Execution worker epoch 与 Frontier attempt 分离；
- Frontier / Execution lease 在最终 transition 前重新验证；
- lease loss 不进入普通业务 failure convergence；
- stale Worker 不得产生新的 terminal durable fact；
- Success / Failure / retry exhaustion 收口到统一 terminalization lifecycle；
- sibling Frontier 在 terminalization 时关闭；
- 通用 Execution transition 不得绕过活动 Frontier guard；
- completion fact 绑定 source Frontier，Replay 对 Execution / Version / fingerprint / Node-set / payload / lifecycle / Next Frontier identity 做一致性校验；
- legacy checkpoint append 已进入统一 durable boundary，sequence uniqueness 由数据库约束保护。

## 3. 实际验证证据

开发者已反馈以下本地结果，基线为 `b5e3c44484f9ffa231fb1f368cfc14afe0d99dea`：

```text
uv run pytest -q
824 passed, 3 skipped, 42 deselected in 34.22s

Tenant Safe Real API Gate
41 passed in 81.83s
[PASS] Tenant-safe Real API gate completed.

uv run alembic upgrade head
uv run alembic current
0039_workflow_node_execution_tenant_trigger (head)
```

这些结果证明 Phase 2.7 主线在该基线已经获得 Backend Regression、Tenant Safe Real API 与 Migration 的实际证据。后续 `37061ab` / `f080ff5` 仅涉及 Phase 2.8 lifecycle 与状态文档，不应把新 Phase 2.8 Unit 结果冒充为已执行。

## 4. 当前验收状态

| Gate | 状态 | 说明 |
|---|---|---|
| 生产主线代码 | ✅ 完成 | Phase 2.7 代码已收口 |
| Backend Unit / Regression | ✅ 有实际证据 | 824 passed / 3 skipped / 42 deselected |
| Migration | ✅ 有实际证据 | head = 0039 |
| Tenant Safe Real API | ✅ 有实际证据 | 41 passed |
| Frontend Gate | 🟡 未在本轮重新执行 | 不借用历史结果 |
| Browser E2E | 🟡 未在本轮重新执行 | 不借用历史结果 |
| 本地手动场景 | 🟡 未在本轮重新执行 | 如发布范围需要再执行 |

因此 Phase 2.7 **主线生产实现已完成，Backend / Migration / Tenant Safe Real API 已有实际证据；Frontend / Browser 等未重新执行部分不宣称最终全栈验收通过**。

## 5. 下一阶段

Phase 2.7 不再是当前开发 blocker。后续开发主线进入 Phase 2.8 Runtime Integration；若最终发布要求完整前端/E2E验收，再独立补齐对应 Gate。
