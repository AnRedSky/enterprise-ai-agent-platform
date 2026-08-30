# P2 Trigger / Execution / Trace / Audit 统一关联

## 目标

在 Runtime Execution 详情中建立企业级四层可观测闭环：**Trigger → Execution → Trace → Audit**。前端只消费后端已经存在的 Contract，不根据时间、状态、排序或唯一记录数量推断 Trigger 与 Execution 的关系。

## 关联事实来源

| 层级 | 前端事实来源 | 规则 |
|---|---|---|
| Trigger | `/workflows/{workflow_id}/triggers` | 仅使用真实 `trigger_id` 查找 |
| Execution | `/runtime/executions/{id}` | 当前 Runtime Execution 唯一事实 |
| Trace | `/runtime/executions/{id}/trace` | 使用真实 `trace_id` 与 trace items |
| Audit | `/runtime/audit-logs?execution_id={id}` | 只展示当前 Execution 的审计记录 |

### Trigger ID 解析优先级

1. Runtime 路由 `trigger_id`。
2. Trace item 的 `data.trigger_id`。
3. 无 ID 时保持“未解析”，禁止猜测。

当前 Webhook 如果后端没有提供真实 Execution ID，仍不能由前端伪造深链接；只能保留已有的 Workflow / Trigger Observation 上下文。

## UI 结构

Runtime Drawer 依次展示：

1. Execution 基础信息。
2. **执行可观测关联**：Trigger ID、Trigger 类型、Execution ID、Trace ID、Audit 数量及关联来源。
3. Trigger 详细信息（能够通过真实 Trigger ID 定位时）。
4. 当前 Execution 的 Audit 审计记录。
5. Retry / Resume 父子 Execution 关系。
6. Runtime Timeline。
7. Workflow Trace Timeline。

## 安全与稳定性

- Audit 查询失败不能阻断 Runtime 主详情。
- Trigger 查询失败不能阻断 Execution / Trace 展示。
- 不向用户展示原始 HTTP 错误、异常堆栈或后端错误正文。
- Technical ID 可以展示和复制，但不能被 UI 翻译或替换成业务猜测值。

## 验收标准

- [x] Execution 详情调用 Audit API 并按 `execution_id` 精确过滤。
- [x] Execution 详情加载 Workflow Trigger 列表。
- [x] Trigger ID 从路由或 Trace `data.trigger_id` 精确解析。
- [x] Trigger → Execution → Trace → Audit 在同一 Runtime 详情中可见。
- [x] 无 Trigger ID 时显示未解析，不进行推断。
- [x] Audit / Trigger 查询失败不影响 Runtime 主链路。
- [x] 专项 Vitest 覆盖成功关联和禁止推断场景。
