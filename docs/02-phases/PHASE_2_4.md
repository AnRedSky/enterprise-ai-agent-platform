# Phase 2.4 — Durable Scheduler

> 状态：**Backend Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire integration Gate、应用生命周期与真实服务重启 Acceptance 的实现已完成；Frontend Regression 与 Workflow Trigger Browser E2E 已由开发者本地实际通过。普通 Tenant Safe Real API Gate 已通过；当前仅等待修复后的 Scheduler Restart Acceptance 本地实际结果后进行最终 Acceptance 汇总。**
> 评估日期：2026-08-25
> 优先级：**P1**

## 1. 方案决策

Phase 2.4 采用“**Contract-first + MVP 边界 + 可替换实现**”：

- 首版解决已发布 Workflow Scheduled Trigger 的持久化、恢复、lease、多实例 ownership、misfire、幂等和审计追踪。
- `next_run_at` 使用 UTC 持久化，调度配置保存 IANA timezone。
- 多实例 ownership 优先使用 PostgreSQL 原子 UPDATE / 行锁。
- 不提前引入 MQ/Kafka、Temporal、独立 Scheduler 服务、复杂 DAG 或通用任务平台。

## 2. 当前实现结构

```text
backend/app/services/workflow_scheduler/
├── __init__.py      # 稳定公开入口
├── contract.py      # 薄的领域聚合入口，不实现具体规则
├── models.py        # 状态、misfire、lease、slot 数据模型
├── time.py          # UTC、IANA timezone、DST 时间语义与槽位构造
├── lease.py         # lease 可抢占判断
├── misfire.py       # misfire 槽位规划
├── repository.py    # PostgreSQL 原子 lease / slot 持久化
└── runtime.py       # Scheduled Trigger 持久化调度器
```

`__init__.py` 负责稳定导出；领域规则按职责拆分，禁止继续向公共 `app/services/` 零散增加同功能文件。`misfire.py` 只依赖 `models.py` 与 `time.py`，不反向依赖聚合入口，避免形成循环依赖。

## 3. Contract 范围

当前覆盖：

1. `enabled / paused / disabled`；
2. IANA timezone 与 UTC 持久化；
3. 可注入 `SchedulerClock`；
4. DST 重复时间选择第一次、不存在时间拒绝；
5. `schedule_slot_key` 稳定幂等键；
6. lease owner / expiry 成对约束；
7. `skip / fire_once / catch_up` misfire；
8. Scheduled Trigger 配置可持久化 `misfire_policy / catch_up_limit`。

## 4. Persistence 第一版

已存在：

- `WorkflowSchedule`：调度状态、next/last run、lease、misfire 等持久化；
- `WorkflowScheduleSlot`：`schedule_slot_key` 唯一约束、planned time、owner 与 WorkflowExecution 关联；
- `0028_durable_scheduler_persistence` Migration；
- `workflow_scheduler/repository.py`：单条 UPDATE 原子 lease claim、owner 条件 release、PostgreSQL `ON CONFLICT DO NOTHING` slot claim、Execution 绑定；
- Repository 的 tenant + trigger scope；
- PostgreSQL Repository lease / release、tenant isolation 与 slot idempotency integration tests。

## 5. Durable Runtime 接入

Runtime 已从“进程内 interval recovery”切换为持久化 Scheduler 状态驱动：

1. Scheduled Trigger 首次进入 Runtime 时由 Repository 确保唯一 `WorkflowSchedule`；
2. 每个 Scheduler 实例拥有唯一 owner，通过 PostgreSQL 原子 lease claim 取得执行权；
3. 以持久化 `next_run_at` 生成稳定 `WorkflowScheduleSlot.schedule_slot_key`；
4. Execution 创建继续复用既有 `WorkflowTriggerService.invoke_scheduled`；
5. Execution 与 slot 绑定后，由 lease owner 原子推进 `next_run_at / last_run_at / last_execution_id` 并释放 lease；
6. Runtime 不复制 Trigger 校验、Execution 状态机或 Repository 规则；
7. Runtime 的 Execution idempotency key 统一由 `ScheduledTriggerScheduler.idempotency_key()` 生成，键空间与 interval slot Contract 保持一致。

## 6. Scheduler API Contract / 状态可观测性

只读状态查询：

```text
GET /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/schedule
```

职责边界：

- API 只负责认证、tenant/workflow/trigger scope 校验和响应转换；
- Scheduler 状态读取统一复用 `WorkflowSchedulerRepository.get_schedule_for_trigger`；
- 不在 API 层复制 next_run、lease、misfire 或 slot 计算；
- 不暴露 Scheduler worker owner，仅返回 `lease_active` 与 `lease_expires_at`；
- 非 Scheduled Trigger 或尚未初始化的 Scheduler 状态返回 404。

## 7. Tenant isolation / misfire integration

### Tenant isolation

- Repository 查询必须同时携带 `tenant_id + trigger_id`；
- lease claim / release / advance 必须同时携带 tenant scope；
- slot 查询保持 tenant scope；
- PostgreSQL 状态查询隔离测试验证错误 tenant 无法读取正确 tenant 的 Scheduler 状态；
- 测试数据准备必须先 flush `WorkflowTrigger`，再写入引用它的 `WorkflowSchedule`，显式建立真实 FK 前置条件。

