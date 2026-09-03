# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`。在处理本轮本地 regression 之前，`main` 已继续推进到 `af306fdb694ec92cf81ec28891996d50fe071f3a`，`frontend` 当前为 `ba0997bf22bdd411f272ab12719b2793b83eee81`，包含此前组织详情修复及其合并基线。

本轮先按开发准则将最新 `main` 纳入 `frontend`，再处理新的静态审计失败项。

本轮未修改后端业务 Contract；frontend 继续消费已确认的正式 API 类型与 Durable Facts。

## 2. 用户最新本地 targeted regression 反馈

用户在 Windows `frontend` 工作树执行包含组织详情回归测试的 targeted 命令，反馈结果：

```text
Test Files  1 failed | 6 passed (7)
Tests       1 failed | 27 passed (28)
```

唯一失败文件仍为 `FullSiteConsistencyStaticAudit.test.ts`，但暴露出的下一项历史问题已经移动到：

- `src/views/tools/components/ToolWorkbench.vue` 仍使用 `v-loading="loading"`。

这说明前一项 `organizations/detail.vue` 的 `v-loading` 已不再是当前静态审计报告中的失败项；当前门禁继续逐项收敛。

## 3. 根因分析

`FullSiteConsistencyStaticAudit.test.ts` 对全部 `src/views/**/*.vue` 执行共享 UI 治理检查，禁止页面层直接使用 `v-loading`。`ToolWorkbench.vue` 已经使用 `PageHeader`、`PageToolbar`、`SurfaceCard`、`StatePanel`，并已通过 `pageState` 表达 loading / empty / error / permission / success，但成功分支中的表格仍保留历史 `v-loading`。

因此问题属于页面状态呈现方式未完全迁移到共享 primitive，而不是工具 API Contract、权限模型或工具生命周期逻辑问题。

## 4. 本轮处理策略

本轮继续遵循：

> 本地实际失败 → 根因分析 → 单一修复 → targeted test → 文档 → 原子提交

修复范围严格限定为 ToolWorkbench 的 loading presentation contract：

- 成功分支不再通过 `v-loading` 对表格施加遮罩；
- 保留现有 `pageState` 的 loading 状态和 `StatePanel` 表达；
- 不修改工具创建、启停、绑定/解绑、执行 API；
- 不修改管理员权限判断；
- 不改变工具与智能体的真实 ID 关系；
- 不新增业务状态机或本地 durable fact。

本轮还为该治理规则补充 ToolWorkbench targeted regression，确保以后不会重新引入 `v-loading`。

## 5. 当前验证状态

本轮环境不能直接执行用户 Windows 工作树中的 `npm test`，因此不记录未经实际执行的“通过”。用户反馈已经确认当前 targeted suite 为 `1 failed / 6 passed / 28 tests`，唯一失败是 ToolWorkbench 的 `v-loading` 静态治理项。

代码修改后需要在本地重新执行：

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

## 6. 本地手动验证流程

1. 打开工具管理页，确认首次加载由统一 `StatePanel` 呈现 Loading。
2. 工具列表成功后确认表格正常展示，不再出现表格 `v-loading` 遮罩实现。
3. 工具为空时确认 Empty 状态及“创建工具”动作正常。
4. 工具数据加载失败时确认 Error 状态提供“重试”，且不暴露原始异常正文。
5. 无权限时确认 Permission 状态阻止误导性操作。
6. 管理员执行创建、启停、绑定、解绑和工具执行时，确认仍调用既有 API，并在需要时刷新后端真实状态。
7. 小屏宽度下确认页面 padding、工具栏和表格容器不产生明显横向布局异常。

## 7. 下一步

当前状态保持 **进行中**：ToolWorkbench 的静态治理修复需要用户本地重新执行 targeted regression 后才能确认通过。全量 `npm test`、build、gate、E2E 仍未由本轮环境实际执行。

若下一轮静态审计继续暴露历史 View primitive，则仍逐项最小化修复，不进行无关的大规模重构。
