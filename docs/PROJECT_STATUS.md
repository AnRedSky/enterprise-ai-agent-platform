# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前远端基线：Phase 2.1-D Frontend Gate 已验证；2.1-E Real API / Regression 正在修复 Gate 阻塞问题。
- 开发原则：所有任务直接基于最新 `main`，禁止 feature / task / 临时分支。
- 当前开发阶段：**Phase 1.9 已完成 / 正式关闭；Phase 2.1 进行中；2.1-A/2.1-B/2.1-C/2.1-D 已完成对应 Gate；2.1-E 已执行 Real API Gate，当前因 AuditLog 查询 PostgreSQL 类型错误失败，已修复并等待本地复验。**
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
275 passed, 23 deselected in 5.02s

uv run pytest -q tests/api_contract/test_api_organization_endpoints.py
4 passed in 1.23s

uv run alembic heads
0023_organization_membership (head)
```

### 2.1-C Real API

```text
23 passed in 37.45s
[PASS] Real API gate completed.
```

### 2.1-D Frontend

用户本地实际结果：

```text
Targeted organization tests
3 test files
15 passed

Frontend Regression
16 test files
67 passed

Production build
✓ built successfully
```

首次 production build 的 `DefaultRow` / `Membership` 类型错误已记录为 `ERR-0020` 并修复；修复后以上三个结果均由用户实际执行通过，因此 2.1-D Gate 已验证。

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
| **Phase 2.1** | **进行中** | Enterprise Organization & Access Governance；2.1-A/2.1-B/2.1-C/2.1-D 已完成；2.1-E Real API Gate 已执行但当前失败，正在修复 |
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

### 2.1-D Organization / Membership Frontend — 已完成 Gate

已提交：

- `frontend/src/api/organizations.ts`
- `frontend/src/views/organizations/index.vue`
- `frontend/src/views/organizations/detail.vue`
- `frontend/src/router/index.ts`
- `frontend/tests/api/organizations.test.ts`
- `frontend/tests/views/Organizations.test.ts`
- `frontend/tests/views/OrganizationDetail.test.ts`

实际结果：15 个定向测试通过、完整 Frontend Regression 67 个测试通过、production build 通过。

### 2.1-E Real API / Regression — **Gate 已执行但失败，修复后待复验**

当前用户实际执行结果：

```text
10 failed, 20 passed in 41.32s
```

主要失败集中在 `/runtime/audit-logs` 返回 500，导致 Organization audit 与既有 Workflow governance 的多个 Real API 场景同时失败；另有 transferred-owner 场景使用固定组织名称导致 409。

根因与修复已记录：`docs/04-errors/ERR-0021-real-api-audit-resource-id-type-mismatch.md`。

已直接提交 main 的修复：

- `RuntimeQueryService.audit_logs()` 将 Organization / Membership UUID scope 子查询显式 cast 为 String，以匹配 `audit_logs.resource_id` 的 VARCHAR 存储类型。
- transferred-owner Real API 测试改为每次使用唯一 Organization 名称，消除跨次真实数据库状态造成的固定名称冲突。

**当前不能标记 2.1-E Passed。下一步不是进入 2.1-F，而是重新执行 Real API Gate；只有 2.1-E 全部通过后才能进入 Browser E2E。**

## 7. 下一步推进原则

严格遵守 `docs/01-governance/DEVELOPMENT.md`：

```text
2.1-E Gate 已发现真实失败
 → 修复 AuditLog PostgreSQL 类型边界
 → 修复 Real API fixture 的固定名称冲突
 → 本地执行 targeted + full backend + Real API Gate
 → 根据实际结果继续修复
 → Real API 全部通过后进入 Browser E2E
 → 更新 Status / Acceptance / Error Record
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
