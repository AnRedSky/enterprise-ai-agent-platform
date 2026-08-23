# Phase 2.4 Durable Scheduler Acceptance

> 当前状态：**Persistence Gate 待本地验收，尚未进入功能 Acceptance。**
> 验收基线：`main`

## 1. 当前 Gate

| 项目 | 状态 |
|---|---|
| Contract / timezone / DST | 已实现，待本地 Gate |
| Scheduler 持久化模型 | 已实现，待本地 Migration Gate |
| Alembic `0028_durable_scheduler_persistence` | 已实现，待本地执行 |
| 原子 lease claim / release | 已实现，待 Repository Gate |
| schedule slot 幂等 claim | 已实现，待 Repository Gate |
| WorkflowExecution 绑定 | 已实现基础能力，待竞态验证 |
| Tenant / Organization scope | 待 API / Runtime 验证 |
| Scheduler API Contract | 待实现 |
| Scheduler Runtime persistence 闭环 | 待实现 |
| Real API acceptance | 待创建 |

## 2. 当前本地测试流程

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_scheduler_contract.py tests/unit/test_workflow_scheduler_persistence_contract.py tests/unit/test_workflow_scheduler_runtime_module.py tests/unit/test_workflow_scheduler_repository.py
uv run alembic upgrade heads
uv run alembic current
uv run pytest -q
```

以上命令仅作为验收入口，未由当前执行者实际运行前不得记录 Passed。

## 3. Persistence Gate 关闭标准

1. targeted tests 全部通过；
2. Alembic heads 升级成功且 current 状态正确；
3. 默认 Backend Regression 通过；
4. PostgreSQL 原子 lease claim / release 真实行为符合 Contract；
5. slot 唯一键重复 claim 不产生重复有效槽位；
6. Execution 绑定在并发条件下保持唯一关联；
7. tenant isolation 在 Repository / API 层成立。

Gate 关闭后才能进入 Scheduler API Contract 与 Runtime persistence 接入。

## 4. Real API Gate 目标

至少覆盖：

- 多实例 lease 竞争；
- lease 过期抢占；
- 重复 schedule slot claim；
- misfire：skip / fire_once / bounded catch_up；
- enabled / paused / disabled；
- WorkflowExecution 关联；
- Tenant Safe organization scope；
- Audit / Trace 关联；
- 服务重启后的 next_run_at / lease 恢复语义。

**当前不记录 Phase 2.4 Passed。**
