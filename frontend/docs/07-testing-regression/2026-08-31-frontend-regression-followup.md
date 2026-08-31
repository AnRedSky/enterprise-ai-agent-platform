# 2026-08-31 前端回归阻塞修复记录

## 1. 背景

本轮开发基于 `main` 最新代码检查 `frontend`。GitHub `main...frontend` 当前为 `identical`，说明此前的 main 同步提交已经完成，本轮无需重复制造同步提交。

开发者本地反馈显示前端回归门禁存在 7 个失败文件、11 个失败测试以及 4 个未处理 Promise rejection，主要集中在 UI-03 / UI-04 状态契约与测试 harness。

## 2. 根因与修复

### 2.1 Knowledge UI-03 Loading 首屏状态

**现象**：`KnowledgeUI03.test.ts` 首次 mount 立即读取 `StatePanel.state`，得到 `empty` 而不是 `loading`。

**根因**：`KnowledgeWorkbench` 的 `loading` 初始值为 `false`，而 `onMounted(loadBases)` 发生在 mount 生命周期之后；因此首个同步渲染周期已经被计算为 Empty。

**修复**：将页面初始 `loading` 设置为 `true`，并保留 `loadBases()` 的 finally 归位逻辑。这样首屏状态稳定为 Loading，异步请求结束后再进入 Success / Empty / Error / Permission。

### 2.2 Runtime UI-04 Loading 首屏状态

**现象**：`RuntimeUI04.test.ts` 首次 mount 得到 `empty`。

**根因**：`RuntimeObservabilityOverview` 同样将 `loading` 初始值设为 `false`。

**修复**：初始 `loading = true`，保持现有异步请求和状态计算逻辑不变。

### 2.3 Tool UI-03 状态契约测试漂移

**现象**：测试仍要求 `el-empty` 和旧文案，但 `ToolWorkbench` 已迁移到公共 `StatePanel` 状态模式。

**根因**：测试没有跟随 UI-03 公共模式迁移更新，形成旧 DOM 断言与当前实现的不一致。

**修复**：测试改为验证 `StatePanel` 的 `empty` 状态、标题和描述；管理员创建动作改为验证 `PageHeader` action slot 的可见文本，而不绑定 Element Plus stub 的内部 DOM 结构。

### 2.4 Runtime Operations Audit Tab 测试

**现象**：测试直接修改 `wrapper.vm.activeTab` 后读取文本，Audit pane 未稳定进入可见/挂载状态。

**根因**：测试依赖 Element Plus Tabs 内部状态同步，而不是用户真实交互。

**修复**：测试定位 `Audit` tab 并触发 click，再执行下一 tick 后验证主体/资源过滤器和审计数据。

### 2.5 Runtime / Audit UI-04 未处理 Promise rejection

**现象**：`it.each` 在测试参数定义阶段直接创建 `Promise.reject(...)`，Vitest 在测试真正消费 Promise 前已经捕获到 unhandled rejection。

**根因**：Rejected Promise 被作为静态测试数据创建，而不是在测试体内创建。

**修复**：将异常响应改为 Promise factory，在每个测试执行阶段创建并立即交给 API mock，消除测试收集阶段的 unhandled rejection。

## 3. 变更范围

- `frontend/src/views/knowledge/components/KnowledgeWorkbench.vue`
- `frontend/src/views/runtime/components/RuntimeObservabilityOverview.vue`
- `frontend/tests/views/KnowledgeUI03.test.ts`（既有契约保持）
- `frontend/tests/views/Tools.test.ts`
- `frontend/tests/views/RuntimeUI04.test.ts`
- `frontend/tests/views/AuditLogUI04.test.ts`
- `frontend/tests/views/OperationsConsole.test.ts`

## 4. 验证状态

本环境无法直接执行用户 Windows 本地 Node/npm 测试：当前运行环境无法解析 `github.com`，因此未伪称已经执行 `npm test` / `npm run build` / `npm run test:gate`。

必须由开发者本地执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm ci
npm test -- tests/views/KnowledgeUI03.test.ts tests/views/Tools.test.ts tests/views/RuntimeUI04.test.ts tests/views/AuditLogUI04.test.ts tests/views/OperationsConsole.test.ts
npm test
npm run build
npm run test:gate
```

其中 `npm run test:gate` 必须以 0 退出码结束，且不得出现 Vitest `Unhandled Errors` / `Unhandled Rejection`。

## 5. 完成判定

当前状态：**待本地验证**。

代码修复已经提交到 `frontend`，但在本地 targeted test、全量 Vitest、build 和 release gate 未实际执行并通过前，不标记为完成。
