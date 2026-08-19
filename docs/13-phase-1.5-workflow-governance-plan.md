# Phase 1.5：Workflow / Governance 开发基线与执行计划

> 本文是 Phase 1.5 的阶段开发基线。固定开发顺序以 `docs/DEVELOPMENT.md` 为唯一工程执行准则。本阶段仍以开发者本地手动测试、`uv run`、`npm` 为质量门禁，不以 GitHub Actions workflow 作为开发测试或验收依据。

## 1. 阶段目标

Phase 1.5 不直接追求一次性实现完整 Workflow Engine，而是先建立与现有 Agent Runtime、RBAC、Tool Runtime、Observability 解耦的 Workflow / Governance 领域边界，并形成可逐项验收的基础闭环。

本阶段第一轮遵循“先 Contract、后执行引擎”的原则：

```text
Workflow Definition
    ↓
Workflow Version
    ↓
Lifecycle / Publish Governance
    ↓
Tenant Contract
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
- Workflow Tenant scope

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
- Tenant isolation contract
- Audit 事件要求
- Runtime 执行必须可追溯的治理约束
- 配置与策略变更的可审计边界

## 3. Phase 1.5 任务拆解

| ID | 任务 | 目标 | 状态 |
|---|---|---|---|
| 1.5-A | Workflow Definition Contract | 建立 Workflow 定义、版本、生命周期与 RBAC/API contract | **Backend 验收通过** |
| 1.5-B | Workflow Version / Publish Governance | 发布版本、不可变版本、发布审计与 Tenant contract | **本地 Backend 验收通过** |
| 1.5-C | Workflow Execution State Machine | 建立 execution / node state contract 与持久化 | **Backend Contract 开发中，等待本地验收** |
| 1.5-D | Workflow Runtime Integration | Workflow → Agent Runtime / Tool Runtime 执行链路 | 待 1.5-C 验收 |
| 1.5-E | Governance / Audit / Trace | 发布、执行、失败、变更的治理闭环 | 待 1.5-D 验收 |
| 1.5-F | Vue Workflow / Governance 管理端 | API types、列表、版本、发布、执行状态与审计展示 | 后端契约稳定后推进 |

## 4. 1.5-B Tenant Contract

Tenant contract 已完成 Backend 第一轮边界并通过开发者本地手工验收：

1. `Tenant` domain 与 `tenants` 表。
2. `User.tenant_id` 为非空 Tenant FK。
3. `Workflow.tenant_id` 为非空 Tenant FK。
4. 历史用户 / Workflow 迁移到稳定 Default Tenant。
5. JWT access token 增加 `tenant_id` claim。
6. 登录 / 注册返回用户所属 `tenant_id`。
7. Workflow Registry 查询带 `tenant_id` scope。
8. Admin 仅当前 Tenant 内跨 Owner 查询。
9. Workflow API 不接受客户端提交 `tenant_id`。
10. 缺少有效 `tenant_id` 的 Token 不允许进入 Tenant-scoped Workflow API。

## 5. 生命周期 / Publish Governance

当前生命周期：

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

发布版本不可变；修改已发布定义必须创建新版本。当前 Published Version 通过 `Workflow.published_version_id` 明确记录。

## 6. API Contract

Registry / Version API：

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

Phase 1.5-C Execution Contract：

```text
POST /api/v1/workflows/{workflow_id}/executions
GET  /api/v1/workflows/executions/{execution_id}
GET  /api/v1/workflows/executions/{execution_id}/nodes
POST /api/v1/workflows/executions/{execution_id}/transition
POST /api/v1/workflows/executions/{execution_id}/nodes/transition
```

Execution 只能从当前已发布 Workflow Version 创建；Tenant scope 必须来自认证上下文，客户端不能指定 Tenant。

## 7. Phase 1.5-C State Contract

Execution 状态：

```text
pending → running → completed
                    ↘ failed
                    ↘ cancelled
pending → cancelled
```

Node Execution 状态：

```text
pending → running → completed
                    ↘ failed
                    ↘ skipped
pending → skipped
```

终态不得再次转换。Execution / Node Execution 均持久化，Execution 保存当前节点、输入输出、错误信息及开始/结束时间；Node Execution 保存节点状态、attempt、输入输出和错误信息。

本阶段明确不实现真实 Agent / Tool 执行，不绑定 Temporal、MQ、Worker 或具体 DAG 引擎。

## 8. Backend 测试范围

严格遵循 Backend Contract → Migration + pytest：

### 1.5-B

- Publish 状态机与幂等性
- Tenant domain / FK
- JWT tenant claim
- Workflow tenant scope
- Full backend regression

### 1.5-C

- Execution 状态合法转换
- Execution 终态保护
- Node 状态合法转换
- Execution / Node migration contract
- Execution API route contract
- 已发布版本执行入口约束
- Tenant-scoped Execution 查询
- Full backend regression

独立手工脚本：

```text
backend/scripts/run_phase_1_5_b_workflow_publish_governance_validation.ps1
backend/scripts/run_phase_1_5_b_tenant_contract_validation.ps1
backend/scripts/run_phase_1_5_c_workflow_execution_validation.ps1
```

所有脚本只执行 **Backend** 场景，不混入 Frontend 测试。Frontend 测试必须独立通过 `npm test` / `npm run build`。

## 9. 后续固定推进顺序

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

## 10. 本阶段暂不实现

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

## 11. 验收门禁

1. Backend pytest 通过且无新增 warnings。
2. Alembic upgrade head 成功。
3. API Scenario 通过。
4. RBAC owner isolation 与 Tenant isolation 通过。
5. Frontend API types / Vitest / build 在进入 UI 后通过。
6. 前后端实际联调通过。
7. 验收文档记录真实执行结果，不预填“通过”。
8. 完成后直接提交 `main`。

## 12. 当前任务状态

**Phase 1.5-A 已完成；Phase 1.5-B Publish Governance 与 Tenant Contract 已通过开发者本地手工验收；当前进入 Phase 1.5-C Workflow Execution State Machine Backend Contract。**

责任角色：开发执行

开始时间：2026-08-19

当前目标：完成 1.5-C Backend Domain、Migration、pytest、API Scenario 与本地手工验收后，再进入 1.5-D Runtime Integration。
