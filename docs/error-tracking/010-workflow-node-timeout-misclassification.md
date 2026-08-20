# 010 - Workflow Node Timeout 被错误分类为 Workflow Timeout

## 实际错误

开发者本地执行 Backend 默认回归：

```text
uv run pytest -q

1 failed, 204 passed, 10 deselected

test_run_marks_workflow_timeout_as_failed
assert failed_node_call.kwargs["error_code"] == "NODE_TIMEOUT"
实际值：WORKFLOW_TIMEOUT
```

测试场景中 Workflow `timeout_ms=10`，Node `timeout_ms=1`。Node 本身应先达到自己的超时边界，因此 Node 与 Execution 最终错误码都应为 `NODE_TIMEOUT`。

## 根因

`backend/app/services/workflow_execution.py` 原先使用：

```python
workflow_timeout = effective_timeout >= remaining
```

但 `effective_timeout` 是：

```python
effective_timeout = min(node_timeout_ms / 1000, remaining)
```

当 Workflow deadline 获胜时，`min()` 会使 `effective_timeout == remaining`；同时在毫秒级 Node timeout 场景中，事件循环调度、数据库/治理调用等执行开销会继续消耗 Workflow 剩余时间，使一个原本明确短于 Workflow deadline 的 Node timeout 被误判为 Workflow timeout。

## 影响

1. Node timeout 的 error_code 可能错误记录为 `WORKFLOW_TIMEOUT`。
2. Execution 的最终 error_code 同步错误。
3. Retry policy 对 `NODE_TIMEOUT` 与 `WORKFLOW_TIMEOUT` 的不同治理语义可能受到影响。
4. 毫秒级 timeout 测试具有时序敏感性。

## 修复方案

直接在 `main` 修复：

将 timeout 来源判断改为根据配置的 Node timeout 与当前 Workflow 剩余预算比较：

```python
workflow_timeout = remaining <= node_timeout_ms / 1000
```

这样不会因为 `min()` 的结果丢失“究竟是哪一个预算先到达”的语义；当 Node timeout 明确短于剩余 Workflow budget 时，`asyncio.TimeoutError` 分类为 `NODE_TIMEOUT`。

## 预防措施

- Node timeout 与 Workflow deadline 必须分别保留来源语义。
- 不使用 `min()` 后的 effective timeout 值反推 timeout 来源。
- 毫秒级 timeout 必须有稳定的单元测试覆盖。
- timeout 规则变更后必须重新执行 Backend 默认回归。

## 验证要求

开发者本地执行：

```powershell
cd backend
uv run pytest -q
```

重点验证：

```text
NODE_TIMEOUT test
WORKFLOW_TIMEOUT test
```

未由开发者实际执行前，不得标记 Backend regression 通过。
