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

不负责：

- 替代 Runtime 执行器
- 替代 RBAC 基础实现
- 替代 Observability 数据采集基础设施

## 3. Phase 1.5 任务拆解

| ID | 任务 | 目标 | 状态 |
|---|---|---|---|
| 1.5-A | Workflow Definition Contract | 建立 Workflow 定义、版本、生命周期与 RBAC/API contract | **Backend 验收通过** |
| 1.5-B | Workflow Version / Publish Governance | 发布版本、不可变版本、发布审计与 Tenant contract | **Publish Governance 已验收；Tenant contract 已落地，等待本地 Backend 验收** |
| 1.5-C | Workflow Execution State Machine | 建立 execution / node state contract 与持久化 | 待 1.5-B 完整验收 |
| 1.5-D | Workflow Runtime Integration | Workflow → Agent Runtime / Tool Runtime 执行链路 | 待 1.5-C 验收 |
| 1.5-E | Governance / Audit / Trace | 发布、执行、失败、变更的治理闭环 | 待 1.5-D 验收 |
| 1.5-F | Vue Workflow / Governance 管理端 | API types、列表、版本、发布、执行状态与审计展示 | 后端契约稳定后推进 |

## 4. 1.5-B Tenant Contract

Tenant contract 已建立 Backend 第一轮边界：

1. 新增 `Tenant` domain 与 `tenants` 表。
2. `User.tenant_id` 为非空 Tenant FK。
3. `Workflow.tenant_id` 为非空 Tenant FK。
4. 现有历史用户 / Workflow 迁移到稳定的 Default Tenant，避免升级过程中出现空 Tenant。
5. JWT access token 增加 `tenant_id` claim。
6. 登录返回 `tenant_id`，注册返回用户所属 `tenant_id`。
7. Workflow Registry 所有查询必须带 `tenant_id` scope。
8. Admin 仅获得当前 Tenant 内跨 Owner 查询能力，不获得跨 Tenant 能力。
9. Workflow API 不接受客户端提交的 `tenant_id`，Tenant 必须来自认证上下文。
10. 缺少有效 `tenant_id` 的 Token 不允许进入 Tenant-scoped Workflow API。

当前 Tenant contract 只解决 Identity → Workflow 的租户边界，不扩展 Agent / Knowledge / Tool / Runtime 全域 Tenant migration；这些领域必须在各自契约稳定后按相同原则逐步纳入。

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

发布版本不可变；修改已发布定义必须创建新版本。

当前 Published Version 通过 `Workflow.published_version_id` 明确记录。发布新版本时旧 Published Version 转为 `deprecated`；重复发布当前活动版本保持幂等且不重复写 Publish AuditLog。

## 6. API Contract

第一轮 Registry / Version API：

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

Workflow response 包含 `tenant_id` 与 `published_version_id`；客户端不能指定 Tenant scope。

## 7. Backend 测试范围

严格遵循：Backend Contract → Migration + pytest。

1.5-B 包含：

- Publish 设置 active version
- Publish 幂等性
- Publish 新版本时旧版本 Deprecated
- Archived version 禁止 Publish
- Workflow / Version mismatch protection
- API authentication contract
- Access token tenant claim
- Tenant domain / FK contract
- Workflow tenant scope contract
- Full backend regression

独立手工脚本：

```text
backend/scripts/run_phase_1_5_b_workflow_publish_governance_validation.ps1
backend/scripts/run_phase_1_5_b_tenant_contract_validation.ps1
```

脚本只执行 **Backend** 场景，不混入 Frontend 测试。Frontend 测试必须独立通过 `npm test` / `npm run build` 执行。

## 8. 后续固定推进顺序

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

## 9. 本阶段暂不实现

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

## 10. 验收门禁

1. Backend pytest 通过且无新增 warnings。
2. Alembic upgrade head 成功。
3. API Scenario 通过。
4. RBAC owner isolation 场景通过；Tenant isolation 只有在 Tenant contract 本地验收后才能标记完成。
5. Frontend API types / Vitest / build 在进入 UI 后通过。
6. 前后端实际联调通过。
7. 验收文档记录真实执行结果，不预填“通过”。
8. 完成后直接提交 `main`。

## 11. 当前任务状态

**Phase 1.5-A 已完成；Phase 1.5-B Publish Governance 已通过开发者本地手工验收；Tenant contract Backend 已落地，等待开发者本地验收。**

责任角色：开发执行

开始时间：2026-08-19

当前目标：完成 1.5-B Tenant contract 的 Backend Domain、Migration、pytest 与本地手工验收后，再进入 1.5-C。

下一阶段：1.5-C Workflow Execution State Machine
