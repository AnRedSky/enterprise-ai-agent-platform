# ERR-0025 Durable Scheduler Runtime 首次接入后的本地验证待闭环

## 1. 问题

Persistence Gate 已在开发者本地通过，但原 Scheduler Runtime 仍直接按内存时间槽计算并调用 `WorkflowTriggerService`，没有使用已经建立的 `WorkflowSchedule` / `WorkflowScheduleSlot` 持久化边界。因此 PostgreSQL lease / slot 能力虽然存在，Runtime 尚未真正使用它承担多实例 ownership、重启恢复和持久化 next_run_at。

## 2. 根因

Phase 2.4 的 Persistence 第一版先完成了模型、Migration 与 Repository，Runtime 保留了此前的 interval recovery 实现，导致“持久化层已存在、运行时仍使用旧调度状态来源”的阶段性断层。

该问题不能通过新增第二个 Scheduler Runtime 或复制 Workflow 执行逻辑解决。正确边界是：

```text
Scheduled Trigger
    -> Scheduler Repository
    -> WorkflowSchedule lease
    -> WorkflowScheduleSlot 幂等
    -> WorkflowTriggerService
    -> WorkflowExecution
```

## 3. 本轮修复

1. Scheduler Runtime 改为从 PostgreSQL `WorkflowSchedule` 恢复调度状态；
2. 每个 Scheduler 实例生成独立 owner，并通过 Repository 原子 claim lease；
3. 以持久化 `planned_at` 生成稳定 slot key，使用 `WorkflowScheduleSlot` 作为最终幂等边界；
4. Execution 创建继续复用既有 `WorkflowTriggerService.invoke_scheduled`，没有复制第二套执行实现；
5. Execution 成功创建后绑定到 slot，并由当前 lease owner 原子推进 `next_run_at / last_run_at / last_execution_id`；
6. 首版继续保持 `misfire=skip`：停机期间的历史积压不逐槽补发，下一次计划从当前未来时间重新计算；
7. 新增 Scheduler Runtime targeted unit test 与独立 Runtime Gate；
8. 所有新增代码补充中文职责、边界和关键依赖说明。

## 4. 风险与验证要求

本轮代码尚未由开发者本地执行验证。必须使用真实 PostgreSQL 完成：

```text
Runtime targeted tests
Repository PostgreSQL integration
Backend Regression
```

禁止使用 JSON/JSONL 替代 Scheduler Runtime 的真实 PostgreSQL 持久化路径。

## 5. 后续

Runtime Gate 实际通过后，继续补充：

1. Runtime tenant isolation / misfire targeted integration；
2. Scheduler API Contract 与持久化状态可观测性；
3. Tenant Safe Real API Gate；
4. Audit / Trace 与 Scheduler lifecycle 完整验收。
