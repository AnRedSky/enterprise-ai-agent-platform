# 2026-09-02 Trigger / Scheduler 包初始化循环依赖

## 现象

Backend Regression Gate 在 pytest collection 阶段失败，`app.main` 导入 Runtime Operator Action 后进入 Trigger Service；Trigger Service 导入 `WorkflowSchedulerRepository` 时会先初始化 `workflow_scheduler` 包，而该包级入口继续导入 Scheduler Runtime。Scheduler Runtime 原先又在模块顶层导入 `WorkflowTriggerService`，因此形成：

```text
Trigger Service
  -> workflow_scheduler 包
    -> Scheduler Runtime
      -> Trigger Service
```

最终 Python 访问处于 partially initialized 状态的 `app.services.trigger`，抛出 `ImportError`。

## 根因

`workflow_scheduler` 包的公开入口需要加载 Runtime，但 Runtime 同时把 Trigger Service 当作模块级依赖。Trigger Service 又需要 Scheduler Repository。这里的依赖实际只在 `tick_once()` 执行阶段使用，不需要在 Scheduler Runtime 模块初始化阶段建立。

## 修复

将 `WorkflowTriggerService` 从 `runtime.py` 的模块级导入移动到 `ScheduledTriggerScheduler.tick_once()` 内部延迟导入。这样保留正式领域入口，不新增第二套 Trigger Service，也不改变生产运行时依赖关系。

同时增加 API Contract 层的包初始化回归测试，直接验证 Trigger 与 Scheduler 两个正式领域包可以连续导入。

## 验证

本修复需要在本地 Backend 环境执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run pytest -q -W error tests/api_contract/test_service_import_boundaries.py tests/api_contract/test_api_agents_endpoints.py --tb=long
```

随后执行完整 Release Gate：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

本记录只记录根因与修复方案，不预填本地测试结果；验收结果以实际执行输出为准。
