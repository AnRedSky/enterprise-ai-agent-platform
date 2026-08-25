# 2026-08-25：Worker 手动运行日志中的 Node running→running 与预期失败路径区分

## 1. 现象

开发者基于 `main@9bb40c8` 完成 Backend Regression 与 Tenant Safe Real API Gate 后，直接运行 `uv run python run_worker.py`，Worker 日志出现三类结果：

```text
503: Circuit Breaker is open
409: Node 不允许从 running 到 running
404: Mock provider HTTP 404
504: Retry backoff exceeds workflow deadline
```

## 2. 初步分类

### 2.1 `503 Circuit Breaker is open`

属于 Circuit Breaker 负向业务路径。当前 Half-Open Probe Gate 已明确允许一个 Probe 得到 `503`，不能把该状态自动视为 Worker 故障。

### 2.2 `404 Mock provider HTTP 404`

属于 Mock Provider 负向测试场景。它验证 Provider HTTP 错误能够沿 Runtime → Execution 失败路径传播；不应通过修改 Worker 吞掉真实错误。

### 2.3 `504 Retry backoff exceeds workflow deadline`

属于 Retry Budget / Workflow Deadline 的设计边界。Runtime 在下一次重试的 backoff 超过 Workflow deadline 时主动终止，不应继续调度下一次 Runtime 调用。

### 2.4 `409 Node 不允许从 running 到 running`

该结果与 Node 状态机设计一致：`running → running` 被明确禁止，不能通过放宽状态机掩盖重复 Runtime。

它仍需要进一步确认数据库中是否存在：

```text
WorkflowExecution.status = pending
        AND
WorkflowNodeExecution.status = running
```

如果存在，该持久化状态属于 Worker ownership fencing 修复前遗留或异常恢复形成的不一致状态；当前阶段禁止自动 resume / 自动把 running Node 改回 pending。

## 3. 工程处理

新增只读诊断：

```text
backend/scripts/dev/inspect_worker_runtime_consistency.py
backend/scripts/dev/worker_runtime_consistency.ps1
```

诊断检查：

1. `pending Execution + running Node` 不变量；
2. `running Execution + expired Worker lease` 候选项；
3. 不修改任何 PostgreSQL 数据；
4. 不启动、停止或重启 API / Scheduler / Worker。

发现 `pending + running Node` 时返回退出码 `2`，要求人工结合 Execution ID、Worker owner、attempt 与日志进一步定位。

## 4. 本地验证

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python .\scripts\dev\inspect_worker_runtime_consistency.py

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev\worker_runtime_consistency.ps1
```

预期无异常时：

```text
[PASS] No pending Execution contains a running Node.
```

发现异常时：

```text
[ERROR] pending/running invariant: execution=<id> ...
[FAIL] Persistent state is inconsistent; do not resume these executions automatically.
```

## 5. 处理边界

本记录不把手工 `run_worker.py` 输出直接等同于 Release Gate 失败。正式质量结论仍以 Backend Regression、Migration、Tenant Safe Real API 与 Scheduler/Worker Recovery Acceptance 的实际结果为准。
