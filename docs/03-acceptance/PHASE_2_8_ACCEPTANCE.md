# Phase 2.8 Acceptance — Multi-Agent Collaboration Runtime Integration

## 1. 验收范围

本文件记录 Phase 2.8 Multi-Agent Collaboration Runtime Integration 的实际实施与验收结果。

本阶段范围包括：

- Phase 2.8-A Delegation Contract；
- AgentDelegation Durable Entity / Repository / Service / API；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget；
- B1 Atomic Delegation Claim；
- B2 Existing Worker Execution bridge；
- B3 generation-fenced completion / failure；
- B4 timeout / cancel / parent semantics；
- B5 Audit / Trace closure；
- B6 Multi-Worker Durable Frontier Runtime；
- 与既有 Workflow Worker、WorkflowRuntime、lease、fencing、Retry / Recovery 的复用边界。

本阶段不包含专用 Delegation 前端 UI，因此 Browser E2E 不作为本 Phase 必选验收门槛。

## 2. 验收原则

- 以开发者本地实际执行结果为准；
- GitHub Actions 不作为开发测试、质量门禁或验收依据；
- Real API 必须验证真实 HTTP + PostgreSQL 持久化；
- Migration 必须实际验证到 head；
- 未执行测试不得标记 Passed；
- 历史失败记录保留用于追溯，不覆盖最新实际通过结果。

## 3. B1-B6 验收矩阵

| 子任务 | 范围 | 状态 | 证据 |
|---|---|---|---|
| B1 | Atomic Delegation Claim | ✅ Passed | B6 targeted Unit/Contract + Real Runtime |
| B2 | Existing Worker Execution bridge | ✅ Passed | B6 Real Runtime，复用既有 Workflow Worker / WorkflowRuntime |
| B3 | Generation-fenced completion / failure | ✅ Passed | fencing tests + B6 Runtime |
| B4 | Timeout / cancel / parent semantics | ✅ Passed | 本地 Runtime / Real API 证据 |
| B5 | Audit / Trace closure | ✅ Passed | AuditLog / WorkflowTraceEvent + targeted tests |
| B6 | Multi-worker Durable Frontier Runtime | ✅ Passed | 正式 B6 Real Gate |

## 4. B6 正式 Gate

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

验收顺序：

```text
[0] prerequisite service verification + Worker/Scheduler isolation
    ↓
[1] Delegation Claim + Worker dispatch Unit/Contract
    ↓
[2] Backend default regression
    ↓
[3] Alembic upgrade/head
    ↓
[4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
```

最新开发者本地实际结果：

```text
[1/4] Delegation Claim + Worker dispatch Unit/Contract
38 passed in 1.08s

[2/4] Backend default regression
870 passed, 3 skipped, 52 deselected in 34.61s

[3/4] Migration/head verification
0039_workflow_node_execution_tenant_trigger (head)

[4/4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
5 passed in 7.48s

[PASS] Phase 2.8 B6 multi-worker Delegation Runtime gate completed.
```

## 5. Real Runtime 验收结论

上述 Gate 结果证明当前 Phase 2.8 Backend Runtime 范围已经满足：

1. Delegation 可以从 pending durable fact 进入正式 Worker Claim；
2. 多 Worker 在真实 PostgreSQL Claim contention 下不会因为固定调度顺序而错误判定任务未消费；
3. Worker Execution 通过既有 Durable Frontier / Workflow Runtime 正式路径执行；
4. generation fencing 能防止 stale Worker 覆盖已完成、取消或新一代执行结果；
5. timeout / cancel 只收敛 Delegation 自身，不直接改变父 Workflow terminal 状态；
6. Delegation Audit / Trace 能关联父 Execution、Delegation 与 Worker Execution；
7. Worker shutdown AsyncEngine cleanup 在 cancellation 下具有安全清理语义；
8. Windows 本地 Gate 能识别可能污染验收的外部 `run_worker.py` / `run_scheduler.py` 消费者；
9. 数据库 migration 已验证到 `0039_workflow_node_execution_tenant_trigger (head)`。

## 6. 已发生工程错误的闭环

本阶段已分析并修复的代表性错误：

- B6 默认 Worker 入口与 Planner-driven Contract 不一致；
- Planner-driven Worker 缺失 Delegation Frontier 正式 Runtime 路由；
- 多 Worker Claim contention 被固定轮次测试误判；
- Worker shutdown AsyncEngine / asyncpg connection cleanup 在 cancellation 下产生 `CancelledError`；
- Windows PowerShell Worker/Scheduler 外部消费者检测存在环境污染与正则解析问题。

对应 `docs/04-errors/` 记录均已更新为“已修复并已验证关闭”，最新 Gate 结果不再存在 B6 blocker。

## 7. Frontend / Browser E2E

本 Phase 未新增 Delegation 专用 UI，因此：

- Frontend API Types：无新增必选范围；
- Frontend UI：无新增必选范围；
- Browser E2E：不作为本 Phase 必选 Gate。

不得为了形式上补齐 Browser Gate 而重复创建未进入产品 Contract 的 Delegation UI。

## 8. Phase 2.8 关闭结论

**Phase 2.8 Multi-Agent Collaboration Runtime Integration 已完成当前定义范围并通过正式 B6 Real Gate。**

当前没有证据表明 B1-B6 存在未解决的 Runtime blocker。历史错误与失败测试结果继续作为工程追溯资料保留，但不得用于否定最新实际 Gate 通过结果。

Phase 2.8 后续仅保留正常回归与发布验证，不再继续扩展未经 Contract 决策的协作能力。

## 9. 下一阶段

下一主线为 **Phase 2.9 Enterprise Integration / Event Infrastructure Contract**，当前仍属于候选/前置评估阶段。

进入 2.9 正式开发前必须：

1. 盘点现有 Event / Webhook / Trigger / Audit / Trace / Outbox 等实现；
2. 确认不存在可复用能力之外的重复 Service / Repository / Runtime / Provider；
3. 明确真实企业场景、可靠性、幂等、投递、顺序、重试、隔离和可观测边界；
4. 冻结 Contract 后再建立正式 Phase 2.9 开发文档与 Acceptance；
5. 遵守 Contract → Migration → Backend → Unit/Integration/Contract → Real API → Acceptance 的既定顺序。