### Misfire integration

Scheduled Trigger Contract：

```text
misfire_policy: skip | fire_once | catch_up
catch_up_limit: 1..100，默认 10
```

运行语义：

- `skip`：历史积压全部跳过，下一运行恢复到未来 interval；
- `fire_once`：历史积压只补一次，随后恢复到未来 interval；
- `catch_up`：最多补跑 `catch_up_limit` 个历史槽位，若仍有积压则由下一 tick 继续有界处理；
- 每个槽位继续通过统一 `schedule_slot_key` 和既有 WorkflowTriggerService idempotency 收敛重复执行；
- 单个 slot 的 `recovery` 元数据只在该 slot 的 `planned_at < now` 时为 `true`，当前槽位不继承整轮 tick 的 misfire 状态。

misfire 计算统一位于 `workflow_scheduler/misfire.py`，Runtime 不复制规则。

## 8. Backend Gate / 最新实际结果

开发者最新反馈：

```text
Backend default regression：397 passed，3 skipped，36 deselected
Tenant Safe Real API Gate（修复后）：35 passed
Frontend Regression：79 passed + production build
Workflow Trigger Browser E2E：1 passed
Organization Browser E2E：3 scenarios passed
Model Provider Browser E2E：2 scenarios passed
```

以上均来自开发者本地实际执行结果。

## 9. 真实服务重启 Acceptance

真实服务重启 Gate 由独立入口执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

当前脚本已取消对 `127.0.0.1:8000` 的固定占用要求：启动前自动申请本机空闲端口作为 tenant-safe fixture bootstrap API。bootstrap 完成后临时进程退出；`tests/api_real/test_scheduler_restart_api.py` 再自行申请新的空闲端口完成真实 Uvicorn 停止/重启验收。

该设计只消除开发机已有 API 服务造成的无意义端口阻断，不改变“restart acceptance 的目标 Scheduler 进程必须由测试自身独占”的边界。真实 PostgreSQL、`next_run_at` 回拨、历史 slot recovery、统一 idempotency key、WorkflowExecution 以及 Audit/Trace tenant/workflow/execution 关联仍由原 Acceptance 测试真实验证。

## 10. Frontend Scheduler 状态可观测性

Backend Scheduler API Contract 已向 Frontend 暴露正式只读入口，Frontend 不实现第二套 Scheduler 计算逻辑：

- `frontend/src/api/workflows.ts` 定义 `SchedulerStatus`，统一调用 `/workflows/{workflow_id}/triggers/{trigger_id}/schedule`；
- Workflow Trigger 页面为 Scheduled Trigger 增加“调度状态”入口；
- 页面展示 status、timezone、misfire、catch-up、next/last run、lease 与最近 Execution；
- Trigger 禁用、删除或 Workflow 切换导致目标失效时，页面清理已选 Scheduler 状态，避免展示过期持久化数据；
- Scheduler Runtime 在 Trigger 创建后存在异步初始化窗口时，Frontend 仅对“Scheduler 状态尚未初始化”执行有限重试，不复制 Scheduler 调度规则；
- Vitest 已补充该初始化窗口的重试断言；
- Workflow Trigger Browser E2E 已实际验证真实 Trigger 创建、Scheduler API 状态、Scheduler UI 状态以及 PostgreSQL 持久化 Config。

## 11. Browser E2E 场景隔离

当前 Organization 领域保持“一 Tenant 一 Organization”。为了让 Browser E2E 在本地可重复执行，不改变生产领域约束：

- `backend/scripts/test/e2e/00_reset_browser_e2e_database.py` 仅清理本地 E2E 数据库的 Organization 根聚合及其级联数据；
- `frontend/scripts/test/e2e/00_run_isolated_test.ps1` 在每个 Browser 场景前执行数据库隔离，再运行真实 Browser -> Vue -> Backend HTTP；
- `01_run_workflow_trigger_e2e.ps1` 只执行 Scheduler Workflow Trigger 场景；
- `02_run_organization_e2e.ps1` 逐个执行 Organization 场景；
- `03_run_model_provider_e2e.ps1` 逐个执行 Model Provider/Profile 场景。

该清理工具仅用于本地 Browser E2E，不得用于生产数据库，不替代 Alembic migration。

## 12. 下一执行顺序

```text
Frontend Release / Regression Gate                         ✓ 已通过
Browser Scheduler Gate                                    ✓ 已通过
Organization / Model Provider Browser E2E                 ✓ 已实际通过
Backend default regression                                 ✓ 已实际通过
Tenant Safe Real API Gate（修复后）                        ✓ 已通过
Scheduler Restart Acceptance（新端口自动化）               ↓ 待执行
Scheduler 多实例 lease / misfire / Execution / Audit Trace Acceptance 汇总
                                                            ↓
Phase 2.4 Passed 评估
```

普通 Tenant Safe Real API Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

Scheduler Restart Acceptance：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

两者仍然是独立 Gate。当前不记录 Phase 2.4 Passed，直到新脚本实际完成真实服务 restart acceptance 并完成 Acceptance 汇总。
