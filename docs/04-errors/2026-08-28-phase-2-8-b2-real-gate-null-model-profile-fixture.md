# Phase 2.8 B2 Real Gate：Mock Profile Fixture 对可选 model_profile_id 的错误前置假设

## 1. 发生时间

2026-08-28

## 2. 影响范围

- `backend/tests/api_real/test_agent_delegation_bridge_api.py`
- Phase 2.8 B2 Worker Execution Bridge Real Gate
- Phase 2.8 B3 Delegation Completion Real Gate（复用同一 Real API 测试文件）

## 3. 实际错误

在提交 `2daeeb62` 后由开发者本地实际执行 B2 Gate：

```text
B2 bridge Unit             3 passed
Backend default regression 850 passed, 3 skipped, 46 deselected
Migration/head              0039_workflow_node_execution_tenant_trigger (head)
B2 Real Gate                1 failed, 2 passed
```

失败位置：

```text
tests/api_real/test_agent_delegation_bridge_api.py
_bind_deterministic_mock_profile()
assert delegation.model_profile_id is not None
```

实际 Delegation 的 `model_profile_id` 为 `NULL`。

## 4. 根因

前一次 B2 Real Gate 修复针对的是“Delegation 绑定开发环境默认 Provider，导致 Runtime 请求外部 endpoint”的问题。对应 Fixture 通过读取 Delegation 已绑定的 Model Profile 推导 Organization，再替换为 deterministic Mock Profile。

但当前 Real Gate 创建 Target Agent 时只指定 `model_id=mock-model`，没有指定 `model_profile_id`。现有 AgentVersion 合法允许 `model_profile_id` 为 `NULL`，Delegation 创建逻辑也会忠实继承 Target Agent version 的 `model_profile_id`。因此测试辅助函数把“可选的生产字段”错误地当成了“测试 Fixture 必须预先存在的字段”。

这不是生产 Delegation Service 的业务错误，而是 Real Gate Fixture 与当前 Agent / Model Profile Contract 不一致。

## 5. 修复

将测试 Fixture 的 Organization 推导来源改为稳定且不依赖已有 Provider 的领域关系：

1. 读取真实 Delegation；
2. 根据 `target_agent_version_id` 读取 Target Agent version；
3. 根据 Target Agent version 读取 Target Agent；
4. 根据 Delegation 的 `tenant_id` 读取该 tenant 唯一 Organization；
5. 自动创建唯一的 `provider_type=mock` Model Provider；
6. 自动创建 `model_type=chat`、`model_name=mock-model` 的 Model Profile；
7. 将 Delegation 的 `model_profile_id` 绑定到该 Mock Profile；
8. 继续执行既有 B1 Claim、Delegation Runtime Bridge 和 Worker Runtime。

整个过程继续由 Real Gate 自动完成，不需要开发者手工填写 Organization ID、Tenant ID、Provider endpoint、API Key、Model、Profile ID 或 Token。

## 6. 设计约束

- 不修改 `AgentVersion.model_profile_id` 的可选性；
- 不修改 Delegation Service 的生产 Provider 继承语义；
- 不增加第二套 Model Provider 实现；
- 不绕过 Governance、tenant boundary、PostgreSQL 持久化或 Worker Runtime；
- Real Gate 仍然验证真实 HTTP + PostgreSQL + Worker Runtime；
- 测试必须自己建立 deterministic Mock Provider 边界，不得依赖开发数据库中的默认 Provider/Profile。

## 7. 后续验证

修复提交后必须由开发者本地实际执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_agent_delegation_runtime_bridge.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

B2/B3 Real Gate 在产生新的本地实际结果前不得标记为通过。
