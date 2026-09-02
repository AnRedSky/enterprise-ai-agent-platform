# Runtime Trace Correlation Ambiguous Mapping

## 1. 发现时间

2026-09-02

## 2. 现象

Runtime Audit / Trace Correlation 的历史审计恢复逻辑通过 `trace_id` 查找 `WorkflowTraceEvent.execution_id` 时，原实现按 `created_at ASC, id ASC LIMIT 1` 取第一条记录。

当同一个 `trace_id` 存在多个 Trace Event 时，即使它们属于同一个 Workflow Execution，原查询也可能返回多行并触发 SQLAlchemy `scalar_one_or_none()` 的 `MultipleResultsFound`；如果同一租户内一个 Trace ID 错误地关联多个 Workflow Execution，首行选择还会产生不可接受的错误关联。

## 3. 根因

`workflow_trace_events.trace_id` 当前不是数据库唯一键，一个 Execution 可以自然产生多个同 Trace ID 的事件，因此不能把“第一条 Trace Event”当作唯一 Execution 映射。

此前代码违反了 Runtime correlation 已确定的治理原则：历史审计缺少正式 `workflow_execution_id` 时，只能在 tenant scope 内恢复一个确定的 Execution，不得猜测旧映射。

## 4. 修复

- 新增 tenant-scoped Trace ID → Execution 解析；
- 使用 `DISTINCT execution_id` 消除同一 Execution 多 Trace Event 的重复行；
- 最多读取两个不同 Execution 用于检测歧义；
- 0 个 Execution 返回未解析；
- 恰好 1 个 Execution 正常恢复；
- 多个 Execution 返回 HTTP 409，明确拒绝猜测关联目标；
- `by_trace` 与历史 `by_audit` 共用同一解析规则，避免双向深链语义漂移。

## 5. 验证

新增：

- `backend/tests/unit/test_runtime_audit_trace_correlation_ambiguity.py`
- `backend/tests/api_real/test_runtime_audit_trace_correlation_ambiguity_acceptance.py`
- `backend/scripts/test/phase-2.10/24_runtime_trace_resolution_regression_gate.ps1`

Gate 不启动或停止 API、Scheduler、Worker、PostgreSQL、Redis；测试数据自动创建和清理；pytest warnings 按错误处理。
