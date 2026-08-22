# Phase 2.1-A — Product / Backend Contract

> 状态：**已完成 Contract 设计，待进入 2.1-B 实现**
> 基线：`main` @ `9de2462629fd92d9584866530cd3e2336bfab804`
> 主题：Organization / Membership / Access Governance

## 1. 决策摘要

### 1.1 Organization 与 Tenant

**Phase 2.1 采用 1:1 映射：一个 Organization 对应一个现有 Tenant。**

原因：当前所有核心资源已经以 `tenant_id` 作为隔离边界。直接把 Organization 再做成独立资源隔离层会导致 Agent、Workflow、Knowledge、Execution、Audit 等大量资源同时迁移授权主键，增加无业务价值的迁移风险。

因此：

```text
Organization (产品概念)
        │ 1:1
        ▼
Tenant (技术隔离边界)
        │
        ├── Agent
        ├── Workflow
        ├── Knowledge
        ├── Tool
        ├── Execution
        └── Audit
```

Organization 是企业产品层概念，Tenant 继续承担数据库隔离和运行时 scope。

### 1.2 Membership

新增 `organization_memberships` 表：

```text
user_id
organization_id
status
role
created_at
updated_at
```

一个 User **允许属于多个 Organization**；但每次请求只能有一个有效 Organization scope。请求 scope 必须经过 Backend 验证 membership 后才能转换为 tenant scope。

现有 `users.tenant_id` 暂时保留，作为迁移兼容字段/默认组织映射，不再作为未来多组织能力的唯一授权来源。

### 1.3 Role

Phase 2.1 不创建复杂 Policy DSL，最小角色固定为：

| Role | 组织管理 | 成员管理 | 资源使用 | 资源管理 |
|---|---|---|---|---|
| owner | 全部 | 全部 | 全部 | 全部 |
| admin | 组织配置 | 成员/角色 | 全部 | 按现有资源 Owner/Admin 规则 |
| member | 只读组织信息 | 无 | 有权限资源 | 按现有资源 Owner/Admin 规则 |

Owner 转移必须是显式操作；普通 Admin 不得删除/降级唯一 Owner。

### 1.4 Membership Lifecycle

```text
invited → active → suspended
              ↓
            removed
```

- `invited`：已创建邀请，但不能访问资源。
- `active`：可按角色访问。
- `suspended`：暂时禁止访问。
- `removed`：永久结束该 membership，不允许通过原记录恢复；重新加入创建新 membership。

## 2. Authorization Contract

最终授权顺序：

```text
Authentication
 → User active
 → Organization scope resolved
 → Membership exists + active
 → Organization role checked
 → Resource tenant_id checked
 → Resource owner/admin rule checked
 → Action allowed
```

禁止：

- 客户端提交 tenant_id 后直接作为授权依据。
- 只验证 user_id 而不验证 membership。
- 前端自行判断 owner/admin 后调用后端管理 API。
- 通过 URL 中的 organization_id 绕过 tenant scope。

## 3. Organization API Contract

Phase 2.1-A 冻结以下逻辑资源，具体版本前缀沿用当前 `/api/v1`：

```text
GET    /organizations
POST   /organizations
GET    /organizations/{organization_id}
PATCH  /organizations/{organization_id}

GET    /organizations/{organization_id}/members
POST   /organizations/{organization_id}/members
PATCH  /organizations/{organization_id}/members/{membership_id}
DELETE /organizations/{organization_id}/members/{membership_id}
```

### 创建 Organization

`POST /organizations`

```json
{
  "name": "Acme AI"
}
```

服务端：

1. 创建 Organization。
2. 创建对应 Tenant。
3. 创建当前用户的 owner membership。
4. 写入 AuditLog。

该操作必须具备幂等/失败回滚语义，不能出现 Organization 已创建而 Tenant 或 owner membership 缺失的半完成状态。

### 成员管理

`POST /organizations/{organization_id}/members`

```json
{
  "user_id": "<uuid>",
  "role": "member"
}
```

Phase 2.1 不实现邮件邀请服务；成员必须引用平台已有 User。邀请邮件/外部身份同步属于后续 IAM Phase。

## 4. Error Contract

| 场景 | HTTP | 语义 |
|---|---:|---|
| Organization 不存在 | 404 | 资源不存在或当前 scope 不可见 |
| 无 membership | 403 | 当前用户无组织访问权 |
| membership 非 active | 403 | 当前 membership 不允许访问 |
| member 执行管理操作 | 403 | 权限不足 |
| 非法 role | 422 | schema validation |
| 删除唯一 owner | 409 | 必须先转移 owner |
| 重复 membership | 409 | 用户已经属于该组织 |
| 跨组织资源访问 | 404/403 | 不泄露跨租户资源存在性，按现有资源 Contract 统一 |

## 5. Migration Contract

### 5.1 兼容原则

不修改既有核心资源的 `tenant_id` 数据类型和含义。

迁移顺序：

```text
Existing Tenant
 → Organization 1:1 record
 → Existing User
 → Membership(active, role derived from existing RBAC)
 → Verify counts
 → Application switches authorization to Membership + Tenant
```

### 5.2 Existing Role compatibility

现有全局 `Role` / `UserRole` 暂时保留以避免一次迁移删除历史权限语义。

Phase 2.1 新增 Organization role 后：

- Organization role 决定组织级管理权限。
- 既有 resource-level owner/admin 检查继续生效。
- 两套权限不得产生“新角色绕过旧资源授权”的路径。

是否在未来删除 `UserRole` 不属于 Phase 2.1。

### 5.3 Migration checks

Migration 必须验证：

- 每个 active Tenant 恰有一个 Organization。
- 每个现有 User 至少有一个 active membership。
- User 的默认 `tenant_id` 与默认 Organization 对应 Tenant 一致。
- owner/admin 映射数量可审计。
- Migration 可重复执行且不重复创建 membership。

## 6. Audit Contract

以下事件必须写 AuditLog：

```text
organization.created
organization.updated
organization.suspended
organization.member.invited
organization.member.activated
organization.member.suspended
organization.member.removed
organization.member.role_changed
organization.owner.transferred
```

Audit 必须关联：

- actor_id
- tenant_id
- organization_id（通过 resource_type/resource_id 或新增结构字段，具体以现有 Audit Contract 最小变更为原则）
- request_id
- trace_id
- action
- status
- error_code（失败时）

## 7. Idempotency / Concurrency

- 创建 membership 必须由数据库唯一约束 `(organization_id, user_id)` 保证并发唯一性。
- 重复创建返回 409，不产生第二条 membership。
- Owner transfer 必须在事务中完成，保证不会出现“零 Owner”或“两个 Owner”最终状态。
- Organization 创建必须使用数据库事务，失败时 Organization/Tenant/owner membership 一起回滚。

## 8. Out of Scope

- SSO / OIDC / SAML。
- SCIM / LDAP / AD。
- 外部邮件邀请系统。
- HR 同步。
- ABAC / Policy DSL。
- 跨 Organization 资源共享。
- 完整 IAM 生命周期平台。

## 9. 2.1-B 实现输入

2.1-B 可以据此开始：

1. SQLAlchemy Organization / Membership model。
2. Alembic migration。
3. Organization service。
4. Membership authorization dependency/service。
5. API schema/router。
6. Audit integration。
7. Backend unit/integration/API Contract tests。

2.1-B 完成后才允许进入 Frontend API Types / UI。
