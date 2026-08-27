# Durable Frontier Checkpoint Continuation

## 问题

Durable Resume Runtime 已实现 completed Node 过滤与 Retry budget 恢复，但 `_resume_version()` 与 `_complete_if_all_nodes_resumed()` 仅作为辅助方法存在，未在 Runtime 主入口形成实际 continuation 闭环。

如果 Worker Recovery 进入 Resume Runtime 后仍直接把原始 Workflow Version 交给父 Runtime，已经成功持久化的 Node 仍可能被重新执行；如果所有 Node 已完成但 Execution 终态提交前发生 Worker Crash，也可能再次进入 Runtime。

## 修复边界

- Resume Runtime 主入口先恢复持久化 Retry budget。
- 线性 Workflow 在进入唯一 `WorkflowRuntime` 前应用 `_resume_version()`，过滤当前 Execution 已完成的 Node。
- 所有线性 Node 已完成时直接使用最后一个 durable Node output 完成 Execution，不重新执行 Node。
- DAG Workflow 不复制 Planner；继续由既有 DAG Planner / Executor 处理。
- Retry budget、Node attempt、Worker fencing generation 继续保持独立语义。

## 关键不变量

```text
completed Node fact
    ↓
Resume Runtime
    ↓
skip completed Node
    ↓
continue unfinished Node
```

```text
all linear Node facts = completed
    ↓
Execution → completed
    ↓
no Node replay
```

## 测试范围

本轮只新增/更新 Unit Test 实现，不执行 pytest。不得把未执行结果记录为 PASS。
