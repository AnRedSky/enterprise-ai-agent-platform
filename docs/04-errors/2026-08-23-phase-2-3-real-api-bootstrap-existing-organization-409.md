# Phase 2.3 Real API Bootstrap — Existing Organization 409

## 发生时间

2026-08-23

## 问题

`backend/scripts/test/api-real/01_run_real_api_tests_tenant_safe.ps1` 在数据库已有治理数据的本地环境中重新执行时，bootstrap 创建 Organization 失败：

```text
POST /organizations -> 409
{"detail":"当前 Tenant 已存在 Organization"}
```

此前 targeted tests、Backend default regression 与 migration 均已通过，但 Real API Gate 在 bootstrap 阶段被 409 阻断。

## 根因

Phase 2.3 的治理边界要求一个 Tenant 对应唯一 Organization。Real API bootstrap 已经从“创建 Organization 时产生错误 Tenant”修正为复用 owner tenant，但 fixture 仍假定每次运行都可以创建新的 Organization。

本地 Real API Gate 是可重复执行的真实 HTTP 场景；当 owner tenant 已经存在 Organization 时，生产 API 正确返回 409。测试 bootstrap 将这个业务唯一性约束误判为不可恢复的初始化错误。

## 修复

`backend/scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py` 调整为：

1. 使用 owner 登录结果读取当前 `tenant_id`；
2. 通过真实 `GET /organizations` 查找 owner tenant 已存在的 Organization；
3. 找到同 tenant Organization 时直接复用；
4. 首次运行且不存在 Organization 时才调用 `POST /organizations`；
5. 对 GET 与 POST 之间的并发竞态，若 POST 返回 409，则重新 GET 并复用同 tenant Organization；
6. 无论创建还是复用，都强制校验 `Organization.tenant_id == owner.tenant_id`；
7. 不通过数据库直写、绕过鉴权或删除既有 Organization 恢复测试。

这样 Real API fixture 与生产 Organization 一对一 Tenant 治理约束保持一致，同时具备重复执行能力。

## 验证要求

开发者本地必须实际重新执行：

```powershell
cd backend

uv run pytest -q `
  tests/unit/test_organization_tenant_scope.py `
  tests/unit/test_model_provider_governance_contract.py `
  tests/api_contract/test_api_model_provider_governance.py `
  tests/unit/test_runtime_model_governance.py `
  tests/unit/test_workflow_runtime.py `
  tests/api_real/test_runtime_model_governance_api.py

uv run pytest -q
uv run alembic upgrade head

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

只有 Real API bootstrap 与后续 pytest 全部实际完成，才能将该问题标记为关闭并继续 Phase 2.3 acceptance。

## 设计约束

- Real API fixture 必须通过生产 HTTP API 创建或查询治理资源。
- Tenant / Organization 唯一性不能由测试脚本绕过。
- owner token、Organization tenant、Workflow execution tenant 必须保持同一治理边界。
- `tenant_safe` runner 不能依赖数据库清理来获得“每次全新环境”的假设。
