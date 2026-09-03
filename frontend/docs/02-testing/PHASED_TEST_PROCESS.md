# Frontend 分阶段测试流程

> 版本基线：`frontend` 分支
>
> 目标：以“阶段测试 → 失败根因分析 → 原子修复 → targeted regression → full regression → build → Real API / Browser E2E”为固定发布路径。

## 1. 测试边界

- 测试脚本不自动启动、停止或重启 API / Worker / Scheduler / Postgres / Redis。
- 测试数据必须由脚本生成或 fixture 提供，禁止依赖人工填写测试信息。
- 前端测试以真实后端 API / 数据结构为契约，不通过数组顺序推断实体关系。
- UI 状态统一验证 Loading / Empty / Error / Permission / Success。
- 运行链路、审计、Trigger、Workflow 等跨页面导航必须使用后端返回的持久化 ID。

## 2. 分阶段执行顺序

### P0：环境与核心回归

```powershell
cd frontend
npm ci
npm exec vitest run tests/views/AppShell.test.ts
```

预期：依赖可用、核心 Shell 测试通过。

### P1：AI 资产

```powershell
npm run test:phase:p1
```

覆盖 Agent、Knowledge、Tool、Model Provider，以及 Agent Workbench UI-05、Agent Debug UI-04。

### P2：自动化与 Runtime

```powershell
npm run test:phase:p2
```

覆盖 Workflow、Workflow UI-03/UI-04/UI-05、Trigger、Runtime、Runtime Deep Link、Runtime Correlations。

### P2.10：Runtime Operations

```powershell
npm run test:phase:p2.10
```

覆盖 Runtime Operations API、Global Runtime Operations 页面及生产构建。

### P3：企业治理

```powershell
npm run test:phase:p3
```

覆盖 Organization、Audit、Integration、Dashboard。

### P4：平台体验

```powershell
npm run test:phase:p4
```

覆盖 AppShell 与平台级共享体验。

### Full-site 静态一致性

```powershell
npm exec vitest run tests/views/FullSiteConsistencyGapAudit.test.ts tests/views/FullSiteConsistencyStaticAudit.test.ts
```

预期：核心页面不存在已禁止的 raw `el-card` / `v-loading` / `el-empty` / `el-result`、数组位置实体推断及常见 optimistic durable-fact mutation。

### 全量 Unit / Build

```powershell
npm run test:unit
npm run build
```

两项均通过后才进入 Real API / Browser E2E。

### 前端回归 Gate

```powershell
npm run test:gate
```

### 最终 UI Release Gate

```powershell
npm run test:final
```

## 3. 本轮本地反馈根因与修复

### 3.1 Workflow Trigger 测试错误地假设页面自动选择 Workflow

现象：`WorkflowTriggers.test.ts` 的 10 个失败均从 `api.triggers('w1')` 未被调用开始。

根因：页面契约要求用户显式选择 Workflow；`onMounted` 只加载 Workflow 列表，不根据数组第一项自动建立目标关系。

修复：测试 fixture 先等待 Workflow 列表，再显式设置 `selectedWorkflowId = 'w1'` 并调用 `loadTriggers()`；同时将测试中的不存在的 `createTrigger()` 调整为真实页面方法 `saveTrigger()`。

设计原则：测试应验证产品真实交互契约，不应通过测试桩迫使页面恢复被治理禁止的 `[0]` 自动推断。

### 3.2 Workflows UI-04/UI-05 测试未建立选中 Workflow 上下文

现象：403 Permission、Trace Loading、Archived Read-only 三项失败显示页面仍处于“请选择 Workflow”。

根因：`Workflows` 页面只有 Workflow 列表自动加载，版本/运行/审计/Trace 状态属于选中 Workflow 的子工作台。

修复：增加 `mountWithWorkflow()` fixture，统一先等待列表，再通过真实 `selectWorkflow(workflow)` 建立上下文；403 断言改为页面实际的权限文案“当前账号没有访问该资源的权限”；归档测试验证真实“已归档”事实及编辑/删除操作不存在。

### 3.3 Agent Debug Loading 测试存在 mounted hook 时序假设

现象：测试立即断言 `loading`，但首次同步渲染时 mounted hook 尚未完成状态更新。

根因：`loadDebugContext()` 在 `onMounted` 中执行，`loading` 是响应式运行态状态，不能用同步首次 render 作为契约。

修复：使用 `vi.waitFor()` 等待 `loading` 状态出现，再释放挂起的 Agent 列表 Promise。

## 4. 测试失败判定原则

- “测试失败但产品代码正确”必须修正 fixture / assertion，而不是修改产品代码迎合旧测试假设。
- “测试失败且产品代码违反后端契约 / UI 治理”必须修正产品代码并补充回归测试。
- Vue Test Utils 中的 unresolved component warning 不是自动等价于产品失败；但若 warning 影响交互或 DOM 契约，必须补充对应 stub。
- `console.error` 仅用于诊断时应避免将原始后端错误暴露给用户 UI；测试必须验证用户看到的是安全、稳定的业务错误文案。

## 5. 本轮验证状态

本轮用户提供的本地反馈在修复前为：

- 第一组：4 个测试文件，33 个测试，23 passed / 10 failed。
- 第二组：5 个测试文件，14 个测试，10 passed / 4 failed。

上述结果是**修复前基线**，不能作为修复后的 PASS 结果。

GitHub 连接器可修改和审阅仓库，但本轮没有在用户 Windows 本地环境执行 `npm exec vitest` / `npm run build`，因此修复后的测试状态必须以用户本地重新执行结果为准。

## 6. 发布前完整流程

1. 同步最新 `main` → `frontend`。
2. P0 环境与核心回归。
3. P1 AI 资产。
4. P2 自动化与 Runtime。
5. P2.10 Runtime Operations。
6. P3 企业治理。
7. P4 平台体验。
8. Full-site 静态一致性。
9. `npm run test:unit`。
10. `npm run build`。
11. `npm run test:gate`。
12. 手动启动依赖服务后执行 Real API acceptance；脚本本身不启动服务。
13. 执行 Browser E2E，使用脚本自动生成的测试数据。
14. `npm run test:final`。
15. 记录实际 PASS/FAIL、失败根因、修复 commit 和环境信息。
