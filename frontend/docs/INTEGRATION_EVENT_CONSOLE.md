# 前端集成事件观察台设计与实现记录

## 1. 任务目标

基于后端已经提供的 `GET /api/v1/runtime/integration-events`，在集成中心增加 Durable Integration Event 观察入口，使运维人员可以直接查看 Workflow、Agent、Scheduler、Model Provider、Tool/Retrieval 等 Runtime 产生的可靠事件事实。

## 2. Contract 对齐

后端接口固定使用当前 JWT 的 `tenant_id`，前端不提供 tenant 查询参数。接口支持分页及以下过滤：`event_type`、`source`、`status`、`subject`、`trace_id`、`request_id`。响应包含 `items/page/page_size/total`，事件项保留 schema version、幂等键、时间、投递状态、尝试次数、错误码及安全的 payload/metadata。

## 3. UI 决策

- 入口放在现有“集成中心”，与 Destination、Subscription、投递运维保持同一业务上下文。
- 使用独立 `IntegrationEventConsole` 组件，避免继续扩大 `integrations/index.vue` 的职责。
- 列表优先展示 Event Type、Source、Subject、Status、Attempts、Occurred，避免在表格中暴露大 Payload。
- 点击事件进入 Drawer 查看完整上下文与 JSON Payload/Metadata。
- 查询只改变前端过滤条件，不允许客户端构造 tenant scope。
- Status 使用统一视觉语义：delivered 为成功、failed/dead_letter 为失败、processing 为处理中，其余为信息态。
- 保留原有 Delivery Operations；Event Observation 是“事实观察”，Delivery Operations 是“可靠投递运维”，两者不混淆。

## 4. 安全与边界

Payload 原样展示是后端已经定义的 Integration Event 运维查询结果；前端不主动增加 prompt、completion、authorization、token 等敏感字段。前端仅负责展示后端返回的数据，不自行拼装或推断事件事实。

## 5. 测试

新增 `tests/views/IntegrationEventConsole.test.ts`，覆盖：

1. 初次加载、事件状态展示及查询参数构造；
2. 点击事件打开详情 Drawer，展示幂等键、Trace ID 与 Payload。

本任务完成后按项目固定顺序执行 targeted test → 全量 test → `npm run build` → `npm run test:gate`，并进行本地手动页面验证。

## 6. 长期演进

当前版本只实现稳定的查询与详情观察。后续按后端 Contract 成熟度逐步增加时间范围过滤、事件详情与 Delivery 关联、Trace 联动、状态聚合、自动刷新和 Observability/SRE 指标，但不得在后端 Contract 未提供能力时由前端虚构业务状态。
