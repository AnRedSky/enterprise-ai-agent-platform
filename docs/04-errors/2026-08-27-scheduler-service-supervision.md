# 2026-08-27 Scheduler Service 双循环监督缺口

## 1. 问题

Scheduler Service 进程同时承载 Scheduled Trigger Dispatch 与 Durable Recovery Scan 两条长期循环。此前入口只等待 Scheduled Trigger Scheduler，Recovery Scan 作为独立后台 task 创建后运行；如果 Recovery Scan 自身出现未处理异常，主 Scheduler 仍可能继续运行，形成“调度服务进程存活但 Durable Recovery 已静默失效”的半存活状态。

## 2. 根因

进程级入口只承担启动和取消职责，没有建立两个长期循环之间的统一生命周期监督边界。Recovery Scan 的异常没有成为 Scheduler Service 的失败条件。

## 3. 修复

`app.entrypoints.scheduler.run_scheduler_service()` 现在同时监督 Scheduled Trigger Dispatch 与 Durable Recovery Scan：

```text
Scheduler Service
   ├── Scheduled Trigger Dispatch
   └── Durable Recovery Scan
            ↓
      FIRST_EXCEPTION
            ↓
任一循环异常 → 停止另一循环 → 传播原始异常 → 进程失败收敛
```

正常停止时两个任务统一取消并等待完成；异常停止时不留下后台孤儿任务。

## 4. 边界

- 不新增 Scheduler、Recovery Scheduler 或 Runtime 实现；
- 不修改 slot、lease、misfire、Recovery Policy、幂等或数据库 Contract；
- 不改变 API Service / Scheduler Service 的独立进程模型；
- 进程级监督只负责生命周期收敛，领域规则仍由正式领域模块实现。

## 5. 单元测试

新增 Recovery Scan 异常场景，验证任一长期循环异常时两个 Scheduler 都执行 stop，原始异常继续向进程入口传播。

当前仅保留 Unit Test 范围；未执行的完整 Gate 不记录为通过。
