# Runtime Audit 历史审计深链无法恢复 Execution

## 1. 发现时间

2026-09-01

## 2. 问题

Runtime Audit / Trace Correlation 的 `by_audit` 查询此前只读取 `AuditLog.workflow_execution_id`。项目保留了早期审计模型的 `execution_id` 历史字段，同时新的 Workflow Execution 领域以 `workflow_execution_id` 为正式关联入口。

因此，历史 AuditLog 即使仍然保留有效的 `tenant_id + trace_id`，也可能因为缺少 `workflow_execution_id` 被错误视为“无法关联”，导致运维人员从 Audit 深链无法回到当前 Workflow Execution。

## 3. 根因

关联服务第一切片只覆盖当前 Workflow Execution 外键路径，没有把历史审计数据已经存在的 Trace 事实作为兼容恢复入口。

直接把历史 `execution_id` 当作新的 `workflow_executions.id` 使用并不安全，因为代码已经明确将该字段定义为早期可观测性模型的兼容字段，无法证明旧 ID 与当前 Workflow Execution 一一对应。

## 4. 修复

- `RuntimeAuditTraceCorrelationService` 新增统一的 Audit → Execution 解析入口；
- 优先使用正式 `workflow_execution_id`；
- 当正式关联为空且存在 `trace_id` 时，仅在当前 tenant scope 内查询 `WorkflowTraceEvent`，由 Trace 事实恢复 `execution_id`；
- 历史 `execution_id` 仅作为兼容事实保留，不直接猜测其与当前 Workflow Execution 的映射；
- 无法通过正式关联或 tenant-scoped Trace 恢复时继续返回不可关联结果，不放宽租户边界。

## 5. 防回归

补充：

- Unit：历史 Audit 通过 tenant-scoped Trace 恢复 Execution；无 Trace 时不猜测映射；
- Real PostgreSQL Acceptance：创建缺少 `workflow_execution_id` 但保留 `trace_id` 的历史 Audit，验证双向深链及 tenant isolation；
- Runtime Correlation Backend Gate：Unit、API Contract、Real PostgreSQL Acceptance、Backend Regression 全部执行，并将 warning 转换为错误。

## 6. 设计边界

该修复只增强既有只读关联查询，不新增 Audit 存储、不修改历史数据、不复制 Workflow Execution 生命周期规则，也不接受客户端传入 `tenant_id`。
