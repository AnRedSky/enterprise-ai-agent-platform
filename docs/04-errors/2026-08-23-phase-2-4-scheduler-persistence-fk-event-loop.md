# Phase 2.4 Scheduler Persistence Gate：FK 顺序与 asyncpg 事件循环错误

## 1. 发现时间

2026-08-23

## 2. 现象

开发者在本地执行 Scheduler Persistence Gate 时出现两类失败：

1. `workflow_schedules.trigger_id` 外键插入失败：测试在同一个 `session.begin()` 中同时新增 `WorkflowTrigger` 与 `WorkflowSchedule`，但两个 ORM 对象没有显式 relationship，flush 顺序未保证先写入 Trigger。
2. 第二个 PostgreSQL integration test 出现 `Event loop is closed` / `asyncpg ... NoneType.send`，根因是 pytest-asyncio 当前配置为 function 级事件循环，而 SQLAlchemy asyncpg 连接池连接被后续测试复用到新的事件循环。

同时发现模块化整改尚未清除数据库 Session 的重复实现：`app.dependencies.db` 与 `app.infrastructure.db.session` 各自创建独立 SQLAlchemy Engine / SessionLocal。该重复入口会放大连接池生命周期问题，也违反 Backend 模块化规则中“同一能力只能保留一个正式实现”的要求。

## 3. 修复原则

- 不修改 Scheduler 生产业务语义；
- 不通过 JSON / Mock 替代 PostgreSQL integration；
- API 层仅通过 `app.infrastructure.db` 使用唯一数据库 Session；
- 删除 `app.dependencies.db` 重复数据库实现；
- Scheduler integration fixture 明确 flush FK 前置实体后再建立依赖实体；
- pytest-asyncio 使用 session 级事件循环，避免 asyncpg pool 跨 loop 复用；
- 相关模块补充中文职责说明。

## 4. 验收要求

本记录对应代码提交后，开发者必须重新执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_scheduler_contract.py tests/unit/test_workflow_scheduler_persistence_contract.py tests/unit/test_workflow_scheduler_repository.py
$env:RUN_DATABASE_INTEGRATION="1"
uv run pytest -q tests/integration/test_workflow_scheduler_repository.py
Remove-Item Env:RUN_DATABASE_INTEGRATION
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_scheduler_persistence_gate.ps1
```

只有上述 PostgreSQL integration / Persistence Gate 实际通过后，才能继续将 Phase 2.4 推进到 Scheduler API Contract 与 Runtime persistence 闭环。

## 5. 当前状态

本记录仅记录开发者提供的失败证据与代码修复，不将尚未重新执行的本地测试标记为 Passed。
