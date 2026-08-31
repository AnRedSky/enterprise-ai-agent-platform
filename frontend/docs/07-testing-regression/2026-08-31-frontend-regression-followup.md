# 2026-08-31 前端回归阻塞修复记录

## 1. 背景

本轮开发首先核对 `main` 与 `frontend` 的同步状态；此前已存在 main → frontend 同步提交。本轮开发者反馈显示前端回归门禁存在 7 个失败文件、11 个失败测试以及 4 个未处理 Promise rejection，主要集中在 UI-03 / UI-04 状态契约与测试 harness。

## 2. 根因与修复

### 2.1 Knowledge UI-03 Loading 首屏状态

`KnowledgeWorkbench` 的 `loading` 初始值为 `false`，而 `onMounted(loadBases)` 发生在 mount 生命周期之后，导致首个同步渲染周期进入 Empty。修复为初始 `loading = true`，请求完成后仍由 `finally` 归位。

### 2.2 Runtime UI-04 Loading 首屏状态

`RuntimeObservabilityOverview` 同样将 `loading` 初始值设为 `false`。修复为初始 `loading = true`，保持现有请求和状态计算逻辑不变。

### 2.3 Tool UI-03 状态契约测试漂移

测试仍要求旧的 `el-empty` DOM，而 `ToolWorkbench` 已迁移到公共 `StatePanel`。测试改为验证 `StatePanel` 的 `empty` 状态、标题和描述；管理员创建动作改为验证 `PageHeader` action slot 的可见文本，不绑定 Element Plus stub 内部 DOM。

### 2.4 Runtime Operations Audit Tab

测试直接修改 `wrapper.vm.activeTab`，依赖 Element Plus Tabs 内部状态同步，导致 Audit pane 未稳定进入测试上下文。测试改为定位 `Audit` tab 并触发 click，再执行下一 tick 后验证过滤器与审计数据。

### 2.5 Runtime / Audit UI-04 Unhandled Rejection

`it.each` 直接在测试参数定义阶段创建 `Promise.reject(...)`，Vitest 在测试消费前即捕获 unhandled rejection。修复为 Promise factory，在每个测试体内创建 rejected Promise 并立即交给 API mock。

## 3. 变更范围

- `frontend/src/views/knowledge/components/KnowledgeWorkbench.vue`
- `frontend/src/views/runtime/components/RuntimeObservabilityOverview.vue`
- `frontend/tests/views/Tools.test.ts`
- `frontend/tests/views/RuntimeUI04.test.ts`
- `frontend/tests/views/AuditLogUI04.test.ts`
- `frontend/tests/views/OperationsConsole.test.ts`

## 4. 验证状态

当前执行环境无法解析 `github.com`，因此无法直接复现用户 Windows 本地 Node/npm 环境；未伪称 `npm test`、`npm run build` 或 `npm run test:gate` 已通过。

开发者本地必须执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm ci
npm test -- tests/views/KnowledgeUI03.test.ts tests/views/Tools.test.ts tests/views/RuntimeUI04.test.ts tests/views/AuditLogUI04.test.ts tests/views/OperationsConsole.test.ts
npm test
npm run build
npm run test:gate
```

`npm run test:gate` 必须以 0 退出码结束，并且不得出现 Vitest `Unhandled Errors` / `Unhandled Rejection`。

## 5. 完成判定

当前状态：**待本地验证**。

在 targeted test、全量 Vitest、build 和 release gate 未实际执行并通过前，不标记本轮修复为完成。
