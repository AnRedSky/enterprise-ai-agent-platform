# Phase 2.6 — Durable Execution Checkpoint Foundation

> 状态：**开发中**；Checkpoint 已接入 WorkflowExecutionService 的 Node completed 边界，Resume Candidate 已完成只读评估，Resume Execution 创建契约已落地；自动从 Checkpoint 继续执行尚未实现。
> 评估日期：2026-08-26
> 优先级：**P1**

## 1. 目标

在 Phase 2.5 已完成 Scheduler / Worker / Runtime 进程与 ownership 边界的基础上，为后续 durable execution 建立唯一 Checkpoint 持久化边界，并逐步形成安全的 Resume Execution 创建与运行边界：

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
后续 Durable Resume Runtime
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
- Resume Execution 继续复用标准 Worker pending claim，不自动抢 lease、不直接启动 Runtime；
- Checkpoint / Resume Contract targeted tests；
- Real API + PostgreSQL Checkpoint persistence 验收测试入口；
- Tenant Safe Real API Source Baseline Gate。

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

## 5. Checkpoint 负责

- 保存可恢复的业务状态快照；
- 保存 Node / Execution 当前状态上下文；
- 保存产生快照时的 Worker owner；
- 保留历史版本，支持后续恢复与审计。

## 6. Checkpoint 不负责

- 不自动把 `running` Execution 改回 `pending`；
- 不执行 Runtime；
- 不绕过 ownership fencing；
- 不修改 Node 状态机；
- 不决定 Retry / Circuit Breaker；
- 不实现 Saga / compensation；
- 不直接提供 HTTP Resume 接口。

## 7. Durable Resume 前置条件与创建契约

Resume Candidate 评估必须满足：

```text
WorkflowExecution.status == failed
        ↓
当前 worker_owner == None
        ↓
存在最新 Checkpoint
        ↓
checkpoint_reason == node.completed
        ↓
checkpoint.node_status == completed
checkpoint.execution_status == running
        ↓
固定原 Execution.workflow_version_id
        ↓
生成 resume:<execution_id>:checkpoint:<sequence>
        ↓
创建新的 pending Resume Execution
```

数据不变量：

1. Source Execution 永远保持 `failed`，不被 Resume 创建过程改写。
2. Resume Execution 必须固定 Source Execution 的 `workflow_version_id`，不得隐式漂移到新的 published version。
3. `resume_of_execution_id + resume_checkpoint_sequence` 必须指向唯一恢复来源事实。
4. `tenant_id + idempotency_key` 继续由数据库唯一约束兜底。
5. 同一 Source + Checkpoint 重复 Resume 请求必须收敛到同一个 pending Execution。
6. Resume 创建不获取 Worker ownership；Worker 仍从 `pending` 队列正常 claim。
7. 当前 Resume Execution 的 `input_data` 使用 Checkpoint `state_data`，作为后续 Runtime Resume 的唯一输入事实；当前 Runtime 仍不会读取该 Resume 元数据跳过已完成 Node。

## 8. 当前明确不实现

- 自动从 Checkpoint 继续执行；
- Runtime 根据 `resume_checkpoint_sequence` 跳过前置 Node；
- `running` Execution checkpoint recovery；
- Saga / compensation；
- HTTP Resume API；
- 绕过 Worker ownership fencing；
- 用 Checkpoint 替代 Node 状态机；
- Resume 创建后直接启动 Runtime。

## 9. Real API 源码基线与警告处理

Tenant Safe Real API Gate 在启动测试前运行 Source Baseline Gate，确认当前本地关键测试源码与远端 `main` 一致，并阻断旧测试实现导致的伪失败。

Checkpoint Resume Candidate 测试统一使用 timezone-aware UTC；当前阶段 targeted、完整 Backend Regression 与 Tenant Safe Real API 验收均应以开发者本地实际执行结果为准，不在文档预填测试结果。

## 10. 下一步

1. 增加 Resume Execution 的真实 PostgreSQL 持久化验收；
2. 固定 Worker 对 Resume Execution 的 claim / fencing 语义；
3. Runtime 增加从 Checkpoint 节点之后继续的确定性入口；
4. 完善跨多 Node DAG / 顺序执行的 Resume 状态重建；
5. 在上述边界稳定后再评估 HTTP Resume 与自动恢复。
