# Phase 2.2-E-4 — Model Provider Audit / Browser Gate Failures

## 1. 发现时间

2026-08-23

## 2. 现象

开发者在 `main` 基线执行 E-4 相关本地 Gate：

### Real API

`backend/scripts/test/api-real/01_run_real_api_tests.ps1`

结果：31 passed、1 failed。

失败用例：

`test_model_provider_profile_governance_lifecycle_real_http`

Provider / Profile CRUD 本身成功，但随后读取 `/runtime/audit-logs` 时无法看到本次 `model_provider.created` AuditLog：

```text
AssertionError: assert 'model_provider.created' in actions
```

根因：`RuntimeQueryService.audit_logs()` 的非 admin 组织范围只识别 `organization` 与 `organization_membership` 两类治理资源；Model Provider / Model Profile AuditLog 使用自身 UUID 作为 `resource_id`，因此虽然 AuditLog 已真实写入数据库，却被查询层的组织可见性过滤掉。

### Browser E2E

`frontend/scripts/test/e2e/02_run_model_provider_governance_e2e.ps1`

结果：1 passed、1 failed。

失败位置：

`frontend/tests/e2e/model-provider-governance.spec.ts:85`

失败原因：

```text
getByLabel('名称') resolved to 2 elements
```

Profile 创建对话框同时存在“名称”和“模型名称”两个 Label，Playwright 的非精确 Label 查询产生 strict mode violation。该问题属于 E2E locator contract，不是生产 UI 表单字段冲突。

## 3. 修复

### Backend

`backend/app/services/runtime_query.py`

新增组织成员范围内的 Model Provider / Model Profile resource-id 子查询：

- `resource_type = model_provider` → 通过 Provider 所属 Organization + active membership 判断可见性。
- `resource_type = model_profile` → 通过 Profile → Provider → Organization + active membership 判断可见性。
- 继续保持跨组织 AuditLog 隔离。

不修改 AuditLog 持久化结构，不新增 migration；本问题属于现有查询授权范围遗漏。

### Frontend E2E

`frontend/tests/e2e/model-provider-governance.spec.ts`

Profile 名称字段改为精确的 accessible name：

```ts
getByRole("textbox", { name: /^\\* 名称$/ })
```

避免与“模型名称”发生前缀匹配。

## 4. 验证要求

修复提交后必须由开发者本地重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\02_run_model_provider_governance_e2e.ps1
```

在本次重新执行完成前，不得把 E-4 或 Phase 2.2 标记为 Passed / Closed。
