# 工程错误：Node Timeout 测试窗口被 Workflow Deadline 抢占

## 1. 发现时间

2026-09-04

## 2. 问题现象

Backend Regression 在 `tests/unit/test_workflow_runtime_timeout.py::test_run_marks_workflow_timeout_as_failed` 失败：

- 期望 Node `error_code = NODE_TIMEOUT`
- 实际得到 `error_code = WORKFLOW_TIMEOUT`

本地反馈：`1056 passed, 10 skipped, 80 deselected, 1 failed`。

## 3. 根因

生产 Runtime 同时存在两层超时语义：

1. Node timeout：单个节点允许执行的最大时间。
2. Workflow deadline：整个 Workflow 从开始到结束允许使用的最大时间。

原测试同时配置 `Workflow timeout = 10ms`、`Node timeout = 1ms`，并让被测节点休眠 50ms。虽然意图是验证 Node timeout，但测试执行本身包含状态转换、Mock 调用与 Runtime 编排开销；进入 `asyncio.wait_for()` 时，Workflow 剩余时间可能已经下降到 Node timeout 以下。此时 Runtime 正确把本次超时解释为 Workflow deadline，而不是 Node timeout。

因此问题不是生产代码错误，而是测试夹具没有为两种超时语义提供稳定且互斥的时间窗口，导致时间敏感测试依赖自然执行开销。

## 4. 修复

将 Node timeout 测试调整为：

- Workflow timeout：1000ms
- Node timeout：10ms
- 模拟 Node 执行：50ms

这样为 Node timeout 留出明显余量，同时仍远低于 Workflow deadline，确保测试稳定验证 `NODE_TIMEOUT`。

Workflow deadline 分支继续由独立测试使用 10ms Workflow timeout + 30000ms Node timeout 验证。

## 5. 防回归原则

时间敏感测试必须显式构造相互独立的时间窗口：

- 验证 Node timeout：`workflow_timeout >> node_timeout`，并保证模拟执行时间明显超过 node timeout。
- 验证 Workflow deadline：`node_timeout >> workflow_timeout`，并保证模拟执行时间明显超过 workflow deadline。
- 不依赖自然时间流逝或极小的毫秒级差值区分两个分支。

该修复不修改生产超时分类逻辑，只修正测试对既有 Contract 的表达。

## 6. 验证命令

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run pytest -q -W error tests/unit/test_workflow_runtime_timeout.py -s
uv run pytest -q -W error
```

上述命令必须以开发者本地实际执行结果作为最终验收依据；本记录不预填通过结果。
