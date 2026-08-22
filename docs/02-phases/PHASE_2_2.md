# Phase 2.2 — Retrieval Production Quality

> 状态：**进行中 / 2.2-B Dataset / Runner、2.2-C Real Provider Quality Gate 与 2.2-D Retrieval Quality Regression / Traceability 当前定义范围已完成并通过此前开发者本地验证；2.2-E Model Provider / Model Profile Governance Foundation 已进入实现。**
> 前置：Phase 2.1 已正式关闭
> 产品主题：企业知识问答的真实语义检索质量、可量化评测与 Provider 回归

Phase 2.2 的目标不是重新建设 Retrieval，而是把现有 Retrieval 能力提升为可重复、可量化、可审计的生产质量体系。

## 2.2-A / B / C / D 当前状态

2.2-A 已形成真实 Provider、Dataset、Recall@K、Precision@K、MRR、Citation correctness、latency、provider error rate、regression identity 与 failure/fallback 的质量契约。

2.2-B 已完成 Dataset Loader 与 PostgreSQL/pgvector evaluation runner。evaluation fixture 与 Runtime hydration contract 不一致问题已修复，并已有开发者实际执行验证证据。

2.2-C 已完成真实 Ollama Provider + PostgreSQL/pgvector Quality Gate，并冻结真实 baseline。当前 main 的 baseline regression 已通过，未修改冻结指标掩盖回归。

2.2-D 已完成 Provider / model / dimension / dataset / retrieval-mode / top-k identity 与 Recall@K / Precision@K / MRR regression comparison，以及真实 Runtime citation evidence bridge。Evaluation run / case / regression summary 已持久化到现有 Runtime Observability / Audit 模型；trace API contract 与 Real API traceability 自动化测试已完成并通过此前本地验证。

## 2.2-E Model Provider / Model Profile Governance Foundation

当前进入 2.2-E，目标是把 Chat / Embedding 模型从 runner、环境变量和业务代码中的具体模型名称进一步提升为可治理的 Provider / Profile 身份。

### Model Provider

组织范围内的 Provider / deployment identity：

```text
organization_id
name
provider_type
provider_name
endpoint
credential_ref
enabled
metadata
```

### Model Profile

Provider 下可选择的具体模型：

```text
provider_id
name
model_type(chat|embedding)
model_name
dimension
capabilities
parameters
enabled
is_default
```

Embedding Profile 必须声明 dimension；Chat Profile 不声明 embedding dimension。

### 当前实现边界

本阶段只建立：

- 数据模型与 Migration。
- Organization scoped Provider / Profile CRUD API。
- owner/admin 写权限。
- credential reference 安全边界。
- Provider / Profile AuditLog。
- default Profile 管理。
- API contract 自动化测试。

下一步才接入 Runtime 与 Evaluation 的 `model_profile_id` 选择和 trace identity；不在本阶段引入 Reranker / Hybrid / Fallback / 路由 / 成本治理。

详细 Contract 见 `PHASE_2_2_E_MODEL_PROVIDER_PROFILE.md`。

## 当前增强：Evaluation Configuration

评估运行与线上 Runtime 配置保持分离，但不再把评估模型和评估参数固化在 runner 代码中。

### 可配置的检索模型 / Provider

一次 evaluation run 可以显式覆盖：

```text
embedding_provider
embedding_base_url
embedding_model
embedding_dimension
embedding_timeout_seconds
```

支持 `ollama` 与 `openai-compatible`。OpenAI-compatible 的 API key 只允许通过环境变量名引用，不能把 Secret 作为命令行参数或报告字段保存。

线上 Runtime 继续使用 `settings`；评估 runner 将显式 provider 注入 `VectorKnowledgeRetrievalService`，不会修改全局应用配置。

### 可配置的评估参数

```text
dataset
fixture
baseline
k / top_k
min_score
min_recall_at_k
min_precision_at_k
min_mrr
min_citation_correctness
max_error_rate
```

