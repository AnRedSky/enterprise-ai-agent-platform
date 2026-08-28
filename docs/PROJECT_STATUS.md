# 项目状态

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 最新 main：`37061abb99fefbf753c088f6644f24d289814c39` — `feat(phase-2.8): establish delegation lifecycle fencing contract`
- 上一关键基线：`b5e3c44484f9ffa231fb1f368cfc14afe0d99dea` — `fix(delegation): serialize active budget creation boundary`
- 本轮核查：以远端最新 `main` 为代码基线，并结合开发者在 `b5e3c44` 上提供的本地实际测试结果判断已完成事实；对 `37061ab` 新增代码不借用旧测试结果冒充通过。

## 2. 上一阶段 / 上一任完成情况

### Phase 2.7 Advanced Workflow Orchestration

主线生产实现已经完成并进入验收收口。上一轮 Durable Resume / Frontier 的真实问题已经完成代码与测试 Contract 收口，开发者随后实际执行 Tenant Safe Real API Gate：

```text
HEAD == origin/main: b5e3c44484f9ffa231fb1f368cfc14afe0d99dea
41 passed in 81.83s
[PASS] Tenant-safe Real API gate completed.
```

同时开发者实际反馈：

```text
uv run pytest -q
824 passed, 3 skipped, 42 deselected in 34.22s
```

因此，之前的 Resume Checkpoint `node_id/node_status = NULL` Contract 漂移、重复 checkpoint、Worker/Scheduler 多实例 Gate 约束等已不再是当前 blocker。Phase 2.7 当前应视为**主线生产能力已完成、核心 Backend/Real API 验证已通过；剩余仅需按发布范围继续完成前端/E2E或最终验收记录时再收口**，不得继续把已解决的 Resume blocker 当作当前开发任务。

### Phase 2.8-A Multi-Agent Collaboration Contract

Contract 已冻结，明确首版目标为受治理的 Orchestrator → Worker Agent Delegation；禁止跨 tenant、无限 spawning、MQ/Kafka、第二套 Retry/Recovery 状态机。Delegation 必须具备 tenant/version/permission、稳定幂等、context isolation、depth/active-count/timeout/model budget、Audit/Trace 与 Worker completion fencing。

### Phase 2.8 Backend Domain + API Contract

上一任已完成：

- `AgentDelegation` Durable Entity；
- `AgentDelegationRepository`；
- `AgentDelegationService`；
- Delegation identity / budget 正式计算入口；
- Delegation 创建、查询、取消 API；
- `0038_agent_delegations` migration；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 约束；
- active budget creation race 的父 Execution 行锁修复；
- Delegation Unit / Real API 基础测试。

这些能力说明 **Delegation Domain + API Contract 已进入可运行的 Backend 基础层，但还不是完整 Worker Runtime**。

## 3. 最新提交的实际新增内容

`37061ab` 新增 `backend/app/services/agent_delegation/lifecycle.py`，将以下规则集中为唯一纯领域入口：

```text
pending → running / cancelled
running → completed / failed / timed_out / cancelled
terminal → 不允许再次进入活动态
Worker completion → 必须是 running + 当前 worker_execution_id generation
timeout → now >= timeout_at
```

同时新增对应 Unit 测试，并新增 `docs/02-phases/PHASE_2_8_RUNTIME.md`。该提交的设计意图是先固定 lifecycle/fencing 不变量，再把 Delegation 接入现有 Worker Runtime，避免旧 Worker、重复 claim、timeout 后迟到 completion 覆盖新 generation。

**注意：开发者尚未提供 `37061ab` 提交后的本地 Unit/Regression 实际执行结果，因此本轮不能把新增 lifecycle Unit 标记为 PASS。**

## 4. 核查对比

| 能力 | 上一阶段完成事实 | 最新 main 状态 | 判断 |
|---|---|---|---|
| Workflow Resume / Recovery | 已完成并通过真实 Gate | 保持 | ✅ 收口 |
| Durable Frontier claim / lease / fencing | 已完成 | 保持 | ✅ 收口 |
| Resume checkpoint Contract | 已修复并通过 41 Real API | 保持 | ✅ blocker 已解除 |
| Scheduler 多实例边界 | 已验证允许多个实例 | 保持 | ✅ |
| Delegation Domain Entity | 已实现 | 保持 | ✅ |
| Delegation API Contract | 已实现 | 保持 | ✅ |
| Delegation active budget race | 已修复并已进入 main | 保持 | ✅ |
| Delegation lifecycle rule | 新增纯规则入口 | `37061ab` | 🟡 待本地验证 |
| Delegation Worker atomic claim | 尚未实现 | 仍缺失 | ⏳ 当前任务 |
| `worker_execution_id` 创建/代际绑定 | 字段已存在 | Runtime 尚未消费 | ⏳ 当前任务 |
| Worker execution / target Agent 实际执行 | 尚未实现 | 尚未实现 | ⏳ 当前任务 |
| Worker completion fencing 持久化写回 | 规则已定义 | Service Runtime 尚未接入 | ⏳ 当前任务 |
| Timeout / cancellation Runtime | Domain 字段/接口存在 | Worker lifecycle 尚未接入 | ⏳ 当前任务 |
| Audit / Trace Worker 子执行链 | 创建时已有基础事件 | Runtime worker fact 尚未闭环 | ⏳ 当前任务 |
| PostgreSQL Integration / Real API Runtime | Contract 有要求 | 尚未完成 | ⏳ 当前任务 |
| 多 Worker 竞争同一 Delegation | 尚未实现 | 尚未实现 | ⏳ 当前任务 |

