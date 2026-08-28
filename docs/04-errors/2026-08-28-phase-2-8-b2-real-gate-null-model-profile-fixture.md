# Phase 2.8 B2 Real Gate：Mock Profile Fixture 与 Agent Version 快照不一致

## 1. 发生时间

2026-08-28

## 2. 影响范围

- `backend/tests/api_real/test_agent_delegation_bridge_api.py`
- Phase 2.8 B2 Worker Execution Bridge Real Gate
- Phase 2.8 B3 Delegation Completion Real Gate（复用同一 Real API 测试文件）

## 3. 第一轮实际错误

在提交 `2daeeb62` 后由开发者本地实际执行 B2 Gate：

```text
B2 bridge Unit             3 passed
B2 Backend regression      850 passed, 3 skipped, 46 deselected
B2 Migration/head          0039_workflow_node_execution_tenant_trigger (head)
B2 Real Gate               1 failed, 2 passed
```

第一轮失败为测试 Fixture 假设 `delegation.model_profile_id` 必须预先存在。该问题已通过从 Delegation target Agent version + tenant 自动创建 deterministic Mock Provider/Profile 修复。

## 4. 第二轮实际错误

修复后开发者重新执行 B2、B3 Gate，Unit、Backend Regression、Migration 均通过，但两个 Real Gate 均在 `AgentDelegationRuntimeBridge.load()` 之前失败：

```text
HTTPException: 409: Delegation model profile 与目标 Agent version 不一致
```

代码检查位置：

```text
backend/app/services/agent_delegation/runtime_bridge.py

if target_version.model_profile_id != delegation.model_profile_id:
    raise HTTPException(409, "Delegation model profile 与目标 Agent version 不一致")
```

## 5. 根因

第一轮 Fixture 修复创建了独立 Mock Model Profile，并只更新了：

```text
AgentDelegation.model_profile_id
```

但 `AgentDelegationRuntimeBridge` 的设计契约要求 Delegation 执行快照必须与目标已发布 AgentVersion 的 `model_profile_id` 一致。否则 Worker 可能以与目标 Agent 发布版本不同的 Model Profile 执行，属于真实 Runtime Contract 违规。

因此第二轮失败不是生产 RuntimeBridge 的缺陷，而是测试 Fixture 形成了一个生产代码明确禁止的非法快照。

## 6. 第二轮修复

Real Gate Fixture 在 Claim 前同时设置：

```text
AgentVersion.model_profile_id = mock_profile.id
AgentDelegation.model_profile_id = mock_profile.id
```

这样 Target Agent published version 与 Delegation 在进入 Claim/Runtime 前引用同一个 deterministic Mock Profile。

Fixture 仍然完全自动化：

1. 查询真实 Delegation；
2. 查询 target Agent version；
3. 查询 target Agent；
4. 通过 Delegation tenant 定位 Organization；
5. 自动创建唯一 Mock Provider；
6. 自动创建唯一 Mock Profile；
7. 同一数据库事务内把 Target Agent version 与 Delegation 绑定到该 Profile；
8. 再进入真实 B1 Claim；
9. 进入 `AgentDelegationRuntimeBridge`；
10. 复用既有 Worker Runtime。

没有修改生产 RuntimeBridge 的一致性校验，也没有增加第二套 Provider。

## 7. 设计约束

- `AgentDelegationRuntimeBridge` 的 target Agent version 与 model profile 一致性校验必须保留；
- Real Gate 不得依赖开发数据库默认 Provider/Profile；
- Real Gate 不得通过修改生产 Runtime 规则来迁就测试 Fixture；
- Target Agent version + Delegation model profile 必须形成一致执行快照；
- Real Gate 必须继续验证真实 HTTP + PostgreSQL + Worker Runtime；
- 测试身份、Token、Tenant、Organization、Provider、Profile、Agent、Workflow、Execution、Delegation 均由脚本自动生成，不要求开发者手工填写；
- B2/B3 在新的本地实际结果产生前不得标记为 Real Gate 通过。

## 8. 后续本地验证

修复后由开发者本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
uv run pytest -q
```

脚本自动负责 PostgreSQL、Redis、Backend 生命周期及测试身份/Token/Fixture；禁止手工启动服务或手工填写测试信息。

在产生新的本地实际结果前，B2/B3 Real Gate 保持“待验证”状态。
