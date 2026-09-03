# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮首先检查远端分支。当前 `main` 与 `frontend` 在本轮修复前均指向同一基线：

- `main`: `df63b91ec81420a73ee78c80994a4f80c3c9b13d`
- `frontend`: `df63b91ec81420a73ee78c80994a4f80c3c9b13d`

因此本轮无需再次执行 `main → frontend` 同步；后续修复均直接提交到 `frontend`。前端开发仍以已确认的后端 Contract 为唯一数据来源，未新增后端业务 Contract。

## 2. 用户最新本地 targeted regression 反馈

用户在 Windows `frontend` 工作树执行：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

反馈结果：

```text
Test Files  1 failed | 4 passed (5)
Tests       1 failed | 22 passed (23)
```

唯一失败文件为 `FullSiteConsistencyStaticAudit.test.ts`，失败点为：

- `src/views/integrations/GlobalRuntimeOperations.vue` 仍使用原始 `<el-card>`。

`Integrations.test.ts`、`IntegrationsUI03UI05.test.ts`、`OperationsConsole.test.ts`、`Organizations.test.ts` 均通过。

## 3. 根因分析

`FullSiteConsistencyStaticAudit.test.ts` 将所有 `src/views/**/*.vue` 的原始 Element Plus Card、Empty、Result 以及 `v-loading` 视为禁止的页面层实现，要求统一通过 `SurfaceCard` / `StatePanel` 表达页面结构和状态。

`GlobalRuntimeOperations.vue` 此前已经具备 Runtime Durable Facts API 和响应式布局，但视觉容器仍沿用历史 `el-card`。这属于公共 UI primitive 治理未完成，而不是后端 Contract 或 Runtime 业务逻辑问题。

## 4. 本轮代码修复

### 4.1 GlobalRuntimeOperations 统一 SurfaceCard / StatePanel

提交：

- `3f6a74fa7874b111e896a98a738c9551fc23e920` — `fix: migrate global runtime cards to shared surface primitive`

调整：

- 所有 Runtime 指标、Worker/Scheduler 状态、诊断、Execution 状态和 Workflow/Trigger 汇总容器由 `el-card` 迁移为 `SurfaceCard`；
- 首次加载使用 `StatePanel state="loading"`；
- 首次请求失败使用 `StatePanel state="error"`；
- 已有成功数据但刷新失败时保留最近成功数据，并使用轻量 `el-alert` 提示恢复动作；
- 保留原 Runtime API、数据字段、状态映射和响应式布局，不重复实现后端业务规则。

### 4.2 IntegrationEventConsole 提前收敛同类历史实现

提交：

- `904940005b6ed0158ace7930a506a9c18f069a05` — `fix: unify integration event page states`

调整：

- `<el-empty>` → `StatePanel state="empty"`；
- `v-loading` → 页面级 `StatePanel state="loading"`；
- 查询失败 → `StatePanel state="error"` 并提供“重新加载”；
- 表格增加 `row-key="id"`，明确以事件 durable ID 作为行身份；
- API 参数、分页、筛选、详情 Drawer 与复制事件编号行为保持不变。

该修复属于同一全站静态治理问题族，但保持独立原子提交，避免把不同页面修改混成单一提交。

## 5. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前约束：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 6. 当前验证状态

当前环境不能直接执行用户 Windows 工作树中的 `npm test`，因此不记录未经实际执行的“通过”。本轮已通过 GitHub 源码检查确认：

- `main` 与 `frontend` 在修复前完全同 SHA；
- `GlobalRuntimeOperations.vue` 已无 `<el-card>`；
- `GlobalRuntimeOperations.vue` 已引入 `SurfaceCard` 与 `StatePanel`；
- `IntegrationEventConsole.vue` 已无 `<el-empty>` / `v-loading`。

用户本地需要先同步最新 `frontend`：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend
git rev-parse HEAD
```

然后重新执行 targeted regression：

```powershell
npm test -- tests/views/FullSiteConsistencyStaticAudit.test.ts tests/views/Integrations.test.ts tests/views/IntegrationsUI03UI05.test.ts tests/views/OperationsConsole.test.ts tests/views/Organizations.test.ts
```

若 targeted regression 全部通过，再按项目标准顺序执行：

```powershell
npm test
npm run build
npm run test:gate
npm run test:e2e
```

没有实际执行的测试不得记录为通过。测试不得自动启动 API、Scheduler、Worker、PostgreSQL、Redis。

## 7. 本地手动验证流程

1. 全局 Runtime：确认首次加载显示统一 Loading；首次失败显示 Error；刷新失败时保留最近成功结果。
2. Runtime 指标、Worker/Scheduler、诊断、Execution、Workflow/Trigger：确认视觉容器统一、窄屏无明显横向溢出。
3. 事件记录：确认 Loading / Empty / Error / Data 四态正确切换，分页与筛选保持有效。
4. 集成中心：确认无投递目标时事件订阅入口保持禁用；存在目标后恢复。
5. 运维窗口：确认 `全局运行态势 / 总览 / 告警 / Provider / Metrics / Audit / 死信` 七个正式 Tab 均可切换。
6. Runtime / Workflow 深链：确认关系仅来自显式 durable ID，不通过数组位置或页面顺序推断。

## 8. 下一步

当前状态保持为 **进行中**，原因是用户本地尚未重新执行包含本轮修复后的 targeted regression，且全量 `npm test` / build / gate / E2E 尚未由本轮环境实际执行。

下一轮严格按照：

> **本地实际失败 → 根因分析 → 单一修复 → targeted test → 文档 → 原子提交**

继续推进。若新的静态审计暴露其他历史 View primitive，再逐个收敛，不进行无关的大规模重构。
