# Global Runtime Operations 前端实现记录

## 1. 范围

本次前端切片基于 main 分支已经稳定的 Global Runtime Operations Contract，实现：

- `frontend/src/api/runtimeOperations.ts` API Types 与 `GET /api/v1/runtime/global` 对齐；
- Operations Console 新增“全局运行态势”Tab；
- 展示 Execution / Workflow / Trigger / Worker / Scheduler 的后端真实事实；
- Vitest 覆盖 Contract 请求参数、核心运行态势、既有 2.10-I 运维能力回归。

前端开发准则要求 Backend Contract → API Types → View / Component → Vitest，并禁止前端复制后端生命周期状态机或推断业务关系。

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

## 8. Phase 2.10-II / II-06 Runtime Audit Query 前端实现

后端已在 `GET /api/v1/runtime/operations/audit/query` 提供 tenant-scoped 分页审计查询 Contract。前端在不新增事实源的前提下，将既有 Operations Console 的 Audit Tab 从简单 `limit` 查询升级为正式分页查询。

### 8.1 Contract 对齐

支持参数：

- `page`：从 1 开始；
- `page_size`：1~100，默认 50；
- `action`：动作精确过滤；
- `resource_type`：资源类型精确过滤；
- `resource_id`：资源标识精确过滤；
- `outcome`：结果精确过滤；
- `since` / `until`：时间窗口。

前端 API client 新增 `runtimeOperationsApi.auditQuery()` 与 `RuntimeAuditQuery / RuntimeAuditQueryResponse`，不接受 `tenant_id`，tenant boundary 继续由后端认证 Claims 决定。

### 8.2 UI 实现

Audit Tab 提供：

- 动作、资源类型、资源标识、结果筛选；
- 开始/结束时间筛选；
- 查询与重置；
- 分页、每页数量切换；
- 空数据、加载和失败恢复反馈；
- 结果表展示 action、resource_type、resource_id、outcome、actor、created_at；
- 操作主体精确过滤与 `actor` 字段展示与 Backend II-07 Contract 保持一致。

页面不展示 Secret、Token 或原始 Provider 错误，不复制后端审计状态机。

### 8.3 测试

`frontend/tests/views/OperationsConsole.test.ts` 新增审计 Contract 回归：

- 首次加载发送 `page=1/page_size=20` 以及空过滤条件；
- 正确渲染资源类型、资源标识、结果和操作主体；
- 验证 actor/action/resource 查询参数入口；
- 验证分页查询入口已经替换旧的无限制 `limit` 审计读取。

### 8.4 Contract 漂移修复

Backend II-07 响应契约将审计主体正式字段定义为 `actor`。此前前端仍使用历史 `actor_id`，造成类型、fixture 与表格字段漂移。该问题已通过以下方式修复：

- API Type 使用正式 `RuntimeAudit` 字段：`tenant_id`、`actor`、`action`、`resource_type`、`resource_id`、`outcome`、`details`、`created_at`；
- Audit Query 参数增加 `actor`，不增加 `tenant_id`；
- View 使用 `actor` 展示操作主体；
- Vitest fixture 与断言全部改为正式 Backend Contract。

本地验收仍必须执行：

```text
npm test -- tests/views/OperationsConsole.test.ts
npm test
npm run build
npm run test:gate
```

实际命令未执行前不得记录为通过；Real API / Browser E2E 仅在本地已有后端服务并满足测试数据自动生成约束时执行。
