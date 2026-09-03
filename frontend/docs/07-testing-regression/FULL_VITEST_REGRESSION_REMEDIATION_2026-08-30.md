# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮开发先通过 GitHub 检查 `main`，发现其已继续前进至 `e2be75afe774d66a493f8f453e29bc517b69ab2a`，且该提交已经包含原 frontend 基线 `e43e5f49107c2d393900aaa2b6c63555bbd65f6e`。随后将最新 `main` 合并进入 `frontend`，并保留本轮 Runtime/UI 与回归文档修改。

最终 `frontend` 使用 merge commit `efaa647ab4c0e054eb9fe2ce7b6ceef10e4657e6`，双亲分别为本轮 frontend 工作头和最新 `main`。因此当前 frontend 与最新 main 的代码基线已经重新统一，同时保留本轮待验证修复。

## 2. 2026-09-03 本地反馈

用户本地 `frontend` 执行：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

反馈结果：

```text
Test Files  3 failed | 2 passed (5)
Tests       2 failed | 12 passed (14)
Failed Suites 2
```

失败根因明确为三组：

1. **测试文件路径解析不兼容当前 Vitest 运行环境**：`IntegrationsUI03UI05.test.ts` 与 `OperationsConsole.test.ts` 使用 `fileURLToPath(new URL(..., import.meta.url))` 读取源码时收到 `The URL must be of scheme file`。
2. **Full-site presentation audit**：`AgentWorkbench.vue` 的 Chat 空消息状态仍使用原始 `<el-empty>`。
3. **Full-site durable relationship audit**：`RuntimeExecutions.vue` 存在 `triggers[0]` 数组位置关系推断；同时该页面残留原始 `el-card`、`el-empty`、`v-loading`。

## 3. 本轮修复

### 3.1 测试源码路径

`IntegrationsUI03UI05.test.ts` 与 `OperationsConsole.test.ts` 改为：

```ts
resolve(process.cwd(), "src/views/...")
```

不再依赖 Vitest/Vue transform 环境中的 `import.meta.url` scheme。

已由最新 main 合入的原子提交：

- `86c2b652e6008c546f061da5ae1c210b4c9abe80` — `test: stabilize integrations source path`
- `ec53bce7cacd078398f04214549129c0fa0660c8` — `test: stabilize operations source path`

### 3.2 AgentWorkbench Chat Empty State

`AgentWorkbench.vue` 将 Chat 无消息场景迁移为 `StatePanel`，并增加 Chat Context 本身的 Empty 状态：

- `loading` → `StatePanel.loading`
- `permission` → `StatePanel.permission`
- `error` → `StatePanel.error + Retry`
- `empty` → `StatePanel.empty`
- Chat `streaming / completed / failed / cancelled` 保持领域状态，不被页面状态组件替代。

已存在于 main 的提交：

- `e43e5f49107c2d393900aaa2b6c63555bbd65f6e` — `fix: align agent chat empty state`

### 3.3 RuntimeExecutions Durable Relationship 与 UI Primitive

`RuntimeExecutions.vue` 已移除无语义价值的 `triggers[0]` fallback。Trigger 只能由：

- 路由入口 `trigger_id`；或
- Trace `data.trigger_id`

提供 durable ID，再通过 `triggers.find(item => item.id === triggerId)` 建立关系，不再根据集合长度或位置推断实体关系。

同时完成页面 primitive 收敛：

- `el-card` → `SurfaceCard`
- `el-empty` → `StatePanel`
- `v-loading` → 页面 Loading `StatePanel`
- Execution / Trigger / Audit / Retry / Resume / Trace 关系仍以后端 durable ID 与字段为准。

本轮提交：

- `b9506c864f1b64e6ad8dc3bdb8d90835185a6de6` — `fix: align runtime execution shared primitives`

## 4. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 持续约束所有 `src/views/**/*.vue`：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation。

这些约束用于保证页面级状态、Surface/Card 结构以及实体关系均来自明确的共享契约和后端事实。

## 5. 当前版本控制事实

最新 main：

`e2be75afe774d66a493f8f453e29bc517b69ab2a`

最新 frontend：

`efaa647ab4c0e054eb9fe2ce7b6ceef10e4657e6`

本轮已通过 merge commit 将最新 main 合入 frontend；merge commit 双亲为 frontend 工作头与 main HEAD。后续开发必须继续以该合并后的 frontend 为唯一工作基线，避免重新基于旧 main 开发。

## 6. 验证状态

当前执行环境不能直接运行用户 Windows 工作树中的 `npm test`，因此不伪造通过结果。

用户本地更新后首先执行 targeted regression：

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

测试环境约束：

- 测试不得自动启动 API、Scheduler、Worker、PostgreSQL、Redis；
- 测试数据必须由 Fixture / Script 自动生成；
- 禁止人工填写测试业务信息；
- targeted regression 通过后再进入完整 gate/E2E。

## 7. 本地手动验证流程

1. 确认 `frontend` 已包含最新 `main` 与本轮修复。
2. 集成中心：无投递目标时事件订阅创建入口保持禁用，创建投递目标后恢复。
3. 运维窗口：确认 `全局运行态势 / 总览 / 告警 / Provider / Metrics / Audit / 死信` 七个正式 Tab 均可切换。
4. 智能体工作台：确认 Loading / Empty / Permission / Error / Success 状态一致；Chat 无生效版本或无消息时使用统一 StatePanel。
5. Runtime：确认 Execution 列表及详情中的 Loading / Empty 状态使用共享组件。
6. Workflow Trigger / Scheduler / Webhook 深链：确认 Trigger ID 只来自显式入口或 Trace durable data，不因集合顺序推断关系。
7. 桌面与窄屏：检查工具栏、表格、Drawer、StatePanel 无明显横向溢出。

## 8. 当前状态

**代码修复与最新 main 同步已完成，等待用户 Windows targeted regression 实测。**

在用户重新执行 targeted regression、unit、build、gate 并提供实际结果前，不将本轮标记为“全量通过”。
