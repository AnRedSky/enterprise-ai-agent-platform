# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前代码提交：`cf60a6cd68c17dd54f67025719f36a40bf31a69b` — `feat(phase-2.8): implement B1 atomic delegation claim`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B1 Atomic Delegation Claim**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力已完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施已完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- lifecycle / Worker fencing 纯规则入口已建立；
- Service 重复 lifecycle 状态规则已删除；
- B1 Atomic Claim 已进入生产代码：使用 PostgreSQL Delegation 行锁，创建真实 `WorkflowExecution` 作为 Worker Execution，并将其 ID 写入 `worker_execution_id`；Worker ownership 复用既有 `worker_owner` / `worker_lease_expires_at`。

## 3. 当前 B1 实现边界

```text
pending Delegation
      │
      │ PostgreSQL SELECT ... FOR UPDATE
      ▼
检查 tenant / status / timeout / parent execution
      │
      ▼
创建 WorkflowExecution(status=running)
      │
      ├── worker_owner
      ├── worker_lease_expires_at
      └── idempotency_key = delegation:<id>
      │
      ▼
Delegation.status = running
Delegation.worker_execution_id = WorkflowExecution.id
      │
      ▼
同一事务提交
```

B1 不创建第二套 Worker lease、Retry 或 Recovery 状态机，也不执行 Agent Runtime。

## 4. 当前未完成

| 能力 | 状态 |
|---|---|
| B1 Atomic Claim 代码 | ✅ 已实现 |
| B1 lifecycle targeted Unit | 🟡 待开发者本地执行 |
| B1 PostgreSQL Integration | ⏳ 待实现/验证 |
| B1 2+ Worker 并发竞争 | ⏳ 待真实 PostgreSQL 验证 |
| B2 Workflow Worker Execution Bridge | ⏳ |
| B3 generation-fenced completion/failure | ⏳ |
| B4 timeout/cancel/parent semantics | ⏳ |
| B5 Audit/Trace 完整闭环 | ⏳ |
| Delegation Runtime Real API Gate | ⏳ |

## 5. 下一开发顺序

```text
B1 targeted Unit
    ↓
B1 PostgreSQL Integration
    ↓
2+ Worker 并发 Claim
    ↓
修复并发边界问题
    ↓
B2 复用 Workflow Worker Execution / Agent Runtime
    ↓
B3 completion / failure + generation fencing
    ↓
B4 timeout / cancel / parent semantics
    ↓
B5 Audit / Trace
    ↓
Real API + PostgreSQL + 多 Worker acceptance
```

## 6. 测试规则

开发者本地实际执行结果为唯一测试依据；GitHub Actions 不作为验收依据。

B1 当前至少需要：

```powershell
cd backend
uv run pytest tests/unit/test_agent_delegation_lifecycle.py -q
uv run pytest -q tests/unit -k delegation
uv run pytest -q
```

PostgreSQL Runtime 验证必须额外证明 2+ Worker 同时 Claim 同一 Delegation 时只有一个 owner 成功，并确认 `worker_execution_id` 与 Worker Execution 持久化一致。

## 7. 当前结论

**项目已从 Delegation Contract / Domain 层正式进入 Runtime Integration。B1 Atomic Delegation Claim 已完成第一版代码实现，但尚未有开发者本地测试证据，因此不能标记为验收通过。下一步直接进行 B1 PostgreSQL 并发 Integration，不扩展前端 UI。**
