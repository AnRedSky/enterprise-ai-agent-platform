# Phase 2.10-II：Execution / Invoke 内部提交边界

## 1. 问题

`WorkflowExecutionService.create()` 与 `transition()` 原先在领域方法内部直接 `commit()`。Manual Trigger `invoke()` 依赖 `create()` 的隐式提交后再写 Trigger Audit，导致 Execution 创建事实与后续 Operator/Trigger 审计无法由同一个事务边界统一控制。

## 2. 根因

领域服务同时承担了“状态变更”和“事务提交”两个职责。调用方无法表达：本次状态变更需要继续参与上层 Operator Action 事务。

## 3. 修复

- `WorkflowExecutionService.create(..., commit=True)`：默认行为保持兼容；`commit=False` 时仅 flush 并保留当前事务。
- `WorkflowExecutionService.transition(..., commit=True)`：增加事务提交控制。
- `WorkflowExecutionService.cancel(..., commit=True)`：向下传递事务控制。
- `WorkflowExecutionService.run(..., commit=True)`：状态转换支持由调用方控制提交边界。
- Manual Trigger `invoke()` 使用 `create(..., commit=False)`，随后在 Runtime 启动前显式完成 Execution + Trigger Audit + Trace 的一次提交。

## 4. 边界说明

Runtime 执行本身仍允许产生独立 Durable Node/Checkpoint 提交；该持久化边界属于 Worker Runtime 的运行事实，不应与 Operator Action 的“创建/治理事实事务”混为一谈。后续若需要全 Runtime 单事务，必须同步改造 Runtime/DAG/Checkpoint 的提交协议，不能通过简单移除单个 `commit()` 实现。

## 5. 验证要求

本次变更提交后必须在本地执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
$env:RUN_DATABASE_INTEGRATION = "1"
uv run pytest -q -W error tests/unit tests/integration -m "unit or integration" --tb=long
```

随后执行 Phase 2.10 Operator Governance Gate 与完整 Backend Regression。未获得实际运行输出前，不将结果标记为通过。
