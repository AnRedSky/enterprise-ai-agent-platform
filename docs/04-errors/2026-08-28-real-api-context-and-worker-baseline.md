# 2026-08-28 Real API Context 与 Worker Baseline 测试边界

## 1. 现象

开发者直接执行 Real API 测试文件，而没有先运行 tenant-safe bootstrap：

```text
uv run pytest tests/api_real/test_runtime_model_governance_api.py -q -m real_api
```

Runtime Governance 测试因 `ORGANIZATION_ID` 缺失而 fail-fast；Workflow Resume 测试在相同条件下 skip；Scheduler 测试因 `TRIGGER_WORKFLOW_ID` 缺失而 fail-fast。

同时，上一轮 tenant-safe Real API 执行曾发现多个 `run_worker.py` 进程同时运行。多个 Worker 消费同一 PostgreSQL Durable Frontier 时，测试结果不能证明当前 `main` Worker 的行为。

## 2. 根因

Real API 测试的身份、tenant、Workflow 与 Trigger 上下文由专用 bootstrap 生成，不属于普通 pytest collection 的隐式 fixture。直接执行测试文件不会自动获得这些环境变量。

Worker 运行态则是独立于测试进程的持久化消费者。多个 Worker 同时运行时，任意一个 Worker 都可能 Claim 测试创建的 Frontier，导致：

```text
测试创建 Execution
        ↓
Worker A / Worker B / Worker C 竞争 Durable Frontier
        ↓
结果无法归因到当前源码 baseline
```

## 3. 处理

Real API Gate 不自动启动或停止服务，但现在在执行测试前 fail-fast 检查 Worker 数量：

- 必须存在 Worker；
- 必须且只能存在一个 `run_worker.py` 进程；
- 多 Worker 时输出 PID / CommandLine，并要求开发者先停止旧 Worker；
- Durable Resume 专用 Gate 与 Tenant Safe Full Gate 均执行该检查。

直接 pytest 命令只用于已经准备好环境变量的针对性调试，不作为正式 Real API 验收入口。

## 4. 正式验收入口

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend

# Durable Frontier Unit
uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q

# Durable Resume Real API
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\05_run_durable_resume_real_tests.ps1

# Tenant-safe Full Real API
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

## 5. 验收边界

本记录只处理测试上下文与 Worker baseline 问题，不将缺少环境变量的直接 pytest 结果解释为生产功能失败，也不将上一轮 7 failed 的 Real API 结果重新标记为通过。

`00532fb` 的 Durable Frontier Claim → Execution `pending → running` 修复必须在单一当前 `main` Worker 基线下重新执行真实 Resume / Scheduler Gate 后，才能确认 Phase 2.7 blocker 是否真正关闭。
