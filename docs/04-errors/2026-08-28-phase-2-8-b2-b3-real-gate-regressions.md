# Phase 2.8 B2/B3 Real Gate 回归记录

## 1. 发现时间

2026-08-28

## 2. 影响范围

- Phase 2.8 B2 Worker Execution Bridge Real Gate
- Phase 2.8 B3 Delegation completion/failure + generation fencing Real Gate
- Backend default regression

## 3. 问题一：Real Gate 自动注册用户缺少 Organization membership

### 现象

B2 Real Gate 在 Worker Runtime 调用 Model Governance 时失败：

```text
403: 当前用户没有有效的 Organization membership
```

随后在本地重新执行 Backend default regression 时发现 `tests/api_contract/test_api_auth_endpoints.py::test_register_returns_user_payload` 返回 `409`，导致 B2/B3 Gate 在回归阶段提前失败。

### 根因

`POST /auth/register` 已按 B2/B3 Real Gate 的真实治理边界修改为：注册事务必须同时绑定默认 Tenant 对应的 active Organization。原 Contract 测试使用的 `FakeDB` 没有模拟该 Organization，因此生产代码正确返回“默认 Organization 尚未初始化 Organization”的 `409`，测试却仍按旧的“只创建 Tenant”契约断言 `200`。

### 修复

1. 更新 `FakeDB`，为默认 Tenant 提供 active Organization 测试前置状态；
2. 注册成功断言改为验证 `User`、`UserRole` 与 `OrganizationMembership` 均进入同一注册事务；
3. 新增默认 Organization 缺失时稳定返回 `409` 的 Contract 测试；
4. 保留 IntegrityError / duplicate user 的冲突测试，确保错误语义不回退。

本次修复不放宽 Organization membership 权限检查，也不绕过 Governance。

## 4. 问题二：B3 fencing 测试 rollback 后访问 expired ORM identity

### 现象

B3 Real Gate 的旧 generation fencing 断言在 `await db.rollback()` 后访问 `delegation_row.id`，SQLAlchemy AsyncSession 默认状态下可能触发属性重新加载，最终产生：

```text
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
```

### 根因

`rollback()` 会使当前 ORM 实例的持久化属性进入 expired 状态；测试在异步 Session 中隐式触发属性 IO，不属于 B3 业务逻辑失败。

### 修复

在执行会导致 rollback 的 fencing 调用前，将不可变的 `delegation_id` 保存为独立 UUID 值；rollback 后所有查询使用该值，不再从已 expired 的 ORM 实例读取主键。

## 5. 验证边界

必须由开发者本地重新执行 B2/B3 Gate。实际结果产生前，不得将 Real Gate 标记为通过；本次提交只修复 Backend Contract 测试基线，不虚报 Real Gate 验收结果。
