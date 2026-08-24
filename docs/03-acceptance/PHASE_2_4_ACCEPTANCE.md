# Phase 2.4 Durable Scheduler Acceptance

> 当前状态：**Persistence、Runtime、Scheduler API Contract 已本地关闭；tenant isolation / misfire integration 为当前实现任务，新增代码尚待本地 Gate 与 Real API 验收。**
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
| Tenant / Organization scope | Repository lease/slot 已验证；状态查询 tenant isolation 新增测试待本地执行 |
| Scheduler Runtime persistence 闭环 | 本地 Gate 已通过：4 passed |
| Scheduler API Contract / 状态可观测性 | 本地 Gate 已通过：6 passed |
| Misfire policy Runtime integration | **本轮新增，待本地 Gate** |
| Tenant Safe Real API acceptance | 待完成 |

## 2. 已实际执行的本地 API / Runtime 流程

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\02_scheduler_runtime_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\03_scheduler_api_contract_gate.ps1
```

用户实际反馈：

```text
Scheduler Runtime targeted tests：4 passed
Alembic current：0028_durable_scheduler_persistence (head) (mergepoint)
Scheduler contract targeted tests：13 passed
Scheduler repository PostgreSQL integration：2 passed
Scheduler API Contract tests：6 passed
Backend default regression：385 passed, 2 skipped, 35 deselected
```

## 3. Tenant isolation / misfire integration 验收目标

### Tenant isolation

1. 正确 tenant + trigger 可以读取 Scheduler 状态；
2. 错误 tenant + 同 trigger ID 返回空结果，不泄露状态；
3. lease claim / release / advance 不允许跨 tenant；
4. schedule slot 不允许跨 tenant 复用查询边界；
5. Scheduler API 继续沿用 Workflow / Trigger tenant scope。

### Misfire

1. `skip`：历史积压不补发；
2. `fire_once`：历史积压只补一次，下一运行恢复未来 interval；
3. `catch_up`：最多处理 `catch_up_limit`，剩余积压在下一 tick 继续；
4. 长时间停机不得产生无界内存槽位；
5. 每个补跑槽位继续通过持久化 `schedule_slot_key` 与既有 Execution idempotency 收敛；
6. `misfire_policy / catch_up_limit` 从 Scheduled Trigger Contract 进入既有 WorkflowSchedule 持久化字段，不新增第二套配置来源。

## 4. 当前新增本地 Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\04_scheduler_tenant_misfire_gate.ps1
```

该 Gate 执行：

```text
Application import
        ↓
Scheduler misfire unit tests
        ↓
Scheduler tenant PostgreSQL integration
        ↓
Scheduler API Contract tests
        ↓
Backend default regression
```

**本地 Gate 未执行前不得记录 Passed。**

## 5. 后续 Acceptance 目标

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
