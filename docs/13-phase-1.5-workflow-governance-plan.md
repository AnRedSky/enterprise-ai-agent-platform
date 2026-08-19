# Phase 1.5：Workflow / Governance 开发基线与执行计划

> 本文是 Phase 1.5 的阶段开发基线。所有开发直接提交 `main`，不创建新的长期功能分支。固定开发顺序以 `docs/DEVELOPMENT.md` 为唯一工程执行准则。本阶段仍以开发者本地手动测试、`uv run`、`npm` 为质量门禁，不以 GitHub Actions workflow 作为开发测试或验收依据。

## 1. 阶段目标

Phase 1.5 不直接追求一次性实现完整 Workflow Engine，而是先建立与现有 Agent Runtime、RBAC、Tool Runtime、Observability 解耦的 Workflow / Governance 领域边界，并形成可逐项验收的基础闭环。

架构文档明确 Workflow 与 Governance 属于平台核心领域；Agent Runtime 应通过 Workflow Engine / State Machine 进行流程编排，Governance 负责审计、版本、发布与配置治理。

本阶段第一轮遵循“先 Contract、后执行引擎”的原则：

```text
Workflow Definition
    ↓
Workflow Version
    ↓
Lifecycle / Publish Governance
    ↓
Workflow Execution State Machine
    ↓
Runtime Integration
    ↓
Governance / Audit / Trace
```

## 2. 领域边界

### Workflow

负责：

- Workflow 定义
- Workflow Version
- Workflow 节点与边关系的 provider-neutral 定义
- Workflow 生命周期
- Workflow 发布版本选择
- Workflow 执行状态模型
- 与 Agent Runtime 的执行入口契约

不负责：

- 具体 LLM Provider 调用
- Tool Registry / Tool Permission 实现
- Knowledge / RAG 检索实现
- 用户、角色、权限基础设施本身
- Trace / Audit 底层存储实现

### Governance

负责：

- Workflow / Agent 可发布状态约束
- Version / Publish 记录
- RBAC scope 检查
- Audit 事件要求
- Runtime 执行必须可追溯的治理约束
- 配置与策略变更的可审计边界

不负责：

- 替代 Runtime 执行器
- 替代 RBAC 基础实现
- 替代 Observability 数据采集基础设施

## 3. Phase 1.5 任务拆解

| ID | 任务 | 目标 | 状态 |
|---|---|---|---|
| 1.5-A | Workflow Definition Contract | 建立 Workflow 定义、版本、生命周期与 RBAC/API contract | **Backend 验收通过** |
| 1.5-B | Workflow Version / Publish Governance | 发布版本、不可变版本与发布审计；补齐 Tenant contract | **执行中：Publish Governance 已落地，等待本地 Backend 验收；Tenant contract 后续补齐** |
| 1.5-C | Workflow Execution State Machine | 建立 execution / node state contract 与持久化 | 待 1.5-B 验收 |
| 1.5-D | Workflow Runtime Integration | Workflow → Agent Runtime / Tool Runtime 执行链路 | 待 1.5-C 验收 |
| 1.5-E | Governance / Audit / Trace | 发布、执行、失败、变更的治理闭环 | 待 1.5-D 验收 |
| 1.5-F | Vue Workflow / Governance 管理端 | API types、列表、版本、发布、执行状态与审计展示 | 后端契约稳定后推进 |

## 4. 第一项可独立验收任务：1.5-A

### 4.1 Backend Domain Contract

已建立 `Workflow` / `WorkflowVersion` provider-neutral domain。

当前仓库已有 Identity/RBAC，但 JWT 与 User 模型尚未建立独立 Tenant domain / `tenant_id` claim。因此 **1.5-A 不虚构 tenant 来源**：该任务已完成现有可验证的 `owner_id + admin` scope；Tenant isolation 作为 1.5-B 的治理补齐项，在 Tenant contract 建立后再纳入 Workflow 数据模型。不得用 `owner_id` 冒充 tenant。

### 4.2 生命周期

第一轮只允许明确、可审计的状态迁移：

```text
Draft
  ↓
Testing
  ↓
Published
  ↓
Deprecated
  ↓
Archived
```

发布版本必须不可变；修改已发布定义必须创建新版本，不允许直接覆盖生产版本。

### 4.3 API Contract

第一轮 Registry / Version API 已建立：

