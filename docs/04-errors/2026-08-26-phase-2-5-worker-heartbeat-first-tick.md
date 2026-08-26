# Worker Heartbeat 首轮等待导致 Backend Regression 失败

- 发现日期：2026-08-26
- Phase：2.5 Scheduler → Worker 执行解耦
- 影响范围：Worker lease heartbeat、Backend Regression Gate
- 发现方式：开发者本地 `01_backend_regression_gate.ps1`

## 1. 现象

最新 `main` 基线执行 Backend Regression 时出现：

```text
test_lease_heartbeat_stops_when_ownership_is_lost
TimeoutError
```

测试构造 `lease_seconds=3`，heartbeat interval 为 `lease_seconds / 3 = 1s`。原实现进入 `_renew_lease_forever()` 后先执行 `asyncio.sleep(interval)`，再调用 `_renew_lease_once()`。当 ownership 已经丢失时，heartbeat 本应立即结束，但实际上必须先等待一个完整 interval，导致 1 秒测试门限超时。

## 2. 根因

原 heartbeat 循环顺序为：

```text
sleep(interval)
    ↓
renew lease
    ↓
发现 ownership 丢失
    ↓
退出
```

该顺序把“周期调度间隔”和“首次 ownership 校验”错误地绑定在一起。Worker claim 后立即创建 heartbeat task，首轮等待没有产品价值，反而扩大了 lease 生命周期边界的不确定性。

## 3. 整改

调整为：

```text
renew lease / ownership check
    ├── ownership 失效 → 立即退出
    ├── 瞬态数据库异常 → 记录并进入下一轮
    └── 成功 → sleep(interval) → 下一轮
```

同时新增单元测试，强制验证首次 heartbeat 不得先等待 interval。

## 4. 设计边界

- 不放宽 Node `running → running` 状态机。
- 不修改 claim / ownership fencing 规则。
- 不允许 lease 到期后旧 Worker 复活 ownership。
- 不复制第二套 Runtime。
- heartbeat 的 interval 只负责后续周期调度；首轮必须立即执行 ownership 检查。
- 本修复不改变瞬态数据库异常的重试语义。

## 5. 验证要求

代码修复提交后，必须由开发者本地实际执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_worker.py tests/unit/test_workflow_execution_worker_fencing.py tests/unit/test_workflow_worker_lease_heartbeat.py

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

随后继续执行 Tenant Safe Real API、Worker Runtime consistency diagnostic 与 Scheduler / Worker Recovery Acceptance。未实际执行前不得记录为 Passed。
