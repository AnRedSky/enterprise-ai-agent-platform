# Phase 2.1 Acceptance — Enterprise Organization & Access Governance

> 状态：**进行中 / 2.1-D Frontend Gate 已验证 / 2.1-E Real API 扩展验证进行中**
> 未执行的 Gate 不得标记 Passed。

## 1. Acceptance Scope

验证企业组织、成员、角色和资源访问治理能力是否形成完整闭环。

## 2. Acceptance Gates

### A. Product / Contract

- [x] Organization ↔ Tenant 关系冻结。
- [x] Membership 生命周期冻结。
- [x] Owner/Admin/Member 权限矩阵冻结。
- [x] 多组织归属策略冻结。
- [x] 现有 User/Tenant/Role 兼容迁移策略冻结。
- [x] API schema/error contract 冻结。

### B. Backend

- [x] Organization CRUD。
- [x] Membership lifecycle。
- [x] Role assignment。
- [x] Resource scope authorization 基础边界。
- [x] AuditLog。
- [x] Unit / Integration / API Contract tests。

2.1-C Backend API + Contract / Real API Gate 已由用户本地实际结果验证。

### C. Database

用户已实际执行：

```powershell
cd backend
uv run alembic upgrade head
uv run alembic heads
```

实际结果：

```text
Running upgrade 0022_workflow_trigger -> 0023_organization_membership
0023_organization_membership (head)
```

- [x] Migration 实际成功。
- [x] 当前 migration head 为 `0023_organization_membership`。
- [x] Existing Tenant/User 兼容映射已覆盖。

### D. Real API

2.1-C 基线 Gate：

```text
23 passed in 37.45s
[PASS] Real API gate completed.
```

2.1-E 新增 Organization / Membership governance real HTTP suite：

```text
backend/tests/api_real/test_organization_governance_api.py
```

- [ ] Organization lifecycle real HTTP regression。
- [ ] Membership role/status lifecycle real HTTP regression。
- [ ] 普通成员不能执行管理员操作。
- [ ] suspended member 无法访问 Organization。
- [ ] Owner Transfer 单 Owner 不变量。
- [ ] Transfer 后新 Owner / 原 Owner 权限边界。
- [ ] Organization AuditLog。

**2.1-E 扩展后的 Gate 尚未由开发者本地重新执行，因此当前保持未通过状态。**

### E. Frontend

用户本地实际验证：

```text
Targeted organization tests: 15 passed
Full frontend regression: 67 passed
Production build: passed
```

- [x] Organization 管理 UI。
- [x] Members / Role / Status UI。
- [x] Owner Transfer UI。
- [x] Frontend Contract tests。
- [x] production build。

### F. Browser E2E

Phase 2.1 需要新增独立 Browser E2E 场景；不得仅依赖现有 Trigger E2E。

- [ ] Admin 管理组织成员完整链路。
- [ ] Member 权限边界。
- [ ] Suspended member 阻断。
- [ ] Owner Transfer。
- [ ] Audit 可追踪。

## 3. 当前执行顺序

```text
2.1-D Frontend Gate 已通过
 → 2.1-E Organization Real API / Regression
 → 根据实际 Gate 修复问题
 → 2.1-F Organization Browser E2E
 → Final Acceptance
```

## 4. Close Conditions

所有涉及范围的 Gate 必须实际执行并记录结果；未执行不得标记 Passed。关闭时同步：

- `docs/PROJECT_STATUS.md`
- `docs/02-phases/PHASE_2_1.md`
- 本文件
- `docs/04-errors/` 中已分析完成的工程错误
