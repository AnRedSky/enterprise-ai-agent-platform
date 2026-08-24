# 2026-08-24 Scheduler tenant / misfire Gate 实测失败

## 1. 现象

修复 Scheduler misfire 循环导入后，开发者本地重新执行 Gate，应用导入已恢复，但新的 tenant isolation / misfire 集成与 Real API 验收暴露出三类实际问题：

1. PostgreSQL tenant isolation 集成测试在插入 `workflow_schedules` 时违反 `workflow_schedules_trigger_id_fkey`；测试数据在同一事务中依赖的 `workflow_triggers` 尚未明确 flush。
2. Scheduled Trigger Contract 已按设计增加默认 `misfire_policy=skip` 与 `catch_up_limit=10`，但旧单元 / Real API 断言仍按旧配置 Contract 做精确相等比较。
3. Runtime 生成的 Scheduler Execution idempotency key 使用 `planned_at` 秒级时间戳，而公开 Scheduler Contract 使用 interval slot 编号；两套键空间不一致导致 Real API 多实例 / Recovery 验收无法按统一 key 读取结果。

## 2. 根因

### 2.1 集成测试数据依赖未显式建立

测试一次性 `session.add_all()` 创建 Tenant、User、Workflow、WorkflowVersion、WorkflowTrigger 与 WorkflowSchedule。真实 PostgreSQL 外键要求 Schedule 的 `trigger_id` 必须先存在。测试本身需要按持久化依赖边界分阶段 flush，避免把 ORM flush 顺序当作测试前置条件。

### 2.2 Contract 变更后测试仍锁定旧输出

`ScheduledTriggerConfig` 已正式包含 `misfire_policy` 与 `catch_up_limit`，默认值分别为 `skip` 与 `10`。旧测试仍断言只有 `timezone` 与 `interval_seconds`，属于测试 Contract 未同步，而不是回退 Scheduler misfire 功能。

### 2.3 Scheduler 幂等键实现出现重复键规则

`ScheduledTriggerScheduler.idempotency_key()` 定义的正式键为：

```text
scheduled:{trigger_id}:{interval_slot}
```

Runtime 原实现却通过 `int(planned_at.timestamp())` 生成另一套键。该实现违反“同一外部 / 领域能力只保留一个正式入口”的原则，也直接破坏 Real API 的多实例收敛验证。

## 3. 修复边界

本轮修复：

- Runtime 统一复用 `ScheduledTriggerScheduler.idempotency_key()` 生成 slot Execution key；
- Runtime 按单个 slot 判断 `recovery`，历史槽位为 `true`，当前槽位为 `false`，避免一次 tick 的全局 misfire 状态污染当前槽位元数据；
- tenant isolation 集成测试先 flush Trigger，再创建 Schedule；
- Unit / Real API 测试同步到当前 Scheduled Trigger Contract；
- Real API Recovery 场景显式把真实 `workflow_schedules.next_run_at` 回拨一个槽位，并使用 `catch_up` + `catch_up_limit=2` 验证持久化 misfire 恢复，而不是依赖进程内伪造 recovery slot。

没有新增 Scheduler、Repository、Provider、Execution 或第二套幂等键实现。

## 4. 验证要求

本修复提交后必须由开发者本地实际执行：

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\04_scheduler_tenant_misfire_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
uv run pytest -q
```

在重新执行前，不将上述 Gate 标记为通过。
