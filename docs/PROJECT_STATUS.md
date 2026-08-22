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
- 当前新增工作：2.2-E Model Provider / Model Profile Governance Foundation，先建立组织范围的 Provider / Profile 数据模型、CRUD API、权限、Audit 与 Migration；不提前引入 Reranker / Hybrid / Provider Fallback / 路由 / 成本治理。

## 当前 main 基线

开发必须从最新 `main` 创建分支；历史提交与旧状态文档不得作为当前代码基线。

## 已验证基线

以下结果为此前开发者实际执行反馈，未将其错误标记为本轮 2.2-E 已重新执行：

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

Real Provider regression 与冻结 baseline 一致：Recall@3=0.6、Precision@3=0.333333、MRR=0.6，identity 未发生变化，provider error rate=0。

## 当前 2.2-E 目标

1. Provider 与实际供应商身份解耦：`provider_type` 表示技术适配器，`provider_name` 表示实际供应商/部署身份。
2. Model Profile 支持 `chat` / `embedding` 两类模型。
3. Embedding Profile 必须保存 dimension；Chat Profile 不保存 embedding dimension。
4. Provider endpoint 可治理；credential 只能保存 reference，不保存实际 Secret。
5. Provider / Profile 按 Organization scope 管理，写操作要求 owner/admin。
6. Provider / Profile 变更写入 AuditLog。
7. Provider 删除前必须确认不存在 Profile。
8. 同一 Provider + model type 只能有一个 default Profile。
9. 为 Runtime / Evaluation 后续接入 `model_profile_id` 提供稳定数据库身份。
10. 不在本任务提前实现 Reranker、Hybrid、Fallback、Provider routing、成本/用量治理。

详细 Contract：`docs/02-phases/PHASE_2_2_E_MODEL_PROVIDER_PROFILE.md`。

## 当前实现

- `model_providers` / `model_profiles` 数据模型。
- Migration `0025_model_provider_governance`。
- `/api/v1/model-providers` Provider CRUD。
- Provider 下 Model Profile CRUD。
- Organization membership / management authorization。
- Audit trace metadata。
- API Contract tests。

## 下一步

1. 本地执行 2.2-E API contract test 与 migration/head verification。
2. 执行 Backend regression gate。
3. 执行 Real API gate，验证真实 PostgreSQL CRUD、Organization scope、Audit 与 lifecycle。
4. Runtime Profile Resolution：AgentVersion / Chat 支持 `model_profile_id`，执行时解析 Provider/Profile，并将 identity 写入 execution trace。
5. Evaluation Profile Selection：evaluation runner 使用受治理 Model Profile，并将 Profile identity 写入 evaluation trace / baseline identity。
6. Frontend Provider/Profile 管理与 Browser E2E 在确认进入该阶段后实施。
7. 只有 Runtime / Evaluation Profile 接入及其 Real API evidence 完成后，才评估是否关闭 2.2。

## 开发纪律

- 未实际执行的测试不得记录为 Passed。
- Baseline 只用于 regression comparison，不得通过修改 baseline 或降低阈值掩盖质量回归。
- 线上 Runtime 数据源继续使用数据库；JSON/JSONL 只用于版本化 evaluation dataset / result。
- 新业务代码不得新增具体模型名称硬编码。
- 新增数据库表必须先有 Migration。
- Secret 不进入数据库明文、CLI、报告或 Git。
- Phase 2.3 的完整 Provider Governance（路由/Fallback/成本/用量治理）仍保持产品路线候选，不因 2.2-E 提前实施。