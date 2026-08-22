# Phase 2.1 — Enterprise Organization & Access Governance

> 状态：**进行中 / 2.1-A Contract 已完成 / 2.1-B Migration Gate 已验证 / 2.1-C Backend API + Real API Gate 已验证 / 2.1-D Frontend UI + Contract Tests 已验证 / 进入 2.1-E Real API + Regression**
> 前置：Phase 1.9 已正式关闭
> 产品主题：企业组织、成员与资源访问治理基础

## 1. 企业场景

平台已经具备 Tenant、User、Role、UserRole 和后端 RBAC，但这些能力还不足以支持真实企业团队协作。Phase 2.1 建立 Organization / Membership / Access Governance 产品边界，并保持 Tenant 作为数据库隔离和 Runtime scope。

## 2. Scope

### 2.1 Organization

- `Organization` 与现有 `Tenant` 采用 1:1 映射。
- 生命周期：`active` / `suspended`。

### 2.2 Membership

- `OrganizationMembership`：user ↔ organization。
- 一个 User 允许属于多个 Organization。
- 状态：`invited` / `active` / `suspended` / `removed`。

### 2.3 Organization Role

- `owner`：组织最高管理权限。
- `admin`：成员、角色和组织级配置管理。
- `member`：使用被授权资源。

### 2.4 Resource Scope

Agent / Workflow / Knowledge / Tool / Audit 等受保护资源最终必须由 Backend Organization/Tenant scope 决定，不能由前端提交的 organization/tenant 参数直接决定授权。

## 3. Backend Contract

```text
GET    /api/v1/organizations
POST   /api/v1/organizations
GET    /api/v1/organizations/{organization_id}
PATCH  /api/v1/organizations/{organization_id}
GET    /api/v1/organizations/{organization_id}/members
POST   /api/v1/organizations/{organization_id}/members
PATCH  /api/v1/organizations/{organization_id}/members/{membership_id}
DELETE /api/v1/organizations/{organization_id}/members/{membership_id}
POST   /api/v1/organizations/{organization_id}/members/{membership_id}/transfer-owner
```

Owner transfer 是显式 mutation；普通 membership PATCH 不允许直接授予 `owner`。

## 4. 已完成任务

### 2.1-A Product / Backend Contract — **已完成**

已冻结 Organization ↔ Tenant、Membership 生命周期、Owner/Admin/Member、迁移兼容、API schema/error/pagination、Resource Scope 与 Audit 规则。

### 2.1-B Database Migration + Domain — **已完成**

已实现 Organization / OrganizationMembership model、Alembic `0023_organization_membership`、Existing Tenant/User 兼容映射、OrganizationService、membership authorization、Owner transfer 与唯一 Owner 防护。

用户本地 Migration：

```text
uv run alembic upgrade head
completed

uv run alembic heads
0023_organization_membership (head)
```

### 2.1-C API Contract Implementation — **Gate 已验证**

已实现：

- Organization CRUD。
- Membership list/create/update/remove。
- 显式 owner transfer。
- active membership / management authorization。
- suspended Organization 的管理恢复路径。
- Organization / Membership AuditLog。
- API Contract tests。

用户本地实际结果：

```text
uv run pytest -q
275 passed, 23 deselected in 5.02s

uv run pytest -q tests/api_contract/test_api_organization_endpoints.py
4 passed in 1.23s

uv run alembic heads
0023_organization_membership (head)

Real API
23 passed in 37.45s
[PASS] Real API gate completed.
```

### 2.1-D Frontend Contract + UI — **Gate 已验证**

已实现：

- Organization 列表、创建、状态展示。
- Organization Detail。
- 成员列表。
- 添加成员。
- 修改 `admin/member` 角色。
- 暂停 / 恢复成员。
- 移除成员。
- Organization 暂停 / 恢复。
- 独立 Owner Transfer 操作与确认。
- `Membership` table row 类型边界修复。
- `el-tag` 测试 stub。

对应 Contract Tests：

```text
frontend/tests/api/organizations.test.ts
frontend/tests/views/Organizations.test.ts
frontend/tests/views/OrganizationDetail.test.ts
```

用户本地实际结果：

```text
Targeted tests
3 test files
15 passed

Frontend Regression
16 test files
67 passed

Production build
✓ built successfully
```

此前首次 Gate 的 `DefaultRow` / `Membership` 5 个 `vue-tsc` 错误已记录为 `ERR-0020` 并修复；修复后的 targeted tests、完整 Vitest 与 production build 均已由用户实际执行通过，因此 2.1-D 现在可以标记为 Gate Passed。

## 5. 2.1-E Real API / Regression — **实现已开始，等待本地 Gate**

本阶段增加 Organization / Membership 真实 HTTP 场景，不再只验证 API Contract：

- Organization list / detail。
- Membership role/status lifecycle。
- suspended member 真实访问阻断。
- Member 不得执行 Organization management / Owner Transfer。
- 显式 Owner Transfer 与单 Owner 不变量。
- Transfer 后新 Owner 管理能力、原 Owner 管理边界。
- Organization management AuditLog。

新增：

```text
backend/tests/api_real/test_organization_governance_api.py
```

Real API bootstrap 现在会创建一次性 Organization + 第二测试用户，并通过临时 context 注入第二用户 token；密码和 token 不写入仓库。测试脚本执行结束会清理 context 与环境变量。

### 2.1-E Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

当前代码已提交，但**尚未由开发者在本地重新执行该扩展后的 Real API Gate，因此不得标记 Passed**。

## 6. 2.1-F Browser E2E + Acceptance

2.1-E Real API Gate 通过后继续：

- 管理员创建组织/管理成员。
- Member 权限边界。
- Suspended member 访问阻断。
- Owner Transfer。
- Organization suspended / recovery。
- Audit 可追踪。

## 7. 明确 Out of Scope

- SSO / OIDC / SAML。
- SCIM。
- LDAP / Active Directory。
- HR 同步。
- 外部邮件邀请服务。
- ABAC / Policy DSL。
- 跨 Organization 资源共享。
- 完整 IAM 管理平台。

## 8. Definition of Done

Phase 2.1 只有同时满足以下条件才能关闭：

1. Product / Backend Contract 已冻结。
2. Migration 实际成功。
3. Organization/Membership/RBAC 后端测试通过。
4. Real API 通过真实 PostgreSQL/Redis。
5. Frontend regression/build 通过。
6. Browser E2E 通过。
7. 成员生命周期、权限边界、Audit 均有自动化证据。
8. `PROJECT_STATUS.md`、Acceptance、错误记录同步。

## 9. 当前执行结论

**2.1-A、2.1-B、2.1-C、2.1-D 已完成对应 Gate；2.1-D Frontend targeted tests / regression / production build 已实际通过。当前直接进入 2.1-E：扩展 Real API / Regression 覆盖 Organization / Membership 真实 PostgreSQL/Redis HTTP 生命周期。2.1-E 未经本地 Gate 验证前，不提前宣告 Passed。**
