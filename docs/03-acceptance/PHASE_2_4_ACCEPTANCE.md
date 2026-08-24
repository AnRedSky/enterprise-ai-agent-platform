# Phase 2.4 Durable Scheduler Acceptance

> 当前状态：**Persistence 与 Runtime Gate 已本地关闭；Scheduler API Contract / 状态可观测性待本地验收，尚未进入完整功能 Acceptance。**
> 验收基线：`main`
> 评估日期：2026-08-24

## 1. 当前 Gate

| 项目 | 状态 |
|---|---|
| Contract / timezone / DST | 本地 Gate 已通过：13 passed |
| Scheduler 持久化模型 | 本地 Migration Gate 已通过 |
| Alembic `0028_durable_scheduler_persistence` | 本地 `current` 为 head |
| 原子 lease claim / release | PostgreSQL Repository integration 已通过：2 passed |
| schedule slot 幂等 claim | PostgreSQL Repository integration 已通过 |
| WorkflowExecution 绑定 | Runtime Gate 已覆盖并通过 |
| Tenant / Organization scope | Repository 已验证，API / Real API 仍待完整验收 |
| Scheduler Runtime persistence 闭环 | Runtime Gate 已通过：4 passed |
| Scheduler API Contract / 状态可观测性 | **本轮实现，待本地 Gate** |
| Real API acceptance | 待完成 |

## 2. 已实际执行的本地 Runtime 流程

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\02_scheduler_runtime_gate.ps1
```

实际结果：

```text
Scheduler Runtime targeted tests：4 passed
Alembic current：0028_durable_scheduler_persistence (head) (mergepoint)
Scheduler contract targeted tests：13 passed
Scheduler repository PostgreSQL integration：2 passed
Backend default regression：384 passed, 2 skipped, 35 deselected
```

以上结果为开发者本地实际反馈，不代表 API Contract 或 Real API 已通过。

## 3. Scheduler API Contract

本轮新增：

```text
GET /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/schedule
```

验收范围：

1. Bearer authentication；
2. workflow / trigger tenant scope；
3. 仅 Scheduled Trigger 可查询；
4. 尚未初始化 Scheduler 状态返回 404；
5. 返回 enabled/status、timezone、schedule expression、next/last run、last execution、lease 状态、misfire policy；
6. 不暴露 Scheduler worker owner；
7. API 不复制 Scheduler Repository / Runtime 领域规则。

固定本地 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\03_scheduler_api_contract_gate.ps1
```

该 Gate 执行：

```text
Application import
        ↓
Scheduler API Contract tests
        ↓
Backend default regression
```

**本地 Gate 未执行前不得记录 Passed。**

## 4. 后续 Acceptance 目标

至少覆盖：

- 多实例 lease 竞争；
- lease 过期抢占；
- 重复 schedule slot claim；
- misfire：skip / fire_once / bounded catch_up；
- enabled / paused / disabled；
- WorkflowExecution 关联；
- Tenant Safe organization scope；
- Audit / Trace 关联；
- 服务重启后的 next_run_at / lease 恢复语义；
- Scheduler 状态 API 的 tenant isolation 与错误边界。

**当前不记录 Phase 2.4 Passed。**
