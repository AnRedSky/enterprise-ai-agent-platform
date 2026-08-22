# Phase 2.1 Acceptance — Enterprise Organization & Access Governance

> 状态：**进行中**
> 当前仅记录已实际完成的 Contract / Migration evidence；未执行的 Gate 不得标记 Passed。

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

- [ ] Organization CRUD。
- [ ] Membership lifecycle。
- [ ] Role assignment。
- [ ] Resource scope authorization。
- [ ] AuditLog。
- [ ] Unit / Integration / API Contract tests。

2.1-C API implementation 已提交，但本轮代码变更后的本地 regression 尚未重新执行，因此本节保持未通过状态。

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
- [ ] `current == heads` 在本轮 API 提交后重新核验。
- [ ] 现有数据兼容性计数 / tenant scope 验证完成。

### D. Real API

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

- [ ] 真实 PostgreSQL/Redis 链路通过。
- [ ] 管理员可以管理成员。
- [ ] 普通成员不能执行管理员操作。
- [ ] suspended/removed member 无法访问受保护资源。
- [ ] AuditLog 可查询。

### E. Frontend

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

- [ ] Organization 管理 UI。
- [ ] Members / Role / Status UI。
- [ ] 后端权限结果正确展示。
- [ ] production build 通过。

### F. Browser E2E

Phase 2.1 需要新增独立 Browser E2E 场景；不得仅依赖现有 Trigger E2E。

- [ ] Admin 管理组织成员完整链路。
- [ ] Member 权限边界。
- [ ] Suspended member 阻断。
- [ ] Audit 可追踪。

## 3. 当前执行顺序

```text
2.1-C API Contract implementation
 → Backend regression
 → API Contract / Real API
 → Frontend Contract + UI
 → Frontend regression/build
 → Phase 2.1 Browser E2E
 → Final Acceptance
```

## 4. Close Conditions

所有涉及范围的 Gate 必须实际执行并记录结果；未执行不得标记 Passed。关闭时同步：

- `docs/PROJECT_STATUS.md`
- `docs/02-phases/PHASE_2_1.md`
- 本文件
- `docs/04-errors/` 中已分析完成的工程错误
