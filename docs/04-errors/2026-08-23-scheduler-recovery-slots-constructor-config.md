# Scheduler recovery slot 构造参数回归

## 发生时间

2026-08-23

## 现象

Backend Module Refactor Gate 在 Backend default regression 阶段失败：

```text
test_scheduler_recovery_slots_remains_callable_after_constructor
assert [5957569, 5957570] == [5957568, 5957569, 5957570]
```

测试创建 `ScheduledTriggerScheduler(recovery_slots=3)` 后，实例的 `max_recovery_slots` 已为 `3`，但 `recovery_slots(now, 300)` 仍使用类方法默认值 `DEFAULT_RECOVERY_SLOTS=2`，因此只返回两个槽位。

## 根因

`ScheduledTriggerScheduler.recovery_slots` 同时承担了“槽位计算工具”和“实例配置计算”两个语义，但实现为 `@classmethod`，其默认参数固定读取类级 `DEFAULT_RECOVERY_SLOTS`，没有使用构造函数保存的 `max_recovery_slots`。

这导致构造函数传入的恢复槽位配置无法影响实例方法调用，形成配置与运行行为不一致。

## 修复

将 `recovery_slots` 收敛为实例方法：

- 未显式传入 `max_recovery_slots` 时使用实例的 `max_recovery_slots`；
- 显式传入时仍允许调用方覆盖实例配置；
- 保留统一的 `MAX_RECOVERY_SLOTS` 边界校验；
- 不新增第二套槽位计算实现，继续复用 `interval_slot`。

## 验证边界

修复提交后必须由开发者本地执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_scheduled_trigger_scheduler.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

在开发者反馈实际执行结果前，不将本修复标记为 Gate 已通过。
