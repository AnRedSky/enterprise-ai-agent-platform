# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.7 Advanced Workflow Orchestration：主线生产代码持续收口；当前 Real API / Runtime 验证仍需开发者本地重新执行，不标记最终验收通过。
- Phase 2.8-A Multi-Agent Collaboration Contract：已冻结。
- 当前开发任务：**Phase 2.8 Backend Domain + API Contract**，首版 Delegation Contract 已完成；当前优先修复 Phase 2.7 Real API blocker，再进入 Phase 2.8 Runtime Integration。

## 2026-08-28 最新开发者反馈

### Durable Frontier Worker targeted Unit

```text
uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q
13 passed in 0.17s
```

该结果证明 `00532fb` 的 Claim → Execution `running` 生命周期修复已经通过 targeted Unit。

### 直接执行 Real API 测试的上下文问题

开发者直接执行以下命令时，没有先运行 tenant-safe Real API bootstrap：

```text
uv run pytest tests/api_real/test_runtime_model_governance_api.py -q -m real_api
```

结果为 2 个测试因为 `ORGANIZATION_ID` 缺失而失败；Workflow Resume 测试在同样缺少上下文时正确显示为 skipped；Scheduler 测试则因 `TRIGGER_WORKFLOW_ID` 缺失而 fail-fast。

这类结果**不能作为 Real API 产品功能失败或通过的依据**。Real API 必须通过专用 Gate 准备 `ACCESS_TOKEN`、`ORGANIZATION_ID`、`TRIGGER_WORKFLOW_ID` 等 tenant-safe context 后执行。

本轮已加强 Real API Gate：

- Tenant Safe Full Gate 检测 Worker 数量；
- Durable Resume 专用 Gate 检测 Worker 数量；
- 若存在多个 `run_worker.py` 进程，Gate 直接阻断并输出 PID / CommandLine，避免旧 Worker 与当前 `main` 代码竞争同一 Durable Frontier，产生无法归因的测试结果。

### 上一轮真实 Worker blocker 仍未被本轮反馈重新验收

上一轮 tenant-safe Gate 在 `8d642a1` 的实际结果为：

```text
7 failed, 34 passed in 199.22s
```

失败集中于 Durable Resume / Resume DAG / Resume Failure 的真实 Worker 生命周期，以及 Scheduler Real API Execution 集合断言。

本轮 `00532fb` 已增加 Claim 成功后的 `pending → running` 同事务生命周期闭环，并由 targeted Unit 通过；但开发者本轮尚未使用 tenant-safe Gate 在“单一当前 main Worker”基线下重新执行完整 Resume / Scheduler Real API，因此**不得将 Phase 2.7 标记为验收通过**。

## 当前验证状态

以下仍未获得本轮开发者实际 PASS：

- Runtime Model Governance Real API；
- Workflow Resume / Resume DAG / Resume Failure Real API；
- Scheduler Real API；
- Tenant Safe Real API 全量 Gate；
- Backend default regression；
- Alembic upgrade head / current；
- Scheduler / Worker 实际生命周期验收。

已获得本轮实际结果：

- Durable Frontier Worker targeted Unit：`13 passed`。
- Runtime Governance 直接命令：因缺少 tenant-safe `ORGANIZATION_ID` 上下文而失败，不作为 Real API 产品结论。
- Workflow Resume 直接命令：因缺少 tenant-safe 上下文而 skipped，不作为 Real API 产品结论。
- Scheduler 直接命令：因缺少 `TRIGGER_WORKFLOW_ID` 而 fail-fast，不作为产品失败结论。

## 下一执行顺序

```text
1. 同步最新 main
2. 停止所有旧 Worker / Scheduler，确保只运行当前 main 代码
3. uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q
4. powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\05_run_durable_resume_real_tests.ps1
5. Scheduler targeted / restart Acceptance
6. powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
7. Backend default regression
8. uv run alembic upgrade head
9. Scheduler / Worker 实际生命周期验收
10. 只有上述 blocker 收口后，继续 Phase 2.8 Delegation Runtime Integration
11. 更新 Phase / Acceptance / Status / Error
```

## 本地服务要求

Unit 不需要外部服务。Real API / Runtime / Scheduler 验收需要开发者单独启动：

- PostgreSQL：`localhost:5432`；
- Redis：`localhost:6379`；
- API Service：`127.0.0.1:8000`；
- Worker Service：真实验收时必须只运行 1 个当前 `main` Worker；多 Worker 验收再按专门场景启动；
- Scheduler Service：Scheduler 生命周期验收时启动 1 个当前 `main` Scheduler；
- Real Provider fixture：由 Real API 测试本地启动；不提交远程 Secret。

测试 Gate 不自动启动或停止服务。
