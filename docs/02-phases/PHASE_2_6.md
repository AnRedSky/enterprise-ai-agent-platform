# Phase 2.6 — Durable Execution Checkpoint Foundation

> 状态：**开发中**；Checkpoint、Resume Candidate 只读评估、Resume Execution 创建契约以及 Worker → Runtime 的第一版顺序 Resume 已完成；真实 PostgreSQL + 独立 Worker 的 Durable Resume Acceptance 与 failure-after-resume Acceptance 已由开发者本地实际执行通过；DAG 分支 Resume、自动恢复尚未实现。
> 评估日期：2026-08-26
> 优先级：**P1**

## 1. 目标

在 Phase 2.5 已完成 Scheduler / Worker / Runtime 进程与 ownership 边界的基础上，为 durable execution 建立唯一 Checkpoint 持久化边界，并逐步形成安全的 Resume Execution 创建与运行边界：

```text
Worker claim / ownership fencing
        ↓
WorkflowExecutionService
        ↓
Node transition
        ↓
Checkpoint Service
        ↓
PostgreSQL immutable checkpoint
        ↓
Resume Candidate assessment
        ↓
Resume Execution creation contract
        ↓
Worker claim / lease
        ↓
Resume Planner
        ↓
WorkflowRuntime（从 checkpoint node 之后继续）
```

Checkpoint 是持久化事实；Resume Execution 是新的 pending 任务，不复活原 failed Execution，也不绕过 Worker ownership。

## 2. 当前实现

- Migration `0032_workflow_execution_checkpoint`；
- Migration `0033_workflow_execution_resume_contract`；
- `WorkflowExecutionCheckpoint` 持久化模型；
- `WorkflowExecutionCheckpointService.append()`；
- `WorkflowExecutionCheckpointService.append_next_in_transaction()`；
- `WorkflowExecutionCheckpointService.latest()`；
- `Node completed` 时自动追加 Checkpoint；
- Node 状态更新与 Checkpoint 追加在同一个数据库事务内提交；
- Execution 内唯一 `sequence`；
- Checkpoint 只追加、不覆盖历史快照；
- `WorkflowExecutionCheckpointRecoveryService`：只读 Resume Candidate 评估；
- `WorkflowExecutionService.resume_from_latest_checkpoint()`：在安全边界满足后创建新的 `pending` Resume Execution；
- Resume Execution 固定原 `workflow_version_id`；
- Resume Execution 持久化 `resume_of_execution_id + resume_checkpoint_sequence` 来源关系；
- Resume Execution 使用 `resume:<execution_id>:checkpoint:<sequence>` 确定性幂等键；
- 重复 Resume 请求命中同一幂等键时返回同一 pending Execution；
- Source Execution 保持 `failed`，不被改写为 `pending` / `running`；
- `WorkflowExecutionResumePlanner`：纯内存生成 Checkpoint 之后的顺序节点计划；
- Worker 对 Resume Execution 在正式 Runtime 前重新读取 Source / Checkpoint，并固定原 Workflow Version；
- Resume Execution 的 `input_data` 使用 Checkpoint `state_data`；
- Runtime 第一版只执行 checkpoint 节点之后的 `nodes` 顺序；
- Resume Planner 不持有数据库 Session，不执行 Runtime，不修改状态机；
- Worker 每个并发 Execution 显式传递自己的数据库 Session，不在 Worker 实例上共享 Session；
- Checkpoint / Resume / Planner targeted tests；
- Real API + PostgreSQL Checkpoint persistence 验收测试入口；
- `tests/api_real/test_workflow_resume_api.py`：以真实 HTTP 创建 Source Execution，以真实 PostgreSQL 检查 Checkpoint，再通过正式 Domain Service 创建 Resume Execution，并由人工启动的独立 Worker 执行恢复；
- `tests/api_real/test_workflow_resume_failure_api.py`：真实 HTTP + PostgreSQL + 独立 Worker 验证 Resume failure-after-resume 后的 lineage / terminal / Checkpoint / ownership 边界；
- `scripts/test/api-real/03_run_durable_resume_acceptance.ps1`：只验证外部 API / Worker 前置条件，不启动、停止或重启任何服务；
- `scripts/test/api-real/04_run_durable_resume_failure_acceptance.ps1`：只验证外部 API / Worker 前置条件，不启动、停止或重启任何服务；
- Tenant Safe Real API Source Baseline Gate；
- 新增 Durable Resume Real API 测试模块已补充中文模块职责说明。

## 3. Checkpoint 事务边界

Node 完成的正式边界为：

```text
Node pending/running
      ↓
WorkflowExecutionService.transition_node(..., completed)
      ↓
更新 Node 状态
      ↓
追加 sequence = max(sequence) + 1 的 Checkpoint
      ↓
flush
      ↓
同一 db.commit()
```

因此禁止出现：

```text
Node completed 已提交
Checkpoint 尚未提交
```

Checkpoint 服务在该路径中不独立 `commit`，而是加入调用方当前事务。

## 4. Resume Execution 创建事务边界

当前阶段 Resume 的正式边界为：

```text
failed Source Execution
        ↓
lock Source Execution
        ↓
latest Checkpoint
        ↓
Resume Candidate assessment
        ↓
固定原 Workflow Version
        ↓
生成确定性 resume idempotency key
        ↓
创建新的 pending Resume Execution
        ↓
记录 source Execution / checkpoint sequence
        ↓
写 Resume audit / trace
        ↓
commit
```

