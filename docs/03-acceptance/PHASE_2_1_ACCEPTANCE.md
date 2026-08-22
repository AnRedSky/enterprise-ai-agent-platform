# Phase 2.1 Acceptance — Enterprise Organization & Access Governance

> 状态：**已正式关闭 / 最终联合验收通过**
> 结论依据：开发者本地实际执行结果；未执行的 Gate 不得标记 Passed。

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

此前用户已实际执行：

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

### D. Real API / Backend Final Joint Gate

本次用户最新实际结果：

```text
uv run pytest -q
275 passed, 30 deselected in 6.92s

scripts/test/api-real/01_run_real_api_tests.ps1
30 passed in 39.91s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

- [x] Organization lifecycle real HTTP regression。
- [x] Membership role/status lifecycle real HTTP regression。
- [x] 普通成员不能执行管理员操作。
- [x] suspended member 无法访问 Organization。
- [x] Owner Transfer 单 Owner 不变量。
- [x] Transfer 后新 Owner / 原 Owner 权限边界。
- [x] Organization AuditLog。

### E. Frontend Final Joint Gate

本次用户最新实际验证：

```text
16 test files passed
69 tests passed
Production build passed
[PASS] Frontend regression gate completed.
```

- [x] Organization 管理 UI。
- [x] Members / Role / Status UI。
- [x] Owner Transfer UI。
- [x] Frontend Contract tests。
- [x] production build。

### F. Browser E2E

#### F-A 基础设施 — **Gate 已通过**

- [x] 独立 Organization Playwright spec。
- [x] 独立 Phase 2.1-F PowerShell Gate script。
- [x] 复用 Desktop Chrome project。
- [x] 使用 `FRONTEND_BASE_URL` / `API_BASE_URL`。
- [x] 使用随机 fixture，避免固定测试账号和组织状态污染。
- [x] 本地 Browser E2E 实际执行。

#### F-B Organization Management — **Gate 已通过**

- [x] Login → Organization list。
- [x] 创建 Organization。
- [x] Organization Detail。
- [x] 添加成员。
- [x] member → admin。
- [x] member active/suspended/recovery。
- [x] Organization suspend/recovery。
- [x] Owner Transfer。
- [x] API 校验单 Owner 不变量。
- [x] 浏览器实际执行通过。

#### F-C Governance Browser Acceptance — **Gate 已通过**

- [x] Auth session 持久化当前 user id。
- [x] Member 不显示 Organization / Membership 管理控件。
- [x] Owner Transfer 仅当前 owner 显示。
- [x] Member 权限边界 Browser E2E。
- [x] Suspended member 阻断 Browser E2E。
- [x] Owner Transfer 后原 Owner / 新 Owner 浏览器权限边界 Browser E2E。
- [x] Owner E2E 增加 Audit UI 可追踪证据。

最新 Browser 实际结果：

```text
scripts/test/e2e/02_run_organization_e2e.ps1
3 passed (14.2s)
[PASS] Phase 2.1-F organization browser E2E contract completed.

npx playwright test tests/e2e/organization-management.spec.ts --project="Desktop Chrome"
3 passed (12.8s)
```

## 3. Close Conditions

- [x] Product / Backend Contract 已冻结。
- [x] Migration 实际成功。
- [x] Organization/Membership/RBAC 后端测试通过。
- [x] Real API 通过真实 PostgreSQL/Redis。
- [x] Frontend regression/build 通过。
- [x] Browser E2E 通过。
- [x] 成员生命周期、权限边界、Audit 均有自动化证据。
- [x] `PROJECT_STATUS.md`、Phase、Acceptance、错误记录同步。

**Phase 2.1 Acceptance 通过并正式关闭。**

## 4. 下一阶段

进入 Phase 2.2 — Retrieval Production Quality。下一验收入口为 `PHASE_2_2_ACCEPTANCE.md`，首项任务为 2.2-A Product / Retrieval Quality Contract。
