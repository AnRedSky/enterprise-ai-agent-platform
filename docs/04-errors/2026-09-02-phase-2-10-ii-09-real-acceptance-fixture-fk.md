# 2026-09-02 — Phase 2.10-II / II-09 Real PostgreSQL 验收夹具违反 Workflow 发布版本外键约束

## 1. 现象

开发者执行：

```powershell
uv run pytest -q -W error tests/api_real/test_operator_action_result_lineage_acceptance.py -m real_api
```

测试在创建 Workflow / WorkflowVersion / WorkflowExecution 夹具时失败：

```text
ForeignKeyViolationError: insert or update on table "workflows"
violates foreign key constraint "fk_workflows_published_version_id"
DETAIL: Key (published_version_id)=... is not present in table "workflow_versions".
```

## 2. 根因

`workflows.published_version_id` 在实际 PostgreSQL schema 中受 `workflow_versions.id` 外键约束，同时 `workflow_versions.workflow_id` 又依赖 `workflows.id`。原验收夹具在同一个 flush 中同时创建：

- `Workflow(published_version_id=version_id)`；
- `WorkflowVersion(id=version_id, workflow_id=workflow_id)`。

虽然两个对象都加入了 SQLAlchemy Session，但该夹具没有显式表达这个循环外键的两阶段持久化顺序，数据库实际收到 Workflow INSERT 时，目标 WorkflowVersion 尚不存在，因此被 PostgreSQL 正确拒绝。

这不是业务生产逻辑错误，而是 Real PostgreSQL 验收夹具没有遵守真实数据库约束顺序。

## 3. 修复

将夹具改为显式两阶段写入：

1. 先创建 Tenant、User、Workflow（`published_version_id=NULL`）和 Published WorkflowVersion；
2. `flush()` 后将 Workflow 状态更新为 `published` 并设置 `published_version_id`；
3. 再创建 failed WorkflowExecution；
4. 最终一次 commit。

同时增加同一 Idempotency-Key 的第二次 Retry 调用，验证重复请求直接复用同一个 Result Resource，不重复产生 Operator Audit。

## 4. 边界判断

- 不新增数据库 migration；
- 不修改已有 Workflow 外键约束；
- 不修改测试所依赖的生产算法；
- 不要求人工填写测试 ID、Token 或业务数据；
- 不自动启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis。

## 5. 后续关注

II-09 修复后，继续检查 Operator Action 的执行事务是否能够保证 `Idempotency -> Result Resource -> Audit -> Trace` 在异常情况下保持原子收敛，重点关注 Retry / Resume / Trigger Invoke 的下游 Service commit 边界。