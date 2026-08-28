# Agent Delegation 活动数量并发窗口

## 现象

Delegation 创建流程先查询父 Workflow Execution，再统计活动 Delegation，最后插入新 Delegation。若两个请求并发执行，两个事务都可能在插入前观察到相同的 `active_count`，从而同时通过 `max_active_delegations` 检查。

## 根因

`max_active_delegations` 是父 Execution 范围内的并发治理规则，仅依赖 Delegation 表的计数查询无法形成创建操作的串行化边界。

## 修复

创建 Delegation 前对 tenant-scoped 父 `WorkflowExecution` 使用 `SELECT ... FOR UPDATE`。同一父 Execution 的 Delegation 创建因此串行化，活动数量检查与插入共享同一个事务边界；数据库唯一约束继续负责 `delegation_key` 的并发幂等收敛。

## 边界

该修复只解决父 Execution 内活动 Delegation 数量的并发超限窗口，不改变 Delegation 生命周期、Retry/Recovery 或 Worker Runtime 语义。后续 Runtime Integration 仍必须实现 Worker claim/completion fencing，并复用现有 Workflow Runtime 的可靠性边界。
