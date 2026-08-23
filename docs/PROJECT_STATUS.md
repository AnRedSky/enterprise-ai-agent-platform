# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**进行中**。
- 2.3-A Provider Governance Contract：**已实现，待开发者本地验证**。
- 2.3-B Backend Domain + API Contract：**已实现，待开发者本地验证**。

## Phase 2.2 最终验证证据

开发者在上一基线实际执行并反馈：

```text
Backend Real API Gate: 32 passed in 58.51s
Frontend Regression Gate: 18 test files / 75 tests passed; vue-tsc + Vite build passed
Model Provider/Profile Browser E2E: 2 passed in 8.1s
```

因此 **E-4 Passed / Phase 2.2 Closed**。不得继续向 2.2 塞入新的 Provider routing / fallback / cost / usage 功能。

## Phase 2.3 当前实现

### 2.3-A Provider Governance Contract

已提交可执行 Contract：

- `explicit_profile` / `organization_default` routing strategy；
- fallback eligible reasons：connectivity / timeout / rate limit / provider 5xx；
- bounded fallback attempts，默认 2；
- model type / capability / provider allowlist constraints；
- cost units + pricing source + pricing version；
- usage identity：organization/provider/profile/model_type/request/trace/outcome；
- Secret 不进入 usage/audit identity。

### 2.3-B Backend Domain + API Contract

已新增真实数据库 Provider/Profile 候选解析接口：

`POST /api/v1/model-providers/routing/resolve`

该接口：

- 使用 PostgreSQL Provider/Profile 数据；
- 强制 Organization membership scope；
- 支持 explicit profile 与 organization default；
- 强制 enabled/model_type/capability/provider allowlist；
- 不返回 endpoint、credential_ref 等敏感连接信息；
- 未新增数据库表或字段，因此当前不需要 Migration。

新增代码/测试：

- `backend/app/services/model_provider_governance_contract.py`
- `backend/tests/unit/test_model_provider_governance_contract.py`
- `backend/app/schemas/model_provider.py`
- `backend/app/services/model_provider.py`
- `backend/app/api/model_providers.py`
- `backend/tests/api_contract/test_api_model_provider_governance.py`

## 验证状态

本轮代码尚未由开发者在本地 uv/PostgreSQL/真实 Provider 环境执行，因此**以下全部 Pending**：

```text
2.3-A targeted unit test: Pending
2.3-B API Contract test: Pending
Backend default regression: Pending
Migration/head verification: Pending
Real API Gate: Pending
```

不得把上述 Pending 写成 Passed。

## 下一执行任务

**2.3-C Runtime Routing Integration**：把治理候选接入现有 `SessionService.load_runtime()` 与 `ModelGateway`，形成真实 candidate → provider invocation 链路；fallback 必须遵守 2.3-A failure semantics，不得使用 Mock fallback 伪造 Provider 成功。

若 2.3-C 引入持久化 routing policy / pricing / usage record，必须先 Alembic Migration。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用数据库；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码与 Phase/Acceptance/Error/Status 必须保持可追溯。
