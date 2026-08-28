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

开发者实际执行最新 baseline `a26681d`：

```text
9 failed, 32 passed in 193.84s
```

主要问题：

- Runtime Model Governance Real API fixture 仍使用历史 `edges: []` 单节点 Definition，与当前 Durable Frontier 合法 DAG Contract 漂移；
- Durable Frontier Runtime Node failure 在事务 rollback 后没有重新持久化失败 Node Fact，导致 Resume 场景只看到前序已提交 Node / Checkpoint；
- Scheduler Real API 仍需在统一的当前 Worker / Scheduler 进程基线下重新验证，当前失败结果不标记 PASS。

## 本轮已提交修复

`ec25bb5f4771dae31f79ba6bd55345e2334bd224` — `fix(workflow): persist failed node facts during frontier recovery`

包含：

- Durable Frontier failure compensation 新增单 Node Frontier 的 `WorkflowNodeExecution(status=failed)` Durable Fact 恢复；
- 保持 Multi-frontier 不猜测具体失败 sibling，避免错误写入 Node failure；
- Runtime Model Governance Real API fixture 改为当前合法最小 DAG：`prepare -> governed-agent`；
- 新增错误记录：`docs/04-errors/2026-08-28-phase-2-7-real-api-durable-frontier-failure-node-fact.md`。

## 当前验证状态

以上修复尚未由开发者本地重新执行，因此以下均不得标记 PASS：

- targeted Unit；
- Runtime Model Governance Real API；
- Workflow Resume / Resume DAG / Resume Failure Real API；
- Tenant Safe Real API 全量 Gate；
- Scheduler / Worker 多实例生命周期验收；
- Backend Regression / Migration Gate。

## 下一执行顺序

```text
1. 同步最新 main 到本地
2. 停止旧 Worker，确保只运行当前 main 代码的 Worker
3. targeted Unit
4. Runtime Governance + Resume targeted Real API
5. Tenant Safe Real API Gate
6. Backend default regression
7. Alembic upgrade head / current
8. Scheduler / Worker 实际生命周期验收
9. Phase 2.8 Delegation Runtime Integration
10. 更新 Phase / Acceptance / Status / Error
```

## 本地服务要求

Unit 不需要外部服务。Real API / Runtime / Scheduler 验收需要开发者单独启动：

- PostgreSQL：`localhost:5432`；
- Redis：`localhost:6379`；
- API Service：`127.0.0.1:8000`；
- Worker Service：至少 1 个当前 `main` Worker；多 Worker 验收时再按场景启动多个；
- Scheduler Service：仅执行 Scheduler 相关验收时启动；
- Real Provider fixture 由 Real API 测试本地启动；使用真实远程 Provider 时再配置未提交 `.env`。

测试 Gate 不自动启动或停止服务。
