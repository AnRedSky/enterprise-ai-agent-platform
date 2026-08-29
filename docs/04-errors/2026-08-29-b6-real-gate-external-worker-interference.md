# Phase 2.8 B6 Real Gate：外部 Worker/Scheduler 干扰

- 日期：2026-08-29
- 阶段：Phase 2.8 B6 Multi-Worker Durable Frontier Runtime
- 状态：已修复测试环境隔离问题，等待本地重新验收

## 现象

本地 B6 Real Gate 的 Unit/Regression/Migration 全部通过，但 Real API 出现两类失败：

1. `test_delegation_is_consumed_by_multiple_worker_instances_through_durable_frontier` 在创建 Delegation 的 HTTP 请求期间出现 `httpx.ReadError: [WinError 10053]`。
2. `test_b1_atomic_claim_allows_one_worker_and_persists_one_execution` 两个显式竞争 Worker 均收到 `409: Delegation 当前状态为 running，不能再次 Claim`，没有任何一个测试 Worker 成功 Claim。

## 根因

本次 B6 Real Gate 明确要求通过测试内创建的 `WorkflowWorker` 实例验证 Delegation Claim、Durable Frontier 和 Runtime 消费边界。若本地同时运行独立的 `run_worker.py` 或 `run_scheduler.py`，后台进程也会消费 PostgreSQL 中刚创建的 pending Delegation/Workflow Execution。

因此 B1/B6 Real API 测试与外部后台消费者之间形成合法业务竞争：

```text
Real API Test                 External Worker
     |                              |
     | create pending Delegation    |
     |----------------------------->|
     |                              | claim
     | explicit Worker claim        |
     |----------------------------->|
     |                              | already running
     |             409               |
```

这不是 Atomic Claim 生产逻辑错误；恰恰是生产 Claim 正确地拒绝第二个竞争者。但验收测试需要证明“两个指定测试 Worker 中一个成功”，因此必须禁止未受控的第三方 Worker/Scheduler 参与。

## 修复

`backend/scripts/test/phase-2.8/06_delegation_multi_worker_runtime_gate.ps1` 新增 `Assert-NoExternalWorkerProcesses`：

- Windows 检测 `run_worker.py` / `run_scheduler.py` 进程命令行。
- 支持 `pgrep` 的环境检测同类进程。
- 发现外部消费者时在 `[0/4]` 前置检查阶段立即失败。
- 不自动启动、重启或停止任何服务。
- 不要求填写 Token、用户、Tenant、Delegation 或其他测试数据。

这样可以在测试真正创建数据前阻止环境污染，避免产生误导性的 B1/B6 运行时结果。

## 为什么不自动停止 Worker

项目测试治理要求 Real Gate 不替用户管理独立服务生命周期。自动停止后台 Worker 会修改用户当前运行环境，并可能影响其他测试/开发任务。因此 Gate 只做确定性的环境检查并给出明确失败原因。

## 验证要求

重新执行 B6 Gate 时应首先看到：

```text
[0/4] Local prerequisite service verification (no service startup)
```

若存在外部 Worker/Scheduler，应在这里明确失败；不存在时才进入 Unit、Regression、Migration 和 Real HTTP + PostgreSQL 验收。
