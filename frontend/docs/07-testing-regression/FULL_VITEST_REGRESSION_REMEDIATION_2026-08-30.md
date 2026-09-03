# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 通过 GitHub compare 确认 `main` 已在原 frontend 基线之上继续前进；`main` 当前 HEAD 为 `e1551fc88402cdca943b1509e516aa93725d1e45`。`frontend` 已先快速前移到该最新 `main`，避免继续基于过期后端测试/文档基线开发。

本次同步不是新增 merge commit：`main` 是原 `frontend` HEAD 的后继，因此采用 fast-forward 更新 `frontend`。

## 2. 2026-09-03 本地反馈

用户本地 `frontend` 执行：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

最新反馈结果：

```text
Test Files  3 failed | 2 passed (5)
Tests       2 failed | 12 passed (14)
Failed Suites 2
```

失败根因已经明确为三组：

1. **测试文件路径解析不兼容当前 Vitest 运行环境**：`IntegrationsUI03UI05.test.ts` 与 `OperationsConsole.test.ts` 使用 `fileURLToPath(new URL(..., import.meta.url))` 读取源码时收到 `The URL must be of scheme file`。
2. **Full-site presentation audit**：`AgentWorkbench.vue` 的 Chat 空消息状态仍使用原始 `<el-empty>`。
3. **Full-site durable relationship audit**：`RuntimeExecutions.vue` 存在 `triggers[0]` 的数组位置关系推断，同时该页面还残留原始 `el-card`、`el-empty` 与 `v-loading`，与全站共享 UI primitive 规则不一致。

## 3. 本轮修复

### 3.1 测试源码路径统一使用工作区根路径

`IntegrationsUI03UI05.test.ts` 与 `OperationsConsole.test.ts` 改为：

```ts
resolve(process.cwd(), "src/views/...")
```

不再依赖 Vitest/Vue transform 环境下 `import.meta.url` 的 URL scheme。

原子提交：

- `86c2b652e6008c546f061da5ae1c210b4c9abe80` — `test: stabilize integrations source path`
- `ec53bce7cacd078398f04214549129c0fa0660c8` — `test: stabilize operations source path`

### 3.2 AgentWorkbench Chat Empty State

`AgentWorkbench.vue` 已将 Chat 无消息场景从原始 `el-empty` 迁移为 `StatePanel`，并增加 Chat Context 本身的 Empty 状态：

- `loading` → `StatePanel.loading`
- `permission` → `StatePanel.permission`
- `error` → `StatePanel.error + Retry`
- `empty` → `StatePanel.empty`
- Chat `streaming / completed / failed / cancelled` 仍保持领域状态，不被页面状态组件替代。

原子提交：

- `e43e5f49107c2d393900aaa2b6c63555bbd65f6e` — `fix: align agent chat empty state`

### 3.3 RuntimeExecutions Durable Relationship 与 UI Primitive

`RuntimeExecutions.vue` 已移除无语义价值的 `triggers[0]` fallback。Trigger 只能由：

- 路由入口 `trigger_id`；或
- Trace `data.trigger_id`

提供 durable ID，再通过 `triggers.find(item => item.id === triggerId)` 建立关系；不再根据集合长度或位置推断实体关系。

同时完成页面共享 primitive 收敛：

- 原始 `el-card` → `SurfaceCard`
- 原始 `el-empty` → `StatePanel`
- `v-loading` → 页面 Loading 状态 `StatePanel`
- Execution / Trigger / Audit / Retry / Resume / Trace 关系仍以后端 durable ID 与字段为准。

原子提交：

- `b9506c864f1b64e6ad8dc3bdb8d90835185a6de6` — `fix: align runtime execution shared primitives`

## 4. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前继续约束所有 `src/views/**/*.vue`：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation。

该规则的目标不是限制 Element Plus 本身，而是确保页面级状态、Surface/Card 结构与 Durable Relationship 均使用项目已经建立的共享契约。

## 5. 后端同步事实

本轮开始时发现 `main` 已经包含原 `frontend` 基线之后的后端测试与错误记录更新，包括 Scheduler Runtime cleanup deadlock、Delegation Worker Runtime 等文档/测试变更。为确保 frontend 基于最新 backend facts 开发，已将 `frontend` fast-forward 到：

`e1551fc88402cdca943b1509e516aa93725d1e45`

其提交信息为 `docs(errors): record scheduler runtime cleanup deadlock`。

随后在 `frontend` 上追加本轮 4 个原子代码/测试提交；本文档为同步记录提交。

## 6. 验证状态

当前执行环境不能直接运行用户 Windows 工作树中的 `npm test`，因此不伪造测试通过结果。

用户本地更新到最新 `frontend` 后，首先执行 targeted regression：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend

npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

随后依次执行：

```powershell
npm run test:unit
npm run build
npm run test:gate
npm run test:e2e
```

测试环境约束保持不变：

- 测试不得自动启动 API、Scheduler、Worker、PostgreSQL、Redis；
- 测试数据必须由 Fixture / Script 自动生成；
- 禁止人工填写测试业务信息；
- targeted regression 通过后再进入完整 gate/E2E。

## 7. 本地手动验证流程

1. 确认 `frontend` 已包含 `main` 最新后端事实及本轮测试/页面修复。
2. 进入集成中心：确认无投递目标时事件订阅创建入口保持禁用，创建投递目标后恢复。
3. 进入运维窗口：确认 `全局运行态势 / 总览 / 告警 / Provider / Metrics / Audit / 死信` 七个正式 Tab 均可切换。
4. 进入智能体工作台：确认列表 Loading / Empty / Permission / Error / Success 状态一致；打开 Chat 时无生效版本显示 Empty State，不出现原始 Element Plus Empty。
5. 进入 Runtime：确认 Execution 列表 Loading / Empty 使用统一状态组件；打开 Execution 详情后，Audit、派生 Execution、Timeline、Trace Empty 均使用统一状态组件。
6. 通过 Workflow Trigger / Scheduler / Webhook 进入 Runtime 深链时，确认 Trigger ID 只来自显式入口上下文或 Trace durable data，不因集合顺序产生关联。
7. 在桌面与窄屏尺寸检查表单、工具栏、表格、Drawer、StatePanel，确认无明显横向溢出。

## 8. 当前状态

**本轮代码修复已提交，等待用户 Windows targeted regression 实测。**

在用户重新执行 targeted regression 并提供实际结果前，不将本轮标记为“全量通过”。