## 5. 当前执行任务：Phase 2.8 Runtime Integration

当前不是继续扩展 Delegation API，而是把现有 Delegation Durable Entity 接入**已有 Workflow Worker / lease / fencing 体系**。

### Task 2.8-B1：Atomic Delegation Claim

目标：在 `AgentDelegationService` 建立 tenant-scoped 原子 Claim：

1. 只允许 `pending` Delegation 被 Claim；
2. 使用 PostgreSQL 行锁 / 条件更新形成单一 ownership boundary；
3. 一次 Claim 生成唯一 `worker_execution_id`；
4. 同一 Delegation 并发 Claim 只能一个 generation 成功；
5. Claim 必须校验 timeout、tenant、状态与治理边界；
6. 不新增第二套 Worker 进程或独立 lease 模型。

### Task 2.8-B2：复用 Workflow Worker Execution

将 target Agent version、model profile、input_data、selected_context_refs、allowed_tools 显式装配到现有 Worker execution；不复制父 Execution 全量 context。

### Task 2.8-B3：Completion / Failure / Timeout / Cancel

统一通过 `lifecycle.py` 校验状态转换与 generation fencing；所有持久化写回在明确事务边界内完成。stale Worker、已取消 Delegation、已超时 Delegation 均必须 fail-closed。

### Task 2.8-B4：Audit / Trace

形成：

```text
source Workflow Execution
  └── Delegation
        └── Worker Execution / Trace
```

Worker 结果可以反查父 Execution，且不得记录 Secret / credential 原文。

### Task 2.8-B5：真实并发验收

至少验证：

- 2 个以上 Worker 同时竞争同一 Delegation；
- 只有一个 generation 成为 owner；
- stale completion 不得覆盖新 owner；
- timeout/cancel 与迟到 completion 收敛；
- PostgreSQL 中状态、worker_execution_id、Audit、Trace 一致。

## 6. 下一步任务顺序

```text
1. 本地同步最新 main / 清理旧进程
2. 验证 37061ab lifecycle targeted Unit
3. Phase 2.8-B1 Atomic Delegation Claim
4. B1 Unit + PostgreSQL Integration
5. B2 复用现有 Worker Execution / Agent Runtime
6. B3 completion / failure / timeout / cancel + fencing
7. B4 Audit / Trace
8. Phase 2.8 Real API Gate
9. 多 Worker 并发 Delegation acceptance
10. Backend default regression + migration verification
11. 如有前端范围，再进入 API Types / UI / E2E
12. 更新 Phase / Acceptance / Status / Error 并提交 main
```

## 7. 当前本地验证基线

开发者已实际验证上一 main：

```text
uv run pytest tests/unit/test_agent_delegation_identity.py tests/unit/test_durable_frontier_worker_dispatch.py -q
23 passed in 0.53s

uv run pytest -q
824 passed, 3 skipped, 42 deselected in 34.22s

uv run alembic upgrade head
uv run alembic current
0039_workflow_node_execution_tenant_trigger (head)

Tenant Safe Real API Gate
41 passed in 81.83s
```

以上属于 `b5e3c44` 已实际反馈的结果。`37061ab` 新增 lifecycle 代码后的结果必须重新执行，不能沿用上述数字。

## 8. 本地服务要求

### Unit

无需外部服务：

```powershell
cd backend
uv run pytest tests/unit/test_agent_delegation_lifecycle.py -q
```

### Integration / Real API / Runtime

必须由开发者提前启动并保持运行：

- PostgreSQL：`localhost:5432`；
- Redis：`localhost:6379`；
- API：`127.0.0.1:8000`；
- Worker：至少 1 个，建议 Runtime 并发验收使用 2 个以上；
- Scheduler：至少 1 个；
- Real Provider fixture：由 Real API 测试自行启动，真实远程 Secret 只允许放本地 `.env`。

Gate 不自动启动或停止这些服务。

## 9. 当前结论

**Phase 2.7 已从“当前 blocker”升级为已完成主线能力；Phase 2.8 Delegation Domain/API 已完成基础层；`37061ab` 已开始真正的 Runtime Integration，但目前只完成 lifecycle/fencing 纯规则，尚未完成 Delegation Worker Claim 与实际执行闭环。**

因此下一任不得继续重复 Resume checkpoint 修复，也不得停留在文档整理；应直接进入 **Phase 2.8-B1 Atomic Delegation Claim → 现有 Worker Execution 接入 → generation-fenced completion → Real API 多 Worker 并发验收**。