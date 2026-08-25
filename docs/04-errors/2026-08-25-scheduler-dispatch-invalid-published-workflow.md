# 2026-08-25 Scheduler 调度消费已发布空 Workflow Definition

## 1. 现象

开发者本地运行 `uv run python run.py` 后，后台 Scheduler 持续输出：

```text
Scheduled Trigger dispatch failed
fastapi.exceptions.HTTPException: 422: Workflow definition 必须包含非空 nodes
```

调用链为：

```text
ScheduledTriggerScheduler.tick_once
  -> WorkflowTriggerService.invoke_scheduled
  -> WorkflowRuntime.validate_definition
  -> 422 Workflow definition 必须包含非空 nodes
```

## 2. 根因

`WorkflowRuntime.validate_definition()` 已经将 `nodes` 非空定义为 Runtime Contract，但 `WorkflowRegistry.publish()` 在发布版本时此前没有复用该 Contract。

因此存在以下非法状态迁移：

```text
draft WorkflowVersion
    -> definition = {"nodes": []}
    -> publish()
    -> Workflow.status = published
    -> Workflow.published_version_id = invalid version
    -> Scheduled Trigger 被 Scheduler 消费
    -> Runtime 首次校验时才失败
```

Scheduler 报错本身不是 `validate_definition()` 的错误；它是在执行边界正确拒绝不可执行定义。真正的工程缺陷是非法 Definition 可以越过 Workflow 发布边界进入 `published` 状态。

## 3. 修复

本次修复在 `backend/app/services/workflow/registry.py` 的 `WorkflowRegistry.publish()` 中，在任何发布状态变更之前调用唯一的 `WorkflowRuntime.validate_definition()`。

这样发布阶段即阻断：

- 空 `nodes`；
- 非对象 node；
- 重复 node id；
- 非法 node type；
- 非法 node config；
- 非法 Runtime timeout / retry / circuit breaker 配置。

不新增第二套 Workflow Definition 校验实现，保持 Runtime Contract 单一入口。

## 4. 为什么不修改 Scheduler 来吞掉 422

该异常属于不可执行 Workflow Definition 的配置/治理错误，不是 transient Scheduler contention，也不是 lease 或 idempotency contention。

如果 Scheduler 把该异常静默吞掉，只会把已经非法发布的数据继续留在生产状态，并掩盖 Workflow 发布边界缺陷。因此本修复优先恢复领域不变量：**published WorkflowVersion 必须满足 Runtime Definition Contract**。

现有已经写入数据库的非法 published version 不会被本次代码自动修改。开发者需要在本地数据库中修复该历史数据，例如删除/停用对应 Trigger、创建合法 Definition 的新版本并重新发布，然后重新启动 Scheduler 验证日志不再出现。

## 5. 验证要求

### 5.1 定向单元测试

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_registry.py
```

预期：新增测试通过，并确认无 `commit()` 发生。

### 5.2 Backend 默认回归

```powershell
cd backend
uv run pytest -q
```

### 5.3 本地 Scheduler 烟囱验证

1. 先停止现有 API/Scheduler 进程。
2. 修复数据库中的历史非法 published WorkflowVersion。
3. 执行 `uv run python run.py`。
4. 观察 Scheduler 连续至少两个 poll interval。
5. 不应再针对该合法 Workflow 输出 `Workflow definition 必须包含非空 nodes`。
6. 再执行 Backend Regression Gate 与需要的 Real API / Browser Gate。

## 6. 验收边界

本次修复只改变 Workflow Version 的发布前置校验，不改变 Scheduler 的 lease、slot、misfire、idempotency、tenant isolation 或 restart recovery Contract。

本次代码提交前未虚构本地 Gate 结果；最终通过状态以开发者本地实际执行结果为准。
