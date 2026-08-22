# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前远端基线：Phase 2.1-D Frontend implementation commits on latest `main`。
- 开发原则：所有任务直接基于最新 `main`，禁止 feature / task / 临时分支。
- 当前开发阶段：**Phase 1.9 已完成 / 正式关闭；Phase 2.1 进行中；2.1-A Contract 已完成；2.1-B Migration Gate 已验证；2.1-C Backend API + Real API Gate 已由本地实际结果验证；2.1-D Organization / Membership Frontend UI + Contract Tests 已实现，等待本地 Frontend Regression / Build Gate。**
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

用户本地实际结果：

```text
uv run pytest -q
275 passed, 23 deselected in 5.02s

uv run pytest -q tests/api_contract/test_api_organization_endpoints.py
4 passed in 1.23s

uv run alembic heads
0023_organization_membership (head)
```

### Real API

```text
23 passed in 37.45s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

上述结果用于确认 2.1-C Backend/API 基线，不代表后续 Frontend 代码的本地 Gate 已执行。

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
| **Phase 2.1** | **进行中** | Enterprise Organization & Access Governance；2.1-A/2.1-B/2.1-C 已完成对应 Gate；2.1-D Frontend UI + Contract Tests 已实现，等待本地 Gate |
| Phase 2.2～2.8 | 路线候选 | Retrieval Quality、Model Governance、Durable Scheduler、Advanced Workflow、Event Infrastructure、Multi-Agent、Agent Marketplace |

## 5. 当前产品能力评估

当前第一阶段已经形成以下完整产品链路：

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
```

Phase 2.1 正在把现有 Tenant/RBAC 基础能力提升为企业 Organization / Membership / Access Governance 产品能力。

## 6. Phase 2.1 当前任务

### 2.1-A Product / Backend Contract — 已完成

已冻结 Organization / Membership / Owner/Admin/Member、迁移兼容、API、Resource Scope 与 Audit 规则。

### 2.1-B Database Migration + Domain — 已完成

已实现 Organization / OrganizationMembership model、Alembic `0023_organization_membership`、Tenant/User 兼容映射、OrganizationService、membership authorization、Owner transfer 与唯一 Owner 防护。

### 2.1-C API Contract Implementation — 已完成 Gate

已实现并由用户本地实际验证：

- Organization CRUD。
- Membership list/create/update/remove。
- 显式 owner transfer mutation。
- active membership / management authorization。
- suspended Organization 管理恢复路径。
- Organization / Membership AuditLog。
- API Contract tests。
- Real HTTP API gate。

### 2.1-D Organization / Membership Frontend — 实现完成，Gate 待执行

已提交：

- `frontend/src/api/organizations.ts`：完整 Organization / Membership API client。
- `frontend/src/views/organizations/index.vue`：Organization 列表、创建、状态展示。
- `frontend/src/views/organizations/detail.vue`：Organization 状态、成员列表、添加/编辑/暂停/恢复/移除成员、Owner Transfer。
- `frontend/src/router/index.ts`：Organization management routes。
- `frontend/tests/api/organizations.test.ts`：Frontend API Contract tests。
- `frontend/tests/views/Organizations.test.ts`：Organization list UI contract tests。
- `frontend/tests/views/OrganizationDetail.test.ts`：Membership lifecycle / Owner Transfer UI contract tests。

前端 UI 不将 Owner 通过普通 role update 暴露；所有高风险操作仍通过 Backend authorization 作为最终安全边界。

**注意：上述 Frontend 代码提交后尚未由本地重新执行 Frontend Regression / production build，因此不能标记 2.1-D Passed。**

### 2.1-E / 2.1-F

2.1-D Frontend Regression / Build 通过后，再执行 Real API + Browser E2E acceptance，随后决定 Phase 2.1 Final Acceptance。

## 7. 下一步推进原则

严格遵守 `docs/01-governance/DEVELOPMENT.md`：

```text
2.1-D Frontend Contract + UI
 → 本地 Frontend targeted tests
 → Frontend regression
 → production build
 → 修复实际失败
 → Real API / Browser E2E
 → Acceptance / Status / Error Record
 → 直接提交 main
```

未实际执行的测试不得标记为 Passed；所有开发、修复、文档与测试变更直接基于 `main`。

## 8. 维护规则

后续任何功能完成、延期、阻塞、范围变化或新的工程错误，都必须同步：

- `docs/PROJECT_STATUS.md`
- 对应 `docs/02-phases/PHASE_x_y.md`
- 对应 `docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md`
- 已分析完成的工程错误写入 `docs/04-errors/`

不得通过聊天、Issue 或 Commit 信息单独作为项目状态记录。
