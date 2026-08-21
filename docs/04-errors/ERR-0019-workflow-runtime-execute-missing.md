# ERR-0019 — WorkflowRuntime 缺失 execute 导致真实 Workflow Execution 500

## 状态

**Open — 已定位并提交修复，等待开发者本地验证。**

## 发现阶段

Phase 1.9-C Real API Reliability Scenarios。

## 现象

Real API bootstrap 在创建 Retry boundary fixture 后调用：

```text
POST /api/v1/workflows/executions/{execution_id}/run
```

预期 bootstrap 使用 404 场景继续初始化，但实际返回：

```text
500 Internal Server Error
{"detail":"Workflow Runtime 执行失败"}
```

Backend 日志进一步显示：

```text
AttributeError: 'WorkflowRuntime' object has no attribute 'execute'
```

同一错误也影响 Scheduled Trigger dispatch。

## 根因

`WorkflowExecutionService.run()` 已经调用：

```python
await runtime.execute(execution, version, actor_id, admin)
```

但当前 `WorkflowRuntime` 只保留了 `execute_node()`，缺少 Runtime orchestration 层的 `execute()` 方法。

因此真实 HTTP Execution Run 与 Scheduled Trigger 都在进入 Runtime 后直接抛出 `AttributeError`，最终被包装成 HTTP 500。

## 修复

在 `backend/app/runtime/workflow_runtime.py` 恢复 `WorkflowRuntime.execute()`，负责：

- 按 definition 声明顺序执行 nodes；
- 通过 `execute_node()` 执行具体节点；
- 应用 node timeout 与 workflow deadline；
- 应用显式 retry policy；
- 应用 workflow retry budget；
- 记录 node failed/completed 状态；
- 对 `CIRCUIT_OPEN` / `WORKFLOW_TIMEOUT` 不进行 retry；
- retry backoff 超过剩余 workflow deadline 时直接结束为 timeout；
- 全部 node 完成后将 Workflow Execution 标记为 completed。

修复提交：

```text
0cb983f979962d182a519a380511284cc11e2cda
fix: restore workflow runtime execution orchestration
```

## 验证边界

代码修复已经提交，但尚未取得开发者本地重新执行的测试结果，因此本错误不能关闭。

必须至少验证：

1. Phase 1.9-C Real API bootstrap 可以成功完成；
2. 既有 Backend Regression 不回归；
3. Real API Gate 全量通过；
4. Scheduled Trigger 不再出现 `WorkflowRuntime.execute` AttributeError；
5. Workflow timeout/retry 单元测试继续通过。
