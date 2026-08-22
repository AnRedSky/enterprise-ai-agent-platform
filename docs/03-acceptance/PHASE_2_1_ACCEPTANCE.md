# Phase 2.1 Acceptance — Enterprise Organization & Access Governance

> 状态：**进行中 / 2.1-D Frontend Gate 已验证 / 2.1-E Real API Gate 已通过 / 2.1-F Browser E2E 实施中**
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
- [x] Real API / PostgreSQL / Redis Gate。

### C. Database

用户已实际执行：

```powershell
cd backend
uv run alembic upgrade head
uv run alembic heads
```

实际结果：

```text
0023_organization_membership (head)
```

- [x] Migration 实际成功。
- [x] 当前 migration head 为 `0023_organization_membership`。
- [x] Existing Tenant/User 兼容映射已覆盖。

### D. Real API

用户最新完整 Gate：

```text
30 passed in 47.60s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

- [x] Organization lifecycle real HTTP regression。
- [x] Membership role/status lifecycle real HTTP regression。
- [x] 普通成员不能执行管理员操作。
- [x] suspended member 无法访问 Organization。
- [x] Owner Transfer 单 Owner 不变量。
- [x] Transfer 后新 Owner / 原 Owner 权限边界。
- [x] Organization AuditLog。

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

### F. Browser E2E — **实施中**

#### F-A 基础设施 — 已实现，待 Gate

- [x] 独立 Organization Playwright spec。
- [x] 独立 Phase 2.1-F PowerShell Gate script。
- [x] 复用 Desktop Chrome project。
- [x] 使用 `FRONTEND_BASE_URL` / `API_BASE_URL`。
- [x] 使用随机 fixture，避免固定测试账号和组织状态污染。
- [ ] 本地 Browser E2E 实际执行。

#### F-B Organization Management — 已实现，待 Gate

- [x] Login → Organization list。
- [x] 创建 Organization。
- [x] Organization Detail。
- [x] 添加成员。
- [x] member → admin。
- [x] member active/suspended/recovery。
- [x] Organization suspend/recovery。
- [x] Owner Transfer。
- [x] API 校验单 Owner 不变量。
- [ ] 浏览器实际执行通过。

#### F-C 后续 Browser Acceptance — 未开始

- [ ] Member UI 权限边界。
- [ ] Suspended member 阻断。
- [ ] Owner Transfer 后原 Owner / 新 Owner 浏览器权限边界。
- [ ] Audit UI 可追踪。

## 3. 当前执行顺序

```text
2.1-E Real API Gate 已通过
 → 2.1-F-A Browser E2E infrastructure
 → 2.1-F-B Organization Management browser contract
 → 本地 Browser E2E Gate
 → 根据实际结果修复
 → F-C governance browser acceptance
 → Full regression + final acceptance
```

## 4. Close Conditions

所有涉及范围的 Gate 必须实际执行并记录结果；未执行不得标记 Passed。关闭时同步：

- `docs/PROJECT_STATUS.md`
- `docs/02-phases/PHASE_2_1.md`
- 本文件
- `docs/04-errors/` 中已分析完成的工程错误
