# Phase 2.2 — Retrieval Production Quality

> 状态：**进行中 / 2.2-B Dataset / Runner、2.2-C Real Provider Quality Gate 与 2.2-D baseline regression 已完成当前交付范围**
> 前置：Phase 2.1 已正式关闭
> 产品主题：企业知识问答的真实语义检索质量、可量化评测与 Provider 回归

## 1. 企业场景

Phase 1.4 已形成 Knowledge / RAG / Retrieval 工程链路，包括 Embedding Provider Contract、Vector / Hybrid Retrieval、Citation、Evaluation 与 Debug。但历史边界明确：Mock Embedding 只能证明工程链路，不能代表真实模型语义质量；真实 Provider 的生产质量尚未形成正式质量 Contract。

Phase 2.2 的目标不是重新建设 Retrieval，而是把现有 Retrieval 能力提升为可重复、可量化、可审计的生产质量体系。

## 2. Scope

### 2.2-A Product / Retrieval Quality Contract

已形成以下产品与质量契约：

- 真实 Embedding Provider 的选择与配置边界。
- Evaluation Dataset 与业务 Corpus 的严格分离。
- Dataset 版本、case ID、query、expected sources、relevant chunks 的固定格式。
- Recall@K、Precision@K、MRR 的计算口径。
- Citation correctness / source attribution 的计算口径。
- Retrieval latency 与 provider error rate 的观察口径。
- Provider / model / dimension 变更后的回归比较规则。
- 最低质量门槛与失败处理规则。
- Mock / deterministic adapter 与真实 Provider 结果的明确证据边界。

### 2.2-B Evaluation Dataset / Runner

已实现并已由开发者本地 Gate 验证：

- 读取现有 `backend/evaluation/knowledge_retrieval_dataset.jsonl`。
- 对 case id、query、relevant chunk IDs、重复 ID、JSON 格式执行严格校验。
- 使用现有 PostgreSQL/pgvector fixture 执行实际 Retrieval。
- 输出 dataset schema version、case 级 ranking、latency、error 与聚合质量指标。
- 保留 baseline quality gate，并将 provider error 显式计入失败条件。
- Fixture 在执行完成后清理，不把评测文件当作线上业务数据源。

本轮开发者本地验证：

```text
Backend regression: 301 passed, 30 deselected
Migration head: 0024_embedding_dimension_contract
Real HTTP API: 30 passed
Real Provider smoke: PASS
```

### 2.2-C Real Provider Quality Gate

已完成真实 Provider Gate，并由开发者在本地实际执行：

- 使用真实 Ollama Embedding Provider，不使用 Mock Provider。
- 使用真实 PostgreSQL / pgvector Retrieval。
- Provider failure 保留为 observation / error，并导致 Gate failure；不静默 fallback。
- 输出 provider / model / embedding dimension / dataset version / retrieval mode / top-k / latency / error / fallback metadata。
- 显式 `--freeze-baseline` 首次冻结真实 Provider baseline；冻结动作本身不会被标记为质量 Gate Passed。
- 后续执行与已冻结 baseline 比较；provider、model、dimension、dataset、retrieval mode 或 top-k 变化会被识别为 regression identity change。

本地实际结果：

```text
provider=ollama
model=nomic-embed-text:latest
embedding_dimension=768
retrieval_mode=real-provider-pgvector
top_k=3
cases=5
successful_cases=5
error_cases=0
error_rate=0.0
fallback_count=0
fallback_used=false
recall@3=0.6
precision@3=0.333333
mrr=0.6
```

首次运行使用 `--freeze-baseline` 创建真实 baseline；随后再次执行 runner，得到：

```text
baseline.status=checked
identity_changed=false
recall delta=0
precision delta=0
mrr delta=0
provider_error_rate=0
quality_gate=passed
```

当前 baseline 的 0.6 Recall@3 / 0.333333 Precision@3 / 0.6 MRR 仅代表当前真实 Provider、Dataset 与 Retrieval 配置的可重复回归基线，不代表绝对语义质量已经达到生产目标。禁止通过修改指标、fallback、截断或补零提高结果。

#### 本地 Ollama Provider 边界

当前 pgvector migration 默认按配置维度建表；本轮本地实际使用 `nomic-embed-text:latest` 的 768 维 embedding，并通过项目已实现的 dimension contract 进行校验。不得把维度不匹配的向量截断、补零或伪造为通过。

### 2.2-D Retrieval Quality Regression

