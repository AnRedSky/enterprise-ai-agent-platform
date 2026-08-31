# Runtime Audit / Trace 关联响应契约过宽

## 1. 发现时间

2026-08-31

## 2. 问题

Runtime Audit / Trace 关联 API 已声明 `RuntimeCorrelationResponse`，但 Trace 与 Audit 分页集合此前使用 `items: list[Any]`。这使公共 API Contract 无法在 OpenAPI 中明确描述集合元素类型，也无法阻止关联服务意外返回错误领域对象。

同时，`/traces/{trace_id}` 的路径参数没有显式长度边界，与同类 Runtime 查询参数的 Contract 硬化策略不一致。

## 3. 根因

关联查询第一切片优先完成双向查询语义和 tenant isolation，但响应模型复用了通用分页模型，并以 `Any` 作为跨领域集合元素类型，导致 API 层缺少明确的 Trace / Audit 响应类型约束。

路径参数则沿用了普通字符串声明，没有把 Trace ID 的已知最大长度约束提升到 FastAPI/OpenAPI Contract。

## 4. 修复

- 新增 `RuntimeCorrelationTracePage`，明确 `items: list[WorkflowTraceItem]`；
- 新增 `RuntimeCorrelationAuditPage`，明确 `items: list[AuditLogItem]`；
- `RuntimeCorrelationResponse` 改为使用上述两个具体分页 Contract；
- `/traces/{trace_id}` 增加 `1..128` 的路径参数边界；
- 新增 API Contract 测试验证 OpenAPI schema、路径边界和 tenant query parameter 禁止暴露。

## 5. 防回归

通过 `backend/scripts/test/phase-2.10/23_runtime_correlation_contract_hardening_gate.ps1` 执行：

1. Runtime correlation Unit regression；
2. Runtime correlation API Contract hardening；
3. Backend targeted regression；
4. Service startup boundary 检查。

Gate 不自动启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis，也不要求人工填写测试 ID。
