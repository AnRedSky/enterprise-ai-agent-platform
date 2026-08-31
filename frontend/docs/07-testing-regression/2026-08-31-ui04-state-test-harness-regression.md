# UI-04 状态测试 Harness 回归记录 — 2026-08-31

## 1. 基线

本轮先确认最新 `main`，随后将其通过 PR #67 合并到 `frontend`。当前 `main` 基线为 `341d12729364ade1cf7cd2b3e108b22312e29fe4`，同步合并提交为 `68ddb1780adaa0102ae09f1bec35e2ca4686e4a5`；当前 `frontend` 已不落后于 `main`。前端继续遵循现行准则：Backend Contract → API Types → View / Component → Vitest → Real API / E2E；状态页面必须覆盖 Loading / Empty / Error / Success / Permission。

用户本地回归反馈集中在 Dashboard / Agent / AuditLog / Tool，以及既有 UI-04 状态测试：

- Agent UI-04：成功态断言错误地把隐藏 Dialog 内的 StatePanel 计入页面；对话调试 Permission 场景的 Dialog stub 没有模拟 `v-model` 可见性，因此打开对话后状态面板无法按真实交互呈现。
- Dashboard：指标测试直接读取 MetricCard 根节点文本，把 label、value、caption、description 拼接后的完整文本当成数值，导致数值断言失败。
- AuditLog / Agent / Tool / Dashboard：测试环境未完整提供 Element Plus `el-icon` 与 loading directive，产生 Vue warning；这些 warning 不代表生产组件缺少依赖，而是测试 Harness 没有覆盖共享组件依赖。

## 2. 根因与决策

### 2.1 Agent Dialog 测试 Harness

`AgentWorkbench` 的多个 `el-dialog` 包含 StatePanel。旧测试 stub 无条件渲染 slot，导致实际不可见的 Dialog 内容进入测试 DOM，从而破坏“成功态页面不存在 StatePanel”的断言。该问题属于测试 Harness 与真实 Element Plus Dialog 可见性语义不一致，不应修改生产页面状态机。

决策：Dialog stub 增加 `modelValue` prop，仅在 `modelValue=true` 时渲染 slot；同时在测试 Harness 中显式提供 `el-icon` stub 和 loading directive。

### 2.2 Dashboard MetricCard 测试契约

`MetricCard` 是公共组件，根节点同时包含 label、value、trend 和 description。测试要求的是指标数值，而不是整个卡片的可见文本，因此应定位公共组件的 value 子节点，而不是修改 MetricCard 的信息架构来迎合测试。

决策：指标断言统一使用 `[data-testid] .ui-metric-card__value`，保持公共组件现有 UI 结构。

### 2.3 Element Plus 测试依赖

`StatePanel` 和 MetricCard 使用 Element Plus 图标；部分业务页面使用 `v-loading`。测试应通过 Harness 提供必要的 stub/directive，避免把正常组件依赖误判为运行时故障，同时保持真实生产组件实现不变。

## 3. 本轮修复

提交：`test: align UI-04 regression harness`

- AgentUI04：修正 Dialog 可见性 stub；补充 `el-icon` 与 loading directive 测试依赖；保持生产 Agent 状态机不变。
- Dashboard：修正 MetricCard 数值断言定位；保持 MetricCard 公共 API 和视觉结构不变。
- 未新增 API client、mapper、状态枚举或业务逻辑。

## 4. 验证状态

用户本地反馈基线：5 个 targeted test 文件、21 个测试，18 个通过、3 个失败；失败均定位到测试 Harness/断言契约，不是 Backend Contract 失败。

当前远程操作环境不能直接执行用户 Windows 工作树中的 npm，因此本记录不把修复后的测试标记为已通过。应在本地执行：

```powershell
npm run test:unit -- --run `
  tests/views/AgentUI04.test.ts `
  tests/views/AuditLogUI04.test.ts `
  tests/views/Dashboard.test.ts `
  tests/views/Tools.test.ts `
  tests/views/OperationsConsole.test.ts
```

随后按项目准则继续：

```powershell
npm test
npm run build
npm run test:gate
```

测试数据继续由 Vitest mock 自动生成，不启动服务、不手工填写业务数据、不使用 `npx` 临时下载测试框架。

## 5. 下一步

targeted UI-04 回归通过后，继续 P1.1 主线：Runtime Tab / 按需加载、Agent 调试上下文、Workflow 生命周期与真实 Execution 联动。避免为了消除测试 warning 修改生产组件或复制公共状态模式。