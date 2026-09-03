# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`。`main` 当前基线为 `af306fdb694ec92cf81ec28891996d50fe071f3a`，`frontend` 已将该最新 `main` 纳入当前历史。

本轮未修改后端业务 Contract；frontend 继续消费已确认的正式 API 类型与 Durable Facts。

## 2. 用户最新本地 targeted regression 反馈

用户在 Windows `frontend` 工作树执行 targeted 命令，反馈结果：

```text
Test Files  1 failed | 7 passed (8)
Tests       1 failed | 36 passed (37)
```

唯一失败项为 `FullSiteConsistencyStaticAudit.test.ts`，当前暴露的问题为：

- `src/views/workflows/WorkflowLifecycle.vue` 仍使用 `v-loading="detailLoading"`。

上一轮的 `ToolWorkbench.vue`、`organizations/detail.vue` `v-loading` 已完成迁移并不再是当前失败项。

## 3. 根因分析

`FullSiteConsistencyStaticAudit.test.ts` 对全部 `src/views/**/*.vue` 执行共享 UI 治理检查，禁止页面层直接使用 `v-loading`。`WorkflowLifecycle.vue` 已经使用 `PageHeader`、`SurfaceCard`、`StatePanel`，但详情区域仍以 `v-loading` 覆盖整个内容网格，同时保留 `el-empty` 作为局部空状态。

因此问题属于页面状态呈现方式未完全迁移到共享 primitive，而不是 Workflow API Contract、Execution 状态机、Trigger 操作或 Durable ID 关系逻辑问题。

## 4. 本轮代码修复

### 4.1 WorkflowLifecycle

本轮将详情区域状态统一收敛到 `StatePanel`：

- `detailLoading` 为真时直接渲染 `StatePanel state="loading"`；
- 详情加载成功后再渲染版本、Execution、Trigger 内容；
- 发布版本缺失改用 `StatePanel state="empty"`；
- Execution 列表为空改用 `StatePanel state="empty"`；
- Trigger 列表为空改用 `StatePanel state="empty"`。

因此移除了页面中的 `v-loading`、`el-empty`，没有增加第二套状态管理。

未修改：

- `workflowApi.list / versions / triggers / listExecutions / schedule`；
- Execution run / cancel / retry / resume；
- Trigger invoke / update / delete；
- Runtime / Trace / Audit 深链参数；
- 权限判断与归档保护；
- 后端 Contract 和 Durable ID 关系。

### 4.2 回归测试

现有 `WorkflowLifecycle.test.ts` 已覆盖共享状态组件、加载失败、权限、空数据、详情刷新、Execution 操作及诊断深链行为。本轮继续依赖 `FullSiteConsistencyStaticAudit.test.ts` 对所有 View 的 `v-loading / el-empty / el-result / el-card` 统一治理。

代码修复采用单一原子提交：

`fix: unify workflow lifecycle loading states`

### 4.3 与前序治理修复的连续性

当前静态审计按“一个页面、一个遗留 primitive、一次最小迁移”推进，已连续处理：

- Organization Detail；
- Tool Workbench；
- Workflow Lifecycle。

避免通过一次性大规模重构改变既有 API、权限或业务行为。

## 5. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前约束：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 6. 当前验证状态

本轮环境不能直接执行用户 Windows 工作树中的 `npm test`，因此不记录未经实际执行的“通过”。当前已根据用户反馈完成根因定位、最小代码修复、既有回归测试复核和文档同步。

用户本地先同步最新 `frontend`：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend
git rev-parse HEAD
```

然后执行 targeted regression：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts tests/views/LoginForm.test.ts tests/views/OrganizationsDetail.test.ts tests/views/Tools.test.ts tests/views/WorkflowLifecycle.test.ts
```

若 targeted regression 全部通过，再执行：

```powershell
npm test
npm run build
npm run test:gate
npm run test:e2e
```

没有实际执行的测试不得记录为通过；测试数据必须由 Fixture / Script 自动生成，不得要求手工填写业务信息，也不得自动启动 API、Scheduler、Worker、PostgreSQL、Redis。

## 7. 本地手动验证流程

1. 打开 Workflow 生命周期页，确认首次加载由统一 `StatePanel` 呈现 Loading。
2. 工作流详情成功后确认版本、Execution、Trigger 三个区域正常展示。
3. 没有已发布版本、没有 Execution、没有 Trigger 时，分别确认对应 Empty 状态正常展示。
4. 详情加载失败时确认 Error 状态提供“重新加载”，且不暴露原始异常正文。
5. 工作流列表无权限时确认 Permission 状态阻止误导性操作。
6. 手动触发、Execution run/cancel/retry/resume、Trigger 编辑/删除后确认页面重新读取后端真实状态。
7. 从 Execution 进入 Runtime / Trace / Audit 时确认 URL 使用真实 `execution_id / workflow_id / workflow_version_id`；从诊断上下文返回时不重新推导关系。
8. 小屏宽度下确认生命周期步骤、详情卡片、操作区保持可读，不产生明显布局溢出。

## 8. 下一步

当前状态保持 **进行中**：WorkflowLifecycle 的静态治理修复需要用户本地重新执行 targeted regression 后才能确认通过。全量 `npm test`、build、gate、E2E 仍未由本轮环境实际执行。

若下一轮静态审计继续暴露历史 View primitive，则仍逐项最小化修复，不进行无关的大规模重构。
