# Scheduler Runtime PostgreSQL 验收：Workflow Definition 与清理顺序问题

日期：2026-09-02

## 现象

Scheduler Runtime PostgreSQL 验收测试在调度派发阶段记录：

```text
HTTPException: 422: Workflow definition 必须包含 nodes 数组
```

随后测试清理阶段删除租户时失败：

```text
ForeignKeyViolationError: update or delete on table "tenants" violates foreign key constraint "integration_events_tenant_id_fkey"
```

## 根因

### 1. 验收 fixture 的 Workflow Definition 不满足 Runtime 输入契约

`WorkflowRuntime.validate_definition()` 要求 definition 是对象，并且必须包含 `nodes` 数组。当前 Trigger Service 明确允许历史空节点版本，因此验收 fixture 可以使用 `{"nodes": []}`，而不能使用 `{}`。

测试原先创建 `WorkflowVersion(definition={})`，导致每次 Scheduled Trigger 派发都在创建 Execution 前失败。

### 2. 清理漏删 Runtime Integration Event

`WorkflowTriggerService.invoke_scheduled()` 在创建 Scheduled Execution 时会发布 `scheduler.trigger.dispatched` Integration Event。该事实通过 `tenant_id` 引用租户。

验收测试原先删除了 Audit、Trace、Frontier、Slot、Execution 等数据，但没有删除 `integration_events`。因此最终删除 Tenant 时触发 PostgreSQL 外键约束。

## 修复

1. 将 Scheduler Runtime 验收 fixture 的 Workflow Definition 改为：

```python
{"nodes": []}
```

这样既满足 Runtime Definition 契约，又利用 Trigger Service 已明确授权的 `allow_legacy_empty_nodes=True` 兼容路径。

2. 在租户清理阶段增加：

```sql
DELETE FROM integration_events WHERE tenant_id = :tenant_id
```

并在删除 WorkflowExecution 前执行，确保由 Runtime 派发产生的 Integration Event 不残留到测试租户删除阶段。

## 预防规则

- PostgreSQL Acceptance fixture 必须使用与生产 Runtime 相同的输入契约，不能用缺字段的伪造 Definition。
- 所有会产生持久化事实的 Runtime Service 都必须进入 Acceptance cleanup 清单。
- 删除 Tenant 前，应优先删除所有 tenant-scoped child facts，再删除 Tenant 本身。
- Acceptance Gate 不负责启动或停止任何受保护服务；只检查依赖就绪状态并执行测试。

## 验证

本次代码修复后的本地验证由开发环境执行以下 Gate：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.4\22_scheduler_runtime_gate.ps1
```

验证重点：

- Scheduler Runtime 不再因缺少 `nodes` 字段而在派发阶段失败。
- Scheduler Runtime 能继续创建 ScheduleSlot、WorkflowExecution、Durable Frontier、Audit、Trace 和 Integration Event。
- Acceptance cleanup 能在 PostgreSQL 外键约束下完整删除本次生成的租户数据。
- Gate 不自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis。
