# Phase 2.7 Checkpoint Tenant Write Boundary

- 日期：2026-08-27
- 阶段：Phase 2.7-A Durable Recovery Closure
- 类型：Durable Checkpoint / Tenant Isolation

## 问题

Checkpoint Recovery 已经通过 `WorkflowExecution` JOIN 支持 tenant scope，但 Checkpoint 的事务写入口此前没有显式接受调用方 tenant scope。这样内部调用如果误传入不属于当前租户的 execution_id，Checkpoint Service 本身缺少可复用的 tenant-boundary Contract。

## 修复

`WorkflowExecutionCheckpointService.append_next_in_transaction()` 增加可选 `tenant_id` scope：

```text
execution_id + tenant_id
        ↓
SELECT WorkflowExecution FOR UPDATE
        ↓
必须命中同一 tenant 的 Execution
        ↓
分配 sequence
        ↓
写入 Checkpoint
```

同时 `latest_recovery_fact()` 的 NodeExecution 查询通过 `WorkflowExecution` JOIN 继承 tenant scope，避免假设 `WorkflowNodeExecution` 自身存在独立 tenant 字段。

## 边界

- Checkpoint 仍属于 WorkflowExecution 的 Durable State。
- sequence 分配仍在锁定 Execution 后进行。
- `append_next_in_transaction()` 不自行 commit，继续由调用方事务统一提交 NodeExecution、Trace 与 Checkpoint。
- execution-level checkpoint 仍不要求 NodeExecution。
- 本修复不创建第二套 Recovery State Source。

## 测试策略

保留 Unit Test；暂停完整 Backend Regression / E2E / Real API Acceptance。当前 GitHub API 工作环境无法执行 pytest，因此不得记录为已通过。