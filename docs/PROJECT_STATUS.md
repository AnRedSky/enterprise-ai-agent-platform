# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前代码提交：`ab641ae85305dd14c1ff872fe61292993ae76008` — `test(phase-2.8): add B1 claim to delegation gate`
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
- B1 Atomic Claim 已进入生产代码：使用 PostgreSQL Delegation 行锁，创建真实 `WorkflowExecution` 作为 Worker Execution，并将其 ID 写入 `worker_execution_id`；Worker ownership 复用既有 `worker_owner` / `worker_lease_expires_at`；
- B1 Real API / PostgreSQL 并发测试实现与 Gate 已加入仓库，但尚未有开发者本地实际执行结果，因此不能标记为验收通过。

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
Audit + Trace
      │
      ▼
同一事务提交
```

B1 不创建第二套 Worker lease、Retry 或 Recovery 状态机，也不执行 Agent Runtime。

## 4. B1 测试实现

新增真实验收测试：

```text
backend/tests/api_real/test_agent_delegation_claim_api.py
```

测试通过真实 HTTP 创建 Delegation，再使用两个独立 PostgreSQL `AsyncSession` 并发调用 `claim_delegation()`，要求：

- 2 个 Worker 竞争同一 Delegation 时恰好 1 个 Claim 成功；
- 成功 Claim 后 Delegation 为 `running`；
- `worker_execution_id` 指向唯一真实 `WorkflowExecution`；
- Worker owner 与 Delegation generation 一致；
- tenant identity 一致；
- 第二次 Claim 必须被拒绝。

Phase 2.8 Gate 已扩展为：

```text
Unit lifecycle / identity
    ↓
Backend default regression
    ↓
Alembic upgrade head / current
    ↓
Delegation Real HTTP + PostgreSQL
    ↓
B1 PostgreSQL two-worker race
```

## 5. 当前未完成

| 能力 | 状态 |
|---|---|
| B1 Atomic Claim 代码 | ✅ 已实现 |
| B1 lifecycle targeted Unit | 🟡 待开发者本地执行 |
| B1 Real HTTP Delegation Contract | 🟡 待开发者本地执行 |
| B1 PostgreSQL 单 Worker Claim | 🟡 待开发者本地执行 |
| B1 2+ Worker 并发竞争 | 🟡 待开发者本地执行 |
| B1 transaction / tenant consistency | 🟡 待开发者本地执行 |
| B2 Workflow Worker Execution Bridge | ⏳ |
| B3 generation-fenced completion/failure | ⏳ |
| B4 timeout/cancel/parent semantics | ⏳ |
| B5 Audit/Trace 完整闭环 | ⏳ |
| Delegation Runtime Real API Gate | ⏳ |

## 6. 下一开发顺序

```text
B1 本地 targeted Unit / Real PostgreSQL Gate
    ↓
若发现真实并发或事务问题，立即修复
    ↓
B1 验收闭环
    ↓
B2 Workflow Worker Execution Bridge
    ↓
B3 completion / failure + generation fencing
    ↓
B4 timeout / cancel / parent semantics
    ↓
B5 Audit / Trace
    ↓
Real API + PostgreSQL + 多 Worker acceptance
```

## 7. 测试规则

开发者本地实际执行结果为唯一测试依据；GitHub Actions 不作为验收依据。

B1 Gate 唯一入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\01_delegation_contract_gate.ps1
```

仅运行不依赖 Real API 的 B1 Unit / Backend / Migration：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\01_delegation_contract_gate.ps1 -SkipRealApi
```

Real API 场景要求：

```powershell
$env:ACCESS_TOKEN = "<开发者本地有效 Token>"
$env:API_BASE_URL = "http://127.0.0.1:8000/api/v1"
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\01_delegation_contract_gate.ps1
```

Gate 脚本必须由开发者实际执行后，才能把 B1 状态从“已实现/待验证”推进为“已验收”。

## 8. 当前结论

**项目已正式进入 Phase 2.8 Runtime Integration。B1 Atomic Delegation Claim 已完成生产代码与自动化验收实现：Delegation 行锁 + 真实 WorkflowExecution + Worker ownership + 同事务持久化均已落地。当前唯一剩余工作是开发者本地真实 PostgreSQL / 双 Worker 并发执行验证；验证完成后立即进入 B2 Workflow Worker Execution Bridge，不扩展前端 UI。**
