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

### E-2 Retrieval Evaluation Profile Selection

E-2 的维度 Contract 已修正为：**不同 Embedding Profile 不要求相同 dimension；每个 Profile 必须与本次 evaluation vector space 的 dimension contract 一致。生产 `knowledge_chunks` 仍保持当前固定维度 contract，不被 Evaluation Profile dimension 改写。**

已实现以下边界：

- Evaluation runner 增加 `--model-profile-id`。
- 选择 Profile 后，runner 必须以 evaluation actor 的 Organization membership 为授权边界，只允许使用 active Organization 下启用的 Embedding Profile / Provider。
- `provider_type`、Provider endpoint、`provider_name`、`model_name`、Embedding `dimension` 与 Profile `parameters` 均从数据库治理对象解析，不再由 runner 固定具体模型身份。
- `credential_ref` 只作为进程环境变量名解析；实际 Secret 不进入 evaluation report、trace、audit 或 Git。
- Evaluation report 固化 `model_profile_id`、`provider_id`、provider identity、model identity 与实际 embedding dimension。
- 选择 governed Profile 时，baseline 同步冻结 Profile / Provider identity；Profile 变化会被 regression gate 识别为 identity change。
- 未选择 governed Profile 时保持现有环境变量/CLI 兼容路径，既有 legacy baseline 不需要无意义地重新冻结。
- 仍然只使用现有 Embedding Provider + PostgreSQL/pgvector retrieval path，不引入 Reranker、Hybrid、Fallback 或 Provider routing。
- 新增独立 `retrieval_evaluation_vectors` Evaluation Vector Space。其 `vector` 列不绑定单一 dimension，并同时保存 `embedding_dimension`；provider 在写入与检索时仍强制校验 Profile dimension，因此不同 Profile 可以使用 768、1024 等不同维度而不会进入生产 `knowledge_chunks`。
- Evaluation Vector Space 按 `knowledge_base_id + embedding_dimension` 隔离，并在 fixture 准备/清理阶段删除；生产固定维度向量不会与 Evaluation 向量混用。

## 6. Migration

新增：

- `model_providers`
- `model_profiles`
- `0026_model_profile_runtime_identity`：为 AgentVersion / Execution / ExecutionEvent 增加 governed Profile identity。
- `0027_retrieval_evaluation_vector_space`：新增独立 Evaluation Vector Space，支持每个 Embedding Profile 使用自己的 dimension contract。

E-2 **不修改既有 `knowledge_chunks` schema，也不把生产向量列改成可变维度**；新增 Evaluation table 只承载 evaluation fixture / evaluation vector。

## 7. 自动化验证

当前 API contract 测试：

```powershell
cd backend
uv run pytest -q tests/api_contract/test_model_provider_contract.py
uv run pytest -q tests/api_contract/test_api_agents_endpoints.py tests/api_contract/test_model_provider_contract.py tests/api_contract/test_model_profile_runtime_contract.py
```

E-2 baseline identity 单元测试：

```powershell
uv run pytest -q tests/unit/test_retrieval_evaluation_baseline.py
```

E-2 cross-dimension vector-space tests：

```powershell
uv run pytest -q `
  tests/unit/test_governed_embedding_profile_smoke.py `
  tests/unit/test_evaluation_vector_space.py
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

### E-2 governed evaluation 自动化 Smoke

为避免手工复制 UUID、避免测试污染正式治理数据，提供：

```powershell
uv run python .\scripts\evaluation\knowledge\run_governed_embedding_profile_smoke.py
```

脚本行为：

1. 检查 `VECTOR_PROVIDER=pgvector`。
2. 通过 Ollama `/api/tags` 确认两个模型已经安装；**不会下载任何模型**。
3. 通过生产 `OllamaEmbeddingProvider` 获取两个现有模型的实际 embedding dimension，不在脚本中硬编码 dimension。
4. 允许 Profile A / Profile B 使用不同 dimension；只拒绝无效的空/非正 dimension。
5. 在现有 active Organization 下创建临时 Ollama Provider 与两个 Embedding Profiles。
6. 使用 Profile A 在独立 Evaluation Vector Space 冻结临时 baseline。
7. 使用 Profile B 复用 Profile A baseline，要求 quality gate 因 governed Profile identity 变化而失败。
8. 检查 evaluation report 中的 `model_profile_id` / `provider_id`、model identity 与 dimension。
9. 删除临时 Provider/Profile，并清理 Evaluation Vector Space。

默认使用当前本地已安装的：

```text
nomic-embed-text:latest
bge-m3:latest
```

也可以显式指定现有模型：

```powershell
uv run python .\scripts\evaluation\knowledge\run_governed_embedding_profile_smoke.py `
  --profile-a-model nomic-embed-text:latest `
  --profile-b-model qwen3-embedding:0.6b
```

脚本不会执行 `ollama pull`。如果指定模型不存在，测试直接失败并打印 `/api/tags` 中的可用模型。

### E-2 手动验证

如果需要手工验证，必须先把示例中的 `<EMBEDDING_PROFILE_UUID>` 替换为数据库中真实存在、当前 evaluation actor 有权访问的 Embedding Profile UUID；**不要把尖括号占位符原样复制到 PowerShell**。

1. 创建 Organization-scoped Provider，并确认 `provider_type` / `provider_name` / endpoint / credential reference 正确。
2. 在同一 Provider 下创建两个 enabled Embedding Profiles，允许实际 dimension 不同；模型必须为当前 Ollama 已安装模型，不下载新模型。
3. 使用 active Organization member 的 actor 执行 evaluation。
4. 使用 `--model-profile-id <真实 UUID>` 运行 Real Provider evaluation；确认 provider/model/dimension 与数据库 Profile 一致。
5. 使用 Profile A 在独立 Evaluation Vector Space 冻结 baseline。
6. 使用 Profile B 对同一 dataset 运行 evaluation；若复用 Profile A baseline，quality gate 必须因为 `model_profile_id` / Provider identity 变化而失败，而不是静默复用 A 的 baseline。
7. 查询 evaluation trace，确认 `model_profile_id` / `provider_id` / dimension 可追踪，且 credential secret 不出现。

示例：

```powershell
uv run python .\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py `
  --model-profile-id <真实的_EMBEDDING_PROFILE_UUID> `
  --k 3
```

首次冻结新的 governed Profile baseline：

```powershell
uv run python .\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py `
  --model-profile-id <真实的_EMBEDDING_PROFILE_UUID> `
  --baseline .\evaluation\knowledge_retrieval_profile_a_baseline.json `
  --freeze-baseline
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

**代码已实现，cross-dimension Evaluation Vector Space 已补齐，待开发者本地执行 Real Provider / baseline identity 验证闭环。**

- Evaluation runner 支持 `model_profile_id`。
- Evaluation report 固化 Profile identity 与 dimension。
- baseline identity 增加受治理 Profile identity，但仍保持 Provider/model/dimension 等核心字段可读。
- 不再要求两个 governed Embedding Profile 与生产 `knowledge_chunks` 使用相同 dimension。

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
6. Evaluation 使用不同 dimension Profile 的真实验证。
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
