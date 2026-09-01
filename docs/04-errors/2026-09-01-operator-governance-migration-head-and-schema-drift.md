# 2026-09-01 Operator Audit API Contract nullable UUID schema 表示不兼容

## 1. 问题现象

开发者执行 `26_operator_audit_query_performance_gate.ps1` 时，Operator Governance Contract 回归出现：

```text
test_operator_audit_query_exposes_filter_bounds FAILED
KeyError: 'format'
```

失败断言位于 `tests/api_contract/test_runtime_operator_audit_contract.py`，测试直接读取 `schemas["operator_action_id"]["format"]`。

## 2. 根因

`operator_action_id` 的生产参数类型是 `UUID | None`。当前 FastAPI / Pydantic OpenAPI 生成器会把可空 UUID 表达为标准的 `anyOf` schema：UUID 分支包含 `type=string` 与 `format=uuid`，另一个分支为 `type=null`。

因此 UUID 的 `format` 并不保证位于参数 schema 顶层。此前 Contract 测试把某一种 OpenAPI 序列化形态误当成固定实现细节，导致测试在 schema 本身正确的情况下触发 `KeyError`。

这不是生产 API 类型错误，也不是数据库 schema 漂移；属于 API Contract 测试对 nullable UUID OpenAPI 表示的兼容性不足。

## 3. 修复

- 在 `tests/api_contract/test_runtime_operator_audit_contract.py` 增加 `_schema_format()` 辅助函数；
- 同时支持顶层 `format` 与 `anyOf` UUID 分支中的 `format`；
- 保留最终契约断言必须为 `format=uuid`，没有放宽为任意字符串；
- 不修改生产 API 参数类型，不通过 `json_schema_extra` 人为污染 OpenAPI schema；
- 保留 `operator_action_id` 的实际 UUID 解析与校验语义。

## 4. 验证要求

必须在同步远端 `main` 后执行：

```powershell
cd backend
uv run pytest -q tests/api_contract/test_runtime_operator_audit_contract.py -W error
uv run pytest -q tests/api_contract/test_runtime_operator_audit_contract.py tests/api_contract/test_runtime_operations_audit_query_contract.py tests/unit -k "operator_audit or operator_action" -W error
uv run alembic heads
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\26_operator_audit_query_performance_gate.ps1
```

## 5. 设计边界

Contract 测试验证业务/API 语义，而不是绑定 OpenAPI nullable schema 的具体序列化布局。生产代码继续使用精确 UUID 类型；数据库 migration 与 tenant boundary 不因测试适配而改变。
