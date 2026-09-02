# Scheduler Runtime：Scheduled Trigger 绕过 Workflow Definition 发布契约

日期：2026-09-02

## 现象

开发者直接运行 Scheduler Runtime 时，已有数据库中的 Scheduled Trigger 反复出现：

```text
HTTPException: 422: Workflow definition 必须包含 nodes 数组
```

此前仅修正 Acceptance fixture 后，不能解决真实运行态中的该错误。

## 根因

`WorkflowRegistry.publish()` 对新的 draft/testing → published 状态迁移使用严格的 `WorkflowRuntime.validate_definition()`，因此新的发布版本必须包含合法且非空的 `nodes` 数组。

但 `WorkflowTriggerService.invoke_scheduled()` 原先调用：

```python
WorkflowRuntime.validate_definition(
    version.definition,
    allow_legacy_empty_nodes=True,
)
```

这使 Scheduled Trigger 与 Workflow 发布契约出现两个不同的 Definition Contract：调度入口允许空节点/历史兼容定义，而正式发布入口不允许。更严重的是，直接绕过发布阶段写入数据库的历史非法 published version 会在 Scheduler 每次 tick 中进入派发路径并持续失败。

这不是测试 fixture 问题，而是后端业务边界不一致：**Scheduler 不得通过兼容参数绕过已经由 Workflow Registry 定义的可执行 Workflow Contract。**

## 修复

1. `WorkflowTriggerService.invoke_scheduled()` 改为直接调用：

```python
nodes = WorkflowRuntime.validate_definition(version.definition)
```

不再为 Scheduled Trigger 提供 `allow_legacy_empty_nodes=True` 的旁路。

2. Scheduler Runtime PostgreSQL Acceptance fixture 改为真正满足发布契约的最小 `input` 节点：

```python
{"nodes": [{"id": "scheduled-input", "type": "input", "config": {}}]}
```

3. 保留 `WorkflowRegistry.publish()` 的严格发布校验，使新非法 Definition 无法通过正式业务入口进入 published 状态。

## 为什么不能继续兼容空节点

Scheduled Trigger 创建的是 pending Workflow Execution 和 Durable Frontier。Frontier 的 node identity 必须来自正式 Workflow Definition；允许空节点会产生无法由 Worker Runtime 执行的任务，破坏 `WorkflowVersion → Execution → Frontier → Runtime` 的单一契约。

历史数据库中已经存在的非法 published 数据不应继续作为合法业务输入。修复代码后，这类数据会被严格校验拒绝，而不是由 Scheduler 创建新的非法 Execution。

## 验证

Targeted Unit：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run pytest -q -W error tests/unit/services/workflow_scheduler/test_misfire.py
```

Scheduler Runtime Real PostgreSQL Acceptance：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.4\22_scheduler_runtime_gate.ps1
```

本地实际结果必须由开发者执行后反馈；在获得新结果前不得标记 Runtime Gate 通过。

## 预防规则

- 同一业务能力只能存在一个正式 Definition Contract。
- Trigger、Scheduler、Worker 不得通过兼容参数绕过 Workflow Registry 的发布约束。
- Acceptance fixture 必须构造真实可发布的最小 Workflow Definition，而不是通过兼容开关让无效 fixture 通过。
- 对历史脏数据只能提供明确的迁移/修复路径，不得把脏数据兼容逻辑扩散到新的业务入口。
