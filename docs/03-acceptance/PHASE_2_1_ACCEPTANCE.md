# Phase 2.1 Acceptance — Enterprise Organization & Access Governance

> 状态：**未开始**
> 本文档先建立验收 Contract，不代表任何功能已经通过。

## 1. Acceptance Scope

验证企业组织、成员、角色和资源访问治理能力是否形成完整闭环。

## 2. Acceptance Gates

### A. Product / Contract

- [ ] Organization ↔ Tenant 关系冻结。
- [ ] Membership 生命周期冻结。
- [ ] Owner/Admin/Member 权限矩阵冻结。
- [ ] 多组织归属策略冻结。
- [ ] 现有 User/Tenant/Role 兼容迁移策略冻结。
- [ ] API schema/error contract 冻结。

### B. Backend

- [ ] Organization CRUD。
- [ ] Membership lifecycle。
- [ ] Role assignment。
- [ ] Resource scope authorization。
- [ ] AuditLog。
- [ ] Unit / Integration / API Contract tests。

### C. Database

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
uv run alembic heads
```

- [ ] Migration 实际成功。
- [ ] `current == heads`。
- [ ] 现有数据兼容性验证完成。

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

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

> Phase 2.1 需要新增独立 Browser E2E 场景；不得仅依赖现有 Trigger E2E。

- [ ] Admin 管理组织成员完整链路。
- [ ] Member 权限边界。
- [ ] Suspended member 阻断。
- [ ] Audit 可追踪。

## 3. Close Conditions

所有涉及范围的 Gate 必须实际执行并记录结果；未执行不得标记 Passed。关闭时同步：

- `docs/PROJECT_STATUS.md`
- `docs/02-phases/PHASE_2_1.md`
- 本文件
- `docs/04-errors/` 中已分析完成的工程错误
