# Phase 2.7 本地回归：Retry 耗尽治理事实与 DAG Root State 回归

## 1. 发现时间

2026-08-28

## 2. 发现来源

开发者本地执行 Backend Unit Regression：

```powershell
cd backend
uv run pytest -q tests/unit
```

实际结果：`94 failed, 622 passed, 2 warnings`。

此前针对 Workflow Retry / Timeout / Runtime 的定向执行结果为：`5 failed, 14 passed`。

## 3. 本轮已确认的生产问题

### 3.1 Retry Budget / Workflow Deadline 缺少最终治理事实

基础 Runtime 已经正确停止 Retry，并向上抛出原始错误或 `WORKFLOW_TIMEOUT`，但 DAG Runtime 扩展入口没有在 Retry Budget 或 Retry Backoff 跨越 Workflow Deadline 时补齐：

- Trace：`node.retry.exhausted`
- Audit：`workflow.node.retry_exhausted`
- `data.reason = retry_budget | workflow_deadline`

因此调用方可以观察到 Execution failed，却无法在治理 Trace 中得到“为什么停止继续 Retry”的确定性事实。

### 3.2 DAG 单根首次执行不应创建 Branch State

首次 DAG 执行只有一个 root frontier 时，基础 Runtime 的普通 `state_data` 已足够作为 root Node 输入，不应额外构造单 root `branch_state_data`。

Branch State 只在首次执行存在多个 root frontier 时创建；Resume 场景则根据已完成 predecessor state 恢复独立 Branch State。

## 4. 修复

- 在 `backend/app/runtime/workflow/dag_runtime.py` 中复用基础 Runtime 的 Retry 实现，不复制 Retry 算法；仅增加耗尽治理事实补充层。
- Retry Backoff 超过 Workflow Deadline 时记录 `workflow_deadline` 与 `WORKFLOW_TIMEOUT`。
- Workflow Retry Budget 已达到上限时记录 `retry_budget`。
- DAG 首次执行仅在 multi-root frontier 时初始化 Branch State；single-root 保持空 Branch State。

## 5. 尚未结案的问题

本次 `tests/unit` 的其余失败大量表现为测试 double / fake DB / mock contract 与当前 Durable Frontier、Resume、Checkpoint、tenant scope、worker fencing 等生产 Contract 不一致，包括：

- `WorkflowNodeExecution.tenant_id` 不存在但旧测试仍直接引用；
- Async SQLAlchemy `execute()` / result mock 层级不匹配；
- Resume / Recovery Service 新增 `tenant_id`、`commit` 等参数后旧 fake service 未同步；
- Frontier terminalization、duplicate completion、checkpoint source binding 等测试仍按旧 Contract 构造数据；
- DAG Contract 已要求 edges 的测试仍使用旧的空 edges / 单节点定义；
- Condition evaluator、DAG join state、frontier identity 等测试仍存在旧断言。

这些问题不能通过放宽生产 Contract 或增加兼容垫片解决；后续应按当前正式 Domain Contract 更新测试 double、fixture 和断言，并逐层重新执行 Unit → Integration → API Contract。

## 6. 验证状态

本记录只记录已实际反馈的本地结果；本轮远端环境无法代替开发者本地运行 pytest，因此修复提交后的最终 PASS/FAIL 必须继续以本地实际执行结果为准。