```text
GET    /api/v1/workflows
POST   /api/v1/workflows
GET    /api/v1/workflows/{workflow_id}
PATCH  /api/v1/workflows/{workflow_id}
DELETE /api/v1/workflows/{workflow_id}
GET    /api/v1/workflows/{workflow_id}/versions
POST   /api/v1/workflows/{workflow_id}/versions
GET    /api/v1/workflows/{workflow_id}/versions/{version_id}
POST   /api/v1/workflows/{workflow_id}/versions/{version_id}/publish
```

1.5-B 在既有 API 上补充 `published_version_id` 返回字段，并允许经过治理校验的版本切换；重复发布当前活动版本保持幂等，不重复写入 Publish AuditLog。

### 4.4 RBAC / Governance Contract

已验证并持续维护：

1. Owner 可以读取和管理自己的 Workflow。
2. 非 Owner 无法越权读取、修改、删除或创建其 Workflow Version。
3. Admin 可以跨 Owner 查询，但不能绕过发布状态约束。
4. Published Version 不允许原地修改。
5. Publish 操作必须产生可审计事件。
6. 当前活动 Published Version 通过 `Workflow.published_version_id` 明确记录。
7. 发布新版本时，旧活动版本转为 `deprecated`。
8. 重复发布当前活动版本为幂等操作，不产生重复 AuditLog。
9. Tenant isolation 仍未宣称完成；必须等待 Identity Tenant contract 后实施。

## 5. 数据模型 / Migration 原则

第一轮已完成数据库设计与 `0013_workflow_definition`。1.5-B 新增 `0014_workflow_publish_governance`：

- `workflows.published_version_id`
- Workflow → active published WorkflowVersion 关联
- FK `ON DELETE SET NULL`
- 索引
- PostgreSQL / Alembic contract
- 时间字段继续使用 timezone-aware UTC 生成策略
- 不使用 SQLAlchemy Declarative API 保留字段名 `metadata`

## 6. Backend 测试范围

严格遵循：Backend Contract → Migration + pytest。

1.5-B 新增：

- Publish 设置 active version
- Publish 幂等性
- Publish 新版本时旧版本 Deprecated
- Archived version 禁止 Publish
- Workflow / Version mismatch protection
- API authentication contract
- Full backend regression

独立手工脚本：

```text
backend/scripts/run_phase_1_5_b_workflow_publish_governance_validation.ps1
```

脚本只执行 **Backend** 场景，不混入 Frontend 测试。Frontend 测试必须独立通过 `npm test` / `npm run build` 执行。

## 7. 后续固定推进顺序

每个 Phase 1.5 小版本严格执行：

```text
① Backend Domain + API Contract
        ↓
② Database Migration + Backend pytest
        ↓
③ Frontend API Types + Vitest
        ↓
④ Frontend UI
        ↓
⑤ Backend API Scenario / 手工验收
        ↓
⑥ 前后端联调
        ↓
⑦ Runtime Integration（需要时）
        ↓
⑧ Backend pytest + Frontend npm test + npm run build
        ↓
⑨ 更新开发 / 验收文档
        ↓
⑩ 提交 main
```

## 8. 本阶段暂不实现

第一轮明确不做：

- Temporal 等具体 Workflow Engine 强绑定
- MQ / Worker 分布式编排
- DAG 高级调度优化
- 多 Agent 协作策略
- 自动补偿 / Saga
- Cron / Event Trigger 全套能力
- 复杂 Policy DSL
- 生产级审批中心
- Workflow 可视化拖拽编辑器

这些能力必须在基础 Contract 与 State Machine 稳定后逐步加入，避免过早绑定具体实现。

## 9. 验收门禁

1. Backend pytest 通过且无新增 warnings。
2. Alembic upgrade head 成功。
3. API Scenario 通过。
4. RBAC owner isolation 场景通过；Tenant isolation 只有在 Tenant contract 建立后才能作为已完成门禁。
5. Frontend API types / Vitest / build 在进入 UI 后通过。
6. 前后端实际联调通过。
7. 验收文档记录真实执行结果，不预填“通过”。
8. 完成后直接提交 `main`。

## 10. 当前任务状态

**Phase 1.5-A 已完成本地 Backend 手工验收；Phase 1.5-B Workflow Version / Publish Governance 执行中。**

责任角色：开发执行

开始时间：2026-08-19

当前目标：完成 1.5-B Publish Governance + Tenant contract 的 Backend Domain、Migration、pytest 与本地手工验收后，再进入 1.5-C。

当前阻塞项：Identity Tenant contract 尚未建立。1.5-B Publish Governance 不依赖 Tenant，可先独立验收；Tenant isolation 不得提前宣称完成。

下一阶段：1.5-C Workflow Execution State Machine
