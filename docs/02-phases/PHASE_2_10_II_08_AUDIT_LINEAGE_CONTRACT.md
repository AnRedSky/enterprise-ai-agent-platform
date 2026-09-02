# Phase 2.10-II / II-08 — Runtime Correlation Audit Fact Visibility

## 1. 目标

在 Runtime Audit / Trace Correlation 已完成分页、tenant boundary、历史 Audit 关联恢复和明确 Trace / Audit 集合 Contract 后，补齐 Audit Item 中实际用于运维深链的事实字段，避免响应 Contract 丢失资源与 Trace 定位信息。

本切片只扩展既有 `AuditLogItem` Contract，不新增数据库事实、不新增查询入口、不复制 AuditLog 生命周期。

## 2. Backend 实现

`AuditLogItem` 增加以下已有 `AuditLog` 持久化字段：

- `resource_type`：审计动作目标资源类型；
- `resource_id`：审计动作目标资源标识；
- `request_id`：产生审计事实的请求标识；
- `trace_id`：审计事实对应的 Trace 标识。

这些字段直接通过 Pydantic `from_attributes` 从既有 `AuditLog` 映射，不改变数据库结构。

## 3. 设计边界

1. 继续以 `AuditLog` 作为唯一审计事实源。
2. 不接受客户端提供 `tenant_id`，关联查询仍由认证 Claims 决定租户边界。
3. 不修改 Runtime Audit / Trace Correlation 查询算法。
4. 不新增 migration，因为所有字段已经存在于 `audit_logs`。
5. `resource_id`、`request_id`、`trace_id` 保持与历史 Audit 数据兼容的可空语义。
6. Contract 扩展必须保持现有 Runtime CorrelationResponse 的分页结构稳定。

## 4. 测试

新增 Contract 断言，验证 OpenAPI 的 `AuditLogItem` 明确暴露 `resource_type`、`resource_id`、`trace_id`。

验证命令：

```powershell
cd backend
uv run pytest -q -W error tests/api_contract/test_runtime_correlations_contract.py
```

随后执行 Backend 全量回归：

```powershell
uv run pytest -q -W error
```

测试不自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；本切片不要求手工填写测试 ID、Token 或业务数据。

## 5. 完成判定

- Audit Correlation Response 能直接表达资源类型、资源标识与 Trace 标识；
- OpenAPI Contract 明确包含新增事实字段；
- 既有 Runtime Correlation Unit / Real PostgreSQL Acceptance 不改变其业务语义；
- Backend Regression 在开发者本地执行并以实际结果为准。
