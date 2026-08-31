# Runtime Audit Query 前端 Contract 对齐错误

## 1. 发现时间
2026-08-31

## 2. 现象
Backend `RuntimeOperationAuditQueryResponse` 已将审计主体字段正式定义为 `actor`，但 Operations Console 前端仍以历史 `actor_id` 作为 Type、测试 fixture 和表格字段；同时前端未暴露 Backend 已提供的 `actor` 查询过滤器。

## 3. 根因
II-07 在 Backend 侧完成审计响应 Contract 硬化与 actor 查询过滤后，前端仍沿用 II-06 第一切片时期的弱化 `RuntimeAudit` 类型，导致 API Types、View、测试 fixture 与正式 Backend Contract 不一致。此前测试 fixture 也使用 `actor_id`，因此没有形成真实 Contract 字段漂移的保护。

## 4. 影响
- 审计表格无法稳定展示 Backend 返回的 `actor`；
- 前端 TypeScript 类型无法准确约束审计响应；
- Operations Console 未提供已稳定的 actor 精确过滤能力；
- 测试不能有效阻止 `actor` / `actor_id` 字段回退。

## 5. 修复
- `RuntimeAudit` 与 `RuntimeAuditQuery` 按 Backend Contract 增加 `tenant_id`、`actor`、`details` 及正式字段；
- Audit Tab 增加 actor 查询输入并透传 `actor`；
- 审计结果表改用 `actor`；
- Vitest fixture 改用正式响应字段，并断言 actor filter Contract。

## 6. 预防措施
后续 Backend Contract 发生字段语义变化时，必须同步检查 `frontend/src/api`、View、fixture 与 Contract tests；禁止使用旧字段别名维持第二套事实模型。
