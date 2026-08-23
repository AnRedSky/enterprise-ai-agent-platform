# Phase 2.2-E — Model Provider / Model Profile Governance Foundation

> 状态：**E-3 实现中**
> E-1 Runtime Profile Resolution、E-2 Retrieval Evaluation Profile Selection 已完成当前定义范围；E-2 cross-dimension 本地 Real Provider evidence 已通过。

## 1. 目标与边界

本阶段把 Chat / Embedding 模型从业务代码与 runner 固定值中解耦，形成可配置、可选择、可追踪、可评估的 Provider / Profile 基础设施。不提前实现 Phase 2.3 的 Reranker、Hybrid、Fallback、路由、成本或用量治理。

## 2. 核心对象

### Model Provider

组织范围 Provider / deployment identity：`organization_id`、`name`、`provider_type`、`provider_name`、`endpoint`、`credential_ref`、`enabled`、`metadata`。`credential_ref` 只能表示 Secret/环境变量引用。

### Model Profile

Provider 下可选择的具体模型：`provider_id`、`name`、`model_type(chat|embedding)`、`model_name`、`dimension`、`capabilities`、`parameters`、`enabled`、`is_default`。Embedding 必须声明 dimension；Chat 不允许填写 dimension。

## 3. 已完成 E-1 / E-2

- AgentVersion 支持 `model_profile_id`，Runtime 解析 Organization-scoped enabled Chat Profile。
- Execution / ExecutionEvent 固化 Profile / Provider / model identity；Secret 不进入 trace。
- Evaluation runner 支持 `--model-profile-id`，Provider / model / dimension / parameters 从数据库治理对象解析。
- Evaluation report / baseline 固化 governed Profile identity；identity 改变必须触发 regression，而不能静默复用旧 baseline。
- 新增 `0027_retrieval_evaluation_vector_space`，Evaluation Vector Space 使用 variable-dimension pgvector，并按 `knowledge_base_id + embedding_dimension` 隔离；生产 `knowledge_chunks` 仍保持 fixed dimension。

## 4. E-2 实际验证

开发者本地实际执行：

```text
13 cross-dimension targeted tests passed
0027_retrieval_evaluation_vector_space = head
Backend regression = 323 passed, 31 deselected
Real HTTP API = 31 passed
Standalone Real API = 31 passed
Governed smoke = status=passed
Profile A = nomic-embed-text:latest / 768
Profile B = qwen3-embedding:0.6b / 1024
Profile B quality_gate = failed because identity changed (expected regression evidence)
```

因此 E-2 不再处于“待验证”状态。上述 evidence 仅代表开发者反馈的本地实际结果，不把 CI 当验收依据。

## 5. E-3 Frontend Provider/Profile Management

### 5.1 Backend contract → Frontend API types/client

复用既有 Backend contract：

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

Frontend 已增加 `frontend/src/api/modelProviders.ts`，保持组织范围、Provider/Profile 类型与后端 schema 一致。

### 5.2 UI

新增 `/organizations/:id/model-providers` 管理页：

- Provider 列表、创建、编辑、删除。
- Profile 列表、创建、编辑、删除。
- Chat / Embedding 类型选择。
- Embedding dimension 输入与展示；Chat 保存时强制提交 `dimension=null`。
- enabled / default 状态展示与编辑。
- Credential 只展示 `credential_ref` 引用，不提供 Secret 输入/回显。
- 从 Organization detail 提供管理入口。

Backend 仍负责 owner/admin 权限、Organization scope、default 唯一性与删除约束；Frontend 不复制后端授权规则。

### 5.3 自动化测试

已增加：

```powershell
cd frontend
npm test -- --run tests/api/modelProviders.test.ts tests/views/ModelProviders.test.ts
```

E-3 代码提交后必须由开发者实际执行该 targeted Vitest；未执行前不标记 Passed。

### 5.4 Gate

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

若 UI 纳入浏览器验收，再独立执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\02_run_organization_e2e.ps1
```

不得创建 Full Regression Gate；Frontend Gate 不调用 pytest/Alembic/Real API Gate。

## 6. E-4 Acceptance 前置条件

E-3 必须完成 Frontend targeted Vitest、Frontend production build，并按需要完成 Browser E2E；随后汇总 Provider/Profile CRUD Real API、权限/Organization scope、Runtime Profile、Evaluation cross-dimension、Audit/Trace、Secret non-disclosure evidence。
