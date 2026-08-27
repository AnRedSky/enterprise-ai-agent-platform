# Phase 2.6 — Durable Execution Checkpoint Foundation Acceptance

## 1. 验收目标

验证 Durable Execution 已形成完整的 Checkpoint、Resume、Automatic Recovery、Scheduler、Worker ownership、lease reclaim、fencing 与 lease-loss active-abort 闭环，并保持所有恢复动作通过正式 Domain / Service / Runtime 边界执行。

```text
Scheduler Scan
    ↓
Recovery Policy / Domain
    ↓
Resume Execution
    ↓
Worker claim / lease / ownership fencing
    ↓
WorkflowRuntime
    ↓
DAG Resume Planner
    ↓
Branch / Join execution
    ↓
PostgreSQL immutable Checkpoint
    ↓
Recovery Trace Link
```

核心原则：Resume 创建不会修改来源 failed Execution，不直接启动 Runtime，不绕过 Worker ownership；旧 Worker 明确失去 ownership 后必须主动停止 Runtime。

## 2. 当前 Unit Test 验证入口

按当前开发策略，仅以 Backend Unit Test 为主线阻塞条件：

```powershell
cd backend
uv run pytest -q
```

Lease Loss Active Abort targeted tests：

```powershell
cd backend
uv run pytest -q `
  tests/unit/test_workflow_worker_lease_guard.py `
  tests/unit/test_workflow_worker_lease_runtime.py `
  tests/unit/test_workflow_execution_terminal_ownership.py
```

本环境无法直接访问项目本地 `backend/.venv`，因此未执行上述命令，不记录 PASS。开发者本地执行后，应把真实 pytest 输出与结果补入本文件。

## 3. Closure 检查范围

### 3.1 Checkpoint / Resume

- Checkpoint 为 immutable execution fact；
- Resume Candidate 通过确定性来源与 checkpoint sequence 建立 lineage；
- Resume Execution 初始为 `pending`，不直接取得 Worker owner；
- Worker claim 前重新校验 Source、Checkpoint 与 Workflow Version；
- Resume 只从合法 checkpoint frontier 继续执行；
- Resume Execution 独立产生新的 Checkpoint sequence。

### 3.2 Automatic Recovery / Scheduler

- Recovery Policy 独立决定是否允许自动恢复；
- Recovery Domain 负责安全创建 Resume；
- `WorkflowExecutionResumeOutcome` 明确区分 `created` / `idempotency_hit`；
- Scheduler Scan 聚合 `candidates / eligible / recovered / rejected / contention / failed`；
- Scheduler Scan 使用 parent trace，每个 Automatic Recovery 使用独立 child trace；
- Recovery Trace Link 持久化 child trace，Worker / Runtime 可恢复该 lineage。

### 3.3 Worker Lease / Reclaim / Fencing

- `pending` 且无 owner 的 Execution 可被 claim；
- `running` 且 lease 已过期的 Execution 可在 PostgreSQL 行锁内 reclaim；
- reclaim 先回到 `pending`，再写入新 owner / lease，并递增 `worker_attempt`；
- 旧 Worker 后续状态推进必须通过 ownership fencing；
- terminal Execution 不残留 worker owner / lease；
- 旧 Worker 在 heartbeat 明确返回 ownership 丢失后，主动取消正在运行的 Runtime；
- terminal status 与 worker ownership / lease 在同一事务中原子清理，不依赖 Worker finally 的后置清理。

### 3.4 Lease Loss Active Abort

生命周期必须满足：

```text
Worker claim
    ↓
Runtime executing
    ↓
lease heartbeat
    ├── owned → continue
    ├── transient error → retry
    └── ownership lost
             ↓
       cancel Runtime task
             ↓
       stale Worker exits
             ↓
       new Worker reclaim / resume
```

Telemetry 必须满足：

- Worker started / finished 继续复用统一 `WorkflowRecoveryTelemetry`；
- lease loss 主动中止时 `outcome=aborted`；
- `reason_code=WORKER_LEASE_LOST`；
- Trace 不携带 Checkpoint `state_data`、Prompt、Secret、Provider credential 或完整业务 payload。

## 4. DAG / Branch / Join

- Multi-frontier Runtime Plan 必须确定性生成；
- 每个 Branch 使用独立 state 深拷贝；
- Branch 按确定性顺序执行，单 Branch 失败立即阻止后续 Branch；
- 所有 Branch 成功后才允许 State Merge 与 `join_ready=true`；
- 同一顶层状态键只有所有分支值一致时才合并；冲突必须显式拒绝；
- Join 仅负责 state aggregation，不调用 Model Provider；
- Join NodeExecution / Checkpoint 继续复用统一 `WorkflowExecutionService.transition_node()`；
- Join 完成后重新读取持久化 completed facts，再计算 downstream frontier。

## 5. 禁止事项

当前不得重新引入：

- 第二套 Worker Runtime；
- 第二套 Lease / Fencing 状态机；
- 平行 Recovery Trace 实现；
- 旧路径兼容垫片；
- 通过 Mock / fixture 替代真实持久化作为 Real API 验收；
- 将未实际执行的测试记录为 PASS。

## 6. Closure 状态

**代码实现：已完成。**

**本轮新增：terminal Execution 与 Worker ownership 原子边界修复及三种终态 Unit Test 覆盖。**

**Unit Test：本环境未实际执行；不得记录 PASS。**

**Phase 2.6 Closure：等待开发者本地 Unit Test 实际结果后关闭。**

完成 Closure 后，下一阶段进入企业级执行能力扩展；在 Closure 前不继续创建平行 Durable Execution 抽象。
