# Runtime Alerting 测试双事务边界错误

## 1. 现象

Backend Regression 在修复 Workflow Frontier stale lease fixture 后，首个失败移动到 `tests/unit/test_runtime_alerting.py::test_evaluator_returns_firing_transition_and_persists_lifecycle_audit`。

失败信息：

```text
AttributeError: '_DB' object has no attribute 'begin_nested'
```

失败调用链：

```text
RuntimeAlertEvaluator.evaluate
  -> _publish_transition
    -> RuntimeIntegrationEventPublisher.publish
      -> db.begin_nested()
```

## 2. 根因

生产 `RuntimeIntegrationEventPublisher` 明确定义了事务内 Durable Integration Event 写入边界，并使用 SQLAlchemy `AsyncSession.begin_nested()` 建立 savepoint，以便利用数据库唯一约束处理幂等冲突。

告警单元测试为了隔离 PostgreSQL，使用了最小 `_DB` 测试双，但该测试双只实现了 `execute`、`scalar`、`add`，没有实现 publisher 依赖的 `begin_nested()` 与 `flush()` AsyncSession 契约。

因此本次失败属于 **测试双契约不完整**，不是 Runtime Alert Evaluator 或 Integration Event Publisher 的生产逻辑错误。

## 3. 修复原则

不降低生产事务安全边界，不在生产代码中加入 `hasattr(db, ...)`、测试专用分支或绕过 savepoint 的兼容逻辑。

测试双补齐生产代码实际依赖的最小 AsyncSession 行为：

- `begin_nested()`：提供异步上下文管理器，模拟 savepoint 生命周期；
- `flush()`：提供异步 no-op，使 Repository create 的持久化契约可以完整执行。

同时增加对 Durable Integration Event 的断言，确保测试不仅验证告警状态转换，也验证通知层唯一事实入口确实产生 `runtime.alert.firing` / `runtime.alert.recovery` 事件及稳定幂等键。

## 4. 边界规则

后续新增测试双时，必须先检查被测 Service/Repository/Provider 实际调用的 Session、Transaction、Repository 或外部依赖契约。测试双可以最小化实现，但不得遗漏被测路径真实依赖的事务语义。

不得为了让测试通过而修改生产代码弱化事务、租约、fencing、幂等或 tenant isolation 约束。

## 5. 验证顺序

```powershell
uv run pytest -q tests/unit/test_runtime_alerting.py
uv run pytest -q --maxfail=1 -x --tb=long
uv run pytest -q
```

最终通过状态必须以开发者本地实际执行结果为准。