阈值用于产品质量门禁；baseline regression 仍独立比较 Provider / model / dimension / dataset / retrieval mode / top-k identity 与历史指标，不得通过降低阈值或修改 baseline 掩盖回归。

Evaluation trace 会持久化本次评估参数，保证一次运行能够被审计和复现。

## 3. 现有 Phase 1.4 能力边界

必须复用并保持：

```text
Document
 ↓
Parser / Cleaner
 ↓
Chunker
 ↓
Embedding Provider
 ↓
Vector / Hybrid Retrieval
 ↓
Context Builder
 ↓
Runtime
 ↓
Citation / Audit / Observability
```

线上 Retrieval 继续使用数据库数据源，评测 JSON/JSONL 只能作为版本化评测输入/输出，不能替代业务数据源。

## 4. Evaluation Case

最小 case 应能够表达：

```text
case_id
query
expected_sources[]
relevant_chunk_ids[] / relevant_source_ids[]
expected_citation_targets[]
metadata
```

当前 Dataset Loader 已严格校验 `id/query/relevant_chunk_ids/expected_citation_targets`；`expected_citation_targets` 必须是 `relevant_chunk_ids` 的子集。

## 5. 指标

- Recall@K：Top-K 是否覆盖 relevant items。
- Precision@K：Top-K 返回结果中 relevant items 的比例。
- MRR：第一个 relevant result 的排名质量。
- Citation correctness：最终引用 target 必须来自实际检索结果且属于 expected citation targets；不得只检查 citation 字段存在。
- Operational metrics：至少记录 retrieval latency 与 provider error rate，并与质量结果分开。

## 6. Failure / Fallback Boundary

- Real Provider unavailable / timeout / dimension mismatch 属于真实失败，必须保留失败证据。
- `fallback_to_lexical` 只有显式配置时才允许改变 retrieval semantics，并必须在结果中标识 fallback。
- 不允许通过捕获 Provider error 后直接切换到 lexical 来伪造 vector quality success。
- Mock Provider 不得用于声明真实语义质量通过。

## 7. Gate 设计

```text
2.2-A Contract
    ↓
2.2-B Dataset / Runner
    ↓
Backend regression
    ↓
Real Provider Quality Gate
    ↓
Retrieval quality regression
    ↓
Citation correctness + Debug / Audit / Observability traceability
    ↓
2.2-E Model Provider / Profile Governance Foundation
    ↓
Acceptance
```

## 8. 既有实际验证证据

```text
API Runtime Contract: 2 passed
Real HTTP API: 31 passed
Backend regression: 309 passed, 31 deselected
Migration head: 0024_embedding_dimension_contract
Real Provider:
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
Backend Release / Regression Gate: passed
```

以上为此前开发者实际反馈，不作为本次 2.2-E 已重新执行的证据。

## 9. Definition of Done

Phase 2.2 当前扩展任务完成前至少必须满足：

1. Retrieval Quality Contract 已冻结。
2. Evaluation Dataset 可版本化、可重复执行。
3. Recall@K / Precision@K / MRR / Citation correctness 定义明确并有自动化计算。
4. Real Provider Quality Gate 通过。
5. Provider / model / dataset regression 可比较。
6. Provider failure / fallback semantics 有自动化证据。
7. Retrieval quality 结果与现有 Citation / Audit / Observability 可追踪。
8. Evaluation model/provider 与 quality parameters 可显式配置并进入 trace。
9. Model Provider / Model Profile 具备组织范围数据模型、CRUD API、权限、Audit 与 migration。
10. Runtime / Evaluation 后续接入 Profile 后必须保留 Provider/Profile/model/dimension identity。
11. `PROJECT_STATUS.md`、Phase、Acceptance、错误记录同步。

当前 1-8 已形成既有工程实现与 Gate 证据；本次先完成第 9 项基础设施，后续完成第 10 项后再评估 Phase 2.2 是否关闭。