# Phase 2.3 Runtime Real API Bootstrap — Organization/Tenant Mismatch

## 发生时间

2026-08-23

## 问题

`backend/scripts/test/api-real/01_run_real_api_tests_tenant_safe.ps1` 在 bootstrap 创建 Organization 后，执行 retry/circuit breaker Workflow fixture 时仍失败：

```text
POST /workflows/executions/{execution_id}/run
expected HTTP 404, got 403
{"detail":"当前用户没有有效的 Organization membership"}
```

Backend targeted tests 与默认 regression 均通过，但 Real API Gate 在 bootstrap 阶段尚未进入 pytest suite。

## 根因

Phase 2.3 Runtime Governance 使用 Workflow Execution 的 `tenant_id` 查找 Organization scope。当前数据模型中 `Organization.tenant_id` 是唯一值，意味着 Organization 与 Tenant 是一对一治理边界；登录用户 JWT 同时携带其 `User.tenant_id`。

原 `OrganizationService.create()` 却在创建 Organization 时额外创建了一个新的 Tenant：

1. 用户登录时 JWT 的 `tenant_id` 指向用户原有 Tenant；
2. 创建 Organization 时生成新的 Tenant，并让 Organization 指向该新 Tenant；
3. owner membership 虽然已经建立，但 membership 所属 Organization 的 tenant 与 JWT / Workflow tenant 不一致；
4. Workflow execution 进入 Runtime Governance 后无法在当前 tenant scope 得到匹配的 active Organization membership，最终表现为 403。

因此上一轮仅调整 Real API bootstrap 的创建顺序并不能彻底解决问题；那只是把 Organization 建立提前，但没有修复治理边界本身。

## 修复

`OrganizationService.create()` 改为：

- 复用 owner 用户当前 `tenant_id`；
- 创建 Organization 前检查该 Tenant 是否已有 Organization；
- 保持 `Organization.tenant_id == User.tenant_id == Workflow.tenant_id`；
- 保留 owner membership 的 active/owner 语义；
- 不新增数据库字段，因此不需要 Alembic migration。

该修复同时符合 `Organization.tenant_id` 的数据库唯一约束，以及 Phase 2.3 Runtime Governance 按 execution tenant 解析 Organization 的现有设计。

## 验证要求

开发者本地必须重新执行完整 Gate，不能仅凭 targeted pytest 将 Real API 标记为 Passed：

```powershell
cd backend

uv run pytest -q \
  tests/unit/test_model_provider_governance_contract.py \
  tests/api_contract/test_api_model_provider_governance.py \
  tests/unit/test_runtime_model_governance.py \
  tests/unit/test_workflow_runtime.py \
  tests/api_real/test_runtime_model_governance_api.py

uv run pytest -q
uv run alembic upgrade head

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

Real API Gate 必须实际完成全部测试后，才能进入 Phase 2.3-E acceptance。

## 设计约束

Real API fixture 不得通过绕过 Organization membership、直接写数据库或修改鉴权校验来恢复旧的预期 HTTP 状态。测试 fixture 与生产 Runtime 必须使用同一套 tenant/governance boundary。