明确禁止：

```text
Source failed
   ↓
直接改 pending
   ↓
直接改 running
```

以及：

```text
Resume creation
   ↓
绕过 Worker claim
   ↓
直接 WorkflowRuntime.execute()
```

## 5. Runtime Resume 执行边界

第一版 Runtime Resume 只覆盖当前 Runtime 已明确实现的顺序执行模型：

```text
Resume Execution pending
        ↓
Worker claim + ownership fencing
        ↓
读取 Source Execution
        ↓
读取指定 checkpoint.sequence
        ↓
校验 source failed / worker_owner == None
        ↓
校验 checkpoint = node.completed + execution=running
        ↓
校验原 workflow_version_id 未漂移
        ↓
Resume Planner 找到 checkpoint.node_id
        ↓
丢弃 checkpoint node 及其之前的 nodes
        ↓
Checkpoint.state_data 作为 current_data
        ↓
只执行剩余 nodes
        ↓
Resume Execution 自己重新生成 Checkpoint
```

安全边界：

1. 原 Source Execution 永不恢复成 `running`。
2. Resume Execution 仍必须从标准 Worker claim 路径进入 Runtime。
3. Planner 不复制 DAG 算法；当前只按 `nodes` 数组顺序确定恢复起点。
4. 当前不声明支持 DAG 分支恢复。未来 DAG Runtime 必须提供独立的图恢复规划器。
5. Resume 使用原 Workflow Version 的内存快照，不修改数据库中的 published Version。
6. 每个并发 Worker Execution 使用自己的数据库 Session；不得通过 Worker 实例级属性保存“当前 Session”。
7. Resume 前重新核对 Source / Checkpoint，而不是仅相信 Resume Execution 创建时的 metadata。
8. Resume Execution 的 Node Execution 集合只记录真正重新执行的剩余节点；源 Execution 的已完成节点不会复制成新的 Node Execution。

## 6. Checkpoint 负责

- 保存可恢复的业务状态快照；
- 保存 Node / Execution 当前状态上下文；
- 保存产生快照时的 Worker owner；
- 保留历史版本，支持后续恢复与审计。

## 7. Checkpoint 不负责

- 不自动把 `running` Execution 改回 `pending`；
- 不执行 Runtime；
- 不绕过 ownership fencing；
- 不修改 Node 状态机；
- 不决定 Retry / Circuit Breaker；
- 不实现 Saga / compensation；
- 不直接提供 HTTP Resume 接口。

## 8. Durable Resume 数据不变量

1. Source Execution 永远保持 `failed`，不被 Resume 创建过程改写。
2. Resume Execution 必须固定 Source Execution 的 `workflow_version_id`，不得隐式漂移到新的 published version。
3. `resume_of_execution_id + resume_checkpoint_sequence` 必须指向唯一恢复来源事实。
4. `tenant_id + idempotency_key` 继续由数据库唯一约束兜底。
5. 同一 Source + Checkpoint 重复 Resume 请求必须收敛到同一个 pending Execution。
6. Resume 创建不获取 Worker ownership；Worker 仍从 `pending` 队列正常 claim。
7. Resume Execution 的 `input_data` 使用 Checkpoint `state_data` 作为当前 Runtime 输入事实。
8. Worker 在实际执行前重新读取 Source / Checkpoint，防止恢复元数据与持久化事实漂移。
9. Resume 完成后的 Checkpoint sequence 在新的 Resume Execution 内重新从 `1` 开始，source lineage 由 `resume_of_execution_id + resume_checkpoint_sequence` 保留；禁止把两个 Execution 的 sequence 混写成单一序列。

## 9. 当前明确不实现

- DAG 分支自动恢复；
- running Execution checkpoint recovery；
- Saga / compensation；
- HTTP Resume API；
- 绕过 Worker ownership fencing；
- 用 Checkpoint 替代 Node 状态机；
- Resume 创建后直接启动 Runtime；
- 自动恢复失败 Execution。

## 10. Real API 源码基线与服务版本

Tenant Safe Real API Gate 在启动测试前运行 Source Baseline Gate，确认当前本地关键测试源码与远端 `main` 一致。

Checkpoint / Resume / Worker Runtime 属于 API / Worker 进程内 Python 代码。代码更新后必须由开发者人工重启受影响的 API Service 与 Worker Service，再执行 Real API / Worker acceptance；Gate 不负责进程生命周期。

## 11. 下一步

1. 冻结 Phase 2.6 DAG Resume Runtime 恢复 Contract（GitHub Issue #49），明确 edge、frontier、分支/汇聚、状态合并、失败、幂等与拓扑安全边界；
2. Contract 冻结后，实现纯内存 DAG Resume Planner，并先补齐单元测试；
3. 将 Planner 接入 Runtime，建立 DAG integration 与 failure boundary；
4. 执行真实 PostgreSQL + 独立 Worker 的 DAG Resume Acceptance；
5. DAG 恢复安全边界稳定后，再评估 HTTP Resume API；
6. 自动恢复仅在上述 ownership、checkpoint、planner、终态与 DAG 边界稳定后进入设计。
