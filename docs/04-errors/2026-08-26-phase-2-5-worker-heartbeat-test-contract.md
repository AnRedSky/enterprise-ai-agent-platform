# Worker Heartbeat 测试契约与生产时序不一致

- 发现日期：2026-08-26
- Phase：2.5 Scheduler → Worker 执行解耦
- 影响范围：Worker lease heartbeat 单元测试
- 发现方式：开发者本地 Worker targeted test

## 1. 现象

在 `f2413b2` 的 heartbeat 首轮立即 ownership 检查整改后，Worker targeted test 出现：

```text
assert calls == 2
assert sleeps == 2
E       assert 1 == 2
```

对应测试场景为：

```text
第 1 次 renew → 瞬态 ConnectionError
第 2 次 renew → ownership=False
```

生产实现已经在首次 renew 前不等待 interval，并且在 ownership 明确失效后立即退出，因此实际 sleep 次数应为 1，而不是 2。

## 2. 根因

测试只描述了“瞬态失败后继续重试”，但没有把 heartbeat 的完整时序契约表达清楚，仍然隐含了“每一次尝试之后都必须 sleep”的旧假设。

正式时序应为：

```text
heartbeat task 创建
        ↓
立即 renew / ownership check
        │
        ├── ownership=False
        │       ↓
        │     立即退出
        │     不再 sleep
        │
        ├── 瞬态数据库异常
        │       ↓
        │     记录日志
        │       ↓
        │     sleep(interval)
        │       ↓
        │     下一次 renew
        │
        └── renew=True
                ↓
            sleep(interval)
                ↓
            下一次 renew
```

因此，sleep 的语义是“准备进入下一轮”，不是“当前 renew 尝试结束后的固定动作”。

## 3. 测试整改

将断言从：

```text
calls == 2
sleeps == 2
```

调整为：

```text
calls == 2
sleeps == 1
```

其中唯一一次 sleep 对应：

```text
瞬态异常 → 记录 → sleep → 重试
```

第二次 renew 返回 ownership 已失效后直接退出，因此不允许再 sleep。

## 4. 设计边界

- 不改变 heartbeat 生产实现。
- 不允许首次 heartbeat 先等待 interval。
- 不允许明确失去 ownership 后继续 sleep / retry。
- 瞬态数据库异常仍必须继续重试。
- lease 已过期时不得通过 heartbeat 复活 ownership。
- 测试必须验证完整时序，而不是只验证调用次数。

## 5. 验证要求

开发者本地应执行：

```powershell
cd backend
uv run pytest -q `
  tests/unit/test_workflow_worker.py `
  tests/unit/test_workflow_execution_worker_fencing.py `
  tests/unit/test_workflow_worker_lease_heartbeat.py
```

随后再执行 Backend Regression Gate。以上命令在开发者本地实际执行前，不记录为 Passed。
