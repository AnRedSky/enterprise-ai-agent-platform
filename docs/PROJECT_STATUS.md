# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已完成既有交付范围，并已有开发者实际执行验证。
- 2.2-C Real Provider Quality Gate：已通过当前 main 的真实 Provider baseline regression。
- 2.2-D Retrieval Quality Regression / Traceability：代码、持久化、API contract 与 Real API traceability 已完成当前定义范围，并已有开发者实际验证通过。
- 2.2-E Model Provider / Model Profile Governance Foundation：Provider / Profile 数据模型、CRUD API、权限、Audit、Migration 已完成；Runtime Profile Resolution E-1 已实现；Retrieval Evaluation Profile Selection E-2 已实现，当前进行 cross-dimension Evaluation Vector Space 修正后的本地 Real Provider evidence 闭环。

## 当前 main 基线

开发严格基于最新 `main`，所有修复与开发直接提交 `main`，不创建长期开发分支。

## 已验证基线

此前开发者实际执行结果：

```text
Governed embedding profile targeted tests: 10 passed
Backend regression gate: 320 passed, 31 deselected
Migration head: 0026_model_profile_runtime_identity
Real HTTP API: 31 passed
Standalone Real API Gate: 31 passed
```

上述结果证明本轮 dimension preflight 修复前后的基础 Backend / Real API regression 均稳定；本次 cross-dimension 修复仍需开发者重新执行 Gate，不能把此前结果标记为本轮代码已验证。

## 本轮问题结论

此前 `settings.embedding_dimension=768` 被错误地同时当成生产 `knowledge_chunks` storage contract 和所有 Evaluation Profile 的合法维度上限，导致真实 1024 维 Embedding Profile 在 fixture 写入前被拒绝。

正确 Contract：

```text
Production Vector Space
  knowledge_chunks.embedding -> fixed configured production dimension (current 768)

Evaluation Vector Space
  retrieval_evaluation_vectors.embedding -> variable pgvector vector
  + embedding_dimension -> actual governed Profile dimension
  + knowledge_base_id -> evaluation scope
```

因此不同 Embedding Profile 不要求相同 dimension；每个 Profile 仍必须严格匹配自己的实际 embedding dimension，并在 Evaluation Vector Space 内按 dimension 隔离。生产向量表不修改、不降维、不截断。

## 本轮实现

- 新增 Migration `0027_retrieval_evaluation_vector_space`。
- 新增 `retrieval_evaluation_vectors`，使用 pgvector variable-dimension `vector`，并保存 `embedding_dimension`。
- `PgVectorRetrievalProvider` 对 evaluation record 识别 `evaluation_chunk_id`，将其写入独立 Evaluation Vector Space；搜索按 `knowledge_base_id + embedding_dimension` 隔离。
- 生产 `knowledge_chunks` 仍保持原 fixed-dimension contract。
- Evaluation provider 仍严格校验实际 embedding length 与当前 governed Profile dimension 一致；不允许通过截断、padding 或修改 baseline 绕过 mismatch。
- Governed smoke 不再把全局 768 storage dimension 当作两个 Profile 的共同 dimension；仅拒绝非正 dimension。
- 增加 cross-dimension unit tests，覆盖 1024 维 evaluation upsert/search 以及 768/1024 Profile smoke contract。
- Evaluation fixture prepare/cleanup 显式清理 Evaluation Vector Space。
- 更新 Phase 2.2-E Contract，明确 E-2 的 cross-dimension storage boundary。

## 当前待验证

本轮代码提交后必须由开发者本地实际执行：

1. Cross-dimension targeted tests。
2. Backend Regression Gate。
3. Migration head verification，确认 `0027_retrieval_evaluation_vector_space`。
4. Standalone Real API Gate。
5. Governed E-2 smoke，优先使用已安装的 `nomic-embed-text:latest` + `qwen3-embedding:0.6b` 验证 768 → 1024。
6. E-2 evidence：Profile / Provider identity、Organization scope、Audit/Trace、credential secret 不泄露。

在上述结果实际反馈前，不标记 E-2 为 Passed，也不进入 E-3。

## 下一步

1. 开发者执行本轮 cross-dimension targeted tests。
2. 执行 Backend / Migration / Real API Gate。
3. 执行 governed Profile A baseline → Profile B identity regression smoke，并确认 768 / 1024 两个 Evaluation Vector Space 不进入生产 `knowledge_chunks`。
4. E-2 evidence 全部通过后，才进入 2.2-E-3 Frontend Provider/Profile Management。
5. E-3 继续遵循 DEVELOPMENT.md：Backend/API contract → Frontend API Types/Vitest/UI → Backend/Frontend 独立 Gate → Browser E2E → 文档验收。

## 开发纪律

- 未实际执行的测试不得记录为 Passed。
- Baseline 只用于 regression comparison，不得通过修改 baseline 或降低阈值掩盖质量回归。
- 线上 Runtime 数据源继续使用数据库；JSON/JSONL 只用于版本化 evaluation dataset / result / baseline。
- 新业务代码不得新增具体模型名称硬编码。
- 新增数据库表或字段必须先有 Migration。
- Secret 不进入数据库明文、CLI、报告或 Git。
- Phase 2.3 的完整 Provider Governance（路由/Fallback/成本/用量治理）仍保持产品路线候选，不因 2.2-E 提前实施。
- 当前已记录的 PowerShell `<PROFILE_UUID>` 占位符误用见 `docs/04-errors/2026-08-22-phase-2-2-e-governed-evaluation-placeholder-command.md`；后续手工验证必须替换为真实 UUID，或优先使用自动化 smoke script。
