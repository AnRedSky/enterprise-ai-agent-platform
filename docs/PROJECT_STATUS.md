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
- 2.2-E Model Provider / Model Profile Governance Foundation：Provider / Profile 数据模型、CRUD API、权限、Audit、Migration 已完成；Runtime Profile Resolution E-1 已实现；Retrieval Evaluation Profile Selection E-2 已实现，当前重点是完成本地真实 Provider evidence 闭环。

## 当前 main 基线

开发严格基于最新 `main`，所有修复与开发直接提交 `main`，不创建长期开发分支。

## 已验证基线

以下结果为此前开发者实际执行反馈，未将其错误标记为本轮 E-1/E-2 新增代码已重新执行：

```text
API contract: 10 passed
Unit retrieval evaluation baseline: 8 passed
Backend regression gate:
  Backend regression: 318 passed, 31 deselected
  Migration head: 0026_model_profile_runtime_identity
  Real HTTP API: 31 passed
  Backend regression gate: passed
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
```

Real Provider regression 与既有 baseline 一致：Recall@3=0.6、Precision@3=0.333333、MRR=0.6，identity 未发生变化，provider error rate=0%。

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
- `scripts/evaluation/knowledge/run_governed_embedding_profile_smoke.py` 使用本地已安装 Ollama 模型创建临时 governed Embedding Profiles，自动获取实际 dimension，执行 Profile A baseline freeze 与 Profile B identity regression 验证；测试不会下载模型并在结束时清理临时治理数据。
- Governed evaluation smoke 的 dimension probe 已改为复用生产 `OllamaEmbeddingProvider`，不再在 smoke 脚本内维护第二套 Ollama embedding HTTP 协议；新增 unit test 覆盖该适配器复用。
- Retrieval evaluation fixture cleanup 已增加显式 transaction rollback，避免 pgvector 写入失败后 cleanup 再次使用 aborted transaction，掩盖原始错误。
- Governed evaluation smoke 已增加 storage-dimension preflight：在创建临时 Provider/Profile fixture 前，拒绝任何与当前 `settings.embedding_dimension` pgvector contract 不一致的实际模型维度，避免再次进入 `knowledge_chunks` 写入失败路径。

## 当前待验证 / 阻塞

本轮已实际发现：`nomic-embed-text:latest` 为 768 维，而当前本地另一个可用 Embedding 模型 `qwen3-embedding:0.6b` 的实际维度与当前 pgvector dimension contract 不一致。原 smoke 因此在 `knowledge_chunks` 写入后进入 `InFailedSQLTransactionError`；该错误已经记录在 `docs/04-errors/2026-08-22-phase-2-2-e-governed-evaluation-pgvector-dimension-transaction.md`，并已修复 cleanup 的 transaction masking。

本轮修复后，dimension mismatch 应在 fixture 创建前直接失败，并明确报告 Profile dimension 与 pgvector storage contract，不再产生 vector write、aborted transaction 或 Windows event-loop cleanup 噪声。

因此以下仍不得标记为 Passed：

1. Governed evaluation smoke 的 Profile A/B 正向 identity regression。
2. 使用两个不同且与当前 pgvector dimension contract 兼容的 Embedding Profiles 完成 Real Provider evaluation。
3. E-2 Real API evidence 闭环。
4. E-2 完成后进入 2.2-E-3 Frontend Provider/Profile Management。

当前本地资源约束下禁止下载新模型；必须使用已安装模型验证。如果没有第二个兼容 dimension 的模型，应继续保持为环境能力阻塞，而不是通过修改 baseline、截断向量或下载模型强行通过。

## 下一步

1. 在当前本地环境重新执行 API contract + migration/head + Backend Gate + Real API Gate，确认 cleanup 修复不产生回归；其中 Real API 单次 `httpx.ReadError/WinError 10054` 需要完整 gate 重跑确认是否为环境瞬时连接中断，不能直接修改业务测试以掩盖。
2. 执行 governed smoke；使用当前 `nomic-embed-text:latest` + `qwen3-embedding:0.6b` 时应在 fixture 创建前得到明确 dimension contract blocker。
3. 只有存在第二个兼容 dimension 的已安装模型后，才执行 Profile A baseline freeze → Profile B identity regression 正向 evidence。
4. E-2 Real API evidence 通过后进入 2.2-E-3 Frontend Provider/Profile Management。

## 开发纪律

- 未实际执行的测试不得记录为 Passed。
- Baseline 只用于 regression comparison，不得通过修改 baseline 或降低阈值掩盖质量回归。
- 线上 Runtime 数据源继续使用数据库；JSON/JSONL 只用于版本化 evaluation dataset / result / baseline。
- 新业务代码不得新增具体模型名称硬编码。
- 新增数据库表或字段必须先有 Migration。
- Secret 不进入数据库明文、CLI、报告或 Git。
- Phase 2.3 的完整 Provider Governance（路由/Fallback/成本/用量治理）仍保持产品路线候选，不因 2.2-E 提前实施。
- 当前已记录的 PowerShell `<PROFILE_UUID>` 占位符误用见 `docs/04-errors/2026-08-22-phase-2-2-e-governed-evaluation-placeholder-command.md`；后续手工验证必须替换为真实 UUID，或优先使用自动化 smoke script。
