# Phase 2.8 B2 Real Gate：默认 Model Provider 外部依赖导致验收失败

## 1. 发生时间

2026-08-28

## 2. 影响范围

- `tests/api_real/test_agent_delegation_bridge_api.py`
- Phase 2.8 B2 Worker Execution Bridge Real Gate
- Phase 2.8 B3 Delegation Completion Real Gate（B3 Gate 复用了同一 B2 Runtime 验证）

## 3. 实际错误

最新 `main` 的 Backend Regression 已通过，但 B2/B3 Real Gate 在真正执行 Target Agent 时失败：

```text
HTTP 503 Service Unavailable
http://127.0.0.1:3477/v1/chat/completions
model = fixture-failing-model
```

此前 B2 Real Gate 的测试职责明确要求使用 Mock Model Provider，但 Delegation 创建后实际继承了本地数据库中的默认 Model Profile。该 Profile 指向本地 `fixture-failing-model` OpenAI-compatible endpoint，因此真实 Runtime 被错误地路由到了开发环境 Provider，而不是测试所声明的 deterministic Mock Provider。

## 4. 根因

Real API 测试创建了真实 Agent / Workflow / Delegation，但没有在 Delegation 的 `model_profile_id` 上建立测试自身的 Provider/Profile 边界。

`ModelGateway` 对已经绑定 Model Profile 的请求不会使用未绑定 Profile 时的本地 mock fallback；只有 Provider 类型为 `mock` 时才会实例化 `MockModelProvider`。因此测试环境中残留或预置的默认 OpenAI-compatible Profile 会直接影响验收结果。

## 5. 修复

在真实 PostgreSQL 测试会话中新增自动化 Fixture：

1. 读取当前 Delegation 已绑定的 Model Profile；
2. 从其 Provider 推导当前 Organization 边界；
3. 自动创建唯一的 `provider_type=mock` Model Provider；
4. 自动创建 `model_name=mock-model` 的 Model Profile；
5. 将当前 Delegation 的 `model_profile_id` 改为该 Mock Profile；
6. 再执行 B1 Claim 与现有 Worker Runtime。

整个过程由测试代码自动完成，不需要开发者填写 Provider URL、API Key、Model、Organization ID、Tenant ID 或其他测试数据。

## 6. 设计约束

该修复只隔离验收 Fixture，不修改生产 Model Gateway 的 Provider fallback 语义，也不绕过 Governance、Organization membership、PostgreSQL 持久化或 Worker Runtime。

Real Gate 仍然保持真实 HTTP + 真实 PostgreSQL + 真实 Worker Runtime 链路；仅将模型技术适配确定性地绑定到项目已有 `MockModelProvider`。

## 7. 验证要求

修复提交后必须由开发者本地重新执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_agent_delegation_runtime_bridge.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

在本地实际结果产生前，不得将 B2/B3 Real Gate 标记为通过。
