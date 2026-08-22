# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前远端基线：`6d6a208b7dac4811db53f42ecdbbe6f496fafd83`
- 开发原则：所有任务直接基于最新 `main`，禁止 feature / task / 临时分支。
- 当前开发阶段：**Phase 1.9 已完成 / 正式关闭；新 Phase 尚未立项。**
- 产品能力基线：`docs/PRODUCT_CAPABILITY_BASELINE.md`
- 产品与功能开发对比矩阵：`docs/PRODUCT_DEVELOPMENT_MATRIX.md`

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

AuditLog focused regression：`2 passed / 0 failed`。

### Browser E2E

```text
Desktop Chrome:
3 passed in 10.5s
[PASS] Browser E2E gate completed.
```

覆盖 Scheduled Trigger、Webhook Trigger、Webhook duplicate-event convergence 与 lifecycle security。

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
| 新 Phase | **尚未立项** | 必须先完成产品需求、架构基线与范围决策，不得自行假定 Phase 2 |

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

详细能力、验收级别、产品边界和差距见：

- `docs/PRODUCT_CAPABILITY_BASELINE.md`
- `docs/PRODUCT_DEVELOPMENT_MATRIX.md`

## 6. 当前已确认的产品 / 工程差距

以下内容是基于现有 Phase 文档确认的能力边界，不自动等同下一阶段任务：

1. 真实 Embedding Provider 语义质量仍需按实际 Provider 场景验证；Phase 1.4 的 Mock 只证明工程链路。
2. Scheduler 当前没有 `next_run_at`、lease、misfire policy、独立 scheduler state。
3. Workflow 当前没有复杂 DAG、Saga、复杂 Policy DSL 或完整 Workflow Designer。
4. 当前没有通用 MQ/Kafka/Event Bus，也没有分布式 Workflow Engine。
5. Multi-Agent orchestration 尚未形成当前 Product Contract。
6. 当前 Auth/RBAC/Tenant 不等同完整 Enterprise IAM / Organization 产品。

这些能力必须先有明确产品需求与架构决策，才能进入新的 Phase。

## 7. 文档基线一致性修复

本轮重新评估发现根 `README.md` 仍保留“当前推进 Phase 1.7”的历史描述，而 `PROJECT_STATUS.md` 已关闭 Phase 1.9。该文档漂移已修正，并新增：

- `docs/PRODUCT_CAPABILITY_BASELINE.md`
- `docs/PRODUCT_DEVELOPMENT_MATRIX.md`

后续产品状态以本文件为准，产品能力以能力基线与开发矩阵为准。

## 8. 下一步推进原则

### 阶段 0：需求与产品基线决策（当前）

暂不创建新的 Phase。先从产品真实使用场景确认：

- 当前平台服务的首要企业用户角色；
- 核心业务场景与关键 KPI；
- 当前能力无法满足的业务需求；
- 上述 G-03～G-06 哪些真正具有产品优先级。

### 阶段 1：形成正式新 Phase

只有需求确认后才创建：

```text
`docs/02-phases/PHASE_x_y.md`
`docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md`
```

并在本文件登记 Phase、范围、完成定义和当前任务。

### 阶段 2：按开发准则拆解

```text
需求 / 架构 Contract
 → Backend Domain + API Contract
 → Migration + Backend Tests
 → Frontend API Types + Vitest
 → Frontend UI
 → Real API
 → Backend Gate
 → Frontend Gate
 → Browser E2E
 → Acceptance / Status / Error Record
 → 直接提交 main
```

不涉及数据库、Frontend 或 Browser 的任务可以裁剪对应步骤，但必须明确裁剪理由和验收边界。

## 9. 维护规则

后续任何功能完成、延期、阻塞、范围变化或新的工程错误，都必须同步：

- `docs/PROJECT_STATUS.md`
- 对应 `docs/02-phases/PHASE_x_y.md`
- 对应 `docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md`
- 已分析完成的工程错误写入 `docs/04-errors/`

不得通过聊天、Issue 或 Commit 信息单独作为项目状态记录。
