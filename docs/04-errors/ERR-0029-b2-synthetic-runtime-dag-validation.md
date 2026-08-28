# ERR-0029 — B2 Synthetic Runtime 被 DAG Contract 错误拦截

## 1. 现象

Phase 2.8 B2 Real HTTP + PostgreSQL Worker Execution Bridge 在开发者本地 Gate 的 `[4/4]` 失败：

```text
ValueError: DAG Workflow 必须包含非空 edges
fastapi.exceptions.HTTPException: 422: DAG Workflow 必须包含非空 edges
```

失败位置为 `DurableResumeWorkflowRuntime.validate_definition()`，触发原因是 B2 Runtime Bridge 构造的临时 Definition 同时包含单个 synthetic agent Node 与 `edges: []`。

## 2. 根因

`WorkflowDagContractValidator` 的约束是：只要 Definition 存在 `edges` 字段，就必须存在非空 edges，并进一步执行 DAG 拓扑校验。

B2 Bridge 的 Runtime Version 是一次 Worker Execution 内存对象，只包含一个已经由 B1 Claim 后确定的 target Agent Node，并不是新的持久化 Workflow DAG。为满足现有 `WorkflowRuntime` 的单 Node 执行能力，Definition 不应声明空 DAG edges。

此前 Bridge 为保持 Definition 形状显式生成了 `edges: []`，导致 DAG validator 将这个一次性单 Node Runtime 错误识别为需要完整 DAG Contract 的 Definition。

## 3. 修复

`AgentDelegationRuntimeBridge.build_runtime_version()` 改为：

- 保留单个 `delegation.target` synthetic agent Node；
- 保留 Delegation target agent version、model profile、input、context refs、allowed tools、trace identity；
- 不写入 `edges` 字段；
- 不伪造 terminal edge 或 self-loop；
- 不修改父 WorkflowVersion 数据库 Definition。

该方案复用既有 `WorkflowRuntime` 的单 Node 能力，不创建第二套 DAG Runtime，也不改变持久化 Workflow Contract。

## 4. 预防

B2 Bridge Unit 必须同时验证：

1. synthetic Definition 只包含目标 Agent Node；
2. Definition 不包含 `edges`；
3. `DurableResumeWorkflowRuntime.validate_definition()` 可以直接接受该 Definition；
4. 父 Workflow Definition 保持不变。

Real Gate 必须继续验证真实 HTTP + PostgreSQL Claim + Worker Runtime 执行链路。

## 5. 验证边界

代码修复已直接提交 `main`，并新增对应 Unit 回归断言；本记录不将本地验证结果预填为通过。开发者必须在同步最新 `main` 后重新执行 B2 Gate，只有 `[4/4]` 实际返回 `1 passed` 才可将 B2 Real Runtime 标记为通过。
