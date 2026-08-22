# Phase 2.2-E — ModelProfile 可选 dimension 的 OpenAPI Contract 断言错误

- 日期：2026-08-22
- Phase：2.2-E Model Provider / Model Profile Governance Foundation
- 类型：测试 Contract 与 Pydantic v2 OpenAPI 表达不一致

## 现象

`tests/api_contract/test_model_provider_contract.py::test_model_provider_openapi_exposes_chat_and_embedding_profiles` 直接断言 `ModelProfileCreate.dimension` 的 OpenAPI schema 存在 `type == integer`，但当前字段定义为 `int | None`。

项目固定使用 Pydantic 2.10.4 / FastAPI 0.115.6。对于可选整数，生成的 OpenAPI schema 表达为 `anyOf: [{type: integer}, {type: null}]`，因此原断言会触发 `KeyError: 'type'`。

## 原因

生产模型定义与数据库设计均允许 embedding dimension 为空（Profile 创建 Contract 中 `dimension` 为可选字段）。错误位于测试 Contract 对 nullable OpenAPI schema 的假设，而不是 Model Profile 生产实现。

## 修复

将 Contract 断言改为验证 `dimension.anyOf` 同时包含 integer 与 null，保持对类型语义的严格约束，同时兼容当前固定的 Pydantic/FastAPI 技术基线。

不通过修改生产 schema 强行生成非 nullable integer，也不降低 Contract 校验强度。

## 验证要求

修复后必须重新执行：

```powershell
cd backend
uv run pytest -q tests/api_contract/test_model_provider_contract.py
uv run alembic upgrade head
uv run alembic current
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

本次提交仅记录已实际发生的测试错误；以上命令在修复提交后由开发者本地重新执行并反馈实际结果。
