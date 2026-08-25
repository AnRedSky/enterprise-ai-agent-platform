# Worker `running → running` 工程错误记录

## 1. 问题

Worker 在执行 Workflow 时出现：

```text
409: Node 不允许从 running 到 running
```

此前只读一致性诊断可以确认部分数据库遗留状态，但不能解释并消除 Worker 在重新消费 `pending Execution` 时再次进入 `running` 的恢复边界。

## 2. 根因边界

Node 状态机明确禁止 `running → running`，该规则不能通过放宽状态机解决。

Worker 的执行链为：

```text
claim pending Execution
    ↓
持久化 worker_owner + lease
    ↓
WorkflowExecutionService.run()
    ↓
Execution pending → running
    ↓
WorkflowRuntime
    ↓
Node pending/failed → running
```

如果 Worker 在 Node 已持久化为 `running` 后异常退出，而 Execution 仍处于 `pending`，下一次 Worker 接管时会再次进入 Runtime。原实现没有恢复阶段，会直接调用 `transition_node(node, "running")`，因此严格状态机得到 `409`。

这属于 **Worker 恢复边界缺失**，而不是 Node 状态机设计错误。

## 3. 整改原则

1. 保持 `running → running` 非法，不降低状态机约束。
2. 只有 Worker 已成功 claim 的 `pending Execution` 才允许执行恢复。
3. Runtime 开始前扫描该 Execution 遗留的 `running Node`。
4. 将遗留 Node 转为 `failed`，错误码固定为 `WORKER_RECOVERY_INTERRUPTED`。
5. 恢复后的 Node 通过现有 `failed → running` 合法入口重新进入 Runtime；恢复逻辑不复制 WorkflowRuntime 的 retry 算法。
6. Node 在恢复后发生的新失败仍由现有 Runtime retry policy 决定是否继续重试。
7. `transition_node` 继续通过 Execution 行锁和 worker ownership fencing 防止旧 Worker 修改新 Worker 已接管的 Execution。
8. 恢复逻辑只作为 Worker 消费路径的一部分，不改变 HTTP 手动 Run 的正常状态机。

## 4. 代码实现

新增 Worker 私有恢复入口：

```text
backend/app/services/workflow_worker/runtime.py
WorkflowWorker._recover_orphaned_running_nodes()
```

调用顺序调整为：

```text
claim_one()
  ↓
load Execution / Version / Workflow
  ↓
recover orphaned running nodes
  ↓
start lease heartbeat
  ↓
WorkflowExecutionService.run()
  ↓
WorkflowRuntime
```

恢复错误码：

```text
WORKER_RECOVERY_INTERRUPTED
```

恢复说明：

```text
Worker 接管 pending Execution 时发现遗留 running Node，已进入恢复态
```

## 5. 为什么不直接允许 `running → running`

如果把状态机修改成允许同状态转换，会隐藏真正的恢复边界，并可能让两个 Runtime 都继续调用 Provider。状态机应该继续作为并发异常的检测器，而不是吞掉异常。

本次修复选择：

```text
发现遗留 running
    ↓
显式记录恢复原因
    ↓
running → failed
    ↓
正常执行入口 failed → running
    ↓
WorkflowRuntime 继续处理节点
```

因此状态转换仍然完整可审计。

## 6. 自动化验证

新增单元测试：

```text
backend/tests/unit/test_workflow_worker.py
```

覆盖：

- 遗留 running Node 被统一恢复为 failed；
- 恢复错误码正确；
- 无遗留 Node 时恢复阶段无副作用；
- 原有 Worker dispatch / stop / 参数校验保持不变。

开发者本地执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_worker.py tests/unit/test_workflow_execution_worker_fencing.py
```

随后执行：

```powershell
uv run pytest -q
```

数据库状态验证：

```powershell
uv run alembic upgrade head
uv run alembic current
```

只读运行时一致性诊断：

```powershell
uv run python .\scripts\dev\inspect_worker_runtime_consistency.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev\worker_runtime_consistency.ps1
```

最终 Backend Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Real API / Worker 生命周期依赖真实服务时，继续使用项目既有 Tenant Safe Real API Gate，不由本修复脚本启动或停止服务。

## 7. 验收标准

- [ ] Node 状态机仍拒绝正常路径的 `running → running`。
- [ ] Worker 接管 `pending Execution + running Node` 时不会直接再次执行 `running → running`。
- [ ] 遗留 Node 有明确 `WORKER_RECOVERY_INTERRUPTED` 错误记录。
- [ ] 恢复后通过既有 `failed → running` 入口重新执行，不复制 retry 算法。
- [ ] ownership fencing 仍有效。
- [ ] Worker targeted tests 通过。
- [ ] Backend Regression Gate 通过。
- [ ] 实际 Worker 生命周期测试确认旧 Worker 不能继续推进新 Worker 接管后的 Execution。
