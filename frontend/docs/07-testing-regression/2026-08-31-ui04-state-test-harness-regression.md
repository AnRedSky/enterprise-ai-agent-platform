# UI-04 状态测试 Harness 回归记录 — 2026-08-31

## 1. 基线

本轮先确认 `main` 与 `frontend` 已同步：当前两者均指向 `02654f4d2b3f0c6cfc227eb3b31e0b38a38527bf`，无待合并差异。前端开发继续直接基于 `frontend` 历史分支状态推进，并遵循现行前端准则：Backend Contract → API Types → View / Component → Vitest → Real API / E2E；状态页面必须覆盖 Loading / Empty / Error / Success / Permission。fileciteturn117file0L2-L2

用户本地回归反馈集中在 Dashboard / Knowledge / Tool，以及既有 UI-03 迁移测试：

- Dashboard：空数据时 UI-03 仍要求核心工作区可见；Error 文案不完整；未知 Execution 状态因页面被 Empty 状态短路而无法出现在 DOM。
- Knowledge / Tool：用户反馈的 UI-04 重试失败与当前远端代码已有的显式 `StatePanel` action 连接存在时间差；当前 `KnowledgeWorkbench` 已通过 `handleStateAction → loadBases` 处理 Error 重试，Tool 已通过 `handleStateAction → load` 处理 Error 重试。
- Knowledge UI-03：旧测试假设 Empty 状态仍渲染完整工作区，与 UI-04 的“状态优先”架构冲突。
- Operations Console：当前远端实现已经包含 Audit 的“资源类型”筛选与表格列，用户反馈对应的断言属于本地代码同步前的旧状态。

## 2. 根因与决策

### 2.1 Dashboard Empty 状态

Dashboard 原先在 `empty` 时只渲染一个页面级 `StatePanel`，因此核心指标、最近执行和常用入口全部被短路。该行为与 UI-03 要求的工作台骨架不一致，也会让空数据页面失去主要导航能力。

决策：保留 Empty `StatePanel` 作为一等状态，同时继续渲染指标、最近执行和常用入口。这样既满足 UI-04 状态表达，又保持 UI-03 工作台结构和快速导航可用。

### 2.2 Dashboard Error 文案

用户可见错误必须遵循“发生了什么 + 下一步怎么办”，不能暴露后端异常。当前统一为“平台数据加载失败，请稍后重试”。未知状态继续使用 `未知状态（技术值）`，不做强制归一化。该规则与前端准则一致。fileciteturn117file0L2-L2

### 2.3 UI-03 / UI-04 测试职责

UI-04 已成为页面状态的正式验收层，旧 UI-03 测试不得继续要求已经被 UI-04 架构取消的渲染条件。因此 Knowledge UI-03 测试调整为验证共享 `PageHeader` + `StatePanel` + Empty recovery action，而不是继续要求 Loading / Empty 时完整业务工作区直接可见。

## 3. 已实施变更

### 3.1 Dashboard 空状态工作区与错误边界

提交：`6173033d18e65ad3ed597f6109ae438781703496`

- Empty 保留 `StatePanel`；
- Empty 下继续展示 5 个核心指标、最近执行和常用入口；
- 错误文案统一为“平台数据加载失败，请稍后重试”；
- 保留未知 Execution 技术值展示规则；
- 未新增 API client、mapper 或状态枚举。

### 3.2 Knowledge UI-03 测试与 UI-04 架构对齐

提交：`aca0cbc523a9318a722c5d5ada50b2c1ed244e4b`

- 删除旧测试对完整工作区的错误假设；
- 改为验证 `PageHeader`、`StatePanel`、Empty 状态说明和“创建知识库”恢复动作；
- 不修改 Backend Contract 或生产 API。

### 3.3 Knowledge 空检索测试边界

提交：`cdffeeffd59d51c9a731f632844089bca1af73ec`

- 空检索问题继续禁止调用 `retrieveKnowledge`；
- 测试改为验证页面状态中的 `retrievalError = "请输入检索问题"`，避免在 Knowledge Empty 状态下要求不存在的检索工作区 DOM；
- 生产逻辑保持“先校验输入，再请求检索 API”。

## 4. 当前代码事实

- Dashboard 已具备 PageHeader / MetricCard / SurfaceCard / StatePanel 公共模式，并在 Empty 状态保留工作台导航。
- Knowledge Error 状态具备显式重试 action；Tool Error 状态同样具备显式重试 action。
- Operations Console Audit 已包含“资源类型”筛选和“资源类型”结果列。
- `StatePanel.test.ts` 已验证 Loading / Empty / Error / Permission / Success 和 recoverable action 六类公共行为。
- 未修改 Backend Contract；未新增第二套状态机；未知状态仍保留技术值。

## 5. 验证状态

用户本地反馈中的 `npm run build` 已成功完成，Vite 生产构建通过，产物正常生成。

用户反馈的全量 Vitest 基线为：`45` 个测试文件、`186` 个测试，其中 `33` 个文件通过、`12` 个文件失败；失败项包含 UI-03 与旧测试 Harness 假设。该结果不能作为当前远端修复后的通过结果，因为随后已发生代码与测试提交。

当前远程操作环境不能直接执行用户 Windows 工作树中的 npm，因此不将未实际执行的命令记录为通过。应在本地按以下顺序复验：

```powershell
npm test -- tests/views/Dashboard.test.ts
npm test -- tests/views/DashboardUI03.test.ts
npm test -- tests/views/DashboardUI04.test.ts
npm test -- tests/views/KnowledgeUI03.test.ts
npm test -- tests/views/KnowledgeUI04.test.ts
npm test -- tests/views/ToolUI04.test.ts
npm test -- tests/views/OperationsConsole.test.ts
npm test -- tests/views/knowledge/KnowledgeWorkbench.test.ts
npm test -- tests/components/StatePanel.test.ts
npm test
npm run build
npm run test:gate
```

测试数据继续通过 Vitest mock 自动生成，不启动服务、不手工填写业务数据、不使用 `npx` 临时下载测试框架。

## 6. 下一步

在上述 targeted regression 全部通过后，继续 P1.1：Runtime Tab / 按需加载、Agent 调试上下文、Workflow 生命周期与真实 Execution 联动；避免继续扩张 UI-03 / UI-04 公共状态范围，优先把状态模式迁移到下一个核心真实业务页面。