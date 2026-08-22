# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 最新产品基线：Phase 2.1-E Real API Gate 已通过；Phase 2.1-F-A / F-B Browser E2E 已通过当前本地 Gate；当前进入 F-C Browser Acceptance。
- 开发原则：所有任务直接基于最新 `main`，禁止把临时分支作为长期开发基线。
- 当前开发阶段：**Phase 1.9 已完成 / 正式关闭；Phase 2.1 进行中；2.1-A/2.1-B/2.1-C/2.1-D/2.1-E/2.1-F-A/2.1-F-B 已完成对应 Gate；当前推进 2.1-F-C governance browser acceptance。**
- 产品能力基线：`docs/PRODUCT_CAPABILITY_BASELINE.md`
- 产品与功能开发对比矩阵：`docs/PRODUCT_DEVELOPMENT_MATRIX.md`
- 产品整体路线：`docs/PRODUCT_ROADMAP.md`

## 2. Phase 2.1 Gate 证据

### Backend / Migration

```text
uv run pytest -q
275 passed, 30 deselected

uv run alembic heads
0023_organization_membership (head)
```

### 2.1-D Frontend

```text
Targeted organization tests: 15 passed
Full Frontend Regression: 67 passed
Production build: passed
```

### 2.1-E Real API

用户最新有效完整 Gate：

```text
[1/2] Prepare real API test context
[2/2] Execute all real HTTP API tests
30 passed in 47.60s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

### 2.1-F Browser E2E

用户最新本地 Gate：

```text
scripts/test/e2e/02_run_organization_e2e.ps1
1 passed (8.7s)
[PASS] Phase 2.1-F organization browser E2E contract completed.
```

并使用 Playwright targeted command 再次验证：

```text
npx playwright test tests/e2e/organization-management.spec.ts --project="Desktop Chrome"
1 passed (8.5s)
```

此前 Browser E2E 连续发现的三个测试实现问题均已记录并修复：

- `getByText('成员')` strict mode：改为唯一 heading locator。
- Auth register 实际字段为 `user_id`：E2E 改为 `memberUser.user_id`。
- Element Plus MessageBox confirmation：改为当前可见 MessageBox 内的 primary confirmation button。

因此 **2.1-F-A / 2.1-F-B 当前可以标记 Passed**。

## 3. Phase 状态

| Phase | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 基础项目初始化与最小能力 |
| Phase 1.2 | 已完成 | 基础平台、Auth/RBAC、Agent、Session、Runtime、Model/Tool 基础能力 |
| Phase 1.3 | 已完成当前历史范围 | Model Gateway / Tool Runtime / Memory / Observability |
| Phase 1.4 | 已完成当前历史范围 | Knowledge / RAG / Retrieval；真实 Provider 语义质量保持验证边界 |
| Phase 1.5 | 已完成 / 正式关闭 | Workflow / Governance / Reliability / Circuit Breaker 基础能力 |
| Phase 1.6 | 已完成 / 正式关闭 | Trigger / Frontend / Browser 历史范围 |
| Phase 1.7 | 已完成 / 正式关闭 | Scheduled Trigger / Governance / Browser E2E |
| Phase 1.8 | 已完成 / 正式关闭 | Event / Webhook Trigger Expansion |
| **Phase 1.9** | **已完成 / 正式关闭** | Runtime Reliability / Production Hardening 全部 Acceptance Gate 通过 |
| **Phase 2.1** | **进行中** | Enterprise Organization & Access Governance；2.1-A～2.1-E、2.1-F-A/F-B 已完成；当前进入 F-C Acceptance |
| Phase 2.2～2.8 | 路线候选 | Retrieval Quality、Model Governance、Durable Scheduler、Advanced Workflow、Event Infrastructure、Multi-Agent、Agent Marketplace |

## 4. Phase 2.1 当前任务

### 2.1-A Product / Backend Contract — 已完成

已冻结 Organization / Membership / Owner/Admin/Member、迁移兼容、API、Resource Scope 与 Audit 规则。

### 2.1-B Database Migration + Domain — 已完成

已实现 Organization / OrganizationMembership model、Alembic `0023_organization_membership`、Tenant/User 兼容映射、OrganizationService、membership authorization、Owner transfer 与唯一 Owner 防护。

### 2.1-C API Contract Implementation — 已完成 Gate

Organization CRUD、Membership lifecycle、Owner transfer、management authorization、suspended Organization recovery、AuditLog 与 API Contract / Real API 基线已验证。

### 2.1-D Organization / Membership Frontend — 已完成 Gate

Organization list/detail、成员管理、role/status、suspend/recovery、Owner Transfer 与 frontend contract tests 已完成。

### 2.1-E Real API / Regression — **已完成 Gate**

```text
Backend regression: 275 passed, 30 deselected
Full Real API: 30 passed
```

### 2.1-F-A Browser E2E 基础设施 — **已完成 Gate**

保持现有 Playwright Desktop Chrome、`FRONTEND_BASE_URL`、`API_BASE_URL` 约定，使用：

```text
frontend/tests/e2e/organization-management.spec.ts
frontend/scripts/test/e2e/02_run_organization_e2e.ps1
```

### 2.1-F-B Organization Management E2E — **已完成 Gate**

当前覆盖并已由真实浏览器执行通过：

- Login → Organization list。
- 创建 Organization。
- Organization Detail。
- 添加成员。
- member → admin。
- member active/suspended/recovery。
- Organization suspend/recovery。
- Owner Transfer。
- 真实 API 校验单 Owner 不变量与目标 Owner 状态。

### 2.1-F-C Governance Browser Acceptance — **已实现，待 Gate**

已补充实现：

- 登录响应持久化 `user_id`，前端根据当前 Organization membership role 决定管理 UI 是否可见。
- Member 不显示 Organization 管理、成员编辑、Owner Transfer 控件。
- Owner Transfer 仅当前 Owner 显示，Transfer 后原 Owner 降级为 Admin，不再显示 Owner Transfer；新 Owner 显示。
- Browser E2E 新增 Member 权限边界与 suspended member 阻断场景。
- Browser E2E 新增 Owner Transfer 后原 Owner / 新 Owner 浏览器权限边界场景。
- 现有 Organization owner E2E 增加 Audit UI `organization.owner.transferred` 可追踪证据。

当前这些新增 F-C 场景尚未由用户本地实际执行，因此 **F-C 不得标记 Passed**。

## 5. 下一步推进原则

```text
2.1-E Real API Gate 已通过
 → 2.1-F-A E2E infrastructure 已通过
 → 2.1-F-B Organization management browser contract 已通过
 → 实现 F-C governance browser acceptance
 → 本地执行新增 F-C Browser E2E
 → 若失败，按实际失败栈修复并记录 docs/04-errors
 → 修复后重新执行 Browser E2E
 → Full Frontend Regression + production build
 → Backend regression + Real API Gate
 → 更新 Status / Acceptance
 → 最终关闭 Phase 2.1
```

未实际执行的测试不得标记为 Passed。

## 6. 维护规则

后续任何功能完成、延期、阻塞、范围变化或新的工程错误，都必须同步：

- `docs/PROJECT_STATUS.md`
- 对应 `docs/02-phases/PHASE_x_y.md`
- 对应 `docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md`
- 已分析完成的工程错误同步 `docs/04-errors/`
