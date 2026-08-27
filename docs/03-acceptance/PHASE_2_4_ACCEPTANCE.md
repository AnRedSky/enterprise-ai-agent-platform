# Phase 2.4 Durable Scheduler Acceptance

> 当前状态：**生产代码继续收口；Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire、API/Scheduler 进程解耦及 Scheduler Service 双循环生命周期监督均已实现。按当前开发策略，完整 Acceptance Gate 暂不作为主线开发阻塞条件。**
> 验收基线：`main`
> 评估日期：2026-08-27

## 1. 当前 Gate 状态

| 项目 | 状态 |
|---|---|
| Contract / timezone / DST | 已实现；本轮不重新执行完整 Gate |
| Scheduler 持久化模型 | 已实现；Migration 已存在 |
| 原子 lease claim / release | 已实现 |
| schedule slot 幂等 claim | 已实现 |
| WorkflowExecution 绑定 | 已实现 |
| Tenant / Organization scope | 已实现 |
| Scheduler Runtime persistence 闭环 | 已实现 |
| Scheduler API Contract / 状态可观测性 | 已实现 |
| Misfire policy Runtime integration | 已实现 |
| API / Scheduler Service 进程解耦 | 已实现 |
| Scheduler Dispatch / Recovery Scan 生命周期监督 | **已实现，本轮新增** |
| Backend default regression | 暂停，待主线生产任务完成后执行 |
| Tenant Safe Real API acceptance | 暂停，待主线生产任务完成后执行 |
| Scheduler Restart Acceptance | 暂停，待主线生产任务完成后执行 |
| Frontend Regression / Browser E2E | 暂停，按最终影响范围执行 |

## 2. Scheduler Service 生命周期 Contract

```text
API Service
    backend/run.py
    → app.main:app
    → HTTP / Auth / API Router
    → 不创建 Scheduler

Scheduler Service
    backend/run_scheduler.py
    → app.entrypoints.scheduler
    ├── Scheduled Trigger Dispatch
    └── Durable Recovery Scan
```

两个长期循环由同一个进程级 Supervisor 管理：

```text
Dispatch + Recovery
       ↓
FIRST_EXCEPTION
       ↓
任一异常
       ↓
停止另一循环
       ↓
传播原始异常
       ↓
Scheduler Service 失败收敛
```

这样避免 Recovery Scan 静默失效而 Scheduled Trigger Dispatch 继续提供不完整调度服务。

## 3. 自动化验证入口

生命周期职责单元测试：

```powershell
cd backend
uv run pytest -q tests/unit/test_service_entrypoints.py
```

完整 Backend / Real API / Restart / Frontend / Browser Gate 暂不执行，待主线生产代码全部完成后集中执行。

## 4. 设计边界

- 不新增 Scheduler、Recovery Scheduler 或 Runtime 实现；
- 不修改 slot、lease、misfire、Recovery Policy、幂等或数据库 Contract；
- 不改变 API Service / Scheduler Service 的独立进程模型；
- 进程级监督只负责生命周期收敛，领域规则仍由正式领域模块实现；
- Worker Service 仍不创建空壳实现。

## 5. 当前结论

Phase 2.4 的生产实现范围继续推进中；本轮已补齐 Scheduler Service 双循环生命周期监督。**Unit Test 尚未在当前环境实际执行，因此不记录 PASS。** 完整 Acceptance Gate 按用户要求暂缓，不阻塞后续生产代码开发。
