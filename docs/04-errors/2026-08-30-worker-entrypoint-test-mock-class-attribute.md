# Worker 入口生命周期测试 Mock 类属性缺失

## 1. 发现时间

2026-08-30

## 2. 影响范围

- `backend/tests/unit/test_worker_entrypoint.py`
- `backend/app/entrypoints/worker.py`
- Worker Service 入口生命周期单元测试

## 3. 现象

执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_worker_entrypoint.py
```

结果为 `1 failed, 2 passed`。

失败位置：`run_worker_service()` 创建 `WebhookDeliveryWorker` 时读取 `WebhookDeliveryWorker.DEFAULT_CONCURRENCY`，但测试使用普通 `lambda` 替换了该类：

```text
AttributeError: 'function' object has no attribute 'DEFAULT_CONCURRENCY'
```

## 4. 根因分析

生产代码依赖 `WebhookDeliveryWorker.DEFAULT_CONCURRENCY` 作为构造参数默认值。该属性属于类级契约，而不是实例属性。

测试为了隔离真实 Worker，将 `WebhookDeliveryWorker` 替换成返回 `MagicMock` 实例的普通函数。普通函数本身不具备生产类的 `DEFAULT_CONCURRENCY` 类属性，因此测试在进入 Worker 主循环之前就失败。

该问题属于测试替身没有保持被替换对象的最小类级契约，并非 `WebhookDeliveryWorker` 生产实现的默认并发值错误。

## 5. 修复方案

将测试中的 Worker 构造替身改为可调用 `MagicMock`，并显式提供生产代码需要的类级契约：

- `webhook_worker_factory.return_value = webhook_worker`
- `webhook_worker_factory.DEFAULT_CONCURRENCY = 4`
- 保持真实构造参数 `lease_seconds=60`、`max_attempts=5`、`concurrency=4` 的断言。

不修改生产代码，不增加兼容层，也不复制 Worker 实现。

## 6. 回归要求

至少执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_worker_entrypoint.py
```

随后执行 Backend default regression：

```powershell
cd backend
uv run pytest -q
```

## 7. 测试边界

该单元测试不启动 API、Worker、Scheduler、PostgreSQL 或 Redis，不产生真实外部副作用；真实 Runtime Acceptance 继续通过独立 Gate 执行，并由 Gate 检查依赖服务是否已由开发者预先启动。
