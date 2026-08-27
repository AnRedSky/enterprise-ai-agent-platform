# Phase 2.6 — Durable Execution Checkpoint Foundation

> 状态：**开发中**；Checkpoint、Resume Candidate 只读评估、Resume Execution 创建契约、Worker → Runtime 的第一版顺序 Resume 与 HTTP Resume API 已完成；真实 PostgreSQL + 独立 Worker 的 Durable Resume Acceptance 与 failure-after-resume Acceptance 已由开发者本地实际执行通过；DAG 分支 Resume、自动恢复尚未全部收口。
> 评估日期：2026-08-27
> 优先级：**P1**

## 1. 目标

在 Phase 2.5 已完成 Scheduler / Worker / Runtime 进程与 ownership 边界的基础上，为 durable execution 建立唯一 Checkpoint 持久化边界，并逐步形成安全的 Resume Execution 创建、HTTP 调用与运行边界：

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
HTTP Resume API
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
- Migration `0034_terminal_execution_releases_worker_lease`；
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
- 新增 Durable Resume Real API 测试模块已补充中文模块职责说明；
- DAG Resume Contract 第一版只接受单一 root；
- DAG Resume Planner 拒绝 predecessor 尚未完成的非闭包 completed facts；
- 单一 frontier Runtime 继续拒绝多个分支，直到状态合并 Contract 冻结；
- `POST /api/v1/workflows/executions/{execution_id}/resume`：通过正式 `WorkflowExecutionService.resume_from_latest_checkpoint()` 创建或幂等命中 Resume Execution；
- HTTP Resume API 只负责 tenant / actor 权限校验、读取 Source Execution、调用 Resume Domain Service 与响应组装，不直接抢 Worker lease、不直接启动 Runtime；
- Execution HTTP 响应补充 `resume_of_execution_id` 与 `resume_checkpoint_sequence`，让客户端可追踪恢复 lineage；
- `tests/unit/test_workflow_resume_api_contract.py`：验证 Resume API HTTP 方法、user/admin 权限契约、Domain Service 委托以及 lineage 响应字段；
- `WorkflowDagMultiFrontierExecutor`：确定性执行当前 Multi-frontier，要求所有 Branch Node Execution 与 Node-level Checkpoint 成功后才能 Join-ready；
- `WorkflowRuntime._execute_multi_frontier()`：在 Join-ready 后使用统一 Checkpoint Service 追加 Execution-level `frontier_completed` Checkpoint，保存 merged state，并继续执行 Worker ownership / fencing 校验；
- `tests/unit/test_workflow_runtime_frontier_checkpoint.py`：验证 Join-ready 的 frontier completion durable boundary 以及 Join 未就绪时不写入 Checkpoint。

## 3. Checkpoint 事务边界

Node 完成的正式边界为：

```text
Node pending/running
      ↓
WorkflowExecutionService.transition_node(..., completed)
      ↓
更新 Node 状态
      ↓
追加 sequence = max(sequence) + 1 的 Node-level Checkpoint
      ↓
flush
      ↓
同一 db.commit()
```

Multi-frontier 的正式边界进一步为：

```text
Branch A completed + Node Checkpoint
Branch B completed + Node Checkpoint
        ↓
WorkflowDagMultiFrontierExecutor
        ↓
all frontier Branch success
        ↓
Join-ready
        ↓
Execution-level frontier_completed Checkpoint
        ↓
继续 Planner / Next Frontier
```

因此禁止出现：

```text
Branch 全部 completed
Join-ready
frontier_completed Checkpoint 尚未建立
```

Checkpoint 服务在 Runtime 的 Multi-frontier 路径中不独立 `commit`，而是加入 Worker / Runtime 当前事务。

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

## 5. HTTP Resume API 边界

当前正式 HTTP Contract：

```text
POST /api/v1/workflows/executions/{execution_id}/resume
        ↓
user / admin authorization
        ↓
WorkflowExecutionService.get(...)
        ↓
WorkflowExecutionService.resume_from_latest_checkpoint(...)
        ↓
new pending Resume Execution
        ↓
Scheduler / Worker 正常领取
```

安全边界：

1. API 只能操作当前 tenant 内且当前用户有权访问的 Source Execution。
2. API 不接受客户端指定 Checkpoint sequence；恢复来源必须由正式 Resume Candidate assessment 决定。
3. API 不允许客户端修改 Resume Execution 的 `workflow_version_id`、`input_data`、ownership 或状态。
4. API 不直接调用 WorkflowRuntime；Resume Execution 必须重新进入标准 pending → Worker claim → Runtime 路径。
5. Resume 幂等键由 Domain Service 根据 Source Execution + Checkpoint sequence 确定性生成，客户端不能通过额外参数制造第二套 Resume 身份。
6. Source failed Execution 保持失败状态；API 返回的是新的 pending Resume Execution。
7. 响应返回 `resume_of_execution_id + resume_checkpoint_sequence`，用于客户端审计与 lineage 展示。

## 6. Runtime Resume 执行边界

当前 Runtime Resume 已扩展到多-frontier 的 Durable Checkpoint 边界：

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
Resume Planner / DAG Contract
        ↓
Multi-frontier Runtime Plan
        ↓
Branch state isolation
        ↓
每个 Branch 执行
        ↓
每个 Branch Node Checkpoint
        ↓
全部 Branch 成功
        ↓
Join-ready
        ↓
frontier_completed Execution-level Checkpoint
        ↓
