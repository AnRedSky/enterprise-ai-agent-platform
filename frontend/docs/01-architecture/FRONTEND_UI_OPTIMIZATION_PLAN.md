# 前端 UI 优化与测试可靠性计划

> 基线：2026-08-30 `main`（commit `1965e769cac8657564e3cc31781ce3b71293570e`）。
>
> 本文记录本轮前端交付的设计决策、当前实现状态、测试问题根因以及后续长期优化路线。后端 Contract 仍是前后端唯一业务契约。

## 1. 本轮基线审阅结论

当前前端已经覆盖企业平台核心工作台：仪表盘、智能体、工具、知识库、工作流、Workflow Trigger、运行记录、组织与成员、模型提供方 / 模型配置、审计日志等领域。当前 main 的核心 UI 已经具备中文业务文案、技术标识保留、运行生命周期操作、Retry / Resume、Trigger → Execution → Trace → Audit 关联以及组织权限控制等能力。

本地反馈中的失败主要不是后端 Contract 不匹配，而是 Vitest 测试桩与异步断言存在两个系统性问题：

1. 测试在“API mock 已被调用”时立即读取 DOM，但 Vue 状态更新发生在 mock Promise resolve 之后，因此存在竞态。
2. 多个 `el-table-column` 测试桩完全丢弃 `label` 和 scoped slot，导致生产页面已经存在的业务文案无法出现在测试 DOM 中。
3. Runtime 测试缺少 `el-date-picker` 测试桩，产生无意义的 Vue unresolved-component warning。
4. 部分 `el-alert` / `el-dialog` 测试桩没有渲染 `title`，使用户可见错误和弹窗标题无法被 DOM 断言覆盖。

因此本轮优先修复测试基础设施和测试时序，而不是修改已经正确实现的生产业务逻辑，避免为了迎合错误测试桩而向生产代码加入重复或隐藏文本。

## 2. UI 设计决策

### 2.1 业务中文、技术标识双层表达

用户可见文本统一采用中文；状态、类型、事件、错误代码等后端枚举继续保留技术值，并采用“中文说明（technical_value）”形式展示未知值。这样既保证企业用户可理解，也保证排障时可以直接定位后端 Contract。

### 2.2 Runtime 采用真实关联，不做推断

运行记录页面遵循后端返回的真实 `retry_of_execution_id`、`resume_of_execution_id`、Trigger ID、Trace `data.trigger_id` 等字段。前端不得根据名称、时间或唯一记录数量猜测 Trigger 或父子 Execution 关系。

### 2.3 错误信息安全降级

用户界面不得直接暴露原始 HTTP 异常、Provider 异常或后端堆栈。界面展示稳定的中文提示；能够安全识别的错误代码继续保留，用于排障和审计。

### 2.4 生命周期操作保持后端语义

工作流和智能体页面的发布、归档、取消、Retry、Durable Resume 等按钮只调用后端已经存在的正式 API，不在前端复制状态机或推导非法状态转换。

## 3. 本轮实现范围

- 新增可复用的 Element Plus 表格测试桩，保留表头、普通字段和 scoped slot。
- 修正 Runtime `el-date-picker` 测试桩缺失问题。
- 将涉及异步加载的 UI 断言改为等待业务状态稳定，而不是仅等待 API mock 被调用。
- 将 Runtime 关系、审计、Retry / Resume 断言绑定到真实 view-model 数据，同时保留用户可见文案测试。
- 修正 Agent、Organization、Organization Detail、Workflow、Dashboard、Model Provider 页面测试中的异步竞态与测试桩丢失问题。
- 保持生产页面现有后端 Contract 调用方式，不新增平行 API 或重复业务逻辑。

## 4. 自动化测试 Gate

### Frontend 回归

```powershell
cd frontend
npm test
npm run build
```

### 官方 Frontend Release Gate

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

### Browser E2E

组织与 Workflow Trigger 场景使用项目已有 E2E Gate，不与 Frontend regression 合并：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\02_run_organization_e2e.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

## 5. 手动验证流程

1. 确认 `main` 工作区干净并同步最新远端代码。
2. 在 `frontend` 执行 `npm install`（依赖未安装时）。
3. 启动已经由开发者准备好的真实 Backend 服务，不由 Frontend Gate 自动启动。
4. 执行 `npm test`，确认所有 Vitest 通过且无 unresolved component warning。
5. 执行 `npm run build`，确认 TypeScript 与 Vite production build 通过。
6. 启动 Frontend 开发服务，按业务顺序人工验证：登录 → Dashboard → 组织 → 模型提供方 → 智能体 → 工作流 → Trigger → Runtime → Audit。
7. 重点检查真实后端返回数据下的空状态、加载态、错误态、未知状态、发布 / 归档边界、Retry / Resume、取消以及 Trigger / Execution / Trace / Audit 关联。
8. 最后分别执行 Frontend Gate 与需要的 Browser E2E Gate，并记录真实执行结果；未执行项不得标记为通过。

## 6. 长期优化路线

### P0：稳定性与契约一致性

- 将所有页面的 loading / empty / error / stale-data 状态统一为可复用 UI 状态模式。
- 建立 API Contract → TypeScript 类型 → ViewModel → UI 的追踪矩阵。
- 统一错误码映射和用户提示策略，禁止页面自行复制错误判断。
- 继续消除测试桩对 Element Plus 内部实现的依赖。

### P1：企业级工作台体验

- Dashboard 增加按组织、智能体、工作流和时间窗口的真实指标筛选。
- Runtime 升级为“概览 → 时间线 → Trace → Audit → 关系 Execution”的可折叠诊断工作台。
- Agent 对话调试增加流式输出、取消、失败重试和运行上下文一体化展示。
- Workflow 编辑、版本、发布、运行和恢复形成连续生命周期工作流。

### P2：治理与权限体验

- 所有组织级页面统一显示当前组织上下文。
- 对 owner / admin / member 权限采用统一前端能力矩阵，但最终权限仍以后端鉴权为准。
- 审计日志增加从资源 ID、Execution ID、Trace ID 反向跳转到 Runtime 的能力。

### P3：可观测性与性能

- 大列表统一分页、服务端过滤、虚拟滚动策略。
- Runtime Trace / Audit 按需加载，避免打开详情时一次性请求无关数据。
- 对 Dashboard 与 Runtime 高频查询增加缓存失效和刷新策略。
- 统一请求取消、重复请求去重和页面离开后的异步任务清理。

### P4：质量工程

- Vitest 覆盖所有状态机边界与 Contract 映射。
- Playwright 覆盖组织权限、Workflow Trigger、Agent 调试、Runtime Retry / Resume 主路径。
- 建立可重复的本地手动验收清单，并与 `frontend/docs` 中的功能文档保持同步。

## 7. 交付原则

本轮提交保持单一原子提交：测试基础设施、受影响测试修复以及本设计记录属于同一项“前端回归稳定性与 UI Contract 验证”交付单元。后续独立 UI 功能应继续以单一业务能力为原子提交，不拆分成仅文档或仅测试的中间提交。
