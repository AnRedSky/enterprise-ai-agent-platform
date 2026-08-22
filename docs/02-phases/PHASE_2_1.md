# Phase 2.1 — Enterprise Organization & Access Governance

> 状态：**进行中 / 2.1-A Contract 已完成 / 2.1-B Migration Gate 已验证 / 2.1-C API Contract Implementation 进行中**
> 当前基线：`main` @ `0b9ea8014a585e6433c25f1747732c7343378759`
> 前置：Phase 1.9 已正式关闭
> 产品主题：企业组织、成员与资源访问治理基础

## 1. 企业场景

平台已经具备 Tenant、User、Role、UserRole 和后端 RBAC，但这些能力还不足以支持真实企业团队协作。典型场景是：

```text
企业管理员
  ↓
创建/管理 Organization
  ↓
管理成员 → 激活/停用
  ↓
分配 Organization Role
  ↓
成员访问 Agent / Workflow / Knowledge
  ↓
Backend 强制 Organization + Tenant + Resource Scope
  ↓
Audit / Trace
```

目标不是立即实现完整 IAM，而是先建立企业组织模型和可演进的授权边界。

## 2. 当前问题

当前 `User` 直接持有 `tenant_id`，`Role` 是全局唯一角色，`UserRole` 直接关联用户与角色。该模型适合当前 Tenant/RBAC 基础能力，但无法表达：

- 一个企业组织下的成员关系与生命周期；
- 组织管理员与普通成员的职责边界；
- 多 Organization membership；
- 成员被停用后统一阻断资源操作；
- 组织管理动作的审计闭环。

Phase 2.1 必须优先解决模型 Contract，而不是直接在现有 RBAC 代码上堆条件判断。

## 3. Scope

### 3.1 Organization

- 产品层 `Organization` 与现有 `Tenant` 采用 1:1 映射。
- Tenant 继续承担数据库隔离和 Runtime scope。
- Organization 生命周期：active / suspended。

### 3.2 Membership

- `OrganizationMembership`：user ↔ organization。
- 一个 User 允许属于多个 Organization。
- 状态：invited / active / suspended / removed。
- 每次请求只有一个有效 Organization scope，必须由 Backend 验证 membership 后转换为 tenant scope。

### 3.3 Organization Role

最小角色：

- `owner`：组织最高管理权限。
- `admin`：成员、角色和组织级配置管理。
- `member`：使用被授权资源。

资源级细粒度权限继续复用现有 Backend authorization；本阶段不实现 ABAC / Policy DSL。

### 3.4 Resource Scope

以下资源访问必须明确使用 Organization/Tenant scope：

- Agent / AgentVersion
- Workflow / WorkflowVersion / Execution
- Knowledge Base / Document / Retrieval
- Tool / AgentTool
- Audit / Observability

不得由前端提交 organization/tenant 来决定最终授权范围。

## 4. Backend Contract

Phase 2.1-A 已冻结以下逻辑资源，最终实现沿用当前 `/api/v1` 版本边界：

```text
GET    /api/v1/organizations
POST   /api/v1/organizations
GET    /api/v1/organizations/{organization_id}
PATCH  /api/v1/organizations/{organization_id}

GET    /api/v1/organizations/{organization_id}/members
POST   /api/v1/organizations/{organization_id}/members
PATCH  /api/v1/organizations/{organization_id}/members/{membership_id}
DELETE /api/v1/organizations/{organization_id}/members/{membership_id}
```

2.1-C 同时提供显式 owner transfer mutation：

```text
POST /api/v1/organizations/{organization_id}/members/{membership_id}/transfer-owner
```

该接口用于满足 Contract 中“Owner 转移必须是显式操作”的约束；普通 membership PATCH 不允许直接写入 `owner`。

具体 request/response schema、分页、排序、错误码实现必须遵守 `docs/02-phases/PHASE_2_1_A_CONTRACT.md`。

### 安全规则

- 当前认证用户只能操作自己有 Organization 管理权限的组织。
- Organization ID 不是授权依据，必须经过 Backend scope 校验。
- 被 suspended/removed 的 membership 不得继续访问受保护资源。
- Owner 不允许被普通 Admin 删除或降级。
- 所有成员、角色、组织状态变更必须产生 AuditLog。
- Organization 被 suspended 后，普通资源访问被阻断，但 owner/admin 必须仍可进入管理路径以恢复 Organization。

## 5. 数据与迁移原则

Phase 2.1-B 必须先完成数据模型设计，再写 Alembic Migration。

预期核心实体：

```text
organizations
organization_memberships
```

现有 `tenants` 保持技术隔离边界；现有 `roles/user_roles` 暂时保留以兼容历史权限语义。新 Organization role 与旧资源级 owner/admin 检查不得形成绕过路径。

Migration 必须验证：

- 每个 active Tenant 恰有一个 Organization。
- 每个现有 User 至少有一个 active membership。
- User 默认 `tenant_id` 与默认 Organization 对应 Tenant 一致。
- membership 不重复。
- 迁移后资源 tenant scope 不发生漂移。

## 6. 任务拆解

### 2.1-A Product / Backend Contract — **已完成**

已冻结：

- Organization ↔ Tenant 1:1 关系。
- Membership 生命周期。
- Owner/Admin/Member 权限矩阵。
- 多组织归属策略。
- User/Tenant/Role 兼容迁移策略。
- API schema / error / pagination / idempotency Contract。
- Resource scope 与 Audit 规则。

详细 Contract：`docs/02-phases/PHASE_2_1_A_CONTRACT.md`。

### 2.1-B Database Migration + Domain — **Migration Gate 已验证，Backend regression 需在本轮 API 变更后重新执行**

已实现：

- SQLAlchemy `Organization` / `OrganizationMembership` model。
- Alembic `0023_organization_membership` migration。
- Existing Tenant/User 数据兼容映射。
- `OrganizationService`。
- active membership / management authorization 基础规则。
- Owner/Admin/Member role 约束。
- Owner transfer 事务锁定与唯一 Owner 防护。
- membership `(organization_id, user_id)` 数据库唯一约束。

用户本地已实际验证：

```text
uv run alembic upgrade head
Running upgrade 0022_workflow_trigger -> 0023_organization_membership

uv run alembic heads
0023_organization_membership (head)
```

此前 Backend regression：`269 passed, 23 deselected`；该结果发生在本轮 2.1-C API 代码变更之前，因此本轮不得复用为 2.1-C 完成证据。

### 2.1-C API Contract Implementation — **进行中**

已实现：

- `backend/app/schemas/organization.py`。
- `backend/app/api/organizations.py`。
- Organization CRUD API。
- Membership list/create/update/remove API。
- 显式 owner transfer API。
- active membership / management authorization。
- suspended Organization 的管理恢复路径。
- Organization / Membership AuditLog 写入。
- API Contract route/authentication tests。

待本地验证：

- `uv run pytest -q`。
- API Contract tests。
- PostgreSQL + Redis Real API。
- Organization / Membership 真实数据生命周期。
- AuditLog 查询与 request/trace context。

### 2.1-D Frontend Contract + UI

尚未开始。必须等 2.1-C Backend Contract 本地 Gate 通过后进入。

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
- 外部邮件邀请服务。
- ABAC / Policy DSL。
- 跨 Organization 资源共享。
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

## 9. 当前执行结论

**2.1-A 已完成；2.1-B Migration Gate 已由本地实际结果验证；当前继续推进 2.1-C API Contract Implementation。2.1-C 本轮代码提交后必须重新执行 Backend regression，再进入 Real API；在这些 Gate 通过前不得进入 Frontend。**
