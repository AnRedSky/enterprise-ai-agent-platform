# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`。当前 `main` 已包含在 `frontend` 的 merge-base 中，当前 merge-base 为 `e2fade475c39f8f6a319b25b168114dfd903634e`；本轮未发现 `frontend` 落后于 `main` 的提交。

本轮未修改后端业务 Contract；frontend 继续消费已确认的正式 API 类型与 Durable Facts。

## 2. 用户最新本地全量 Vitest 反馈

用户在 Windows `frontend` 工作树执行 `npm test`，反馈结果：

```text
Test Files  8 failed | 62 passed (70)
Tests       9 failed | 314 passed (323)
```

失败项分为四类：

1. `ToolWorkbenchUI03UI05.test.ts` 在测试 fixture 中存在未转义的 Vue template 双引号，导致 Vite/esbuild 在加载测试文件阶段直接报 `Syntax error "b"`。
2. `Agents.test.ts` 对用户可见错误文案要求句末 `。`，而当前实现使用无句号的既有文案；属于测试契约漂移，不涉及后端错误正文泄漏。
3. Audit Log 的 Runtime durable-ID 测试使用过于严格的字符串空格格式，同时 Full-site gap audit 错把 `AuditLogWorkbench.vue` 外层壳视为必须直接持有 `StatePanel`；实际状态 primitive 已由其子组件 `AuditLogPanel.vue` 持有。
4. Dashboard / Knowledge UI-04 的状态测试仍假设“全部数据为空”时必须由页面外层 StatePanel 终止 workspace，但当前设计已经把空状态下沉到最近执行区域 / shared primitive；测试应验证用户可见状态与工作区行为，而不是要求旧的 DOM 结构。

## 3. 根因分析

### 3.1 ToolWorkbench 测试编译失败

测试 fixture 使用普通双引号包裹 Vue template，同时 template 内部存在 `@click="$emit(...)"`，转义层级错误使 esbuild 无法解析测试文件。该问题发生在测试加载阶段，尚未进入业务断言。

### 3.2 Agents 错误文案断言漂移

`AgentWorkbench.vue` 已通过统一 `userError()` 屏蔽原始 HTTP / provider 错误正文。测试只需验证稳定的用户可见 fallback 与不泄漏原始错误即可，不应因中文句末标点差异造成回归失败。

### 3.3 Audit durable-ID / shared-state 断言过度耦合

`AuditLogPanel.vue` 已直接使用 `row.execution_id` 进入 Runtime；Audit 页面壳 `AuditLogWorkbench.vue` 只负责 PageHeader 与子组件组合。因此测试应验证 durable ID 传递关系与状态归属，而不是依赖单一字符串格式或要求父壳重复声明 `StatePanel`。

### 3.4 Dashboard / Knowledge 状态测试与当前 UI 结构漂移

Dashboard 当前允许“指标全为 0”时继续展示工作区，并在“最近执行”卡片内使用 `StatePanel state="empty"`。Knowledge Workbench 则在知识库成功加载后进入完整 `.grid` 工作区。测试应围绕成功工作区、错误恢复和空状态语义断言，而不是假设旧版顶层 DOM 结构。

## 4. 本轮最小修复

### 4.1 ToolWorkbench 测试 fixture

修复 `ToolWorkbenchUI03UI05.test.ts` 的 ConfirmDialog stub 字符串边界，使 Vite/esbuild 可以正常解析测试文件。未修改 ToolWorkbench API、权限、确认交互或 durable ID 行为。

原子提交：

`fix: repair tool workbench test fixture syntax`

### 4.2 Agent 错误文案测试契约

将测试断言对齐当前稳定用户可见 fallback：`智能体列表加载失败，请刷新后重试`，继续验证不会把 `500 Internal Server Error` 或 `provider unavailable` 暴露给用户。

原子提交：

`test: align agent error assertion with user-facing contract`

### 4.3 Audit Log

- Runtime 深链测试改为语义正则，验证 `execution_id` 来自 `executionId` 且 source 为 `audit`，不再绑定无意义空格格式；
- Full-site gap audit 将 shared-state 检查落到真正承载状态的 `AuditLogPanel.vue`；
- Audit Log 成功加载后明确展示 `审计日志已更新`，保持 UI-04 成功反馈契约；
- 保留 `row.execution_id` → Runtime 的 durable ID 关系，不根据列表顺序推断 Execution。

原子提交：

`test: make audit execution link assertion semantic`

`test: audit delegated state ownership correctly`

`fix: expose audit refresh success state`

### 4.4 Dashboard

取消“聚合数据全为空即进入顶层 empty 状态”的分支，使 Dashboard 在数据为空时仍展示指标与常用入口，并由“最近执行”区域的 `StatePanel state="empty"` 呈现 `暂无运行记录`。

这保持了 UI-03 快速入口可用性，也满足 UI-04 的 Empty 状态治理，不引入第二套状态管理。

原子提交：

`fix: keep dashboard empty execution state visible`

### 4.5 Knowledge UI-04 测试

将成功场景从“没有任何 `.state-panel`”调整为“存在 `.grid` 工作区且不存在 loading/error panel”；恢复成功场景同样验证 `.grid` 与 error panel 消失。这样测试验证用户实际可见的成功工作区，而不依赖 shared primitive 的内部 DOM 结构。

原子提交：

`test: assert knowledge success state by workspace semantics`

## 5. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前约束：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 6. 当前验证状态

本轮环境不能直接执行用户 Windows 工作树中的 `npm test`，因此**不记录未经实际执行的“通过”**。当前已经根据用户反馈完成失败分类、根因定位、最小代码/测试修复和文档同步。

用户本地同步最新 `frontend`：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend
git rev-parse HEAD
```

本轮完成后，先执行原始全量回归：

```powershell
npm test
```

若全量通过，再执行：

```powershell
npm run build
npm run test:gate
npm run test:e2e
```

没有实际执行的测试不得记录为通过；测试数据必须由 Fixture / Script 自动生成，不得要求手工填写业务信息，也不得自动启动 API、Scheduler、Worker、PostgreSQL、Redis。

## 7. 本地手动验证流程

1. 打开 Dashboard，使用空数据 fixture 验证指标、常用入口和“暂无运行记录”同时可见。
2. 打开 Knowledge Workbench，分别验证 Loading、Success、Empty、Error/Retry、Permission 状态。
3. 打开 Audit Log，确认首次加载 Loading、成功刷新反馈、Empty、Error、Permission 状态均使用 shared `StatePanel`。
4. 在 Audit Log 中点击真实 `execution_id`，确认 Runtime URL 使用该 durable ID，不通过列表位置推断。
5. 打开 Agent Workbench，触发列表错误，确认只展示用户可读 fallback，不显示 HTTP/provider 原始错误。
6. 打开 Tool Workbench，确认加载、错误、空状态均正常，并验证启用/停用确认后按 durable `tool.id` 调用后端。
7. 小屏宽度下确认上述页面操作区、表格、状态面板和卡片保持可读，不产生明显布局溢出。

## 8. 下一步

当前状态仍为 **进行中**：本轮修复尚未由用户 Windows 工作树重新执行 `npm test` 验证。下一步以用户最新全量 Vitest 结果为准：若仍失败，继续按照“单一根因 → 最小修复 → targeted/full regression → 文档 → 原子提交”推进，不进行无关的大规模重构。
