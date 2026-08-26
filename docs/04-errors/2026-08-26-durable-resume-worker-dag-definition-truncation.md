# Durable Resume Worker 提前裁剪 DAG Definition 导致真实恢复超时

## 发生时间

2026-08-26

## 现象

Durable Resume 的纯内存单元测试与 Backend Regression 均通过，但真实 PostgreSQL + 独立 Worker 的 Resume success acceptance 在等待 Resume Execution 完成时超时。

已观察到：

- Source Execution 能正常失败并生成 `node.completed` Checkpoint；
- Resume Execution 能正常创建为 `pending`，并固定 `resume_of_execution_id` 与 Checkpoint sequence；
- Worker 能成功领取 Resume Execution；
- Resume Execution 未能在真实验收窗口内进入 `completed`。

## 根因

Worker 的 `_prepare_resume_runtime()` 在进入 `WorkflowRuntime` 前调用顺序 Resume Planner，并将原始 Workflow Version 的 `definition["nodes"]` 替换为 Checkpoint 后的剩余 Nodes。

后续 `WorkflowRuntime._resolve_resume_nodes()` 又需要使用完整 DAG Definition 与 Source Execution 已完成 Node 集合重新计算当前 frontier。被提前裁剪的 Definition 已经不包含 Source Checkpoint 对应的 predecessor，例如：

```text
原始 DAG：prepare → provider-call
Source completed：prepare
Worker 提前裁剪后：provider-call
```

此时 Planner 收到 `completed_node_ids={prepare}`，但 `prepare` 已不属于被校验的 Definition，因此违反 DAG Resume Contract。Runtime 无法可靠判断 `provider-call` 是否是合法 frontier，最终导致 Resume Worker 执行链路不能正常完成。

## 修复

Worker 的 Resume 准备阶段职责收敛为：

1. 重新校验 Source Execution、Checkpoint、Worker ownership 与 Workflow Version；
2. 将 Checkpoint `state_data` 写入 Resume Execution 的 `input_data`；
3. **保留完整 Workflow Version Definition，不提前裁剪 Nodes**；
4. 由 `WorkflowRuntime` 使用 Source Node Execution 完成事实和完整 DAG Definition 计算真实 Resume frontier。

这样 Worker 不重复实现 DAG Resume Planner，也不会丢失 predecessor / branch Contract 所需的图上下文。

## 回归测试

新增 Worker 单元测试验证：

- Resume 输入状态来自 Checkpoint；
- Runtime Version 保留完整 DAG Definition；
- Source checkpoint node 不会因为 Worker 预裁剪而从 Definition 中消失。

真实验收仍必须使用：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\05_run_durable_resume_real_tests.ps1
```

该 Gate 要求开发者人工启动最新 API 与 Worker，不由测试脚本控制服务生命周期。

## 边界

本修复不扩大当前 Phase 2.6 的 DAG 分支能力。多个 frontier 仍由 Runtime 明确拒绝；当前只允许已经冻结状态合并 Contract 的单一 frontier 顺序恢复。