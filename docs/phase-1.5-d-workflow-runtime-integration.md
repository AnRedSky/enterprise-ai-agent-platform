# Phase 1.5-D：Workflow Runtime Integration

## 1. 目标

在 1.5-C Execution State Machine 基础上，将已发布 Workflow Version 与实际 Runtime 执行链路连接起来，形成可持久化、可查询、可失败收敛的最小执行闭环。

本阶段遵循 Agent Runtime / Workflow Engine 分层原则：API 只负责协议适配，Workflow Service 负责生命周期，Workflow Runtime 负责节点执行，Model Gateway 负责模型供应商抽象。

## 2. 本阶段范围

### 2.1 Workflow Definition 最小运行契约

```json
{
  "nodes": [
    {"id": "input", "type": "input"},
    {"id": "agent", "type": "agent", "config": {"agent_id": "<published-agent-id>"}},
    {"id": "output", "type": "output"}
  ]
}
```

- 节点按 `nodes` 声明顺序串行执行。
- 支持 `input`、`agent`、`output` 三类节点。
- `agent` 必须引用已发布 Agent；非 admin 用户只能执行自己拥有的 Agent。
- 不在本阶段推断或实现并行、条件分支、循环、任意 Python 执行。

### 2.2 Runtime 生命周期

```text
pending
  ↓
running
  ↓
completed / failed / cancelled
```

每个节点均持久化：

```text
pending → running → completed / failed
```

节点失败必须导致 Workflow Execution 收敛到 `failed`，并记录 `error_code / error_message`。

### 2.3 API

新增：

```text
POST /api/v1/workflows/executions/{execution_id}/run
```

要求：

- tenant scope 校验；
- owner/admin RBAC；
- 只能运行 `pending` execution；
- 只能运行创建时锁定的已发布 Workflow Version；
- Runtime 完成后返回持久化 execution 状态。

## 3. 不属于本阶段

- MQ / Worker 异步调度
- Temporal
- 并行 DAG 调度
- 条件分支 / 循环
- Tool Runtime 编排
- Human-in-the-loop
- Workflow Governance / Audit / Trace 扩展
- Vue Workflow UI

以上能力分别进入后续 1.5-E / 1.5-F 或后续 Runtime 扩展。

## 4. 测试门禁

Backend：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
uv run alembic current
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_d_workflow_runtime_validation.ps1
```

本阶段不涉及数据库结构变更，因此 `alembic upgrade head` 应保持幂等并停留在 0016 head。

前端测试必须独立执行，不得由 Backend 验证脚本调用。

## 5. 验收标准

1. Workflow Runtime Definition 校验测试通过。
2. Input / Output 节点数据链路保持正确。
3. Agent 节点调用已发布 AgentVersion / ModelGateway。
4. Node Execution 状态持久化。
5. Execution 成功收敛为 `completed`。
6. Runtime 节点异常收敛为 `failed`。
7. owner/admin 权限边界不被 Runtime 绕过。
8. Backend 全量 pytest 通过且无未解释 warning。
9. migration 实际执行通过。
10. 验收结果写回 `docs/PROJECT_STATUS.md` 后才能进入 1.5-E。
