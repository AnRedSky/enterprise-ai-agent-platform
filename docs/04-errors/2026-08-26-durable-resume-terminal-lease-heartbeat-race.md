# Durable Resume 终态租约心跳竞态

## 1. 现象

Durable Resume 的真实 PostgreSQL / Worker 验收中，Resume Execution 已进入 `failed` 终态后，Worker lease heartbeat 仍尝试更新 `worker_lease_expires_at`，触发 `ck_workflow_execution_worker_lease_pair`。

同时，在 Windows + pytest-asyncio 的真实 API 测试中出现 `Event loop is closed`、`NoneType.send` 以及 `Connection._cancel was never awaited`，这些是数据库连接在测试事件循环关闭后清理的次生表现，不是业务失败根因。

## 2. 根因

原 heartbeat 实现先 `SELECT` 当前 Worker ownership、状态和租约，再修改 ORM 对象并提交。该流程存在 TOCTOU 窗口：

1. heartbeat SELECT 到 `running + worker_owner`；
2. Runtime 在另一个事务中把 Execution 推进到 `completed/failed/cancelled` 并原子释放 ownership；
3. 已经读取旧 ORM 状态的 heartbeat 随后只更新 `worker_lease_expires_at`；
4. 数据库检查约束拒绝“终态 + 非空 lease”组合。

因此，单纯在 SELECT 条件中限制 `pending/running` 不能完成并发 fencing。

## 3. 修复

`WorkflowWorker._renew_lease_once()` 改为单条带 fencing 条件的 `UPDATE`：

- `id == execution_id`
- `worker_owner == 当前 Worker`
- `status IN ('pending', 'running')`
- `worker_lease_expires_at > now`

只有 `rowcount == 1` 才提交并继续 heartbeat；`rowcount == 0` 视为 ownership 已丢失并立即退出。这样终态释放与旧 Worker 心跳更新之间不再存在“读旧对象后覆盖终态”的窗口。

## 4. 验证要求

必须在本地真实环境执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_worker_lease_heartbeat.py tests/unit/test_workflow_worker_lease_fencing.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\05_run_durable_resume_real_tests.ps1
```

Real API Gate 前必须保持 API、Scheduler、Worker 均已按项目本地运行方式启动，并确认数据库已迁移到当前 head。

## 5. 边界

本修复不新增数据库结构，不改变 Durable Resume Checkpoint/lineage 契约；只修正 Worker heartbeat 与终态 lease release 的并发 ownership fencing。
