# 2026-08-28 Phase 2.7 Real API blockers and Phase 2.8 transition

## 1. 现象

开发者在 `main` 的 `1917a15` 基线执行 tenant-safe Real API Gate：

- 25 个 Real API 测试中 15 个失败；
- 其中 Runtime Governance 的多个 fixture 使用 `edges: []`，与当前 DAG Contract 的“非空 edges”校验不一致；
- Resume DAG 失败场景出现 source 只有 `prepare/completed`、缺少后续 Node/Checkpoint 的现象；
- Webhook / Governance 场景出现 `Node 不允许从 completed 到 failed`；
- 多个普通 Execution `/run` 出现 409，说明真实 Worker 抢占与 Runtime 生命周期仍需要重新执行确认。

## 2. 根因分析

### 2.1 WorkflowNodeExecution 缺少 tenant durable identity

当前 Runtime 的 DAG Resume 查询需要按 Execution tenant 限制已完成 Node，但 `WorkflowNodeExecution` ORM 没有 `tenant_id`。这会使真实 DAG Runtime 与测试 double 的行为不一致，并可能在 Worker Runtime 中提前中断。

本轮增加：

- `workflow_node_executions.tenant_id`；
- 历史数据从 `workflow_executions.tenant_id` 回填；
- tenant 外键与索引；
- PostgreSQL BEFORE INSERT trigger，在旧调用路径只提供 `execution_id` 时由数据库补齐 tenant fact。

### 2.2 Real API DAG fixture contract drift

当前生产 DAG validator 明确要求非空 `edges`。Runtime Governance 测试中的单节点 DAG 使用 `edges: []` 属于测试 Contract 漂移，不应通过放宽生产 validator 解决。

### 2.3 Node completed 后异常再次进入 failed

Runtime 的 Node policy 需要继续验证完成 Checkpoint 写入异常时的事务回滚边界；如果完成状态已写入 Session 后后续 Durable Write 失败，异常路径不得在同一未回滚状态上再次提交 `completed -> failed`。

本轮先通过 tenant durable identity 修复最早的 DAG Runtime 中断；该生命周期场景必须在本地重新执行 Real API 后决定是否需要下一独立修复。

## 3. 验证要求

上述分析来自开发者实际反馈；本记录不将修复后的 Real API / Migration 结果标记为 PASS。

下一次本地验证必须重新执行：

1. `uv run pytest -q`；
2. `uv run alembic upgrade head` 与 `uv run alembic current`；
3. Phase 2.7 Real API Gate；
4. Phase 2.8 Delegation Contract Real API Gate；
5. Worker / Scheduler 实际运行场景。

只有实际本地输出才能更新为 PASS。
