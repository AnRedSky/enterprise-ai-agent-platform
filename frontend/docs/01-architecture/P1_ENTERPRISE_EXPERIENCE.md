# P1 前端企业级体验深化

> 基线：2026-08-30 远端 `main`，commit `dbe1febb5e6584e6a3b23b00539f5e330edff255`。

## 本次目标

本轮不重复实现已有 Backend Contract，而是在现有功能之上强化三个连续工作流：

1. **Runtime 可观测性工作台**：进入运行中心前先展示最近 Execution 健康概览，并提供失败 / 进行中 / 已完成的快速诊断入口。
2. **Agent 对话调试**：明确调试不是孤立聊天，而是“发布版本 → 对话 → 请求/会话/Trace/Execution → 运行中心”的连续诊断路径。
3. **Workflow 生命周期**：以草稿 → 版本 → 发布 → 运行 → 恢复的生命周期视图辅助用户理解已有后端状态机，并从 Trigger / Runtime 继续操作。

## 设计决策

### Runtime

- 概览使用真实 `/runtime/executions` 数据，不复制后端统计逻辑。
- 指标仅计算当前拉取窗口中的 Execution；页面仍以运行中心的服务端分页数据为准。
- 失败指标直接进入运行中心，继续使用既有 Execution → Trace → Audit 诊断链路。

### Agent

- 保留现有真实流式对话、Abort、请求标识、链路追踪标识、会话标识和执行标识。
- 新增调试上下文说明与运行中心入口，不复制 Chat API。
- 发布版本仍是进入对话调试的前置条件。

### Workflow

- 生命周期面板不改变状态机，也不自行调用 Workflow API。
- Trigger 和 Runtime 使用现有路由作为正式操作入口。
- 阶段展示允许通过 `lifecycle` 查询参数表达外部上下文，默认展示草稿阶段。

## 响应式与交互

- Runtime / Agent 面板在窄屏下自动转为双列 / 单列布局。
- Workflow 生命周期面板采用固定诊断卡，避免改变现有大型工作流页面布局；移动端压缩为单列。
- 所有新增操作均为导航或现有能力入口，不引入平行 API。

## 验证要求

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

重点回归：

- Runtime 原有 Retry / Resume、Trigger → Execution → Trace → Audit。
- Agent 原有发布、对话流式输出、停止生成、错误降级。
- Workflow 原有版本、发布、执行、取消、Retry、Resume、Trace 与 Audit。

> 本次代码提交必须保持为单一原子提交；本地 Gate 未实际执行前，不将其记录为通过。

## 后续 P1.1

- Runtime：详情抽屉拆分为概览 / 时间线 / Trace / Audit 标签页，并实现按需加载。
- Agent：增加多轮会话上下文、重新生成、复制响应、Token / 延迟摘要，并把执行详情与 Runtime 深链路关联。
- Workflow：增加当前版本时间轴、发布确认差异、Trigger 状态摘要以及执行结果深链路。
- 三者统一请求取消、刷新状态、错误码展示和权限能力矩阵。
