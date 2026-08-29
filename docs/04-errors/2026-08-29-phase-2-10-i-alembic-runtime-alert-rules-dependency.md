# Phase 2.10-I Alembic 迁移拓扑导致 `runtime_alert_rules` 缺失

## 1. 现象

本地执行 `uv run alembic upgrade heads` 时，0045 告警生命周期迁移在创建 `runtime_alert_instances` 时失败：

```text
asyncpg.exceptions.UndefinedTableError: relation "runtime_alert_rules" does not exist
```

同一环境下 Scheduler 启动也会因查询 `runtime_alert_rules` 失败而退出；该问题进一步导致 Backend 测试在导入 runtime operations 包时无法正常进入业务测试阶段。

## 2. 根因

0043 之后存在两个并行的 0044 migration：

- `0044_runtime_operations_enterprise`：创建 `runtime_alert_rules`；
- `0044_webhook_destination_provider`：补充 Webhook Destination Provider 元数据。

0045 同时把两个 0044 写入 `down_revision` 元组，但真实本地 Alembic 执行从 0043 升级时只先执行了 Webhook Provider 分支，随后进入 0045；0045 创建告警实例表时，`runtime_alert_rules` 尚不存在。

因此问题不是业务 Service 查询顺序，而是 migration graph 没有形成可执行且明确的依赖关系。

## 3. 修复

0045 改为：

```python
down_revision = "0044_webhook_destination_provider"
depends_on = "0044_runtime_operations_enterprise"
```

这样 0045 仍保持 Webhook Provider 分支的线性父节点，同时通过显式 `depends_on` 要求 Runtime Operations 分支先完成，确保 `runtime_alert_rules` 在 0045 创建外键之前已经存在。

同时更新 `tests/unit/test_migration_graph.py`，从检查双 `down_revision` 改为检查 `down_revision + depends_on`，避免测试继续固化错误拓扑。

## 4. 测试 Gate 调整

`backend/scripts/test/phase-2.10/03_alert_notification_lifecycle_real_gate.ps1` 改为只检查 Scheduler / Worker 已经运行，不再自动启动或停止任何服务。

测试身份、租户、规则、Policy、Destination、Subscription 和业务数据仍由测试自动生成与清理，不要求人工填写测试数据。

## 5. 验证要求

修复提交后必须在本地实际执行：

```powershell
cd backend
uv run alembic heads
uv run alembic upgrade heads
uv run alembic current
uv run pytest -q tests/unit/test_migration_graph.py
```

随后在已手动启动 API / Scheduler / Worker 的环境执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\03_alert_notification_lifecycle_real_gate.ps1
```

本记录只描述已发现的工程错误与修复方案，不预填本地验收结果。
