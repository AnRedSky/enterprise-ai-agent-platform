# Phase 2.8 Delegation Runtime Integration — Worker 生命周期第一步

## 本轮实现

Phase 2.8-A 已冻结 Delegation 的生命周期与 Worker completion fencing Contract。本轮在不新增数据库结构、不复制 Workflow Execution 状态机的前提下，先将以下不可变规则落成唯一领域规则入口：

- `pending → running/cancelled`；
- `running → completed/failed/timed_out/cancelled`；
- 所有终态不可再次进入活动态；
- Worker completion 必须处于 `running`，且携带与当前 `worker_execution_id` 相同的 generation identity；
- Delegation timeout 使用调用方统一时钟，边界为 `now >= timeout_at`。

实现位置：`backend/app/services/agent_delegation/lifecycle.py`。

## 为什么先做生命周期与 fencing

Delegation Durable Entity 已经具备 `worker_execution_id`，但当前 Worker Service 仍以 Workflow Execution / Durable Frontier 为正式 work item。若直接把 Delegation 接入 Worker 而没有先固定 completion fencing，旧 Worker、重复 claim 或超时后的迟到结果可能覆盖新一代结果。

因此本轮只固化纯规则，并通过 Unit 覆盖，为下一步 Delegation Worker Claim / Worker Execution 创建提供唯一状态与 fencing 基础；不创建第二套 retry/recovery 状态机。

## 下一步

1. 在 `AgentDelegationService` 增加 tenant-scoped 原子 Claim，写入唯一 `worker_execution_id`；
2. 复用现有 Workflow Worker 的 lease / fencing 边界，不新增独立 Worker 进程；
3. 将 target Agent version 的显式输入、context refs、allowed tools 与 model profile 接入实际 Worker execution；
4. 完成结果以 generation fencing 写回 Delegation，并产生 Audit / Trace；
5. 增加 PostgreSQL Integration 与 Real API：成功、失败、timeout、cancel、stale completion；
6. 真实 Worker 多实例运行下验证同一 Delegation 只能被一个 generation 完成。

## 当前边界

本轮没有声称 Delegation 已经能够由 Worker 实际执行。Real API 仍必须在本地服务启动后重新执行；未执行的结果不得记录为 PASS。