已实现 Provider / model / dataset / dimension / retrieval-mode / top-k identity 与 Recall@K / Precision@K / MRR 的 baseline regression comparison，并输出 regression report。开发者本地重跑结果显示 identity 未变化、质量指标 delta 全为 0、provider error rate 为 0，regression Gate 通过。

当前剩余工作不是重复冻结 baseline，而是继续建立：

1. Citation correctness 的自动化证据；
2. Retrieval Debug / Audit / Observability 对评测 case、Provider、Dataset 与 regression 结果的追踪关系；
3. 在真实数据与明确产品质量目标基础上再定义绝对质量门槛；当前不得用主观阈值否定或掩盖已经冻结的真实 baseline。

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

现有 `lexical-v2`、vector、hybrid、Citation、Retrieval Debug 和 provider-neutral Contract 不在 2.2-A 重新设计。线上 Retrieval 继续使用数据库数据源，评测 JSON/JSONL 只能作为版本化评测输入/输出，不能替代业务数据源。

## 4. 2.2-A Contract

### 4.1 Evaluation Case

最小 case 应能够表达：

```text
case_id
query
expected_sources[]
relevant_chunk_ids[] / relevant_source_ids[]
expected_citation_targets[]
metadata
```

当前 Dataset Loader 已对现有 JSONL 的 `id/query/relevant_chunk_ids` 核心字段执行严格校验；expected source / citation target 将在后续 Citation Gate 扩展到实际数据集。

### 4.2 指标

#### Recall@K

衡量 Top-K 是否覆盖已标注 relevant items。

#### Precision@K

衡量 Top-K 返回结果中 relevant items 的比例。

#### MRR

衡量第一个 relevant result 的排名质量。

#### Citation correctness

验证最终引用是否来自检索到且与 query / expected source 对应的有效来源；不得只检查 citation 字段存在。

#### Operational metrics

至少记录 retrieval latency 与 provider error rate，并与质量结果分开，不得用错误过滤提高质量分数。

### 4.3 最低门槛

具体阈值必须基于真实评测数据集和 Provider baseline 冻结后确定。2.2-A 不得凭空设定无法解释的数字门槛；但必须明确“未达到门槛即 Gate failed”的规则。

### 4.4 Provider 回归

Provider / model / dimension / dataset 任一发生变化时，必须记录：

```text
provider
model
embedding_dimension
dataset_version
retrieval_mode
top_k
metrics
latency
error_count
fallback_count
```

新结果必须可与 baseline 做差异比较。

## 5. Failure / Fallback Boundary

- Real Provider unavailable / timeout / dimension mismatch 属于真实失败，必须保留失败证据。
- `fallback_to_lexical` 只有显式配置时才允许改变 retrieval semantics，并必须在结果中标识 fallback。
- 不允许通过捕获 Provider error 后直接切换到 lexical 来伪造 vector quality success。
- Mock Provider 不得用于声明真实语义质量通过。

## 6. 数据与安全边界

- Evaluation Dataset 不得包含真实生产 Secret。
- Provider API key 只能进入未提交的 `backend/.env`。
- Dataset 中如包含业务文本，必须采用项目允许的测试数据或脱敏数据。
- Evaluation scope 必须与现有 Tenant / Organization / Knowledge authorization 边界一致。
- 评测结果必须能追踪 Provider / Dataset / Retrieval mode / Query case。

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
如有前端质量可见性变化，再增加 Frontend / Browser Gate
    ↓
Acceptance
```

2.2 不默认增加 Browser E2E；只有产品范围实际改变 Retrieval UI / Debug / quality visibility 时才建立独立 Browser Gate。

## 8. 明确 Out of Scope

- 新增通用 MQ/Kafka/Event Bus。
- Workflow / Scheduler / Multi-Agent 扩展。
- 完整 Model Provider Governance。
- 新的复杂 Retrieval DSL。
- 用数据库业务表存储评测数据而替代版本化评测文件。
- 用 Mock 结果替代真实 Provider 质量结论。

## 9. Definition of Done

Phase 2.2 关闭前至少必须满足：

1. Retrieval Quality Contract 已冻结。
2. Evaluation Dataset 可版本化、可重复执行。
3. Recall@K / Precision@K / MRR / Citation correctness 定义明确并有自动化计算。
4. Real Provider Quality Gate 通过。
5. Provider / model / dataset regression 可比较。
6. Provider failure / fallback semantics 有自动化证据。
7. Retrieval quality 结果与现有 Citation / Audit / Observability 可追踪。
8. `PROJECT_STATUS.md`、Phase、Acceptance、错误记录同步。
