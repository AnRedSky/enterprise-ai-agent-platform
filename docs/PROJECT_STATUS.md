# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前代码基线：`54624f31` — `fix(worker): finalize delegation after runtime session closes`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B2 Worker Execution Bridge Real Gate 修复与本地验收**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力已完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施已完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- lifecycle / Worker fencing 纯规则入口已建立；
- B1 Atomic Claim 已完成生产实现，并已通过本地真实 HTTP + PostgreSQL 双 Worker 并发 Gate；
- B2 Worker Execution Bridge 已进入生产代码，复用现有 Workflow Worker / WorkflowRuntime 执行目标 Agent version；
- B3 Delegation completion/failure 已进入生产代码，以 `worker_execution_id` 作为 Worker generation fencing identity；
- B2 Runtime Session / Execution terminalization / Model Profile Snapshot 等前置问题已经完成修复；
- Delegation terminal write 已完成 tenant + running + worker generation fencing 与 ORM bulk DML 边界整改。

## 3. 最新本地验收反馈

开发者在 `612dbf55` 及其后续基线本地实际执行 B2 Gate：

```text
B2 bridge Unit             3 passed
Backend regression         850 passed, 3 skipped, 46 deselected
Migration/head             0039_workflow_node_execution_tenant_trigger (head)
B2 Real Gate               1 failed, 2 passed
```

失败为：

```text
assert persisted.status == "completed"
E AssertionError: assert 'running' == 'completed'
```

该结果确认 Target Agent Runtime、Worker Execution terminalization 与 generation context 均正常，但 Delegation finalization 仍位于 Runtime Session `async with` 生命周期内部。此前仅调整 Session/DML 的多轮修复没有建立真正的代码级生命周期边界。

## 4. 本轮真实修复

`54624f31` 将 Delegation finalization 从 Runtime Session 生命周期内部彻底移出：

- Runtime 开始前快照不可变的 tenant / Worker generation identity；
- Runtime 与 Worker Execution terminalization 继续使用既有 Runtime Session；
- Runtime 内部不再在 `finally` 中执行 Delegation finalization；
- Runtime `async with SessionLocal()` 完整退出后，才进入 Delegation 独立 finalization Session；
- Runtime 异常先保存 `outcome`、`reason_code` 与待抛异常，Session 关闭后先完成 Delegation terminalization，再恢复原异常传播语义；
- finalization Session 重新读取 Worker Execution 并执行 tenant + worker generation fencing；
- Delegation terminal state、AuditLog、WorkflowTraceEvent 继续原子提交；
- 不增加第二套 Worker、Lease、Retry、Recovery 或 Provider。

这次修复不再依赖 `AsyncSession.close()` 作为生命周期补偿，而是通过 Python `async with` 结构保证 Runtime Session 与 Delegation finalization Session 真正先后执行。

对应错误记录：`docs/04-errors/2026-08-28-b2-delegation-finalization-session-lifetime.md`。

## 5. B2 当前实现边界

```text
B1 Claim
    ↓
WorkflowExecution.worker_execution_id
    ↓
AgentDelegationRuntimeBridge
    ↓
单 Node 内存 Runtime Version
    ↓
既有 DurableResumeWorkflowRuntime
    ↓
既有 WorkflowRuntime
    ↓
Worker Execution terminalization（Runtime Session）
    ↓
Runtime Session async with 完整退出
    ↓
独立 Delegation finalization Session
    ↓
tenant + worker_execution_id fencing
    ↓
Delegation completed / failed + AuditLog + WorkflowTraceEvent
```

## 6. B3 当前实现

B3 不允许旧 Worker generation 修改新 generation 的 Delegation 状态；Worker lease 丢失时不提前收敛 Delegation。completion/failure 必须在 Runtime Session 完整关闭后执行独立终态事务。

## 7. 自动化验收

B2 正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
```

Gate 本身只做前置服务检查，不启动任何服务；测试账号、密码、Access Token 与测试数据均由脚本自动生成，不要求手工填写。

当前脚本要求本地前置环境已经运行：

- PostgreSQL：Docker Compose `postgres`；
- Redis：Docker Compose `redis`；
- Backend HTTP API：`http://127.0.0.1:8000/health` 可访问。

由于开发准则明确禁止测试 Gate 自动启动服务，本地必须先通过项目既有开发运行方式准备这些前置服务，然后再执行 Gate。Gate 不会自行拉起、重启或停止服务。

本轮修复尚未宣称 B2 Real Gate 已通过；最终结果必须以开发者重新执行上述命令后的实际输出为准。
