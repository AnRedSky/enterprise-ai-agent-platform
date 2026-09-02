# ERR-0041 Tenant Safe Real API Bootstrap 重复创建 Membership

## 现象

开发者执行 Backend Regression Gate 时，Backend regression、migration/head verification 与 Phase 2.10 Operator Action Result Lineage Gate 均通过，但 Tenant Safe Real API Gate 在 bootstrap 阶段失败：

```text
POST /organizations/{organization_id}/members -> 409
{"detail":"用户已经属于该 Organization"}
```

## 根因

`/auth/register` 当前 Contract 会将新注册用户自动加入默认 Tenant 对应的 active Organization，并创建 `OrganizationMembership(role="member")`。Tenant Safe Real API bootstrap 在注册新成员后仍继续调用 `POST /organizations/{organization_id}/members`，重复创建同一 membership，因此被 `OrganizationService.add_member()` 按设计拒绝。

这属于测试夹具编排与当前认证/Organization Contract 漂移，不是生产 API 的业务错误。

## 修复

调整 `backend/scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py`：

1. 注册测试用户后不再重复调用 `POST /members`；
2. 通过正式 `GET /organizations/{organization_id}/members` 定位注册时自动创建的 membership；
3. 通过正式 `PATCH /organizations/{organization_id}/members/{membership_id}` 将测试成员从 `member` 提升为 `admin`；
4. 保留所有 fixture 身份、密码、Organization 与 membership ID 自动生成，不要求开发者手工填写测试数据；
5. 保留旧 Organization 恢复路径和 tenant boundary 检查。

## 预防

- Real API bootstrap 必须以当前认证、Organization、Membership Contract 为唯一事实源，不得复制历史 fixture 流程。
- 注册后若业务已经自动建立 membership，测试只能读取并通过正式管理 API 调整角色，不得再次执行创建接口。
- Tenant Safe Real API Gate 继续保持“不自动启动/重启/停止 API、Worker、Scheduler、PostgreSQL、Redis”的服务边界。
- 新增或修改认证/Organization Contract 后，必须同步检查所有 Real API bootstrap 脚本中的 fixture 生命周期。

## 验证边界

本轮开发者反馈中：

- Phase 2.10 Operator Action Result Lineage Gate：通过；
- Backend Regression：`1042 passed, 3 skipped, 79 deselected`；
- Migration/head verification：`0056_merge_legacy_audit_and_operator_governance_heads (head)`；
- Tenant Safe Real API Gate：因上述 bootstrap 重复 membership 问题阻塞；
- 修复提交后需要由开发者重新执行 Tenant Safe Real API Gate 与完整 Backend Regression，未执行前不得标记该 Gate 为通过。
