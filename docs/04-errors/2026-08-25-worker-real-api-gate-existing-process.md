# Worker Real API Gate 检测到已有 Worker 进程

## 发生时间

2026-08-25

## 问题

执行 Backend Regression Gate 的 Tenant Safe Real API Gate 时，脚本在启动临时 Worker Service 前主动检查 `run_worker.py` 进程。

本地已经按当前服务化架构手动启动 Worker Service，因此检测到两个现有 `run_worker.py` 进程后，Gate 直接失败，尚未进入真实 HTTP API 测试。

典型输出：

```text
检测到已有 Worker Service 进程。Tenant Safe Real API Gate 将启动独立 Worker 消费 scheduled Execution，请先停止以下进程后重新执行
```

## 根因

测试 Gate 的进程隔离假设与当前本地服务启动方式不一致：

- 当前 API、Scheduler、Worker 均允许作为独立服务手动启动。
- Tenant Safe Real API Gate 也需要能够在已有 Worker Service 存在时重复执行。
- 旧 Gate 将“已有 Worker”视为测试前置冲突，而不是可复用的执行消费者。
- Workflow Worker 使用 PostgreSQL `pending Execution + worker lease + skip locked` 进行竞争认领，因此多个 Worker 可以安全竞争同一执行队列；测试夹具本身具有独立数据边界。

## 修复

Tenant Safe Real API Gate 改为：

1. 先检查是否已有 `run_worker.py` Worker Service。
2. 如果存在，则复用现有 Worker，不再启动第二个消费者。
3. 如果不存在，则由 Gate 启动临时 Worker Service。
4. 只有 Gate 自己启动的 Worker 才在 `finally` 中停止。
5. 已有 Worker 不由 Gate 停止，避免破坏开发者本地独立服务生命周期。
6. Scheduler restart acceptance 仍要求独立执行，并继续禁止其他 Scheduler/Worker 进程参与，以保证服务重启恢复测试的进程边界明确。

## 验证要求

代码提交后必须重新执行：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

其中 Tenant Safe Real API Gate 在存在本地 Worker Service 时应输出 `reusing it instead of starting a duplicate consumer`，并继续进入真实 HTTP API 测试，而不是提前失败。
