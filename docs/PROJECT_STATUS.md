# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B6 Delegation Multi-Worker Runtime acceptance 已完成**
- 下一主线：**Phase 2.8 收口并进入 Phase 2.9 Enterprise Integration / Event Infrastructure Contract**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- B1 Atomic Claim 已完成并通过本地真实 HTTP + PostgreSQL 双 Worker 并发 Gate；
- B2 Worker Execution Bridge 已完成，复用既有 Workflow Worker / WorkflowRuntime；
- B3 Delegation completion/failure generation fencing 已完成；
- B4 timeout / cancel / parent semantics 已完成并由开发者本地 Real Gate 验收通过；
- Runtime Session / Execution terminalization / Model Profile Snapshot / Frontier heartbeat 锁序问题已完成修复；
- Scheduler 对单节点顺序 Workflow 的空 `edges` 语义已与 DAG Runtime 对齐；
- B5 Delegation Audit / Trace 基础闭环已实现，创建与取消事件已写入 AuditLog / WorkflowTraceEvent；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成并通过 targeted Unit Gate；
- B6 已补齐 Delegation 从 pending fact 到 Durable Frontier Worker dispatch 的正式运行链路；
- B6 多 Worker contention、drain 时序、Worker shutdown cleanup 及 Windows PowerShell Worker/Scheduler 隔离检查已完成修复。

## 3. 最新本地验收证据

最新开发者本地执行的正式 B6 Gate 已全部通过：

```text
[1/4] Delegation Claim + Worker dispatch Unit/Contract
38 passed in 1.08s

[2/4] Backend default regression
870 passed, 3 skipped, 52 deselected in 34.61s

[3/4] Migration/head verification
0039_workflow_node_execution_tenant_trigger (head)

[4/4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
5 passed in 7.48s

[PASS] Phase 2.8 B6 multi-worker Delegation Runtime gate completed.
```

因此 **B6 已达到本地 Real Gate 通过条件，不再处于阻塞状态**。

验收结果说明：

1. Unit/Contract 层的 Delegation Claim 与 Worker dispatch 已通过；
2. Backend 默认回归测试保持通过，当前基线为 `870 passed, 3 skipped, 52 deselected`；
3. Alembic 数据库迁移已验证到 `0039_workflow_node_execution_tenant_trigger` head；
4. 真实 HTTP + PostgreSQL + 多 Worker Durable Frontier Runtime 已通过 5 个 Real API 验收用例；
5. B6 验收前置的 Windows 外部 Worker/Scheduler 隔离检查已正确识别并阻止污染性后台消费者；在无外部消费者条件下 Gate 正常完成。

## 4. B6 实现与问题闭环

B6 开发期间本地 Real Gate 暴露并完成以下工程问题修复：

1. 多 Worker 两轮 dispatch 只消费部分 Delegation：根因是 PostgreSQL Claim contention 与固定轮次测试时序组合导致合法竞争被错误解释为任务未消费；已改为有界窗口内安全 drain；
2. B2 Real API 测试绕过正式 Durable Frontier dispatch 边界：已改为通过正式 `WorkflowWorker` Frontier Claim / Execute 边界验证 Target Agent Runtime；
3. Worker 关闭阶段 AsyncEngine / asyncpg connection close 在主 Task cancellation 下出现 `CancelledError`：已使用独立 cleanup Task + `asyncio.shield()` 保证底层连接池清理完成，并恢复原 cancellation 语义；
4. Real Gate 存在外部 Worker/Scheduler 消费测试 Delegation 的环境污染风险：已增加项目路径感知的 Windows PowerShell 进程隔离检查；Gate 不自动启动、停止或重启任何服务；
5. Windows PowerShell 进程检测曾存在正则字符串引用解析错误：已改为稳定的路径感知匹配实现。

对应错误记录：

- `docs/04-errors/2026-08-29-phase-2-8-b6-worker-entrypoint-and-delegation-runtime.md`
- `docs/04-errors/2026-08-29-phase-2-8-b6-multi-worker-acceptance-contention.md`
- `docs/04-errors/2026-08-29-worker-async-engine-shutdown-cancelled-error.md`

B6 相关修复提交链已经完成闭环，最终以实际 Real Gate 通过结果作为验收依据，不以历史失败记录覆盖当前状态。

## 5. B6 自动化验收

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

Gate 自动生成测试用户、Token、tenant、ID 与测试数据；Gate 本身不启动、重启或停止任何服务，只验证 PostgreSQL、Redis、Backend API 本地前置条件，并在真实验收前检查当前项目是否存在外部 `run_worker.py` / `run_scheduler.py` 消费者。

验收顺序：

```text
[0] prerequisite service verification + Worker/Scheduler isolation
    ↓
[1] Delegation Claim + Worker dispatch Unit/Contract
    ↓
[2] Backend default regression
    ↓
[3] Alembic upgrade/head
    ↓
[4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
```

最新实际 Gate 已按上述入口完成并通过。

## 6. 当前阶段判断

```text
Phase 2.7 Advanced Workflow                         ✅ 完成
Phase 2.8-A Delegation Contract                    ✅ 完成
B1 Atomic Claim                                    ✅ 完成
B2 Worker Execution Bridge                         ✅ 完成
B3 Completion/Failure Generation Fencing           ✅ 完成
B4 Timeout / Cancel / Parent Semantics             ✅ 完成
B5 Audit / Trace                                   ✅ 完成
B6 Multi-Worker Durable Frontier Runtime            ✅ 完成
Phase 2.8 Runtime Integration                      🟢 已达到收口条件
```

当前没有证据表明 B6 仍存在未解决的 Runtime 阻塞问题。后续不应继续围绕已经通过的 B6 Gate 重复修改测试等待时间、Claim 逻辑或 Worker shutdown cleanup，除非出现新的实际回归证据。

## 7. 下一主线任务

```text
B6 Real Gate Passed
    ↓
Phase 2.8 文档与验收收口
    ↓
Phase 2.9 Enterprise Integration / Event Infrastructure Contract
    ↓
Contract → Migration → Backend implementation → Unit/Integration → Real API Gate
```

进入 Phase 2.9 前必须先确认现有 Integration / Event Infrastructure 是否已经存在正式领域实现，禁止重复创建平行 Service、Repository、Runtime 或 Provider。新功能必须继续遵循 `docs/01-governance/DEVELOPMENT.md` 的领域模块化、Contract-first、Migration-first、测试 Gate 隔离及直接提交 `main` 的规则。