下一 frontier / Join planning
```

安全边界：

1. 原 Source Execution 永不恢复成 `running`。
2. Resume Execution 仍必须从标准 Worker claim 路径进入 Runtime。
3. Planner 不复制 DAG 算法；DAG Contract / Frontier Planner 负责图结构与完成事实，Runtime Planner 负责 frontier 收敛。
4. Resume 使用原 Workflow Version 的内存快照，不修改数据库中的 published Version。
5. 每个并发 Worker Execution 使用自己的数据库 Session；不得通过 Worker 实例级属性保存“当前 Session”。
6. Resume 前重新核对 Source / Checkpoint，而不是仅相信 Resume Execution 创建时的 metadata。
7. `completed_node_ids` 必须形成从唯一 root 向下的 predecessor 闭包；否则拒绝恢复，避免把不可能由当前顺序 Runtime 产生的持久化事实当作合法输入。
8. Resume Execution 的 Node Execution 集合只记录真正重新执行的节点；源 Execution 的已完成节点不会复制成新的 Node Execution。
9. Multi-frontier Branch 必须使用独立 state snapshot，禁止 Branch 之间共享可变 state。
10. Join-ready 必须建立在所有 frontier Branch 执行成功且 Node-level Checkpoint 已完成的基础上。
11. `frontier_completed` 是 Execution-level Checkpoint，不携带 Node Fact；其 `state_data` 是经过既有 Branch State Merge Contract 验证的 merged state。
12. `frontier_completed` 写入继续执行 Worker owner / fencing generation 与 tenant scope 校验，并不绕过现有 Checkpoint Durable Write Contract。

## 7. Checkpoint 负责

- 保存可恢复的业务状态快照；
- 保存 Node / Execution 当前状态上下文；
- 保存产生快照时的 Worker owner；
- 保存 Multi-frontier 全部 Branch 完成后的 merged state；
- 以 Execution-level `frontier_completed` 记录 frontier 的 durable completion boundary；
- 保留历史版本，支持后续恢复与审计。

## 8. Checkpoint 不负责

- 不自动把 `running` Execution 改回 `pending`；
- 不执行 Runtime；
- 不绕过 ownership fencing；
- 不修改 Node 状态机；
- 不决定 Retry / Circuit Breaker；
- 不实现 Saga / compensation；
- 不直接启动 Resume Runtime；
- 不在没有全部 Branch Durable Checkpoint 的情况下声明 Join-ready。

## 9. Durable Resume 数据不变量

1. Source Execution 永远保持 `failed`，不被 Resume 创建过程改写。
2. Resume Execution 必须固定 Source Execution 的 `workflow_version_id`，不得隐式漂移到新的 published version。
3. `resume_of_execution_id + resume_checkpoint_sequence` 必须指向唯一恢复来源事实。
4. `tenant_id + idempotency_key` 继续由数据库唯一约束兜底。
5. 同一 Source + Checkpoint 重复 Resume 请求必须收敛到同一个 pending Execution。
6. Resume 创建不获取 Worker ownership；Worker 仍从 `pending` 队列正常 claim。
7. Resume Execution 的 `input_data` 使用 Checkpoint `state_data` 作为当前 Runtime 输入事实。
8. Worker 在实际执行前重新读取 Source / Checkpoint，防止恢复元数据与持久化事实漂移。
9. Resume 完成后的 Checkpoint sequence 在新的 Resume Execution 内重新从 `1` 开始，source lineage 由 `resume_of_execution_id + resume_checkpoint_sequence` 保留；禁止把两个 Execution 的 sequence 混写成单一序列。
10. DAG Resume Contract 的第一版 root 必须唯一；Planner 接收到的 completed facts 必须满足所有 predecessor 已完成。
11. HTTP Resume API 不改变上述 Domain 不变量，只提供受权限保护的调用入口。
12. Multi-frontier Join-ready 之前必须完成全部 Branch Node-level Checkpoint；否则 Runtime 不得推进到下一 frontier。
13. `frontier_completed` 必须为 Execution-level Checkpoint，且 state_data 必须是既有 Merge Contract 的确定性结果。

## 10. 当前明确不实现

- DAG 分支自动恢复的全自动 Recovery Policy 编排；
- running Execution checkpoint recovery；
- Saga / compensation；
- 自动恢复失败 Execution 的更高阶 backoff / DLQ 编排；
- HTTP API 直接启动 Runtime；
- 绕过 Worker ownership fencing；
- 用 Checkpoint 替代 Node 状态机；
- Resume 创建后直接启动 Runtime。

## 11. Real API 源码基线与服务版本

Tenant Safe Real API Gate 在启动测试前运行 Source Baseline Gate，确认当前本地关键测试源码与远端 `main` 一致。

Checkpoint / Resume / Worker Runtime 属于 API / Worker 进程内 Python 代码。代码更新后必须由开发者人工重启受影响的 API Service 与 Worker Service，再执行 Real API / Worker acceptance；Gate 不负责进程生命周期。

## 12. 下一步

1. 在本地仅执行新增 Resume / DAG Runtime / frontier checkpoint targeted unit tests，确认当前主线代码单元测试通过；
2. 暂停完整 Backend / Frontend / Browser / Real API 验收流程，不以其作为当前开发推进门槛；
3. 继续实现 Durable Resume 后续主线：多-frontier Resume 的下一 frontier 持久化事实与 terminal boundary 收口；
4. 自动恢复继续沿现有 Recovery Policy / ownership / lease / retry 上限 Contract 演进；
5. DAG 分支自动恢复必须继续复用现有 Planner / Merge / Checkpoint Contract，不创建平行实现。
