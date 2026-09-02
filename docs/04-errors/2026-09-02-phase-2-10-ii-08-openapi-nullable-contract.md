# 2026-09-02 — Phase 2.10-II Runtime Correlation OpenAPI Nullable Contract

## 现象

开发者本地执行：

```powershell
uv run pytest -q -W error tests/api_contract/test_runtime_correlations_contract.py
```

结果为 `5 passed, 1 failed`，失败位置：

```text
assert audit_item["resource_id"]["type"] == "string"
KeyError: 'type'
```

## 根因

`AuditLogItem.resource_id` 与 `trace_id` 在 Python Contract 中声明为 `str | None`。当前 FastAPI / Pydantic OpenAPI 3.1 schema 对 nullable primitive 使用 JSON Schema 的联合表达，而不是始终在字段根节点输出 `type: string`。因此测试错误地把 nullable 字段当作非 nullable 字段断言。

这不是生产响应序列化错误，也不需要数据库 migration。

## 修复

将 Contract 测试改为验证 nullable string 的语义，而不是绑定某一种 OpenAPI 序列化形态：

- 允许 `type: ["string", "null"]`；
- 允许 `anyOf: [{"type": "string"}, {"type": "null"}]`；
- 兼容历史 `nullable: true` 形态。

同时继续强制 `resource_type` 为非空 string。

## 防回归

新增 II-09 Operator Action Result Lineage Real PostgreSQL Acceptance 与对应 Gate，进一步验证 Audit Resource / Trace 字段在真实持久化链中的使用，而不是只验证 OpenAPI 文档。
