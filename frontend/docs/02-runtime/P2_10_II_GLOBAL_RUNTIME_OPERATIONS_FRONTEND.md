# Global Runtime Operations 前端实现记录

## 1. 范围

本次前端切片基于 main 分支已经稳定的 Global Runtime Operations Contract，实现：

- `frontend/src/api/runtimeOperations.ts` API Types 与 `GET /api/v1/runtime/global` 对齐；
- Operations Console 新增“全局运行态势”Tab；
- 展示 Execution / Workflow / Trigger / Worker / Scheduler 的后端真实事实；
- Vitest 覆盖 Contract 请求参数、核心运行态势、既有 2.10-I 运维能力回归。

前端开发准则要求 Backend Contract → API Types → View / Component → Vitest，并禁止前端复制后端生命周期状态机或推断业务关系。fileciteturn242file0

## 2. Backend Contract 对齐

后端正式入口为 `GET /api/v1/runtime/global`，查询参数：

| 参数 | 类型 | 默认/约束 | 前端用途 |
|---|---|---|---|
| `window_hours` | integer | 24，1~168 | 全局态势时间窗口 |
| `workflow_id` | UUID | optional | 工作流过滤 |
| `agent_id` | UUID | optional | Agent 关联过滤 |
| `trigger_id` | UUID | optional | Trigger 过滤 |
| `execution_id` | UUID | optional | Execution 过滤 |
| `execution_status` | string | optional | Execution 状态过滤 |
| `limit` | integer | 50，1~100 | 最近执行数量 |

当前 Operations Console 首屏只发送 `window_hours` 与 `limit`，不在 UI 中伪造其他关联关系。

响应核心结构：

- `filters`
- `executions.total/status_counts/active_count/recovery_count/items`
- `workflows.total/status_counts`
- `triggers.total/status_counts/scheduled_enabled`
- `worker.liveness/liveness_reason_code/running_frontiers/pending_frontiers/leased_frontiers/expired_leases/active_worker_owners`
- `scheduler.liveness/liveness_reason_code/enabled_scheduled_triggers/durable_frontier_backlog`

Worker / Scheduler 当前没有持久化 heartbeat fact，因此后端明确返回 `liveness=unknown`；前端只做中文解释，不将其渲染为“正常”或“故障”。

## 3. API Types 设计

新增：

- `RuntimeGlobalFilters`
- `RuntimeGlobalExecution`
- `RuntimeGlobalPosture`
- `GlobalRuntimeQuery`
- `runtimeOperationsApi.global()`

时间字段保持 ISO 字符串，UUID 保持字符串，状态值保持后端原值。前端仅负责展示映射。

## 4. UI 设计

Operations Console 采用“全局态势 → 总览 → 专项运维 Tab”的信息层级：

1. 全局态势：快速观察 Execution、Workflow、Scheduler backlog、Worker lease；
2. Worker / Scheduler：显示 liveness 与 reason code；
3. 最近执行：直接展示后端 `executions.items`，不从页面文本推断关系；
4. 原有 Event / Delivery / Provider / Alert / Metrics / Audit / Dead Letter 能力保持不变。

响应式布局继续使用现有 900px breakpoint，移动端指标卡切换为单列。

## 5. 安全与租户边界

前端不接受 tenant_id 参数，也不构造跨租户查询。Tenant identity 由后端认证 claims 决定。前端仅传递业务过滤条件。

Secret、Token、Provider 原始错误均不进入全局态势页面。

## 6. 测试

新增/更新：

`frontend/tests/views/OperationsConsole.test.ts`

覆盖：

- Global Contract 请求参数 `{ window_hours: 24, limit: 50 }`；
- Execution / Workflow / Worker / Scheduler 核心事实渲染；
- `unknown + NO_DURABLE_HEARTBEAT_FACT` 的兼容展示；
- 既有 2.10-I 运维指标与 Provider / Alert API 回归；
- 全局与既有运维 Tab 同时存在。

标准本地顺序遵循准则：

```text
npm test -- tests/views/OperationsConsole.test.ts
npm test
npm run build
npm run test:gate
```

本次代码提交阶段未在远程环境宣称上述本地命令已通过；实际通过结果必须以开发机执行日志为准。测试不得自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis。

## 7. 已知限制

- 当前首屏不提供 Global Contract 的高级过滤表单；API Types 已完整支持，后续可在不改变 Contract 的情况下增加诊断筛选交互。
- Worker / Scheduler liveness 保持 `unknown`，这是后端 Contract 的事实，不由前端补充心跳推断。
