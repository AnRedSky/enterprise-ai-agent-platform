# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前代码基线：`1418baf` — `fix(db): register complete ORM metadata before runtime claims`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B2 Workflow Worker Execution Bridge**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力已完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施已完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- lifecycle / Worker fencing 纯规则入口已建立；
- B1 Atomic Claim 已完成生产实现：PostgreSQL Delegation 行锁、真实 `WorkflowExecution`、Worker owner/lease、`worker_execution_id` 与同事务持久化；
- B1 Real HTTP + PostgreSQL 双 Worker 并发 Gate 已由开发者本地实际执行并通过；
- ORM metadata registry 已修复跨模块 ForeignKey 运行时注册问题；
- **B2 Worker Execution Bridge 已进入生产代码：已 Claim Execution 通过正式 Delegation Runtime Bridge 显式装配 target Agent version、model profile、input、selected context refs、allowed tools 与 trace identity，并复用现有 Workflow Worker / WorkflowRuntime。**

## 3. B1 本地验收结果

开发者本地最新 `main` 实际执行：

```text
Model registry Unit       2 passed
Delegation targeted Unit 30 passed
Backend regression        846 passed, 3 skipped, 43 deselected
Migration                 0039_workflow_node_execution_tenant_trigger (head)
Real Delegation Contract  1 passed
B1 PostgreSQL race        1 passed
```

最终输出：

```text
[PASS] Phase 2.8 Delegation + B1 Atomic Claim gate completed.
```

该结果仅代表本次开发者本地实际执行，不使用 GitHub Actions 作为验收依据。

## 4. B2 当前实现边界

```text
B1 Claim
    ↓
WorkflowExecution(worker_execution_id)
    ↓
AgentDelegationRuntimeBridge
    ├── target_agent_version_id
    ├── target_agent_id
    ├── model_profile_id
    ├── input_data
    ├── selected_context_refs
    ├── allowed_tools
    └── trace_id
    ↓
内存 Runtime Version
    ↓
既有 DurableResumeWorkflowRuntime
    ↓
既有 WorkflowRuntime
    ↓
Target Agent published version
    ↓
既有 ModelGateway / Governance / Provider
```

B2 不创建第二套 Worker、Lease、Retry、Recovery 或 Provider；不修改父 Workflow Version 数据库记录，不复制父 Execution checkpoint、memory 或 credential。

`selected_context_refs` 与 `allowed_tools` 当前作为显式、受治理的 Runtime context 装配；实际工具执行权限仍由后续 Tool Runtime Contract 决定，不在 B2 中复制工具系统。

## 5. B2 自动化验收

新增：

```text
backend/app/services/agent_delegation/runtime_bridge.py
backend/tests/unit/test_agent_delegation_runtime_bridge.py
backend/tests/api_real/test_agent_delegation_bridge_api.py
backend/scripts/test/phase-2.8/02_worker_execution_bridge_gate.ps1
```

B2 Gate 自动完成：

1. B2 Bridge Unit；
2. Backend default regression；
3. Alembic upgrade/head；
4. 自动启动 PostgreSQL / Redis；
5. 自动启动 Backend（未运行时）；
6. 自动注册临时用户并登录取得 Token；
7. 真实 HTTP 创建 Orchestrator / Target Agent / Workflow / Delegation；
8. 真实 PostgreSQL Claim；
9. 通过现有 Worker Runtime Entry 执行 Target Agent；
10. 验证 Worker Execution 使用 Target Agent version 与 model profile，并保持 parent Workflow Version 不变。

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
```

禁止手工填写 Token、用户名、密码、tenant、ID 或测试数据。

## 6. 当前未完成

| 能力 | 状态 |
|---|---|
| B1 Atomic Claim | ✅ 本地真实验收通过 |
| B2 Worker Execution Bridge 生产实现 | ✅ |
| B2 Unit Gate | ⏳ 待开发者本地执行 |
| B2 Real HTTP + PostgreSQL + Runtime | ⏳ 待开发者本地执行 |
| B3 generation-fenced completion/failure | ⏳ |
| B4 timeout/cancel/parent semantics | ⏳ |
| B5 Audit/Trace 完整闭环 | ⏳ |
| Delegation Runtime multi-worker acceptance | ⏳ |

## 7. 下一开发顺序

```text
B2 Unit / Real PostgreSQL Runtime Gate
    ↓
若发现 Runtime / tenant / model profile / context assembly 问题，立即修复
    ↓
B2 验收闭环
    ↓
B3 completion / failure + generation fencing
    ↓
B4 timeout / cancel / parent semantics
    ↓
B5 Audit / Trace
    ↓
Delegation 多 Worker + PostgreSQL + Runtime acceptance
```

## 8. 测试规则

开发者本地实际执行结果为唯一测试依据；GitHub Actions 不作为验收依据。

B1 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\01_delegation_contract_gate.ps1
```

B2 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
```

Real API Gate 会自动生成临时身份与 Token，不要求开发者手工输入任何信息。

## 9. 当前结论

**B1 已由开发者本地真实 PostgreSQL 双 Worker Gate 验收通过。项目已经进入 B2 Workflow Worker Execution Bridge：生产代码已将 Delegation 显式桥接到现有 Worker Runtime，并新增 Unit + Real API/PostgreSQL 自动化验收入口。下一步直接执行 B2 Gate；通过后进入 B3 generation-fenced completion/failure。**
