# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B4 Timeout / Cancel / Parent Semantics**
- B2/B3 已由开发者本地实际验收通过；下一主线任务按 Roadmap 进入 B4。

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- B1 Atomic Claim 已完成并通过本地真实 HTTP + PostgreSQL 双 Worker 并发 Gate；
- B2 Worker Execution Bridge 已完成，复用既有 Workflow Worker / WorkflowRuntime；
- B3 Delegation completion/failure generation fencing 已完成；
- Runtime Session / Execution terminalization / Model Profile Snapshot / Frontier heartbeat 锁序问题已完成修复；
- Scheduler 对单节点顺序 Workflow 的空 `edges` 语义已与 DAG Runtime 对齐。

## 3. 最新本地验收证据

开发者在 `79d68c58` 基线执行：

```text
B2 bridge Unit             3 passed
Backend regression         853 passed, 3 skipped, 46 deselected
Migration/head             0039_workflow_node_execution_tenant_trigger (head)
B2 Real Gate               3 passed

B3 Delegation lifecycle    30 passed
Backend regression         853 passed, 3 skipped, 46 deselected
Migration/head             0039_workflow_node_execution_tenant_trigger (head)
B3 Real Gate               3 passed

Workflow DAG contract      2 passed
```

因此此前反复出现的 `AgentDelegation.status == running`、Worker lease race、Frontier lock inversion 已不再是当前阻塞项。

## 4. B4 实现

### 4.1 Delegation timeout

新增正式 timeout 运行时边界：

- `timeout_at` 继续作为 Delegation 生命周期的唯一持久化时间边界；
- Worker Runtime 使用 `min(Workflow Runtime timeout, Delegation remaining timeout)`；
- Delegation timeout 触发时，子 Worker Execution 通过既有 Execution lifecycle 进入 `cancelled`；
- Runtime Session 完整退出后，再使用独立 Session 将 Delegation 原子收敛为 `timed_out`；
- timeout 不直接修改父 Workflow Execution；
- 迟到 Worker completion/failure 因 Delegation 已进入终态而被 generation fencing 拒绝。

### 4.2 Cancel

现有 `POST /workflows/{execution_id}/delegations/{delegation_id}/cancel` 继续复用 Delegation lifecycle：

```text
pending → cancelled
running → cancelled
```

取消只结束 Delegation，不直接把父 Workflow Execution 推入 terminal 状态；重复取消 fail-closed。

### 4.3 Parent semantics

B4 明确保持：

```text
Worker completed / failed / timed_out / cancelled
        ↓
Delegation 自身终态
        ↓
父 Workflow Execution 继续由既有 Workflow / Execution / Retry / Recovery Contract 决定
```

禁止为 Multi-Agent 创建第二套父流程 Retry / Recovery 状态机。

## 5. B4 自动化验收

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\04_delegation_timeout_cancel_gate.ps1
```

Gate 不启动、重启或停止任何服务，只验证前置环境。测试用户、密码、Access Token、tenant、ID 与测试数据均由脚本自动生成。

Gate 顺序：

```text
[0] prerequisite service verification
    ↓
[1] Delegation timeout Unit
    ↓
[2] Backend default regression
    ↓
[3] Alembic upgrade/head verification
    ↓
[4] Real HTTP + PostgreSQL B4 timeout/cancel/parent semantics
```

B4 Real API 必须实际证明：

1. cancel → Delegation `cancelled`；
2. duplicate cancel → 409；
3. timeout → Worker Execution `cancelled` + Delegation `timed_out`；
4. timeout/cancel 均不终止父 Workflow Execution；
5. timeout 后 stale completion 不得覆盖终态；
6. PostgreSQL 持久化状态与 generation identity 一致。

## 6. 下一主线任务

B4 验收通过后继续：

```text
B5 Audit / Trace closure
    ↓
Delegation multi-worker + PostgreSQL + Runtime acceptance
    ↓
Phase 2.8 closure
    ↓
Phase 2.9 Enterprise Integration / Event Infrastructure Contract
```

未执行的 B4 测试不得标记 Passed；Migration head 必须保持 `0039_workflow_node_execution_tenant_trigger`。
