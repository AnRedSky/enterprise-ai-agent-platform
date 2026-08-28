# Phase 2.8 B2/B3 Real Gate 回归记录

## 1. 发现时间

2026-08-28

## 2. 影响范围

- Phase 2.8 B2 Worker Execution Bridge Real Gate
- Phase 2.8 B3 Delegation completion/failure + generation fencing Real Gate

## 3. 问题一：Real Gate 自动注册用户缺少 Organization membership

### 现象

B2 Real Gate 在 Worker Runtime 调用 Model Governance 时失败：

```text
403: 当前用户没有有效的 Organization membership
```

失败位置为 `OrganizationService.require_active_membership()`。

### 根因

`POST /auth/register` 只创建 `User` 与 `UserRole`，没有把新用户加入当前默认 Tenant 对应的 active Organization。认证 Token 中携带了正确的 Tenant，但 Governance 访问 Organization 时仍然无法通过 membership 边界。

### 修复

注册事务现在同时完成：

1. 确认默认 Tenant 存在；
2. 确认默认 Tenant 对应的 active Organization 存在；
3. 创建普通 `user` Role（不存在时）；
4. 创建用户；
5. 创建 active `OrganizationMembership(role="member")`；
6. 在同一事务中提交。

如果默认 Organization 尚未初始化，则注册直接返回稳定的 409，而不是创建一个缺少完整治理边界的孤立用户。

## 4. 问题二：B3 fencing 测试 rollback 后访问 expired ORM identity

### 现象

B3 Real Gate 的旧 generation fencing 断言在 `await db.rollback()` 后访问 `delegation_row.id`，SQLAlchemy AsyncSession 默认状态下可能触发属性重新加载，最终产生：

```text
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
```

### 根因

`rollback()` 会使当前 ORM 实例的持久化属性进入 expired 状态；测试在异步 Session 外部隐式触发属性 IO，不属于 B3 业务逻辑失败。

### 修复

在执行会导致 rollback 的 fencing 调用前，将不可变的 `delegation_id` 保存为独立 UUID 值；rollback 后所有查询使用该值，不再从已 expired 的 ORM 实例读取主键。

## 5. 设计边界

本次修复不放宽 Organization membership 权限检查，也不绕过 Governance；B2 仍然必须经过真实用户、Tenant、Organization membership 与 Model Governance 链路。

B3 测试修复不改变生产 fencing 逻辑，仅消除测试自身的 AsyncSession expired-object 使用错误。

## 6. 后续验证

必须由开发者本地重新执行 B2/B3 Gate，实际结果未产生前不得将 Real Gate 标记为通过。
