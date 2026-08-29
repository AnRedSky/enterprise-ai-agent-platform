# Phase 2.10 Enterprise Integration Event Operations

## 1. 阶段目标

Phase 2.9 已完成 Runtime Integration、Durable Event、Reliable Delivery 与 Webhook Real Acceptance。本阶段不重复建设事件生产链路，而是把 Integration Event 正式提升为可运营的企业级运行事实：可查询、可聚合、可追踪、可诊断，并为后续重试、Replay、Dead Letter、Observability 和权限治理提供稳定边界。

## 2. 任务拆解

### 2.10-A Integration Event Operations Query
状态：**开发中，第一切片已实现**。

已实现：
- `GET /api/v1/runtime/integration-events` 租户隔离查询；
- 分页及 event_type/source/status/subject/trace_id/request_id 过滤；
- occurred_from / occurred_to 时间范围过滤；
- `GET /api/v1/runtime/integration-events/summary` 状态与来源聚合；
- 聚合与列表使用完全相同的 tenant scope 和过滤边界。

### 2.10-B Delivery Operations
待实现：把事件与 Webhook Delivery、lease、attempt、失败原因建立可追踪运维关系，并提供统一失败诊断入口。

### 2.10-C Retry / Replay Operations
待实现：提供受权限控制的 retry/replay 运维动作、幂等保护、操作审计及结果反馈。

### 2.10-D Tenant-scoped Operations Console
已具备基础 Event Observation UI；后续增加时间范围、状态聚合、事件到 Delivery 的关联和 Trace 联动。

### 2.10-E Observability
待实现：事件吞吐、失败率、延迟、积压、Dead Letter 等指标进入统一 Observability/SRE 边界。

### 2.10-F Dead Letter Management
待实现：Dead Letter 查询、原因分类、人工恢复策略、权限和审计。

### 2.10-G Runtime Operational Acceptance
待实现：真实 PostgreSQL + HTTP 验证 Query、Summary、tenant isolation、Delivery relation、Replay/Audit 及运维控制边界。

## 3. 设计约束

1. tenant_id 永远来自当前认证上下文，不接受客户端 tenant 查询参数。
2. Summary 必须复用列表查询的过滤条件，避免出现列表与统计口径不一致。
3. 事件查询只读，不改变 Durable Event 状态。
4. Replay/Retry 必须走正式 Delivery/Integration 领域入口，禁止直接修改数据库状态。
5. 运维动作必须产生 Audit Event，并保留操作者、目标对象、结果和失败原因。
6. 不在 Event Operations API 中引入 Provider Secret、Authorization、Token、Prompt、Completion 或检索正文等敏感运行数据。

## 4. 当前交付单元

本切片修改：
- RuntimeQueryService：增加统一事件时间过滤及 tenant-scoped summary；
- Runtime API：增加时间过滤参数和 summary endpoint；
- Runtime schema：增加 IntegrationEventSummaryResponse；
- API contract：验证新 Operations endpoint 注册与认证边界；
- Unit：验证 tenant scope 与状态/来源聚合。

## 5. 下一切片

下一优先级为 **2.10-B Delivery Operations Query**：以 Integration Event 为入口查询关联 Delivery、当前 lease、attempt、最后错误和审计事实，使管理后台可以从“事件事实”直接进入“投递故障诊断”。
