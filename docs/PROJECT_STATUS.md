# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已完成既有交付范围，并已有开发者实际执行验证。
- 2.2-C Real Provider Quality Gate：已通过当前 main 的真实 Provider baseline regression。
- 2.2-D Retrieval Quality Regression / Traceability：代码、持久化、API contract 与 Real API traceability 已完成当前定义范围，并已有开发者实际验证通过。
- 评估配置化：已完成 evaluation provider/model/dimension、dataset/fixture/baseline、top-k/min-score 与质量阈值的显式配置能力。
- 2.2-E Model Provider / Model Profile Governance Foundation：Provider / Profile 数据模型、CRUD API、权限、Audit、Migration 已完成；Runtime Profile Resolution E-1 已实现；Retrieval Evaluation Profile Selection E-2 已实现，待本地 Gate / Real API 证据闭环。

## 当前 main 基线

开发严格基于最新 `main`，所有修复与开发直接提交 `main`，不创建分支。

## 已验证基线

以下结果为此前开发者实际执行反馈，未将其错误标记为本轮 E-1/E-2 已重新执行：

```text
Real HTTP API: 31 passed
API Runtime Contract: 2 passed
Real Provider runner:
  provider=ollama
  model=nomic-embed-text:latest
  embedding_dimension=768
  cases=5
  provider_error_rate=0
  recall@3=0.6
  precision@3=0.333333
  mrr=0.6
  citation_correctness=0.333333
  quality_gate=passed
Backend regression gate:
  Backend regression: 309 passed, 31 deselected
  Migration head: 0024_embedding_dimension_contract
  Real HTTP API: 31 passed
  Backend regression gate: passed
```

Real Provider regression 与冻结 baseline 一致：Recall@3=0.6、Precision@3=0.333333、MRR=0.6，identity 未发生变化，provider error rate=0%。

## 当前 2.2-E 目标

1. Provider 与实际供应商身份解耦：`provider_type` 表示技术适配器，`provider_name` 表示实际供应商/部署身份。
2. Model Profile 支持 `chat` / `embedding` 两类模型。
3. Embedding Profile 必须保存 dimension；Chat Profile 不保存 embedding dimension。
4. Provider endpoint 可治理；credential 只能保存 reference，不保存实际 Secret。
5. Provider / Profile 按 Organization scope 管理，写操作要求 owner/admin。
6. Provider / Profile 变更写入 AuditLog。
7. Provider 删除前必须确认不存在 Profile。
8. 同一 Provider + model type 只能有一个 default Profile。
9. Runtime / Evaluation 使用 `model_profile_id`，并将 identity 固化到 trace / evaluation trace。
10. 不在本任务提前实现 Reranker、Hybrid、Fallback、Provider routing、成本/用量治理。

详细 Contract：`docs/02-phases/PHASE_2_2_E_MODEL_PROVIDER_PROFILE.md`。

## 当前实现

- `model_providers` / `model_profiles` 数据模型。
- Migration `0025_model_provider_governance`。
- Migration `0026_model_profile_runtime_identity`。
- `/api/v1/model-providers` Provider CRUD。
- Provider 下 Model Profile CRUD。
- Organization membership / management authorization。
- Audit trace metadata。
- AgentVersion 支持可选 `model_profile_id`。
- Chat Runtime 解析 Organization-scoped Chat Profile，并将 Provider endpoint / credential reference / model / parameters 交给 Model Gateway。
- Execution / ExecutionEvent 持久化 `model_profile_id` / `provider_id` identity。
- 未选择 Profile 时保留原 `model_id` / 环境变量兼容路径。
- Retrieval Evaluation runner 支持 `--model-profile-id`，按 evaluation actor 的 Organization membership 解析启用的 Embedding Profile。
- 选定 Embedding Profile 后，evaluation runner 从数据库读取 Provider endpoint、provider_type、provider identity、model_name、dimension 与 parameters；credential_ref 仅作为进程环境变量名解析，不进入 report / trace / audit。
- Evaluation report 固化 `model_profile_id` / `provider_id` / provider identity；baseline 在选择 governed Profile 时同步冻结 Profile / Provider identity。
- Legacy baseline 在未选择 governed Profile 时保持兼容，不要求重新冻结既有 baseline。
- Model Provider OpenAPI contract 测试改为验证语义约束（integer + minimum=1 + nullable），避免绑定 Pydantic union schema 的具体输出顺序。
- Standalone evaluation trace runner 显式注册 Model Profile / Provider ORM mapper，避免 `Execution.model_profile_id` 在独立脚本上下文中触发 SQLAlchemy metadata 缺失。

## 当前待验证

本轮 E-1/E-2 新增代码尚未由开发者本地重新执行，因此以下均保持“待验证”，不预填通过：

1. API contract / Backend regression。
2. Migration `0026_model_profile_runtime_identity` upgrade/head。
3. Real API Provider/Profile lifecycle。
4. 使用自定义 Chat Profile 的真实 Chat Runtime。
5. 使用自定义 Embedding Profile 的真实 Retrieval Evaluation。
6. 不同 Embedding Profile 的 baseline identity / regression 行为。
7. Execution / Evaluation trace 的 Profile / Provider identity 查询。
8. Secret 不进入 response / trace / audit 的验证。

## 下一步

1. 本地执行 E-1/E-2 API contract + migration/head + Backend Gate + Real API Gate。
2. 使用两个不同的 Organization-scoped Embedding Profiles，分别运行 Real Provider evaluation，确认 runner 不再依赖后端固定 embedding model/provider/dimension。
3. 冻结 governed Profile baseline 后，再执行第二个 Profile 的回归测试，确认 Profile identity change 被质量门禁识别，而不会通过修改 baseline 掩盖变化。
4. E-2 Real API evidence 通过后进入 2.2-E-3 Frontend Provider/Profile Management。
5. 只有 Runtime / Evaluation Profile 接入及其 Real API evidence 完成后，才评估是否关闭 2.2。

## 开发纪律

- 未实际执行的测试不得记录为 Passed。
- Baseline 只用于 regression comparison，不得通过修改 baseline 或降低阈值掩盖质量回归。
- 线上 Runtime 数据源继续使用数据库；JSON/JSONL 只用于版本化 evaluation dataset / result / baseline。
- 新业务代码不得新增具体模型名称硬编码。
- 新增数据库表或字段必须先有 Migration。
- Secret 不进入数据库明文、CLI、报告或 Git。
- Phase 2.3 的完整 Provider Governance（路由/Fallback/成本/用量治理）仍保持产品路线候选，不因 2.2-E 提前实施。
