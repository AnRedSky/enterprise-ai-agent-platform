# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前远端基线：`0b9ea8014a585e6433c25f1747732c7343378759`
- 开发原则：所有任务直接基于最新 `main`，禁止 feature / task / 临时分支。
- 当前开发阶段：**Phase 1.9 已完成 / 正式关闭；Phase 2.1 进行中；2.1-A Contract 已完成；2.1-B Migration Gate 已由本地实际结果验证；2.1-C API Contract Implementation 进行中。**
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

## 3. Phase 1.9 最终本地 Gate 证据

历史证据保持原记录，不代表本轮重新执行：

### Backend

```text
uv run pytest -q
264 passed, 23 deselected in 4.80s
```

### Migration

```text
uv run alembic upgrade head
completed

uv run alembic current
0022_workflow_trigger (head)

uv run alembic heads
0022_workflow_trigger (head)
```

### Real API

```text
23 passed in 39.47s
[PASS] Real API gate completed.
```

### Frontend

```text
Frontend Vitest:
13 test files passed
52 tests passed

Frontend production build:
passed

Frontend Regression Gate:
[PASS]
```

### Browser E2E

```text
Desktop Chrome:
3 passed in 10.5s
[PASS] Browser E2E gate completed.
```

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
| **Phase 2.1** | **进行中** | Enterprise Organization & Access Governance；2.1-A 完成；2.1-B Migration Gate 已验证；2.1-C API Contract Implementation 进行中 |
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

## 6. 当前确认的产品 / 工程差距与路线

| 缺口 | 企业价值 | 路线 | 当前状态 |
|---|---|---|---|
| Organization / Membership / Enterprise Access | 让企业可以真正管理成员与资源边界 | Phase 2.1 | **P0 / 正在开发** |
| Retrieval 真实 Provider 质量 | 保证知识问答业务质量可量化 | Phase 2.2 | P0，待质量 Contract |
| Model Provider Governance | 控制模型选择、故障切换和成本 | Phase 2.3 | P1，待产品决策 |
| Durable Scheduler | 支撑长期任务、故障恢复和多实例语义 | Phase 2.4 | P1，待产品决策 |
| Advanced Workflow | 支撑复杂业务流程编排 | Phase 2.5 | P1，待执行语义决策 |
| Event Infrastructure | 支撑高吞吐异步业务集成 | Phase 2.6 | P2，仅需求成立后 |
| Multi-Agent | 支撑复杂任务的 Agent 协作 | Phase 2.7 | P2，尚无 Contract |
| Agent Asset / Marketplace | 企业内部复用、发布和治理 Agent 资产 | Phase 2.8 | P2，尚无 Contract |

## 7. Phase 2.1 当前任务

### 2.1-A Product / Backend Contract — 已完成

已冻结：

1. Organization ↔ Tenant 1:1 关系。
2. Membership 生命周期与多组织归属。
3. Owner/Admin/Member 权限矩阵。
4. User/Tenant/Role 兼容迁移策略。
5. API schema / error / pagination / idempotency Contract。
6. Resource scope 与 Audit 规则。

详细 Contract：`docs/02-phases/PHASE_2_1_A_CONTRACT.md`。

### 2.1-B Database Migration + Domain — Migration Gate 已验证

已实现并由用户本地 Migration 验证：

- SQLAlchemy `Organization` / `OrganizationMembership` model。
- Alembic `0023_organization_membership` migration。
- Existing Tenant/User 数据兼容映射。
- `OrganizationService`。
- active membership / management authorization 基础规则。
- Owner/Admin/Member role 约束。
- Owner transfer 事务锁定与唯一 Owner 防护。
- membership `(organization_id, user_id)` 数据库唯一约束。

用户本地实际结果：

```text
uv run alembic upgrade head
Running upgrade 0022_workflow_trigger -> 0023_organization_membership

uv run alembic heads
0023_organization_membership (head)
```

### 2.1-C API Contract Implementation — 进行中

本轮已提交：

- Organization API schema。
- Organization / Membership router。
- Organization CRUD。
- Membership list/create/update/remove。
- 显式 owner transfer mutation。
- active membership / management authorization。
- suspended Organization 的管理恢复路径。
- Organization / Membership AuditLog 写入。
- API Contract route/authentication tests。

**注意：本轮 API 代码提交后尚未由本地重新执行 Backend regression，因此不能标记 2.1-C Passed。**

### 2.1-D～2.1-F

暂不进入 Frontend；必须先完成 2.1-C Backend regression + API Contract + Real API 所需 Gate。

## 8. Phase 2.1 验收入口

- Phase：`docs/02-phases/PHASE_2_1.md`
- Contract：`docs/02-phases/PHASE_2_1_A_CONTRACT.md`
- Acceptance：`docs/03-acceptance/PHASE_2_1_ACCEPTANCE.md`
- Product Roadmap：`docs/PRODUCT_ROADMAP.md`

Phase 2.1 完成前不得声称 Organization / Enterprise IAM 已完整实现或验收通过。

## 9. 下一步推进原则

严格遵守 `docs/01-governance/DEVELOPMENT.md`：

```text
2.1-C API Contract Implementation
 → 本地 Backend regression
 → 修复实际失败
 → API Contract / Real API
 → 2.1-E Regression
 → 2.1-D Frontend Contract + UI
 → 2.1-F Browser E2E
 → Acceptance / Status / Error Record
 → 直接提交 main
```

不涉及某层时必须在 Phase 文档说明原因。所有开发、修复、文档与测试变更直接基于 `main`。

## 10. 维护规则

后续任何功能完成、延期、阻塞、范围变化或新的工程错误，都必须同步：

- `docs/PROJECT_STATUS.md`
- 对应 `docs/02-phases/PHASE_x_y.md`
- 对应 `docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md`
- 已分析完成的工程错误写入 `docs/04-errors/`

不得通过聊天、Issue 或 Commit 信息单独作为项目状态记录。
