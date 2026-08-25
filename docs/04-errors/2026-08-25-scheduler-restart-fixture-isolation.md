# 2026-08-25 Scheduler Restart Acceptance 夹具隔离

## 1. 发生阶段

Phase 2.4 / Scheduler Durable Persistence / Real Service Restart Acceptance。

## 2. 开发者实际反馈

最新远端 `main` 为 `c8ae987`。独立执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

真实 Uvicorn 启动、停止、重启流程已经进入测试，但重启后的历史 slot 未产生 WorkflowExecution：

```text
AssertionError: []
assert len(rows) == 1
```

同时 API 日志出现过：

```text
Scheduled Trigger dispatch failed
422: Workflow definition 必须包含非空 nodes
```

## 3. 本轮分析结论

Scheduler Runtime 当前明确要求已发布 Workflow Version 的 `definition.nodes` 非空，因此不能通过放宽 `WorkflowRuntime.validate_definition()` 来掩盖错误。

原 Acceptance 测试直接依赖通用 Real API bootstrap 输出的 `TRIGGER_WORKFLOW_ID`。该方式把 Scheduler restart 生命周期验收与另一套 Real API fixture 生命周期耦合在一起：

```text
通用 Real API bootstrap
        │
        ├── 创建多个测试 Fixture
        ├── 写入共享 PostgreSQL
        └── 输出 TRIGGER_WORKFLOW_ID
                    │
                    ▼
Scheduler Restart Acceptance
        │
        └── 依赖共享 Fixture 的 Workflow Definition
```

即使通用 bootstrap 当前创建了最小可执行 Workflow，restart acceptance 仍不应该把“目标 Workflow Definition 正确”这一前置条件隐式交给另一个 Gate。API 日志中的空 `nodes` 也说明共享本地数据库可能存在历史无效 Published Workflow / Scheduled Trigger；该数据不应成为本 Acceptance 的隐式输入。

## 4. 修复

`backend/tests/api_real/test_scheduler_restart_api.py` 改为在 Acceptance 自身的真实 HTTP 生命周期中创建专属 Workflow / Version / Scheduled Trigger：

1. 创建 Workflow；
2. 创建最小可执行 Version：`input + output`；
3. 发布 Version；
4. 立即通过真实 HTTP GET 再验证持久化 definition 的 `nodes` 非空；
5. 创建 Scheduled Trigger；
6. 首次生命周期立即将 Trigger 置为 `disabled`，允许 Scheduler 初始化 `WorkflowSchedule`，但禁止首次 worker 抢先消费 slot；
7. 停止真实 Uvicorn 后，由测试直接在真实 PostgreSQL 中同时激活 Trigger、激活 Schedule 并回拨历史 `next_run_at`；
8. 重启新的真实 Uvicorn 进程，验证历史 slot 产生唯一 WorkflowExecution；
9. 继续验证 `scheduled_slot`、`recovery`、AuditLog、WorkflowTraceEvent、tenant/workflow/execution 关联以及 slot 幂等；
10. 最后仅删除本测试创建的 Scheduled Trigger，不删除已发布 Workflow，遵守生产 Workflow 删除边界。

该修复不改变生产 Scheduler Runtime、Workflow Runtime Contract、misfire 或 idempotency 规则，只收紧 Acceptance 的输入边界并消除共享 Workflow fixture 依赖。

## 5. 自动化验收入口

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

脚本仍负责：

- 动态申请 bootstrap 端口；
- 准备 tenant-safe Real API context；
- 启动/停止 bootstrap 进程；
- 调用独立 restart acceptance；
- finally 清理临时环境变量与 context 文件。

## 6. 验收要求

本轮代码提交本身不预填通过结果。必须以开发者本地实际执行结果确认：

```text
1. Backend default regression
2. Tenant Safe Real API Gate
3. Scheduler Restart Acceptance
4. Frontend Regression
5. 需要时重新执行 Browser E2E
```

其中 Scheduler Restart Acceptance 必须单独执行，并以 `[PASS] Scheduler real restart acceptance completed.` 作为脚本成功标志。