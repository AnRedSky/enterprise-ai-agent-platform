# Phase 2.2 — Retrieval Production Quality

> 状态：**进行中 / 2.2-B Dataset / Runner、2.2-C Real Provider Quality Gate 与 2.2-D baseline regression 已完成既有交付范围；最新 main 的 Scheduled Trigger Real API 与 Real Provider runner 暴露回归问题，本轮已完成代码修复，待本地 Gate 重新验证；Citation correctness Contract 已实现，真实 Runtime citation 与 Debug/Audit/Observability traceability 仍在推进**
> 前置：Phase 2.1 已正式关闭
> 产品主题：企业知识问答的真实语义检索质量、可量化评测与 Provider 回归

Phase 2.2 的目标不是重新建设 Retrieval，而是把现有 Retrieval 能力提升为可重复、可量化、可审计的生产质量体系。

## 2.2-A / B / C / D 当前状态

2.2-A 已形成真实 Provider、Dataset、Recall@K、Precision@K、MRR、Citation correctness、latency、provider error rate、regression identity 与 failure/fallback 的质量契约。

2.2-B 已完成 Dataset Loader 与 PostgreSQL/pgvector evaluation runner。最新 main 暴露 evaluation fixture 与 Runtime hydration contract 不一致问题，已修复，待重新本地验证。

2.2-C 已完成真实 Ollama Provider + PostgreSQL/pgvector Quality Gate，并冻结真实 baseline；最新 main 的 runtime bridge 重跑曾因 fixture hydration 状态不一致得到 0 recall / 0 MRR，本轮已修复 fixture 生命周期。

当前 baseline 仅代表真实 Provider / Dataset / Retrieval 配置的可重复回归基线，不代表绝对语义质量已达生产目标。禁止通过修改指标、fallback、截断或补零提高结果。

2.2-D 已完成 Provider / model / dimension / dataset / retrieval-mode / top-k identity 与 Recall@K / Precision@K / MRR regression comparison，以及真实 Runtime citation evidence bridge。

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
Acceptance
```

## 8. Definition of Done

Phase 2.2 关闭前至少必须满足：

1. Retrieval Quality Contract 已冻结。
2. Evaluation Dataset 可版本化、可重复执行。
3. Recall@K / Precision@K / MRR / Citation correctness 定义明确并有自动化计算。
4. Real Provider Quality Gate 通过。
5. Provider / model / dataset regression 可比较。
6. Provider failure / fallback semantics 有自动化证据。
7. Retrieval quality 结果与现有 Citation / Audit / Observability 可追踪。
8. `PROJECT_STATUS.md`、Phase、Acceptance、错误记录同步。
