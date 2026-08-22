# Phase 2.2-E — Model Provider / Model Profile Governance Foundation

> 状态：**实现中**
> 前置：Phase 2.2 当前 Retrieval Quality 工程链路与 evaluation configuration 已形成；本任务作为其后续基础设施增强，不引入 Reranker / Hybrid 新能力。
> 目标：让 Chat / Embedding 模型从业务代码与 runner 固定值中解耦，形成可配置、可选择、可追踪、可评估的模型基础设施。

## 1. 本任务为什么属于当前阶段

当前 Retrieval Production Quality 已经要求 evaluation run 能够显式指定 Provider、model、dimension 与评估参数；如果模型身份仍只存在于环境变量或 runner 参数，长期无法形成企业级治理、审计和运行时选择能力。

因此本任务先建立 **Model Provider + Model Profile** 数据与管理边界，但不把 Phase 2.3 的 Provider 路由、Fallback、成本治理、用量治理提前实现。

## 2. 核心对象

### Model Provider

表示一个组织可治理的模型供应商/部署入口：

- `organization_id`
- `name`
- `provider_type`：技术适配器类型，例如 `openai-compatible`、`ollama`
- `provider_name`：实际供应商/部署身份
- `endpoint`
- `credential_ref`
- `enabled`
- `metadata`

`credential_ref` 只能表示 Secret/环境变量引用，不保存实际 API key。

### Model Profile

表示 Provider 下可被业务选择的具体模型：

- `provider_id`
- `name`
- `model_type`: `chat` / `embedding`
- `model_name`
- `dimension`：Embedding 必填，Chat 不允许填写
- `capabilities`
- `parameters`
- `enabled`
- `is_default`

## 3. API Contract

```text
GET    /api/v1/model-providers?organization_id={id}
POST   /api/v1/model-providers
PATCH  /api/v1/model-providers/{provider_id}
DELETE /api/v1/model-providers/{provider_id}

GET    /api/v1/model-providers/{provider_id}/profiles
POST   /api/v1/model-providers/{provider_id}/profiles
PATCH  /api/v1/model-providers/model-profiles/{profile_id}
DELETE /api/v1/model-providers/model-profiles/{profile_id}
```

Provider / Profile 管理要求 Organization active membership；写操作要求 Organization `owner/admin`。

## 4. 安全边界

- 不允许 API key 进入数据库明文。
- 不允许 API key 进入 CLI 参数、evaluation report 或 audit metadata。
- Provider endpoint 可以保存，但 credential 只能保存引用。
- Provider/Profile 的所有变更写入 AuditLog。
- 删除仍被 Profile 使用的 Provider 必须拒绝。
- 同一 Provider + model type 只能有一个 default Profile；设置新 default 会取消旧 default。

## 5. Retrieval / Runtime 使用边界

本任务建立治理对象和 API，不提前引入 Reranker、Hybrid、Fallback 或路由策略。

运行时选择原则：

```text
AgentVersion.model_profile_id
        ↓
Organization-scoped Model Profile
        ↓
Provider endpoint / credential_ref / model_name / parameters
        ↓
Model Gateway
        ↓
Execution / ExecutionEvent 固化 Profile + Provider identity
```

`model_profile_id` 为兼容性可选字段；未配置时继续沿用既有 `model_id` / 环境变量默认行为。配置 Profile 后，Profile 的 `model_name` 与 `parameters` 成为本次 Chat 调用的实际模型配置，不再由后端新增具体模型名称硬编码。

当前 E-1 已实现：

- AgentCreate / VersionCreate 支持 `model_profile_id`。
- AgentVersion 持久化 `model_profile_id`。
- Chat Runtime 解析当前用户可使用的启用 Chat Profile 与 Provider。
- OpenAI-compatible / Ollama adapter 使用 Profile 的 `model_name`、Provider endpoint、credential reference 与 Profile parameters。
- Execution / ExecutionEvent 持久化 `model_profile_id`、`provider_id` 与模型 identity。
- 未选择 Profile 时保持旧 `model_id` 兼容路径。

Credential resolution 仅在进程环境中根据 `credential_ref` 读取 Secret，不将 Secret 写入数据库或 trace。

## 6. Migration

新增：

- `model_providers`
- `model_profiles`
- `0026_model_profile_runtime_identity`：为 AgentVersion / Execution / ExecutionEvent 增加 governed Profile identity。

## 7. 自动化验证

当前新增 API contract 测试：

```powershell
cd backend
uv run pytest -q tests/api_contract/test_model_provider_contract.py
uv run pytest -q tests/api_contract/test_api_agents_endpoints.py tests/api_contract/test_model_provider_contract.py tests/api_contract/test_model_profile_runtime_contract.py
```

数据库迁移：

```powershell
uv run alembic upgrade head
uv run alembic current
```

完整 Backend Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\release\01_backend_regression_gate.ps1
```

完整 Real API Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

Runtime Profile Real API 验证要求：

1. 创建 Organization-scoped Provider。
2. 创建 enabled Chat Profile，并配置真实可用的 endpoint / credential_ref / model_name。
3. 将 `model_profile_id` 写入 AgentVersion 并发布 Agent。
4. Chat 请求实际调用该 Profile，而不是 `MODEL_DEFAULT_NAME`。
5. Runtime trace 能查询到 `model_profile_id`、`provider_id`、model identity。
6. Secret 不出现在 trace / audit / response。

## 8. 后续拆分

### 2.2-E-1 — Runtime Profile Resolution

**代码已实现，待本地 Gate / Real API 验证闭环。**

### 2.2-E-2 — Retrieval Evaluation Profile Selection

- Evaluation runner 支持 `model_profile_id`。
- Evaluation report 固化 Profile identity。
- baseline identity 增加受治理 Profile identity，但仍保持 Provider/model/dimension 等核心字段可读。

### 2.2-E-3 — Frontend Management

- Provider 管理。
- Chat / Embedding Profile 管理。
- 默认 Profile 选择。
- Secret reference 只显示引用，不显示 Secret。

### 2.2-E-4 — Acceptance

必须提供：

1. Provider CRUD Real API。
2. Profile CRUD Real API。
3. 权限与 Organization scope。
4. Migration head。
5. Runtime 使用自定义 Profile 的真实验证。
6. Evaluation 使用不同 Profile 的真实验证。
7. Audit / Trace evidence。
8. Frontend Vitest / Browser E2E（若 UI 纳入本阶段）。

## 9. 明确不做

- Reranker。
- Hybrid Search 新实现。
- Provider Fallback。
- Provider 路由策略。
- 成本计费/Token quota。
- MQ/Kafka/Temporal。
- 新的 Agent orchestration。

上述能力继续保留在后续产品路线，不因本任务提前实现。
