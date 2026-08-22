# Phase 2.1 — Enterprise Organization & Access Governance

> 状态：**已立项 / 待开发**
> 基线：`main` @ `0150ce83fa36b407b2f4d01b603b524fa3d05977`
> 前置：Phase 1.9 已正式关闭
> 产品主题：企业组织、成员与资源访问治理基础

## 1. 企业场景

平台已经具备 Tenant、User、Role、UserRole 和后端 RBAC，但这些能力还不足以支持真实企业团队协作。典型场景是：

```text
企业管理员
  ↓
创建/管理 Organization
  ↓
邀请成员 → 激活/停用
  ↓
分配 Organization Role
  ↓
成员访问 Agent / Workflow / Knowledge
  ↓
Backend 强制 Organization + Resource Scope
  ↓
Audit / Trace
```

目标不是立即实现完整 IAM，而是先建立企业组织模型和可演进的授权边界。

## 2. 当前问题

当前 `User` 直接持有 `tenant_id`，`Role` 是全局唯一角色，`UserRole` 直接关联用户与角色。该模型适合当前 Tenant/RBAC 基础能力，但无法表达：

- 一个企业组织下的成员关系与生命周期；
- 组织管理员与普通成员的职责边界；
- 未来组织级资源授权的稳定扩展点；
- 成员被停用后统一阻断资源操作；
- 组织管理动作的审计闭环。

Phase 2.1 必须优先解决模型 Contract，而不是直接在现有 RBAC 代码上堆条件判断。

## 3. Scope

### 3.1 Organization

- `Organization` 标识、名称、状态、创建时间。
- Organization 与现有 Tenant 的兼容关系必须在 Contract 中明确。
- 生命周期：active / suspended。

### 3.2 Membership

- `OrganizationMembership`：user ↔ organization。
- 状态：invited / active / suspended / removed。
- 角色归属在 Organization scope 内定义。
- 一个用户是否允许加入多个 Organization 必须在 Contract 中明确；若暂不支持，应通过数据约束固定，而不是隐含实现。

### 3.3 Organization Role

Phase 2.1 最小角色：

- `owner`：组织最高管理权限。
- `admin`：成员、角色和组织级配置管理。
- `member`：使用被授权资源。

资源级细粒度权限继续复用现有 Backend authorization 能力；本阶段不实现 ABAC / Policy DSL。

### 3.4 Resource Scope

以下资源访问必须明确使用 Organization/Tenant scope：

- Agent / AgentVersion
- Workflow / WorkflowVersion / Execution
- Knowledge Base / Document / Retrieval
- Tool / AgentTool
- Audit / Observability

不得由前端提交 organization/tenant 来决定最终授权范围。

## 4. Backend Contract

建议 API：

```text
GET    /api/v1/organizations
POST   /api/v1/organizations
GET    /api/v1/organizations/{organization_id}
PATCH  /api/v1/organizations/{organization_id}

GET    /api/v1/organizations/{organization_id}/members
POST   /api/v1/organizations/{organization_id}/members
PATCH  /api/v1/organizations/{organization_id}/members/{membership_id}
DELETE /api/v1/organizations/{organization_id}/members/{membership_id}

GET    /api/v1/organizations/{organization_id}/roles
```

最终路径、请求/响应 schema、错误码、分页、排序、幂等性和权限矩阵由 Phase 2.1-A Contract 任务冻结后再实现。

### 安全规则

- 当前认证用户只能操作自己有 Organization 管理权限的组织。
- Organization ID 不是授权依据，必须经过 Backend scope 校验。
- 被 suspended/removed 的 membership 不得继续访问受保护资源。
- Owner 不允许被普通 Admin 删除或降级；具体 Owner 转移规则由 Contract 冻结。
- 所有成员、角色、组织状态变更必须产生 AuditLog。

## 5. 数据与迁移原则

Phase 2.1 必须先完成数据模型设计，再写 Alembic Migration。

预期新增实体：

```text
organizations
organization_memberships
organization_roles（若最终决定不复用现有 Role）
organization_role_bindings（若需要）
```

是否直接复用现有 `tenants` / `roles`，必须在 Phase 2.1-A 通过兼容迁移方案决定。禁止在没有数据迁移策略的情况下直接修改既有 `tenant_id` 语义。

## 6. 任务拆解

### 2.1-A Product / Backend Contract

- 冻结 Organization ↔ Tenant 关系。
- 冻结 Membership 生命周期。
- 冻结 Owner/Admin/Member 权限矩阵。
- 冻结多组织归属策略。
- 冻结现有 User/Tenant/Role 数据迁移策略。
- 冻结 API schema / error contract。

### 2.1-B Database Migration + Domain

- Alembic migration。
- SQLAlchemy model。
- Organization/Membership Service。
- 兼容现有 Tenant/RBAC。
- Backend unit/integration tests。

### 2.1-C API Contract

- API router。
- schema。
- authorization dependency/service。
- audit integration。
- API contract tests。

### 2.1-D Frontend Contract + UI

- API types。
- Organization 管理页面。
- Members / role / status 管理。
- 后端错误与权限结果展示。
- Vitest。

### 2.1-E Real API / Regression

- PostgreSQL + Redis 本地真实链路。
- Migration upgrade/current/heads。
- Real HTTP API。
- Backend regression。
- Frontend regression/build。

### 2.1-F Browser E2E + Acceptance

- 管理员创建组织/管理成员。
- Member 权限边界。
- Suspended member 访问阻断。
- Audit 可追踪。
- Acceptance / Project Status / Error Record。

## 7. 明确 Out of Scope

- SSO / OIDC / SAML。
- SCIM。
- LDAP / Active Directory。
- HR 同步。
- ABAC / Policy DSL。
- 跨组织资源共享。
- 完整 IAM 管理平台。

## 8. Definition of Done

Phase 2.1 只有同时满足以下条件才能关闭：

1. Product / Backend Contract 已冻结。
2. Migration 实际 `uv run alembic upgrade head` 成功。
3. Organization/Membership/RBAC 后端测试通过。
4. Real API 通过真实 PostgreSQL/Redis。
5. Frontend regression/build 通过。
6. 涉及用户链路的 Browser E2E 通过。
7. 成员生命周期、权限边界、Audit 均有自动化证据。
8. `PROJECT_STATUS.md`、Acceptance、错误记录同步。

## 9. 下一步

当前只执行 **2.1-A Product / Backend Contract**。在该 Contract 未冻结前，不创建数据库 Migration 和业务实现代码。
