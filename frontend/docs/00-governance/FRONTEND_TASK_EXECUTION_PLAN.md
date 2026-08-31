# 前端长期任务执行计划

> 本文件是前端持续开发的任务执行台账，不替代项目阶段文档。状态必须基于远端 `main`、当前前端代码和本地实际测试结果更新。

## 1. 当前基线

- 最新远端 `main`：`ac90bd2e86f76f9100e67d948e3cbde261527b61`（2026-08-31，worker/scheduler diagnostics UI）。
- 当前 `frontend` 与最新 `main` 已处于同一提交，无需产生空合并提交；本轮开发继续只消费已经稳定的后端 Contract，不提前实现尚未完成 Acceptance 的后端能力。
- 前端开发准则明确要求：后端稳定能力是正式前端实现的唯一前置条件，开发顺序固定为 Backend Contract / Tests / Acceptance → Frontend API Types → View / Component → Vitest → Real API / E2E。
- 本轮选择已稳定的 Organization / Membership Contract 继续前端化，不进入最新 Runtime Operations / Scheduler 后端主线。

## 2. 本轮交付：Organization 成员管理体验增强

状态：**进行中**。

### 实现范围

1. 复用现有 `/organizations/{organization_id}/members` 分页 Contract，不新增 API client。
2. 成员列表使用固定 `page_size=20`，页码通过 `offset=(page-1)*20` 计算。
3. 成员总数使用后端 `total`，只有超过一页时显示分页控件。
4. 成员角色、状态、所有权转移、暂停/恢复、移除等既有生命周期操作保持原 Backend Contract。
5. 添加、编辑、删除、状态变更、所有权转移后保持当前页面上下文；删除导致当前页越界时自动回退到最后有效页。
6. 成员加载错误独立于组织详情错误，提供可恢复的用户提示，不展示原始异常。
7. 组织详情在 900px / 600px 以下增加响应式布局，操作区和分页在窄屏下保持可用。
8. 新增 targeted Vitest 覆盖分页参数、页码状态、既有成员生命周期和权限边界。

### Contract 对齐

前端继续调用：

```text
GET  /organizations/{organization_id}/members?offset={offset}&limit={limit}
POST /organizations/{organization_id}/members
PATCH /organizations/{organization_id}/members/{membership_id}
POST /organizations/{organization_id}/members/{membership_id}/transfer-owner
DELETE /organizations/{organization_id}/members/{membership_id}
```

列表响应继续使用：

```text
{
  "items": Membership[],
  "total": number
}
```

前端不复制后端 RBAC、tenant boundary 或所有权状态机，仅根据当前用户 membership 的真实角色/状态决定是否展示管理入口。

## 3. 长期任务队列

### P0：核心业务闭环

| ID | 领域 | 目标 | 状态 | 验收 |
|---|---|---|---|---|
| FE-P0-01 | Agent | 创建 → Version → Publish → Runtime → Trace/Audit 闭环 | 进行中 | View + API + Real 联调 |
| FE-P0-02 | Workflow | 编辑 → 校验 → 发布 → Execution → Trace | 进行中 | View + API + E2E |
| FE-P0-03 | Runtime | Execution → Event → Trace → Audit 统一详情链路 | 进行中 | View + API + E2E |
| FE-P0-04 | Knowledge | 知识资产 → 检索 → Agent 关联 → Runtime 验证 | 待实施 | View + API |
| FE-P0-05 | Tool | 工具配置 → Agent 关联 → Runtime 调用结果 | 待实施 | View + API |
| FE-P0-06 | Organization | 组织 → 成员 → 权限 → 资源边界 | 进行中 | View + API + E2E |
| FE-P0-07 | Model Provider | Provider/Model 配置与 Agent 使用关系 | 待实施 | View + API |
| FE-P0-08 | Audit | 跨领域操作证据查询与详情 | 进行中 | View + API + E2E |
| FE-P0-09 | Integration | Event → Delivery → Audit → Replay → Dead Letter | 待实施 | View + Real API |

### P1：稳定性与企业级体验

- FE-P1-01：统一 Loading / Empty / Error / Success / Permission 状态。
- FE-P1-02：统一错误分类与用户提示隔离。
- FE-P1-03：统一中文状态映射，未知值安全回退。
- FE-P1-04：清理 Element Plus 未解析组件警告（进行中）。
- FE-P1-05：统一公共模式，并完成核心页面渐进增强（进行中）。
- FE-P1-06：建立 1440 / 1280 / 1024 / 768 / 390 响应式验收矩阵。
- FE-P1-07：补充核心页面 Playwright 用户旅程。
- FE-P1-08：完成 Runtime / Agent / Workflow 深度交互与可观测性工作台。

### P2：后端稳定后再实施

- Provider Registry / Health；
- Alert Rule 与 firing/recovery 生命周期；
- Notification Routing / Provider fallback；
- Notification SLO / Route Metrics；
- Runtime Alert Scheduler 运维视图；
- Prometheus / OpenTelemetry 配置与观测状态。

## 4. 固定执行流程

```text
同步远端 main
    ↓
确认 Backend Contract / Tests / Acceptance
    ↓
检索现有 API / Types / View / Components / Tests / Docs
    ↓
确定最小业务切片
    ↓
API Types → View / Component → Vitest
    ↓
targeted test → npm test → npm run build → npm run test:gate
    ↓
必要时 Real API / Browser E2E
    ↓
同步 frontend/docs / 项目状态
    ↓
一个原子提交
```

## 5. 本轮验证状态

本轮代码通过 GitHub 远端源码审查完成实现提交；当前环境没有直接执行用户本地 Node/Vitest/build 的能力，因此不能将 targeted Vitest、全量 Vitest、build 或 test gate 记录为“通过”。

用户本地验收应按：

```powershell
cd frontend
npm test -- tests/views/OrganizationDetail.test.ts
npm test
npm run build
npm run test:gate
```

需要真实后端时，再执行项目既有 Real API / Browser E2E 流程。测试不得自动启动或停止后端服务，也不得依赖手工输入测试数据。

## 6. 完成定义

任务只有同时满足 Backend Contract、类型、用户链路、状态完整性、安全边界、targeted/full Vitest、build、test gate、必要 Real API/E2E、文档同步和原子提交等条件，才能标记 `已完成`。

没有实际执行证据不得写成“通过”。
