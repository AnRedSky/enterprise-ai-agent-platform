# 2026-08-25 Scheduled Trigger 历史 Workflow Definition 兼容

## 1. 现象

本地启动 Backend 后，Scheduler 持续输出：

```text
Scheduled Trigger dispatch failed
HTTPException: 422: Workflow definition 必须包含非空 nodes
```

调用链为：

```text
Scheduler tick
  -> WorkflowTriggerService.invoke_scheduled
  -> WorkflowRuntime.validate_definition
  -> historical published WorkflowVersion.definition
  -> {"nodes": []}
```

## 2. 根因

当前 Runtime Definition Contract 已收紧为：

- `nodes` 必须为非空数组；
- 每个 node 必须为对象；
- node 必须包含合法 `id` / `type`；
- node config 与 Runtime 配置必须通过统一校验。

但是数据库中已经存在 Contract 收紧前创建的历史 `published` Workflow Version。历史数据中的 `{"nodes": []}` 在当时可以作为无操作 Workflow 保存，但现在直接进入 Scheduler 执行校验会被当作新版本非法 Definition。

## 3. 兼容边界

本次不降低新版本发布 Contract，也不把任意非法历史节点转换为新节点。

唯一兼容范围：

```text
已发布历史版本 + nodes == []
    -> Scheduler 显式开启历史兼容
    -> 作为无操作 Workflow 执行并正常完成

新版本 draft/testing -> published
    -> 默认严格 Runtime Contract
    -> nodes == [] 仍然拒绝

历史 published + nodes 非空但包含非法 node
    -> 仍然拒绝
```

这样可以保持历史审计数据可执行，同时防止兼容开关成为新的 Definition 校验后门。

## 4. 实现

- `WorkflowRuntime.validate_definition()` 增加 `allow_legacy_empty_nodes` 显式开关；默认值保持严格 Contract。
- `WorkflowRuntime.execute()` 透传该兼容边界。
- `WorkflowExecutionService.run()` 透传该兼容边界。
- `WorkflowTriggerService.invoke_scheduled()` 仅 Scheduler 路径显式开启该开关。
- manual / 普通 Execution 创建路径不启用兼容开关。
- 新增 `test_workflow_definition_legacy_compatibility.py`，覆盖严格拒绝、显式兼容以及非法非空节点仍拒绝三个边界。

## 5. 为什么不直接修改历史数据库数据

历史 Workflow Version 属于版本与审计记录，不能通过批量重写历史 Definition 来伪造新的节点语义。对于空节点，其旧语义可以确定为无操作 Workflow，因此可以安全兼容；对于字符串节点等缺少 `type/config` 的旧形态，无法可靠推断原执行语义，因此继续拒绝。

如果后续确认所有历史空节点都不再需要执行，应由独立的数据生命周期任务归档或停用对应 Workflow/Trigger，而不是扩大 Runtime 兼容范围。

## 6. 验证

必须由开发者本地实际执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_definition_legacy_compatibility.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

启动真实 Backend 后还应确认 Scheduler 日志不再对历史空节点 Trigger 周期性抛出同一 422。

本记录不预填测试通过状态，最终状态以开发者本地实际执行结果为准。
