# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.7 Advanced Workflow Orchestration：主线生产代码持续收口；当前 Real API / Runtime 验证仍需开发者本地重新执行，不标记最终验收通过。
- Phase 2.8-A Multi-Agent Collaboration Contract：已冻结。
- 当前开发任务：**Phase 2.8 Backend Domain + API Contract**，首版 Delegation Contract 已完成；当前优先修复 Phase 2.7 Real API blocker，再进入 Phase 2.8 Runtime Integration。

## 2026-08-28 开发者实际反馈

### Unit targeted

```text
uv run pytest tests/unit/services/workflow/checkpoint/test_checkpoint_export_fencing.py -q
2 passed in 0.49s
```

### Tenant Safe Real API

开发者实际执行最新 baseline `8d642a1`：

```text
7 failed, 34 passed in 199.22s
```

本轮反馈已经证明上一轮 `edges: []` Contract 漂移与失败 Node Fact 丢失问题不再是当前失败主因；剩余失败集中在 Durable Resume / Scheduler 真实运行边界：

- Resume / Resume DAG / Resume Failure 新 Execution 长时间未进入期望终态；
- Scheduler Real API 的真实 Execution 集合断言仍失败；
- 本次本地环境存在多个同时运行的 Worker PID，必须先停止旧 Worker，再只启动当前 `main` Worker 进行下一轮验证，避免旧进程继续消费当前测试生成的 Durable Frontier。

## 本轮工程修复

### Durable Frontier Claim → Runtime 生命周期闭环

`DurableFrontierWorkflowWorker.claim_one_frontier()` 在成功 Claim pending Execution 后，原先只设置 Worker ownership / lease，却没有在同一事务把 Execution 从 `pending` 推进到 `running`。这与 Durable Frontier completion contract 不一致：`complete_frontier_with_checkpoint()` 明确要求成功 Frontier 只能作用于 `running` Execution。

本轮修复：

- Claim 成功后在同一事务将 pending Execution 设置为 `running`；
- 首次启动写入 `started_at`；
- 同一事务记录 `execution.state_changed -> running` Trace；
- 保留原有 Worker owner / attempt / lease fencing；
- expired running Execution 重新回收为 pending 后继续在同一 Claim 事务启动为 running；
- 不新增第二套 Runtime / Execution 状态机，也不提前 commit。

## 当前验证状态

本轮代码修复尚未由开发者本地重新执行，因此以下均不得标记 PASS：

- Durable Frontier Worker targeted Unit；
- Runtime Model Governance Real API；
- Workflow Resume / Resume DAG / Resume Failure Real API；
- Scheduler Real API；
- Tenant Safe Real API 全量 Gate；
- Backend Regression / Migration Gate；
- Scheduler / Worker 多实例生命周期验收。

## 下一执行顺序

```text
1. 同步最新 main 到本地
2. 停止所有旧 Worker / Scheduler，确保只运行当前 main 代码
3. uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q
4. Runtime Governance + Resume targeted Real API
5. Scheduler targeted Real API（Scheduler 需要独立启动时只启动一个当前 main Scheduler）
6. Tenant Safe Real API Gate
7. Backend default regression
8. Alembic upgrade head / current
9. Scheduler / Worker 实际生命周期验收
10. Phase 2.8 Delegation Runtime Integration
11. 更新 Phase / Acceptance / Status / Error
```

## 本地服务要求

Unit 不需要外部服务。Real API / Runtime / Scheduler 验收需要开发者单独启动：

- PostgreSQL：`localhost:5432`；
- Redis：`localhost:6379`；
- API Service：`127.0.0.1:8000`；
- Worker Service：至少 1 个当前 `main` Worker；真实验收前必须停止旧 Worker；多 Worker 验收时再按场景启动多个；
- Scheduler Service：仅执行 Scheduler 生命周期验收时启动，默认只启动 1 个当前 `main` Scheduler；
- Real Provider fixture 由 Real API 测试本地启动；使用真实远程 Provider 时再配置未提交 `.env`。

测试 Gate 不自动启动或停止服务。
