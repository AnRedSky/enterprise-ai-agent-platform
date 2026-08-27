# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前阶段：Phase 2.4 Durable Scheduler 生产代码继续收口；Phase 2.7 Recovery / Replay lifecycle closure 已完成。
- Phase 2.7 已完成 Conditional Branching、Durable Frontier Scheduling、Scheduler → Worker → Runtime、Retry Scheduling、Frontier → Checkpoint 原子推进、Runtime failure convergence、Durable Resume Bootstrap、Recovery Trace 原子事务、Join predecessor contract、tenant boundary、Checkpoint lineage、Decision Replay Guard、Multi-frontier Checkpoint boundary、Execution fencing、stale Worker Checkpoint late-write guard、Node → Checkpoint fencing propagation、Checkpoint durable write boundary、Multi-frontier Join Recovery、Replay Decision Convergence、Resume lifecycle idempotency closure。
- Phase 2.4 已完成 Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire、API/Scheduler 进程解耦；**本轮继续完成 Scheduler Dispatch + Durable Recovery Scan 双循环生命周期监督**，避免 Recovery Scan 异常后服务处于半存活状态。
- Phase 2.2 Retrieval Production Quality：已正式关闭。
- Phase 2.3 Model Provider Governance：已正式关闭。
- Phase 2.5 Scheduler → Worker Execution Decoupling：已正式关闭。
- Phase 2.6 Durable Execution Checkpoint Foundation：生产代码实现已完成；Unit Test 实际 Closure 仍按本地执行结果记录。
- Backend 模块化整改：已完成既有领域迁移，不作为当前主线阻塞条件。
- Frontend Phase 1.3：SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费、Chat / Runtime 失败、断流、取消 UI 生命周期均已完成。

## Phase 2.4 当前实现

```text
Durable Scheduler
├── Persistence                                ✅
├── Lease / ownership / fencing                ✅
├── Misfire / catch-up                         ✅
├── Slot idempotency                           ✅
├── WorkflowExecution binding                 ✅
├── Scheduler Runtime                          ✅
├── Scheduler API Contract                     ✅
├── Tenant isolation                           ✅
├── API / Scheduler process separation         ✅
└── Scheduler dual-loop supervision             ✅ 本轮
       ├── Scheduled Trigger Dispatch
       └── Durable Recovery Scan
              ↓
       FIRST_EXCEPTION supervision
              ↓
       unified shutdown / failure convergence
```

## Recovery / Replay 当前状态

```text
Recovery / Replay Closure
├── Durable Resume Bootstrap                   ✅
├── Recovery Trace atomic transaction          ✅
├── Join predecessor contract                 ✅
├── Resume tenant boundary                    ✅
├── Resume Checkpoint lineage                 ✅
├── Cross-Execution Replay Identity           ✅
├── Multi-frontier Checkpoint boundary        ✅
├── Execution fencing generation              ✅
├── stale Worker Checkpoint late-write guard  ✅
├── Node → Checkpoint fencing propagation     ✅
├── Checkpoint durable write boundary         ✅
├── Multi-frontier Join Recovery              ✅
├── Replay decision convergence               ✅
└── Resume lifecycle idempotency closure      ✅
```

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test 结果。

## 本轮交付

- `backend/app/entrypoints/scheduler.py`
- `backend/tests/unit/test_service_entrypoints.py`
- `docs/04-errors/2026-08-27-scheduler-service-supervision.md`
- `docs/02-phases/PHASE_2_4.md`
- `docs/PROJECT_STATUS.md`

本轮完成 Scheduler Service 双循环生命周期监督：Scheduled Trigger Dispatch 与 Durable Recovery Scan 任一长期循环发生未处理异常时，统一停止另一循环并传播原始异常；正常停止时统一取消并等待任务结束。该变更不新增 Scheduler / Recovery / Runtime 平行实现，不改变数据库、slot、lease、misfire 或 API Contract。

**Unit Test：本轮未在当前环境执行，因此不记录 PASS。完整 Gate / Real API / E2E 按当前主线策略继续暂停。**

## 下一主线

Phase 2.4 Durable Scheduler 的生产代码继续按 canonical domain implementation 收口；优先补齐尚未完成的生产能力，不为测试 Gate 创建新的平行实现。所有主线生产任务完成后，再集中执行开发者本地 Unit Test / Gate / Acceptance。
