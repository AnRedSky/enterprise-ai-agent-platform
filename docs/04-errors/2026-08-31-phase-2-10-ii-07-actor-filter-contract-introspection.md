# Phase 2.10-II / II-07：Actor 过滤 Contract 测试框架兼容错误

## 1. 现象

`20_runtime_audit_actor_action_hardening_gate.ps1` 在 Actor + Action Unit/API Contract 阶段失败。

失败断言位于：

`backend/tests/api_contract/test_runtime_operations_audit_actor_filter_contract.py`

原测试直接读取 FastAPI `Query` 对象的 `field_info.max_length`，本地固定依赖 `fastapi==0.115.6` / `pydantic==2.10.4` 时该属性并不是 `FieldInfo` 的稳定公开访问入口，因此触发：

`AttributeError: 'Query' object has no attribute 'max_length'`

同一 Gate 的 Actor + Action 业务测试与 Real PostgreSQL Acceptance 尚未被该断言继续阻断验证；此前 Actor Filter Real Gate 已通过。

## 2. 根因

生产路由已经通过 `Query(..., max_length=128)` 声明 actor 参数长度约束。问题不在 API Contract 本身，而在测试使用了 FastAPI/Pydantic 内部参数对象的实现细节作为 Contract 断言。

测试真正需要验证的是公开 HTTP/OpenAPI Contract 是否声明 `actor` 为可选参数且最大长度为 128，而不是某个框架内部 `FieldInfo` 对象是否暴露名为 `max_length` 的属性。

## 3. 修复

将 Contract 测试改为：

1. 继续通过路由依赖确认 `actor` 为非必填参数；
2. 通过 `app.openapi()` 读取公开 GET Contract；
3. 从 OpenAPI 参数 schema 断言 `actor.maxLength == 128`；
4. 保留 GET-only 路由断言。

这样测试验证的是对客户端真正可见的 API Contract，同时避免绑定 FastAPI/Pydantic 内部对象属性实现。

## 4. 防回归

后续新增 API Contract 测试应优先验证：

- HTTP method / path；
- OpenAPI parameter / request / response schema；
- HTTP status code；
- tenant boundary 与业务语义。

除非确有必要，不应直接依赖 FastAPI/Pydantic 内部 `FieldInfo`、`Query` 等实现对象的非稳定属性。

## 5. 验证命令

```powershell
cd backend
uv run pytest -q tests/api_contract/test_runtime_operations_audit_actor_filter_contract.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\20_runtime_audit_actor_action_hardening_gate.ps1
uv run pytest -q
```

本次修复提交前未将未实际执行的本地结果标记为通过；最终 Gate 结果以开发者本地执行结果为准。
