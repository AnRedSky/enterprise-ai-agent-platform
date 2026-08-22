# Phase 2.1 — Enterprise Organization & Access Governance

> 状态：**进行中 / 2.1-A Contract 已完成 / 2.1-B Migration Gate 已验证 / 2.1-C Backend API + Real API Gate 已验证 / 2.1-D Frontend UI + Contract Tests 已验证 / 2.1-E Real API Gate 已通过 / 2.1-F-A/F-B/F-C Browser E2E 已通过 / 最终联合验收待执行**
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

## 4. Gate 状态

### 2.1-A Product / Backend Contract — **已完成**

Organization ↔ Tenant、Membership 生命周期、Owner/Admin/Member、迁移兼容、API schema/error/pagination、Resource Scope 与 Audit 规则已冻结。

### 2.1-B Database Migration + Domain — **已完成**

已实现 Organization / OrganizationMembership model、Alembic `0023_organization_membership`、Existing Tenant/User 兼容映射、OrganizationService、membership authorization、Owner transfer 与唯一 Owner 防护。

### 2.1-C API Contract Implementation — **Gate 已验证**

Organization CRUD、Membership lifecycle、Owner transfer、management authorization、suspended Organization recovery、Organization/Membership AuditLog 与 API Contract tests 已完成；既有 Real API 基线已通过。

### 2.1-D Frontend Contract + UI — **Gate 已验证**

Organization list/create/status、Organization Detail、成员管理、role/status mutation、remove、suspend/recovery、Owner Transfer 与 frontend contract tests 已完成。

用户本地实际结果：

```text
Targeted tests: 15 passed
Frontend Regression: 67 passed
Production build: passed
```

### 2.1-E Real API / Regression — **Gate 已通过**

用户最新有效 Gate：

```text
uv run pytest -q
275 passed, 30 deselected

scripts/test/api-real/01_run_real_api_tests.ps1
30 passed in 47.60s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

### 2.1-F Browser E2E + Acceptance — **F-A/F-B/F-C 已通过，最终联合验收待执行**

本阶段不复用既有 Workflow Trigger E2E 作为 Organization 验收证据，新增独立 Browser E2E。

#### 2.1-F-A Browser E2E 基础设施 — **Gate 已通过**

- 保持现有 Playwright `Desktop Chrome` project 与 `FRONTEND_BASE_URL` / `API_BASE_URL` 约定。
- 使用 `frontend/tests/e2e/organization-management.spec.ts`。
- 使用 `frontend/scripts/test/e2e/02_run_organization_e2e.ps1`。
- Fixture 使用随机用户名、密码、Organization 名称，避免污染固定账号/固定组织状态。
- 浏览器通过真实 Login 进入 Vue UI；fixture provisioning 使用真实 Backend HTTP API。

#### 2.1-F-B Organization Management E2E — **Gate 已通过**

浏览器场景已实际执行并通过：

1. 注册真实 E2E Owner 用户与第二测试用户。
2. Login → `/organizations`。
3. 创建 Organization。
4. 进入 Organization Detail。
5. 添加 Membership。
6. `member → admin` 角色变更。
7. `active → suspended → active` 成员生命周期。
8. `active → suspended → active` Organization 生命周期。
9. 显式 Owner Transfer。
10. 通过真实 API 校验 transfer 后只有一个 Owner 且目标成员为 active Owner。

#### 2.1-F-C Governance Browser Acceptance — **Gate 已通过**

已实现并由用户本地真实 Browser Gate 验证：

1. Auth login response 返回 `user_id`，前端 Session 持久化当前用户身份。
2. Organization Detail 根据当前 membership role 控制管理 UI：
   - owner/admin 可管理；
   - member 不显示管理操作；
   - Owner Transfer 仅 owner 可见。
3. Member 浏览器权限边界测试通过。
4. suspended member 浏览器阻断测试通过；Backend 403 被前端归一化为稳定的 Organization Detail 业务错误文案。
5. Owner Transfer 后原 Owner / 新 Owner 浏览器权限边界测试通过。
6. Organization owner E2E 包含 Audit UI `organization.owner.transferred` 可追踪证据。

用户最新实际结果：

```text
scripts/test/e2e/02_run_organization_e2e.ps1
3 passed (14.2s)
[PASS] Phase 2.1-F organization browser E2E contract completed.

npx playwright test tests/e2e/organization-management.spec.ts --project="Desktop Chrome"
3 passed (12.8s)
```

此前失败的 suspended member 403 UI error contract 已修复并经本次真实 Browser Gate 验证通过。

## 5. F-C 后续补充与最终验收

F-C Browser Acceptance Gate 通过后：

- Full frontend regression + production build。
- Backend regression。
- Real API Gate。
- 汇总 Browser / API / Audit Evidence。
- 更新 PROJECT_STATUS / Acceptance。
- 满足 Definition of Done 后正式关闭 Phase 2.1。

## 6. 明确 Out of Scope

- SSO / OIDC / SAML。
- SCIM。
- LDAP / Active Directory。
- HR 同步。
- 外部邮件邀请服务。
- ABAC / Policy DSL。
- 跨 Organization 资源共享。
- 完整 IAM 管理平台。

## 7. Definition of Done

Phase 2.1 只有同时满足以下条件才能关闭：

1. Product / Backend Contract 已冻结。
2. Migration 实际成功。
3. Organization/Membership/RBAC 后端测试通过。
4. Real API 通过真实 PostgreSQL/Redis。
5. Frontend regression/build 通过。
6. Browser E2E 通过。
7. 成员生命周期、权限边界、Audit 均有自动化证据。
8. `PROJECT_STATUS.md`、Acceptance、错误记录同步。

## 8. 当前执行结论

**2.1-E 已由完整 Real API Gate 验证通过；2.1-F-A/F-B/F-C 已由真实浏览器 Gate 验证通过。当前不再修改 F-C 实现，下一步执行 Full Frontend Regression / Production Build、Backend Regression、Real API Gate 联合验收；全部通过后同步 Acceptance / PROJECT_STATUS 并正式关闭 Phase 2.1。**
