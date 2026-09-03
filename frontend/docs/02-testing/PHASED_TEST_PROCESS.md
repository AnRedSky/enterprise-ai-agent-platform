# Frontend 分阶段测试流程

> 版本基线：`frontend` 分支。
>
> 固定路径：阶段测试 → 失败根因分析 → 原子修复 → targeted regression → full regression → build → Real API / Browser E2E。

## 1. 测试边界

- 测试脚本不自动启动、停止或重启 API / Worker / Scheduler / Postgres / Redis。
- 测试数据由脚本生成或 fixture 提供，禁止依赖人工填写测试信息。
- 前端测试以真实后端 API / 数据结构为契约，不通过数组顺序推断实体关系。
- UI 状态统一验证 Loading / Empty / Error / Permission / Success。
- 运行链路、审计、Trigger、Workflow 等跨页面导航必须使用后端返回的持久化 ID。

## 2. 分阶段执行

```powershell
cd frontend
npm ci
npm exec vitest run tests/views/AppShell.test.ts
npm run test:phase:p1
npm run test:phase:p2
npm run test:phase:p2.10
npm run test:phase:p3
npm run test:phase:p4
npm exec vitest run tests/views/FullSiteConsistencyGapAudit.test.ts tests/views/FullSiteConsistencyStaticAudit.test.ts
npm run test:unit
npm run build
npm run test:gate
```

Real API / Browser E2E 只在本地依赖服务由开发者手动启动后执行；测试脚本不负责启动服务：

```powershell
cd frontend
npm run test:e2e
npm run test:final
```

如需一键执行本地前端回归（仍不会自动启动后端服务）：

```powershell
npm run test:local:full
```

## 3. 分阶段覆盖

- **P1**：Agent、Knowledge、Tool、Model Provider、Agent Workbench UI-05、Agent Debug UI-04。
- **P2**：Workflow、Workflow UI-03/UI-04/UI-05、Trigger、Runtime、Runtime Deep Link、Runtime Correlations。
- **P2.10**：Runtime Operations API / UI 与 production build。
- **P3**：Organization、Audit、Integration、Dashboard。
- **P4**：AppShell 与平台共享体验。
- **Full-site**：raw UI primitive、数组位置实体推断、常见 optimistic durable-fact mutation、关键 durable ID 导航约束。

## 4. 本轮失败根因与解决方案

### Workflow Trigger

`WorkflowTriggers.test.ts` 的 10 个失败均从 `api.triggers('w1')` 未调用开始。根因是页面只自动读取 Workflow 列表，Trigger 必须建立显式 Workflow 上下文；页面没有、也不应恢复数组第一项自动选择。测试 fixture 已改为显式设置 `selectedWorkflowId` 后调用 `loadTriggers()`，并将不存在的 `createTrigger()` 调整为页面真实方法 `saveTrigger()`。

### Workflows UI-04/UI-05

403 Permission、Trace Loading、Archived Read-only 三项失败均发生在测试没有建立选中 Workflow 上下文时。测试现通过 `selectWorkflow(workflow)` 建立真实上下文，并按页面真实文案断言权限和归档状态。

### Agent Debug UI-04

Loading 测试立即断言 `loading`，但状态由 `onMounted(loadDebugContext)` 更新，属于 mounted 后的响应式运行态。测试现使用 `vi.waitFor()` 等待 Loading 状态出现后再释放挂起 Promise。

## 5. 本轮基线与验证声明

用户提供的修复前本地基线：

- 第一组：4 个文件、33 个测试，23 passed / 10 failed。
- 第二组：5 个文件、14 个测试，10 passed / 4 failed。

这些是**修复前结果**，不能作为修复后 PASS。

本轮 GitHub 操作完成代码与测试修正，但 GitHub 连接器不能在用户 Windows 工作区执行 `npm exec vitest` / `npm run build`。因此修复后的最终结果必须以用户本地重新执行为准，未执行项目不会被标记为 PASS。

## 6. 失败判定原则

- 产品契约正确、测试假设错误：修 fixture / assertion，不修改产品代码迎合旧测试。
- 产品违反后端契约或 UI 治理：修产品代码并补回归测试。
- unresolved component warning 只有在影响交互或 DOM 契约时才升级为失败。
- 原始后端错误不得直接展示给用户；测试应验证稳定、安全的业务错误文案。
