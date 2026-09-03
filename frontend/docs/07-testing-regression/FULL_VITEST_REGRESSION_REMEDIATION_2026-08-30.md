# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`。在处理本轮本地 regression 之前，`main` 已继续推进到 `af306fdb694ec92cf81ec28891996d50fe071f3a`，`frontend` 已将该最新 `main` 纳入当前历史。

本轮未修改后端业务 Contract；frontend 继续消费已确认的正式 API 类型与 Durable Facts。

## 2. 用户最新本地 targeted regression 反馈

用户在 Windows `frontend` 工作树执行包含组织详情回归测试的 targeted 命令，反馈结果：

```text
Test Files  1 failed | 6 passed (7)
Tests       1 failed | 27 passed (28)
```

唯一失败文件为 `FullSiteConsistencyStaticAudit.test.ts`，当前暴露的问题为：

- `src/views/tools/components/ToolWorkbench.vue` 仍使用 `v-loading="loading"`。

上一轮的 `organizations/detail.vue` `v-loading` 已完成迁移并不再是当前失败项。

## 3. 根因分析

`FullSiteConsistencyStaticAudit.test.ts` 对全部 `src/views/**/*.vue` 执行共享 UI 治理检查，禁止页面层直接使用 `v-loading`。`ToolWorkbench.vue` 已经使用 `PageHeader`、`PageToolbar`、`SurfaceCard`、`StatePanel`，并已通过 `pageState` 表达 loading / empty / error / permission / success，但成功分支中的表格仍保留历史 `v-loading`。

因此问题属于页面状态呈现方式未完全迁移到共享 primitive，而不是工具 API Contract、权限模型或工具生命周期逻辑问题。

## 4. 本轮代码修复

### 4.1 ToolWorkbench

本轮仅移除成功分支表格上的 `v-loading="loading"`。

Loading 仍由既有 `pageState` + `StatePanel state="loading"` 表达；成功后才渲染工具表格，因此不会损失用户可见的 Loading 状态，也不会引入第二套状态逻辑。

未修改：

- `listTools` / `listAgents` API；
- 工具创建、启停、绑定、解绑、执行行为；
- 管理员权限判断；
- 工具与智能体真实 ID 关系；
- 后端 Contract。

### 4.2 回归测试

扩展既有 `frontend/tests/views/Tools.test.ts`，增加静态 presentation contract：

- `ToolWorkbench.vue` 不得包含 `v-loading`；
- 页面仍通过 `StatePanel` 与 `pageState` 表达 loading。

代码、回归测试与本轮错误记录保持在同一个原子修复提交中。

## 5. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前约束：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 6. 当前验证状态

本轮环境不能直接执行用户 Windows 工作树中的 `npm test`，因此不记录未经实际执行的“通过”。当前已根据用户反馈完成根因定位、最小代码修复、针对性回归测试和文档同步。

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
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts tests/views/LoginForm.test.ts tests/views/OrganizationsDetail.test.ts tests/views/Tools.test.ts
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

1. 打开工具管理页，确认首次加载由统一 `StatePanel` 呈现 Loading。
2. 工具列表成功后确认表格正常展示，不再出现表格 `v-loading` 遮罩实现。
3. 工具为空时确认 Empty 状态及“创建工具”动作正常。
4. 工具数据加载失败时确认 Error 状态提供“重试”，且不暴露原始异常正文。
5. 无权限时确认 Permission 状态阻止误导性操作。
6. 管理员执行创建、启停、绑定、解绑和工具执行时，确认仍调用既有 API，并在需要时刷新后端真实状态。
7. 小屏宽度下确认页面 padding、工具栏和表格容器不产生明显横向布局异常。

## 8. 下一步

当前状态保持 **进行中**：ToolWorkbench 的静态治理修复需要用户本地重新执行 targeted regression 后才能确认通过。全量 `npm test`、build、gate、E2E 仍未由本轮环境实际执行。

若下一轮静态审计继续暴露历史 View primitive，则仍逐项最小化修复，不进行无关的大规模重构。
