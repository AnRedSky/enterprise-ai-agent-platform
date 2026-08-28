# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.7 Advanced Workflow Orchestration：主线生产代码持续收口；当前 Real API / Runtime 验证仍需开发者本地重新执行，不标记最终验收通过。
- Phase 2.8-A Multi-Agent Collaboration Contract：已冻结。
- 当前开发任务：**Phase 2.8 Backend Domain + API Contract**，首版 Delegation Contract 已完成；当前优先修复 Phase 2.7 Real API blocker，再进入 Phase 2.8 Runtime Integration。

## 2026-08-28 最新开发者反馈与本轮修复

### Durable Frontier Worker targeted Unit

```text
uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q
13 passed in 0.17s
```

该结果证明当前 `main` 的 Claim → Execution `running` 生命周期修复已经通过 targeted Unit。

### Real API 多实例服务边界已调整

Real API Gate 现在要求：

- 至少 1 个当前 `main` Worker；允许多个 Worker 并发运行；
- 至少 1 个当前 `main` Scheduler；允许多个 Scheduler 并发运行；
- Gate 不因 Worker / Scheduler 数量大于 1 而失败。

该约束与 Durable Frontier 的 PostgreSQL claim / lease / fencing，以及 Scheduler slot claim / idempotency 的真实并发验收语义一致。旧版“必须只有一个 Worker / Scheduler”约束已经删除。

### 直接执行 Real API 测试的上下文问题

开发者直接执行 Real API 测试时，如果没有先运行 tenant-safe Real API bootstrap，可能缺失 `ORGANIZATION_ID`、`TRIGGER_WORKFLOW_ID` 等上下文。此类结果不能作为 Real API 产品功能通过或失败的依据；正式验收必须通过专用 Gate 准备 tenant-safe context。

### 本轮 5 个 Real API 失败的根因已经完成代码/测试修复

最新 tenant-safe Gate 实际反馈为 `36 passed / 5 failed`，失败集中于：

1. Usage Accounting fixture 使用历史 `edges: []` Definition，与当前非空 DAG Edge Contract 漂移；
2. Durable Resume / Resume DAG / Resume Failure Real API 测试直接调用 `WorkflowExecutionService.resume_from_latest_checkpoint()`，绕过正式 `WorkflowExecutionResumeContractService` 的 Durable Bootstrap，因此创建了没有首个 Frontier 的 pending Resume Execution，Worker 没有 durable work item 可消费。

本轮已经完成：

- Usage Accounting fixture 改为 `prepare → usage-agent` 最小合法 DAG；
- Resume / Resume DAG / Resume Failure 验收统一通过正式 Resume Contract 创建 Resume；
- Resume DAG 验收显式覆盖 Bootstrap 复制的 completed Node lineage；
- 新增错误记录 `docs/04-errors/2026-08-28-phase-2-7-real-api-resume-test-contract-drift.md`。

以上修复**尚未由开发者本地重新执行**，因此不得预填 PASS。

## 当前验证状态

已获得本轮实际结果：

- Durable Frontier Worker targeted Unit：`13 passed`。

本轮修复后尚未获得新的开发者实际 PASS：

- Runtime Model Governance Real API；
- Workflow Resume / Resume DAG / Resume Failure Real API；
- Usage Accounting Real API；
- Scheduler Real API；
- Tenant Safe Real API 全量 Gate；
- Backend default regression；
- Alembic upgrade head / current；
- Scheduler / Worker 实际生命周期验收。

## 下一执行顺序

```text
1. 同步最新 main
2. 确认 PostgreSQL / Redis / API / Scheduler / Worker 均已启动
3. Worker targeted Unit
4. Runtime Governance + Usage Accounting + Resume targeted Real API
5. Scheduler targeted Real API
6. Tenant Safe Real API 全量 Gate
7. Backend default regression
8. uv run alembic upgrade head
9. Scheduler / Worker 多实例实际生命周期验收
10. Phase 2.7 blocker 全部收口后，继续 Phase 2.8 Delegation Runtime Integration
11. 更新 Phase / Acceptance / Status / Error
```

## 本地服务要求

Unit 不需要外部服务。Real API / Runtime / Scheduler 验收需要开发者单独启动：

- PostgreSQL：`localhost:5432`；
- Redis：`localhost:6379`；
- API Service：`127.0.0.1:8000`；
- Worker Service：至少 1 个当前 `main` Worker；允许多个 Worker 并发运行；
- Scheduler Service：至少 1 个当前 `main` Scheduler；允许多个 Scheduler 并发运行；
- Real Provider fixture：由 Real API 测试本地启动；不提交远程 Secret。

测试 Gate 不自动启动或停止服务。