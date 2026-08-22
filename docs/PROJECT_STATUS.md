# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 最新产品基线：Phase 2.1-E Real API Gate 已通过；当前进入 Phase 2.1-F Browser E2E + Acceptance。
- 开发原则：所有任务直接基于最新 `main`，禁止把临时分支作为长期开发基线。
- 当前开发阶段：**Phase 1.9 已完成 / 正式关闭；Phase 2.1 进行中；2.1-A/2.1-B/2.1-C/2.1-D/2.1-E 已完成对应 Gate；2.1-F-A / 2.1-F-B 已实现，待本地 Browser E2E Gate。**
- 产品能力基线：`docs/PRODUCT_CAPABILITY_BASELINE.md`
- 产品与功能开发对比矩阵：`docs/PRODUCT_DEVELOPMENT_MATRIX.md`
- 产品整体路线：`docs/PRODUCT_ROADMAP.md`

## 2. Phase 1.9 最终状态

| 能力 | 状态 |
|---|---|
| Workflow Runtime Reliability | 1.9-C 专项验证通过 |
| Retry / Timeout / Idempotency / Deadline | 1.9-C Real API 验证通过 |
| Circuit Breaker | 1.9-C Real API 验证通过 |
| Scheduled Trigger | 1.9-D Browser E2E 复验通过 |
| Webhook Trigger | 1.9-D Browser E2E 复验通过 |
| Frontend Governance UI | 1.9-D Frontend Regression / Build 通过 |
| Browser E2E | 1.9-D 独立 Gate 通过 |
| Phase 1.9 Final Acceptance | **正式关闭** |

## 3. Phase 2.1 Gate 证据

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

此前 `/runtime/audit-logs` PostgreSQL UUID/VARCHAR 类型错误与固定 Organization 名称冲突已修复；直接运行 Organization Real API 测试而未先准备 context 所产生的 7 个 `fixture context is missing` 不计为产品 Gate 失败。

## 4. Phase 状态

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
| **Phase 2.1** | **进行中** | Enterprise Organization & Access Governance；2.1-A～2.1-E 已完成；2.1-F-A / F-B 已实现，待 Browser E2E Gate |
| Phase 2.2～2.8 | 路线候选 | Retrieval Quality、Model Governance、Durable Scheduler、Advanced Workflow、Event Infrastructure、Multi-Agent、Agent Marketplace |

## 5. 当前产品能力评估

当前产品链路：

```text
Identity / RBAC
      ↓
Agent / Session / Runtime
      ↓
Model Gateway / Tool Runtime / Memory / Observability
      ↓
Knowledge / RAG / Retrieval
      ↓
Workflow / Governance
      ↓
Manual / Scheduled / Webhook Trigger
      ↓
Runtime Reliability / Audit / Trace
      ↓
Vue Management + Browser E2E
      ↓
Organization / Membership / Access Governance
```

Phase 2.1 正在把现有 Tenant/RBAC 基础能力提升为企业 Organization / Membership / Access Governance 产品能力。

## 6. Phase 2.1 当前任务

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

### 2.1-F-A Browser E2E 基础设施 — **已实现，待 Gate**

保持现有 Playwright Desktop Chrome、`FRONTEND_BASE_URL`、`API_BASE_URL` 约定，新增：

```text
frontend/tests/e2e/organization-management.spec.ts
frontend/scripts/test/e2e/02_run_organization_e2e.ps1
```

测试数据采用随机用户名、密码、Organization 名称，真实 API provisioning 后由浏览器完成 Login 与 UI 操作。

### 2.1-F-B Organization Management E2E — **已实现，待 Gate**

当前覆盖：

- Login → Organization list。
- 创建 Organization。
- Organization Detail。
- 添加成员。
- member → admin。
- member active/suspended/recovery。
- Organization suspend/recovery。
- Owner Transfer。
- 真实 API 校验单 Owner 不变量与目标 Owner 状态。

尚未由开发者本地执行，因此不能标记 Passed。

## 7. 下一步推进原则

严格遵守项目开发准则：

```text
2.1-E Real API Gate 已通过
 → 2.1-F-A E2E infrastructure
 → 2.1-F-B Organization management browser contract
 → 本地执行 targeted Browser E2E
 → 若失败，按实际失败栈修复
 → 若通过，再执行 Full Frontend Regression + Browser Acceptance
 → 补齐 Member boundary / Suspended member / Audit evidence
 → 更新 Status / Acceptance / Error Record
 → 最终关闭 Phase 2.1
```

未实际执行的测试不得标记为 Passed。

## 8. 维护规则

后续任何功能完成、延期、阻塞、范围变化或新的工程错误，都必须同步：

- `docs/PROJECT_STATUS.md`
- 对应 `docs/02-phases/PHASE_x_y.md`
- 对应 `docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md`
- 已分析完成的工程错误写入 `docs/04-errors/`
