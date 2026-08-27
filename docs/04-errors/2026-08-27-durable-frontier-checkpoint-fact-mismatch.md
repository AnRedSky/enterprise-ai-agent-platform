# Durable Frontier Checkpoint Fact Mismatch

- 日期：2026-08-27
- Phase：2.7 Terminalization / Replay Closure
- 状态：已修复，测试暂未执行

## 问题

`WorkflowExecutionCheckpointService.append_next_in_transaction()` 已经能够识别同一 `source Frontier + frontier_completed` 存在的 Durable completion fact，但此前只有在 `execution_status` 与 `state_data` 完全一致时才返回既有 fact；如果已有 fact 与本次请求存在 lifecycle 或 payload drift，代码会继续进入 sequence 分配并追加新的 Checkpoint。

这会把“同一 Durable identity 的冲突写入”错误地转化为“新的 Durable fact”，破坏 Replay convergence 和 completion fact uniqueness。

## 修复

现在 writer boundary 对已有 `frontier_completed` fact 采用 fail-closed 策略：

```text
0 facts
  -> 创建唯一 fact

1 fact
  -> lifecycle + payload 相同：返回既有 fact
  -> lifecycle 或 payload 不同：HTTP 409，禁止 add/flush

>1 facts
  -> HTTP 409，Durable fact 已分叉
```

不会因为 drift 重新分配 sequence。

## Unit Test

`backend/tests/unit/test_checkpoint_duplicate_completion_guard.py` 新增覆盖：

- existing completion + lifecycle drift -> reject；
- existing completion + payload drift -> reject；
- duplicate completion facts -> reject。

## 测试状态

本轮没有执行 pytest、Backend Regression、Migration、API、E2E 或本地手动测试。