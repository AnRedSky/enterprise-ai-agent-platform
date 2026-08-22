# Phase 2.1 — Enterprise Organization & Access Governance

> 状态：**已正式关闭 / 2.1-A～2.1-F-C 全部 Gate 已验证 / 最终联合验收已通过**
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

## 3. Gate 状态

### 2.1-A Product / Backend Contract — **已完成**

Organization ↔ Tenant、Membership 生命周期、Owner/Admin/Member、迁移兼容、API schema/error/pagination、Resource Scope 与 Audit 规则已冻结。

### 2.1-B Database Migration + Domain — **已完成**

已实现 Organization / OrganizationMembership model、Alembic `0023_organization_membership`、Existing Tenant/User 兼容映射、OrganizationService、membership authorization、Owner transfer 与唯一 Owner 防护。Migration 已实际执行并确认 `0023_organization_membership (head)`。

### 2.1-C API Contract Implementation — **Gate 已验证**

Organization CRUD、Membership lifecycle、Owner transfer、management authorization、suspended Organization recovery、Organization/Membership AuditLog 与 API Contract tests 已完成。

### 2.1-D Frontend Contract + UI — **Gate 已验证**

Organization list/create/status、Organization Detail、成员管理、role/status mutation、remove、suspend/recovery、Owner Transfer 与 frontend contract tests 已完成。

### 2.1-E Real API / Regression — **最终联合验收通过**

本次最终联合验收实际结果：

```text
Backend:
275 passed, 30 deselected in 6.92s

Real API:
30 passed in 39.91s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

### 2.1-F Browser E2E + Acceptance — **最终联合验收通过**

F-A/F-B/F-C 均由真实 Browser Gate 验证。最新实际结果：

```text
scripts/test/e2e/02_run_organization_e2e.ps1
3 passed (14.2s)
[PASS] Phase 2.1-F organization browser E2E contract completed.

npx playwright test tests/e2e/organization-management.spec.ts --project="Desktop Chrome"
3 passed (12.8s)
```

覆盖：Login、Organization 管理、Membership lifecycle、Member 权限边界、suspended member 阻断、Owner Transfer 后权限边界以及 Audit UI 证据。

## 4. 最终联合验收

用户最新本地实际结果：

### Frontend Regression / Build

```text
16 test files passed
69 tests passed
Production build passed
[PASS] Frontend regression gate completed.
```

### Backend Regression

```text
275 passed, 30 deselected in 6.92s
```

### Real API

```text
30 passed in 39.91s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

### Browser E2E

```text
3 passed (14.2s)
```

### 最终结论

Phase 2.1 的 Definition of Done 已全部满足：Product / Backend Contract、Migration、Backend tests、真实 PostgreSQL/Redis Real API、Frontend regression/build、Browser E2E、成员生命周期、权限边界和 Audit 均具有实际自动化证据。

**Phase 2.1 正式关闭。**

## 5. 明确 Out of Scope

- SSO / OIDC / SAML。
- SCIM。
- LDAP / Active Directory。
- HR 同步。
- 外部邮件邀请服务。
- ABAC / Policy DSL。
- 跨 Organization 资源共享。
- 完整 IAM 管理平台。

## 6. 后续路线

Phase 2.1 关闭后，按 `docs/PRODUCT_ROADMAP.md` 进入 **Phase 2.2 — Retrieval Production Quality**。下一项正式任务为 2.2-A Product / Retrieval Quality Contract，在未冻结 Provider、数据集、Recall/Precision/Citation 指标前，不直接进入 Provider 或数据库实现。
